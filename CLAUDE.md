# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`aa-burnneweden` is a Django plugin for [Alliance Auth](https://allianceauth.readthedocs.io/) that manages EVE Online corporation burner contracts. It is packaged with [Flit](https://flit.pypa.io/).

**All plugin source code lives in `aa_burnneweden/`.** This is the only directory that gets shipped. `aa-testsite/` is the local test suite — a throwaway Docker Alliance Auth stack used to run and exercise the plugin. Never put plugin logic or migrations in `aa-testsite/`.

## Development Commands

`aa-testsite/` mounts the repo root into the container at `/app/aa-burnneweden` and runs `pip install -e` on startup, so edits to `aa_burnneweden/` are picked up after a service restart — no image rebuild needed. The compose file is at `aa-testsite/docker-compose.yml`.

```bash
# Start all services
docker compose -f aa-testsite/docker-compose.yml up -d

# Stop all services
docker compose -f aa-testsite/docker-compose.yml down

# Restart web server after Python changes
docker compose -f aa-testsite/docker-compose.yml restart allianceauth_gunicorn

# Restart workers after task code changes
docker compose -f aa-testsite/docker-compose.yml restart allianceauth_worker allianceauth_beat

# Run a Django management command
docker exec -it allianceauth_gunicorn python manage.py <command>

# Generate and apply migrations
docker exec -it allianceauth_gunicorn python manage.py makemigrations aa_burnneweden
docker exec -it allianceauth_gunicorn python manage.py migrate

# Collect static files
docker exec -it allianceauth_gunicorn python manage.py collectstatic --noinput

# View logs
docker compose -f aa-testsite/docker-compose.yml logs -f allianceauth_gunicorn
```

### Pre-PR sanity check (runs locally, no Docker needed)

```bash
python -m compileall -q aa_burnneweden
python -c "import aa_burnneweden"
```

### Rebuilding the image (required after `pyproject.toml` dependency changes)

```bash
docker compose -f aa-testsite/docker-compose.yml build
docker compose -f aa-testsite/docker-compose.yml up -d
```

## Architecture

### Plugin structure

The shipped package is `aa_burnneweden/` only. Files to modify when working on the plugin:

| File | Purpose |
|---|---|
| `models.py` | Data model: `OwnerCorporation`, `Contract`, `ContractItem`, `DiscordNotificationPreference` |
| `managers.py` | `ContractManager` / `ContractQuerySet` — all queryset filters live here |
| `views.py` | All HTTP views, permission checks, and action handlers |
| `tasks.py` | Celery tasks for ESI sync |
| `notifications.py` | Celery tasks for Discord DMs (optional dependency) |
| `urls.py` | URL routing under the `aa_burnneweden` namespace |
| `admin.py` | Django admin registration |
| `auth_hooks.py` | Alliance Auth menu/hook registration |
| `apps.py` | AppConfig |
| `providers.py` | ESI client singleton |
| `signals.py` | Django signal handlers |
| `migrations/` | Schema migrations — generate with `makemigrations aa_burnneweden` |
| `templates/aa_burnneweden/` | HTML templates |

### Data model

- **`OwnerCorporation`** — a corporation whose ESI token is used to pull contracts. Configured via the Admin panel using a character's ESI token.
- **`Contract`** — a single item-exchange contract. Status is a **computed property** (not a stored field) derived from `date_rejected`, `date_completed`, `esi_status`, and `date_started` in that priority order.
- **`ContractItem`** — individual items in a contract (included or requested).
- **`DiscordNotificationPreference`** — per-user opt-in settings for Discord DM notifications.

**Critical invariant:** `date_completed` and `date_rejected` are app-managed fields. They are **never imported from ESI** and must never be overwritten by sync tasks. Contracts completed in-game appear as "running" in the app until a runner explicitly marks them done.

**ESI-cancelled contracts** (`esi_status` in `cancelled`, `deleted`, `reversed`) are **deleted** from the local database rather than kept with a cancelled status.

### `ContractManager` / `ContractQuerySet`

`managers.py` provides a custom queryset with named filters: `.open()`, `.accepted()`, `.completed()`, `.rejected()`, `.cancelled()`, `.active()`, `.for_puller(user)`, `.for_runner(user)`, `.with_status(value)`. Always use these instead of raw field filters.

### Permissions (role model)

Four permissions on `Contract.Meta`:

| Permission | Role |
|---|---|
| `basic_access` | Required to access the app at all |
| `puller_access` | Can view own submitted contracts and sync via ESI |
| `runner_access` | Can view open contracts and accept/complete/reject them |
| `staff_access` | Can manage all contracts (reassign, cancel, reject any) |
| `admin_access` | Full access including corporation configuration |

Staff and admin implicitly get puller and runner capabilities in the views.


### Discord notifications (optional)

All notification tasks in `notifications.py` are no-ops when `aadiscordbot` is not installed. They check `apps.is_installed("aadiscordbot")` at the top of each task. The `discord` package (from `aadiscordbot`) provides `Embed` and `Color` — these imports are inside the task bodies to avoid hard dependency errors.

### ESI integration

Uses `django-esi` (`esi.client`, `Token`). Corporation sync requires the `esi-contracts.read_corporation_contracts.v1` scope; puller sync requires `esi-contracts.read_character_contracts.v1`. `HTTPNotModified` (304) is handled gracefully by skipping the sync.

## Workflow

- All changes go through pull requests; no direct pushes to `main`.
- At least one approval from a code owner is required before merging.
- Do not add agent-specific config files, prompts, or metadata to the repository.
