# API Testing Guide

This guide tests the v1 API locally after the Docker Compose stack is running.

## 1. Prerequisites

Start the application from the repository root:

```bash
docker compose up --build -d
docker compose ps
```

The `api`, `worker`, `postgres`, and `rabbitmq` services should be running. The `database-init` service should show `Exited (0)` because it is a one-time initialization task.

Base URL:

```text
http://localhost:8000
```

The commands below use Bash-compatible `curl`. They also work in Git Bash on Windows.

## 2. Health check

```bash
curl -i http://localhost:8000/healthz
```

Expected:

- HTTP `200 OK`
- `status` is `healthy`
- `postgresql` is `up`
- `rabbitmq` is `up`

## 3. Successful synchronous request

```bash
curl -i -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 4000,
    "preferences": ["nature", "museum"]
  }'
```

Expected:

- HTTP `200 OK`
- `mode` is `sync`
- `status` is `succeeded`
- `callback_status` is `not_applicable`
- The response contains up to three plan stops

Save the returned `id` for the request lookup tests.

## 4. Successful asynchronous request and callback

The following test uses `httpbin.org`, which accepts the callback POST and returns a successful response. It requires internet access.

```bash
curl -i -X POST http://localhost:8000/async \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 4000,
    "preferences": ["nature", "museum"],
    "callback_url": "https://httpbin.org/post"
  }'
```

Expected immediate response:

- HTTP `202 Accepted`
- `status` is `pending`
- Response contains `id` and `status_url`

Poll the returned status URL, replacing the placeholder:

```bash
curl -i http://localhost:8000/requests/REPLACE_WITH_REQUEST_ID
```

Expected final state:

- `status` becomes `succeeded`
- `callback_status` becomes `delivered`
- The response contains the generated plan

## 5. Callback retry and dead-letter handling

Start the local callback receiver. Its `/callback/fail` endpoint always returns
`503`, which is a retryable callback failure:

```bash
docker compose --profile load-test up -d callback-receiver
```

Submit an asynchronous request using that endpoint:

```bash
curl -i -X POST http://localhost:8000/async \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 4000,
    "preferences": ["nature"],
    "callback_url": "http://callback-receiver:9000/callback/fail"
  }'
```

Poll the returned request ID:

```bash
curl http://localhost:8000/requests/REPLACE_WITH_REQUEST_ID
```

The first delivery happens immediately. The service then retries after 5, 30,
and 120 seconds. Poll for approximately three minutes. Expected final state:

- Planning remains `succeeded`
- Four callback attempts have been made
- `callback_status` becomes `dead_lettered`
- The final message is stored in `callback.dlq`
- Planning success and callback delivery success remain separate states

Transient network failures and HTTP `408`, `429`, and `5xx` responses are
retried. Other `4xx` responses are permanent failures and are not retried.

Inspect the persisted attempts:

```bash
docker compose exec postgres psql -U outing_app -d outing_planner -c \
  "SELECT request_id, attempt_number, outcome, http_status, started_at, next_retry_at FROM callback_attempts WHERE request_id = 'REPLACE_WITH_REQUEST_ID' ORDER BY attempt_number;"
```

## 6. No plan because the budget is too low

```bash
curl -i -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 10,
    "preferences": ["nature"]
  }'
```

Expected:

- HTTP `400 Bad Request`
- `status` is `failed`
- `failed_constraint` is `budget`
- The failure is persisted and can be queried by request ID

## 7. Group size above the API limit

The API permits a group of up to 100. This request exceeds that boundary:

```bash
curl -i -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 101,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 10000,
    "preferences": ["nature"]
  }'
```

Expected:

- HTTP `400 Bad Request`
- Validation reports that `group_size` must be at most 100
- No request is created

## 8. Invalid age range

```bash
curl -i -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 40,
    "age_max": 20,
    "budget_inr": 4000,
    "preferences": ["nature"]
  }'
```

Expected:

- HTTP `400 Bad Request`
- Validation explains that `age_min` must be less than or equal to `age_max`
- No request is created

## 9. Duplicate preferences

```bash
curl -i -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 4000,
    "preferences": ["nature", "nature"]
  }'
```

Expected:

- HTTP `400 Bad Request`
- Validation reports that preference tags must be unique

## 10. Invalid callback URL

```bash
curl -i -X POST http://localhost:8000/async \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 4000,
    "preferences": ["nature"],
    "callback_url": "http://localhost:9000/callback"
  }'
```

Expected:

- Request is rejected because production callback validation requires a safe HTTPS destination
- No async planning job is created

## 11. Unknown fields

```bash
curl -i -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "budget_inr": 4000,
    "preferences": [],
    "unexpected_field": true
  }'
```

Expected:

- HTTP `400 Bad Request`
- The additional field is rejected

## 12. Missing required field

This request omits `budget_inr`:

```bash
curl -i -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Central Bengaluru",
    "outing_date": "2026-10-10",
    "group_size": 4,
    "age_min": 20,
    "age_max": 35,
    "preferences": []
  }'
```

Expected HTTP status: `400 Bad Request`.

## 13. Get a request by ID

```bash
curl -i http://localhost:8000/requests/REPLACE_WITH_REQUEST_ID
```

Expected HTTP status: `200 OK`.

### Unknown request ID

```bash
curl -i http://localhost:8000/requests/00000000-0000-0000-0000-000000000000
```

Expected HTTP status: `404 Not Found`.

### Malformed request ID

```bash
curl -i http://localhost:8000/requests/not-a-uuid
```

Expected HTTP status: `400 Bad Request`.

## 14. List requests

### List synchronous requests

```bash
curl -i "http://localhost:8000/requests?mode=sync&limit=20"
```

### List asynchronous requests

```bash
curl -i "http://localhost:8000/requests?mode=async&limit=20"
```

Expected:

- HTTP `200 OK`
- `items` contains only the requested mode
- Results are ordered newest first

### Invalid mode

```bash
curl -i "http://localhost:8000/requests?mode=invalid&limit=20"
```

Expected HTTP status: `400 Bad Request`.

### Invalid limit

```bash
curl -i "http://localhost:8000/requests?mode=sync&limit=101"
```

Expected HTTP status: `400 Bad Request`.

## 15. Pagination

Create several requests, then request a small page:

```bash
curl "http://localhost:8000/requests?mode=sync&limit=2"
```

Copy the returned `next_cursor` and pass it without modifying it:

```bash
curl --get http://localhost:8000/requests \
  --data-urlencode "mode=sync" \
  --data-urlencode "limit=2" \
  --data-urlencode "cursor=REPLACE_WITH_NEXT_CURSOR"
```

Expected:

- The second page does not repeat records from the first page
- `next_cursor` becomes `null` after the final page

## 16. Persistence after restart

First create a request and save its ID. Restart the API and worker:

```bash
docker compose restart api worker
```

Wait for the health endpoint, then query the saved ID:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/requests/REPLACE_WITH_REQUEST_ID
```

Expected: the request and its result are still present because PostgreSQL uses a named Docker volume.

## 17. Inspect RabbitMQ

RabbitMQ management UI:

```text
http://localhost:15672
```

Local credentials:

```text
Username: outing_app
Password: local_dev_password
```

Queue state can also be checked from the terminal:

```bash
docker compose exec rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers
```

Expected queues include:

- `planner.jobs`
- `callback.jobs`
- `callback.retry.5s`
- `callback.retry.30s`
- `callback.retry.120s`
- `planner.dlq`
- `callback.dlq`

## 18. Inspect PostgreSQL records

```bash
docker compose exec postgres psql -U outing_app -d outing_planner -c \
  "SELECT id, mode, status, callback_status, created_at FROM requests ORDER BY created_at DESC;"
```

Check seeded venues:

```bash
docker compose exec postgres psql -U outing_app -d outing_planner -c \
  "SELECT name, area, estimated_cost_inr FROM venues ORDER BY name;"
```

## 19. Check logs

```bash
docker compose logs --tail 100 api worker
```

Follow logs while submitting requests:

```bash
docker compose logs -f api worker
```

Unexpected tracebacks, unhandled exceptions, or repeated container restarts indicate a failed test.

## 20. Stop or reset the environment

Stop the stack while retaining PostgreSQL and RabbitMQ data:

```bash
docker compose down
```

Delete all local data and rebuild from the fixed seed file:

```bash
docker compose down -v
docker compose up --build -d
```

Use the reset operation only when previous request history is no longer needed.
