from __future__ import annotations

import copy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24721_worldbank_transport_gate as target  # noqa: E402


def fake_protocol() -> dict:
    with (
        patch.object(target, "_parents_valid", return_value=True),
        patch.object(target, "_manifest", return_value={"x": "a" * 64}),
        patch.object(target, "_watcher_snapshot", return_value=[]),
        patch.object(target, "sha256", return_value="b" * 64),
        patch.object(target, "validate_protocol", side_effect=lambda root, value: value),
    ):
        return target.build_protocol(ROOT, now=0)


class Process:
    pid = 99_999_999
    returncode = None
    stdin = stdout = stderr = None

    def communicate(self, _request: str, timeout: float | None = None):
        raise __import__("subprocess").TimeoutExpired("helper", timeout)

    def wait(self, timeout: float | None = None):
        del timeout
        self.returncode = -15
        return self.returncode


class V24721WorldBankTransportGateTests(unittest.TestCase):
    def test_protocol_freezes_preexisting_target_union_and_no_launch(self) -> None:
        value = fake_protocol()
        self.assertEqual(value["target_selection"]["target_count"], 6)
        self.assertFalse(value["target_selection"]["selected_after_transport_outcome"])
        self.assertEqual(value["execution"]["total_requests"], 24)
        self.assertEqual(value["execution"]["primary_representation"], "aggregate_json")
        self.assertTrue(value["execution"]["representation_selected_before_transport_outcome"])
        self.assertFalse(value["authorization"]["transport_launch"])
        self.assertFalse(value["authorization"]["benchmark_dev64_or_exact220"])

    def test_protocol_tamper_fails_closed(self) -> None:
        value = fake_protocol()
        value["execution"]["attempts_per_endpoint_per_wave"] = 2
        value.pop("protocol_payload_sha256")
        value["protocol_payload_sha256"] = target.payload_sha256(value)
        with (
            patch.object(target, "_manifest", return_value={"x": "a" * 64}),
            patch.object(target, "_watcher_snapshot", return_value=[]),
            patch.object(target, "sha256", return_value="b" * 64),
        ):
            with self.assertRaises(RuntimeError):
                target.validate_protocol(ROOT, value=value)

    def test_preaudit_resealed_protocol_or_test_tamper_fails_closed(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24721_worldbank_transport_preactivation_audit",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 0,
            "protocol_sha256": "b" * 64,
            "tests": {
                "passed": True,
                "observed": target.EXPECTED_TESTS,
                "expected": target.EXPECTED_TESTS,
                "output_sha256": "c" * 64,
            },
            "label_blind_audit": {
                "accesses": [],
                "evaluator_imports": [],
                "passed": True,
            },
            "runtime_state": {
                "protected_watchers": [],
                "shared_api_lease_inactive": True,
                "runner_active": False,
            },
            "findings": [],
            "audit_valid": True,
            "authorization": {
                "activation_publication": True,
                "transport_launch": False,
                "benchmark_dev64_or_exact220": False,
                "evaluator": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with (
            patch.object(target, "sha256", return_value="b" * 64),
            patch.object(target, "_watcher_snapshot", return_value=[]),
        ):
            target.validate_preaudit(value)
            tampered = copy.deepcopy(value)
            tampered["tests"]["observed"] -= 1
            tampered.pop("audit_payload_sha256")
            tampered["audit_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_preaudit(tampered)

    def test_hard_get_timeout_is_content_free(self) -> None:
        process = Process()
        with patch.object(target, "_terminate_group", side_effect=lambda item: item.wait()):
            result = target.hard_get(
                target.runtime.endpoint_url(target.runtime.TARGETS[0], "bulk_zip"),
                timeout_seconds=0.1,
                popen=lambda *_args, **_kwargs: process,
            )
        self.assertEqual(result["kind"], "hard_total_wall_timeout")
        self.assertEqual(result["body"], b"")
        self.assertNotIn("url", result)

    def test_run_experiment_gate_requires_full_transport(self) -> None:
        def success(wave, spec, representation):
            record_vector = {
                f"{chr(65 + (index // 676))}{chr(65 + ((index // 26) % 26))}{chr(65 + (index % 26))}": Decimal(index)
                for index in range(205)
            }
            receipt = {
                "wave": wave,
                "target_key": target.runtime.target_key(spec),
                "indicator": spec.indicator,
                "year": spec.year,
                "representation": representation,
                "url_sha256": "a" * 64,
                "attempts": 1,
                "success": True,
                "failure_type": None,
                "http_status": 200,
                "elapsed_seconds": 0.01,
                "response_bytes": 100,
                "raw_sha256": "b" * 64,
                "semantic_sha256": "c" * 64,
                "record_count": 205,
                "non_null_count": 205,
                "response_country_value_or_content_persisted": False,
            }
            return receipt, {}, record_vector

        with (
            patch.object(target, "_request_one", side_effect=success),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            result, decision = target.run_experiment()
        self.assertTrue(result["passed"])
        self.assertEqual(result["successes"], 24)
        self.assertTrue(
            result["checks"]["bulk_comparator_all_requests_http_200_and_schema_valid"]
        )
        self.assertEqual(decision["status"], "transport_go")

        calls = 0

        def one_failure(*args):
            nonlocal calls
            calls += 1
            receipt, parsed, records = success(*args)
            if calls == 1:
                receipt = copy.deepcopy(receipt)
                receipt.update({"success": False, "failure_type": "transport_error", "http_status": None, "record_count": 0, "non_null_count": 0})
                return receipt, None, None
            return receipt, parsed, records

        with (
            patch.object(target, "_request_one", side_effect=one_failure),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            result, decision = target.run_experiment()
        self.assertTrue(result["passed"])
        self.assertFalse(
            result["checks"]["bulk_comparator_all_requests_http_200_and_schema_valid"]
        )
        self.assertEqual(decision["status"], "transport_go")

        def primary_failure(*args):
            receipt, parsed, records = success(*args)
            if args[2] == "aggregate_json":
                receipt = copy.deepcopy(receipt)
                receipt.update({"success": False, "failure_type": "transport_error", "http_status": None, "record_count": 0, "non_null_count": 0})
                return receipt, None, None
            return receipt, parsed, records

        with (
            patch.object(target, "_request_one", side_effect=primary_failure),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            result, decision = target.run_experiment()
        self.assertFalse(result["passed"])
        self.assertEqual(decision["status"], "transport_no_go")

    def test_ast_label_blind_scan_and_source_policy(self) -> None:
        accesses, imports = target.ast_findings(ROOT)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        protocol = fake_protocol()
        self.assertTrue(protocol["source_policy"])
        self.assertFalse(any(protocol["source_policy"].values()))


if __name__ == "__main__":
    unittest.main()
