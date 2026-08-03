from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import run_observed_subprocess  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import validate_receipt  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24318_deadline_conservation_runtime import MODEL_FIELD  # noqa: E402
from deepwide_agent.v24319_runner_integration import validate_envelope  # noqa: E402


FIXTURE = ROOT / "tests/fixtures/v24319_synthetic_child.py"
MODES = {
    "success_baseline": ("success", "baseline", "success"),
    "success_candidate": ("success", "candidate", "success"),
    "slot_reject": ("slot_reject", "candidate", "success"),
    "cache_defer_baseline": ("cache_defer", "baseline", "success"),
    "cache_defer_candidate": ("cache_defer", "candidate", "success"),
    "nonzero": ("nonzero", "candidate", "child_nonzero_with_terminal_receipt"),
    "timeout": ("timeout", "candidate", "hard_deadline_timeout"),
    "missing_result": ("missing_result", "candidate", "zero_exit_missing_result_envelope"),
    "invalid_result": ("invalid_result", "candidate", "result_envelope_invalid"),
    "missing_model": ("missing_model", "candidate", "model_receipt_missing_or_invalid"),
    "missing_transport": ("missing_transport", "candidate", "transport_receipt_missing_or_invalid"),
}


def environment() -> dict[str, str]:
    return {
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def write_new(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def slots(output: Path) -> Path:
    value = output / "slots"
    value.mkdir()
    for index in range(1, 3):
        write_new(value / f"slot_{index:02d}.lock", {"slot": index})
    return value


def run_matrix() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
        output = Path(temporary)
        slot_root = slots(output)
        for name, (mode, arm, expected) in MODES.items():
            directory = output / name
            directory.mkdir()
            task = {
                "opaque_id": "task_0123456789abcdef01234567",
                "question": "Return one table. The column names are: Name, Date.",
            }
            write_new(directory / "visible_task.json", task)
            result = directory / "result.json"
            model = directory / "model_receipt.json"
            transport = directory / "transport_health.json"
            terminal = directory / "child_terminal_receipt.json"
            command = [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(FIXTURE),
                "--mode", mode, "--arm", arm,
                "--task", str(directory / "visible_task.json"),
                "--result", str(result),
                "--model-receipt", str(model),
                "--transport", str(transport),
                "--terminal", str(terminal),
                "--slots", str(slot_root),
                "--output-root", str(output),
            ]
            observed = run_observed_subprocess(
                cwd=ROOT,
                output_root=output,
                directory=directory,
                command=command,
                environment=environment(),
                timeout_seconds=0.4 if mode == "timeout" else 4.0,
                result_validator=validate_envelope,
                model_receipt_validator=lambda value: validate_receipt(value, expected_cap=2),
                transport_receipt_validator=validate_transport_health,
                result_name=result.name,
                model_receipt_name=model.name,
                transport_receipt_name=transport.name,
                terminal_name=terminal.name,
                parent_name="parent_exit_receipt.json",
            )
            parent = validate_parent_receipt(observed.receipt)
            rows[name] = {"expected": expected, "parent": parent}
            if expected == "success":
                envelope = json.loads(result.read_text(encoding="utf-8"))
                validate_envelope(envelope)
                rows[name]["logical"] = envelope["result"][MODEL_FIELD]["logical_admissions_total"]
                rows[name]["requests"] = envelope["result"][MODEL_FIELD]["provider_requests_total"]
                rows[name]["rejected"] = envelope["result"][MODEL_FIELD]["pre_provider_rejections_total"]
    return rows


class V24319SubprocessIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = run_matrix()

    def test_all_eleven_parent_taxonomies_are_exact(self) -> None:
        self.assertEqual(set(self.rows), set(MODES))
        self.assertEqual(
            {name: row["parent"]["failure_taxonomy"] for name, row in self.rows.items()},
            {name: expected for name, (_, _, expected) in MODES.items()},
        )

    def test_deadline_stops_are_complete_success_envelopes(self) -> None:
        for name in ("slot_reject", "cache_defer_baseline", "cache_defer_candidate"):
            parent = self.rows[name]["parent"]
            self.assertTrue(parent["child_terminal_receipt_valid"])
            self.assertTrue(parent["result_envelope_valid"])
            self.assertTrue(parent["model_receipt_valid"])
            self.assertTrue(parent["transport_receipt_valid"])
        self.assertGreater(self.rows["slot_reject"]["rejected"], 0)
        self.assertEqual(
            self.rows["slot_reject"]["logical"],
            self.rows["slot_reject"]["requests"] + self.rows["slot_reject"]["rejected"],
        )

    def test_structural_failures_never_masquerade_as_success(self) -> None:
        for name in (
            "nonzero", "timeout", "missing_result", "invalid_result", "missing_model", "missing_transport"
        ):
            self.assertNotEqual(self.rows[name]["parent"]["failure_taxonomy"], "success")


if __name__ == "__main__":
    unittest.main()
