"""Fail-closed regression tests for the local, unexposed demo PostgreSQL backup."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
import importlib.util
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/ops/shopvivaliz-db-backup.py"
spec = importlib.util.spec_from_file_location("shopvivaliz_backup", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def valid_docker_info():
    return {
        "Id": "sha256:permitted-local-container",
        "Name": "/supabase_db_solange-client-demo",
        "State": {
            "Pid": 7440, "Status": "running", "Health": {"Status": "healthy"}
        },
        "Config": {
            "Image": "public.ecr.aws/supabase/postgres:15.8.1.085",
            "Env": ["POSTGRES_USER=supabase_admin", "POSTGRES_DB=postgres"],
        },
    }


class LocalDemoSocketBackupTest(TestCase):
    def setUp(self):
        self.target = next(
            target for target in mod.PROFILES["main"]
            if target["name"] == "solange-staging"
        )

    def test_main_targets_still_include_production_demo_and_mei(self):
        self.assertEqual(
            [target["name"] for target in mod.PROFILES["main"]],
            ["solange-production", "solange-staging", "mei-email"],
        )
        self.assertEqual(self.target["mode"], "host_socket")
        self.assertEqual(self.target["user"], "supabase_admin")
        self.assertEqual(self.target["database"], "postgres")
        self.assertNotIn("mode", mod.PROFILES["main"][0])
        self.assertNotIn("mode", mod.PROFILES["main"][2])

    def test_only_fixed_host_client_is_elevated_and_output_has_private_owner(self):
        info = valid_docker_info()
        arguments = []

        def fake_run(args, **kw):
            arguments.append((list(args), kw))
            kw["stdout"].write(b"PGDMPfixture-no-customer-data")

        with TemporaryDirectory() as td:
            destination = Path(td) / "backup.dump"
            with patch.object(mod, "inspect_container", side_effect=[info, info]):
                with patch.object(mod, "run_checked", side_effect=fake_run):
                    mod.host_socket_dump(self.target, destination)
            self.assertEqual(destination.read_bytes(), b"PGDMPfixture-no-customer-data")
        self.assertEqual(len(arguments), 1)
        args, kwargs = arguments[0]
        self.assertEqual(args[:3], ["sudo", "-n", "/usr/bin/pg_dump"])
        self.assertIn("--no-password", args)
        self.assertEqual(args[args.index("-h")+1], "/proc/7440/root/run/postgresql")
        self.assertEqual(args[args.index("-p")+1], "5432")
        self.assertEqual(args[args.index("-U")+1], "supabase_admin")
        self.assertEqual(args[args.index("-d")+1], "postgres")
        self.assertEqual(args[-3:], ["-Fc", "-Z", "3"])
        self.assertNotIn("-f", args)
        self.assertNotIn("PGPASSWORD", str(args))
        self.assertIn("stdout", kwargs)

    def test_wrong_target_must_never_use_sudo(self):
        for key, value in (
            ("name", "mei-email"), ("container", "mei-mg-email-db"),
            ("user", "postgres"), ("database", "app"),
        ):
            with self.subTest(key=key):
                invalid = dict(self.target)
                invalid[key] = value
                with patch.object(mod, "run_checked") as run:
                    with self.assertRaisesRegex(
                        RuntimeError, "host_socket_target_not_allowlisted"
                    ):
                        mod.host_socket_dump(invalid, Path("/dev/null"))
                    run.assert_not_called()

    def test_unhealthy_unexpected_image_or_pid_fails_closed(self):
        for mutation in (
            lambda info: info["State"].update({"Pid": 0}),
            lambda info: info["State"]["Health"].update({"Status": "unhealthy"}),
            lambda info: info["Config"].update({"Image": "postgres:untrusted"}),
            lambda info: info["Config"].update({"Env": ["POSTGRES_USER=other"]}),
        ):
            info = valid_docker_info()
            mutation(info)
            with patch.object(mod, "inspect_container", return_value=info):
                with patch.object(mod, "run_checked") as run:
                    with self.assertRaisesRegex(
                        RuntimeError, "local_demo_identity_or_health_unverified"
                    ):
                        mod.host_socket_dump(self.target, Path("/dev/null"))
                    run.assert_not_called()

    def test_container_replacement_during_dump_must_reject_archive(self):
        before = valid_docker_info()
        after = deepcopy(before)
        after["State"]["Pid"] = 7441
        with TemporaryDirectory() as td:
            dest = Path(td) / "backup.dump"
            with patch.object(mod, "inspect_container", side_effect=[before, after]):
                with patch.object(mod, "run_checked") as run:
                    with self.assertRaisesRegex(
                        RuntimeError, "local_demo_identity_changed_during_dump"
                    ):
                        mod.host_socket_dump(self.target, dest)
                    run.assert_called_once()

    def test_sudo_denial_is_not_bypassed_or_retried_insecurely(self):
        failure = subprocess.CalledProcessError(1, ["sudo", "-n", "/usr/bin/pg_dump"])
        with TemporaryDirectory() as td:
            with patch.object(
                mod, "inspect_container", return_value=valid_docker_info()
            ):
                with patch.object(mod, "run_checked", side_effect=failure) as run:
                    with self.assertRaises(subprocess.CalledProcessError):
                        mod.host_socket_dump(self.target, Path(td) / "dump")
                    run.assert_called_once()


if __name__ == "__main__":
    main()
