from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24726_fresh_bulk_transport_gate as target  # noqa: E402


def fake_protocol() -> dict:
    with (
        patch.object(target, "_parents", return_value=({}, {})),
        patch.object(target, "_manifest", return_value={"x": "a" * 64}),
        patch.object(target, "_watchers", return_value=[]),
        patch.object(target, "sha256", return_value="b" * 64),
        patch.object(
            target,
            "validate_protocol",
            side_effect=lambda root, value: value,
        ),
    ):
        return target.build_protocol(ROOT, now=0)


class TimeoutProcess:
    pid = 99_999_999
    returncode = None
    stdin = stdout = stderr = None

    def communicate(self, _request: str, timeout: float | None = None):
        raise subprocess.TimeoutExpired("helper", timeout)

    def wait(self, timeout: float | None = None):
        del timeout
        self.returncode = -15
        return self.returncode


def code(index: int) -> str:
    return "".join(
        chr(ord("A") + value)
        for value in (index // 676, (index // 26) % 26, index % 26)
    )


def synthetic_request(
    wave: int,
    spec: target.runtime.FreshTarget,
    representation: str,
    *,
    fail_primary: bool = False,
    fail_comparator: bool = False,
):
    is_primary = representation == target.runtime.PRIMARY_REPRESENTATION
    failed = (is_primary and fail_primary) or (
        not is_primary and fail_comparator
    )
    count = 265 if is_primary else 260
    url = target.runtime.endpoint_url(spec, representation)
    records = {code(index): Decimal(index) for index in range(count)}
    receipt = {
        "wave": wave,
        "target_key": target.runtime.target_key(spec),
        "indicator": spec.indicator,
        "year": spec.year,
        "representation": representation,
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "attempts": 1,
        "success": not failed,
        "failure_type": "transport_error" if failed else None,
        "http_status": None if failed else 200,
        "elapsed_seconds": 0.01,
        "response_bytes": 0 if failed else 100,
        "raw_sha256": None if failed else "b" * 64,
        "semantic_sha256": None if failed else "c" * 64,
        "record_count": 0 if failed else count,
        "non_null_count": 0 if failed else count,
        "response_country_value_or_content_persisted": False,
    }
    return receipt, None if failed else records


class V24726FreshBulkTransportGateTests(unittest.TestCase):
    def test_protocol_defaults_to_no_launch_and_binds_fresh_targets(self) -> None:
        value = fake_protocol()
        self.assertEqual(
            [item["target_key"] for item in value["target_selection"]["target_vector"]],
            ["IT.NET.USER.ZS@2022", "SP.DYN.LE00.IN@2022"],
        )
        self.assertTrue(
            value["target_selection"]["selected_before_any_v24726_transport_outcome"]
        )
        self.assertEqual(value["execution"]["primary_representation"], "bulk_zip")
        self.assertEqual(value["execution"]["total_requests"], 8)
        self.assertEqual(value["execution"]["workers"], 4)
        self.assertFalse(value["authorization"]["transport_launch"])
        self.assertFalse(value["authorization"]["benchmark_dev64_or_exact220"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = fake_protocol()
        value["execution"]["attempts_per_endpoint_per_wave"] = 2
        value.pop("protocol_payload_sha256")
        value["protocol_payload_sha256"] = target.payload_sha256(value)
        with (
            patch.object(target, "_manifest", return_value={"x": "a" * 64}),
            patch.object(target, "_watchers", return_value=[]),
            patch.object(target, "sha256", return_value="b" * 64),
        ):
            with self.assertRaises(RuntimeError):
                target.validate_protocol(ROOT, value=value)

    def test_resealed_preaudit_tamper_fails_closed(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24726_fresh_bulk_transport_preactivation_audit",
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
            patch.object(target, "_watchers", return_value=[]),
        ):
            target.validate_preaudit(value)
            tampered = copy.deepcopy(value)
            tampered["tests"]["observed"] -= 1
            tampered.pop("audit_payload_sha256")
            tampered["audit_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_preaudit(tampered)

    def test_hard_timeout_is_content_free(self) -> None:
        process = TimeoutProcess()
        with patch.object(target, "_terminate", side_effect=lambda item: item.wait()):
            result = target.hard_get(
                target.runtime.endpoint_url(
                    target.runtime.TARGETS[0],
                    target.runtime.PRIMARY_REPRESENTATION,
                ),
                timeout_seconds=0.1,
                popen=lambda *_args, **_kwargs: process,
            )
        self.assertEqual(result["kind"], "hard_total_wall_timeout")
        self.assertEqual(result["body"], b"")
        self.assertNotIn("url", result)

    def test_primary_gate_go_no_go_and_comparator_independence(self) -> None:
        with (
            patch.object(target, "_request_one", side_effect=synthetic_request),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            result, decision = target.run_experiment()
            target.validate_result(result)
            target.validate_decision(decision, result=result)
        self.assertTrue(result["passed"])
        self.assertEqual(result["primary_successes"], 4)
        self.assertEqual(result["comparator_successes"], 4)
        self.assertEqual(decision["status"], "transport_go")

        def comparator_failure(*args):
            return synthetic_request(*args, fail_comparator=True)

        with (
            patch.object(target, "_request_one", side_effect=comparator_failure),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            result, decision = target.run_experiment()
            target.validate_result(result)
            target.validate_decision(decision, result=result)
        self.assertTrue(result["passed"])
        self.assertFalse(
            result["checks"]["comparator_all_requests_http_200_and_schema_valid"]
        )
        self.assertEqual(decision["status"], "transport_go")

        def primary_failure(*args):
            return synthetic_request(*args, fail_primary=True)

        with (
            patch.object(target, "_request_one", side_effect=primary_failure),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            result, decision = target.run_experiment()
            target.validate_result(result)
            target.validate_decision(decision, result=result)
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
