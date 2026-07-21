# Disk Space Exhaustion

## Symptoms
- Writes fail with `No space left on device` (errno 28).
- Disk usage at or near 100% on a mount such as `/`, `/var`, or a data volume.
- Databases go read-only, log shipping stalls, and the node may report `DiskPressure`.

## Likely causes
- Unrotated or overly verbose application logs filling `/var/log`.
- A runaway file or accumulated core dumps.
- Docker or container image and layer buildup.
- A data volume that is genuinely at capacity.

## Diagnosis
- Confirm which mount is full:
  `df -h`
- Find the largest directories on the affected mount:
  `du -x -h --max-depth=1 /var | sort -rh | head`
- Check for large deleted-but-still-open files held by a process:
  `lsof +L1`

## Remediation
- Rotate and compress logs immediately, then fix the logrotate configuration.
- Reclaim container space (prunes only unused data):
  `docker system prune -af`
- Truncate a specific runaway log without breaking the writer:
  `truncate -s 0 /var/log/<file>.log`
- If a data volume is genuinely full, expand the volume or add capacity.

## Escalation
Escalate to platform on-call to resize the volume, or to the service owner if application logging volume is the root cause.
