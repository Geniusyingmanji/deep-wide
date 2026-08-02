from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import run_v24260_score_first_smoke as runner  # noqa: E402


class V24260ImportBootstrapTests(unittest.TestCase):
    def test_frozen_child_fails_and_successor_help_succeeds_under_isolation(self) -> None:
        failed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / "scripts/run_v24259_score_first_task.py"), "--help"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        repaired = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / runner.CHILD), "--help"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn(b"No module named 'scripts'", failed.stderr)
        self.assertEqual(repaired.returncode, 0)
        self.assertEqual(repaired.stderr, b"")

    def test_successor_changes_only_child_entrypoint(self) -> None:
        protocol = {
            "provider_contract": {
                "model": {"proxy_url": "u", "name": "m", "reasoning_effort": "low", "service_tier": "p", "timeout_seconds": 1, "max_retries": 1},
                "search": {"model": "s", "timeout_seconds": 1, "max_retries": 1, "workers": 1, "fetch_workers": 1, "fetch_timeout_seconds": 1},
            },
            "limits": {"wall_seconds": 600, "model_calls": 3, "search_queries": 8, "fetch_targets": 16, "search_results_per_query": 3, "evidence_chars": 100000, "page_chars": 5000},
        }
        paths = [Path("a"), Path("b"), Path("c")]
        parent = runner.parent._task_command(ROOT, protocol, *paths)
        successor = runner._task_command(ROOT, protocol, *paths)
        self.assertEqual(parent[:3], successor[:3])
        self.assertNotEqual(parent[3], successor[3])
        self.assertEqual(parent[4:], successor[4:])


if __name__ == "__main__":
    unittest.main()
