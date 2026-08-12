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

from deepwide_agent import v25191_export_tolerant_quality_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts import run_v25191_export_tolerant_quality as runner  # noqa: E402
from test_v25151_generic_record_quote_candidate_runtime import GenericRecordSearch  # noqa: E402
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    CANDIDATE_CONTENT,
    NO_GAIN_CONTENT,
    EscapedProductionModel,
)
from unittest import mock


class V25191NaturalQuoteQualityTests(unittest.TestCase):
    def _row(self, opaque_id: str, *, escaped: bool = True) -> dict:
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
            inner = EscapedProductionModel() if escaped else EscapedProductionModel(
                "| Domain | Type | TLD Manager |\n"
                "| --- | --- | --- |\n"
                "| .in | country-code | 111 |"
            )
            model = runner.accounting._EffectAccountingModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(question, phase, content=NO_GAIN_CONTENT)
                for phase in contract.runtime.PHASES
            }
            # Test doubles expose the same effect counters used by the runner.
            for client in searches.values():
                client.actual_search_invocations = 0
                client.actual_logical_query_count = 0
                client.actual_fetch_invocations = 0
                client.actual_fetch_request_count = 0
                original_search = client.search_many
                original_fetch = client.fetch_urls

                def search_many(queries, _original=original_search, _client=client, **kwargs):
                    values = list(queries)
                    _client.actual_search_invocations += 1
                    _client.actual_logical_query_count += len(values)
                    return _original(values, **kwargs)

                def fetch_urls(requests, _original=original_fetch, _client=client):
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

    def test_population_is_natural_prompt_and_enriched_scope_is_bound(self):
        tasks = contract.task_vector()
        selection = contract.validate_selection(ROOT, tracked=True)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(selection["identity_history_zero_hit_count"], 20)
        self.assertTrue(selection["preselection_enriched_for_license_literal_pipe"])
        self.assertFalse(selection["preselection_is_unconditional_natural_population"])
        for task, package in zip(tasks, contract.PACKAGES, strict=True):
            self.assertIn(f"<PACKAGE>{package}</PACKAGE>", task["question"])
            self.assertNotIn(r"\|", task["question"])
            self.assertNotIn("https://", task["question"])

    def test_same_response_active_row_is_changed_and_effect_bound(self):
        row = self._row(contract.task_vector()[0]["opaque_id"])
        receipt = row["content_free_receipt"]
        self.assertTrue(receipt["same_raw_counterfactual_active"])
        self.assertTrue(receipt["prediction_changed"])
        self.assertIn("Unknown", row["predictions"][contract.CONTROL_ARM])
        self.assertIn('"country | code"', row["predictions"][contract.CANDIDATE_ARM])
        sparse = row["parent_result"]["parent_result"]["parent_result"][
            "parent_result"
        ]
        self.assertEqual(
            row["actual_effect_snapshot"]["model_logical_requests"],
            sparse["content_free_receipt"]["provider_forward_count"],
        )

    def test_synthetic_full_denominator_passes_mechanism_gate(self):
        rows = [self._row(task["opaque_id"]) for task in contract.task_vector()]
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["same_raw_counterfactual_active_tasks"], 20)
        self.assertEqual(aggregate["prediction_changed_tasks"], 20)
        self.assertTrue(decision["same_response_mechanism_gate_passed"])
        self.assertTrue(decision["postfreeze_external_evaluator_design"])
        self.assertFalse(decision["external_evaluator_now"])

    def test_parent_safe_export_failure_remains_terminal_and_gate_valid(self):
        question = (
            "Retrieve one record. Return exactly one Markdown table and no prose. "
            "Columns exactly: Domain | Type | TLD Manager."
        )
        task = {"opaque_id": contract.task_vector()[0]["opaque_id"], "question": question}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = EscapedProductionModel()
            model = runner.accounting._EffectAccountingModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(
                    question, phase, content=CANDIDATE_CONTENT
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

                def search_many(queries, _original=original_search, _client=client, **kwargs):
                    values = list(queries)
                    _client.actual_search_invocations += 1
                    _client.actual_logical_query_count += len(values)
                    return _original(values, **kwargs)

                def fetch_urls(requests, _original=original_fetch, _client=client):
                    values = list(requests)
                    _client.actual_fetch_invocations += 1
                    _client.actual_fetch_request_count += len(values)
                    return _original(values)

                client.search_many = search_many
                client.fetch_urls = fetch_urls
            with mock.patch.object(
                contract.runtime.effect_parent,
                "export_public_predictions",
                side_effect=RuntimeError("synthetic export failure"),
            ):
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
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["runtime_completed"])
        receipt = checked["content_free_receipt"]
        self.assertTrue(receipt["parent_public_export_failure_present"])
        self.assertTrue(receipt["parent_public_export_fallback_to_safe_production"])

    def test_gate_fails_closed_on_activation_effect_credit_or_export_tamper(self):
        rows = [self._row(task["opaque_id"]) for task in contract.task_vector()]
        base = runner.aggregate_rows(rows, wall_seconds=2.0)
        for field, value in (
            ("activation_and_change", 9),
            ("additional_effect_tasks", 1),
            ("unsafe_public_export_failure_tasks", 1),
            ("positive_signed_credit_count", 1),
        ):
            changed = copy.deepcopy(base)
            if field == "activation_and_change":
                changed["same_raw_counterfactual_active_tasks"] = value
                changed["prediction_changed_tasks"] = value
            else:
                changed[field] = value
            with self.subTest(field=field):
                if field == "positive_signed_credit_count":
                    with self.assertRaises(RuntimeError):
                        runner.mechanism_decision(changed)
                else:
                    decision = runner.mechanism_decision(changed)
                    self.assertFalse(decision["same_response_mechanism_gate_passed"])

    def test_outer_failure_is_fixed_zero_and_tamper_fails_closed(self):
        task = contract.task_vector()[0]
        row = runner._terminal_outer_failure(task, RuntimeError("synthetic"), 1.0)
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["failure_as_zero"])
        changed = copy.deepcopy(checked)
        changed["predictions"][contract.CANDIDATE_ARM] = "changed"
        import hashlib

        changed["prediction_sha256"][contract.CANDIDATE_ARM] = hashlib.sha256(
            b"changed"
        ).hexdigest()
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(changed)

    def test_forward_closure_is_label_blind_secret_free_and_evaluator_free(self):
        privileged = {
            "category", "question_type", "task_category", "split",
            "ground_truth", "gold", "answer_key", "score", "reward",
        }
        for relative in contract.forward_dependency_closure(ROOT):
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
