# aa-burnneweden

Alliance Auth plugin for managing EVE Online corporation burner contracts.

## Features

- ESI auto-sync of corporation item-exchange contracts
- Role-based access: Pullers, Runners, Staff, Admin
- Staff can reject, reassign, cancel, or complete any contract
- Runners claim open contracts and mark them complete/cancelled
- Pullers see only their own submitted contracts

## Celery Tasks

These tasks run via Celery and should be scheduled with Celery beat (or `django-celery-beat`).

| Task | Recommended interval | Description |
|---|---|---|
| `update_all_contracts` | Every 15–30 min | Queues an ESI sync for each active owner corporation. ESI caches contract data for ~15 min, so polling faster than that has no effect. |
| `update_contracts_for_corporation` | — (called by above) | Fetches item-exchange contracts from ESI for a single corporation and upserts them into the database. Also fetches contract items for newly created contracts. |
| `resolve_contract_issuers` | Every 30–60 min | Links contract issuers to their Alliance Auth user accounts. Runs against contracts where the issuer was not yet registered in AA at import time. |

## Installation

1. `pip install git+ssh://git@github.com/MrAkaki/aa-burnneweden.git@main`
2. Add `aa_burnneweden` to `INSTALLED_APPS`
3. Run `python manage.py migrate`
4. Add the required permissions to your AA groups
5. Configure a corporation via the Admin panel
