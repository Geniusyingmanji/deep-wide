from __future__ import annotations

import ast
import copy
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24968_requirement_quality_gate as gate  # noqa: E402


class V24968RequirementQualityGateTests(unittest.TestCase):
    def test_population_is_fresh_and_runtime_vector_is_visible_only(self) -> None:
        self.assertEqual(gate.TASK_COUNT, 21)
        self.assertEqual(len(set(gate.TASKS)), 21)
        self.assertFalse(
            {project for project, _repo in gate.TASKS}
            & (gate.DEVELOPMENT_EXCLUSIONS | gate.PRIOR_EXTERNAL_EXCLUSIONS)
        )
        self.assertTrue(
            all(set(task) == {"opaque_id", "question"} for task in gate.task_vector())
        )

    def test_visible_identity_parser_and_query_vector(self) -> None:
        self.assertEqual(
            gate.parse_visible_identity(gate.task_vector()[0]["question"]),
            gate.TASKS[0],
        )
        self.assertEqual(len(gate.query_vector()), 21)
        self.assertTrue(all(len(row) == 4 for row in gate.query_vector()))
        self.assertNotEqual(
            gate.payload_sha256(gate.query_vector()),
            gate.payload_sha256(gate.parent.query_vector()),
        )

    def test_arm_first_position_is_exactly_balanced(self) -> None:
        orders = gate.arm_order_vector()
        self.assertTrue(all(set(order) == set(gate.ARMS) for order in orders))
        self.assertEqual(Counter(order[0] for order in orders), Counter({arm: 7 for arm in gate.ARMS}))

    def test_protocol_freezes_three_arm_matched_cost_and_no_public_launch(self) -> None:
        value = gate.build_protocol(
            now=1,
            require_clean=False,
            require_pristine=False,
            require_build=False,
        )
        execution = value["execution"]
        self.assertEqual(execution["arms"], list(gate.ARMS))
        self.assertEqual(execution["evidence_chars_per_arm"], 6_000)
        self.assertEqual(execution["candidate_requirement_quota_chars"], 2_500)
        self.assertTrue(execution["same_search_responses_for_all_arms"])
        self.assertFalse(value["authorization"]["public_exact220_or_other_benchmark_launch"])

    def test_exact_prediction_metrics(self) -> None:
        gold = {
            "package": "example-pkg",
            "version": "2.0",
            "requires_python": ">=3.10, <4",
            "github_tag": "v2.0",
            "github_date": "2026-08-01",
        }
        prediction = (
            "| Package | PyPI latest version | Requires-Python | GitHub latest release tag | GitHub latest release date (YYYY-MM-DD) |\n"
            "|---|---|---|---|---|\n"
            "| example_pkg | 2.0 | >=3.10,<4 | V2.0 | 2026-08-01 |"
        )
        value = gate.evaluate_prediction(prediction, gold)
        self.assertEqual(value["exact_table_success"], 1)
        self.assertEqual(value["composite"], 1.0)

    def test_partial_prediction_is_not_exact(self) -> None:
        gold = {
            "package": "example",
            "version": "2.0",
            "requires_python": ">=3.10",
            "github_tag": "v2.0",
            "github_date": "2026-08-01",
        }
        prediction = (
            "| Package | PyPI latest version | Requires-Python | GitHub latest release tag | GitHub latest release date (YYYY-MM-DD) |\n"
            "|---|---|---|---|---|\n"
            "| example | 2.0 | >=3.10 | v1.9 | 2026-07-01 |"
        )
        value = gate.evaluate_prediction(prediction, gold)
        self.assertEqual(value["exact_table_success"], 0)
        self.assertGreater(value["composite"], 0.0)
        self.assertLess(value["composite"], 1.0)

    def _mechanism_aggregate(self) -> dict[str, object]:
        value: dict[str, object] = {
            "terminal_task_count": 21,
            "completed_task_count": 21,
            "failure_as_zero_task_count": 0,
            "logical_query_rows": 84,
            "search_provider_attempts": 42,
            "search_provider_response_calls": 42,
            "search_http_2xx": 42,
            "search_transport_failures": 0,
            "hosted_search_deadline_failures": 0,
            "minimum_selected_leads_per_task": {arm: 6 for arm in gate.ARMS},
            "requirement_selection_changed_vs_stable": 18,
            "requirement_selection_changed_vs_source_fair": 18,
            "requirement_evidence_changed_vs_stable": 21,
            "requirement_evidence_changed_vs_source_fair": 21,
            "candidate_requirement_coverage_task": 20,
            "candidate_both_requirement_quota_task": 18,
            "requirement_prediction_changed_vs_stable": 15,
            "requirement_prediction_changed_vs_source_fair": 15,
            "planned_union_fetches": 180,
            "actual_hard_fetch_helper_calls": 178,
            "fetch_deadline_rejections": 2,
        }
        for arm in gate.ARMS:
            value[f"{arm}_evidence_chars"] = 21 * 6_000
            value[f"{arm}_model_attempts"] = 21
            value[f"{arm}_model_success"] = 21
            value[f"{arm}_model_input_tokens"] = 100_000
            value[f"{arm}_model_output_tokens"] = 10_000
        return value

    def test_mechanism_gate_allows_irrelevant_raw_fetch_failure(self) -> None:
        aggregate = self._mechanism_aggregate()
        self.assertTrue(gate.mechanism_decision(aggregate)["mechanism_gate_passed"])
        aggregate["requirement_aware_authority_evidence_chars"] = 20 * 6_000
        decision = gate.mechanism_decision(aggregate)
        self.assertFalse(decision["mechanism_gate_passed"])
        self.assertIn("fixed_evidence_budget_all_arms", decision["failed_checks"])

    def test_quality_gate_requires_strict_gain_over_both_controls(self) -> None:
        keys = ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")
        arms = {
            gate.STABLE: {"evaluator_valid": 21, "exact_table_successes": 5, **{key: 0.7 for key in keys}},
            gate.SOURCE_FAIR: {"evaluator_valid": 21, "exact_table_successes": 6, **{key: 0.71 for key in keys}},
            gate.REQUIREMENT: {"evaluator_valid": 21, "exact_table_successes": 7, **{key: 0.72 for key in keys}},
        }
        for arm in arms.values():
            arm["evaluator_invalid_or_not_run"] = 0
        comparisons = {}
        for control in (gate.STABLE, gate.SOURCE_FAIR):
            comparisons[f"{gate.REQUIREMENT}_minus_{control}"] = {
                key: arms[gate.REQUIREMENT][key] - arms[control][key]
                for key in ("exact_table_successes", *keys, "evaluator_invalid_or_not_run")
            }
        metrics = {"arms": arms, "comparisons": comparisons}
        self.assertTrue(
            gate.quality_decision(metrics, {"mechanism_gate_passed": True})[
                "requirement_quality_gate_go"
            ]
        )
        bad = copy.deepcopy(metrics)
        bad["comparisons"][f"{gate.REQUIREMENT}_minus_{gate.SOURCE_FAIR}"]["exact_table_successes"] = 0
        self.assertFalse(
            gate.quality_decision(bad, {"mechanism_gate_passed": True})[
                "requirement_quality_gate_go"
            ]
        )

    def test_valid_forward_audit_can_record_mechanism_no_go(self) -> None:
        value = {
            "role": "v24968_requirement_quality_forward_audit",
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

    def test_gold_attempts_both_endpoints_even_if_pypi_fails(self) -> None:
        class Response:
            def __init__(self, *, status: int, value: object) -> None:
                self.status_code = status
                self.content = b"payload"
                self._value = value

            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    raise gate.requests.HTTPError("failed")

            def json(self) -> object:
                return self._value

        responses = [
            Response(status=503, value={}),
            Response(
                status=200,
                value={"tag_name": "v1.0", "published_at": "2026-08-01T00:00:00Z"},
            ),
        ]
        with mock.patch.object(gate.requests, "get", side_effect=responses):
            value = gate._fetch_gold(0)
        self.assertEqual(value["pypi_attempts"], 1)
        self.assertEqual(value["github_attempts"], 1)
        self.assertFalse(value["valid"])

    def test_forward_ast_excludes_evaluator_and_privileged_names(self) -> None:
        self.assertTrue(gate._forward_ast_safe())
        source = (ROOT / gate.SCRIPT).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("deepwidebench" in name for name in imports))

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


if __name__ == "__main__":
    unittest.main()
