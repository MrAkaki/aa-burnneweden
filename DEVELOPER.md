# Developer Guide

Local development uses a stripped-down Alliance Auth stack in `aa-testsite/` — SQLite instead of MariaDB, WhiteNoise for static files, no Nginx, no Grafana. The `aa-burnneweden` plugin is mounted from the repo root and installed as an editable package so code changes are picked up without rebuilding.

## Prerequisites

- Docker with Compose v2 (`docker compose` not `docker-compose`)
- An EVE Online developer app — register at https://developers.eveonline.com
  - Callback URL: `http://localhost:8000/sso/callback`

---

## First-time setup

```bash
# 1. Fill in your EVE SSO credentials
#    Edit aa-testsite/.env and set ESI_SSO_CLIENT_ID and ESI_SSO_CLIENT_SECRET

# 2. Fix permissions on the SQLite data directory
chmod 777 aa-testsite/data/sqlite

# 3. Build the image (only needed once, or after Dockerfile changes)
docker compose -f aa-testsite/docker-compose.yml build

# 4. Start everything
docker compose -f aa-testsite/docker-compose.yml up -d

# 5. Create your admin user
docker exec -it allianceauth_gunicorn python manage.py createsuperuser
```

The site will be at http://localhost:8000 — log in via Django admin at http://localhost:8000/admin/

---

## Common Docker commands

```bash
# Start all services
docker compose -f aa-testsite/docker-compose.yml up -d

# Stop all services
docker compose -f aa-testsite/docker-compose.yml down

# Restart a single service
docker compose -f aa-testsite/docker-compose.yml restart allianceauth_gunicorn

# View logs (all services)
docker compose -f aa-testsite/docker-compose.yml logs -f

# View logs for one service
docker compose -f aa-testsite/docker-compose.yml logs -f allianceauth_gunicorn

# Run a Django management command
docker exec -it allianceauth_gunicorn python manage.py <command>

# Open a shell inside the container
docker exec -it allianceauth_gunicorn bash
```

---

## Working on aa-burnneweden

The plugin source (`aa_burnneweden/`) is mounted into the containers at `/app/aa-burnneweden` and installed as an editable package (`pip install -e`) on every startup. You do **not** need to rebuild the image when editing Python files.

### After changing Python code

Gunicorn runs a single worker — restart it to pick up changes:

```bash
docker compose -f aa-testsite/docker-compose.yml restart allianceauth_gunicorn
```

Celery workers need a restart too if you changed task code:

```bash
docker compose -f aa-testsite/docker-compose.yml restart allianceauth_worker allianceauth_beat
```

### After adding a new migration

```bash
# Generate the migration file locally (or inside the container)
docker exec -it allianceauth_gunicorn python manage.py makemigrations aa_burnneweden

# Apply it
docker exec -it allianceauth_gunicorn python manage.py migrate
```

### After changing static files (CSS/JS/images)

```bash
docker exec -it allianceauth_gunicorn python manage.py collectstatic --noinput
```

### After changing `pyproject.toml` dependencies

The editable install is re-run on container startup, but new dependencies aren't automatically installed. Rebuild the image:

```bash
docker compose -f aa-testsite/docker-compose.yml build
docker compose -f aa-testsite/docker-compose.yml up -d
```

---

## Enabling optional AA apps

Edit `aa-testsite/conf/local.py` and uncomment entries in `INSTALLED_APPS`, then run migrations:

```bash
docker exec -it allianceauth_gunicorn python manage.py migrate
docker compose -f aa-testsite/docker-compose.yml restart allianceauth_gunicorn
```

---

## Resetting the database

```bash
docker compose -f aa-testsite/docker-compose.yml down
rm aa-testsite/data/sqlite/aa.sqlite3
docker compose -f aa-testsite/docker-compose.yml up -d
# Re-create your superuser afterwards
docker exec -it allianceauth_gunicorn python manage.py createsuperuser
```
