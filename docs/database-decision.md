# Database Decision: PostgreSQL

## Decision

Use **PostgreSQL** as the primary database for venues, requests, planner results, callback delivery records, and transactional outbox events.

## Why relational storage instead of NoSQL?

| Requirement | Why SQL fits |
|---|---|
| Structured entities | Venues, requests, callbacks, and outbox events have stable schemas. |
| Data integrity | Foreign keys, unique constraints, and checks enforce valid state. |
| Atomic updates | Request results, statuses, and outbox events can be committed together. |
| Querying | SQL supports filtering, ordering, pagination, reporting, and recovery queries. |

NoSQL adds flexibility that this data does not require and would move more consistency checks into application code.

## Why PostgreSQL over SQLite?

- PostgreSQL handles concurrent writes from API processes and RabbitMQ workers.
- SQLite serializes writes and may suffer lock contention during load tests.
- PostgreSQL provides row-level locking and is suitable for multiple application instances.

## Why PostgreSQL over MySQL?

- `JSONB` is useful for searchable request and result snapshots.
- Partial indexes efficiently target records such as pending requests or unpublished outbox events.
- `FOR UPDATE SKIP LOCKED` supports concurrent outbox publishers and recovery workers.
- PostgreSQL provides strong constraints and predictable transactional behavior.

MySQL 8 could satisfy the core requirements, but PostgreSQL provides a more direct fit for request tracking and the RabbitMQ transactional-outbox pattern.
