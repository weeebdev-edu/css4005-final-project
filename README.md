# campus-app — final project template

> **CSS4005 Cloud Infrastructure Construction — Final Project template (Narxoz University).** Click **“Use this template”** to create your own public repo.
> Assignment: [final-project.pdf](https://weeebdev-edu.github.io/css4005/pdfs/final-project.pdf) · Rubric: [final-project-rubric.pdf](https://weeebdev-edu.github.io/css4005/pdfs/final-project-rubric.pdf) · Report template: [final-project-report-template.pdf](https://weeebdev-edu.github.io/css4005/pdfs/final-project-report-template.pdf) · Free tier guide: [free-tier-guide.pdf](https://weeebdev-edu.github.io/css4005/pdfs/free-tier-guide.pdf)


A small, production-shaped web service that you **deploy and operate** for your
final project. The app is done for you, already observable and configurable.
Your job is everything around it: infrastructure, containers, orchestration,
CI/CD, secrets, monitoring, logging, security and the database.

Click **Use this template** to create your own repository (public, so it works
as a portfolio). Read your course's final-project assignment for the exact
requirements and your personal variant.

## What the app does

- Stores **items** (title, description) in a relational database:
  **PostgreSQL** or **MySQL**.
- Stores **attachments** in object storage: a local folder, **Amazon S3** or
  **Google Cloud Storage**.
- Optionally records every write as an event in **ClickHouse** (analytics).
- Exposes **health checks**, **Prometheus metrics** and **JSON logs**.
- Has a **password policy checker** you can use in your security checks.

## Run it locally (5 minutes)

You need Docker with Compose.

```bash
cp .env.example .env            # edit the values; never commit .env
docker compose up --build       # app + PostgreSQL
curl localhost:8000/readyz      # {"ready":true,...}
curl -X POST localhost:8000/api/items -H 'content-type: application/json' -d '{"title":"hello"}'
```

Other local setups:

```bash
# MySQL instead of PostgreSQL: switch DB_URL in .env to the mysql line, then
docker compose --profile mysql up --build
# ClickHouse analytics: uncomment CLICKHOUSE_URL in .env, then
docker compose --profile clickhouse up --build
# Prometheus (:9090) + Grafana (:3000, admin / GRAFANA_ADMIN_PASSWORD) with a ready dashboard
docker compose --profile monitoring up --build
# Port already taken on your machine? APP_PORT=8080 GRAFANA_PORT=3300 docker compose ...
```

Run the tests and the linter without Docker:

```bash
make venv && make test && make lint
```

## Configuration (environment variables)

Every setting is an environment variable. **Any secret can instead be read from
a file**: set `NAME_FILE=/path/to/file` (this is how Kubernetes and Docker
secrets are mounted).

| Variable | Required | Example / default | Meaning |
|---|---|---|---|
| `SECRET_KEY` | **yes** | 48 random chars | App secret. The app refuses to start if it's missing or shorter than 32 characters. |
| `DB_URL` | **yes** | `postgresql+psycopg://app_rw:${DB_PASSWORD}@db:5432/campus` | Database. Use `mysql+pymysql://...` for MySQL. |
| `DB_PASSWORD` | if `DB_URL` has `${DB_PASSWORD}` | from your secret manager | Filled into `DB_URL` and URL-encoded by the app. |
| `CLICKHOUSE_URL` | no | `clickhouse://analytics:PW@clickhouse:8123/campus` | Enables the ClickHouse events table. |
| `STORAGE_BACKEND` | no | `local` · `s3` · `gcs` | Where attachments go. |
| `BUCKET` | for s3/gcs | `ivanov-230103-files` | Bucket name (or a folder for `local`). |
| `APP_NAME` | no | `campus-app` | Shown on the home page. |
| `APP_OWNER` | no | `Ivanov Ivan (230103001)` | **Put your name and ID here.** Shown on `/` and `/info`. |
| `APP_VERSION`, `GIT_SHA` | no | set by your CI | Shown on `/info`; useful to prove which release is running. |
| `LOG_LEVEL`, `LOG_FORMAT` | no | `INFO`, `json` | Logging. Keep JSON in production. |
| `PASSWORD_MIN_LENGTH` | no | `12` | Used by the password checker. |

Cloud credentials are **not** configured here. boto3 (AWS) and
google-cloud-storage (GCP) use their default credential chains: an instance
role or service account in the cloud, `AWS_ENDPOINT_URL` for local emulators.
Never put access keys in the image, the repo or `.env` files you commit.

## Endpoints

| Method & path | What it does |
|---|---|
| `GET /` | HTML page with app name, owner, version and the host that served it |
| `GET /info` | JSON: version, git sha, hostname, db engine, storage backend |
| `GET /healthz` | Liveness: the process is up (no dependencies checked) |
| `GET /readyz` | Readiness: database and storage reachable, else **503** |
| `GET /metrics` | Prometheus: `http_requests_total`, `http_request_duration_seconds`, `items_total`, `db_up` |
| `GET/POST /api/items` | List (with `limit`, `offset`) / create items |
| `GET/PUT/DELETE /api/items/{id}` | Read / update / delete one item |
| `POST/GET /api/items/{id}/attachment` | Upload / download a file (multipart field `file`, max 10 MB) |
| `POST /api/admin/check-password` | `{"password": "..."}` → which policy rules pass |

Interactive API docs: `http://localhost:8000/docs`.

## What's in the repo

```
app/                 the service (FastAPI, SQLAlchemy, prometheus-client)
app/sql/             EXAMPLE least-privilege roles for PostgreSQL / MySQL, ClickHouse DDL
tests/               pytest suite (uses SQLite, no services needed)
Dockerfile           multi-stage, non-root, with HEALTHCHECK
compose.yaml         LOCAL development only
deploy/local/        Prometheus + Grafana config for the local monitoring profile
.github/workflows/   ci.yml: lint + tests only
```

## What is deliberately left for you

The template stops at "runs on my laptop". Your project adds, depending on your
course and variant:

- **Infrastructure as code** (Terraform) for your cloud: AWS **or** GCP.
- **Networking**: your own VPC, subnets and firewall rules; the database is
  never reachable from the internet.
- **Orchestration**: Kubernetes manifests or a Helm chart (Deployment,
  Service, Ingress, probes using `/healthz` and `/readyz`, resource limits,
  autoscaling), or the platform your variant requires.
- **Database**: your own PostgreSQL / MySQL (and ClickHouse if your variant
  has it) with separate roles (`admin`, `app_rw`, `app_ro`), a password policy
  and backups. Start from `app/sql/`, then harden it.
- **Secrets**: a cloud secret manager (AWS Secrets Manager / SSM Parameter
  Store, or GCP Secret Manager), delivered to the app as env vars or files.
- **CI/CD**: extend `ci.yml` with image build, security checks (secret scan,
  image scan, dependency audit, password policy), push to a registry, deploy
  and rollback.
- **Monitoring and logging**: scrape `/metrics`, dashboards, alert rules,
  central collection of the JSON logs.

Keep the app code mostly as it is: you're graded on how you build, ship, secure
and run it, not on new features.
