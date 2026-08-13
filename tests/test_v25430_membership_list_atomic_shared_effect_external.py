from __future__ import annotations

import copy
import json
import re
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
from deepwide_agent import v25426_membership_list_atomic_shared_runtime as runtime  # noqa: E402
from deepwide_agent import v25430_membership_list_atomic_shared_effect_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import run_v25430_membership_list_atomic_shared_effect_external as runner  # noqa: E402
from test_v25349_shared_prefix_grounded_fact_paired_runtime import FactSearch  # noqa: E402


RFC_QUOTE = (
    "RFC 9240 Title Alpha Authors Alice Status Standards Track Stream IETF "
    "Published May 2022"
)
_EVIDENCE_RECORD = re.compile(
    r"(?ms)^\[E(?P<ordinal>[0-9]{4})\] kind=fetched_page\n"
    r"(?P<body>.*?)(?=\n\n\[E[0-9]{4}\] kind=fetched_page\n|\Z)"
)


class RfcSearch(FactSearch):
    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        for batch in output:
            for item in batch.get("results", []):
                item["raw_content"] = RFC_QUOTE
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
                        "RFC Editor 9240 9241",
                        "RFC Editor 9242 9243",
                        "RFC 9240 metadata",
                        "RFC 9241 metadata",
                    ],
                }
            )
        elif self.logical_calls == 2:
            if "VISIBLE RECORD MEMBERSHIP CONSTRAINT:" not in str(system):
                raise AssertionError("grounded membership constraint is absent")
            text = json.dumps(
                {
                    "pivots": ["RFC 9240"],
                    "row_targets": [
                        "RFC 9240",
                        "RFC 9241",
                        "RFC 9242",
                        "RFC 9243",
                    ],
                    "authority_terms": ["RFC Editor"],
                    "queries": [
                        "RFC 9240 RFC Editor metadata",
                        "RFC 9241 RFC Editor metadata",
                    ],
                    "records": [
                        {
                            "page_ordinal": 1,
                            "quote": RFC_QUOTE,
                            "row_identity": "RFC 9240",
                            "fields": [
                                {
                                    "column": "Status",
                                    "source_field": "Status",
                                    "value": "Standards Track",
                                }
                            ],
                        }
                    ],
                }
            )
        else:
            if not json_mode:
                raise AssertionError("third call must request JSON mode")
            ordinal = None
            for match in _EVIDENCE_RECORD.finditer(str(user)):
                if RFC_QUOTE in match.group("body"):
                    ordinal = int(match.group("ordinal"))
                    break
            if ordinal is None:
                raise AssertionError("RFC evidence is absent")
            table = (
                "| RFC | Title | Authors | Status | Stream | Published |\n"
                "|---|---|---|---|---|---|\n"
                "| RFC 9240 | Alpha | Alice | Unknown | IETF | May 2022 |\n"
                "| RFC 9241 | Beta | Bob | Proposed Standard | IETF | June 2022 |\n"
                "| RFC 9242 | Gamma | Carol | Informational | IETF | July 2022 |\n"
                "| RFC 9243 | Delta | Dan | Experimental | IETF | August 2022 |"
            )
            text = json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "page_ordinal": ordinal,
                            "quote": RFC_QUOTE,
                            "row_identity": "RFC 9240",
                            "fields": [
                                {
                                    "column": "Status",
                                    "source_field": "Status",
                                    "value": "Standards Track",
                                }
                            ],
                        }
                    ],
                }
            )
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
            "membership_constraint_applied_tasks": 20,
            "base_visible_membership_exact_tasks": 20,
            "grounded_record_membership_constraint_applied_tasks": 20,
            "all_grounded_raw_records_membership_aligned_tasks": 20,
            "selected_raw_record_tasks": 8,
            "verified_record_tasks": 4,
            "raw_candidate_changed_tasks": 4,
            "guarded_candidate_changed_from_base_tasks": 4,
            "changed_coordinate_count": 4,
            "retained_candidate_coordinate_count": 4,
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


class V25430MembershipListAtomicSharedEffectExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.row, cls.result, cls.stage = completed_row()

    def test_contract_population_arms_caps_and_quality_gate_are_frozen(self) -> None:
        self.assertEqual(contract.population.RFC_NUMBERS, tuple(range(9240, 9320)))
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(runner.ARMS, runtime.ARMS)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertTrue(
            contract.quality_gate()[
                "guarded_whole_table_exact_strictly_greater_than_base"
            ]
        )

    def test_real_runtime_chain_exposes_three_shared_arms_and_receipts(self) -> None:
        decoded = runner._decode_completed(self.result, self.stage)
        self.assertEqual(set(self.row["predictions"]), set(runtime.ARMS))
        self.assertEqual(decoded["predictions"], self.row["predictions"])
        self.assertTrue(
            decoded["membership_receipt"]["membership_constraint_applied"]
        )
        self.assertTrue(
            decoded["grounded_receipt"][
                "grounded_record_membership_constraint_applied"
            ]
        )
        self.assertEqual(
            self.row["actual_effect_snapshot"]["query_admitted_count"], 4
        )
        self.assertEqual(
            self.row["actual_effect_snapshot"]["model_admitted_count"], 3
        )
        self.assertLessEqual(
            self.row["actual_effect_snapshot"]["fetch_admitted_count"], 14
        )

    def test_failure_as_zero_freezes_three_identical_fallback_arms(self) -> None:
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
            ("membership_constraint_applied_tasks", 19),
            ("base_visible_membership_exact_tasks", 19),
            ("grounded_record_membership_constraint_applied_tasks", 19),
            ("grounded_raw_membership_violation_count_total", 1),
            ("selected_raw_record_tasks", 7),
            ("verified_record_tasks", 3),
            ("raw_candidate_changed_tasks", 3),
            ("missing_row_rejected_field_count_total", 3),
            ("editor_validation_failure_tasks", 1),
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
                changed["predictions"][runtime.GUARDED_ARM] += "x"
            elif kind == "receipt":
                changed["runtime_result"][
                    "combined_membership_list_atomic_receipt"
                ]["grounded_raw_membership_violation_count"] += 1
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
