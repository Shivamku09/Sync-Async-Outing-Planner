RabbitMQ vs asyncio.Queue — Technology Decision
================================================

Decision
--------
Use RabbitMQ for asynchronous request processing in the Outing Planner.

Comparison
----------

| Criterion                  | asyncio.Queue                                      | RabbitMQ                                                   |
|----------------------------|----------------------------------------------------|------------------------------------------------------------|
| Storage location           | Memory inside one Python process                   | External message broker                                    |
| Survives application crash | No; queued jobs are lost                            | Yes, with durable queues and persistent messages           |
| Delivery acknowledgement   | No durable acknowledgement                         | Manual consumer acknowledgements                           |
| Failed-job retry           | Must be implemented manually                       | Retry queues and dead-letter exchanges can be configured   |
| Worker crash recovery      | In-flight work may be lost                          | Unacknowledged messages can be redelivered                  |
| Horizontal scaling         | Queue is not shared between application instances  | Multiple worker processes or machines can share the queue  |
| Backpressure               | Bounded maxsize within one process                  | Queue capacity, consumer prefetch, and publisher controls  |
| Dead-letter handling       | Must be implemented in application code            | Supported through dead-letter exchanges and queues         |
| Monitoring                 | Custom metrics are required                         | Queue depth, consumers, and message rates are observable   |
| Operational complexity     | Low                                                  | Medium; a broker must be deployed and monitored            |
| Network dependency         | None                                                 | API and workers must connect to RabbitMQ                   |
| Duplicate delivery         | Uncommon within one running process                 | Possible; consumers must be idempotent                     |
| Best fit                   | Small, single-process, non-durable background work  | Reliable asynchronous jobs requiring durability and retry  |

Why RabbitMQ was selected
-------------------------

1. An accepted asynchronous request should not disappear when the API process restarts or crashes.
2. Failed jobs and callback deliveries require controlled retries instead of being silently lost.
3. Manual acknowledgements allow a message to be removed only after its result is safely persisted.
4. Unacknowledged messages can be redelivered when a worker fails during processing.
5. API instances and worker instances can scale independently.
6. Dead-letter queues provide a visible location for jobs that exceed their retry limit.
7. RabbitMQ is designed for task delivery and is a better fit for this workload than an event-streaming platform such as Kafka.

Required reliability settings
-----------------------------

- Declare durable exchanges and queues.
- Publish persistent messages and enable publisher confirms.
- Use manual consumer acknowledgements.
- Acknowledge a planner message only after the outcome is persisted in PostgreSQL.
- Set consumer prefetch to bound concurrent work.
- Use bounded retries with delay/backoff and a dead-letter queue.
- Make workers idempotent because RabbitMQ delivery is at least once and duplicates are possible.
- Publish only the request ID; load the authoritative request data from PostgreSQL.
- Use a transactional outbox, or document and recover the database-to-broker publication failure window.

Trade-off accepted
------------------

RabbitMQ adds deployment, configuration, monitoring, and failure-handling complexity. This cost is accepted because durable jobs, acknowledgements, retry support, worker recovery, and independent scaling are more important for this design than the simplicity of an in-process asyncio.Queue.
