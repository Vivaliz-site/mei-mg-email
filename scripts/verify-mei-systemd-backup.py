#!/usr/bin/env python3
"""Read-only freshness gate for the existing single-writer Mei backup timer.

This gate never makes a dump, restarts services, exposes a database port or
writes to Object Storage. It does not certify an isolated restore.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

BACKUP_SERVICE = "shopvivaliz-db-backup.service"
BACKUP_TIMER = "shopvivaliz-db-backup.timer"
RUNTIME_SCRIPT = Path("/home/ubuntu/.local/bin/shopvivaliz-db-backup.py")
DUMP_OBJECT = "db-backups/main/mei-email-latest.dump"
MAX_AGE = timedelta(hours=12)
MAX_LAG = timedelta(hours=1)


class VerificationError(Exception):
    """Expected fail-closed verification error identified only by code."""


def command(*args: str) -> str:
    try:
        result = subprocess.run(
            list(args), capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError("COMMAND_UNAVAILABLE") from exc
    if result.returncode != 0:
        raise VerificationError("READ_ONLY_PROBE_REJECTED")
    return result.stdout.strip()


def latest_service_completion(now: datetime) -> datetime:
    metadata = command(
        "systemctl", "show", BACKUP_SERVICE,
        "-p", "Result", "-p", "ExecMainStatus", "-p", "ActiveState",
        "-p", "InactiveEnterTimestamp",
    )
    fields = dict(line.split("=", 1) for line in metadata.splitlines() if "=" in line)
    if (fields.get("Result") != "success"
            or fields.get("ExecMainStatus") != "0"
            or fields.get("ActiveState") != "inactive"):
        raise VerificationError("BACKUP_SERVICE_NOT_COMPLETED_SUCCESSFULLY")
    if command("systemctl", "is-active", BACKUP_TIMER) != "active":
        raise VerificationError("BACKUP_TIMER_INACTIVE")
    timestamp = fields.get("InactiveEnterTimestamp", "")
    try:
        finished = datetime.strptime(
            timestamp, "%a %Y-%m-%d %H:%M:%S UTC"
        ).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise VerificationError("BACKUP_FINISH_TIME_UNVERIFIED") from exc
    if not (now - MAX_AGE <= finished <= now):
        raise VerificationError("BACKUP_SERVICE_RESULT_STALE")
    return finished


def runtime_oci_settings(script: Path = RUNTIME_SCRIPT) -> tuple[str, str, str]:
    """Read only literal OCI settings from trusted host script; no execution."""
    try:
        tree = ast.parse(script.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise VerificationError("OCI_SETTINGS_UNVERIFIABLE") from exc
    literals: dict[str, str] = {}
    for item in tree.body:
        if not isinstance(item, ast.Assign) or not isinstance(item.value, ast.Constant):
            continue
        if not isinstance(item.value.value, str):
            continue
        for target in item.targets:
            if isinstance(target, ast.Name) and target.id in ("NAMESPACE", "BUCKET", "OCI"):
                literals[target.id] = item.value.value
    if any(not literals.get(key) for key in ("NAMESPACE", "BUCKET", "OCI")):
        raise VerificationError("OCI_SETTINGS_INCOMPLETE")
    if not Path(literals["OCI"]).is_file():
        raise VerificationError("OCI_CLI_NOT_FOUND")
    return literals["OCI"], literals["NAMESPACE"], literals["BUCKET"]


def object_metadata(key: str, settings: tuple[str, str, str]) -> tuple[datetime, int]:
    cli, namespace, bucket = settings
    body = command(
        cli, "os", "object", "head", "--auth", "instance_principal",
        "--namespace-name", namespace, "--bucket-name", bucket,
        "--name", key, "--output", "json",
    )
    try:
        result = json.loads(body)
        if not isinstance(result, dict) or not result.get("etag"):
            raise ValueError("missing_object_metadata")
        stamp = parsedate_to_datetime(result["last-modified"])
        size = int(result["content-length"])
        if stamp.tzinfo is None or size < 1:
            raise ValueError("invalid_object_metadata")
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise VerificationError("OCI_OBJECT_METADATA_INVALID") from exc
    return stamp.astimezone(timezone.utc), size


def verify(
    now: datetime, service_finished: datetime,
    dump: tuple[datetime, int], checksum: tuple[datetime, int],
) -> None:
    dump_time, dump_bytes = dump
    checksum_time, checksum_bytes = checksum
    if dump_bytes < 4096 or not 64 <= checksum_bytes <= 2048:
        raise VerificationError("OCI_BACKUP_ARTIFACT_SIZE_INVALID")
    if not (now - MAX_AGE <= dump_time <= checksum_time <= service_finished <= now):
        raise VerificationError("OCI_BACKUP_ARTIFACT_NOT_FRESH_OR_OUT_OF_ORDER")
    if checksum_time - dump_time > MAX_LAG or service_finished - checksum_time > MAX_LAG:
        raise VerificationError("OCI_BACKUP_ATTESTATION_WINDOW_EXCEEDED")


def main() -> int:
    try:
        now = datetime.now(timezone.utc)
        finished = latest_service_completion(now)
        settings = runtime_oci_settings()
        dump = object_metadata(DUMP_OBJECT, settings)
        checksum = object_metadata(DUMP_OBJECT + ".sha256", settings)
        verify(now, finished, dump, checksum)
    except VerificationError as exc:
        print("MEI_SYSTEMD_BACKUP_READBACK=FAIL code=" + str(exc), file=sys.stderr)
        return 2
    print("MEI_SYSTEMD_BACKUP_READBACK=PASS read_only=true "
          "single_writer=systemd timer=active remote_dump=true "
          "remote_checksum_manifest=true recent_service_completion=true "
          "restore_drill=NOT_CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
