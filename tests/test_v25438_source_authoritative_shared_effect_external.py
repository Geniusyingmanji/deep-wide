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

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25434_source_authoritative_shared_runtime as runtime  # noqa: E402
from deepwide_agent import v25438_source_authoritative_shared_effect_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25438_source_authoritative_shared_effect_external as runner  # noqa: E402
from test_v25349_shared_prefix_grounded_fact_paired_runtime import FactSearch  # noqa: E402


RFC_PAGE = (
    "| RFC | Title | Authors | Status | Stream | Published |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| RFC 9160 | Alpha | Alice | Standards Track | IETF | May 2022 |"
)


class RfcSearch(FactSearch):
    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        if self._phase != runtime.PHASES[1]:
            return output
        for batch in output:
            for item in batch.get("results", []):
                item.update(
                    {
                        "url": "https://www.rfc-editor.org/rfc/rfc9160.html",
                        "fetch_url": "https://www.rfc-editor.org/rfc/rfc9160.html",
                        "title": "RFC 9160",
                    }
                )
        return output

    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        if self._phase != runtime.PHASES[1]:
            return output
        for batch in output:
            for item in batch.get("results", []):
                item.update(
                    {
                        "url": "https://www.rfc-editor.org/rfc/rfc9160.html",
                        "fetch_url": "https://www.rfc-editor.org/rfc/rfc9160.html",
                        "requested_url": "https://www.rfc-editor.org/rfc/rfc9160.html",
                        "title": "RFC 9160",
                        "raw_content": RFC_PAGE,
                    }
                )
        return output


class RfcModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens
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
                        "RFC Editor 9160 9161",
                        "RFC Editor 9162 9163",
                        "RFC 9160 metadata",
                        "RFC 9161 metadata",
                    ],
                }
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": ["RFC 9160"],
                    "row_targets": [
                        "RFC 9160",
                        "RFC 9161",
                        "RFC 9162",
                        "RFC 9163",
                    ],
                    "authority_terms": ["RFC Editor"],
                    "queries": [
                        "RFC 9160 RFC Editor metadata",
                        "RFC 9161 RFC Editor metadata",
                    ],
                    "records": [],
                }
            )
        else:
            if not json_mode:
                raise AssertionError("third call must request JSON mode")
            table = (
                "| RFC | Title | Authors | Status | Stream | Published |\n"
                "|---|---|---|---|---|---|\n"
                "| RFC 9160 | Alpha | Alice | Unknown | IETF | May 2022 |\n"
                "| RFC 9161 | Beta | Bob | Proposed Standard | IETF | June 2022 |\n"
                "| RFC 9162 | Gamma | Carol | Informational | IETF | July 2022 |\n"
                "| RFC 9163 | Delta | Dan | Experimental | IETF | August 2022 |"
            )
            text = json.dumps({"table": table, "records": []})
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def completed_row() -> tuple[dict, dict, dict]:
    task = contract.task_vector()[0]
    model = RfcModel()
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        root = Path(raw)
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        outer = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                RfcSearch(task["question"], phase), budget, phase=phase
            )
            for phase in runtime.PHASES
        }
        result, stage = runtime.run_task(
            task,
            model=outer,
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
            "accepted_authority_page_tasks": 4,
            "accepted_authority_page_count_total": 4,
            "available_candidate_tasks": 2,
            "available_candidate_count_total": 2,
            "selected_candidate_tasks": 2,
            "selected_candidate_count_total": 2,
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


class V25438SourceAuthoritativeSharedEffectExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.row, cls.result, cls.stage = completed_row()

    def test_contract_population_arms_caps_and_quality_gate_are_frozen(self) -> None:
        self.assertEqual(contract.population.RFC_NUMBERS, tuple(range(9160, 9240)))
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(runner.ARMS, runtime.ARMS)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertTrue(
            contract.quality_gate()[
                "candidate_whole_table_exact_strictly_greater_than_base"
            ]
        )

    def test_real_runtime_chain_exposes_source_candidate_and_receipt(self) -> None:
        decoded = runner._decode_completed(self.result, self.stage)
        self.assertEqual(set(self.row["predictions"]), set(runtime.ARMS))
        self.assertEqual(decoded["predictions"], self.row["predictions"])
        source = decoded["source_receipt"]
        self.assertTrue(source["synthesis_capture_valid"])
        self.assertGreaterEqual(source["accepted_authority_page_count"], 1)
        self.assertEqual(source["available_candidate_count"], 1)
        self.assertEqual(source["applied_coordinate_count"], 1)
        self.assertTrue(self.row["candidate_prediction_changed"])
        self.assertEqual(self.row["actual_effect_snapshot"]["query_admitted_count"], 4)
        self.assertEqual(self.row["actual_effect_snapshot"]["model_admitted_count"], 3)
        self.assertLessEqual(self.row["actual_effect_snapshot"]["fetch_admitted_count"], 14)

    def test_failure_as_zero_freezes_two_identical_fallback_arms(self) -> None:
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            RuntimeError("synthetic"),
            1.0,
            budget=None,
            health=None,
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
            ("accepted_authority_page_tasks", 3),
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
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_resealed_prediction_receipt_or_credit_tamper_fails(self) -> None:
        for kind in ("prediction", "receipt", "credit"):
            changed = copy.deepcopy(self.row)
            if kind == "prediction":
                changed["predictions"][runtime.CANDIDATE_ARM] += "x"
            elif kind == "receipt":
                changed["runtime_result"]["source_authoritative_receipt"][
                    "accepted_authority_page_count"
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

    def test_forward_closure_excludes_quality_evaluator_and_diagnosis(self) -> None:
        paths = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertFalse(any("evaluate_v254" in path for path in paths))
        self.assertFalse(any("diagnose_v254" in path for path in paths))

    def test_runtime_boundary_rejects_privileged_input_before_effect(self) -> None:
        task = {**contract.task_vector()[0], "category": "forbidden"}
        with self.assertRaises(ValueError):
            runner.run_one_task(task)


if __name__ == "__main__":
    unittest.main()
