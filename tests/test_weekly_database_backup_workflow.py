"""Regression for independent, fail-closed weekly database backup steps."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/weekly-database-backups.yml"
BACKUP_COMMAND = "/home/ubuntu/.local/bin/shopvivaliz-db-backup.py"


class WeeklyDatabaseBackupContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.main = cls.text.split("\n  main-host:\n", 1)[1].split(
            "\n  secondary-host:\n", 1
        )[0]
        cls.secondary = cls.text.split("\n  secondary-host:\n", 1)[1]

    def test_three_independent_targets_are_attempted_exactly_once(self):
        steps = re.findall(
            r"(?ms)^      - name: ([^\n]+)\n(.*?)(?=^      - name: |\Z)",
            self.main,
        )
        self.assertEqual(len(steps), 3)
        targets = ("solange-production", "solange-staging", "mei-email")
        for (_, body), target in zip(steps, targets):
            self.assertIn(
                "run: " + BACKUP_COMMAND + " --profile main --target " + target,
                body,
            )
            self.assertEqual(body.count("run: " + BACKUP_COMMAND), 1)
        self.assertEqual(
            [re.search(r"--target ([^\s]+)", s[1]).group(1) for s in steps],
            list(targets),
        )
        self.assertNotIn("run: " + BACKUP_COMMAND + " --profile main\n", self.main)

    def test_later_targets_run_after_prior_failure_but_cannot_mask_it(self):
        steps = re.findall(
            r"(?ms)^      - name: ([^\n]+)\n(.*?)(?=^      - name: |\Z)",
            self.main,
        )
        self.assertEqual(len(steps), 3)
        for _, body in steps[1:]:
            self.assertIn("if: ${{ !cancelled() }}", body)
        for forbidden in ("continue-on-error:", "|| true", "always()", "set +e"):
            self.assertNotIn(forbidden, self.main)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_runners_schedule_and_other_profile_unchanged(self):
        for contract in (
            "cron: '30 4 * * 0'",
            "workflow_dispatch:",
            "runs-on: [self-hosted, mei-backend]",
            "runs-on: [self-hosted, mei-ci]",
            "timeout-minutes: 60",
            "timeout-minutes: 30",
            "group: weekly-database-backups",
            "run: " + BACKUP_COMMAND + " --profile secondary",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.text)
        self.assertEqual(self.text.count(BACKUP_COMMAND), 4)


if __name__ == "__main__":
    unittest.main()
