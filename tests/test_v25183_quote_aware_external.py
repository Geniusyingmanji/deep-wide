from __future__ import annotations

import ast
import copy
import json
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

from deepwide_agent import v25110_exact_visible_schema as parser  # noqa: E402
from deepwide_agent import v25183_quote_aware_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts import control_v25183_quote_aware_external as control  # noqa: E402
from scripts import run_v25183_quote_aware_external as runner  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    QUESTION,
)
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    CANDIDATE_CONTENT,
    EscapedProductionModel,
    NO_GAIN_CONTENT,
)


class AccountingSearch(GenericRecordSearch):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.actual_search_invocations = 0
        self.actual_logical_query_count = 0
        self.actual_fetch_invocations = 0
        self.actual_fetch_request_count = 0

    def search_many(self, queries, **kwargs):
        values = list(queries)
        self.actual_search_invocations += 1
        self.actual_logical_query_count += len(values)
        return super().search_many(values, **kwargs)

    def fetch_urls(self, requests):
        values = list(requests)
        self.actual_fetch_invocations += 1
        self.actual_fetch_request_count += len(values)
        return super().fetch_urls(values)


class V25183QuoteAwareExternalTests(unittest.TestCase):
    def _row(self, opaque_id: str, *, positive_gain: bool = False) -> dict:
        task = {"opaque_id": opaque_id, "question": QUESTION}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = EscapedProductionModel()
            model = runner._EffectAccountingModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            content = CANDIDATE_CONTENT if positive_gain else NO_GAIN_CONTENT
            searches = {
                phase: AccountingSearch(QUESTION, phase, content=content)
                for phase in contract.runtime.PHASES
            }
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
                runner._health(),
                runner._actual_effect_snapshot(model, searches),
            )
        return runner.validate_task_row(row)

    def test_visible_population_schema_and_disjoint_audit_are_bound(self):
        tasks = contract.task_vector()
        selection = contract.validate_population_audit(ROOT, tracked=True)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len(set(contract.PACKAGES)), 20)
        self.assertEqual(selection["identity_history_zero_hit_count"], 20)
        self.assertEqual(
            selection["ordered_identity_vector_sha256"],
            contract.IDENTITY_SELECTION_SHA256,
        )
        for task, package in zip(tasks, contract.PACKAGES, strict=True):
            self.assertIn(f"<PACKAGE>{package}</PACKAGE>", task["question"])
            self.assertEqual(
                parser.extract_exact_visible_columns(task["question"]),
                list(contract.COLUMNS),
            )
            self.assertNotIn("https://", task["question"])

    def test_mechanism_and_quality_authority_are_narrow(self):
        gate = contract.mechanism_gate()
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertEqual(gate["minimum_quote_aware_repair_applied_tasks"], 12)
        self.assertEqual(gate["maximum_public_export_failure_tasks"], 0)
        self.assertEqual(
            contract.quality_gate(),
            {
                "quality_evaluator_authorized": False,
                "mechanism_gate_cannot_establish_outer_utility": True,
                "successful_mechanism_gate_only_authorizes_independent_natural_quality_gate_design": True,
                "deepwidebench_or_sota": False,
            },
        )
        self.assertFalse(
            contract.source_policy()[
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )

    def test_synthetic_no_gain_row_repairs_and_preserves_effect_accounting(self):
        row = self._row(contract.task_vector()[0]["opaque_id"])
        receipt = row["content_free_receipt"]
        sparse = row["parent_result"]["parent_result"]["parent_result"]
        self.assertEqual(receipt["quote_aware_repair_applied_count"], 1)
        self.assertEqual(receipt["public_export_completed_count"], 1)
        self.assertFalse(receipt["public_export_failure_present"])
        self.assertEqual(
            row["actual_effect_snapshot"]["model_logical_requests"],
            sparse["content_free_receipt"]["provider_forward_count"],
        )
        self.assertEqual(
            row["predictions"][contract.PRODUCTION_ARM],
            row["predictions"][contract.DETERMINISTIC_FINAL_ARM],
        )

    def test_synthetic_positive_gain_row_preserves_repaired_cell(self):
        row = self._row(
            contract.task_vector()[1]["opaque_id"], positive_gain=True
        )
        receipt = row["content_free_receipt"]
        self.assertEqual(receipt["quote_aware_repair_applied_count"], 1)
        self.assertFalse(receipt["candidate_publication_fallback"])
        self.assertNotEqual(
            row["predictions"][contract.PRODUCTION_ARM],
            row["predictions"][contract.DETERMINISTIC_FINAL_ARM],
        )
        self.assertIn(
            '"country | code"',
            row["predictions"][contract.DETERMINISTIC_FINAL_ARM],
        )

    def test_full_synthetic_denominator_passes_mechanism_and_reliability(self):
        rows = [
            self._row(task["opaque_id"])
            for task in contract.task_vector()
        ]
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["quote_aware_repair_applied_tasks"], 20)
        self.assertEqual(aggregate["public_export_completed_tasks"], 20)
        self.assertEqual(aggregate["public_export_failure_tasks"], 0)
        self.assertTrue(decision["quote_aware_mechanism_gate_passed"])
        self.assertTrue(decision["production_reliability_gate_passed"])
        self.assertTrue(decision["independent_natural_quality_gate_design"])
        self.assertFalse(decision["external_evaluator"])

    def test_gate_fails_closed_on_effect_export_or_credit_tamper(self):
        rows = [self._row(task["opaque_id"]) for task in contract.task_vector()]
        base = runner.aggregate_rows(rows, wall_seconds=2.0)
        for field, value in (
            ("public_export_completed_tasks", 19),
            ("public_export_failure_tasks", 1),
            ("parent_behavior_drift_tasks", 1),
            ("physical_queries", 79),
            ("physical_fetches", 281),
            ("positive_signed_credit_count", 1),
        ):
            changed = copy.deepcopy(base)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                runner.mechanism_decision(changed)

    def test_task_row_outer_failure_and_resealed_tamper_fail_closed(self):
        row = self._row(contract.task_vector()[0]["opaque_id"])
        changed = copy.deepcopy(row)
        changed["prediction_sha256"][contract.PRODUCTION_ARM] = "0" * 64
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(changed)
        fallback = runner._terminal_outer_failure(
            contract.task_vector()[0], RuntimeError("synthetic"), 1.0
        )
        self.assertTrue(runner.validate_task_row(fallback)["failure_as_zero"])

    def test_build_audit_dry_run_is_valid_without_external_effect(self):
        fake_tests = {
            "expected": control.EXPECTED_TESTS,
            "observed": control.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(
            control, "_tests", return_value=fake_tests
        ), mock.patch.object(
            control, "_parents_valid", return_value=True
        ), mock.patch.object(
            control, "_future_pristine", return_value=True
        ):
            value = control.build_audit(now=1, require_clean=False)
        checked = control.validate_build(value)
        self.assertTrue(checked["audit_valid"])
        self.assertEqual(checked["findings"], [])
        self.assertFalse(checked["authorization"]["external_forward"])
        self.assertFalse(checked["authorization"]["external_evaluator"])
        self.assertFalse(
            checked["network_model_search_fetch_evaluator_benchmark_or_api_called"]
        )

    def test_forward_closure_is_label_blind_secret_free_and_evaluator_free(self):
        privileged_names = {
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
        for relative in (contract.CONTRACT, contract.RUNNER, contract.CONTROL):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(relative))
            privileged = {
                str(node.slice.value)
                for node in ast.walk(tree)
                if isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in privileged_names
            }
            self.assertEqual(privileged, set())
            self.assertNotIn("run_official_eval_local", source)
            self.assertIsNone(contract.SECRET.search(source))
        self.assertNotIn(
            "v25175_production_normalizer_external_contract",
            json.dumps(contract.dependency_manifest(ROOT, tracked=False)),
        )


if __name__ == "__main__":
    unittest.main()
