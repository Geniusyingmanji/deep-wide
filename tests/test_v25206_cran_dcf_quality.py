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
    v25200_post_effect_tolerant_vertical_receipt as compatibility,
)
from deepwide_agent import (  # noqa: E402
    v25206_cran_dcf_quality_contract as contract,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts import run_v25206_cran_dcf_quality as runner  # noqa: E402
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    EscapedProductionModel,
    NO_GAIN_CONTENT,
)


class V25206PostEffectTolerantQualityTests(unittest.TestCase):
    def _row(self, opaque_id: str) -> dict:
        runner._ensure_compatibility_validation()
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

    def _rows(self) -> list[dict]:
        return [self._row(task["opaque_id"]) for task in contract.task_vector()]

    def test_fresh_population_diagnosis_and_exact_compatibility_are_bound(self) -> None:
        tasks = contract.task_vector()
        selection = contract.validate_selection(ROOT, tracked=True)
        diagnosis = contract._validate_diagnosis(ROOT, tracked=True)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(selection["identity_history_zero_hit_count"], 20)
        self.assertFalse(selection["v25195_population_reuse"])
        self.assertFalse(selection["v25199_population_reuse"])
        self.assertFalse(selection["v25203_population_reuse"])
        self.assertTrue(
            diagnosis["diagnosis"][
                "v25203_quality_outcome_is_evaluator_invalid_not_model_no_go"
            ]
        )
        self.assertEqual(
            compatibility._FROZEN_VALIDATE.__module__,
            "deepwide_agent.v25158_vertical_key_value_candidate_runtime",
        )
        self.assertIn(
            invariant_observer.parent.validate_receipt,
            {
                compatibility.validate_receipt,
                runner.failure_probe._observed_validate,
            },
        )
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

    def test_zero_application_aggregate_and_mechanism_gate_are_valid(self) -> None:
        rows = self._rows()
        sidecar = runner.build_compatibility_aggregate(
            rows, [None] * contract.TASK_COUNT, [False] * contract.TASK_COUNT
        )
        aggregate = runner.aggregate_rows(
            rows, wall_seconds=2.0, compatibility_aggregate=sidecar
        )
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(sidecar["compatibility_applied_tasks"], 0)
        self.assertEqual(aggregate["physical_queries"], 80)
        self.assertTrue(
            decision["checks"][
                "post_effect_compatibility_observability_complete"
            ]
        )
        self.assertTrue(decision["same_response_mechanism_gate_passed"])

    def test_application_is_aggregate_only_and_cannot_mask_outer_failure(self) -> None:
        rows = self._rows()
        sidecar = runner.build_compatibility_aggregate(
            rows, [None] * contract.TASK_COUNT, [True, *([False] * 19)]
        )
        encoded = json.dumps(sidecar, ensure_ascii=False)
        self.assertEqual(sidecar["compatibility_applied_tasks"], 1)
        self.assertEqual(
            sidecar["compatibility_applied_runtime_completed_tasks"], 1
        )
        for task in contract.task_vector():
            self.assertNotIn(task["opaque_id"], encoded)
        for package in contract.PACKAGES:
            self.assertNotIn(package, encoded)

        failure = failure_observer.observe_outer_failure(
            ValueError("V2.51.58 vertical key-value candidate receipt drifted"),
            outer_failure_stage="runtime",
        )
        rows[0] = runner._terminal_outer_failure(
            contract.task_vector()[0], failure, 1.0
        )
        observation = invariant_observer.observe_receipt_invariants(
            self._receipt(self._rows()[0])
        )
        changed = copy.deepcopy(observation)
        changed["violation_codes"] = ["grammar_accounting"]
        changed["violation_count"] = 1
        changed["frozen_validator_expected_to_accept"] = False
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = contract.payload_sha256(changed)
        sidecar = runner.build_compatibility_aggregate(
            rows, [changed, *([None] * 19)], [True, *([False] * 19)]
        )
        aggregate = runner.aggregate_rows(
            rows, wall_seconds=2.0, compatibility_aggregate=sidecar
        )
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(
            sidecar["compatibility_applied_outer_failure_tasks"], 1
        )
        self.assertFalse(
            decision["checks"][
                "post_effect_compatibility_observability_complete"
            ]
        )

    @staticmethod
    def _receipt(row: dict) -> dict:
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

    def test_aggregate_tamper_credit_count_or_unknown_code_fails_closed(self) -> None:
        rows = self._rows()
        sidecar = runner.build_compatibility_aggregate(
            rows, [None] * 20, [False] * 20
        )
        for kind in ("count", "code", "credit"):
            changed = copy.deepcopy(sidecar)
            if kind == "count":
                changed["compatibility_applied_tasks"] = 1
            elif kind == "code":
                changed["residual_v25158_violation_code_counts"] = {
                    "private_value": 1
                }
                changed["residual_v25158_violation_event_count"] = 1
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("aggregate_payload_sha256")
            changed["aggregate_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                runner.validate_compatibility_aggregate(changed)

    def test_composed_install_accepts_exact_safe_state_and_observes_residuals(self) -> None:
        base = self._receipt(self._row(contract.task_vector()[0]["opaque_id"]))
        safe = copy.deepcopy(base)
        safe["parent_post_effect_failure_present"] = True
        safe.pop("receipt_payload_sha256")
        safe["receipt_payload_sha256"] = contract.payload_sha256(safe)
        runner.install_runtime_observers()
        compatibility_token = compatibility.begin_task()
        failure_token = runner.failure_probe.begin_task()
        try:
            self.assertEqual(
                invariant_observer.parent.validate_receipt(safe), safe
            )
            self.assertTrue(compatibility.compatibility_applied())
            self.assertIsNone(runner.failure_probe.failure_observation())
        finally:
            runner.failure_probe.end_task(failure_token)
            compatibility.end_task(compatibility_token)

        unsafe = copy.deepcopy(safe)
        unsafe["provider_failure_present"] = True
        unsafe.pop("receipt_payload_sha256")
        unsafe["receipt_payload_sha256"] = contract.payload_sha256(unsafe)
        compatibility_token = compatibility.begin_task()
        failure_token = runner.failure_probe.begin_task()
        try:
            with self.assertRaises(ValueError):
                invariant_observer.parent.validate_receipt(unsafe)
            self.assertFalse(compatibility.compatibility_applied())
            self.assertIsNotNone(runner.failure_probe.failure_observation())
        finally:
            runner.failure_probe.end_task(failure_token)
            compatibility.end_task(compatibility_token)

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
        self.assertIn(contract.COMPATIBILITY, closure)
        self.assertNotIn(contract.DCF_PARSER, closure)
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
