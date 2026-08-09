from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24966_source_fair_quality_gate as gate  # noqa: E402


class V24966SourceFairQualityGateTests(unittest.TestCase):
    def test_population_and_queries_are_fixed_and_fresh(self) -> None:
        self.assertEqual(len(gate.PACKAGES), 20)
        self.assertEqual(len(set(gate.PACKAGES)), 20)
        self.assertEqual(len(gate.task_vector()), 20)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in gate.task_vector()))
        self.assertTrue(all(len(row) == 4 for row in gate.query_vector()))
        self.assertNotEqual(
            gate.payload_sha256(gate.query_vector()),
            gate.payload_sha256(gate.source_gate.query_vector()),
        )

    def test_protocol_freezes_matched_cost_and_no_public_launch(self) -> None:
        value = gate.build_protocol(
            now=1,
            require_clean=False,
            require_pristine=False,
            require_build=False,
        )
        execution = value["execution"]
        self.assertTrue(execution["same_search_response_replayed"])
        self.assertTrue(execution["same_task_local_fetch_union"])
        self.assertEqual(execution["evidence_chars_per_arm"], 24_000)
        self.assertFalse(value["authorization"]["public_exact220_or_other_benchmark_launch"])

    def test_source_policy_is_label_blind_and_entropy_shadow_only(self) -> None:
        policy = gate.source_policy()
        self.assertFalse(
            policy[
                "deepwidebench_manifest_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_used_for_selection_or_credit"])
        self.assertTrue(policy["pypi_gold_endpoint_opened_only_after_prediction_freeze"])

    def test_fixed_evidence_budget(self) -> None:
        leads = [
            {"url": f"https://source{index}.example/page", "title": f"Page {index}"}
            for index in range(6)
        ]
        fetched = {
            gate.canonicalize_url(lead["url"]): {
                "title": lead["title"],
                "raw_content": "x" * 5_000,
            }
            for lead in leads
        }
        evidence, pages, chars = gate._build_evidence(leads, fetched)
        self.assertEqual(len(evidence), gate.EVIDENCE_CHARS)
        self.assertEqual(pages, 6)
        self.assertEqual(chars, 30_000)

    def test_insufficient_evidence_fails_closed(self) -> None:
        leads = [{"url": "https://one.example", "title": "One"}]
        fetched = {
            gate.canonicalize_url(leads[0]["url"]): {"raw_content": "x" * 30_000}
        }
        with self.assertRaises(RuntimeError):
            gate._build_evidence(leads, fetched)

    def test_exact_prediction_metrics(self) -> None:
        gold = {
            "package": "Example-Pkg",
            "version": "2.1.0",
            "date": "2026-08-01",
            "requires_python": ">=3.10, <4",
        }
        prediction = (
            "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
            "|---|---|---|---|\n"
            "| example_pkg | 2.1.0 | 2026-08-01 | >= 3.10,<4 |"
        )
        value = gate.evaluate_prediction(prediction, gold)
        self.assertEqual(value["exact_table_success"], 1)
        self.assertEqual(value["composite"], 1.0)

    def test_wrong_value_is_not_exact_but_partial(self) -> None:
        gold = {
            "package": "example",
            "version": "2.1.0",
            "date": "2026-08-01",
            "requires_python": ">=3.10",
        }
        prediction = (
            "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
            "|---|---|---|---|\n"
            "| example | 2.0.0 | 2026-08-01 | >=3.10 |"
        )
        value = gate.evaluate_prediction(prediction, gold)
        self.assertEqual(value["exact_table_success"], 0)
        self.assertGreater(value["composite"], 0.0)
        self.assertLess(value["composite"], 1.0)

    def test_quality_gate_requires_strict_exact_gain_and_nonregression(self) -> None:
        arms = {
            gate.CONTROL: {
                "evaluator_valid": 20,
                "exact_table_successes": 5,
                "entity_recall": 0.8,
                "row_f1": 0.8,
                "item_f1": 0.7,
                "column_f1": 1.0,
                "composite": 0.825,
                "evaluator_invalid_or_not_run": 0,
            },
            gate.CANDIDATE: {
                "evaluator_valid": 20,
                "exact_table_successes": 6,
                "entity_recall": 0.8,
                "row_f1": 0.8,
                "item_f1": 0.72,
                "column_f1": 1.0,
                "composite": 0.83,
                "evaluator_invalid_or_not_run": 0,
            },
        }
        delta = {
            key: arms[gate.CANDIDATE][key] - arms[gate.CONTROL][key]
            for key in (
                "exact_table_successes",
                "entity_recall",
                "row_f1",
                "item_f1",
                "column_f1",
                "composite",
                "evaluator_invalid_or_not_run",
            )
        }
        metrics = {
            "arms": arms,
            f"{gate.CANDIDATE}_minus_{gate.CONTROL}": delta,
        }
        decision = gate.quality_decision(metrics, {"mechanism_gate_passed": True})
        self.assertTrue(decision["source_fair_quality_gate_go"])
        bad = copy.deepcopy(metrics)
        bad[f"{gate.CANDIDATE}_minus_{gate.CONTROL}"]["item_f1"] = -0.001
        decision = gate.quality_decision(bad, {"mechanism_gate_passed": True})
        self.assertFalse(decision["source_fair_quality_gate_go"])

    def test_mechanism_gate_requires_prediction_change(self) -> None:
        aggregate = {
            "terminal_task_count": 20,
            "completed_task_count": 20,
            "failure_as_zero_task_count": 0,
            "logical_query_rows": 80,
            "search_provider_attempts": 40,
            "search_provider_response_calls": 40,
            "search_http_2xx": 40,
            "transport_failures": 0,
            "hosted_search_deadline_failures": 0,
            "stable_first_seen_selected_leads": 200,
            "cumulative_source_fair_selected_leads": 200,
            "minimum_selected_leads_per_task": {
                gate.CONTROL: 10,
                gate.CANDIDATE: 10,
            },
            "selection_changed_task_count": 20,
            "source_coverage_gain_task_count": 18,
            "stable_first_seen_registrable_sources": 50,
            "cumulative_source_fair_registrable_sources": 100,
            "stable_first_seen_usable_pages": 180,
            "cumulative_source_fair_usable_pages": 180,
            "stable_first_seen_evidence_chars": 20 * 24_000,
            "cumulative_source_fair_evidence_chars": 20 * 24_000,
            "stable_first_seen_model_attempts": 20,
            "cumulative_source_fair_model_attempts": 20,
            "stable_first_seen_model_success": 20,
            "cumulative_source_fair_model_success": 20,
            "stable_first_seen_model_input_tokens": 100_000,
            "stable_first_seen_model_output_tokens": 10_000,
            "cumulative_source_fair_model_input_tokens": 100_000,
            "cumulative_source_fair_model_output_tokens": 10_000,
            "prediction_changed_task_count": 9,
            "planned_union_fetches": 300,
            "actual_hard_fetch_helper_calls": 300,
            "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 0,
            "fetch_deadline_rejections": 0,
        }
        decision = gate.mechanism_decision(aggregate)
        self.assertFalse(decision["mechanism_gate_passed"])
        self.assertIn("prediction_changes_enough_tasks", decision["failed_checks"])
        aggregate["prediction_changed_task_count"] = 10
        self.assertTrue(gate.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_forward_ast_excludes_privileged_names(self) -> None:
        self.assertTrue(gate._forward_ast_safe())
        source = (ROOT / "scripts/v24966_source_fair_quality_gate.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("deepwidebench" in name for name in imports))

    def test_evidence_does_not_fall_back_to_provider_lead_title(self) -> None:
        leads = [
            {
                "url": f"https://source{index}.example/page",
                "title": "UNTRUSTED PROVIDER NARRATIVE",
            }
            for index in range(6)
        ]
        fetched = {
            gate.canonicalize_url(lead["url"]): {
                "title": "Fetched title",
                "raw_content": "x" * 5_000,
            }
            for lead in leads
        }
        evidence, _pages, _chars = gate._build_evidence(leads, fetched)
        self.assertNotIn("UNTRUSTED PROVIDER NARRATIVE", evidence)

    def test_arm_order_is_deterministic_and_balanced(self) -> None:
        orders = [gate._arm_order(row["opaque_id"]) for row in gate.task_vector()]
        self.assertTrue(all(set(order) == set(gate.ARMS) for order in orders))
        self.assertEqual(orders.count(gate.ARMS), 10)
        self.assertEqual(orders.count(gate.ARMS[::-1]), 10)

    def test_protocol_seal_rejects_tamper(self) -> None:
        value = gate.build_protocol(
            now=1,
            require_clean=False,
            require_pristine=False,
            require_build=False,
        )
        value["execution"]["evidence_chars_per_arm"] = 1
        with self.assertRaises(RuntimeError):
            gate.validate_protocol(value, require_manifest=False)

    def test_valid_forward_audit_may_record_mechanism_no_go(self) -> None:
        value = {
            "role": "v24966_source_fair_quality_forward_audit",
            "protocol_id": gate.PROTOCOL_ID,
            "audit_valid": True,
            "findings": [],
            "checks": {"artifact_integrity": True},
            "mechanism_decision": {"mechanism_gate_passed": False},
            "authorization": {
                "postfreeze_external_evaluator_protocol": False,
                "public_exact220_or_other_benchmark_launch": False,
            },
        }
        value["audit_payload_sha256"] = gate.payload_sha256(value)
        self.assertFalse(
            gate.validate_forward_audit(value)["authorization"][
                "postfreeze_external_evaluator_protocol"
            ]
        )


if __name__ == "__main__":
    unittest.main()
