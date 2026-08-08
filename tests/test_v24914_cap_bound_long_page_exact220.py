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

from deepwide_agent import v24909_keyless_fixed_budget_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24914_cap_bound_long_page_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24913_cap_bound_long_page_fetch import (  # noqa: E402
    CapBoundLongPageSearchClient,
)
from scripts import control_v24914_cap_bound_long_page_exact220 as control  # noqa: E402
from scripts import finalize_v24914_cap_bound_long_page_exact220 as finalizer  # noqa: E402
from scripts import run_v24635_exact220 as scheduler  # noqa: E402
from scripts import run_v24635_exact220_task as task_algorithm  # noqa: E402
from scripts import run_v24913_cap_bound_long_page_task as generic_child  # noqa: E402
from scripts import run_v24914_cap_bound_long_page_exact220 as runner  # noqa: E402
from scripts import run_v24914_cap_bound_long_page_exact220_task as child  # noqa: E402


QUESTION = (
    "Return one table with columns: Country | Target Metric.\n"
    "<COUNTRIES>Omega Republic [OMG]</COUNTRIES>"
)


class Limits:
    evidence_chars = 60_000
    page_chars = 12_000


def batches(content: str) -> list[dict]:
    return [
        {
            "results": [
                {
                    "title": "Official data",
                    "url": "https://official.example/data",
                    "raw_content": content,
                }
            ]
        }
    ]


class V24914CapBoundLongPageExact220Tests(unittest.TestCase):
    def test_only_fetch_projection_binding_changes_from_parent(self) -> None:
        self.assertEqual(
            {key: value for key, value in contract.LIMITS.items() if key != "page_chars"},
            {key: value for key, value in parent.LIMITS.items() if key != "page_chars"},
        )
        self.assertEqual((parent.LIMITS["page_chars"], contract.LIMITS["page_chars"]), (5_000, 12_000))
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)

    def test_exact_capacity_and_hard_call_caps(self) -> None:
        self.assertEqual(
            (contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP),
            (220, 20, 8),
        )
        self.assertEqual(
            {name: contract.LIMITS[name] for name in (
                "wall_seconds", "model_calls", "search_queries", "fetch_targets"
            )},
            {"wall_seconds": 240, "model_calls": 3, "search_queries": 4, "fetch_targets": 10},
        )

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

    def test_long_page_projection_recovers_late_evidence_and_receipt(self) -> None:
        evidence, receipt = generic_child.project_evidence(
            QUESTION,
            [],
            batches("boilerplate " * 600 + "\nOmega Republic [OMG]: 999"),
            Limits(),
        )
        self.assertIn("Omega Republic [OMG]: 999", evidence)
        self.assertTrue(receipt["long_page_mechanism_engaged"])

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        control.configure()
        self.assertEqual(control.base._runtime_findings(), ([], [], []))

    def test_finalizer_and_create_only_surfaces_are_fresh(self) -> None:
        finalizer.configure()
        self.assertIn("v24914_cap_bound", str(finalizer.parent.base.FINAL_RESULT))
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

    def test_single_change_requires_content_free_receipt(self) -> None:
        value = contract._single_change()
        self.assertTrue(value["to"]["content_free_receipt"])
        self.assertFalse(value["entropy_or_information_gain_used_for_credit_or_routing"])


if __name__ == "__main__":
    unittest.main()
