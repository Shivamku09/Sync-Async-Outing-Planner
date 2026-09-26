# Sync-Async Outing Planner

A FastAPI outing planner demonstrating synchronous and asynchronous processing of the same deterministic task. Async requests are persisted in PostgreSQL, delivered through RabbitMQ, processed by a worker, and reported to a callback URL.

## Run locally

### Prerequisites

- Git
- Docker Desktop with Docker Compose

No local Python, PostgreSQL, or RabbitMQ installation is required.

```powershell
git clone https://github.com/Shivamku09/Sync-Async-Outing-Planner.git
cd Sync-Async-Outing-Planner
Copy-Item .env.example .env
docker compose up --build
```

After all containers are healthy:

- Swagger UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/healthz>
- RabbitMQ management: <http://localhost:15672>
- RabbitMQ login: `outing_app` / `local_dev_password`

The credentials are intentionally local demo values and must not be reused in a public environment.

## Try the synchronous API

```powershell
$body = @{
  location = "Central Bengaluru"
  outing_date = "2026-10-10"
  group_size = 4
  age_min = 20
  age_max = 35
  budget_inr = 4000
  preferences = @("nature", "museum")
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8000/sync `
  -ContentType "application/json" -Body $body
```

The endpoint performs the planner work inline and returns the completed result.

## Try the asynchronous API

Create a temporary HTTPS callback URL with a request-inspection service such as webhook.site, then use it below:

```powershell
$body = @{
  location = "Central Bengaluru"
  outing_date = "2026-10-10"
  group_size = 4
  age_min = 20
  age_max = 35
  budget_inr = 4000
  preferences = @("nature", "museum")
  callback_url = "https://REPLACE_WITH_YOUR_CALLBACK_URL"
} | ConvertTo-Json

$accepted = Invoke-RestMethod -Method Post -Uri http://localhost:8000/async `
  -ContentType "application/json" -Body $body

Invoke-RestMethod -Uri ("http://localhost:8000" + $accepted.status_url)
```

The async endpoint immediately returns `202 Accepted`. The worker later generates the plan, updates PostgreSQL, and posts the result to the callback URL.

## Containers

| Service | Responsibility |
|---|---|
| `api` | Serves FastAPI sync, async, query, and health endpoints |
| `worker` | Runs outbox publishing, planning, and callback handlers |
| `postgres` | Stores requests, results, callback attempts, and outbox events |
| `rabbitmq` | Delivers planner and callback jobs |
| `database-init` | Creates missing tables and inserts fixed venue records idempotently |

PostgreSQL and RabbitMQ use named Docker volumes. Normal container or machine restarts retain their data.

## Stop or reset

Stop containers while retaining data:

```powershell
docker compose down
```

Delete all local PostgreSQL and RabbitMQ data and start clean:

```powershell
docker compose down -v
docker compose up --build
```

The second command reruns table creation and seed insertion. The initialization is idempotent, so ordinary restarts do not create duplicate venues.

## Design documentation

- [High-level design](docs/HLD.md)
- [Low-level design](docs/LLD.md)
- [Database decision](docs/database-decision.md)
- [RabbitMQ decision](docs/rabbitmq-vs-asyncio-queue.md)
- [API testing guide](docs/API-TESTING.md)
- [Load testing guide](docs/LOAD-TESTING.md)
- [Loom walkthrough presentation](docs/Sync-Async-Outing-Planner-Loom-Walkthrough.pptx)
