# High API Latency

## Symptoms
- p99 (and often p95) response time spikes well above baseline on dashboards.
- Clients see slow responses, `504 Gateway Timeout`, or upstream timeouts.
- Request queue depth and thread-pool saturation climb; throughput may drop.

## Likely causes
- A slow downstream dependency (database, cache, or a third-party API).
- Thread-pool or connection-pool saturation causing requests to queue.
- A recent deploy that introduced an N+1 query or removed a cache.
- Under-scaled replicas for the current traffic level.

## Diagnosis
- Break latency down by endpoint and by downstream span in the tracing tool (Datadog APM / OpenTelemetry).
- Check whether the spike lines up with a deploy or a traffic increase.
- Inspect saturation signals: thread-pool active vs max, database pool usage, garbage-collection pauses.

## Remediation
- If a single downstream is slow, add a timeout and a circuit breaker so it fails fast instead of queuing.
- If a recent deploy regressed latency, roll it back:
  `kubectl rollout undo deployment/<name>`
- Scale out replicas to absorb load:
  `kubectl scale deployment/<name> --replicas=<n>`
- Restore or warm the cache that was removed or is cold.

## Escalation
Escalate to the team that owns the slow downstream. Page the incident commander if latency breaches the customer-facing SLO.
