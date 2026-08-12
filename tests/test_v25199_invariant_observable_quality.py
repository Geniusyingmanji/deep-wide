from __future__ import annotations

import ast
import copy
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
    v25196_vertical_receipt_invariant_observer as invariant_observer,
)
from deepwide_agent import (  # noqa: E402
    v25199_invariant_observable_quality_contract as contract,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts import run_v25199_invariant_observable_quality as runner  # noqa: E402
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    EscapedProductionModel,
    NO_GAIN_CONTENT,
)


class V25199InvariantObservableQualityTests(unittest.TestCase):
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

    def test_fresh_population_and_exact_parent_failure_are_bound(self) -> None:
        tasks = contract.task_vector()
        selection = contract.validate_selection(ROOT, tracked=True)
        parent = contract._validate_parent(ROOT, tracked=True)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(selection["identity_history_zero_hit_count"], 20)
        self.assertFalse(selection["v25195_population_reuse"])
        self.assertEqual(parent["frozen_failure_as_zero_tasks"], 1)
        self.assertEqual(parent["failure_stage"], "runtime")
        self.assertEqual(parent["failure_code"], "v25158_receipt_validation")
        for task, package in zip(tasks, contract.PACKAGES, strict=True):
            self.assertIn(f"<PACKAGE>{package}</PACKAGE>", task["question"])
            self.assertNotIn(r"\|", task["question"])
            self.assertNotIn("https://", task["question"])

    def test_success_row_is_parent_valid_and_has_no_behavior_delta(self) -> None:
        row = self._row(contract.task_vector()[0]["opaque_id"])
        self.assertTrue(row["runtime_completed"])
        self.assertIsNone(row["failure_observation"])
        self.assertTrue(row["content_free_receipt"]["prediction_changed"])
        self.assertEqual(row["role"], runner.TASK_ROLE)

    def test_zero_failure_invariant_aggregate_and_gate_are_valid(self) -> None:
        rows = [self._row(task["opaque_id"]) for task in contract.task_vector()]
        invariant = runner.build_invariant_observation_aggregate(
            rows, [None] * contract.TASK_COUNT
        )
        self.assertEqual(invariant["violation_code_counts"], {})
        self.assertEqual(invariant["v25158_receipt_failure_tasks"], 0)
        aggregate = runner.aggregate_rows(
            rows, wall_seconds=2.0, invariant_aggregate=invariant
        )
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["physical_queries"], 80)
        self.assertTrue(
            decision["checks"]["v25158_invariant_observability_complete"]
        )
        self.assertTrue(decision["same_response_mechanism_gate_passed"])

    def test_one_v25158_failure_is_aggregated_without_task_identity(self) -> None:
        rows = [self._row(task["opaque_id"]) for task in contract.task_vector()]
        observation = invariant_observer.observe_receipt_invariants(
            self._v25158_receipt(rows[0])
        )
        changed_observation = copy.deepcopy(observation)
        changed_observation["violation_codes"] = ["grammar_accounting"]
        changed_observation["violation_count"] = 1
        changed_observation["frozen_validator_expected_to_accept"] = False
        changed_observation.pop("receipt_payload_sha256")
        changed_observation["receipt_payload_sha256"] = contract.payload_sha256(
            changed_observation
        )
        invariant_observer.validate_observation(changed_observation)
        failure = failure_observer.observe_outer_failure(
            ValueError("V2.51.58 vertical key-value candidate receipt drifted"),
            outer_failure_stage="runtime",
        )
        rows[0] = runner._terminal_outer_failure(
            contract.task_vector()[0], failure, 1.0
        )
        invariant = runner.build_invariant_observation_aggregate(
            rows, [changed_observation, *([None] * 19)]
        )
        self.assertEqual(
            invariant["violation_code_counts"], {"grammar_accounting": 1}
        )
        self.assertEqual(invariant["v25158_invariant_observer_missing_tasks"], 0)
        encoded = json.dumps(invariant, ensure_ascii=False)
        for task in contract.task_vector():
            self.assertNotIn(task["opaque_id"], encoded)
        for package in contract.PACKAGES:
            self.assertNotIn(package, encoded)

        with self.assertRaises(RuntimeError):
            runner.build_invariant_observation_aggregate(
                rows, [None, changed_observation, *([None] * 18)]
            )

    @staticmethod
    def _v25158_receipt(row: dict) -> dict:
        found: list[dict] = []

        def walk(value) -> None:
            if isinstance(value, dict):
                if value.get("role") == (
                    "v25158_content_free_vertical_key_value_candidate_receipt"
                ):
                    found.append(value)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(row)
        if len(found) != 1:
            raise AssertionError("expected one V2.51.58 receipt")
        return found[0]

    def test_missing_probe_observation_fails_observability_check_only(self) -> None:
        base = {
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
            "physical_fetches": 200,
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
            "outer_failure_code_counts": {"v25158_receipt_validation": 1},
            "terminal_effect_hard_failures": 0,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
            "v25158_receipt_failure_tasks": 1,
            "v25158_invariant_observed_failure_tasks": 0,
            "v25158_invariant_observer_missing_tasks": 1,
            "v25158_invariant_violation_code_counts": {},
            "v25158_invariant_violation_event_count": 0,
        }
        checked = runner.validate_aggregate(base)
        decision = runner.mechanism_decision(checked)
        self.assertFalse(
            decision["checks"]["v25158_invariant_observability_complete"]
        )
        self.assertTrue(decision["checks"]["exact_fixed_denominator_query_budget"])

    def test_aggregate_tamper_credit_or_unknown_code_fails_closed(self) -> None:
        rows = [self._row(task["opaque_id"]) for task in contract.task_vector()]
        invariant = runner.build_invariant_observation_aggregate(
            rows, [None] * contract.TASK_COUNT
        )
        aggregate = runner.aggregate_rows(
            rows, wall_seconds=2.0, invariant_aggregate=invariant
        )
        for kind in ("credit", "code"):
            changed = copy.deepcopy(aggregate)
            if kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["v25158_invariant_violation_code_counts"] = {
                    "private_value": 1
                }
                changed["v25158_invariant_violation_event_count"] = 1
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                runner.validate_aggregate(changed)

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
        self.assertIn(contract.INVARIANT_OBSERVER, closure)
        self.assertIn(contract.FAILURE_PROBE, closure)
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
