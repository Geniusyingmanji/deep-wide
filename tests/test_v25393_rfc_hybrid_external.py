from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25389_hybrid_record_fallback_runtime as runtime  # noqa: E402
from deepwide_agent import v25393_rfc_hybrid_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import audit_v25136_sparse_production_build as semantic  # noqa: E402
from scripts import run_v25393_rfc_hybrid_external as runner  # noqa: E402
from test_v25349_shared_prefix_grounded_fact_paired_runtime import (  # noqa: E402
    FactSearch,
)


RFC_QUOTE = (
    "RFC 9680 Title Alpha Authors Alice Status Standards Track Stream IETF "
    "Published 2024-01"
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


class RfcHybridModel:
    def __init__(
        self, *, joint_mode: str, grounded_mode: str = "valid"
    ) -> None:
        if joint_mode not in {"valid", "invalid", "empty"}:
            raise ValueError(joint_mode)
        if grounded_mode not in {"valid", "invalid", "empty"}:
            raise ValueError(grounded_mode)
        self.joint_mode = joint_mode
        self.grounded_mode = grounded_mode
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
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
                        "RFC Editor 9680 9681",
                        "RFC Editor 9682 9683",
                        "RFC 9680 metadata",
                        "RFC 9681 metadata",
                    ],
                }
            )
        elif self.logical_calls == 2:
            grounded: dict[str, object] = {
                "pivots": ["RFC 9680"],
                "row_targets": [
                    "RFC 9680", "RFC 9681", "RFC 9682", "RFC 9683"
                ],
                "authority_terms": ["RFC Editor"],
                "queries": [
                    "RFC 9680 RFC Editor metadata",
                    "RFC 9681 RFC Editor metadata",
                ],
            }
            if self.grounded_mode != "empty":
                grounded["records"] = [
                    {
                        "page_ordinal": 1,
                        "quote": (
                            RFC_QUOTE
                            if self.grounded_mode == "valid"
                            else "fabricated RFC 9680 Status Historic text"
                        ),
                        "row_identity": "RFC 9680",
                        "fields": [
                            {
                                "column": "Status",
                                "source_field": "Status",
                                "value": (
                                    "Standards Track"
                                    if self.grounded_mode == "valid"
                                    else "Historic"
                                ),
                            }
                        ],
                    }
                ]
            text = json.dumps(grounded)
        else:
            self.assert_joint_mode = bool(json_mode)
            ordinal = None
            for match in _EVIDENCE_RECORD.finditer(str(user)):
                if RFC_QUOTE in match.group("body"):
                    ordinal = int(match.group("ordinal"))
                    break
            if ordinal is None:
                raise AssertionError("RFC second-wave quote is absent")
            table = (
                "| RFC | Title | Authors | Status | Stream | Published |\n"
                "|---|---|---|---|---|---|\n"
                "| RFC 9680 | Alpha | Alice | Unknown | IETF | 2024-01 |\n"
                "| RFC 9681 | Beta | Bob | Proposed Standard | IETF | 2024-02 |\n"
                "| RFC 9682 | Gamma | Carol | Informational | IETF | 2024-03 |\n"
                "| RFC 9683 | Delta | Dan | Experimental | IETF | 2024-04 |"
            )
            records = []
            if self.joint_mode != "empty":
                records = [
                    {
                        "page_ordinal": ordinal,
                        "quote": (
                            RFC_QUOTE
                            if self.joint_mode == "valid"
                            else "fabricated RFC 9680 Status Historic text"
                        ),
                        "row_identity": "RFC 9680",
                        "fields": [
                            {
                                "column": "Status",
                                "source_field": "Status",
                                "value": (
                                    "Standards Track"
                                    if self.joint_mode == "valid"
                                    else "Historic"
                                ),
                            }
                        ],
                    }
                ]
            text = json.dumps(
                {
                    "table": table,
                    "records": records,
                }
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def completed_row(*, joint_mode: str, grounded_mode: str = "valid"):
    task = contract.task_vector()[0]
    model = RfcHybridModel(
        joint_mode=joint_mode, grounded_mode=grounded_mode
    )
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
            budget=budget,
            health=runner._health(),
        )
    return model, budget, runner.validate_task_row(row)


def passing_aggregate() -> dict:
    values = {name: 0 for name in runner.AGGREGATE_INTEGER_FIELDS}
    values.update(
        {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "failure_as_zero_tasks": 0,
            "content_free_stage_receipt_tasks": 20,
            "first_wave_completed_tasks": 20,
            "second_wave_completed_tasks": 20,
            "grounded_plan_provider_success_tasks": 20,
            "joint_envelope_exact_tasks": 20,
            "base_synthesis_success_tasks": 20,
            "exact_canonical_base_table_tasks": 20,
            "joint_source_tasks": 4,
            "grounded_source_tasks": 4,
            "no_source_tasks": 12,
            "joint_raw_record_tasks": 4,
            "joint_raw_record_count_total": 4,
            "grounded_raw_record_tasks": 8,
            "grounded_raw_record_count_total": 8,
            "selected_raw_record_tasks": 8,
            "selected_raw_record_count_total": 8,
            "record_output_strict_valid_tasks": 20,
            "verified_record_tasks": 4,
            "verified_record_count_total": 4,
            "verified_field_count_total": 4,
            "missing_row_rejected_field_count_total": 0,
            "changed_safe_coordinate_tasks": 4,
            "changed_safe_coordinate_count_total": 4,
            "attributable_prediction_changed_tasks": 4,
            "unattributable_prediction_changed_tasks": 0,
            "editor_validation_failure_tasks": 0,
            "outer_failure_tasks": 0,
            "budget_rejection_tasks": 0,
            "unrecoverable_hard_failure_tasks": 0,
            "completed_physical_queries": 80,
            "completed_physical_fetches": 200,
            "completed_physical_model_forwards": 60,
            "all_physical_queries": 80,
            "all_physical_fetches": 200,
            "all_physical_model_forwards": 60,
            "per_task_hard_cap_preserved_tasks": 20,
            "positive_signed_credit_count": 0,
            "system_total_tokens": 1,
        }
    )
    return runner.validate_aggregate(
        {
            **values,
            "batch_wall_seconds": 1.0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "prediction_text_query_url_title_page_quote_record_identity_field_value_answer_or_credential_persisted": False,
        }
    )


class V25393RfcHybridExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.joint_model, cls.joint_budget, cls.joint_row = completed_row(
            joint_mode="valid"
        )
        cls.grounded_model, cls.grounded_budget, cls.grounded_row = completed_row(
            joint_mode="empty"
        )
        cls.invalid_joint_model, _, cls.invalid_joint_row = completed_row(
            joint_mode="invalid"
        )
        cls.none_model, _, cls.none_row = completed_row(
            joint_mode="empty", grounded_mode="empty"
        )

    def test_contract_population_budget_and_funnel_gate_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.population.RFC_NUMBERS, tuple(range(9680, 9760)))
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        gate = contract.mechanism_gate()
        self.assertEqual(gate["minimum_selected_raw_record_tasks"], 8)
        self.assertEqual(gate["minimum_verified_record_tasks"], 4)
        self.assertEqual(gate["minimum_changed_safe_coordinate_tasks"], 4)
        self.assertEqual(gate["minimum_attributable_prediction_changed_tasks"], 4)
        self.assertEqual(gate["positive_signed_credit_count"], 0)

    def test_joint_source_is_content_free_and_three_model_attributable(self) -> None:
        row = self.joint_row
        stage = row["content_free_stage_receipt"]
        hybrid = stage["hybrid_record_fallback_receipt"]
        self.assertEqual(self.joint_model.logical_calls, 3)
        self.assertTrue(self.joint_model.assert_joint_mode)
        self.assertEqual(row["actual_effect_snapshot"]["query_admitted_count"], 4)
        self.assertLessEqual(row["actual_effect_snapshot"]["fetch_admitted_count"], 14)
        self.assertEqual(row["actual_effect_snapshot"]["model_admitted_count"], 3)
        self.assertEqual(hybrid["record_source"], "joint")
        self.assertEqual(hybrid["grounded_raw_record_count"], 1)
        self.assertEqual(hybrid["joint_raw_record_count"], 1)
        self.assertEqual(hybrid["selected_raw_record_count"], 1)
        self.assertEqual(hybrid["verified_record_count"], 1)
        self.assertEqual(hybrid["changed_safe_coordinate_count"], 1)
        self.assertTrue(row["prediction_changed"])
        self.assertTrue(row["attributable_prediction_change"])
        self.assertNotIn("prediction", row)
        serialized = json.dumps(row, sort_keys=True)
        for forbidden in (RFC_QUOTE, "Standards Track", "2024-01", "| RFC |"):
            self.assertNotIn(forbidden, serialized)

    def test_empty_joint_selects_grounded_before_verification(self) -> None:
        row = self.grounded_row
        hybrid = row["content_free_stage_receipt"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertEqual(self.grounded_model.logical_calls, 3)
        self.assertEqual(hybrid["record_source"], "grounded")
        self.assertEqual(hybrid["joint_raw_record_count"], 0)
        self.assertEqual(hybrid["grounded_raw_record_count"], 1)
        self.assertTrue(hybrid["grounded_fallback_selected"])
        self.assertEqual(hybrid["verified_record_count"], 1)
        self.assertTrue(row["attributable_prediction_change"])

    def test_nonempty_invalid_joint_preempts_valid_grounded(self) -> None:
        row = self.invalid_joint_row
        hybrid = row["content_free_stage_receipt"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertEqual(self.invalid_joint_model.logical_calls, 3)
        self.assertEqual(hybrid["record_source"], "joint")
        self.assertEqual(hybrid["joint_raw_record_count"], 1)
        self.assertEqual(hybrid["grounded_raw_record_count"], 1)
        self.assertTrue(hybrid["joint_nonempty_preempts_grounded"])
        self.assertFalse(hybrid["grounded_fallback_selected"])
        self.assertEqual(hybrid["verified_record_count"], 0)
        self.assertFalse(row["prediction_changed"])

    def test_empty_joint_and_grounded_partition_to_none(self) -> None:
        row = self.none_row
        hybrid = row["content_free_stage_receipt"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertEqual(self.none_model.logical_calls, 3)
        self.assertEqual(hybrid["record_source"], "none")
        self.assertEqual(hybrid["selected_raw_record_count"], 0)
        self.assertTrue(hybrid["no_record_source_selected"])
        self.assertFalse(row["prediction_changed"])

    def test_gate_go_and_each_funnel_threshold_fail_closed(self) -> None:
        aggregate = passing_aggregate()
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        for field, value in (
            ("joint_envelope_exact_tasks", 17),
            ("selected_raw_record_tasks", 7),
            ("verified_record_tasks", 3),
            ("changed_safe_coordinate_tasks", 3),
            ("attributable_prediction_changed_tasks", 3),
            ("missing_row_rejected_field_count_total", 3),
            ("completed_physical_model_forwards", 61),
        ):
            changed = copy.deepcopy(aggregate)
            changed[field] = value
            with self.subTest(field=field):
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_failure_row_is_terminal_content_free_and_keeps_partial_effects(self) -> None:
        budget = cap.PhysicalEffectBudget()
        budget.reserve("model", 1, stage="model_plan")
        budget.reserve("query", 2, stage="shared_first_wave_search")
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            ValueError("synthetic"),
            1.0,
            budget=budget,
            health=runner._health(),
        )
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["failure_as_zero"])
        self.assertIsNone(checked["content_free_stage_receipt"])
        self.assertEqual(checked["actual_effect_snapshot"]["query_admitted_count"], 2)
        self.assertFalse(
            checked[
                "prediction_text_query_url_title_page_quote_record_identity_field_value_answer_or_credential_persisted"
            ]
        )

    def test_resealed_receipt_effect_credit_or_privileged_tamper_fails(self) -> None:
        for kind in ("receipt", "effect", "credit", "privileged"):
            changed = copy.deepcopy(self.joint_row)
            if kind == "receipt":
                hybrid = changed["content_free_stage_receipt"][
                    "hybrid_record_fallback_receipt"
                ]
                hybrid["record_source"] = "grounded"
                hybrid["joint_nonempty_preempts_grounded"] = False
                hybrid["grounded_fallback_selected"] = True
                hybrid.pop("receipt_payload_sha256")
                hybrid["receipt_payload_sha256"] = contract.payload_sha256(
                    hybrid
                )
            elif kind == "effect":
                changed["actual_effect_snapshot"]["model_admitted_count"] = 4
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["category"] = "forbidden"
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_result_never_directly_authorizes_benchmark(self) -> None:
        aggregate = passing_aggregate()
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": runner.FORWARD_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "execution_start_sha256": "a" * 64,
                "execution_start_payload_sha256": "b" * 64,
                "task_rows_sha256": "c" * 64,
                "prediction_freeze_sha256": "d" * 64,
                "aggregate": aggregate,
                "mechanism_decision": runner.mechanism_decision(aggregate),
                "authorization": {
                    "forward_audit": True,
                    "deepwidebench_successor_build": False,
                    "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                    "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
                },
            },
            "result_payload_sha256",
        )
        self.assertEqual(runner.validate_forward_result(value), value)
        changed = copy.deepcopy(value)
        changed["authorization"]["deepwidebench_successor_build"] = True
        changed.pop("result_payload_sha256")
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(ValueError):
            runner.validate_forward_result(changed)

    def test_runner_rejects_privileged_task_before_effect(self) -> None:
        task = dict(contract.task_vector()[0])
        task["question_type"] = "forbidden"
        for effect_name in (
            "HardTotalWallResponsesClient",
            "RobustLatePageBoundSearchClient",
        ):
            with self.subTest(effect=effect_name), mock.patch.object(
                runner, effect_name,
                side_effect=AssertionError("effect boundary crossed"),
            ), self.assertRaises(ValueError):
                runner.run_one_task(task)

    def test_forward_closure_is_label_blind_and_evaluator_free(self) -> None:
        closure = contract.forward_dependency_closure(ROOT)
        findings = semantic._semantic_findings(closure)
        self.assertEqual(findings["privileged_runtime_field_accesses"], [])
        self.assertEqual(findings["evaluator_capabilities"], [])
        self.assertEqual(findings["credential_literal_hits"], [])
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = {
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
        accesses = [
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in forbidden
        ]
        self.assertEqual(accesses, [])


if __name__ == "__main__":
    unittest.main()
