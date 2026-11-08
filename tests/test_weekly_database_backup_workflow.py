"""Regression for single-writer, fail-closed weekly database backup orchestration."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/weekly-database-backups.yml"
BACKUP_COMMAND = "python3 scripts/ops/shopvivaliz-db-backup.py"
SECONDARY_VERIFY_COMMAND = "python3 scripts/verify-mlrr-systemd-backup.py"
VERIFY_COMMAND = "python3 scripts/verify-mei-systemd-backup.py"


class WeeklyDatabaseBackupContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.main = cls.text.split("\n  main-host:\n", 1)[1].split(
            "\n  secondary-host:\n", 1
        )[0]
        cls.secondary = cls.text.split("\n  secondary-host:\n", 1)[1]

    @classmethod
    def steps(cls):
        return re.findall(
            r"(?ms)^      - name: ([^\n]+)\n(.*?)(?=^      - name: |\Z)",
            cls.main,
        )

    def test_main_job_has_two_local_targets_and_read_only_mei_verification(self):
        steps = self.steps()
        self.assertEqual(len(steps), 4)
        self.assertIn("uses: actions/checkout@v6", steps[0][1])
        self.assertIn("persist-credentials: false", steps[0][1])
        for index, target in ((1, "solange-production"), (2, "solange-staging")):
            self.assertIn(
                "run: " + BACKUP_COMMAND + " --profile main --target " + target,
                steps[index][1],
            )
        self.assertIn("run: " + VERIFY_COMMAND, steps[3][1])
        self.assertEqual(self.main.count("run: " + BACKUP_COMMAND), 2)
        self.assertNotIn("--target mei-email", self.main)
        self.assertTrue((ROOT / "scripts/verify-mei-systemd-backup.py").is_file())

    def test_unrelated_failures_do_not_suppress_next_step_or_mask_job(self):
        steps = self.steps()
        self.assertEqual(len(steps), 4)
        for _, body in steps[2:]:
            self.assertIn("if: ${{ !cancelled() }}", body)
        for forbidden in ("continue-on-error:", "|| true", "always()", "set +e"):
            self.assertNotIn(forbidden, self.main)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_single_writer_schedule_and_secondary_profile_unchanged(self):
        # The systemd Mei backup timer runs every Sunday 04:30 UTC;
        # this workflow must not upload the same key simultaneously.
        for contract in (
            "cron: '15 6 * * 0'",
            "workflow_dispatch:",
            "runs-on: [self-hosted, mei-backend]",
            "runs-on: [self-hosted, mei-ci]",
            "timeout-minutes: 60",
            "timeout-minutes: 30",
            "group: weekly-database-backups",
            "run: " + SECONDARY_VERIFY_COMMAND,
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.text)
        self.assertEqual(self.text.count(BACKUP_COMMAND), 2)
        self.assertEqual(self.text.count(SECONDARY_VERIFY_COMMAND), 1)
        self.assertNotIn("/home/ubuntu/.local/bin/shopvivaliz-db-backup.py", self.secondary)
        self.assertIn("uses: actions/checkout@v6", self.secondary)
        self.assertIn("persist-credentials: false", self.secondary)

    def test_secondary_runner_only_attests_an_existing_MLRR_systemd_writer(self):
        self.assertIn("runs-on: [self-hosted, mei-ci]", self.secondary)
        self.assertIn("run: " + SECONDARY_VERIFY_COMMAND, self.secondary)
        self.assertNotIn("--profile secondary", self.secondary)
        self.assertNotIn("continue-on-error:", self.secondary)
        verifier = (ROOT / "scripts/verify-mlrr-systemd-backup.py").read_text(
            encoding="utf-8")
        for needed in ("marina-a1-4c24g", "mlrr-phase3",
                       "db-backups/secondary/mlrr-phase3-latest.dump",
                       "/usr/local/sbin/shopvivaliz-db-backup.py",
                       "MLRR_SYSTEMD_BACKUP_READBACK=PASS",
                       "MLRR_SYSTEMD_BACKUP_READBACK=FAIL"):
            with self.subTest(needed=needed):
                self.assertIn(needed, verifier)
        for forbidden in ('"object", "put"', "pg_dump", "docker exec",
                          "systemctl restart"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, verifier)

    def test_verifier_never_runs_backup_or_writes_remote_objects(self):
        script = (ROOT / "scripts/verify-mei-systemd-backup.py").read_text(
            encoding="utf-8"
        )
        for allowed in (
            "shopvivaliz-db-backup.service",
            "shopvivaliz-db-backup.timer",
            "instance_principal",
            "last-modified",
            "content-length",
            "sha256",
            "READBACK=PASS",
            "READBACK=FAIL",
        ):
            with self.subTest(marker=allowed):
                self.assertIn(allowed, script)
        for forbidden in (
            "os object put", '"object", "put"', "pg_dump", "docker exec",
            "systemctl restart",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
