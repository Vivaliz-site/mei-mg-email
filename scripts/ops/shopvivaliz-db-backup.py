#!/usr/bin/env python3
import argparse
import fcntl
import stat
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

NAMESPACE = "gruilpqsbqqb"
BUCKET = "shopvivaliz-free-archive"
OCI = "/home/ubuntu/.venvs/oci-cli/bin/oci"
PG_DUMP = "/usr/bin/pg_dump"
PG_RESTORE = "/usr/bin/pg_restore"

PROFILES = {
    "main": [
        {"name": "solange-production", "container": "supabase_db_solange-rolla-consultorio"},
        {"name": "solange-staging", "container": "supabase_db_solange-client-demo",
         "mode": "host_socket", "user": "supabase_admin", "database": "postgres"},
        {"name": "mei-email", "container": "mei-mg-email-db"},
    ],
    "secondary": [
        {"name": "mlrr-phase3", "container": "mlrr-pg-prod", "user": "postgres", "database": "mlrr_phase3", "mode": "container"},
    ],
}


def targets_for(profile):
    return [dict(item) for item in PROFILES[profile]]


def object_name(profile, name):
    return f"db-backups/{profile}/{name}-latest.dump"


def inspect_container(name):
    raw = subprocess.check_output(["docker", "inspect", name], text=True)
    return json.loads(raw)[0]


def connection_for(target):
    info = inspect_container(target["container"])
    env = {}
    for item in info["Config"].get("Env", []):
        key, _, value = item.partition("=")
        env[key] = value
    user = target.get("user") or env.get("POSTGRES_USER")
    database = target.get("database") or env.get("POSTGRES_DB")
    password = env.get("POSTGRES_PASSWORD", "")
    ports = info["NetworkSettings"]["Ports"].get("5432/tcp") or []
    if not ports:
        raise RuntimeError(f"no published postgres port for {target['container']}")
    return {
        "host": "127.0.0.1",
        "port": ports[0]["HostPort"],
        "user": user,
        "database": database,
        "password": password,
    }


def host_socket_dump(target, dump):
    """Dump a strictly allowlisted local demo via its private Unix socket.

    The PostgreSQL 15 client inside this historical Docker image fails with
    SIGSEGV (139); the host PostgreSQL 16 client was validated against the
    exact container-local socket, without publishing any DB port. The runner
    runs as ubuntu and only the fixed pg_dump binary is elevated via sudo -n.
    Neither credentials nor SQL/data are printed to the action log.
    """
    if (target.get("name") != "solange-staging"
            or target.get("container") != "supabase_db_solange-client-demo"
            or target.get("user") != "supabase_admin"
            or target.get("database") != "postgres"):
        raise RuntimeError("host_socket_target_not_allowlisted")
    info = inspect_container(target["container"])
    state = info.get("State") or {}
    config = info.get("Config") or {}
    image = str(config.get("Image") or "")
    settings = dict(item.split("=", 1) for item in config.get("Env", [])
                    if "=" in item)
    pid = state.get("Pid")
    if (info.get("Name") != "/" + target["container"]
            or state.get("Status") != "running"
            or (state.get("Health") or {}).get("Status") != "healthy"
            or not image.startswith("public.ecr.aws/supabase/postgres:")
            or type(pid) is not int or pid < 2
            or not info.get("Id")
            or settings.get("POSTGRES_USER") != target["user"]
            or settings.get("POSTGRES_DB") != target["database"]):
        raise RuntimeError("local_demo_identity_or_health_unverified")
    socket_dir = f"/proc/{pid}/root/run/postgresql"
    # Write through a pre-opened, owner-private destination rather than
    # root-owned -f output, preserving archive ownership for pg_restore.
    # No host-port mapping and no PG password are required or requested.
    with open(dump, "wb") as out:
        run_checked(["sudo", "-n", PG_DUMP, "--no-password",
                     "-h", socket_dir, "-p", "5432",
                     "-U", target["user"], "-d", target["database"],
                     "-Fc", "-Z", "3"], stdout=out)
    after = inspect_container(target["container"])
    if (after.get("Id") != info["Id"]
            or (after.get("State") or {}).get("Pid") != pid
            or (after.get("State") or {}).get("Status") != "running"):
        raise RuntimeError("local_demo_identity_changed_during_dump")


def run_checked(args, *, env=None, stdin=None, stdout=None):
    subprocess.run(args, env=env, stdin=stdin, stdout=stdout, check=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_target(profile, target):
    obj = object_name(profile, target["name"])
    with tempfile.TemporaryDirectory(prefix="shopvivaliz-db-backup-") as td:
        dump = Path(td) / "backup.dump"
        listing = Path(td) / "restore.list"
        manifest = Path(td) / "backup.sha256"
        if target.get("mode") == "host_socket":
            host_socket_dump(target, dump)
        elif target.get("mode") == "container":
            with open(dump, "wb") as out:
                run_checked(["docker", "exec", target["container"], "pg_dump",
                             "-U", target["user"], "-d", target["database"],
                             "-Fc", "-Z", "3"], stdout=out)
        else:
            conn = connection_for(target)
            env = os.environ.copy()
            env["PGPASSWORD"] = conn["password"]
            cmd = [PG_DUMP, "-h", conn["host"], "-p", conn["port"], "-U", conn["user"],
                   "-d", conn["database"], "-Fc", "-Z", "3", "-f", str(dump)]
            run_checked(cmd, env=env)
        size = dump.stat().st_size
        if size < 4096:
            raise RuntimeError(f"dump unexpectedly small for {target['name']}: {size}")
        with open(listing, "w") as out:
            run_checked([PG_RESTORE, "-l", str(dump)], stdout=out)
        entries = sum(1 for line in listing.read_text().splitlines() if line and not line.startswith(";"))
        if entries < 5:
            raise RuntimeError(f"restore list too small for {target['name']}: {entries}")
        digest = sha256_file(dump)
        manifest.write_text(f"{digest}  {Path(obj).name}\n")
        put_object(dump, obj)
        put_object(manifest, obj + ".sha256")
        remote_entries = verify_remote_copy(obj, size, digest)
        print(
            f"backup_verified name={target['name']} bytes={size} "
            f"restore_entries={entries} remote_restore_entries={remote_entries} sha256={digest}"
        )


def put_object(path, name):
    run_checked([OCI, "os", "object", "put", "--auth", "instance_principal",
                 "--namespace-name", NAMESPACE, "--bucket-name", BUCKET,
                 "--file", str(path), "--name", name, "--force"], stdout=subprocess.DEVNULL)


def verify_remote_copy(name, expected_size, expected_digest):
    with tempfile.TemporaryDirectory(prefix="shopvivaliz-db-remote-verify-") as td:
        remote_dump = Path(td) / "remote.dump"
        remote_manifest = Path(td) / "remote.sha256"
        remote_listing = Path(td) / "remote.restore.list"
        run_checked([OCI, "os", "object", "get", "--auth", "instance_principal",
                     "--namespace-name", NAMESPACE, "--bucket-name", BUCKET,
                     "--name", name, "--file", str(remote_dump)], stdout=subprocess.DEVNULL)
        run_checked([OCI, "os", "object", "get", "--auth", "instance_principal",
                     "--namespace-name", NAMESPACE, "--bucket-name", BUCKET,
                     "--name", name + ".sha256", "--file", str(remote_manifest)], stdout=subprocess.DEVNULL)
        actual_size = remote_dump.stat().st_size
        if actual_size != expected_size:
            raise RuntimeError(
                f"remote size mismatch for {name}: local={expected_size} remote={actual_size}"
            )
        manifest_fields = remote_manifest.read_text().split()
        manifest_digest = manifest_fields[0] if manifest_fields else ""
        if manifest_digest != expected_digest:
            raise RuntimeError(f"remote checksum manifest mismatch for {name}")
        actual_digest = sha256_file(remote_dump)
        if actual_digest != expected_digest:
            raise RuntimeError(f"remote sha256 mismatch for {name}")
        with open(remote_listing, "w") as out:
            run_checked([PG_RESTORE, "-l", str(remote_dump)], stdout=out)
        entries = sum(
            1 for line in remote_listing.read_text().splitlines()
            if line and not line.startswith(";")
        )
        if entries < 5:
            raise RuntimeError(f"remote restore list too small for {name}: {entries}")
        return entries


LOCK_DIR = Path("/home/ubuntu/.local/state/shopvivaliz-backup-locks")


def locked_backup_target(profile, target):
    """Per-database host-local lease, held through OCI upload and readback.

    The lock file is persistent on purpose, but the kernel releases the FLOCK
    automatically when the process exits, including in cancelled Actions.
    """
    if profile != "main" or target.get("name") not in (
            "solange-production", "solange-staging"):
        raise RuntimeError("unrecognized_scheduled_local_backup_target")
    LOCK_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = LOCK_DIR.lstat()
    if (not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != os.geteuid()
            or stat.S_IMODE(directory.st_mode) != 0o700):
        raise RuntimeError("unsafe_local_backup_lock_directory")
    lock_path = LOCK_DIR / (target["name"] + ".lock")
    flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(lock_path, flags, 0o600)
    try:
        lock_stat = os.fstat(fd)
        if (not stat.S_ISREG(lock_stat.st_mode)
                or lock_stat.st_uid != os.geteuid()
                or stat.S_IMODE(lock_stat.st_mode) != 0o600):
            raise RuntimeError("unsafe_local_backup_lock_file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("local_backup_target_already_running") from exc
        backup_target(profile, target)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--target")
    args = parser.parse_args()
    targets = targets_for(args.profile)
    if args.target:
        targets = [t for t in targets if t["name"] == args.target]
        if not targets:
            raise SystemExit(f"unknown target: {args.target}")
    for target in targets:
        if args.profile == "main" and target["name"] in ("solange-production", "solange-staging"):
            locked_backup_target(args.profile, target)
        else:
            backup_target(args.profile, target)


if __name__ == "__main__":
    main()
