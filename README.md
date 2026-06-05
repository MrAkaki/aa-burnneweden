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

### Scheduled tasks

| Task | Recommended interval | Description |
|---|---|---|
| `update_all_contracts` | Every 15–30 min | Queues an ESI sync for each active owner corporation. ESI caches contract data for ~15 min, so polling faster than that has no effect. |
| `resolve_contract_issuers` | Every 30–60 min | Back-fills `issuer_user` for contracts imported before the issuer was linked in Alliance Auth. |

### Internal tasks (do not schedule directly)

| Task | Trigger | Description |
|---|---|---|
| `update_contracts_for_corporation` | Called by `update_all_contracts` | Fetches corporation item-exchange contracts, upserts contract rows, and fetches items for newly created contracts. |
| `update_contracts_for_character` | Called by `update_contracts_for_puller` | Fetches character contracts for one puller character and imports contracts assigned to configured owner corporations. |

### User-triggered tasks

| Task | Trigger | Description |
|---|---|---|
| `update_contracts_for_puller` | Puller sync action in UI | Queues per-character sync tasks for a user based on their linked puller tokens. |

### Optional utility task

| Task | Recommended interval | Description |
|---|---|---|
| `resolve_contract_acceptors` | Optional / on-demand | Placeholder task for accepted-by backfill; currently logs only and does not modify records. |

## Installation

1. `pip install git+https://github.com/MrAkaki/aa-burnneweden.git@main`
2. Add `aa_burnneweden` to `INSTALLED_APPS`
3. Run `python manage.py migrate`
4. Add the required permissions to your AA groups
5. Configure a corporation via the Admin panel

## Optional: Discord Direct Messages

If you want to send Discord direct messages to users, install and configure
`allianceauth-discordbot`.

- App page: https://apps.allianceauth.org/apps/detail/allianceauth-discordbot
- This integration is optional and not required for core `aa-burnneweden` features.

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
