# Kafka Consumer Lag

## Symptoms
- Consumer group lag grows: `records-lag-max` is high and rising.
- Downstream data is stale; the consumer group is falling behind the producers.
- Frequent consumer group rebalances appear in the logs.

## Likely causes
- Consumers processing slower than producers publish (too few consumers or a slow handler).
- A poison message or a slow downstream call stalling one partition.
- Frequent rebalances because processing time exceeds `max.poll.interval.ms`.
- Fewer consumers than partitions, so some partitions are under-served.

## Diagnosis
- Inspect lag per partition:
  `kafka-consumer-groups.sh --bootstrap-server <broker> --describe --group <group>`
- Check whether one partition dominates the lag (skew or a stuck handler).
- Look for rebalance loops and rising processing time in the consumer logs.

## Remediation
- Scale consumers up to (but not beyond) the partition count to add parallelism.
- Reduce `max.poll.records` or raise `max.poll.interval.ms` if long processing is triggering rebalances.
- Move slow work off the poll loop (hand it to a worker) so polls stay frequent.
- If a poison message is blocking a partition, route it to a dead-letter topic and continue.

## Escalation
Escalate to the platform or streaming team if the brokers are unhealthy or a partition reassignment is needed.
