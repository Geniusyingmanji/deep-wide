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

from deepwide_agent import v25061_docsrs_late_record_gate_contract as contract  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v25060_version_qualified_late_record as parent_representation,
)
from deepwide_agent import (  # noqa: E402
    v25061_pure_version_qualified_late_record as pure_representation,
)
from deepwide_agent.native_search import (  # noqa: E402
    decode_web_text as production_decode,
    html_to_document,
)
from deepwide_agent.v25061_html_surface import (  # noqa: E402
    decode_web_text,
    html_to_title_text,
)
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25061_docsrs_late_record_gate as runner  # noqa: E402


def html(crate: str = "anyhow", version: str = "1.0.100") -> str:
    return (
        "<html><head><title>"
        + crate
        + " "
        + version
        + " - Docs.rs</title></head><body>"
        + "<h1>"
        + crate
        + "-"
        + version
        + "</h1>"
        + "<p>"
        + ("Long public documentation line. " * 220)
        + "</p><h2>License</h2><p>MIT</p>"
        + "<table><tr><th>Key</th><th>Value</th></tr>"
        + "<tr><td>Example</td><td>Visible</td></tr></table>"
        + "<script>License: forbidden</script></body></html>"
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


def success_row(position: int, *, engaged: bool = True) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v25061_docsrs_late_record_task_receipt",
        "protocol_id": contract.PROTOCOL_ID,
        "task_position": position,
        "terminal": True,
        "fetch_attempts": 1,
        "fetch_success": True,
        "http_status": 200,
        "decoded_page_characters": 7000,
        "input_characters_beyond_parent_prefix": 2000,
        "qualified_identity_binding_count": 1,
        "complete_record_count": 1,
        "late_target_field_count": 1 if engaged else 0,
        "admissible_record_count": 1 if engaged else 0,
        "mechanism_engaged": engaged,
        "candidate_evidence_changed": engaged,
        "projection_failure_count": 0,
        "positive_signed_credit_count": 0,
        "failure_as_zero": False,
        "failure_stage": "none",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_search_or_evaluator_called": False,
        "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash": False,
    }
    return runner.validate_task_row(contract.seal(value, "result_payload_sha256"))


class V25061DocsRsLateRecordGateTests(unittest.TestCase):
    def test_pure_representation_matches_parent_fieldwise_on_synthetic_cases(self) -> None:
        question = contract.task_vector()[0]["question"]
        title = "async-kit 1.53.1 - Documentation"
        base = "\n".join(
            (
                title,
                "Documentation portal",
                "async-kit-1.53.1",
                "Platform",
                "x86_64-unknown-linux-gnu",
                *("Long public documentation line." for _ in range(180)),
                "License",
                "MIT",
            )
        )
        cases = (
            {
                "url": "https://docs.example.org/crate/async-kit/latest",
                "title": title,
                "text": base,
            },
            {
                "url": "https://docs.example.org/crate/async-kit/latest",
                "title": title,
                "text": base.replace("async-kit-1.53.1", "async-kit-1.53.0"),
            },
            {
                "url": "https://docs.example.org/crate/async-kit/latest",
                "title": title,
                "text": base + "\nLicense: Apache-2.0",
            },
            {
                "url": "https://docs.example.org/crate/async-kit/latest",
                "title": "async-kit — Official Documentation",
                "text": "\n".join(
                    (
                        "async-kit — Official Documentation",
                        "async-kit — Official Documentation",
                        *("Long public documentation line." for _ in range(180)),
                        "License: MIT",
                    )
                ),
            },
        )
        for page in cases:
            with self.subTest(title=page["title"], tail=page["text"][-40:]):
                parent = parent_representation.build_representation(question, page)
                pure = pure_representation.build_representation(question, page)
                self.assertEqual(set(pure), set(parent))
                for field in parent:
                    self.assertEqual(pure[field], parent[field], field)

    def test_pure_representation_matches_parent_fieldwise_on_docsrs_shape(self) -> None:
        question = contract.task_vector()[0]["question"]
        decoded = decode_web_text(html().encode("utf-8"), "utf-8")
        title, text = html_to_title_text(decoded)
        page = {
            "url": "https://docs.rs/crate/anyhow/latest",
            "title": title,
            "text": text,
        }
        parent = parent_representation.build_representation(question, page)
        pure = pure_representation.build_representation(question, page)
        self.assertEqual(set(pure), set(parent))
        for field in parent:
            self.assertEqual(pure[field], parent[field], field)

    def test_pure_html_surface_matches_production_title_text_and_decode(self) -> None:
        raw = html().encode("utf-8")
        decoded = decode_web_text(raw, "iso-8859-1")
        self.assertEqual(decoded, production_decode(raw, "iso-8859-1"))
        title, text = html_to_title_text(decoded)
        expected_title, expected_text, _links = html_to_document(
            decoded, "https://docs.example.org/crate/anyhow/latest"
        )
        self.assertEqual((title, text), (expected_title, expected_text))
        self.assertNotIn("forbidden", text)
        self.assertIn("Key | Value", text)

    def test_population_is_fixed_fresh_disjoint_and_question_hides_identity(self) -> None:
        self.assertEqual(len(contract.CRATES), 20)
        self.assertEqual(len(set(contract.CRATES)), 20)
        self.assertFalse(
            set(contract.CRATES) & set(contract.CONSUMED_DEVELOPMENT_CRATES)
        )
        for crate, task in zip(contract.CRATES, contract.task_vector(), strict=True):
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(crate.casefold(), task["question"].casefold())
            self.assertEqual(
                tuple(extract_robust_visible_columns(task["question"])),
                contract.COLUMNS,
            )
        self.assertEqual(len(contract.endpoint_vector()), 20)

    def test_protocol_exact_schema_zero_model_and_resealed_tamper_fails(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(value["execution"]["model_calls"], 0)
        self.assertEqual(value["execution"]["search_calls"], 0)
        self.assertEqual(value["execution"]["evaluator_calls"], 0)
        self.assertFalse(value["authorization"]["model_or_evaluator_on_this_population"])
        with (
            mock.patch.object(
                contract, "dependency_manifest", return_value=value["source_manifest"]
            ),
            mock.patch.object(
                contract, "watcher_snapshot", return_value=value["protected_watchers"]
            ),
            mock.patch.object(contract, "sha256", return_value="0" * 64),
        ):
            self.assertEqual(contract.validate_protocol(ROOT, value), value)
            changed = copy.deepcopy(value)
            changed["unexpected_metadata"] = True
            changed = contract.seal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                contract.validate_protocol(ROOT, changed)

    def test_single_fetch_produces_content_free_natural_exposure_receipt(self) -> None:
        endpoint = contract.endpoint_vector()[0]
        response = Response(body=html(contract.CRATES[0]).encode(), url=endpoint)
        with mock.patch.object(runner.requests, "get", return_value=response) as get:
            value = runner._fetch_one(0)
        get.assert_called_once()
        self.assertTrue(value["fetch_success"])
        self.assertEqual(value["fetch_attempts"], 1)
        self.assertEqual(value["qualified_identity_binding_count"], 1)
        self.assertEqual(value["late_target_field_count"], 1)
        self.assertTrue(value["mechanism_engaged"])
        self.assertFalse(
            value[
                "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash"
            ]
        )

    def test_http_failure_is_terminal_zero_and_never_retried(self) -> None:
        response = Response(body=b"", status=503)
        with mock.patch.object(runner.requests, "get", return_value=response) as get:
            value = runner._fetch_one(0)
        get.assert_called_once()
        self.assertTrue(value["terminal"])
        self.assertTrue(value["failure_as_zero"])
        self.assertEqual(value["failure_stage"], "http_status")
        self.assertFalse(value["mechanism_engaged"])

    def test_representation_exception_is_explicit_projection_failure(self) -> None:
        response = Response(body=html(contract.CRATES[0]).encode())
        with (
            mock.patch.object(runner.requests, "get", return_value=response),
            mock.patch.object(
                runner.representation,
                "build_representation",
                side_effect=ValueError("synthetic failure"),
            ),
        ):
            value = runner._fetch_one(0)
        self.assertEqual(value["failure_stage"], "representation")
        self.assertEqual(value["projection_failure_count"], 1)
        self.assertTrue(value["failure_as_zero"])

    def test_fixed_denominator_aggregate_and_mechanism_threshold(self) -> None:
        rows = [success_row(index, engaged=index < 8) for index in range(20)]
        aggregate = runner.aggregate(rows)
        self.assertEqual(aggregate["task_count"], 20)
        self.assertEqual(aggregate["fetch_attempts"], 20)
        self.assertEqual(aggregate["mechanism_exposed_pages"], 8)
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        rows[-1] = runner._failure_row(19, status=503, stage="http_status")
        rows[-2] = runner._failure_row(18, status=503, stage="http_status")
        rows[-3] = runner._failure_row(17, status=503, stage="http_status")
        decision = runner.mechanism_decision(runner.aggregate(rows))
        self.assertFalse(decision["mechanism_gate_passed"])
        self.assertIn("minimum_fetch_successes", decision["failed_checks"])

    def test_task_receipt_exact_schema_and_resealed_sensitive_tamper_fail(self) -> None:
        value = success_row(0)
        for mutation in ("extra", "sensitive", "credit"):
            changed = copy.deepcopy(value)
            if mutation == "extra":
                changed["crate"] = "must-not-persist"
            elif mutation == "sensitive":
                changed[
                    "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash"
                ] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                runner.validate_task_row(changed)

    def test_local_forward_freezes_twenty_content_free_rows_without_model(self) -> None:
        rows = [success_row(index, engaged=index < 8) for index in range(20)]
        protocol = {"protected_watchers": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(runner, "_clean_pushed"),
                mock.patch.object(runner, "_read", return_value={}),
                mock.patch.object(contract, "validate_protocol", return_value=protocol),
                mock.patch.object(runner, "_validate_start", return_value={}),
                mock.patch.object(contract, "watcher_snapshot", return_value=[]),
                mock.patch.object(runner, "_fetch_one", side_effect=rows),
            ):
                value = runner.run_forward()
            self.assertEqual(value["aggregate"]["task_count"], 20)
            self.assertTrue(value["mechanism_decision"]["mechanism_gate_passed"])
            self.assertTrue((root / contract.TASK_ROWS).is_file())
            self.assertTrue((root / contract.FORWARD_RESULT).is_file())
            persisted = (root / contract.TASK_ROWS).read_text(encoding="utf-8")
            for forbidden in (
                contract.CRATES[0],
                "https://docs.rs",
                "Column names",
                "MIT",
            ):
                self.assertNotIn(forbidden, persisted)
            persisted_rows = [
                runner.validate_task_row(json.loads(line))
                for line in persisted.splitlines()
                if line.strip()
            ]
            self.assertEqual(len(persisted_rows), 20)
            self.assertTrue(
                all(
                    row[
                        "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash"
                    ]
                    is False
                    for row in persisted_rows
                )
            )

    def test_forward_closure_has_no_privileged_evaluator_secret_or_native_search(self) -> None:
        closure = contract.forward_dependency_closure(ROOT)
        self.assertNotIn(Path("src/deepwide_agent/native_search.py"), closure)
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
        runner_source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        tree = ast.parse(runner_source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertNotIn("deepwide_agent.native_search", imported)


if __name__ == "__main__":
    unittest.main()
