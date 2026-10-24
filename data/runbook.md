# Pipeline Failure Runbook (synthetic)

## schema_drift
Symptoms: column count mismatch, "cannot merge fields", unexpected type, missing column.
Checks: compare the current schema with the last successful run's schema. Identify added, removed, or retyped columns.
Fix: update the schema mapping or cast. For added columns, decide whether to ingest or ignore. Rerun the failed partition only.
Escalate: if a column was removed or retyped in a breaking way, notify the data owner before changing the mapping.

## expired_credentials
Symptoms: ExpiredToken, 401 or 403 from an API, authentication failed, password expired.
Checks: find which credential the job uses and its rotation date.
Fix: rotate or refresh the credential in the secrets manager, then rerun.
Escalate: if the credential is owned by an external partner, open a request with the partner contact. Never paste secrets into tickets.

## out_of_memory
Symptoms: OutOfMemoryError, container killed for exceeding memory limits, executor lost.
Checks: compare input size with the 30-day average. Look for skew (one key holding a large share of rows).
Fix: for a volume spike, increase memory or add partitions. For skew, salt the key or filter null keys before the join.
Escalate: if input volume grew more than 3x without notice, ask the upstream owner why.

## upstream_file_missing
Symptoms: file not found, zero-byte file, empty input directory.
Checks: confirm the upstream SLA time and whether the file has arrived since. Check the last successful file date.
Fix: wait until past the SLA, then contact the upstream owner. Rerun once the file lands. Do not generate a substitute file.
Escalate: if the SLA is breached by more than 2 hours, page the upstream owner.

## data_quality_threshold
Symptoms: DQ check failed, null rate above threshold, row count below minimum.
Checks: compare to the 7-day average. Check whether the upstream load completed fully.
Fix: do not lower the threshold to make the job pass. Find whether the source is partial or broken, and rerun after it is corrected.
Escalate: always notify the data owner when a quality threshold fails, because downstream campaigns may be affected.

## permission_denied
Symptoms: AccessDenied, not authorized, missing USE SCHEMA or table privileges.
Checks: look for recent policy or role changes near the failure time.
Fix: request the missing permission through the access process, with the exact action and resource from the error.
Escalate: never grant broad permissions to get a job passing. Least privilege applies.

## dependency_timeout
Symptoms: read timeout, retries exhausted, lock wait timeout.
Checks: is the downstream service slow or down? Is another process holding a lock, and for how long?
Fix: rerun only the failed batches. For locks, wait for or coordinate with the lock holder. Do not kill another team's session without approval.
Escalate: if the same dependency timed out on three runs in a week, open a reliability ticket for its owner.

## duplicate_load
Symptoms: unique constraint violation, overlapping partitions, duplicate rows after a retry.
Checks: was an earlier run partially successful? Was a manual backfill run at the same time as the schedule?
Fix: make the load idempotent (delete the partition and reload, or merge on a key). Remove duplicates before rerunning.
Escalate: if duplicates reached a downstream table, notify its consumers.

## unknown
Symptoms: generic internal error with no stack trace or useful message.
Checks: look at previous runs, recent deployments, and platform status.
Fix: do not guess. Collect more information (platform logs, deployment history) and hand off to a human.
Escalate: always. Mark needs_human true.
