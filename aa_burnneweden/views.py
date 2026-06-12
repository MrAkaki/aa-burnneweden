import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import models
from django.db.models import Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from esi.decorators import token_required
from esi.models import Token

from .models import Contract, DiscordNotificationPreference, OwnerCorporation
from .tasks import sync_contracts, update_contracts_for_puller

_PULLER_SSO_SCOPE = "esi-contracts.read_character_contracts.v1"


def _get_stats():
    today = now()
    cutoff_24h = today - timedelta(hours=24)
    cutoff_7d = today - timedelta(days=7)
    cutoff_30d = today - timedelta(days=30)

    fast_done = (
        Contract.objects.filter(date_completed__isnull=False)
        .annotate(
            dur=ExpressionWrapper(
                F("date_completed") - F("date_issued"), output_field=DurationField()
            )
        )
        .filter(dur__lt=timedelta(hours=4))
        .count()
    )

    # Daily completions for the last 30 days (for the chart)
    daily_rows = (
        Contract.objects.filter(date_completed__gte=cutoff_30d)
        .annotate(day=TruncDate("date_completed"))
        .values("day")
        .annotate(count=Count("pk"))
        .order_by("day")
    )
    daily_map = {row["day"]: row["count"] for row in daily_rows}
    chart_labels = []
    chart_values = []
    for i in range(29, -1, -1):
        day = (today - timedelta(days=i)).date()
        chart_labels.append(day.strftime("%b %d"))
        chart_values.append(daily_map.get(day, 0))

    return {
        "stat_open": Contract.objects.open().count(),
        "stat_running": Contract.objects.running().count(),
        "stat_closed_24h": Contract.objects.filter(date_completed__gte=cutoff_24h).count(),
        "stat_fast_done": fast_done,
        "stat_completed_week": Contract.objects.filter(date_completed__gte=cutoff_7d).count(),
        "stat_completed_month": Contract.objects.filter(date_completed__gte=cutoff_30d).count(),
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
    }


_CORP_SSO_SCOPE = "esi-contracts.read_corporation_contracts.v1"


@login_required
@permission_required("aa_burnneweden.basic_access", raise_exception=True)
def index(request):
    return redirect("aa_burnneweden:main_view")


@login_required
@permission_required("aa_burnneweden.basic_access", raise_exception=True)
def main_view(request):
    user = request.user
    ctx = _get_stats()
    is_staff = user.has_perm("aa_burnneweden.staff_access") or user.has_perm("aa_burnneweden.admin_access")
    ctx["is_staff"] = is_staff

    qs_base = Contract.objects.select_related(
        "issuer_character",
        "issuer_user",
        "issuer_user__profile__main_character",
        "accepted_by",
        "accepted_by__profile__main_character",
        "assigned_runner",
        "assigned_runner__profile__main_character",
    ).order_by("-date_issued")

    if is_staff or user.has_perm("aa_burnneweden.puller_access"):
        ctx["show_puller_tab"] = True
        puller_qs = qs_base.filter(issuer_user=user)
        ctx["puller_open"] = puller_qs.open()
        ctx["puller_running"] = puller_qs.running()
        ctx["puller_closed"] = puller_qs.closed()
        from esi.models import Token as EsiToken
        puller_tokens = EsiToken.objects.filter(user=user, scopes__name=_PULLER_SSO_SCOPE)
        ctx["puller_characters"] = list(
            puller_tokens.values("character_id", "character_name").distinct()
        )
        ctx["has_puller_token"] = puller_tokens.exists()
        ctx["my_open"] = Contract.objects.filter(issuer_user=user).open().count()
        ctx["my_running"] = Contract.objects.filter(issuer_user=user).running().count()
        ctx["my_completed"] = Contract.objects.filter(issuer_user=user, date_completed__isnull=False).count()

    if is_staff or user.has_perm("aa_burnneweden.runner_access"):
        ctx["show_runner_tab"] = True
        cutoff_7d = now() - timedelta(days=7)
        cutoff_30d = now() - timedelta(days=30)
        my_qs = qs_base.filter(
            models.Q(accepted_by=user) | models.Q(assigned_runner=user)
        )
        ctx["runner_available"] = qs_base.open()
        ctx["runner_running"] = my_qs.running().distinct()
        ctx["runner_closed"] = my_qs.closed().distinct()
        ctx["my_runs_active"] = ctx["runner_running"].count()
        ctx["my_runs_week"] = my_qs.filter(date_completed__gte=cutoff_7d).distinct().count()
        ctx["my_runs_month"] = my_qs.filter(date_completed__gte=cutoff_30d).distinct().count()

    if is_staff:
        from django.contrib.auth.models import Permission
        from django.contrib.auth.models import User as AuthUser
        runner_perm = Permission.objects.filter(codename="runner_access").first()
        if runner_perm:
            runner_users = AuthUser.objects.filter(
                models.Q(user_permissions=runner_perm) | models.Q(groups__permissions=runner_perm)
            ).select_related("profile__main_character").distinct()
        else:
            runner_users = AuthUser.objects.none()
        ctx["show_staff_tab"] = True
        ctx["staff_open"] = qs_base.open()
        ctx["staff_running"] = qs_base.running()
        ctx["staff_closed"] = qs_base.closed()
        ctx["status_choices"] = Contract.STATUSES
        ctx["runner_users"] = runner_users

    from django.apps import apps as django_apps
    ctx["discord_available"] = django_apps.is_installed("aadiscordbot")
    ctx["discord_prefs"], _ = DiscordNotificationPreference.objects.get_or_create(user=user)

    return render(request, "aa_burnneweden/main.html", ctx)


@login_required
@permission_required("aa_burnneweden.puller_access", raise_exception=True)
def dashboard(request):
    contracts = Contract.objects.for_puller(request.user).select_related(
        "owner_corporation__corporation",
        "issuer_character",
        "issuer_user",
        "issuer_user__profile__main_character",
        "accepted_by",
        "accepted_by__profile__main_character",
        "assigned_runner",
        "assigned_runner__profile__main_character",
    ).order_by("-date_issued")

    return render(request, "aa_burnneweden/dashboard.html", {"contracts": contracts})


@login_required
@permission_required("aa_burnneweden.puller_access", raise_exception=True)
@require_POST
def puller_sync(request):
    update_contracts_for_puller.delay(request.user.pk)
    messages.success(request, "Sync queued — your contracts will refresh shortly.")
    return redirect(reverse("aa_burnneweden:main_view") + "?tab=tab-puller")


@login_required
@permission_required("aa_burnneweden.puller_access", raise_exception=True)
@token_required(new=True, scopes=_PULLER_SSO_SCOPE)
def puller_add_character(request, token):
    return redirect(reverse("aa_burnneweden:main_view") + "?tab=tab-dashboard")


@login_required
@permission_required("aa_burnneweden.puller_access", raise_exception=True)
@require_POST
def puller_remove_character(request):
    from esi.models import Token as EsiToken

    character_id = request.POST.get("character_id")
    if character_id:
        deleted, _ = EsiToken.objects.filter(
            user=request.user,
            character_id=character_id,
            scopes__name=_PULLER_SSO_SCOPE,
        ).delete()
        if deleted:
            messages.success(request, "Character removed from contract sync.")
        else:
            messages.warning(request, "Character not found.")
    return redirect(reverse("aa_burnneweden:main_view") + "?tab=tab-dashboard")


@login_required
@permission_required("aa_burnneweden.runner_access", raise_exception=True)
def contracts_runner(request):
    qs = Contract.objects.for_runner(request.user).select_related(
        "owner_corporation__corporation",
        "issuer_character",
        "issuer_user",
        "issuer_user__profile__main_character",
        "accepted_by",
        "accepted_by__profile__main_character",
        "assigned_runner",
        "assigned_runner__profile__main_character",
    ).order_by("-date_issued")

    open_contracts = qs.open()
    my_contracts = qs.filter(
        models.Q(accepted_by=request.user) | models.Q(assigned_runner=request.user)
    ).filter(
        models.Q(date_started__isnull=False)
        | models.Q(date_completed__isnull=False)
        | models.Q(date_rejected__isnull=False)
        | models.Q(date_cancelled__isnull=False)
    ).distinct()

    return render(
        request,
        "aa_burnneweden/contracts_runner.html",
        {"open_contracts": open_contracts, "my_contracts": my_contracts},
    )


@login_required
@permission_required("aa_burnneweden.staff_access", raise_exception=True)
def contracts_staff(request):
    status_filter = request.GET.get("status", "")
    contracts = Contract.objects.select_related(
        "owner_corporation__corporation",
        "issuer_character",
        "issuer_user",
        "issuer_user__profile__main_character",
        "accepted_by",
        "accepted_by__profile__main_character",
        "assigned_runner",
        "assigned_runner__profile__main_character",
    ).order_by("-date_issued")

    if status_filter:
        contracts = contracts.with_status(status_filter)

    owners = OwnerCorporation.objects.select_related("corporation").filter(is_active=True)

    return render(
        request,
        "aa_burnneweden/contracts_staff.html",
        {
            "contracts": contracts,
            "status_choices": Contract.STATUSES,
            "current_status": status_filter,
            "owners": owners,
        },
    )


@login_required
@permission_required("aa_burnneweden.basic_access", raise_exception=True)
def contract_detail(request, pk):
    contract = get_object_or_404(
        Contract.objects.select_related(
            "owner_corporation__corporation",
            "issuer_character",
            "issuer_user",
            "issuer_user__profile__main_character",
            "accepted_by",
            "accepted_by__profile__main_character",
            "assigned_runner",
            "assigned_runner__profile__main_character",
        ).prefetch_related("items"),
        pk=pk,
    )
    user = request.user

    if (
        not user.has_perm("aa_burnneweden.runner_access")
        and not user.has_perm("aa_burnneweden.staff_access")
        and not user.has_perm("aa_burnneweden.admin_access")
    ):
        if contract.issuer_user != user:
            return HttpResponseForbidden()

    return render(request, "aa_burnneweden/contract_detail.html", {"contract": contract})


@login_required
@permission_required("aa_burnneweden.runner_access", raise_exception=True)
@require_POST
def contract_complete(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    user = request.user
    is_staff = user.has_perm("aa_burnneweden.staff_access") or user.has_perm("aa_burnneweden.admin_access")

    if not is_staff and contract.accepted_by != user and contract.assigned_runner != user:
        return HttpResponseForbidden()

    if contract.status != "running":
        messages.error(request, "Only running contracts can be completed.")
        return _smart_redirect(request)

    comment = request.POST.get("comment", "").strip()
    update_fields = ["date_completed", "completed_by"]
    contract.date_completed = now()
    contract.completed_by = user
    if comment:
        contract.staff_notes = comment
        update_fields.append("staff_notes")
    contract.save(update_fields=update_fields)

    from .notifications import notify_runner_contract_completed
    notify_runner_contract_completed.delay(contract.pk)

    messages.success(request, f"Contract #{contract.contract_id} marked as completed.")
    return _smart_redirect(request)


@login_required
@permission_required("aa_burnneweden.runner_access", raise_exception=True)
@require_POST
def contract_cancel(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    user = request.user
    is_staff = user.has_perm("aa_burnneweden.staff_access") or user.has_perm("aa_burnneweden.admin_access")

    if not is_staff and contract.accepted_by != user and contract.assigned_runner != user:
        return HttpResponseForbidden()

    if contract.status != "running":
        messages.error(request, "Only running contracts can be cancelled.")
        return _smart_redirect(request)

    contract.date_cancelled = now()
    contract.cancelled_by = user
    contract.save(update_fields=["date_cancelled", "cancelled_by"])

    from .notifications import notify_runner_contract_canceled
    notify_runner_contract_canceled.delay(contract.pk)

    messages.success(request, f"Contract #{contract.contract_id} cancelled.")
    return _smart_redirect(request)


@login_required
@permission_required("aa_burnneweden.staff_access", raise_exception=True)
@require_POST
def contract_reject(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    user = request.user

    if contract.status not in ("open", "running"):
        messages.error(request, "Only open or running contracts can be force-rejected.")
        return _smart_redirect(request)

    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "A rejection reason is required.")
        return _smart_redirect(request)

    contract.date_rejected = now()
    contract.rejected_by = user
    contract.staff_notes = reason
    contract.save(update_fields=["date_rejected", "rejected_by", "staff_notes"])

    from .notifications import notify_runner_contract_rejected
    notify_runner_contract_rejected.delay(contract.pk)

    messages.success(request, f"Contract #{contract.contract_id} rejected.")
    return _smart_redirect(request)


@login_required
@permission_required("aa_burnneweden.runner_access", raise_exception=True)
@require_POST
def bulk_complete(request):
    user = request.user
    is_staff = user.has_perm("aa_burnneweden.staff_access") or user.has_perm("aa_burnneweden.admin_access")
    pks = request.POST.getlist("pks")

    qs = Contract.objects.running().filter(pk__in=pks)
    if not is_staff:
        qs = qs.filter(models.Q(accepted_by=user) | models.Q(assigned_runner=user))

    from .notifications import notify_runner_contract_completed
    count = 0
    for contract in qs:
        contract.date_completed = now()
        contract.completed_by = user
        contract.save(update_fields=["date_completed", "completed_by"])
        notify_runner_contract_completed.delay(contract.pk)
        count += 1

    if count:
        messages.success(request, f"{count} contract(s) marked as completed.")
    else:
        messages.warning(request, "No eligible contracts were found.")
    return _smart_redirect(request)


@login_required
@permission_required("aa_burnneweden.runner_access", raise_exception=True)
@require_POST
def bulk_reject(request):
    user = request.user
    is_staff = user.has_perm("aa_burnneweden.staff_access") or user.has_perm("aa_burnneweden.admin_access")
    pks = request.POST.getlist("pks")
    reason = request.POST.get("reason", "").strip()

    if not reason:
        messages.error(request, "A rejection reason is required.")
        return _smart_redirect(request)

    qs = Contract.objects.running().filter(pk__in=pks)
    if not is_staff:
        qs = qs.filter(models.Q(accepted_by=user) | models.Q(assigned_runner=user))

    from .notifications import notify_runner_contract_rejected
    count = 0
    for contract in qs:
        contract.date_rejected = now()
        contract.rejected_by = user
        contract.staff_notes = reason
        contract.save(update_fields=["date_rejected", "rejected_by", "staff_notes"])
        notify_runner_contract_rejected.delay(contract.pk)
        count += 1

    if count:
        messages.success(request, f"{count} contract(s) rejected.")
    else:
        messages.warning(request, "No eligible contracts were found.")
    return _smart_redirect(request)


@login_required
@permission_required("aa_burnneweden.runner_access", raise_exception=True)
@require_POST
def bulk_cancel(request):
    user = request.user
    is_staff = user.has_perm("aa_burnneweden.staff_access") or user.has_perm("aa_burnneweden.admin_access")
    pks = request.POST.getlist("pks")

    qs = Contract.objects.running().filter(pk__in=pks)
    if not is_staff:
        qs = qs.filter(models.Q(accepted_by=user) | models.Q(assigned_runner=user))

    from .notifications import notify_runner_contract_canceled
    count = 0
    for contract in qs:
        contract.date_cancelled = now()
        contract.cancelled_by = user
        contract.save(update_fields=["date_cancelled", "cancelled_by"])
        notify_runner_contract_canceled.delay(contract.pk)
        count += 1

    if count:
        messages.success(request, f"{count} contract(s) cancelled.")
    else:
        messages.warning(request, "No eligible contracts were found.")
    return _smart_redirect(request)


@login_required
@permission_required("aa_burnneweden.staff_access", raise_exception=True)
@require_POST
def contract_reassign(request, pk):
    from django.contrib.auth.models import User

    contract = get_object_or_404(Contract, pk=pk)
    runner_id = request.POST.get("runner_id")

    if runner_id:
        try:
            runner = User.objects.get(pk=runner_id)
        except User.DoesNotExist:
            messages.error(request, "Selected runner not found.")
            return redirect("aa_burnneweden:contracts_staff")

        contract.assigned_runner = runner
        contract.save(update_fields=["assigned_runner"])
        messages.success(request, f"Contract #{contract.contract_id} assigned to {runner.username}.")
    else:
        contract.assigned_runner = None
        contract.save(update_fields=["assigned_runner"])
        messages.success(request, f"Contract #{contract.contract_id} unassigned.")

    return redirect("aa_burnneweden:contracts_staff")


@login_required
@permission_required("aa_burnneweden.basic_access", raise_exception=True)
@require_POST
def discord_settings(request):
    user = request.user
    pref, _ = DiscordNotificationPreference.objects.get_or_create(user=user)

    is_runner = (
        user.has_perm("aa_burnneweden.runner_access")
        or user.has_perm("aa_burnneweden.staff_access")
        or user.has_perm("aa_burnneweden.admin_access")
    )
    is_puller = (
        user.has_perm("aa_burnneweden.puller_access")
        or user.has_perm("aa_burnneweden.staff_access")
        or user.has_perm("aa_burnneweden.admin_access")
    )

    if is_runner:
        pref.notify_contract_created = "notify_contract_created" in request.POST
        pref.notify_contract_started = "notify_contract_started" in request.POST
        pref.notify_contract_rejected = "notify_contract_rejected" in request.POST
        pref.notify_contract_completed = "notify_contract_completed" in request.POST
    if is_puller:
        pref.notify_new_open_contracts = "notify_new_open_contracts" in request.POST
    pref.save()

    enabled = []
    if pref.notify_contract_created:
        enabled.append("New contract available")
    if pref.notify_contract_started:
        enabled.append("Contract started")
    if pref.notify_contract_rejected:
        enabled.append("Contract rejected")
    if pref.notify_contract_completed:
        enabled.append("Contract completed / canceled")
    if pref.notify_new_open_contracts:
        enabled.append("New open contracts")

    from .notifications import send_discord_confirmation_dm
    send_discord_confirmation_dm.delay(user.pk, enabled)

    messages.success(request, "Discord notification preferences saved.")
    return redirect(reverse("aa_burnneweden:main_view") + "?tab=tab-notifications")


@login_required
@permission_required("aa_burnneweden.admin_access", raise_exception=True)
def admin_config(request):
    owners = OwnerCorporation.objects.select_related("corporation", "character")
    return render(request, "aa_burnneweden/admin_config.html", {"owners": owners})


@login_required
@permission_required("aa_burnneweden.admin_access", raise_exception=True)
@require_POST
def admin_sync(request):
    sync_contracts.delay()
    messages.success(request, "ESI sync queued for all active corporations.")
    return redirect("aa_burnneweden:admin_config")


@login_required
@permission_required("aa_burnneweden.admin_access", raise_exception=True)
@token_required(new=True, scopes=_CORP_SSO_SCOPE)
def corp_sso_post_auth(request, token):

    character = EveCharacter.objects.filter(character_id=token.character_id).first()
    if not character:
        messages.error(request, "Character record not found. Please try again.")
        return redirect("aa_burnneweden:admin_config")

    corp, _ = EveCorporationInfo.objects.get_or_create(
        corporation_id=character.corporation_id,
        defaults={
            "corporation_name": character.corporation_name,
            "corporation_ticker": character.corporation_ticker,
            "member_count": 0,
        },
    )

    _, created = OwnerCorporation.objects.update_or_create(
        corporation=corp,
        defaults={"character": character, "is_active": True},
    )

    action = "Added" if created else "Updated"
    messages.success(
        request,
        f"{action} corporation '{corp.corporation_name}' "
        f"using character '{character.character_name}'.",
    )
    return redirect("aa_burnneweden:admin_config")


_VALID_TABS = frozenset(
    {"tab-dashboard", "tab-puller", "tab-runner", "tab-staff", "tab-notifications"}
)


def _smart_redirect(request):
    tab = request.POST.get("active_tab", "")
    base = reverse("aa_burnneweden:main_view")
    if tab in _VALID_TABS:
        return redirect(f"{base}?tab={tab}")
    return redirect(base)
