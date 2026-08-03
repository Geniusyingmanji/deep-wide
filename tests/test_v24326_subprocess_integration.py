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

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_observed_subprocess,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24326_runner_integration import (  # noqa: E402
    validate_envelope,
    validate_observed_bundle,
)


FIXTURE = ROOT / "tests/fixtures/v24326_synthetic_child.py"
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": (
        "Use web evidence to complete the table. The column names are: Name, Year. "
        "Return one Markdown table only."
    ),
}
MODES = {
    "success": "success",
    "slot_reject": "success",
    "reserve_failure": "success",
    "nonzero": "child_nonzero_with_terminal_receipt",
    "timeout": "hard_deadline_timeout",
    "missing_result": "zero_exit_missing_result_envelope",
    "missing_model": "model_receipt_missing_or_invalid",
    "missing_transport": "transport_receipt_missing_or_invalid",
    "invalid_result": "result_envelope_invalid",
    "drift_model": "result_envelope_invalid",
    "drift_transport": "result_envelope_invalid",
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


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def run_matrix() -> dict[str, dict]:
    output: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
        root = Path(temporary)
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 3):
            write(slots / f"slot_{index:02d}.lock", {"slot": index})
        task = root / "visible_task.json"
        write(task, TASK)
        for mode, expected in MODES.items():
            directory = root / mode
            directory.mkdir()
            result = directory / "result.json"
            model = directory / "model_slot_receipt.json"
            transport = directory / "transport_health.json"
            terminal = directory / "child_terminal_receipt.json"

            def validate_result(value, *, model=model, transport=transport):
                envelope = validate_envelope(value)
                if not model.is_file() or not transport.is_file():
                    return envelope
                try:
                    model_value = json.loads(model.read_text(encoding="utf-8"))
                    transport_value = json.loads(
                        transport.read_text(encoding="utf-8")
                    )
                    validate_model_receipt(model_value, expected_cap=2)
                    validate_transport_health(transport_value)
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    return envelope
                return validate_observed_bundle(
                    envelope,
                    model_slot_receipt=model_value,
                    transport_health=transport_value,
                    expected_cap=2,
                )

            observed = run_observed_subprocess(
                cwd=ROOT,
                output_root=root,
                directory=directory,
                command=[
                    str(ROOT / ".venv-eval/bin/python"),
                    "-I",
                    "-B",
                    str(FIXTURE),
                    "--mode",
                    mode,
                    "--task",
                    str(task),
                    "--result",
                    str(result),
                    "--model-receipt",
                    str(model),
                    "--transport",
                    str(transport),
                    "--terminal",
                    str(terminal),
                    "--slots",
                    str(slots),
                    "--output-root",
                    str(root),
                ],
                environment=environment(),
                timeout_seconds=0.35 if mode == "timeout" else 4.0,
                result_validator=validate_result,
                model_receipt_validator=lambda value: validate_model_receipt(
                    value, expected_cap=2
                ),
                transport_receipt_validator=validate_transport_health,
                result_name=result.name,
                model_receipt_name=model.name,
                transport_receipt_name=transport.name,
                terminal_name=terminal.name,
                parent_name="parent_exit_receipt.json",
            )
            parent = validate_parent_receipt(observed.receipt)
            row = {"expected": expected, "parent": parent}
            if expected == "success":
                row["envelope"] = json.loads(result.read_text(encoding="utf-8"))
            output[mode] = row
    return output


class V24326SubprocessIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = run_matrix()

    def test_parent_taxonomy_is_exact(self) -> None:
        self.assertEqual(
            {
                mode: self.rows[mode]["parent"]["failure_taxonomy"]
                for mode in MODES
            },
            MODES,
        )

    def test_success_slot_reject_and_reserve_failure_are_complete_results(self) -> None:
        success = self.rows["success"]["envelope"]["result"]
        slot = self.rows["slot_reject"]["envelope"]["result"]
        reserve = self.rows["reserve_failure"]["envelope"]["result"]
        self.assertGreater(
            success["shared_prefix_revision_receipt"]["admitted_cell_changes"], 0
        )
        self.assertTrue(
            slot["shared_prefix_revision_receipt"]["candidate_identity_handoff"]
        )
        self.assertTrue(
            reserve["shared_prefix_revision_receipt"]["candidate_identity_handoff"]
        )

    def test_public_parent_matrix_is_content_free(self) -> None:
        public = {
            mode: self.rows[mode]["parent"]
            for mode in MODES
        }
        encoded = json.dumps(public, ensure_ascii=False)
        for forbidden in (
            TASK["opaque_id"],
            TASK["question"],
            "Alpha",
            "2025",
            "private",
        ):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
