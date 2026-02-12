import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "csmh-orchestrator.py"

spec = importlib.util.spec_from_file_location("csmh_orchestrator", MODULE_PATH)
orchestrator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["csmh_orchestrator"] = orchestrator
spec.loader.exec_module(orchestrator)


class OrchestratorTests(unittest.TestCase):
    def test_blocked_propagation_reverse_dependency_order(self) -> None:
        mission = {
            "objective": "blocked propagation",
            "tasks": [
                {"id": "d", "command": "echo d", "depends_on": ["c"], "writes": ["logical:d"]},
                {"id": "c", "command": "echo c", "depends_on": ["b"], "writes": ["logical:c"]},
                {"id": "b", "command": "echo b", "depends_on": ["a"], "writes": ["logical:b"]},
                {"id": "a", "command": "exit 1", "depends_on": [], "writes": ["logical:a"]},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            mission_path = Path(tmp) / "mission.json"
            mission_path.write_text(json.dumps(mission), encoding="utf-8")
            report = orchestrator.run_mission(mission_path, quiet=True)

        self.assertEqual(report["status"], "failed")
        self.assertEqual(sorted(report["failed_or_blocked"]), ["a", "b", "c", "d"])
        self.assertEqual(report["tasks"]["a"]["status"], "failed")
        self.assertEqual(report["tasks"]["b"]["status"], "blocked")
        self.assertEqual(report["tasks"]["c"]["status"], "blocked")
        self.assertEqual(report["tasks"]["d"]["status"], "blocked")

    def test_timeout_stdout_stderr_bytes_are_decoded(self) -> None:
        timeout_exc = subprocess.TimeoutExpired("demo", 0.01, output=b"partial-out", stderr=b"partial-err")
        with mock.patch.object(orchestrator.subprocess, "run", side_effect=timeout_exc):
            result = orchestrator.run_command("demo", 0.01)

        self.assertEqual(result.exit_code, 124)
        self.assertEqual(result.stdout, "partial-out")
        self.assertEqual(result.stderr, "partial-err")

    def test_timeout_float_accepted_in_task_schema(self) -> None:
        mission = {
            "objective": "float timeout",
            "tasks": [
                {
                    "id": "float-timeout",
                    "command": "echo ok",
                    "depends_on": [],
                    "writes": ["logical:float-timeout"],
                    "timeout_sec": 1.0,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            mission_path = Path(tmp) / "mission.json"
            mission_path.write_text(json.dumps(mission), encoding="utf-8")
            report = orchestrator.run_mission(mission_path, quiet=True)

        self.assertEqual(report["status"], "succeeded")

    def test_main_rejects_directory_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(MODULE_PATH), tmp],
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("mission path is not a file", proc.stdout)

    def test_retry_backoff_included_in_duration(self) -> None:
        task = orchestrator.TaskSpec(
            id="always-fail",
            command="python3 -c 'import sys; sys.exit(1)'",
            depends_on=[],
            writes=["logical:always-fail"],
            timeout_sec=None,
            retries=1,
        )
        result = orchestrator.execute_task(task)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.attempts, 2)
        self.assertGreaterEqual(result.duration_sec, 0.2)

    def test_run_phase_does_not_mutate_input_spec(self) -> None:
        spec_obj = orchestrator.TaskSpec(
            id="phase",
            command="echo phase",
            depends_on=[],
            writes=[],
            timeout_sec=1.0,
            retries=0,
        )

        result = orchestrator.run_phase("verify", spec_obj, quiet=True)

        self.assertEqual(spec_obj.id, "phase")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "verify")


if __name__ == "__main__":
    unittest.main()
