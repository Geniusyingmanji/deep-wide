from __future__ import annotations

import ast
import copy
import json
import pickle
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24970_same_process_search_readiness import (  # noqa: E402
    EXPECTED_KEY_COUNT,
    NEUTRAL_QUERY,
    POLICY_ID,
    run_readiness,
    validate_receipt,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


def response(status: int, payload: dict | None = None) -> Mock:
    value = Mock()
    value.status_code = status
    value.json.return_value = payload or {}
    value.headers = {}
    return value


def success(ordinal: int) -> Mock:
    return response(
        200,
        {
            "results": [
                {
                    "title": f"neutral-{ordinal}",
                    "url": f"https://docs{ordinal}.example/page",
                    "content": "discarded",
                    "score": 1.0,
                }
            ]
        },
    )


def credentials() -> tuple[str, ...]:
    return tuple(f"synthetic-ephemeral-{index:02d}" for index in range(12))


class V24970SameProcessSearchReadinessTests(unittest.TestCase):
    def run_gate(self, factory):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw) / "probe"
            root.mkdir()
            return run_readiness(
                credentials(),
                root,
                session_nonce="0123456789abcdef",
                post_factory=factory,
            )

    def test_all_twelve_healthy_returns_one_shot_capability(self) -> None:
        receipt, capability = self.run_gate(
            lambda ordinal: Mock(return_value=success(ordinal))
        )
        aggregate = receipt["aggregate"]
        self.assertTrue(receipt["passed"])
        self.assertEqual(aggregate["tested_key_count"], EXPECTED_KEY_COUNT)
        self.assertEqual(aggregate["healthy_key_count"], EXPECTED_KEY_COUNT)
        self.assertEqual(aggregate["status_2xx"], EXPECTED_KEY_COUNT)
        self.assertEqual(aggregate["successful_queries"], EXPECTED_KEY_COUNT)
        self.assertGreaterEqual(aggregate["projected_url_leads"], EXPECTED_KEY_COUNT)
        self.assertIsNotNone(capability)
        assert capability is not None
        self.assertNotIn("synthetic-ephemeral", repr(capability))
        self.assertEqual(capability.consume(receipt), credentials())
        self.assertTrue(capability.consumed)
        with self.assertRaises(RuntimeError):
            capability.consume(receipt)

    def test_one_432_fails_closed_without_capability(self) -> None:
        receipt, capability = self.run_gate(
            lambda ordinal: Mock(
                return_value=response(432) if ordinal == 7 else success(ordinal)
            )
        )
        self.assertFalse(receipt["passed"])
        self.assertEqual(receipt["aggregate"]["healthy_key_count"], 11)
        self.assertEqual(receipt["aggregate"]["status_432"], 1)
        self.assertEqual(receipt["aggregate"]["key_local_disables"], 1)
        self.assertIsNone(capability)

    def test_2xx_without_url_lead_fails_closed(self) -> None:
        receipt, capability = self.run_gate(
            lambda ordinal: Mock(
                return_value=response(200, {"results": []})
                if ordinal == 3
                else success(ordinal)
            )
        )
        self.assertFalse(receipt["passed"])
        self.assertEqual(receipt["aggregate"]["status_2xx"], 12)
        self.assertEqual(receipt["aggregate"]["successful_queries"], 11)
        self.assertIsNone(capability)

    def test_credential_echo_fails_closed_and_receipt_has_no_secret(self) -> None:
        keys = credentials()

        def factory(ordinal: int) -> Mock:
            if ordinal == 2:
                return Mock(
                    return_value=response(
                        200,
                        {
                            "results": [
                                {
                                    "title": keys[1],
                                    "url": "https://echo.example/page",
                                }
                            ]
                        },
                    )
                )
            return Mock(return_value=success(ordinal))

        receipt, capability = self.run_gate(factory)
        encoded = json.dumps(receipt, sort_keys=True)
        self.assertFalse(receipt["passed"])
        self.assertEqual(receipt["aggregate"]["credential_echo_rejections"], 1)
        self.assertIsNone(capability)
        self.assertTrue(all(key not in encoded for key in keys))

    def test_exact_credential_shape_and_nonce_are_required(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw) / "probe"
            root.mkdir()
            with self.assertRaises(ValueError):
                run_readiness(credentials()[:11], root)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw) / "probe"
            root.mkdir()
            with self.assertRaises(ValueError):
                run_readiness(credentials(), root, session_nonce="bad nonce")

    def test_root_must_be_empty_ordinary_directory(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            base = Path(raw)
            real = base / "real"
            real.mkdir()
            link = base / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(ValueError):
                run_readiness(credentials(), link)
            (real / "occupied").write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                run_readiness(credentials(), real)

    def test_receipt_tamper_and_capability_receipt_mismatch_fail(self) -> None:
        receipt, capability = self.run_gate(
            lambda ordinal: Mock(return_value=success(ordinal))
        )
        assert capability is not None
        changed = copy.deepcopy(receipt)
        changed["aggregate"]["healthy_key_count"] = 11
        changed["aggregate"]["unhealthy_key_count"] = 1
        with self.assertRaises(ValueError):
            validate_receipt(changed)
        resealed = copy.deepcopy(changed)
        resealed["passed"] = False
        resealed.pop("receipt_payload_sha256")
        resealed["receipt_payload_sha256"] = payload_sha256(resealed)
        validate_receipt(resealed)
        with self.assertRaises(RuntimeError):
            capability.consume(resealed)

    def test_capability_cannot_be_copied_or_serialized(self) -> None:
        receipt, capability = self.run_gate(
            lambda ordinal: Mock(return_value=success(ordinal))
        )
        self.assertTrue(receipt["passed"])
        assert capability is not None
        with self.assertRaises(TypeError):
            copy.copy(capability)
        with self.assertRaises(TypeError):
            copy.deepcopy(capability)
        with self.assertRaises(TypeError):
            pickle.dumps(capability)

    def test_receipt_is_aggregate_only_and_non_authorizing(self) -> None:
        receipt, _capability = self.run_gate(
            lambda ordinal: Mock(return_value=success(ordinal))
        )
        self.assertEqual(receipt["policy_id"], POLICY_ID)
        self.assertNotIn("rows", receipt)
        self.assertNotIn("credentials", receipt)
        self.assertFalse(receipt["per_key_rows_persisted"])
        self.assertFalse(receipt["benchmark_forward_authorized_by_receipt_alone"])
        self.assertFalse(
            receipt[
                "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read"
            ]
        )

    def test_neutral_query_and_runtime_source_are_label_blind(self) -> None:
        self.assertIn("official documentation", NEUTRAL_QUERY)
        path = ROOT / "src/deepwide_agent/v24970_same_process_search_readiness.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertEqual(semantic_audit._accesses(path, ROOT), [])
        self.assertNotRegex(
            source,
            r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}",
        )


if __name__ == "__main__":
    unittest.main()
