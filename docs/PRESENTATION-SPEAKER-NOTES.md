# Presentation Speaker Notes

These notes follow the slide order in `Sync-Async-Outing-Planner-Loom-Walkthrough.pptx`. They are written as a simple speaking guide rather than a script that must be memorized.

## Slide 1 — Sync–Async Outing Planner

“Hi, I am Shivam Kushwaha. This project demonstrates the difference between synchronous and asynchronous API processing using the same outing-planning task. The backend uses FastAPI, PostgreSQL, RabbitMQ, and Docker Compose. I will explain the problem, architecture, implementation, API flow, and measured load-test results.”

## Slide 2 — The problem statement

“The assignment asks us to perform the same work through two different API models. In the synchronous model, the client waits until processing finishes and receives the result in the same response. In the asynchronous model, the client quickly receives a request ID, processing continues in the background, and the final result is sent to a callback URL. The main comparison is behavior, reliability, and performance under load.”

## Slide 3 — The deterministic workload

“I selected a Bangalore outing planner as the common workload. The input contains the location, date, group size, age range, budget, and preferences. The planner applies the same deterministic rules every time and returns up to three suitable venues with the total and remaining budget. Both endpoints use exactly the same planner service, so the comparison remains fair.”

## Slide 4 — High-level architecture

“The client calls FastAPI. PostgreSQL stores requests, results, callback information, and outbox events. RabbitMQ carries planner and callback jobs. The worker runs the outbox publisher, planner handler, and callback handler. For synchronous requests, FastAPI directly calls the planner. For asynchronous requests, the API persists the request and the worker completes it through RabbitMQ. Docker Compose starts the complete environment locally.”

## Slide 5 — How the synchronous endpoint works

“The sync flow is intentionally straightforward. First, the API validates the body. It stores the request with processing status, calls the shared planner once, saves the result, and returns it immediately. It does not use RabbitMQ and does not perform a backend retry. A successful plan returns 200, while invalid input or an impossible plan returns a simple 400 response.”

## Slide 6 — How the asynchronous endpoint works

“For the async flow, the API validates both the planning input and callback URL. It stores the request and an outbox event in one database transaction, then immediately returns 202 with a request ID and status URL. The outbox publisher sends the job to RabbitMQ. The planner worker processes it and stores the result. Finally, the callback worker sends the result to the callback URL. The client can also query the request at any time.”

## Slide 7 — Persistence and reliability

“PostgreSQL is the source of truth, while RabbitMQ transports background work. The transactional outbox prevents a request from being saved without its corresponding queue event. RabbitMQ queues and messages are durable. Request claims use leases so duplicate processing is avoided. Callback attempts are stored with their duration, HTTP status, and outcome. Docker volumes preserve PostgreSQL and RabbitMQ data across normal restarts.”

## Slide 8 — Callback safety and failure handling

“Callback URLs must be treated as untrusted input. Public callbacks require HTTPS. URLs containing credentials are rejected, private addresses are blocked, redirects are disabled, and response size and timeouts are limited. If the callback URL is unavailable, the planning result remains saved and available through the status API. The callback attempt and failure state are also stored separately for tracking.”

## Slide 9 — How the evaluation concerns are addressed

“There are four important concerns. First, callback failures cannot remove the completed planning result; the failure is timed and recorded. Second, RabbitMQ preserves dispatch order, while independent requests may complete in a different order because workers run concurrently. Third, the queue, worker prefetch, connection pools, and backlog limit protect the application during bursts. Fourth, callback validation, HTTPS, network checks, timeouts, redirect blocking, and size limits reduce callback abuse.”

## Slide 10 — My contribution

“My contribution includes the HLD and LLD, the API contracts, shared planner implementation, PostgreSQL repositories and seed data, RabbitMQ integration, transactional outbox, dependency-injection container, service and repository interfaces, callback security, Docker setup, testing documents, and the load generator. I also ran the complete system locally and verified sync, async, callback, persistence, and load-test behavior.”

## Slide 11 — API examples for the demo

“These are the two main API requests. The sync request contains the planning fields and immediately returns the completed request resource. The async request contains the same fields plus a callback URL and immediately returns 202. I can then use the returned request ID with GET requests slash ID to check the final state. The same examples are also available in Swagger.”

## Slide 12 — How load testing works

“The load generator is a separate process, so it does not use resources inside the API container. It uses asyncio and HTTPX to send requests with configurable concurrency. For async tests, a separate callback receiver correlates callbacks by request ID. The generator records total requests, success and failure counts, throughput, sync latency, acknowledgement latency, and complete time-to-callback. It prints a summary and writes a JSON report.”

## Slide 13 — Measured load-test output

“This test sent 50 requests to each endpoint with concurrency 10. All 50 sync requests succeeded, with throughput of 20.9 requests per second. The sync median latency was about 248 milliseconds. All 50 async requests were accepted, processed, and delivered to the callback receiver, with zero missing callbacks. The async acknowledgement median was about 242 milliseconds, while median end-to-end callback time was about 6.1 seconds.”

## Slide 14 — What this demonstrates

“The project demonstrates that sync and async APIs can share the same business logic while providing different client behavior. Sync is suitable when the caller needs the result immediately. Async is suitable when work should be buffered and processed independently. PostgreSQL provides traceability, RabbitMQ handles background delivery, and Docker makes the complete demonstration reproducible. I will finish by showing Swagger, one sync request, one async request, the stored status, and the load-test output.”

## Suggested recording flow

1. Present slides 1–10 for the problem, architecture, safeguards, and contribution.
2. Open Swagger and demonstrate `/healthz`, `/sync`, `/async`, and `/requests/{id}`.
3. Briefly show RabbitMQ management and the PostgreSQL-backed request state.
4. Return to slides 12–13 and explain the load generator and measured output.
5. Close with slide 14.
