from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24973_identity_bound_field_quality_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import finalize_v24973_identity_bound_field_quality as finalizer  # noqa: E402
from scripts import run_v24973_identity_bound_field_quality as runner  # noqa: E402


class V24973IdentityBoundFieldQualityTests(unittest.TestCase):
    def test_population_is_fixed_fresh_and_visible_only(self) -> None:
        self.assertEqual(len(contract.TASKS), 20)
        self.assertEqual(len(set(contract.TASKS)), 20)
        self.assertFalse({project for project, _repo in contract.TASKS} & contract.PRIOR_PROJECTS)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in contract.task_vector()))

    def test_endpoint_vectors_separate_forward_html_from_postfreeze_api(self) -> None:
        self.assertTrue(all(row[0].startswith("https://pypi.org/pypi/") for row in contract.endpoint_vector()))
        self.assertTrue(all(row[1].startswith("https://github.com/") for row in contract.endpoint_vector()))
        self.assertTrue(all(row[1].startswith("https://api.github.com/repos/") for row in contract.gold_endpoint_vector()))
        self.assertNotEqual(contract.endpoint_vector(), contract.gold_endpoint_vector())

    def test_arm_order_is_exactly_balanced(self) -> None:
        orders = contract.arm_order_vector()
        self.assertTrue(all(set(order) == set(contract.ARMS) for order in orders))
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in orders), 10)

    def test_build_protocol_freezes_matched_cost_and_no_public_launch(self) -> None:
        value = contract.validate_protocol_untracked(
            ROOT, contract.build_protocol_untracked(ROOT, now=1)
        )
        execution = value["execution"]
        self.assertEqual(execution["evidence_chars_per_arm"], 16_000)
        self.assertEqual(execution["namespace_evidence_chars"], 8_000)
        self.assertEqual(execution["model_concurrency"], 8)
        self.assertTrue(execution["exactly_one_model_attempt_per_arm"])
        self.assertFalse(value["authorization"]["public_exact220_or_sota"])

    def test_source_policy_is_label_blind_and_entropy_shadow_only(self) -> None:
        policy = contract.source_policy()
        self.assertFalse(policy["deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_credit"])
        self.assertTrue(policy["prediction_freeze_before_evaluator_metrics_or_quality_decision"])

    def test_github_html_projection_binds_exact_latest_tag_and_date(self) -> None:
        repository = "owner/repo"
        html = """
        <html><head><title>Releases · owner/repo · GitHub</title></head><body>
        <a href="/owner/repo/releases/tag/v2.0">v2.0</a>
        <a href="/owner/repo/releases/latest">Latest</a>
        <relative-time datetime="2026-08-01T12:00:00Z">1 Aug</relative-time>
        </body></html>
        """
        title, projection, tag = runner._github_release_projection(html, repository)
        self.assertEqual(title, "Releases · owner/repo · GitHub")
        self.assertEqual(tag, "v2.0")
        self.assertIn("v2.0 2026-08-01\nLatest", projection)
        version_html = html.replace(">v2.0</a>", ">Version v2.0</a>")
        self.assertEqual(
            runner._github_release_projection(version_html, repository)[2], "v2.0"
        )
        named_html = html.replace(">v2.0</a>", ">Bug-fix Release</a>")
        self.assertEqual(
            runner._github_release_projection(named_html, repository)[2], "v2.0"
        )

    def test_github_html_projection_rejects_wrong_identity_and_missing_latest(self) -> None:
        wrong = "<title>Releases · other/repo · GitHub</title>"
        with self.assertRaises(ValueError):
            runner._github_release_projection(wrong, "owner/repo")
        missing = "<title>Releases · owner/repo · GitHub</title><a href='/owner/repo/releases/tag/v1'>v1</a>"
        with self.assertRaises(ValueError):
            runner._github_release_projection(missing, "owner/repo")

    def test_raw_evidence_is_exactly_namespace_balanced(self) -> None:
        pages = [{"text": "p" * 9000}, {"text": "g" * 9000}]
        value = runner._raw_balanced_evidence(pages)
        self.assertEqual(len(value), 16_000)
        self.assertEqual(value[:11], "[PYPI JSON]")
        self.assertEqual(value[8_000:8_022], "[GITHUB RELEASES HTML]")

    def _row(self, *, changed: bool = True) -> dict:
        predictions = {
            contract.CONTROL_ARM: "control",
            contract.CANDIDATE_ARM: "candidate" if changed else "control",
        }
        value = {
            "artifact_version": 1,
            "role": "v24973_identity_bound_field_task_result",
            "protocol_id": contract.PROTOCOL_ID,
            "opaque_id": contract.task_vector()[0]["opaque_id"],
            "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
            "terminal": True,
            "completed": True,
            "status": "completed",
            "failure_as_zero": False,
            "fetch_attempts": 2,
            "fetch_successes": 2,
            "fetch_status_counts": {"200": 2},
            "search_tool_calls": 0,
            "github_api_calls": 0,
            "compact_receipt": {
                "exact_authority_page_count": 2,
                "identity_bound_page_count": 2,
                "identity_mismatch_page_count": 0,
                "malformed_page_count": 0,
                "field_observation_count": 4,
                "unique_bound_field_count": 4,
                "unknown_field_count": 0,
                "conflicting_field_count": 0,
                "compact_prefix_chars": 400,
            },
            "compact_record_admitted": True,
            "candidate_evidence_changed": True,
            "evidence_chars": {arm: 16_000 for arm in contract.ARMS},
            "model_success": {arm: True for arm in contract.ARMS},
            "model_attempt_counts": {arm: 1 for arm in contract.ARMS},
            "model_usage": {arm: {"total_tokens": 10} for arm in contract.ARMS},
            "predictions": predictions,
            "prediction_sha256": {arm: contract.payload_sha256(predictions[arm]) for arm in contract.ARMS},
            "prediction_changed": changed,
            "wall_seconds": 1.0,
            "same_exact_address_page_bytes_for_both_arms": True,
            "control_has_fixed_equal_namespace_raw_char_quota": True,
            "candidate_prefixes_compact_record_then_same_ordered_raw_evidence": True,
            "same_evidence_chars_prompt_model_output_cap": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_credit": False,
            "retry_resume_skip_or_selective_rerun": False,
            "contains_question_field_value_url_page_answer_or_credential": False,
        }
        return contract.seal(value, "result_payload_sha256")

    def test_task_row_validation_rejects_tamper(self) -> None:
        row = self._row()
        runner.validate_task_row(row)
        changed = copy.deepcopy(row)
        changed["github_api_calls"] = 1
        with self.assertRaises(ValueError):
            runner.validate_task_row(changed)

    def test_mechanism_gate_requires_ten_prediction_changes(self) -> None:
        expected = contract.gates()["mechanism"]
        aggregate = {
            "terminal_tasks": 20,
            "completed_tasks": 20,
            "fallback_tasks": 0,
            "fetch_attempts": 40,
            "successful_shared_fetches": 40,
            "admitted_compact_records": 20,
            "candidate_evidence_changed_tasks": 20,
            "prediction_changed_tasks": 9,
            "unique_bound_fields": 80,
            "field_conflicts": 0,
            "evidence_chars": {arm: expected["evidence_chars_per_arm"] for arm in contract.ARMS},
        }
        for arm in contract.ARMS:
            aggregate[f"{arm}_model_successes"] = 20
            aggregate[f"{arm}_model_attempts"] = 20
        decision = runner.mechanism_decision(aggregate)
        self.assertFalse(decision["mechanism_gate_passed"])
        self.assertIn("minimum_prediction_change", decision["failed_checks"])
        aggregate["prediction_changed_tasks"] = 10
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_exact_prediction_metrics(self) -> None:
        gold = {
            "package": "demo-pkg", "version": "2.0", "requires_python": ">=3.10",
            "github_tag": "v2.0", "github_date": "2026-08-01",
        }
        prediction = (
            "| Package | PyPI latest version | Requires-Python | GitHub latest release tag | GitHub latest release date (YYYY-MM-DD) |\n"
            "|---|---|---|---|---|\n| demo_pkg | 2.0 | >= 3.10 | V2.0 | 2026-08-01 |"
        )
        metrics = finalizer.evaluate_prediction(prediction, gold)
        self.assertEqual(metrics["exact_table_success"], 1)
        self.assertEqual(metrics["composite"], 1.0)

    def test_quality_gate_requires_strict_exact_gain_and_nonregression(self) -> None:
        keys = ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")
        arms = {
            contract.CONTROL_ARM: {"evaluator_valid": 20, "exact_table_successes": 5, "evaluator_invalid_or_not_run": 0, "fallback_tasks": 0, **{key: 0.8 for key in keys}},
            contract.CANDIDATE_ARM: {"evaluator_valid": 20, "exact_table_successes": 6, "evaluator_invalid_or_not_run": 0, "fallback_tasks": 0, **{key: 0.81 for key in keys}},
        }
        delta = {key: arms[contract.CANDIDATE_ARM][key] - arms[contract.CONTROL_ARM][key] for key in ("exact_table_successes", *keys, "evaluator_invalid_or_not_run", "fallback_tasks")}
        metrics = {"arms": arms, f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta}
        self.assertTrue(finalizer.quality_decision(metrics, {"mechanism_gate_passed": True})["identity_bound_field_quality_gate_go"])
        delta["item_f1"] = -0.001
        self.assertFalse(finalizer.quality_decision(metrics, {"mechanism_gate_passed": True})["identity_bound_field_quality_gate_go"])

    def test_gold_fetch_attempts_both_endpoints_after_first_failure(self) -> None:
        class Response:
            def __init__(self, status: int, value: object) -> None:
                self.status_code = status
                self.content = b"payload"
                self._value = value
            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    raise requests.HTTPError("failed")
            def json(self) -> object:
                return self._value
        import requests
        responses = [
            Response(503, {}),
            Response(200, {"draft": False, "prerelease": False, "tag_name": "v1", "published_at": "2026-08-01T00:00:00Z", "html_url": f"https://github.com/{contract.TASKS[0][1]}/releases/tag/v1"}),
        ]
        with mock.patch.object(finalizer.requests, "get", side_effect=responses):
            value = finalizer._fetch_gold(0)
        self.assertEqual(value["pypi_attempts"], 1)
        self.assertEqual(value["github_attempts"], 1)
        self.assertFalse(value["valid"])

    def test_forward_sources_have_no_privileged_or_evaluator_capability(self) -> None:
        for relative in (contract.SOURCE, contract.EXTRACTOR, contract.RUNTIME):
            path = ROOT / relative
            self.assertEqual(semantic_audit._accesses(path, ROOT), [])
            self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])
        source = (ROOT / contract.RUNTIME).read_text(encoding="utf-8")
        imports = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("deepwidebench" in name or "finalize" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
