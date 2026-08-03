from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24349_structural_semantic_runtime import (  # noqa: E402
    run_v24349_task,
    run_v24349_total_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import (  # noqa: E402
    BASELINE_UNKNOWN,
    Clock,
    Model,
    Search,
    TASK,
    limits,
)


DUPLICATE_BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha-A | Unknown |
| Alpha A | 2024 |
```"""
CONFLICT_BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha-A | 2023 |
| Alpha A | 2024 |
```"""


class V24349StructuralSemanticRuntimeTests(unittest.TestCase):
    def run_case(self, *, baseline: str, eligible: bool = False):
        value = run_v24349_task(
            TASK,
            model=Model(baseline=baseline),
            search=Search(eligible=eligible),
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value

    def test_duplicate_baseline_is_normalized_without_total_fallback(self) -> None:
        value = self.run_case(baseline=DUPLICATE_BASELINE)
        core = value["semantic_result"]["core_result"]
        self.assertTrue(core["shared_prefix_revision_receipt"]["effect_accounting_complete"])
        self.assertEqual(core["completion_kind"], "identity_no_reserve")
        self.assertIn("| Alpha A | 2024 |", core["baseline_prediction"])
        self.assertNotIn("| Alpha-A |", core["baseline_prediction"])
        receipt = value["structural_receipt"]["normalization_receipt"]
        self.assertEqual(receipt["duplicate_identity_group_count"], 1)
        self.assertEqual(receipt["consensus_filled_unknown_cell_count"], 0)

    def test_conflicting_duplicate_value_becomes_unknown(self) -> None:
        value = self.run_case(baseline=CONFLICT_BASELINE)
        baseline = value["semantic_result"]["core_result"]["baseline_prediction"]
        self.assertIn("| Alpha-A | Unknown |", baseline)
        receipt = value["structural_receipt"]["normalization_receipt"]
        self.assertEqual(receipt["conflicting_known_cell_count"], 1)
        self.assertFalse(receipt["conflicting_known_value_selected_as_truth"])

    def test_unique_baseline_preserves_existing_semantic_admission(self) -> None:
        value = self.run_case(baseline=BASELINE_UNKNOWN, eligible=True)
        semantic = value["semantic_result"]
        self.assertIn("| Alpha | 2025 |", semantic["core_result"]["candidate_prediction"])
        self.assertEqual(semantic["semantic_active_receipt"]["admitted_cell_changes"], 1)
        self.assertGreater(
            semantic["semantic_active_receipt"]["credited_conditional_entropy_reduction_nats"],
            0,
        )
        self.assertEqual(
            value["structural_receipt"]["normalization_receipt"][
                "duplicate_identity_group_count"
            ],
            0,
        )

    def test_structural_normalization_is_shared_not_candidate_only(self) -> None:
        value = self.run_case(baseline=DUPLICATE_BASELINE)
        receipt = value["structural_receipt"]
        self.assertTrue(receipt["normalization_applied_to_shared_baseline_before_arm_branch"])
        self.assertTrue(receipt["same_normalized_baseline_for_baseline_and_candidate"])
        self.assertTrue(receipt["candidate_only_adds_semantic_support_and_entropy_gate"])
        core = value["semantic_result"]["core_result"]
        self.assertEqual(core["baseline_prediction"], core["candidate_prediction"])
        semantic = value["semantic_result"]["semantic_active_receipt"]
        self.assertTrue(semantic["baseline_and_candidate_share_exact_raw_pages"])
        self.assertEqual(
            semantic["baseline_active_evidence_sha256"],
            semantic["candidate_active_evidence_sha256"],
        )

    def test_duplicate_normalization_keeps_frozen_effect_budget(self) -> None:
        model = Model(baseline=DUPLICATE_BASELINE)
        search = Search(eligible=False)
        value = run_v24349_task(
            TASK,
            model=model,
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        core = value["semantic_result"]["core_result"]
        receipt = core["shared_prefix_revision_receipt"]
        self.assertEqual(model.requests, 2)
        self.assertEqual(search.calls, 1)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(receipt["logical_model_admissions"], 2)
        self.assertEqual(receipt["provider_model_requests"], 2)
        self.assertEqual(receipt["core_logical_queries"], 4)
        self.assertEqual(receipt["core_fetch_targets"], 7)
        self.assertEqual(receipt["reserve_fetch_targets"], 3)

    def test_private_normalization_or_receipt_tamper_fails_replay(self) -> None:
        value = self.run_case(baseline=DUPLICATE_BASELINE)
        for field in ("private", "receipt"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "private":
                    altered["structural_private_state"]["normalization_result"][
                        "normalized_table"
                    ] += " "
                else:
                    altered["structural_receipt"]["normalization_receipt"][
                        "merged_duplicate_row_count"
                    ] = 0
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_total_fallback_preserves_content_free_structural_stage(self) -> None:
        class BrokenTableModel(Model):
            def complete(self, *args, **kwargs):
                value = super().complete(*args, **kwargs)
                if len(self.prompts) == 2:
                    value.text = "not a table"
                return value

        value = run_v24349_total_task(
            TASK,
            model=BrokenTableModel(),
            search=Search(eligible=False),
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        semantic = value["semantic_result"]
        # The synthetic recovery call also fails to return a table. The total
        # fallback must retain a fixed content-free structural stage.
        self.assertFalse(
            semantic["core_result"]["shared_prefix_revision_receipt"][
                "effect_accounting_complete"
            ]
        )
        stage = value["structural_receipt"]["content_free_stage_receipt"]
        self.assertEqual(stage["stage"], "baseline_table_parse")
        self.assertEqual(stage["reason"], "table_parse_rejected")
        self.assertEqual(stage["model_requests_lower_bound"], 3)

    def test_public_receipt_is_content_free_and_label_blind(self) -> None:
        value = self.run_case(baseline=DUPLICATE_BASELINE)
        encoded = json.dumps(value["structural_receipt"], ensure_ascii=False)
        self.assertNotIn("Alpha", encoded)
        self.assertNotIn("2024", encoded)
        self.assertFalse(
            value["structural_receipt"][
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )

    def test_privileged_key_is_rejected_before_any_effect(self) -> None:
        model = Model(baseline=DUPLICATE_BASELINE)
        search = Search(eligible=False)
        with self.assertRaises(ValueError):
            run_v24349_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_process_control_exception_is_not_converted_to_prediction(self) -> None:
        class InterruptSearch(Search):
            def search_many(self, *args, **kwargs):
                del args, kwargs
                raise KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            run_v24349_total_task(
                TASK,
                model=Model(baseline=DUPLICATE_BASELINE),
                search=InterruptSearch(eligible=False),
                limits=limits(),
                monotonic=Clock(),
            )


if __name__ == "__main__":
    unittest.main()
