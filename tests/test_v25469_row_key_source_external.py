from __future__ import annotations

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

from deepwide_agent import v25465_row_key_bound_structured_source_runtime as runtime  # noqa: E402
from deepwide_agent import v25469_row_key_source_external_contract as contract  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25469_row_key_source_external as runner  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import GroundedFrontierSearch  # noqa: E402


class FrozenRowKeyModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["ignored"],
                    "queries": [
                        "Kabul AFN jurisdiction",
                        "Kabul AFN country",
                        "IANA root zone AF",
                        "AF domain manager",
                    ],
                }
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": ["Afghanistan"],
                    "row_targets": [".af"],
                    "authority_terms": ["IANA Root Zone Database"],
                    "queries": ["IANA .af record", ".af TLD Manager"],
                    "records": [],
                }
            )
        else:
            if json_mode:
                raise AssertionError("third call must request plain table text")
            text = (
                "| Domain | Type | TLD Manager |\n"
                "|---|---|---|\n"
                "| .af | Unknown | Old Manager |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class FrozenRowKeySearch(GroundedFrontierSearch):
    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        if self._phase == runtime.PHASES[0] or not output:
            return output
        target = "https://www.iana.org/domains/root/db/af.html"
        first = output[0].get("results") if isinstance(output[0], dict) else None
        if isinstance(first, list) and first:
            first[0].update({"url": target, "fetch_url": target, "title": ".af record"})
        for batch in output:
            trace = batch.get("hosted_search_trace") if isinstance(batch, dict) else None
            if not isinstance(trace, dict):
                continue
            for action in trace.get("actions") or []:
                for source in action.get("sources") or []:
                    if "iana.org" in str(source.get("url") or ""):
                        source.update(
                            {"url": target, "fetch_url": target, "title": ".af record"}
                        )
        return output

    def fetch_urls(self, requests_):
        values = list(requests_)
        output = super().fetch_urls(values)
        if self._phase == runtime.PHASES[0]:
            return output
        target = "https://www.iana.org/domains/root/db/af.html"
        replacement = next(
            (item for item in values if str(item.get("url") or "") == target), None
        )
        if replacement is None:
            return output
        content = "Type: country-code\nTLD Manager: Ministry of Communications"
        self._prefixes[target] = content
        result = {
            "title": ".af record",
            "url": target,
            "fetch_url": target,
            "requested_url": target,
            "raw_content": content,
            "content": "",
        }
        if output and output[0].get("results"):
            output[0]["results"][0] = result
        else:
            output.insert(
                0,
                {
                    "query": replacement.get("query", ""),
                    "answer": "",
                    "results": [result],
                    "error": None,
                    "provider": "synthetic-fetch",
                },
            )
        return output


def completed_row() -> tuple[dict, dict, dict]:
    task = contract.task_vector()[0]
    model = FrozenRowKeyModel()
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        output = Path(raw)
        slots = output / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=output,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        searches = {
            phase: cap.HardCappedSearchClient(
                FrozenRowKeySearch(task["question"], phase), budget, phase=phase
            )
            for phase in runtime.PHASES
        }
        result, stage = runtime.run_task(
            task,
            model=cap.HardCappedModelLimiter(bounded, budget),
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            budget=budget,
            monotonic=time.monotonic,
        )
        row = runner._from_runtime(
            task,
            result,
            stage,
            elapsed=1.0,
            budget=budget,
            health=runner._health(),
        )
    return runner.validate_task_row(row), result, stage


def passing_aggregate() -> dict:
    values = {name: 0 for name in runner.AGGREGATE_INTEGER_FIELDS}
    values.update(
        {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "parent_role_tasks": 20,
            "first_wave_completed_tasks": 20,
            "second_wave_completed_tasks": 20,
            "grounded_plan_provider_success_tasks": 20,
            "base_synthesis_success_tasks": 20,
            "exact_canonical_base_table_tasks": 20,
            "synthesis_capture_valid_tasks": 20,
            "captured_same_forward_page_tasks": 20,
            "captured_same_forward_page_count_total": 100,
            "accepted_unique_identity_page_tasks": 3,
            "accepted_unique_identity_page_count_total": 3,
            "available_candidate_tasks": 2,
            "available_candidate_count_total": 2,
            "applied_candidate_tasks": 2,
            "applied_coordinate_count_total": 2,
            "prediction_changed_tasks": 2,
            "all_physical_queries": 80,
            "all_physical_fetches": 200,
            "all_physical_model_forwards": 60,
            "completed_physical_queries": 80,
            "completed_physical_fetches": 200,
            "completed_physical_model_forwards": 60,
            "per_task_hard_cap_preserved_tasks": 20,
            "system_total_tokens": 1,
        }
    )
    return runner.validate_aggregate(
        {
            **values,
            "batch_wall_seconds": 1.0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate": False,
        }
    )


class V25469RowKeySourceExternalTests(unittest.TestCase):
    def test_contract_population_caps_and_quality_gate_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(runner.ARMS, runtime.ARMS)
        self.assertEqual(contract.mechanism_gate()["minimum_prediction_changed_tasks"], 2)
        self.assertTrue(
            contract.quality_gate()["candidate_whole_table_exact_strictly_greater_than_base"]
        )
        self.assertFalse(
            contract.source_policy()["historical_population_forward_or_output_reused"]
        )

    def test_real_parent_chain_decodes_and_freezes_two_predictions(self) -> None:
        row, result, stage = completed_row()
        decoded = runner._decode_completed(result, stage)
        self.assertEqual(set(row["predictions"]), set(runtime.ARMS))
        self.assertEqual(row["predictions"], decoded["predictions"])
        self.assertTrue(row["synthesis_capture_valid"])
        self.assertGreaterEqual(row["accepted_unique_identity_page_count"], 1)
        self.assertGreaterEqual(row["available_candidate_count"], 1)
        self.assertTrue(row["candidate_prediction_changed"])
        self.assertEqual(row["actual_effect_snapshot"]["query_admitted_count"], 4)
        self.assertEqual(row["actual_effect_snapshot"]["model_admitted_count"], 3)
        self.assertLessEqual(row["actual_effect_snapshot"]["fetch_admitted_count"], 14)

    def test_failure_as_zero_freezes_identical_fallback_arms(self) -> None:
        row = runner._terminal_outer_failure(
            contract.task_vector()[0], RuntimeError("synthetic"), 1.0,
            budget=None, health=None,
        )
        self.assertTrue(row["failure_as_zero"])
        self.assertEqual(len(set(row["predictions"].values())), 1)
        self.assertEqual(set(row["predictions"]), set(runtime.ARMS))

    def test_passing_aggregate_satisfies_full_mechanism_gate(self) -> None:
        decision = runner.mechanism_decision(passing_aggregate())
        self.assertTrue(decision["mechanism_gate_passed"])
        self.assertTrue(decision["postfreeze_quality_protocol_authorized"])

    def test_each_new_mechanism_threshold_fails_closed(self) -> None:
        for field, value in (
            ("synthesis_capture_valid_tasks", 19),
            ("accepted_unique_identity_page_tasks", 2),
            ("available_candidate_tasks", 1),
            ("applied_candidate_tasks", 1),
            ("prediction_changed_tasks", 1),
            ("application_failure_tasks", 1),
        ):
            changed = passing_aggregate()
            changed[field] = value
            with self.subTest(field=field):
                try:
                    changed = runner.validate_aggregate(changed)
                except ValueError:
                    continue
                self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_resealed_prediction_receipt_or_credit_tamper_fails(self) -> None:
        row, _result, _stage = completed_row()
        for kind in ("prediction", "receipt", "credit"):
            changed = copy.deepcopy(row)
            if kind == "prediction":
                changed["predictions"][runtime.CANDIDATE_ARM] += "x"
            elif kind == "receipt":
                changed["runtime_result"]["row_key_bound_source_receipt"][
                    "accepted_unique_identity_page_count"
                ] += 1
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_result_never_authorizes_quality_or_benchmark_directly(self) -> None:
        aggregate = passing_aggregate()
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": runner.FORWARD_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "aggregate": aggregate,
                "mechanism_decision": runner.mechanism_decision(aggregate),
                "authorization": {
                    "forward_audit": True,
                    "postfreeze_quality_protocol": False,
                    "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                    "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
                },
            },
            "result_payload_sha256",
        )
        self.assertEqual(runner.validate_forward_result(value), value)

    def test_forward_closure_excludes_truth_evaluator_and_historical_outcomes(self) -> None:
        paths = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertFalse(any("evaluate_v254" in path for path in paths))
        self.assertFalse(any("diagnose_v254" in path for path in paths))
        self.assertFalse(any("v25461_date_bounded_official_rfc_xml_shared_effect_external_forward_result" in path for path in paths))
        self.assertFalse(any(path.startswith("outputs/") for path in paths))

    def test_runtime_boundary_rejects_privileged_input_before_effect(self) -> None:
        task = {**contract.task_vector()[0], "category": "forbidden"}
        with self.assertRaises(ValueError):
            runner.run_one_task(task)


if __name__ == "__main__":
    unittest.main()
