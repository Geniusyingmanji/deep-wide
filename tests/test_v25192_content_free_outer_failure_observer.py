from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import (  # noqa: E402
    v25192_content_free_outer_failure_observer as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


class V25192ContentFreeOuterFailureObserverTests(unittest.TestCase):
    def test_all_runtime_layers_have_static_failure_code_coverage(self) -> None:
        modules = (
            "v25135_sparse_production_runtime.py",
            "v25139_targeted_revision_runtime.py",
            "v25143_quote_attested_cell_edit_runtime.py",
            "v25147_deterministic_quote_candidate_runtime.py",
            "v25151_generic_record_quote_candidate_runtime.py",
            "v25158_vertical_key_value_candidate_runtime.py",
            "v25165_observed_vertical_key_value_runtime.py",
            "v25180_quote_aware_production_runtime.py",
            "v25188_export_failure_tolerant_same_response_runtime.py",
        )
        expected_messages: set[str] = set()
        for name in modules:
            path = ROOT / "src/deepwide_agent" / name
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Raise)
                    and isinstance(node.exc, ast.Call)
                    and isinstance(node.exc.func, ast.Name)
                    and node.exc.func.id in {"RuntimeError", "ValueError"}
                    and len(node.exc.args) == 1
                    and isinstance(node.exc.args[0], ast.Constant)
                    and isinstance(node.exc.args[0].value, str)
                ):
                    expected_messages.add(node.exc.args[0].value)
        runner_messages = {
            "V2.51.95 accounting search configuration drifted",
            "V2.51.95 task identity drifted",
            "V2.51.95 task row drifted",
            "V2.51.95 bound runtime row drifted",
            "V2.51.95 outer failure row drifted",
        }
        self.assertEqual(
            set(target.STATIC_MESSAGE_TO_CODE), expected_messages | runner_messages
        )
        expected_versions = {
            message.split(" ", 1)[0]
            for message in expected_messages | runner_messages
        }
        observed_versions = {
            message.split(" ", 1)[0]
            for message in target.STATIC_MESSAGE_TO_CODE
        }
        self.assertEqual(observed_versions, expected_versions)
        self.assertEqual(
            len(target.STATIC_MESSAGE_TO_CODE),
            len(set(target.STATIC_MESSAGE_TO_CODE.values())),
        )
        for message, code in target.STATIC_MESSAGE_TO_CODE.items():
            with self.subTest(message=message):
                value = target.observe_outer_failure(
                    ValueError(message), outer_failure_stage="runtime"
                )
                self.assertEqual(value["failure_code"], code)
                self.assertTrue(value["static_exception_message_mapped"])
                self.assertNotIn(message, json.dumps(value))

    def test_three_outer_stages_are_exact_and_content_free(self) -> None:
        message = "V2.51.88 same-response result drifted"
        for stage in target.OUTER_FAILURE_STAGES:
            with self.subTest(stage=stage):
                value = target.observe_outer_failure(
                    ValueError(message), outer_failure_stage=stage
                )
                self.assertEqual(value["outer_failure_stage"], stage)
                self.assertEqual(
                    value["failure_code"], "v25188_result_envelope_validation"
                )
                self.assertFalse(
                    value[
                        "raw_exception_message_repr_traceback_or_frame_persisted_or_hashed"
                    ]
                )
        with self.assertRaises(ValueError):
            target.observe_outer_failure(
                ValueError(message), outer_failure_stage="unknown"
            )

    def test_dynamic_messages_collapse_by_safe_exception_type(self) -> None:
        first = target.observe_outer_failure(
            ValueError("secret task alpha https://example.invalid/value"),
            outer_failure_stage="runtime",
        )
        second = target.observe_outer_failure(
            ValueError("different secret task beta"),
            outer_failure_stage="runtime",
        )
        self.assertEqual(first, second)
        self.assertEqual(first["failure_code"], "unclassified_value_error")
        self.assertFalse(first["static_exception_message_mapped"])
        encoded = json.dumps(first)
        for forbidden in ("alpha", "beta", "example.invalid", "secret task"):
            self.assertNotIn(forbidden, encoded)

    def test_unknown_exception_class_is_coarsened(self) -> None:
        class ContentBearingException(Exception):
            pass

        value = target.observe_outer_failure(
            ContentBearingException("private value"),
            outer_failure_stage="conversion",
        )
        self.assertEqual(value["outer_failure_type"], "Exception")
        self.assertEqual(value["failure_code"], "unclassified_exception")
        self.assertNotIn("ContentBearingException", json.dumps(value))

    def test_tamper_stage_code_credit_or_content_fails_closed(self) -> None:
        base = target.observe_outer_failure(
            RuntimeError("V2.51.80 repair lost safe public production"),
            outer_failure_stage="runtime",
        )
        changes = {
            "stage": ("outer_failure_stage", "other"),
            "code": ("failure_code", "raw_message_here"),
            "credit": ("entropy_or_information_gain_assigns_signed_credit", True),
            "content": (
                "contains_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_or_credential",
                True,
            ),
        }
        for kind, (field, replacement) in changes.items():
            changed = copy.deepcopy(base)
            changed[field] = replacement
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_observation(changed)

    def test_module_is_label_blind_effect_free_and_has_no_dynamic_hash(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25192_content_free_outer_failure_observer.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
        hits = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in privileged
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertEqual(hits, set())
        self.assertTrue(
            calls.isdisjoint(
                {
                    "complete",
                    "search_many",
                    "fetch_urls",
                    "create_connection",
                    "read_text",
                    "write_text",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
