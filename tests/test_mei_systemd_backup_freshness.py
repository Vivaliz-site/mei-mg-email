"""Unit tests for the read-only Mei systemd/OCI backup freshness attestation."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "mei_backup_verifier", ROOT / "scripts/verify-mei-systemd-backup.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MeiBackupFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 8, 6, 15, tzinfo=timezone.utc)
        self.finished = self.now - timedelta(hours=1, minutes=30)
        self.dump = (self.finished - timedelta(seconds=16), 1_314_755_257)
        self.checksum = (self.finished - timedelta(seconds=14), 88)

    def check_failure(self, code, *, now=None, finished=None, dump=None, checksum=None):
        with self.assertRaises(mod.VerificationError) as raised:
            mod.verify(
                now if now is not None else self.now,
                finished if finished is not None else self.finished,
                dump if dump is not None else self.dump,
                checksum if checksum is not None else self.checksum,
            )
        self.assertEqual(str(raised.exception), code)

    def test_recent_single_writer_artifact_headers_are_accepted(self):
        self.assertIsNone(mod.verify(self.now, self.finished, self.dump, self.checksum))

    def test_missing_or_short_dump_fails(self):
        self.check_failure("OCI_BACKUP_ARTIFACT_SIZE_INVALID",
                           dump=(self.dump[0], 100))

    def test_missing_checksum_manifest_fails(self):
        self.check_failure("OCI_BACKUP_ARTIFACT_SIZE_INVALID",
                           checksum=(self.checksum[0], 0))

    def test_checksum_before_dump_fails(self):
        self.check_failure("OCI_BACKUP_ARTIFACT_NOT_FRESH_OR_OUT_OF_ORDER",
                           checksum=(self.dump[0] - timedelta(seconds=1), 88))

    def test_old_remote_object_fails_even_if_service_succeeded(self):
        self.check_failure("OCI_BACKUP_ARTIFACT_NOT_FRESH_OR_OUT_OF_ORDER",
                           dump=(self.now - timedelta(days=2), self.dump[1]))

    def test_late_checksum_manifest_fails(self):
        self.check_failure("OCI_BACKUP_ATTESTATION_WINDOW_EXCEEDED",
                           dump=(self.finished - timedelta(hours=2), self.dump[1]))

    def test_failed_systemd_service_never_certifies(self):
        values = [
            "Result=failed\nExecMainStatus=1\nActiveState=inactive\n"
            "InactiveEnterTimestamp=Sun 2026-11-08 04:38:49 UTC",
            "active",
        ]
        with patch.object(mod, "command", side_effect=values):
            with self.assertRaisesRegex(
                mod.VerificationError, "BACKUP_SERVICE_NOT_COMPLETED_SUCCESSFULLY"
            ):
                mod.latest_service_completion(self.now)

    def test_stale_systemd_service_result_fails(self):
        values = [
            "Result=success\nExecMainStatus=0\nActiveState=inactive\n"
            "InactiveEnterTimestamp=Sat 2026-11-07 04:38:49 UTC",
            "active",
        ]
        with patch.object(mod, "command", side_effect=values):
            with self.assertRaisesRegex(
                mod.VerificationError, "BACKUP_SERVICE_RESULT_STALE"
            ):
                mod.latest_service_completion(self.now)

    def test_oci_metadata_requires_header_provenance(self):
        with patch.object(mod, "command", return_value=json.dumps({
            "etag": "e", "content-length": "88",
            "last-modified": "Sun, 08 Nov 2026 04:38:35 GMT",
        })):
            stamp, size = mod.object_metadata("a.sha256", ("oci", "namespace", "bucket"))
        self.assertEqual(size, 88)
        self.assertEqual(stamp.tzinfo, timezone.utc)
        with patch.object(mod, "command", return_value="{}"):
            with self.assertRaisesRegex(mod.VerificationError, "OCI_OBJECT_METADATA_INVALID"):
                mod.object_metadata("a", ("oci", "namespace", "bucket"))

    def test_host_oci_config_read_as_literals_only(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "backup.py"
            path.write_text(
                "NAMESPACE='n'\nBUCKET='b'\nOCI='/bin/sh'\n"
                "raise RuntimeError('Must not execute')\n",
                encoding="utf-8",
            )
            self.assertEqual(mod.runtime_oci_settings(path), ("/bin/sh", "n", "b"))
            path.write_text("OCI='/bin/sh'\n", encoding="utf-8")
            with self.assertRaisesRegex(mod.VerificationError, "OCI_SETTINGS_INCOMPLETE"):
                mod.runtime_oci_settings(path)


if __name__ == "__main__":
    unittest.main()
