"""Fail-closed tests for the read-only Marina MLRR systemd backup observer."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import stat
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts/verify-mlrr-systemd-backup.py"
spec = importlib.util.spec_from_file_location("mlrr_backup_observer", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

TRUSTED_WRAPPER = (
    "#!/bin/sh\n"
    "set -eu\n"
    "HELPER=/usr/local/sbin/shopvivaliz-db-backup.py\n"
    '[ -x "$HELPER" ] || { echo "missing canonical backup helper: $HELPER" >&2; exit 1; }\n'
    'exec "$HELPER" --profile secondary --target mlrr-phase3\n'
)
TRUSTED_SOURCE = (
    "PROFILES = {'secondary': ["
    "{'name': 'mlrr-phase3', 'container': 'mlrr-pg-prod', "
    "'user': 'postgres', 'database': 'mlrr_phase3', 'mode': 'container'}]}\n"
)


class MarinaMlrrBackupObserverTests(unittest.TestCase):
    def assert_contract(self, wrapper=TRUSTED_WRAPPER, source=TRUSTED_SOURCE,
                        owner=0, mode=stat.S_IFREG | 0o755):
        with (
            patch.object(module.socket, "gethostname", return_value=module.EXPECTED_HOST),
            patch.object(module.os, "geteuid", return_value=1000),
            patch.object(module.pwd, "getpwuid",
                         return_value=SimpleNamespace(pw_name="ubuntu")),
            patch.object(Path, "lstat",
                         return_value=SimpleNamespace(st_uid=owner, st_mode=mode)),
            patch.object(Path, "read_text", side_effect=[wrapper, source]),
            patch.object(module.reader, "command",
                         return_value="ExecStart={ path=/usr/local/sbin/shopvivaliz-db-backup ; argv[]=... }"),
        ):
            module.validate_single_writer()

    def test_real_pinned_writer_contract_can_be_verified(self):
        self.assert_contract()

    def test_full_wrapper_allowlist_rejects_extra_shell_commands(self):
        """An extra foreground/background writer may never be certified."""
        valid = TRUSTED_WRAPPER
        extra = (
            ("background_before_exec",
             valid.replace(
                 'exec "$HELPER" --profile secondary --target mlrr-phase3',
                 '"$HELPER" --profile secondary --target mlrr-phase3 &\n'
                 'exec "$HELPER" --profile secondary --target mlrr-phase3')),
            ("foreground_before_exec",
             valid.replace(
                 'exec "$HELPER" --profile secondary --target mlrr-phase3',
                 'echo unexpected-command\n'
                 'exec "$HELPER" --profile secondary --target mlrr-phase3')),
            ("extra_command_after_exec",
             valid + 'echo unreachable-but-untrusted\n'),
            ("extra_command_before_guard",
             valid.replace("set -eu\n", "set -eu\necho unauthorized\n")),
            ("background_between_guard_and_exec",
             valid.replace(
                 'exec "$HELPER" --profile secondary',
                 'sh -c "echo another-writer" &\n'
                 'exec "$HELPER" --profile secondary')),
            ("guard_replaced_by_hidden_writer",
             valid.replace(
                 '[ -x "$HELPER" ] ||',
                 '[ -x "$HELPER" ] && "$HELPER" --profile secondary --target mlrr-phase3 & ||')),
            ("subshell_in_assignment",
             valid.replace(
                 "HELPER=/usr/local/sbin/shopvivaliz-db-backup.py",
                 "HELPER=$(echo /usr/local/sbin/shopvivaliz-db-backup.py)")),
            ("removed_errexit", valid.replace("set -eu\n", "")),
            ("altered_guard", valid.replace("missing canonical backup helper", "different helper error")),
            ("extra_comment", valid + '# unauthorized content\n'),
            ("extra_blank_line", valid + '\n'),
        )
        for label, wrapper in extra:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    module.reader.VerificationError, "MLRR_BACKUP_WRAPPER_MISMATCH"
                ):
                    self.assert_contract(wrapper=wrapper)

    def test_wrong_host_never_queries_or_certifies_other_machine(self):
        with patch.object(module.socket, "gethostname", return_value="always-free-arm-1787907847-26"):
            with self.assertRaisesRegex(
                module.reader.VerificationError, "WRONG_MLRR_BACKUP_HOST_OR_USER"
            ):
                module.validate_single_writer()

    def test_wrong_backup_wrapper_or_profile_fails_closed(self):
        for wrapper, source, expected_error in (
            (TRUSTED_WRAPPER.replace("--target mlrr-phase3", "--target mei-email"),
             TRUSTED_SOURCE, "MLRR_BACKUP_WRAPPER_MISMATCH"),
            (TRUSTED_WRAPPER, TRUSTED_SOURCE.replace("mlrr-pg-prod", "wrong-container"),
             "MLRR_BACKUP_TARGET_MISMATCH"),
            (TRUSTED_WRAPPER, "PROFILES=some_arbitrary_call()\n",
             "MLRR_BACKUP_PROFILES_UNVERIFIABLE"),
        ):
            with self.subTest(expected_error=expected_error):
                with self.assertRaisesRegex(module.reader.VerificationError, expected_error):
                    self.assert_contract(wrapper=wrapper, source=source)

    def test_untrusted_writer_mode_or_owner_is_denied(self):
        for owner, mode in (
            (1000, stat.S_IFREG | 0o755),
            (0, stat.S_IFLNK | 0o777),
            (0, stat.S_IFREG | 0o775),
        ):
            with self.subTest(owner=owner, mode=oct(mode)):
                with self.assertRaisesRegex(
                    module.reader.VerificationError, "MLRR_BACKUP_WRITER_UNTRUSTED"
                ):
                    self.assert_contract(owner=owner, mode=mode)

    def test_verified_recent_oci_dump_and_manifest_emit_readonly_pass(self):
        now = datetime.now(timezone.utc)
        service_end = now - timedelta(minutes=30)
        dump = (service_end - timedelta(seconds=6), 307814)
        manifest = (service_end - timedelta(seconds=3), 90)
        with (
            patch.object(module, "validate_single_writer"),
            patch.object(module.reader, "latest_service_completion",
                         return_value=service_end),
            patch.object(module.reader, "runtime_oci_settings",
                         return_value=("oci", "n", "bucket")),
            patch.object(module.reader, "object_metadata",
                         side_effect=[dump, manifest]) as metadata,
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = module.main()
        self.assertEqual(status, 0)
        self.assertIn("MLRR_SYSTEMD_BACKUP_READBACK=PASS", output.getvalue())
        self.assertIn("restore_drill=NOT_CERTIFIED", output.getvalue())
        self.assertEqual(metadata.call_count, 2)
        self.assertEqual(
            [x.args[0] for x in metadata.call_args_list],
            [module.DUMP_OBJECT, module.DUMP_OBJECT + ".sha256"]
        )

    def test_missing_remote_evidence_fails_without_fallback_writer(self):
        with (
            patch.object(module, "validate_single_writer"),
            patch.object(module.reader, "latest_service_completion",
                         return_value=datetime.now(timezone.utc)),
            patch.object(module.reader, "runtime_oci_settings",
                         return_value=("oci", "n", "bucket")),
            patch.object(module.reader, "object_metadata",
                         side_effect=module.reader.VerificationError(
                             "OCI_OBJECT_METADATA_INVALID"
                         )),
        ):
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                status = module.main()
        self.assertEqual(status, 2)
        self.assertIn("MLRR_SYSTEMD_BACKUP_READBACK=FAIL", output.getvalue())
        self.assertNotIn("PASS", output.getvalue())


if __name__ == "__main__":
    unittest.main()
