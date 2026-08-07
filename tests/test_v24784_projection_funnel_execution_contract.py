from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24784_projection_funnel_execution_contract as target  # noqa: E402


def table(task: dict[str, str], *, changed: bool = False) -> str:
    entities = target.visible_entities(task["question"])
    return (
        "```markdown\n| Organization | Founded | Country |\n"
        "| --- | --- | --- |\n"
        + "\n".join(
            f"| {entity} | {'2001' if changed and index == 0 else 'Unknown'} | Unknown |"
            for index, entity in enumerate(entities)
        )
        + "\n```"
    )


def scheduler() -> dict:
    return {
        "same_model_query_and_total_fetch_target_caps_as_parent": True,
        "failed_url_retried": False,
        "field_label_candidate_value_or_model_judgment_used_for_reserve_routing": False,
        "actual_fetch_request_count": 10,
        "initial_fetch_request_count": 8,
        "reserve_fetch_request_count": 2,
        "initial_usable_page_count": 6,
        "reserve_usable_page_count": 2,
        "actual_usable_page_count": 8,
        "failed_url_retry_count": 0,
        "final_entities_with_two_or_more_usable_identity_sources": 2,
        "initial_usable_identity_source_count_vector": [1, 1, 2, 2],
        "final_usable_identity_source_count_vector": [2, 2, 2, 2],
        "reserve_target_entity_count": 2,
        "query_text_used_to_establish_alignment": False,
        "strict_two_independent_same_value_gate_changed": False,
    }


def semantic(*, changed: int = 1) -> dict:
    return {
        "final_changed_cell_count": changed,
        "projection_backed_eligible_support_set_count": changed,
        "new_model_search_fetch_or_evaluator_effect": 0,
        "candidate_changes_only_baseline_unknown_cells": True,
        "semantic_candidate_requires_projection_binding": True,
        "semantic_candidate_requires_two_independent_sources": True,
        "any_same_cell_value_conflict_abstains": True,
    }


def funnel_counts() -> dict:
    value = {name: 0 for name in target.FUNNEL_SUM_FIELDS}
    value.update(
        {
            "target_count": 8,
            "baseline_unknown_target_count": 8,
            "core_page_count": 6,
            "reserve_page_count": 2,
            "input_page_count": 8,
            "intact_page_count": 8,
            "page_target_pair_count": 64,
            "supported_column_pair_count": 64,
            "exact_entity_anchor_pair_count": 8,
            "target_segment_pair_count": 8,
            "explicit_relation_token_pair_count": 2,
            "parsable_relation_pair_count": 2,
            "bound_relation_pair_count": 2,
            "projection_emitted_pair_count": 2,
            "semantic_projection_count": 2,
            "distinct_target_value_projection_count": 1,
            "projection_target_binding_count": 1,
            "projection_unknown_target_value_group_count": 1,
            "projection_two_or_more_source_group_count": 1,
            "catalog_candidate_target_value_group_count": 1,
            "catalog_eligible_support_set_count": 1,
            "projection_backed_eligible_support_set_count": 1,
            "unconflicted_projection_backed_unknown_proposal_count": 1,
        }
    )
    return value


class V24784ProjectionFunnelExecutionContractTests(unittest.TestCase):
    def test_visible_tasks_and_failure_tables_are_exact(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 8)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        for task in tasks:
            entities = target.visible_entities(task["question"])
            self.assertEqual(len(entities), 4)
            columns, rows = target._baseline_matrix(target.failure_prediction(task))
            self.assertEqual(columns, list(target.EXPECTED_COLUMNS))
            self.assertEqual([row[0] for row in rows], entities)
            self.assertTrue(all(row[1:] == ["Unknown", "Unknown"] for row in rows))

    def test_observation_requires_explicit_valid_funnel_for_counts(self) -> None:
        task = target.task_vector()[0]
        result = {
            "opaque_id": task["opaque_id"],
            "status": "validated",
            "base_result_valid": True,
            "funnel_receipt_valid": True,
            "predictions": {
                "baseline": table(task),
                "staged_fallback_semantic": table(task, changed=True),
            },
            "scheduler_receipt": scheduler(),
            "semantic_receipt": semantic(),
            "projection_funnel_receipt": funnel_counts(),
        }
        with (
            patch.object(target.integration, "validate_projection", return_value=result),
            patch.object(target.funnel, "validate_receipt", return_value=result["projection_funnel_receipt"]),
        ):
            value = target.content_free_observation(result, task)
        self.assertEqual(value["changed_cell_count"], 1)
        self.assertEqual(value["funnel_counts"]["projection_emitted_pair_count"], 2)
        self.assertTrue(value["task_local_joint_projection_backed_safe_change"])
        missing = copy.deepcopy(result)
        missing.update(
            status="private_catalog_absent",
            funnel_receipt_valid=False,
            projection_funnel_receipt=None,
        )
        with patch.object(
            target.integration, "validate_projection", return_value=missing
        ):
            value = target.content_free_observation(missing, task)
        self.assertIsNone(value["funnel_counts"])
        self.assertFalse(value["task_local_joint_projection_backed_safe_change"])

    def test_forward_row_preserves_explicit_failure_status(self) -> None:
        task = target.task_vector()[0]
        predictions = target.failure_predictions(task)
        row = {
            "ordinal": 1,
            "opaque_id": task["opaque_id"],
            "predictions": predictions,
            "prediction_sha256": {
                arm: hashlib.sha256(value.encode()).hexdigest()
                for arm, value in predictions.items()
            },
            "runtime_status": "parent_failure",
            "projection_valid": False,
            "base_result_valid": False,
            "funnel_receipt_valid": False,
        }
        self.assertEqual(target.validate_forward_row(row), row)
        changed = copy.deepcopy(row)
        changed["runtime_status"] = "validated"
        changed["projection_valid"] = True
        with self.assertRaises(ValueError):
            target.validate_forward_row(changed)

    def test_summary_rejects_status_or_funnel_partition_tamper(self) -> None:
        summary = {
            "artifact_version": 1,
            "role": "v24784_projection_funnel_forward_run_summary",
            "policy_id": target.POLICY_ID,
            **{name: 0 for name in target.SUMMARY_COUNT_FIELDS},
            "selected_tasks": 8,
            "selected_arm_predictions": 16,
            "valid_projection_results": 8,
            "base_valid_task_results": 8,
            "validated_funnel_task_count": 8,
            "status_validated_count": 8,
            "projection_emitted_task_count": 1,
            "projection_backed_support_task_count": 1,
            "unconflicted_projection_backed_unknown_proposal_task_count": 1,
            "task_local_joint_projection_backed_safe_change_task_count": 1,
            "target_count": 64,
            "page_target_pair_count": 64,
            "supported_column_pair_count": 64,
            "bound_relation_pair_count": 1,
            "projection_emitted_pair_count": 1,
            "semantic_projection_count": 1,
            "distinct_target_value_projection_count": 1,
            "projection_target_binding_count": 1,
            "projection_unknown_target_value_group_count": 1,
            "projection_two_or_more_source_group_count": 1,
            "catalog_candidate_target_value_group_count": 1,
            "catalog_eligible_support_set_count": 1,
            "projection_backed_eligible_support_set_count": 1,
            "unconflicted_projection_backed_unknown_proposal_count": 1,
            "funnel_reason_counts": {
                name: (64 if name == "explicit_relation_absent" else 0)
                for name in target.funnel.REASONS
            },
            "forward_wall_seconds": 10.0,
            "experiment_wall_ceiling_seconds": 210.0,
            "within_experiment_wall_ceiling": True,
            "parent_failure_taxonomy_counts": {"success": 8},
            "all_task_ordinals_submitted_once": True,
            "resume_retry_skip_or_selective_rerun": False,
            "private_question_query_url_host_page_or_private_content_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        }
        summary["summary_payload_sha256"] = target.payload_sha256(summary)
        target.validate_run_summary(summary)
        for mutate in (
            lambda value: value.__setitem__("status_validated_count", 7),
            lambda value: value["funnel_reason_counts"].__setitem__(
                "explicit_relation_absent", 63
            ),
        ):
            changed = copy.deepcopy(summary)
            mutate(changed)
            changed.pop("summary_payload_sha256")
            changed["summary_payload_sha256"] = target.payload_sha256(changed)
            with self.assertRaises(ValueError):
                target.validate_run_summary(changed)

    def test_fixed_effect_and_authority_constants(self) -> None:
        self.assertEqual(target.EXECUTOR_CONCURRENCY, 8)
        self.assertEqual(target.MODEL_SLOT_CAP, 8)
        self.assertEqual(target.PARENT_TIMEOUT_SECONDS, 195.0)
        self.assertEqual(target.EXPERIMENT_WALL_CEILING_SECONDS, 210.0)
        self.assertEqual(
            [target.LIMITS[name] for name in ("model_calls", "search_queries", "fetch_targets")],
            [2, 4, 10],
        )
        self.assertEqual(set(target.FORWARD_STATUSES), {
            "validated", "private_catalog_absent", "base_runtime_failure",
            "funnel_validation_failure", "parent_failure",
        })

    def test_runtime_contract_source_has_no_private_or_evaluator_import(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        for marker in (
            "evaluation/",
            "population_private",
            "outputs/v24780_staged_fallback_external",
            "evaluator_mapping",
        ):
            self.assertNotIn(marker, source)
        self.assertNotIn("from evaluation", source)
        self.assertNotIn("import evaluator", source)


if __name__ == "__main__":
    unittest.main()
