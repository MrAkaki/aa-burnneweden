from celery import shared_task
from celery.utils.log import get_task_logger
from django.apps import apps

logger = get_task_logger(__name__)


def _discord_active():
    return apps.is_installed("aadiscordbot")


def _send_dm(user, embed):
    """Resolve the Discord ID in sync Celery context, then dispatch via the fully-async path."""
    from aadiscordbot.cogs.utils.exceptions import NotAuthenticated
    from aadiscordbot.tasks import send_message
    from aadiscordbot.utils.auth import get_discord_user_id

    try:
        discord_id = get_discord_user_id(user)
    except NotAuthenticated:
        logger.warning("User %d has no linked Discord account, skipping DM.", user.pk)
        return
    send_message(user_id=discord_id, embed=embed)


@shared_task
def notify_runners_new_contract(contract_pk: int):
    """Broadcast a new open contract to all opted-in runners."""
    if not _discord_active():
        return
    from discord import Color, Embed

    from .models import Contract, DiscordNotificationPreference

    try:
        contract = Contract.objects.select_related("issuer_character", "issuer_user").get(pk=contract_pk)
    except Contract.DoesNotExist:
        return

    embed = Embed(
        title="New Burner Contract Available",
        description=f"**{contract.title or f'Contract #{contract.contract_id}'}**",
        color=Color.green(),
    )
    embed.add_field(name="Reward", value=f"{contract.reward:,.0f} ISK" if contract.reward else "—")
    embed.add_field(name="Issued by", value=contract.issuer_main_name)

    prefs = DiscordNotificationPreference.objects.filter(notify_contract_created=True).select_related("user")
    for pref in prefs:
        try:
            _send_dm(pref.user, embed)
        except Exception:
            logger.exception("Failed to DM user %d for new contract %d.", pref.user_id, contract_pk)


@shared_task
def notify_runner_contract_started(contract_pk: int):
    """Notify the specific runner that their contract has been accepted/started."""
    if not _discord_active():
        return
    from discord import Color, Embed

    from .models import Contract, DiscordNotificationPreference

    try:
        contract = Contract.objects.select_related("accepted_by", "assigned_runner").get(pk=contract_pk)
    except Contract.DoesNotExist:
        return

    runner = contract.assigned_runner or contract.accepted_by
    if not runner:
        return

    try:
        pref = runner.burner_discord_prefs
    except DiscordNotificationPreference.DoesNotExist:
        return

    if not pref.notify_contract_started:
        return

    embed = Embed(
        title="Contract Started",
        description=f"**{contract.title or f'Contract #{contract.contract_id}'}** is now active.",
        color=Color.blue(),
    )
    embed.add_field(name="Reward", value=f"{contract.reward:,.0f} ISK" if contract.reward else "—")

    try:
        _send_dm(runner, embed)
    except Exception:
        logger.exception("Failed to DM runner %d for started contract %d.", runner.pk, contract_pk)


@shared_task
def notify_runner_contract_rejected(contract_pk: int):
    """Notify the runner on a rejected contract."""
    if not _discord_active():
        return
    from discord import Color, Embed

    from .models import Contract, DiscordNotificationPreference

    try:
        contract = Contract.objects.select_related("accepted_by", "assigned_runner").get(pk=contract_pk)
    except Contract.DoesNotExist:
        return

    runner = contract.assigned_runner or contract.accepted_by
    if not runner:
        return

    try:
        pref = runner.burner_discord_prefs
    except DiscordNotificationPreference.DoesNotExist:
        return

    if not pref.notify_contract_rejected:
        return

    embed = Embed(
        title="Contract Rejected",
        description=f"**{contract.title or f'Contract #{contract.contract_id}'}** was rejected.",
        color=Color.red(),
    )
    if contract.staff_notes:
        embed.add_field(name="Reason", value=contract.staff_notes)

    try:
        _send_dm(runner, embed)
    except Exception:
        logger.exception("Failed to DM runner %d for rejected contract %d.", runner.pk, contract_pk)


@shared_task
def notify_runner_contract_completed(contract_pk: int):
    """Notify the runner that their contract was marked completed."""
    if not _discord_active():
        return
    from discord import Color, Embed

    from .models import Contract, DiscordNotificationPreference

    try:
        contract = Contract.objects.select_related("completed_by", "assigned_runner", "accepted_by").get(pk=contract_pk)
    except Contract.DoesNotExist:
        return

    runner = contract.assigned_runner or contract.accepted_by
    if not runner:
        return

    try:
        pref = runner.burner_discord_prefs
    except DiscordNotificationPreference.DoesNotExist:
        return

    if not pref.notify_contract_completed:
        return

    embed = Embed(
        title="Contract Completed",
        description=f"**{contract.title or f'Contract #{contract.contract_id}'}** has been completed.",
        color=Color.green(),
    )

    try:
        _send_dm(runner, embed)
    except Exception:
        logger.exception("Failed to DM runner %d for completed contract %d.", runner.pk, contract_pk)


@shared_task
def notify_runner_contract_canceled(contract_pk: int):
    """Notify the runner that their active contract was canceled."""
    if not _discord_active():
        return
    from discord import Color, Embed

    from .models import Contract, DiscordNotificationPreference

    try:
        contract = Contract.objects.select_related("accepted_by", "assigned_runner").get(pk=contract_pk)
    except Contract.DoesNotExist:
        return

    runner = contract.assigned_runner or contract.accepted_by
    if not runner:
        return

    try:
        pref = runner.burner_discord_prefs
    except DiscordNotificationPreference.DoesNotExist:
        return

    if not pref.notify_contract_completed:
        return

    embed = Embed(
        title="Contract Canceled",
        description=f"**{contract.title or f'Contract #{contract.contract_id}'}** was canceled.",
        color=Color.orange(),
    )

    try:
        _send_dm(runner, embed)
    except Exception:
        logger.exception("Failed to DM runner %d for canceled contract %d.", runner.pk, contract_pk)


@shared_task
def notify_pullers_open_contracts():
    """Periodic task: DM opted-in pullers about unannounced open contracts."""
    if not _discord_active():
        return
    from discord import Color, Embed

    from .models import Contract, DiscordNotificationPreference

    unannounced = list(
        Contract.objects.open()
        .filter(discord_dm_sent=False)
        .select_related("issuer_user", "issuer_character")
    )

    if not unannounced:
        return

    for contract in unannounced:
        if not contract.issuer_user_id:
            continue
        try:
            pref = contract.issuer_user.burner_discord_prefs
        except DiscordNotificationPreference.DoesNotExist:
            continue

        if not pref.notify_new_open_contracts:
            continue

        embed = Embed(
            title="Your Burner Contract is Open",
            description=f"**{contract.title or f'Contract #{contract.contract_id}'}** is now open and waiting for a runner.",
            color=Color.blurple(),
        )
        embed.add_field(name="Reward", value=f"{contract.reward:,.0f} ISK" if contract.reward else "—")

        try:
            _send_dm(contract.issuer_user, embed)
        except Exception:
            logger.exception("Failed to DM puller %d for open contract %d.", contract.issuer_user_id, contract.pk)

    pks = [c.pk for c in unannounced]
    Contract.objects.filter(pk__in=pks).update(discord_dm_sent=True)
    logger.info("Processed open contract DMs for %d contracts.", len(pks))


@shared_task
def send_discord_confirmation_dm(user_pk: int, enabled_events: list):
    """Send a confirmation DM when a user saves their notification preferences."""
    if not _discord_active():
        return
    from django.contrib.auth.models import User

    from discord import Color, Embed

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return

    if enabled_events:
        lines = "\n".join(f"• {e}" for e in enabled_events)
        embed = Embed(
            title="Burn New Eden — Notifications Enabled",
            description=f"You will now receive Discord DMs for:\n\n{lines}",
            color=Color.blurple(),
        )
    else:
        embed = Embed(
            title="Burn New Eden — Notifications Disabled",
            description="All Burn New Eden Discord DM notifications have been disabled.",
            color=Color.dark_gray(),
        )

    try:
        _send_dm(user, embed)
    except Exception:
        logger.exception("Failed to send confirmation DM to user %d.", user_pk)
