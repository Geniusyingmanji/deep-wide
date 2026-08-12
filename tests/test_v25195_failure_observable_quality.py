from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25192_content_free_outer_failure_observer as failure_observer,
)
from deepwide_agent import (  # noqa: E402
    v25195_failure_observable_quality_contract as contract,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts import run_v25195_failure_observable_quality as runner  # noqa: E402
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    EscapedProductionModel,
    NO_GAIN_CONTENT,
)


class V25195FailureObservableQualityTests(unittest.TestCase):
    def _row(self, opaque_id: str) -> dict:
        question = (
            "Retrieve one record. Return exactly one Markdown table and no prose. "
            "Columns exactly: Domain | Type | TLD Manager."
        )
        task = {"opaque_id": opaque_id, "question": question}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            model = runner.accounting._EffectAccountingModelSlotLimiter(
                EscapedProductionModel(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(
                    question, phase, content=NO_GAIN_CONTENT
                )
                for phase in contract.runtime.PHASES
            }
            for client in searches.values():
                client.actual_search_invocations = 0
                client.actual_logical_query_count = 0
                client.actual_fetch_invocations = 0
                client.actual_fetch_request_count = 0
                original_search = client.search_many
                original_fetch = client.fetch_urls

                def search_many(
                    queries,
                    _original=original_search,
                    _client=client,
                    **kwargs,
                ):
                    values = list(queries)
                    _client.actual_search_invocations += 1
                    _client.actual_logical_query_count += len(values)
                    return _original(values, **kwargs)

                def fetch_urls(
                    requests, _original=original_fetch, _client=client
                ):
                    values = list(requests)
                    _client.actual_fetch_invocations += 1
                    _client.actual_fetch_request_count += len(values)
                    return _original(values)

                client.search_many = search_many
                client.fetch_urls = fetch_urls
            value = contract.runtime.run_task(
                task,
                model=model,
                searches=searches,
                limits=ScoreFirstLimits(**contract.LIMITS),
                monotonic=lambda: 100.0,
            )
            row = runner._from_runtime(
                task,
                value,
                1.0,
                runner.accounting._health(),
                runner.accounting._actual_effect_snapshot(model, searches),
            )
        return runner.validate_task_row(row)

    def test_fresh_visible_population_and_parent_no_go_are_bound(self) -> None:
        tasks = contract.task_vector()
        selection = contract.validate_selection(ROOT, tracked=True)
        parent = contract._validate_parent(ROOT, tracked=True)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(selection["identity_history_zero_hit_count"], 20)
        self.assertEqual(parent["frozen_failure_as_zero_tasks"], 15)
        self.assertFalse(parent["mechanism_gate_passed"])
        self.assertFalse(parent["evaluator_authorized"])
        for task, package in zip(tasks, contract.PACKAGES, strict=True):
            self.assertIn(f"<PACKAGE>{package}</PACKAGE>", task["question"])
            self.assertNotIn(r"\|", task["question"])
            self.assertNotIn("https://", task["question"])

    def test_success_row_has_no_failure_observation_and_is_effect_bound(self) -> None:
        row = self._row(contract.task_vector()[0]["opaque_id"])
        receipt = row["content_free_receipt"]
        self.assertTrue(row["runtime_completed"])
        self.assertIsNone(row["failure_observation"])
        self.assertTrue(receipt["same_raw_counterfactual_active"])
        self.assertTrue(receipt["prediction_changed"])
        sparse = row["parent_result"]["parent_result"]["parent_result"][
            "parent_result"
        ]
        self.assertEqual(
            row["actual_effect_snapshot"]["model_logical_requests"],
            sparse["content_free_receipt"]["provider_forward_count"],
        )

    def test_terminal_failure_retains_only_valid_stage_and_code(self) -> None:
        task = contract.task_vector()[0]
        observation = failure_observer.observe_outer_failure(
            ValueError("V2.51.88 parent/counterfactual binding drifted"),
            outer_failure_stage="conversion",
        )
        row = runner._terminal_outer_failure(task, observation, 1.0)
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["failure_as_zero"])
        self.assertEqual(
            checked["failure_observation"]["failure_code"],
            "v25188_parent_counterfactual_binding",
        )
        self.assertEqual(
            checked["failure_observation"]["outer_failure_stage"],
            "conversion",
        )
        encoded = json.dumps(checked)
        self.assertNotIn("parent/counterfactual binding drifted", encoded)

    def test_fixed_denominator_effect_budgets_do_not_shrink_on_failure(self) -> None:
        aggregate = {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 19,
            "failure_as_zero_tasks": 1,
            "model_generated_tasks": 19,
            "fallback_tasks": 0,
            "same_raw_counterfactual_active_tasks": 19,
            "prediction_changed_tasks": 19,
            "parent_safe_public_export_failure_tasks": 0,
            "parent_safe_public_export_fallback_tasks": 0,
            "unsafe_public_export_failure_tasks": 0,
            "additional_effect_tasks": 0,
            "physical_queries": 80,
            "physical_fetches": 280,
            "physical_model_forwards": 60,
            "model_provider_requests": 60,
            "model_provider_attempts": 60,
            "model_provider_successes": 60,
            "system_total_tokens": 100,
            "content_free_receipt_valid_tasks": 19,
            "outer_or_accounting_failure_tasks": 1,
            "outer_failure_stage_counts": {
                "runtime": 1,
                "conversion": 0,
                "row_validation": 0,
            },
            "outer_failure_code_counts": {
                "unclassified_value_error": 1
            },
            "terminal_effect_hard_failures": 0,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
        }
        checked = runner.validate_aggregate(aggregate)
        decision = runner.mechanism_decision(checked)
        self.assertTrue(
            decision["checks"]["exact_fixed_denominator_query_budget"]
        )
        self.assertTrue(
            decision["checks"]["fixed_denominator_fetch_cap_preserved"]
        )
        self.assertTrue(decision["checks"]["failure_observability_complete"])
        self.assertFalse(decision["checks"]["all_runtime_tasks_completed"])

    def test_synthetic_full_denominator_passes_mechanism_gate(self) -> None:
        rows = [self._row(task["opaque_id"]) for task in contract.task_vector()]
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["physical_queries"], 80)
        self.assertEqual(
            aggregate["outer_failure_stage_counts"],
            {"runtime": 0, "conversion": 0, "row_validation": 0},
        )
        self.assertEqual(aggregate["outer_failure_code_counts"], {})
        self.assertTrue(decision["same_response_mechanism_gate_passed"])
        self.assertTrue(decision["postfreeze_external_evaluator_design"])
        self.assertFalse(decision["external_evaluator_now"])

    def test_failure_observation_or_signed_credit_tamper_fails_closed(self) -> None:
        task = contract.task_vector()[0]
        observation = failure_observer.observe_outer_failure(
            RuntimeError("dynamic"), outer_failure_stage="runtime"
        )
        row = runner.validate_task_row(
            runner._terminal_outer_failure(task, observation, 1.0)
        )
        for kind in ("observation", "credit", "prediction"):
            changed = copy.deepcopy(row)
            if kind == "observation":
                changed["failure_observation"]["failure_code"] = "unsafe"
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            else:
                changed["predictions"][contract.CANDIDATE_ARM] = "changed"
                changed["prediction_sha256"][contract.CANDIDATE_ARM] = (
                    hashlib.sha256(b"changed").hexdigest()
                )
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(
                (RuntimeError, ValueError)
            ):
                runner.validate_task_row(changed)

    def test_forward_closure_is_label_blind_secret_free_and_evaluator_free(self) -> None:
        privileged = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        closure = contract.forward_dependency_closure(ROOT)
        self.assertIn(contract.FAILURE_OBSERVER, closure)
        self.assertIn(contract.STAGED_EXECUTION, closure)
        for relative in closure:
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(relative))
            hits = {
                str(node.slice.value)
                for node in ast.walk(tree)
                if isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in privileged
            }
            self.assertEqual(hits, set(), relative)
            self.assertIsNone(contract.SECRET.search(source), relative)
        self.assertFalse((ROOT / contract.EVALUATOR).exists())


if __name__ == "__main__":
    unittest.main()
