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

from deepwide_agent import v24933_contextual_record_value_projector as projector  # noqa: E402
from deepwide_agent import v24935_unicode_total_replication_contract as parent  # noqa: E402
from deepwide_agent import v24938_contextual_record_exact220_contract as contract  # noqa: E402
from scripts import control_v24938_contextual_record_exact220 as control  # noqa: E402
from scripts import finalize_v24938_contextual_record_exact220 as finalizer  # noqa: E402
from scripts import run_v24635_exact220 as scheduler  # noqa: E402
from scripts import run_v24635_exact220_task as task_algorithm  # noqa: E402
from scripts import run_v24938_contextual_record_exact220 as runner  # noqa: E402
from scripts import run_v24938_contextual_record_exact220_task as child  # noqa: E402


QUESTION = """Return exactly one Markdown table. Column names: Entity | Population [POP] @2024.
<ENTITIES>
1. Alpha Republic [ALP]
</ENTITIES>"""


def batches() -> list[dict]:
    return [
        {
            "results": [
                {
                    "title": "Official",
                    "url": "https://example.invalid/data",
                    "content": "# Population [POP] @2024\n\nAlpha Republic [ALP]: 991\nCompatibility: ½ ℃ ™",
                }
            ]
        }
    ]


class V24938ContextualRecordExact220Tests(unittest.TestCase):
    def tearDown(self) -> None:
        child._VISIBLE_QUESTION = None
        child._LAST_RECEIPT = None

    def test_only_projector_changes_from_parent(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(
            contract._single_change()["from"],
            "v24928_unicode_total_visible_row_sparse_table_compactor_v1",
        )
        self.assertEqual(contract._single_change()["to"], projector.POLICY_ID)

    def test_exact_capacity_and_hard_caps(self) -> None:
        self.assertEqual(
            (contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP),
            (220, 20, 8),
        )
        self.assertEqual(
            {name: contract.LIMITS[name] for name in ("wall_seconds", "model_calls", "search_queries", "fetch_targets")},
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

    def test_contextual_runtime_adapter_retains_bound_pair(self) -> None:
        child._VISIBLE_QUESTION = QUESTION
        limits = type("Limits", (), {"page_chars": 5000, "evidence_chars": 30000})()
        projection = child.contextual_record_evidence_projection([], batches(), limits)
        self.assertIn("Alpha Republic [ALP]: 991", projection)
        receipt = child._LAST_RECEIPT["candidate_receipt"]
        self.assertEqual(receipt["supported_contextual_target_value_pair_count"], 1)
        self.assertEqual(receipt["retained_contextual_target_value_pair_count"], 1)

    def test_unicode_totality_is_preserved(self) -> None:
        child._VISIBLE_QUESTION = QUESTION
        limits = type("Limits", (), {"page_chars": 5000, "evidence_chars": 30000})()
        child.contextual_record_evidence_projection([], batches(), limits)
        self.assertGreater(
            child._LAST_RECEIPT["unicode_total_compaction_receipt"]["nfkc_expansion_characters"],
            0,
        )

    def test_runtime_receipt_is_content_free_and_tamper_evident(self) -> None:
        child._VISIBLE_QUESTION = QUESTION
        limits = type("Limits", (), {"page_chars": 5000, "evidence_chars": 30000})()
        child.contextual_record_evidence_projection([], batches(), limits)
        receipt = child.validate_runtime_receipt(child._LAST_RECEIPT)
        self.assertFalse(receipt["contains_question_query_url_host_page_projection_prediction_or_hash"])
        self.assertFalse(receipt["mapping_gold_category_question_type_split_evaluator_score_reward_read"])
        self.assertFalse(receipt["entropy_or_information_gain_assigns_credit"])
        tampered = copy.deepcopy(receipt)
        tampered["candidate_receipt"]["retained_contextual_target_value_pair_count"] += 1
        with self.assertRaises(ValueError):
            child.validate_runtime_receipt(tampered)

    def test_external_evidence_chain_preserves_ceiling_no_go(self) -> None:
        evidence = contract._validate_evidence_chain(ROOT)
        self.assertTrue(evidence["corrected_external_mechanism_go_valid"])
        self.assertTrue(evidence["layout_diverse_external_ceiling_tie_valid"])
        self.assertFalse(evidence["external_gate_authorized_public_exact220"])

    def test_runner_and_child_bind_fresh_policy(self) -> None:
        runner.configure()
        runner.base.configure_algorithm()
        self.assertEqual(scheduler.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(scheduler.CHILD_MARKER, contract.CHILD_MARKER)
        child.configure()
        self.assertEqual(task_algorithm.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertIs(child.runtime._evidence_projection, child.contextual_record_evidence_projection)

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        control.configure()
        self.assertEqual(control.base._runtime_findings(), ([], [], []))

    def test_finalizer_and_create_only_surfaces_are_fresh(self) -> None:
        finalizer.configure()
        self.assertIn("v24938_contextual_record", str(finalizer.parent.parent.base.FINAL_RESULT))
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.base.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.base.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
