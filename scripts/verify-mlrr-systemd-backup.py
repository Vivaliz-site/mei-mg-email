#!/usr/bin/env python3
"""Read-only attestation of the existing Marina MLRR single-writer backup.

The Ubuntu runner must never create a competing dump or OCI writer. This
attests the specific root-owned, systemd-operated MLRR target, not a restore.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import pwd
import re
import socket
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

SHARED = Path(__file__).resolve().with_name("verify-mei-systemd-backup.py")
WRAPPER = Path("/usr/local/sbin/shopvivaliz-db-backup")
RUNTIME_SCRIPT = Path("/usr/local/sbin/shopvivaliz-db-backup.py")
DUMP_OBJECT = "db-backups/secondary/mlrr-phase3-latest.dump"
EXPECTED_HOST = "marina-a1-4c24g"
# Exact five-line root-owned script installed on Marina, verified by read-only
# inspection on 2026-11-08. A two-line substring test is insufficient: an
# additional foreground/background invocation could start a competing writer.
CANONICAL_WRAPPER = (
    "#!/bin/sh\n"
    "set -eu\n"
    "HELPER=/usr/local/sbin/shopvivaliz-db-backup.py\n"
    '[ -x "$HELPER" ] || { echo "missing canonical backup helper: $HELPER" >&2; exit 1; }\n'
    'exec "$HELPER" --profile secondary --target mlrr-phase3\n'
)
EXPECTED_TARGET = {
    "name": "mlrr-phase3", "container": "mlrr-pg-prod",
    "user": "postgres", "database": "mlrr_phase3", "mode": "container",
}

spec = importlib.util.spec_from_file_location("mei_backup_shared_reader", SHARED)
if spec is None or spec.loader is None:
    raise RuntimeError("SHARED_VERIFIER_UNAVAILABLE")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def validate_single_writer() -> None:
    """Require the exact installed/root-owned source and host identity."""
    if (socket.gethostname().split(".")[0] != EXPECTED_HOST
            or pwd.getpwuid(os.geteuid()).pw_name != "ubuntu"):
        raise reader.VerificationError("WRONG_MLRR_BACKUP_HOST_OR_USER")
    for path in (WRAPPER, RUNTIME_SCRIPT):
        try:
            info = path.lstat()
        except OSError as exc:
            raise reader.VerificationError("MLRR_BACKUP_WRITER_MISSING") from exc
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != 0
                or stat.S_IMODE(info.st_mode) & 0o022):
            raise reader.VerificationError("MLRR_BACKUP_WRITER_UNTRUSTED")

    try:
        wrapper = WRAPPER.read_text(encoding="utf-8")
        source = RUNTIME_SCRIPT.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise reader.VerificationError("MLRR_BACKUP_WRITER_UNREADABLE") from exc
    # Fail closed on *all* wrapper drift, including background jobs, injected
    # shell statements, extra trailing commands, and replaced safety guards.
    # This inspects text only; neither the wrapper nor the backup is executed.
    if wrapper != CANONICAL_WRAPPER:
        raise reader.VerificationError("MLRR_BACKUP_WRAPPER_MISMATCH")

    try:
        tree = ast.parse(source)
        profiles = [
            ast.literal_eval(node.value) for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "PROFILES"
                    for target in node.targets)
        ]
    except (SyntaxError, ValueError, TypeError) as exc:
        raise reader.VerificationError("MLRR_BACKUP_PROFILES_UNVERIFIABLE") from exc
    if len(profiles) != 1 or profiles[0].get("secondary") != [EXPECTED_TARGET]:
        raise reader.VerificationError("MLRR_BACKUP_TARGET_MISMATCH")

    service = reader.command(
        "systemctl", "show", reader.BACKUP_SERVICE, "-p", "ExecStart",
    )
    if not re.search(r"(?:^|[\s{])path=/usr/local/sbin/shopvivaliz-db-backup(?=[\s;}]|$)", service):
        raise reader.VerificationError("MLRR_BACKUP_SERVICE_EXEC_MISMATCH")


def main() -> int:
    try:
        validate_single_writer()
        now = datetime.now(timezone.utc)
        finished = reader.latest_service_completion(now)
        settings = reader.runtime_oci_settings(RUNTIME_SCRIPT)
        dump = reader.object_metadata(DUMP_OBJECT, settings)
        checksum = reader.object_metadata(DUMP_OBJECT + ".sha256", settings)
        reader.verify(now, finished, dump, checksum)
    except reader.VerificationError as exc:
        print("MLRR_SYSTEMD_BACKUP_READBACK=FAIL code=" + str(exc), file=sys.stderr)
        return 2
    print(
        "MLRR_SYSTEMD_BACKUP_READBACK=PASS read_only=true "
        "single_writer=systemd host=marina-a1-4c24g "
        "profile=secondary target=mlrr-phase3 timer=active "
        "remote_dump=true remote_checksum_manifest=true "
        "recent_service_completion=true restore_drill=NOT_CERTIFIED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
