# Database Connection Pool Exhaustion

## Symptoms
- Application logs show `HikariPool-1 - Connection is not available, request timed out after 30000ms`.
- Postgres logs: `FATAL: remaining connection slots are reserved for non-replication superuser connections` or `FATAL: sorry, too many clients already`.
- Request latency climbs, then requests fail with 500s; health checks that hit the database start flapping.

## Likely causes
- Traffic spike exceeding the configured pool size.
- Connection leak: code paths that borrow a connection and never return it (missing `close()` or an unclosed transaction).
- Long-running or stuck queries holding connections open.
- Pool `maximumPoolSize` set lower than `threads * concurrent-queries`.

## Diagnosis
- Current connections by state:
  `SELECT state, count(*) FROM pg_stat_activity GROUP BY state;`
- Longest-running queries:
  `SELECT pid, now() - query_start AS runtime, state, query FROM pg_stat_activity ORDER BY runtime DESC LIMIT 10;`
- Compare active connections against the ceiling:
  `SHOW max_connections;`

## Remediation
- Terminate a specific stuck backend (confirm the pid first):
  `SELECT pg_terminate_backend(<pid>);`
- Kill idle-in-transaction connections older than five minutes:
  `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND now() - state_change > interval '5 minutes';`
- Temporarily raise the application pool size and roll the deployment, then find and fix the leak.
- If saturation is from a spike, scale read replicas or add PgBouncer in transaction-pooling mode.

## Escalation
Escalate to the database on-call if `max_connections` must be raised (requires a restart) or if a leak cannot be isolated within 30 minutes.
