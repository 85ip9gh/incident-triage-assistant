# Kubernetes Pod OOMKilled

## Symptoms
- `kubectl describe pod` shows `Last State: Terminated`, `Reason: OOMKilled`, `Exit Code: 137`.
- The container is killed whenever it exceeds its memory limit; restarts get more frequent under load.
- Node pressure events such as `The node was low on resource: memory`.

## Likely causes
- Memory `limits` set below the application's real working set.
- A memory leak or an unbounded in-memory cache or buffer.
- A batch job or request that loads too much into memory at once.
- JVM or runtime heap sizing not aligned with the container memory limit.

## Diagnosis
- Confirm the OOM kill and exit code 137:
  `kubectl describe pod <pod>`
- Compare live usage against limits:
  `kubectl top pod <pod> --containers`
- Review the workload's `resources.limits.memory` and `resources.requests.memory`.

## Remediation
- Raise `resources.limits.memory` (and `requests`) to cover the observed peak plus headroom, then roll out.
- For the JVM, set `-XX:MaxRAMPercentage` so the heap stays under the container limit.
- Cap in-memory caches and stream large payloads instead of buffering them fully.
- If it is a genuine leak, capture a heap dump before the next restart and hand it to the service owner.

## Escalation
Escalate to the service owner for a suspected leak; escalate to platform on-call if multiple unrelated pods OOM on the same node, which points to an under-provisioned node.
