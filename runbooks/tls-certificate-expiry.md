# TLS Certificate Expiry

## Symptoms
- Clients fail with `x509: certificate has expired or is not yet valid`.
- Browsers show `NET::ERR_CERT_DATE_INVALID`; `curl` reports `SSL certificate problem: certificate has expired`.
- TLS handshakes across a service start failing abruptly at a specific timestamp.

## Likely causes
- A certificate reached its `notAfter` date and was not renewed.
- Auto-renewal (cert-manager / ACME) failed silently.
- A renewed certificate was issued but never reloaded by the server.
- Clock skew on the client or server making a valid certificate look expired.

## Diagnosis
- Inspect the served certificate's validity dates:
  `echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -dates`
- For cert-manager, check the Certificate resource:
  `kubectl describe certificate <name>`
- Verify the system time is correct on both ends (`date -u`).

## Remediation
- Renew and deploy the certificate. With cert-manager, force re-issue by deleting the stale secret so it is regenerated.
- Reload the server or ingress so it picks up the new certificate (for example, restart the ingress controller or run `nginx -s reload`).
- If clock skew is the cause, fix NTP; do not touch the certificate.

## Escalation
Escalate to the platform or security team that owns the PKI or ACME issuer if renewal keeps failing.
