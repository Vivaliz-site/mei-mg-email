# Weekly database backups

The scheduled database backup workflow runs every Sunday at 04:30 UTC.

- `mei-backend` runs the validated `main` profile on the primary VM.
- `mei-ci` runs the validated `secondary` profile on the secondary VM.
- Each profile creates PostgreSQL custom-format dumps, validates them with `pg_restore -l`, uploads them to OCI Object Storage, and verifies the remote object size.
- `workflow_dispatch` remains available for manual recovery and verification runs.

The workflow is intentionally pinned to the existing self-hosted runner labels so each host backs up only the persistent databases it owns.

## Independent targets and failure handling (Audit V5, issue #195)

The main-host job calls the pre-existing `shopvivaliz-db-backup.py` three times, with
an explicit `--profile main --target` for each local database:

- `solange-production`: local Docker database only;
- `solange-staging`: **legacy local demo Docker database**, NOT the managed
  Supabase staging database used by the published Solange app;
- `mei-email`: the independent Mei email database.

The two later steps use `if: ${{ !cancelled() }}`: a failure of one target
must not prevent an attempt for another, while the **entire job still fails**
if any target fails. No `continue-on-error`, `|| true`, alternate runner,
new schedule, firewall/port exposure, or duplicate backup process is permitted.
A green backup for one target does not certify another target or a complete
restore. The secondary-host `--profile secondary` job is unchanged.

**Observed fail-closed conditions on 08 Nov 2026:** the legacy
`supabase_db_solange-client-demo` container has no published host PostgreSQL
port (normal network isolation). A separate internal schema-only `pg_dump`
canary ended with exit 139, despite `pg_isready` and `psql SELECT 1`
passing. Do not change the target blindly to Docker exec, make the database
public, suppress a failed step, or infer a valid managed Supabase backup.
Investigate the local legacy dump separately and keep it failed until proven.

OCI Object Storage object `db-backups/main/mei-email-latest.dump` had
`last-modified=2026-11-08T04:38:33Z` in read-only metadata, even though
the weekly workflow had failed. This can indicate an independent writer.
Before any manual rerun, establish the actual owner/schedule and avoid
simultaneous uploads, then verify the source identity, remote digest,
restore drill, retention and provenance. **Do not use OCI object
`time-created` as freshness proof for overwritten `-latest` keys.**

The managed Supabase staging backup/readback gate remains separately blocked
under `Vivaliz-site/solange-rolla-consultorio#191`; this workflow's legacy
Docker dump cannot satisfy that gate.
