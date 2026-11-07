"""Contract tests for all agent entrypoints and the shared task ledger adapter."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md")
MARKER = "MANDATORY_AGENT_CHECKLIST_V1"

class AgentChecklistContractTests(unittest.TestCase):
    def test_every_agent_entrypoint_preserves_proofs_without_universal_plan_gate(self):
        for path in REQUIRED:
            with self.subTest(path=path):
                data = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn(MARKER, data)
                self.assertIn("Checklist proporcional", data)
                self.assertNotIn("## Checklist de execucao obrigatorio", data)
                self.assertIn("MFA", data)
                self.assertIn("RBAC", data)
                self.assertIn("prova", data.lower())
                if path != ".github/copilot-instructions.md":
                    self.assertIn("plan-checklist", data)
                    self.assertIn("check-step", data)
                    self.assertIn("next-step", data)

    def test_required_ci_executes_this_test_and_covers_entrypoints(self):
        path = ROOT / ".github/workflows/task-continuity-contract.yml"
        data = path.read_text(encoding="utf-8")
        self.assertIn("tests.test_agent_checklist_contract_v1", data)
        self.assertIn("tests/test_agent_checklist_contract_v1.py", data)
        self.assertIn(".github/copilot-instructions.md", data)

    def test_adapter_forwards_checked_step_to_canonical_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = Path(tmp) / "controller.py"
            controller.write_text("import json,os,sys\nprint(json.dumps({'argv':sys.argv[1:],'repository':os.environ.get('SHOPVIVALIZ_TASK_REPOSITORY')}))\n")
            env = dict(os.environ)
            env["SHOPVIVALIZ_CONTINUITY_STATE_CLI"] = str(controller)
            env["SHOPVIVALIZ_AGENT_TASK_STATE_DIR"] = tmp
            args = [sys.executable, str(ROOT / "scripts/agent_task_state.py"),
                    "check-step", "--task", "test-1", "--step-id", "1",
                    "--evidence", "artifact", "--verification", "validated"]
            completed = subprocess.run(args, env=env, text=True, capture_output=True, timeout=20)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            data = json.loads(completed.stdout)
            self.assertEqual(data["repository"], "Vivaliz-site/mei-mg-email")
            self.assertEqual(data["argv"], args[2:])

    def test_missing_canonical_controller_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["SHOPVIVALIZ_CONTINUITY_STATE_CLI"] = str(Path(tmp) / "missing.py")
            completed = subprocess.run([sys.executable, str(ROOT / "scripts/agent_task_state.py"),
                                        "plan-checklist", "--task", "test-1", "--step", "inspect"],
                                       env=env, text=True, capture_output=True, timeout=20)
            self.assertEqual(completed.returncode, 69)
            self.assertIn("global_continuity_controller_unavailable", completed.stderr)

if __name__ == "__main__":
    unittest.main()
