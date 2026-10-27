# Queue Architecture

Orders enter a durable queue. The queue retry policy uses exponential backoff with a cap of five attempts.

## Worker Concurrency

Worker concurrency is limited to eight workers per node to protect the database.
