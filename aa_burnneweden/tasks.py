from celery import shared_task
from celery.utils.log import get_task_logger
from esi.exceptions import HTTPNotModified

from . import notifications  # noqa: F401 — register notification tasks with Celery

from django.utils.timezone import now

logger = get_task_logger(__name__)


@shared_task
def update_all_contracts():
    from .models import OwnerCorporation

    corp_pks = list(
        OwnerCorporation.objects.filter(is_active=True).values_list("pk", flat=True)
    )
    for pk in corp_pks:
        update_contracts_for_corporation.delay(pk)
    logger.info("Queued contract sync for %d corporations.", len(corp_pks))


@shared_task
def update_contracts_for_corporation(owner_corp_pk: int):
    from esi.models import Token

    from .models import Contract, ContractItem, OwnerCorporation
    from .providers import esi

    try:
        owner = OwnerCorporation.objects.select_related(
            "corporation", "character"
        ).get(pk=owner_corp_pk)
    except OwnerCorporation.DoesNotExist:
        logger.error("OwnerCorporation pk=%d not found.", owner_corp_pk)
        return

    corp_id = owner.corporation.corporation_id
    character_id = owner.character.character_id

    token = (
        Token.objects.filter(
            character_id=character_id,
            scopes__name="esi-contracts.read_corporation_contracts.v1",
        )
        .require_valid()
        .first()
    )

    if not token:
        logger.warning(
            "No valid ESI token for character %d (corp %d).", character_id, corp_id
        )
        return

    try:
        raw_contracts = esi.client.Contracts.GetCorporationsCorporationIdContracts(
            corporation_id=corp_id,
            token=token,
        ).results()
    except HTTPNotModified:
        logger.debug("Contracts unchanged for corp %d (304), skipping.", corp_id)
        return
    except Exception:
        logger.exception("ESI fetch failed for corp %d.", corp_id)
        return

    from .models import CANCELLED_ESI_STATUSES

    updated = 0
    for raw in raw_contracts:
        if raw.type != "item_exchange":
            continue
        if raw.assignee_id != corp_id:
            continue

        # ESI-cancelled/deleted/reversed contracts are not tracked — remove if present.
        if raw.status in CANCELLED_ESI_STATUSES:
            deleted, _ = Contract.objects.filter(
                owner_corporation=owner,
                contract_id=raw.contract_id,
            ).delete()
            if deleted:
                logger.info(
                    "Removed ESI-%s contract %d for corp %d.",
                    raw.status, raw.contract_id, corp_id,
                )
            continue

        issuer_char, issuer_user = _resolve_issuer(raw.issuer_id)

        contract, created = Contract.objects.get_or_create(
            owner_corporation=owner,
            contract_id=raw.contract_id,
            defaults={
                "issuer_character": issuer_char,
                "issuer_user": issuer_user,
                "title": raw.title or "",
                "price": raw.price or 0,
                "reward": raw.reward or 0,
                "volume": raw.volume or 0,
                "date_issued": raw.date_issued,
                "date_expired": raw.date_expired,
                "date_started": raw.date_accepted,
                # date_completed is app-managed (set via contract_complete view);
                # never import it from ESI — a contract completed in-game should
                # appear as "running" until a runner marks it done in the app.
                "esi_status": raw.status,
            },
        )

        if not created:
            update_fields = ["esi_status", "date_started"]
            contract.esi_status = raw.status
            prev_started = contract.date_started
            contract.date_started = raw.date_accepted
            # date_completed and date_rejected are app-managed — never overwrite them

            # Backfill issuer_character / issuer_user if missing at import time
            if not contract.issuer_character_id and issuer_char:
                contract.issuer_character = issuer_char
                update_fields.append("issuer_character")
            if not contract.issuer_user_id and issuer_user:
                contract.issuer_user = issuer_user
                update_fields.append("issuer_user")

            contract.save(update_fields=update_fields)

            if not prev_started and contract.date_started:
                from .notifications import notify_runner_contract_started
                notify_runner_contract_started.delay(contract.pk)

            # Resolve accepted_by from ESI acceptor_id if not yet set
            acceptor_id = getattr(raw, "acceptor_id", None)
            if acceptor_id and not contract.accepted_by_id:
                _resolve_accepted_by(contract, acceptor_id)

        if created:
            _fetch_contract_items(owner, contract, token)
            acceptor_id = getattr(raw, "acceptor_id", None)
            if acceptor_id:
                _resolve_accepted_by(contract, acceptor_id)
            if not contract.date_started:
                from .notifications import notify_runners_new_contract
                notify_runners_new_contract.delay(contract.pk)

        updated += 1

    owner.last_updated = now()
    owner.save(update_fields=["last_updated"])
    logger.info("Synced %d item-exchange contracts for corp %d.", updated, corp_id)


_PULLER_ESI_SCOPE = "esi-contracts.read_character_contracts.v1"


@shared_task
def update_contracts_for_puller(user_pk: int):
    from esi.models import Token

    char_ids = list(
        Token.objects.filter(user_id=user_pk, scopes__name=_PULLER_ESI_SCOPE)
        .values_list("character_id", flat=True)
        .distinct()
    )
    for char_id in char_ids:
        update_contracts_for_character.delay(char_id, user_pk)
    logger.info("Queued character contract sync for user %d (%d characters).", user_pk, len(char_ids))


@shared_task
def update_contracts_for_character(character_id: int, user_pk: int):
    from esi.models import Token

    from .models import Contract, OwnerCorporation
    from .providers import esi

    token = (
        Token.objects.filter(
            user_id=user_pk,
            character_id=character_id,
            scopes__name=_PULLER_ESI_SCOPE,
        )
        .require_valid()
        .first()
    )
    if not token:
        logger.warning("No valid puller token for character %d (user %d).", character_id, user_pk)
        return

    owner_map = {
        oc.corporation.corporation_id: oc
        for oc in OwnerCorporation.objects.filter(is_active=True).select_related("corporation")
    }
    if not owner_map:
        logger.warning("No active owner corporations configured.")
        return

    try:
        raw_contracts = esi.client.Contracts.GetCharactersCharacterIdContracts(
            character_id=character_id,
            token=token,
        ).results()
    except HTTPNotModified:
        logger.debug("Character contracts unchanged for character %d (304), skipping.", character_id)
        return
    except Exception:
        logger.exception("ESI fetch failed for character %d.", character_id)
        return

    from .models import CANCELLED_ESI_STATUSES

    issuer_char, issuer_user = _resolve_issuer(character_id)
    updated = 0
    for raw in raw_contracts:
        if raw.type != "item_exchange":
            continue
        owner = owner_map.get(raw.assignee_id)
        if not owner:
            continue

        # ESI-cancelled/deleted/reversed contracts are not tracked — remove if present.
        if raw.status in CANCELLED_ESI_STATUSES:
            deleted, _ = Contract.objects.filter(
                owner_corporation=owner,
                contract_id=raw.contract_id,
            ).delete()
            if deleted:
                logger.info(
                    "Removed ESI-%s contract %d (character %d).",
                    raw.status, raw.contract_id, character_id,
                )
            continue

        contract, created = Contract.objects.get_or_create(
            owner_corporation=owner,
            contract_id=raw.contract_id,
            defaults={
                "issuer_character": issuer_char,
                "issuer_user": issuer_user,
                "title": raw.title or "",
                "price": raw.price or 0,
                "reward": raw.reward or 0,
                "volume": raw.volume or 0,
                "date_issued": raw.date_issued,
                "date_expired": raw.date_expired,
                "date_started": raw.date_accepted,
                # date_completed is app-managed — never import from ESI
                "esi_status": raw.status,
            },
        )

        if not created:
            update_fields = ["esi_status", "date_started"]
            contract.esi_status = raw.status
            prev_started = contract.date_started
            contract.date_started = raw.date_accepted
            # date_completed and date_rejected are app-managed — never overwrite them

            # Backfill issuer_character / issuer_user if missing at import time
            if not contract.issuer_character_id and issuer_char:
                contract.issuer_character = issuer_char
                update_fields.append("issuer_character")
            if not contract.issuer_user_id and issuer_user:
                contract.issuer_user = issuer_user
                update_fields.append("issuer_user")

            contract.save(update_fields=update_fields)

            if not prev_started and contract.date_started:
                from .notifications import notify_runner_contract_started
                notify_runner_contract_started.delay(contract.pk)

            acceptor_id = getattr(raw, "acceptor_id", None)
            if acceptor_id and not contract.accepted_by_id:
                _resolve_accepted_by(contract, acceptor_id)

        if created:
            _fetch_character_contract_items(character_id, contract, token)
            acceptor_id = getattr(raw, "acceptor_id", None)
            if acceptor_id:
                _resolve_accepted_by(contract, acceptor_id)
            if not contract.date_started:
                from .notifications import notify_runners_new_contract
                notify_runners_new_contract.delay(contract.pk)

        updated += 1

    logger.info("Synced %d item-exchange contracts for character %d.", updated, character_id)


def _fetch_character_contract_items(character_id: int, contract, token):
    from .models import ContractItem
    from .providers import esi

    try:
        items = esi.client.Contracts.GetCharactersCharacterIdContractsContractIdItems(
            character_id=character_id,
            contract_id=contract.contract_id,
            token=token,
        ).results()
    except Exception:
        logger.exception("Failed to fetch items for character contract %d.", contract.contract_id)
        return

    objs = [
        ContractItem(
            contract=contract,
            type_id=item.type_id,
            quantity=item.quantity if item.quantity is not None else 1,
            is_included=item.is_included if item.is_included is not None else True,
            is_singleton=item.is_singleton if item.is_singleton is not None else False,
        )
        for item in items
    ]
    ContractItem.objects.bulk_create(objs, ignore_conflicts=True)


@shared_task
def resolve_contract_issuers():
    from allianceauth.eveonline.models import EveCharacter

    from .models import Contract

    unresolved = Contract.objects.filter(issuer_user__isnull=True).exclude(
        issuer_character__isnull=True
    )

    resolved = 0
    for contract in unresolved.select_related("issuer_character"):
        try:
            char = EveCharacter.objects.get(
                character_id=contract.issuer_character.character_id
            )
            if char.userprofile:
                contract.issuer_user = char.userprofile.user
                contract.save(update_fields=["issuer_user"])
                resolved += 1
        except (EveCharacter.DoesNotExist, AttributeError):
            pass

    logger.info("Resolved issuers for %d contracts.", resolved)


@shared_task
def resolve_contract_acceptors():
    from allianceauth.eveonline.models import EveCharacter

    from .models import Contract

    # Back-fill accepted_by on contracts that have date_started but no accepted_by
    unresolved = Contract.objects.filter(
        date_started__isnull=False,
        accepted_by__isnull=True,
    )

    resolved = 0
    for contract in unresolved:
        # No ESI acceptor_id stored — skip; will be resolved on next sync
        pass

    logger.info("Resolved acceptors for %d contracts.", resolved)


def _resolve_character(character_id: int):
    from allianceauth.eveonline.models import EveCharacter

    try:
        return EveCharacter.objects.get(character_id=character_id)
    except EveCharacter.DoesNotExist:
        pass

    # Character not in AA yet — fetch it from ESI and create the record.
    try:
        return EveCharacter.objects.create_character(character_id)
    except Exception:
        logger.warning("Could not create EveCharacter for id=%d.", character_id)
        return None


def _resolve_issuer(character_id: int):
    """Return (EveCharacter, User) for the given ESI character id in one step.

    Creates the EveCharacter from ESI if it isn't in AA yet, then immediately
    looks up the linked AA user so callers never need a separate resolve task.
    Returns (None, None) when the character cannot be resolved at all.
    """
    char = _resolve_character(character_id)
    if char is None:
        return None, None
    user = None
    try:
        user = char.userprofile.user
    except Exception:
        pass
    return char, user


def _resolve_accepted_by(contract, acceptor_id: int):
    from allianceauth.eveonline.models import EveCharacter

    try:
        char = EveCharacter.objects.get(character_id=acceptor_id)
        if char.userprofile:
            contract.accepted_by = char.userprofile.user
            contract.save(update_fields=["accepted_by"])
    except (EveCharacter.DoesNotExist, AttributeError):
        pass


def _fetch_contract_items(owner, contract, token):
    from .models import ContractItem
    from .providers import esi

    corp_id = owner.corporation.corporation_id
    try:
        items = esi.client.Contracts.GetCorporationsCorporationIdContractsContractIdItems(
            corporation_id=corp_id,
            contract_id=contract.contract_id,
            token=token,
        ).results()
    except Exception:
        logger.exception(
            "Failed to fetch items for contract %d.", contract.contract_id
        )
        return

    objs = [
        ContractItem(
            contract=contract,
            type_id=item.type_id,
            quantity=item.quantity if item.quantity is not None else 1,
            is_included=item.is_included if item.is_included is not None else True,
            is_singleton=item.is_singleton if item.is_singleton is not None else False,
        )
        for item in items
    ]
    ContractItem.objects.bulk_create(objs, ignore_conflicts=True)
