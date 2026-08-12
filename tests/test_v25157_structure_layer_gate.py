from __future__ import annotations

import ast
import contextlib
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25155_projection_structure_observer as observer  # noqa: E402
from deepwide_agent import v25157_structure_layer_gate_contract as contract  # noqa: E402
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v25157_structure_layer_gate as control  # noqa: E402
from scripts import run_v25157_structure_layer_gate as runner  # noqa: E402


def html() -> str:
    return (
        "<html><head><title>Public package page</title></head><body>"
        "<table><tr><th>Package:</th><td>example</td></tr>"
        "<tr><th>Version:</th><td>1.0</td></tr>"
        "<tr><th>License:</th><td>MIT</td></tr>"
        "<tr><th>NeedsCompilation:</th><td>no</td></tr></table>"
        "</body></html>"
    )


class Response:
    def __init__(self, *, body: bytes, status: int = 200, url: str | None = None):
        self.body = body
        self.status_code = status
        self.url = url or contract.endpoint_vector()[0]
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size: int):
        for start in range(0, len(self.body), chunk_size):
            yield self.body[start : start + chunk_size]


def success_row(position: int, *, projected: bool = True) -> dict:
    raw = "<table><tr><td>A:</td><td>B</td></tr></table>"
    extracted = "A: | B"
    projected_text = extracted if projected else "plain"
    counts = observer.aggregate_observations(
        [observer.observe_structure(raw, extracted, projected_text)]
    )["counts"]
    value = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_task_receipt",
        "protocol_id": contract.PROTOCOL_ID,
        "task_position": position,
        "terminal": True,
        "fetch_attempts": 1,
        "fetch_success": True,
        "http_status": 200,
        "structure_counts": counts,
        "failure_as_zero": False,
        "failure_stage": "none",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_hosted_search_or_evaluator_called": False,
        "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    return runner.validate_task_row(contract.seal(value, "result_payload_sha256"))


class V25157StructureLayerGateTests(unittest.TestCase):
    def test_population_selection_is_bound_and_question_hides_identity(self) -> None:
        selection = contract.validate_population_selection(ROOT, tracked=False)
        self.assertTrue(selection["audit_valid"])
        self.assertEqual(selection["identity_history_zero_hit_count"], 20)
        self.assertEqual(len(contract.PACKAGES), 20)
        for package, task in zip(
            contract.PACKAGES, contract.task_vector(), strict=True
        ):
            self.assertNotIn(package.casefold(), task["question"].casefold())
            self.assertEqual(
                tuple(extract_robust_visible_columns(task["question"])),
                contract.COLUMNS,
            )

    def test_protocol_is_fixed_zero_model_and_resealed_tamper_fails(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(value["execution"]["model_calls"], 0)
        self.assertEqual(value["execution"]["hosted_search_calls"], 0)
        self.assertEqual(value["execution"]["evaluator_calls"], 0)
        self.assertFalse(value["authorization"]["model_or_evaluator_on_this_population"])
        with mock.patch.object(
            contract, "dependency_manifest", return_value=value["source_manifest"]
        ), mock.patch.object(
            contract, "watcher_snapshot", return_value=value["protected_watchers"]
        ), mock.patch.object(
            contract, "sha256", side_effect=lambda path: (
                "0" * 64
                if Path(path).name == contract.BUILD_AUDIT.name
                else value["freshness"]["population_selection_audit_sha256"]
            )
        ):
            self.assertEqual(contract.validate_protocol(ROOT, value), value)
            changed = copy.deepcopy(value)
            changed["execution"]["model_calls"] = 1
            changed = contract.seal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                contract.validate_protocol(ROOT, changed)

    def test_single_fetch_produces_three_layer_content_free_receipt(self) -> None:
        endpoint = contract.endpoint_vector()[0]
        response = Response(body=html().encode(), url=endpoint)
        with mock.patch.object(runner.requests, "get", return_value=response) as get:
            value = runner._fetch_one(0)
        get.assert_called_once()
        self.assertTrue(value["fetch_success"])
        counts = value["structure_counts"]
        self.assertEqual(counts["observed_page_count"], 1)
        self.assertEqual(counts["raw_structured_page_count"], 1)
        self.assertGreaterEqual(counts["raw_table_count"], 1)
        self.assertFalse(
            value[
                "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash"
            ]
        )

    def test_redirect_and_http_failure_are_terminal_zero_without_retry(self) -> None:
        for status, stage in ((302, "redirect"), (503, "http_status")):
            response = Response(body=b"", status=status)
            with mock.patch.object(runner.requests, "get", return_value=response) as get:
                value = runner._fetch_one(0)
            self.assertEqual(get.call_count, 1)
            self.assertTrue(value["failure_as_zero"])
            self.assertEqual(value["failure_stage"], stage)
            self.assertTrue(all(count == 0 for count in value["structure_counts"].values()))

    def test_projection_exception_is_explicit_failure_as_zero(self) -> None:
        response = Response(body=html().encode())
        with mock.patch.object(runner.requests, "get", return_value=response), mock.patch.object(
            runner.projection, "build_projection", side_effect=ValueError("synthetic")
        ):
            value = runner._fetch_one(0)
        self.assertEqual(value["failure_stage"], "projection_or_observer")
        self.assertTrue(value["failure_as_zero"])

    def test_fixed_denominator_aggregate_and_structure_gate(self) -> None:
        rows = [success_row(index) for index in range(20)]
        aggregate = runner.aggregate(rows)
        self.assertEqual(aggregate["task_count"], 20)
        self.assertEqual(aggregate["fetch_attempts"], 20)
        self.assertTrue(
            runner.mechanism_decision(aggregate)[
                "structure_localization_gate_passed"
            ]
        )
        for index in range(3):
            rows[index] = runner._failure_row(
                index, status=503, stage="http_status"
            )
        decision = runner.mechanism_decision(runner.aggregate(rows))
        self.assertFalse(decision["structure_localization_gate_passed"])
        self.assertIn("minimum_fetch_successes", decision["failed_checks"])

    def test_task_receipt_tamper_and_sensitive_fields_fail_closed(self) -> None:
        value = success_row(0)
        for mutation in ("extra", "sensitive", "credit", "count"):
            changed = copy.deepcopy(value)
            if mutation == "extra":
                changed["package"] = "must-not-persist"
            elif mutation == "sensitive":
                changed[
                    "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash"
                ] = True
            elif mutation == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["structure_counts"]["observed_page_count"] = 2
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                runner.validate_task_row(changed)

    def test_local_forward_freezes_twenty_content_free_rows(self) -> None:
        rows = [success_row(index) for index in range(20)]
        protocol = {"protected_watchers": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(runner, "ROOT", root))
                stack.enter_context(mock.patch.object(runner, "_clean_pushed"))
                stack.enter_context(mock.patch.object(runner, "_read", return_value={}))
                stack.enter_context(
                    mock.patch.object(contract, "validate_protocol", return_value=protocol)
                )
                stack.enter_context(mock.patch.object(runner, "_validate_start", return_value={}))
                stack.enter_context(mock.patch.object(runner, "_fetch_one", side_effect=rows))
                value = runner.run_forward()
            self.assertEqual(value["aggregate"]["task_count"], 20)
            persisted = (root / contract.TASK_ROWS).read_text(encoding="utf-8")
            for forbidden in (
                contract.PACKAGES[0],
                "https://cran.r-project.org",
                "Public package page",
                "MIT",
            ):
                self.assertNotIn(forbidden, persisted)

    def test_forward_closure_has_no_privileged_evaluator_secret_or_model(self) -> None:
        closure = contract.forward_dependency_closure(ROOT)
        evaluator = []
        secrets = []
        privileged = []
        for relative in closure:
            path = ROOT / relative
            source = path.read_text(encoding="utf-8")
            evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
            privileged.extend(semantic_audit._accesses(path, ROOT))
            if contract.SECRET.search(source):
                secrets.append(str(relative))
        unexpected = [
            value
            for value in privileged
            if not value.endswith("clients.py:565:score")
        ]
        self.assertEqual(evaluator, [])
        self.assertEqual(secrets, [])
        self.assertEqual(unexpected, [])
        runner_tree = ast.parse((ROOT / contract.RUNNER).read_text(encoding="utf-8"))
        runner_calls = {
            node.func.attr
            for node in ast.walk(runner_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(
            runner_calls.isdisjoint({"complete", "search_many", "run_official_eval"})
        )

    def test_control_expected_suite_total_and_dry_build_audit(self) -> None:
        self.assertEqual(control.EXPECTED_TESTS, 50)
        fake_tests = {
            "expected": 50,
            "observed": 50,
            "suites": [],
            "passed": True,
        }
        fake_semantic = {
            "dependency_closure": [],
            "dependency_closure_sha256": "0" * 64,
            "privileged_field_accesses": [],
            "permitted_provider_relevance_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "direct_forward_source_model_or_hosted_search_calls": [],
            "module_level_model_or_hosted_search_calls": [],
            "dormant_dependency_model_or_hosted_search_call_definitions": [],
        }
        with mock.patch.object(control, "_tests", return_value=fake_tests), mock.patch.object(
            control, "_semantic_audit", return_value=fake_semantic
        ), mock.patch.object(
            control.contract, "dependency_manifest", return_value={
                str(control.contract.CONTROL): "0",
                str(control.contract.TEST): "0",
                str(control.contract.POPULATION_SOURCE): "0",
                str(control.contract.POPULATION_TEST): "0",
                str(control.contract.POPULATION_AUDIT): "0",
                str(control.contract.PARENT_BUILD_AUDIT): "0",
            }
        ), mock.patch.object(
            control.contract, "forward_dependency_closure", return_value=()
        ), mock.patch.object(
            control.contract, "watcher_snapshot", return_value=[
                {"pid": pid, "start_ticks": ticks, "marker": marker}
                for pid, ticks, marker in contract.EXPECTED_WATCHERS
            ]
        ), mock.patch.object(
            control.contract, "validate_population_selection", return_value={
                "identity_history_zero_hit_count": 20
            }
        ), mock.patch.object(
            control.contract, "sha256", side_effect=lambda path: (
                contract.PARENT_BUILD_AUDIT_SHA256
                if Path(path).name == contract.PARENT_BUILD_AUDIT.name
                else "0" * 64
            )
        ), mock.patch.object(
            control.contract, "build_protocol", return_value={
                "execution": {"model_calls": 0}
            }
        ), mock.patch.object(
            control, "_future_pristine", return_value=True
        ):
            value = control.build_audit(now=1, require_clean=False)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["authorization"]["external_forward"])


if __name__ == "__main__":
    unittest.main()
