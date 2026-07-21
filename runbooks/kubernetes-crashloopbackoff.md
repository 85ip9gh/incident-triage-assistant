# Kubernetes CrashLoopBackOff

## Symptoms
- `kubectl get pods` shows a pod in `CrashLoopBackOff`.
- Events include `Back-off restarting failed container`.
- The container starts, exits non-zero, and Kubernetes restarts it on an exponential back-off.
- A failing liveness probe may report `Liveness probe failed` shortly before each restart.

## Likely causes
- Application crashes on startup: bad config, a missing environment variable or secret, or a failed migration.
- Failing liveness or readiness probe (wrong path, wrong port, or too-short `initialDelaySeconds`).
- A required dependency is unreachable at boot (database or a downstream service).
- A bad image or entrypoint shipped in the last deploy.

## Diagnosis
- Read the logs from the crashed container instance:
  `kubectl logs <pod> --previous`
- Describe the pod for the exit code and recent events:
  `kubectl describe pod <pod>`
- Check `Last State: Terminated` for the exit code and reason.

## Remediation
- If a config value or secret is missing, fix the ConfigMap/Secret and roll out:
  `kubectl rollout restart deployment/<name>`
- If a probe is too aggressive, raise `initialDelaySeconds` / `failureThreshold` and re-apply.
- If a bad image shipped, roll back to the previous revision:
  `kubectl rollout undo deployment/<name>`
- Reproduce locally with the same image and environment before re-deploying.

## Escalation
Escalate to the service owner if the crash originates in application code, or to platform on-call if the node or kubelet is implicated.
