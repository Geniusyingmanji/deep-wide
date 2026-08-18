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
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25065_quote_verified_record_binding as quote  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25375_schema_total_changed_safe_runtime as schema  # noqa: E402
from deepwide_agent import v25401_grounded_record_membership_runtime as old  # noqa: E402
from deepwide_agent import v25569_constraint_totality_safe_handoff_runtime as surface  # noqa: E402
from deepwide_agent import v25575_canonical_column_totality_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    QUESTION,
    limits,
)
from test_v25401_grounded_record_membership_runtime import (  # noqa: E402
    GroundedMembershipModel,
    run_runtime,
)
from test_v24990_query_vector_paired_runtime import (  # noqa: E402
    SyntheticRobustSearch,
)


NFKC_QUESTION = (
    "Use public sources and return one table. "
    "Columns exactly: Entity | Ｍetric | Value. Preserve exact spelling."
)
V25379_PREDICTIONS = ROOT / (
    "outputs/v25379_changed_safe_exact220_v1_20260813/"
    "runtime_predictions.jsonl"
)
V25379_PREDICTIONS_SHA256 = (
    "d93293f6383006522373b5f1cb16a58ae21fc4c2eb6033ea7c28f5cf6bdaa32d"
)


class _NoRecordHybrid:
    prepared_records = None
    grounded_prepared_records = None

    @staticmethod
    def choose_record_source() -> str:
        return "none"


class _NfkcAlignedModel(GroundedMembershipModel):
    """Keep the first two synthetic calls and align call three to the task."""

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls < 2:
            return super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        del system, user, max_output_tokens
        if not json_mode:
            raise AssertionError("third call must request JSON mode")
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        table = (
            "| Entity | Ｍetric | Value |\n"
            "|---|---|---|\n"
            "| Alpha | count | 1 |"
        )
        return ModelResult(
            text=json.dumps({"table": table, "records": []}),
            usage={},
            response_id=None,
            attempts=1,
        )


class _FrozenThirdResponseModel:
    """Three successful synthetic calls with one frozen table as call three."""

    def __init__(self, prediction: str) -> None:
        self.prediction = str(prediction)
        columns, _reason = surface._projection_columns(self.prediction)
        self.plan_columns = list(columns or ("Result", "Value"))
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
        if not json_mode:
            raise AssertionError("all replay calls must request JSON mode")
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": self.plan_columns,
                    "queries": [
                        "public source requested facts",
                        "official source requested table",
                        "public registry requested values",
                        "authoritative data requested fields",
                    ],
                },
                ensure_ascii=False,
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": [],
                    "row_targets": [],
                    "authority_terms": [],
                    "queries": [
                        "synthetic public source one",
                        "synthetic public source two",
                    ],
                    "records": [],
                }
            )
        elif self.logical_calls == 3:
            text = json.dumps(
                {"table": self.prediction, "records": []},
                ensure_ascii=False,
            )
        else:
            raise AssertionError("runtime exceeded the frozen three-call budget")
        return ModelResult(
            text=text,
            usage={},
            response_id=None,
            attempts=1,
        )


def _run_full_synthetic_runtime(module, task, prediction):
    inner = _FrozenThirdResponseModel(prediction)
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        output_root = Path(raw)
        slots = output_root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text(
                "{}\n", encoding="utf-8"
            )
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=slots,
            output_root=output_root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        model = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                SyntheticRobustSearch(task["question"], "111"),
                budget,
                phase=phase,
            )
            for phase in module.PHASES
        }
        result, stage = module.run_task(
            task,
            model=model,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return result, stage, cap.validate_budget_receipt(budget.receipt()), inner


def _frozen_prediction_rows() -> dict[str, dict]:
    raw = V25379_PREDICTIONS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != V25379_PREDICTIONS_SHA256:
        raise AssertionError("frozen V2.53.79 prediction fixture drifted")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    by_id = {str(row["opaque_id"]): row for row in rows}
    if len(rows) != 220 or len(by_id) != 220:
        raise AssertionError("frozen V2.53.79 prediction denominator drifted")
    return by_id


class V25575CanonicalColumnTotalityRuntimeTests(unittest.TestCase):
    def test_nfkc_column_drift_old_fails_and_successor_is_terminal(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "V2.53.95 selected verifier state drifted"
        ):
            run_runtime(old, _NfkcAlignedModel(), question=NFKC_QUESTION)
        result, stage, budget = run_runtime(
            target, _NfkcAlignedModel(), question=NFKC_QUESTION
        )
        self.assertEqual(target.validate_result(result), result)
        self.assertEqual(target.validate_stage_receipt(stage), stage)
        self.assertEqual(result["policy_id"], target.POLICY_ID)
        self.assertEqual(result["role"], target.HANDOFF_ROLE)
        self.assertEqual(
            result["nonadmission_reason"],
            target.CANONICAL_COLUMN_NONADMISSION,
        )
        self.assertEqual(
            result["prediction"], result["private_parent_result"]["prediction"]
        )
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(budget["model_admitted_count"], 3)

    def test_corrected_verifier_uses_one_canonical_column_contract(self) -> None:
        plan, _observation, _source = schema.projected_plan(
            {}, NFKC_QUESTION, limits()
        )
        self.assertNotEqual(
            tuple(plan["columns"]),
            tuple(quote._text(value) for value in plan["columns"]),
        )
        verifier = target._CanonicalColumnVerifier(_NoRecordHybrid())
        prepared = verifier.prepare_record_proposal(
            NFKC_QUESTION, plan["columns"], ()
        )
        self.assertEqual(
            tuple(prepared["columns"]), quote._safe_columns(plan["columns"])
        )

    def test_canonical_parent_behavior_and_sealed_surface_are_preserved(self) -> None:
        result, stage, _budget = run_runtime(
            target, GroundedMembershipModel(), question=QUESTION
        )
        checked = surface.validate_result(result)
        checked_stage = surface.validate_stage_receipt(stage)
        self.assertEqual(checked, result)
        self.assertEqual(checked_stage, stage)
        self.assertEqual(
            checked_stage["runtime_result_payload_sha256"],
            checked["result_payload_sha256"],
        )

    def test_invalid_column_contracts_remain_fail_closed(self) -> None:
        verifier = target._CanonicalColumnVerifier(_NoRecordHybrid())
        invalid = (
            ("Entity", "entity"),
            ("Entity", "x" * 81),
            ("Entity", "bad|column"),
            ("Entity", "   "),
        )
        for columns in invalid:
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                verifier.prepare_record_proposal("Visible question", columns, ())

    def test_question_or_prepared_column_tamper_still_fails(self) -> None:
        verifier = target._CanonicalColumnVerifier(_NoRecordHybrid())
        for changed in (
            {"question": "different", "columns": ("Entity", "Value")},
            {"question": "Visible question", "columns": ("Entity", "Other")},
        ):
            prepared = {
                "role": "synthetic",
                "question": changed["question"],
                "columns": changed["columns"],
            }
            with mock.patch.object(
                target.visible_parent.verifier,
                "prepare_record_proposal",
                return_value=prepared,
            ), self.assertRaises(ValueError):
                verifier.prepare_record_proposal(
                    "Visible question", ("Entity", "Value"), ()
                )

    def test_full_visible_220_validator_replay_closes_eleven_failures(self) -> None:
        old_failures = 0
        new_failures = 0
        limits_value = schema.score.ScoreFirstLimits(
            wall_seconds=240,
            model_calls=3,
            search_queries=4,
            fetch_targets=10,
            search_results_per_query=3,
            evidence_chars=60_000,
            page_chars=5_000,
        )
        from deepwide_agent import v25573_totality_exact220_contract as contract

        for task in contract.task_vector(ROOT):
            plan, _observation, _source = schema.projected_plan(
                {}, task["question"], limits_value
            )
            try:
                old._GroundedRecordMembershipHybridInner
                old_verifier = target.visible_parent._TaskLocalVerifier(
                    _NoRecordHybrid()
                )
                old_verifier.prepare_record_proposal(
                    task["question"], plan["columns"], ()
                )
            except ValueError:
                old_failures += 1
            try:
                new_verifier = target._CanonicalColumnVerifier(
                    _NoRecordHybrid()
                )
                new_verifier.prepare_record_proposal(
                    task["question"], plan["columns"], ()
                )
            except ValueError:
                new_failures += 1
        self.assertEqual(old_failures, 11)
        self.assertEqual(new_failures, 0)

    def test_full_visible_220_runtime_replay_closes_eleven_failures(self) -> None:
        """Exercise every runtime stage without network, truth, or evaluator."""

        from deepwide_agent import v25573_totality_exact220_contract as contract

        tasks = contract.task_vector(ROOT)
        frozen = _frozen_prediction_rows()
        self.assertEqual(
            {task["opaque_id"] for task in tasks}, set(frozen)
        )
        predecessor_failures: dict[str, str] = {}
        new_failures: dict[str, str] = {}
        new_modes = {
            "canonical_projection": 0,
            "byte_exact_parent_handoff": 0,
            "canonical_column_handoff": 0,
        }
        for task in tasks:
            prediction = frozen[task["opaque_id"]]["prediction"]
            try:
                _old_result, _old_stage, old_budget, old_model = (
                    _run_full_synthetic_runtime(surface, task, prediction)
                )
                self.assertEqual(old_model.logical_calls, 3)
                self.assertEqual(old_budget["model_admitted_count"], 3)
            except ValueError as exc:
                predecessor_failures[task["opaque_id"]] = (
                    f"{type(exc).__name__}: {exc}"
                )
            try:
                result, stage, budget, model = _run_full_synthetic_runtime(
                    target, task, prediction
                )
                target.validate_runtime_pair(result, stage)
                self.assertEqual(model.logical_calls, 3)
                self.assertEqual(budget["query_admitted_count"], 4)
                self.assertLessEqual(budget["fetch_admitted_count"], 14)
                self.assertEqual(budget["model_admitted_count"], 3)
                if result["role"] == target.HANDOFF_ROLE:
                    new_modes["canonical_column_handoff"] += 1
                    self.assertEqual(result["prediction"], prediction)
                else:
                    new_modes[result["mode"]] += 1
            except ValueError as exc:
                new_failures[task["opaque_id"]] = f"{type(exc).__name__}: {exc}"
        self.assertEqual(len(predecessor_failures), 11)
        self.assertEqual(
            set(predecessor_failures.values()),
            {"ValueError: V2.53.95 selected verifier state drifted"},
        )
        self.assertEqual(new_failures, {})
        self.assertEqual(
            new_modes,
            {
                "canonical_projection": 209,
                "byte_exact_parent_handoff": 0,
                "canonical_column_handoff": 11,
            },
        )

    def test_integration_contract_is_label_blind_and_zero_credit(self) -> None:
        value = target.integration_contract()
        self.assertEqual(value["runtime_input_keys"], ["opaque_id", "question"])
        self.assertTrue(
            value[
                "prepared_and_requested_columns_use_same_v25065_safe_columns"
            ]
        )
        self.assertFalse(
            value[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertFalse(value["historical_per_task_outcome_runtime_routing"])
        self.assertFalse(
            value["entropy_or_information_gain_assigns_signed_credit"]
        )
        self.assertEqual(value["positive_signed_credit_count"], 0)

    def test_resealed_handoff_receipt_prediction_or_reason_tamper_fails(self) -> None:
        result, stage, _budget = run_runtime(
            target, _NfkcAlignedModel(), question=NFKC_QUESTION
        )
        for kind in ("receipt", "prediction", "reason", "stage"):
            changed = copy.deepcopy(result)
            if kind == "receipt":
                receipt = changed["canonical_column_handoff_receipt"]
                receipt["raw_column_count"] += 1
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = target.payload_sha256(receipt)
            elif kind == "prediction":
                changed["prediction"] += "\n"
            elif kind == "reason":
                changed["nonadmission_reason"] = "other"
            else:
                changed_stage = copy.deepcopy(stage)
                changed_stage["runtime_result_payload_sha256"] = "a" * 64
                changed_stage.pop("receipt_payload_sha256")
                changed_stage["receipt_payload_sha256"] = target.payload_sha256(
                    changed_stage
                )
                self.assertEqual(
                    target.validate_stage_receipt(changed_stage), changed_stage
                )
                with self.assertRaises(ValueError):
                    target.validate_runtime_pair(result, changed_stage)
                continue
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_source_has_no_privileged_or_direct_external_capability(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25575_canonical_column_totality_runtime.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
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
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in forbidden_fields:
                    privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        self.assertFalse(
            any(
                name in {
                    "os",
                    "pathlib",
                    "subprocess",
                    "requests",
                    "httpx",
                    "socket",
                    "urllib",
                }
                for name in imports
            )
        )
        for forbidden_call in (
            "open(",
            "getenv(",
            "run_official_eval_local(",
        ):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
