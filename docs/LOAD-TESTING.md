# Load Testing Guide

The load generator is kept in this repository but runs separately from the application. It does not consume API or worker resources and is started only through the `load-test` Docker Compose profile.

## Components

- `load-generator` sends concurrent requests to `/sync`, `/async`, or both.
- `callback-receiver` behaves as the external callback consumer for async tests.
- Reports are printed to the console and saved as JSON under `load-results/`.

For `both` mode, `--requests` is the number sent to each endpoint. For example, `--requests 100` sends 100 sync and 100 async requests.

## Start the application

```bash
docker compose up --build -d
```

## Smoke test

```bash
docker compose --profile load-test run --rm load-generator \
  --mode both \
  --requests 10 \
  --concurrency 2 \
  --callback-timeout 30
```

## Sync load test

```bash
docker compose --profile load-test run --rm load-generator \
  --mode sync \
  --requests 500 \
  --concurrency 20
```

The sync summary includes:

- Total requests sent
- Successful and failed requests
- Overall test duration and throughput
- Successful-request latency p50, p95, and p99

## Async load test

```bash
docker compose --profile load-test run --rm load-generator \
  --mode async \
  --requests 500 \
  --concurrency 20 \
  --callback-timeout 60
```

The async summary includes:

- Total requests sent
- Successful and failed requests
- Accepted and rejected submissions
- Callbacks received and missing
- Successful and failed planning results
- Acknowledgement latency p50, p95, and p99
- Time-to-callback p50, p95, and p99

Time-to-callback is measured from the start of the `/async` submission until the callback receiver accepts the correlated callback. Durations use timestamps from containers on the same Docker host.

## Recommended profiles

| Profile | Requests per mode | Concurrency | Purpose |
|---|---:|---:|---|
| Smoke | 10 | 2 | Verify correctness |
| Normal | 500 | 20 | Establish normal behavior |
| High load | 2,000 | 50 | Compare sync and async behavior |
| Stress | 5,000 | 100 | Observe saturation and rejection |

Increase load gradually. Very high concurrency can be limited by the local computer rather than the application.

## JSON report

The default report is written to:

```text
load-results/load-test-result.json
```

Use a different filename to keep multiple runs:

```bash
docker compose --profile load-test run --rm load-generator \
  --mode both \
  --requests 1000 \
  --concurrency 50 \
  --output /results/load-test-1000.json
```

Generated JSON reports are ignored by Git. The `load-results` directory itself remains in the repository.

## Stop the test receiver

The one-off generator container removes itself after completion. Stop the callback receiver with:

```bash
docker compose --profile load-test stop callback-receiver
```
