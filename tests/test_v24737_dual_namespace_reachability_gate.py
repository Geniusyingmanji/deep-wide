from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24737_dual_namespace_reachability_gate as target  # noqa: E402


def fake_protocol() -> dict:
    with (
        patch.object(target, "_parents", return_value=None),
        patch.object(target, "_manifest", return_value={"x": "a" * 64}),
        patch.object(target, "_watchers", return_value=[]),
        patch.object(target, "sha256", return_value="b" * 64),
        patch.object(target, "validate_protocol", side_effect=lambda root, value: value),
    ):
        return target.build_protocol(ROOT, now=0)


class TimeoutProcess:
    pid = 99_999_999
    returncode = None
    stdin = stdout = stderr = None

    def communicate(self, _request: str, timeout: float | None = None):
        raise subprocess.TimeoutExpired("helper", timeout)

    def wait(self, timeout: float | None = None):
        del timeout; self.returncode = -15; return self.returncode


def request_receipts() -> list[dict]:
    return [
        {
            "request_index": index,
            "namespace": "ror" if url in target.helper.ROR_URLS else "worldbank",
            "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
            "attempts": 1,
            "transport_success": True,
            "failure_type": None,
            "http_status": 200,
            "elapsed_seconds": 0.01,
            "response_bytes": 100,
            "raw_sha256": "a" * 64,
            "response_content_persisted": False,
        }
        for index, url in enumerate(target._request_vector(), 1)
    ]


def task_receipts(*, ror_change: bool = True, wb_change: bool = True) -> list[dict]:
    rows = []
    for position in range(1, target.TASK_COUNT + 1):
        namespace = "ror" if position <= target.TASKS_PER_CLUSTER else "worldbank"
        changed = (namespace == "ror" and ror_change and position == 1) or (namespace == "worldbank" and wb_change and position == 13)
        rows.append(
            {
                "position": position,
                "namespace": namespace,
                "runtime_valid": True,
                "prediction_changed": changed,
                "changed_cell_count": 2 if changed else 0,
                "primary_identity_bound_target_count": 1 if changed else 0,
                "target_value_bound_cell_count": 2 if changed else 0,
                "response_or_prediction_content_persisted_in_public_aggregate": False,
            }
        )
    return rows


class V24737DualNamespaceReachabilityGateTests(unittest.TestCase):
    def test_protocol_binds_24_tasks_50_requests_and_no_launch(self) -> None:
        value = fake_protocol()
        self.assertEqual(value["task_contract"]["task_count"], 24)
        self.assertEqual(value["execution"]["unique_request_count"], 50)
        self.assertEqual(value["execution"]["workers"], 25)
        self.assertLessEqual(
            ((value["execution"]["unique_request_count"] + value["execution"]["workers"] - 1)
             // value["execution"]["workers"])
            * value["execution"]["hard_total_wall_seconds"],
            value["execution"]["experiment_wall_ceiling_seconds"],
        )
        self.assertFalse(value["authorization"]["forward_launch"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertNotIn("v24733_dual_namespace_evaluator", value["dependency_manifest"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = fake_protocol(); value["execution"]["attempts_per_url"] = 2
        value.pop("protocol_payload_sha256"); value["protocol_payload_sha256"] = target.payload_sha256(value)
        with patch.object(target, "_manifest", return_value={"x": "a" * 64}), patch.object(target, "_watchers", return_value=[]), patch.object(target, "sha256", return_value="b" * 64):
            with self.assertRaises(RuntimeError): target.validate_protocol(ROOT, value=value)

    def test_resealed_preaudit_tamper_fails_closed(self) -> None:
        value = {
            "role": "v24737_dual_namespace_reachability_preactivation_audit", "protocol_id": target.PROTOCOL_ID,
            "protocol_sha256": "b" * 64, "tests": {"passed": True, "observed": 16, "expected": 16},
            "label_blind_audit": {"accesses": [], "evaluator_imports": [], "passed": True},
            "runtime_state": {"protected_watchers": [], "shared_api_lease_inactive": True, "runner_active": False},
            "findings": [], "audit_valid": True,
            "authorization": {"activation_publication": True, "forward_launch": False, "evaluator": False, "benchmark_dev64_or_exact220": False, "leaderboard_or_sota": False},
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with patch.object(target, "sha256", return_value="b" * 64), patch.object(target, "_watchers", return_value=[]):
            target.validate_preaudit(value); tampered = copy.deepcopy(value); tampered["tests"]["observed"] = 15; tampered.pop("audit_payload_sha256"); tampered["audit_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError): target.validate_preaudit(tampered)

    def test_hard_timeout_is_content_free(self) -> None:
        process = TimeoutProcess()
        with patch.object(target, "_terminate", side_effect=lambda item: item.wait()):
            result = target.hard_get(target._request_vector()[0], timeout_seconds=0.1, popen=lambda *_args, **_kwargs: process)
        self.assertEqual(result["kind"], "hard_total_wall_timeout")
        self.assertEqual(result["body"], b"")
        self.assertNotIn("url", result)
        launch_error = target.hard_get(
            target._request_vector()[0],
            timeout_seconds=0.1,
            popen=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
        )
        self.assertEqual(launch_error["kind"], "helper_launch_error")
        self.assertEqual(launch_error["body"], b"")

    def test_aggregate_requires_reachability_in_both_clusters(self) -> None:
        with patch.object(target, "sha256", return_value="d" * 64):
            result, decision = target.aggregate(task_receipts(), request_receipts(), experiment_wall_seconds=1.0, prediction_sha256="d" * 64, freeze_sha256="d" * 64, now=0)
            target.validate_result(result)
        self.assertTrue(result["passed"])
        self.assertEqual(decision["status"], "dual_namespace_reachability_go")
        tampered = copy.deepcopy(result)
        tampered["request_successes"] -= 1
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = target.payload_sha256(tampered)
        with patch.object(target, "sha256", return_value="d" * 64):
            with self.assertRaises(RuntimeError):
                target.validate_result(tampered)
        with patch.object(target, "sha256", return_value="d" * 64):
            result, decision = target.aggregate(task_receipts(wb_change=False), request_receipts(), experiment_wall_seconds=1.0, prediction_sha256="a" * 64, freeze_sha256="b" * 64, now=0)
        self.assertFalse(result["passed"])
        self.assertEqual(decision["status"], "dual_namespace_reachability_no_go")

    def test_ast_label_blind_and_request_vector_are_exact(self) -> None:
        self.assertEqual(target.ast_findings(ROOT), ([], []))
        self.assertEqual(set(target._request_vector()), set(target.helper.ALLOWED_URLS))
        protocol = fake_protocol()
        self.assertFalse(any(protocol["source_policy"].values()))


if __name__ == "__main__":
    unittest.main()
