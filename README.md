# aa-burnneweden

Alliance Auth plugin for managing EVE Online corporation burner contracts.

## Features

- ESI auto-sync of corporation item-exchange contracts
- Role-based access: Pullers, Runners, Staff, Admin
- Contract lifecycle: open → running → completed / rejected / cancelled
- Runners claim open contracts and mark them complete or cancelled
- Pullers see only their own submitted contracts and can trigger per-character ESI sync
- Staff can reject, reassign, force-cancel, or bulk-action any contract
- Bulk complete / reject / cancel for multiple contracts at once
- Statistics dashboard (open, running, completions by day/week/month)
- Optional Discord DM notifications with per-user, per-event opt-in

## Celery Tasks

These tasks run via Celery and should be scheduled with Celery beat (or `django-celery-beat`).

### Scheduled tasks

| Task | Recommended interval | Description |
|---|---|---|
| `sync_contracts` | Every 15–30 min | Syncs all active owner corporations: upserts contracts, handles ESI-cancelled/expired/rejected statuses, resolves issuers and acceptors. ESI caches contract data for ~15 min so polling faster has no effect. |
| `notify_pullers_open_contracts` | Every 15–30 min | Sends Discord DMs to opted-in pullers about new open contracts that have not yet been announced. No-op when `aadiscordbot` is not installed. |

### User-triggered tasks

| Task | Trigger | Description |
|---|---|---|
| `update_contracts_for_puller` | Puller sync button in UI | Queues per-character sync tasks for the current user based on their linked puller ESI tokens. |

### Internal tasks (do not schedule directly)

| Task | Trigger | Description |
|---|---|---|
| `update_contracts_for_character` | Called by `update_contracts_for_puller` | Fetches character contracts for one puller character and imports those assigned to configured owner corporations. |

## Installation

1. `pip install git+https://github.com/MrAkaki/aa-burnneweden.git@main`
2. Add `aa_burnneweden` to `INSTALLED_APPS`
3. Run `python manage.py migrate`
4. Add the required permissions to your AA groups
5. Configure a corporation via the in-app admin config page (uses SSO — no Django admin panel needed)

### Required ESI scopes

| Scope | Used by |
|---|---|
| `esi-contracts.read_corporation_contracts.v1` | Corporation sync (`sync_contracts`) |
| `esi-contracts.read_character_contracts.v1` | Puller sync (`update_contracts_for_puller`) |

## Optional: Discord Direct Messages

If you want Discord direct messages to users, install and configure `allianceauth-discordbot`.

- App page: https://apps.allianceauth.org/apps/detail/allianceauth-discordbot
- This integration is optional and not required for core `aa-burnneweden` features.
- All notification tasks are no-ops when `aadiscordbot` is not installed.

### Minimum configuration

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS += [
    "allianceauth.services.modules.discord",
    "aadiscordbot",
]
```

Add to your settings (e.g. `local.py`):

```python
DISCORD_GUILD_ID = "your-guild-id"
DISCORD_APP_ID = "your-app-id"
DISCORD_APP_SECRET = "your-app-secret"
DISCORD_BOT_TOKEN = "your-bot-token"
DISCORD_CALLBACK_URL = f"{SITE_URL}/discord/callback/"
```

For the local testsite (`aa-testsite/`), set the above values in `aa-testsite/.env`.

### Discord notification events

Users opt in per-event from the Notifications tab in the app:

| Event | Who receives it |
|---|---|
| New contract available | Runners (opted in) |
| Contract started | The assigned runner |
| Contract rejected | The assigned runner |
| Contract completed | The assigned runner |
| Contract canceled | The assigned runner |
| New open contracts | Pullers (opted in) |

## Collaboration

This repository uses a PR-only workflow.

- Do not push or merge directly to `main`
- All changes must go through a pull request
- Pull requests must have at least 1 approval
- Required review must come from code owners

### Tooling and Agent Policy

Collaborators may use any local tools they prefer (including AI or agentic coding tools) while working.

- The repository and source code remain tool-agnostic
- Do not add agent-specific configs, prompts, instructions, or metadata files to this repo
- Keep contributions focused on application code, tests, docs, and standard project configuration
- Proposed changes are reviewed on code quality and behavior, not on which tool was used

### Branch Protection (GitHub Ruleset)

Configure a branch ruleset targeting `main` with the following settings:

- Require a pull request before merging
- Require approvals (set to 1)
- Require review from Code Owners
- Dismiss stale pull request approvals when new commits are pushed
- Require conversation resolution before merging
- Block force pushes
- Block branch deletion
