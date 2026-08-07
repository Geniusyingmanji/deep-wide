from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24790_cross_tab_execution_contract as target  # noqa: E402


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
    }


def semantic(*, changed: int = 1) -> dict:
    return {
        "final_changed_cell_count": changed,
        "candidate_changes_only_baseline_unknown_cells": True,
        "semantic_candidate_requires_projection_binding": True,
        "semantic_candidate_requires_two_independent_sources": True,
        "any_same_cell_value_conflict_abstains": True,
        "new_model_search_fetch_or_evaluator_effect": 0,
    }


def counts(*, strict: bool = True) -> dict[str, int]:
    value = {name: 0 for name in target.SELECTED_SUM_FIELDS}
    value.update(
        target_count=1,
        unknown_target_count=1,
        projection_group_count=1,
        unknown_projection_group_count=1,
        unknown_two_or_more_source_projection_group_count=1,
        catalog_candidate_group_count=1,
        catalog_eligible_support_set_count=1,
        projection_backed_support_group_count=1,
        unconflicted_unknown_proposal_group_count=1,
        changed_target_count=1,
        changed_to_projected_value_group_count=1,
        strict_joint_safe_change_group_count=int(strict),
    )
    return value


def selected_receipt(*, strict: bool = True) -> dict:
    local = {
        "has_unknown_projection_group": True,
        "has_unknown_two_or_more_source_projection_group": True,
        "has_projection_backed_support_group": True,
        "has_unconflicted_unknown_proposal_group": True,
        "has_changed_target": True,
        "has_strict_joint_safe_change_group": strict,
    }
    return {
        "selected_target_count": 1,
        "selected_target_is_baseline_unknown": True,
        "selected_by_canonical_row_major_order": True,
        "full_target_catalog_validated": True,
        "full_target_catalog_and_projection_vector_mutated": False,
        "single_target_catalog_rebuilt": False,
        "other_visible_entities_retained_as_segment_boundaries": True,
        "prediction_bytes_changed_by_observer": False,
        "cross_tab_receipt": {
            **counts(strict=strict),
            "task_local_joint": local,
            "same_catalog_and_predictions_observed_without_mutation": True,
            "cross_task_or_cross_group_margins_used_as_joint": False,
        },
    }


class V24790CrossTabExecutionContractTests(unittest.TestCase):
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

    def test_observation_uses_same_group_joint_receipt(self) -> None:
        task = target.task_vector()[0]
        result = {
            "opaque_id": task["opaque_id"],
            "status": "validated",
            "base_result_valid": True,
            "selected_receipt_valid": True,
            "predictions": {
                "baseline": table(task),
                "staged_fallback_semantic": table(task, changed=True),
            },
            "scheduler_receipt": scheduler(),
            "semantic_receipt": semantic(),
            "selected_cross_tab_receipt": selected_receipt(),
        }
        with (
            patch.object(target.integration, "validate_projection", return_value=result),
            patch.object(target.selected, "validate_receipt", return_value=result["selected_cross_tab_receipt"]),
        ):
            value = target.content_free_observation(result, task)
        self.assertEqual(value["selected_counts"]["strict_joint_safe_change_group_count"], 1)
        self.assertTrue(value["selected_task_local"]["has_strict_joint_safe_change_group"])
        self.assertTrue(value["selected_receipt_contract"])
        self.assertEqual(value["changed_cell_count"], 1)

    def test_missing_receipt_is_explicit_not_a_zero_cross_tab(self) -> None:
        task = target.task_vector()[0]
        result = {
            "opaque_id": task["opaque_id"],
            "status": "private_catalog_absent",
            "base_result_valid": True,
            "selected_receipt_valid": False,
            "predictions": {
                "baseline": table(task),
                "staged_fallback_semantic": table(task),
            },
            "scheduler_receipt": scheduler(),
            "semantic_receipt": semantic(changed=0),
            "selected_cross_tab_receipt": None,
        }
        with patch.object(target.integration, "validate_projection", return_value=result):
            value = target.content_free_observation(result, task)
        self.assertIsNone(value["selected_counts"])
        self.assertIsNone(value["selected_task_local"])
        self.assertFalse(value["selected_receipt_contract"])

    def test_valid_receipt_with_rebuild_attestation_fails_closed(self) -> None:
        task = target.task_vector()[0]
        receipt = selected_receipt()
        receipt["single_target_catalog_rebuilt"] = True
        result = {
            "opaque_id": task["opaque_id"],
            "status": "validated",
            "base_result_valid": True,
            "selected_receipt_valid": True,
            "predictions": {
                "baseline": table(task),
                "staged_fallback_semantic": table(task, changed=True),
            },
            "scheduler_receipt": scheduler(),
            "semantic_receipt": semantic(),
            "selected_cross_tab_receipt": receipt,
        }
        with (
            patch.object(target.integration, "validate_projection", return_value=result),
            patch.object(target.selected, "validate_receipt", return_value=receipt),
        ):
            with self.assertRaisesRegex(ValueError, "safety contract"):
                target.content_free_observation(result, task)

    def test_forward_row_preserves_explicit_parent_failure(self) -> None:
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
            "selected_receipt_valid": False,
        }
        self.assertEqual(target.validate_forward_row(row), row)
        changed = copy.deepcopy(row)
        changed.update(runtime_status="validated", projection_valid=True)
        with self.assertRaises(ValueError):
            target.validate_forward_row(changed)

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
            "validated", "no_baseline_unknown_target", "private_catalog_absent",
            "base_runtime_failure", "selected_catalog_or_observer_failure",
            "parent_failure",
        })

    def test_summary_rejects_cross_group_joint_inflation(self) -> None:
        from scripts import run_v24790_cross_tab_external as runner

        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('item["selected_task_local"][name]', source)
        self.assertNotIn(
            'has_unknown_two_or_more_source_projection_group_task_count"] > 0 and',
            source,
        )
        self.assertIn('"cross_task_or_cross_group_margins_used_as_joint": False', source)

    def test_runtime_contract_source_has_no_private_or_evaluator_import(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        for marker in ("evaluation/", "population_private", "private_truth.json", "evaluator_mapping"):
            self.assertNotIn(marker, source)
        self.assertNotIn("from evaluation", source)
        self.assertNotIn("import evaluator", source)


if __name__ == "__main__":
    unittest.main()
