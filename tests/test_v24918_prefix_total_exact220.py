from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24914_cap_bound_long_page_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24918_prefix_total_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24913_cap_bound_long_page_fetch import CapBoundLongPageSearchClient  # noqa: E402
from deepwide_agent.v24916_prefix_total_long_page_packer import OVERFLOW_MESSAGE  # noqa: E402
from scripts import control_v24918_prefix_total_exact220 as control  # noqa: E402
from scripts import finalize_v24918_prefix_total_exact220 as finalizer  # noqa: E402
from scripts import run_v24635_exact220 as scheduler  # noqa: E402
from scripts import run_v24635_exact220_task as task_algorithm  # noqa: E402
from scripts import run_v24918_prefix_total_exact220 as runner  # noqa: E402
from scripts import run_v24918_prefix_total_exact220_task as child  # noqa: E402


class V24918PrefixTotalExact220Tests(unittest.TestCase):
    def test_only_projection_totality_changes_from_parent(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)

    def test_exact_capacity_and_hard_call_caps(self) -> None:
        self.assertEqual(
            (contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP),
            (220, 20, 8),
        )
        self.assertEqual(contract.LIMITS["wall_seconds"], 240)

    def test_task_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_runner_and_child_bind_fresh_namespace_and_12k_fetch(self) -> None:
        runner.configure()
        runner.base.configure_algorithm()
        self.assertEqual(scheduler.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(scheduler.CHILD_MARKER, contract.CHILD_MARKER)
        child.configure()
        self.assertEqual(task_algorithm.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(task_algorithm.LIMITS["page_chars"], 12_000)
        self.assertIs(
            task_algorithm.ThinSameResponseCitationTitleBackfillSearchClient,
            CapBoundLongPageSearchClient,
        )

    def test_single_change_is_exact_overflow_totality(self) -> None:
        value = contract._single_change()
        self.assertEqual(value["field"], "structural_projection_cap_totality")
        self.assertFalse(value["unrelated_exception_swallowed"])
        self.assertFalse(value["entropy_or_information_gain_used_for_credit_or_routing"])
        self.assertIn("structural selection exceeded", OVERFLOW_MESSAGE)

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        control.configure()
        self.assertEqual(control.base._runtime_findings(), ([], [], []))

    def test_finalizer_and_create_only_surfaces_are_fresh(self) -> None:
        finalizer.configure()
        self.assertIn("v24918_prefix_total", str(finalizer.parent.base.FINAL_RESULT))
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.base.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.base.publish_new(path, {})

    def test_protocol_rejects_privileged_runtime_input_contract(self) -> None:
        tasks = contract.task_vector(ROOT)
        value = {
            "task_contract": {
                "runtime_input_keys": ["opaque_id", "question"],
                "selected_count": 220,
                "opaque_id_vector_sha256": contract.payload_sha256(
                    [task["opaque_id"] for task in tasks]
                ),
                "visible_question_vector_sha256": contract.payload_sha256(
                    [task["question"] for task in tasks]
                ),
            }
        }
        altered = copy.deepcopy(value)
        altered["task_contract"]["runtime_input_keys"].append("question_type")
        with self.assertRaises(RuntimeError):
            contract.task_vector(ROOT, altered)

    def test_build_audit_is_valid_and_label_blind(self) -> None:
        value = contract._validate_build_audit(ROOT)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])


if __name__ == "__main__":
    unittest.main()
