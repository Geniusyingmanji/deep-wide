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

from scripts import v24742_fresh_resilience_gate as target  # noqa: E402


def fake_protocol() -> dict:
    with (
        patch.object(target, "_parents", return_value=None),
        patch.object(target, "_manifest", return_value={"x": "a" * 64}),
        patch.object(target, "_watchers", return_value=[]),
        patch.object(target, "sha256", return_value="b" * 64),
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


def representation_row(representation: str, valid: bool) -> dict:
    count = 265 if representation == "bulk_zip" else 260
    return {
        "representation": representation,
        "schema_valid": valid,
        "record_count": count if valid else 0,
        "semantic_sha256": "a" * 64 if valid else None,
        "response_content_persisted": False,
    }


def target_receipt(index: int, valid: tuple[bool, bool]) -> dict:
    rows = [
        representation_row(representation, observed)
        for representation, observed in zip(target.runtime.REPRESENTATIONS, valid, strict=True)
    ]
    count = sum(valid)
    comparison = None
    agreement = False
    consistency_failed = False
    if count == 2:
        comparison = {
            "preferred_record_count": 265,
            "fallback_record_count": 260,
            "common_domain_count": 260,
            "preferred_only_domain_count": 5,
            "fallback_only_domain_count": 0,
            "common_value_mismatch_count": 0,
            "common_domain_sha256": "b" * 64,
            "preferred_only_domain_sha256": "c" * 64,
            "fallback_only_domain_sha256": "d" * 64,
            "content_persisted": False,
        }
        agreement = True
    selected = "bulk_zip" if valid[0] else "aggregate_json" if valid[1] else None
    admitted_count = 265 if selected == "bulk_zip" else 260 if selected else 0
    value = {
        "artifact_version": 1,
        "role": "v24740_target_resilience_content_free_receipt",
        "policy_id": target.runtime.POLICY_ID,
        "target_key": target.runtime.target_key(target.runtime.TARGETS[index]),
        "fixed_requested_representations": list(target.runtime.REPRESENTATIONS),
        "representation_receipts": rows,
        "schema_valid_representation_count": count,
        "selected_representation": selected,
        "target_admitted": count > 0 and not consistency_failed,
        "dual_valid_common_value_agreement": agreement,
        "dual_valid_consistency_failed": consistency_failed,
        "comparison": comparison,
        "admitted_record_count": admitted_count,
        "failure_type_counts": (
            {"schema_or_transport_invalid": 2 - count} if count < 2 else {}
        ),
        "target_failure_isolated": True,
        "response_country_value_or_content_persisted": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = target.runtime.payload_sha256(value)
    return target.runtime.validate_receipt(value)


def bundle_receipt(receipts: list[dict]) -> dict:
    admitted = sum(row["target_admitted"] for row in receipts)
    value = {
        "artifact_version": 1,
        "role": "v24740_bundle_resilience_content_free_receipt",
        "policy_id": target.runtime.POLICY_ID,
        "target_count": 2,
        "admitted_target_count": admitted,
        "abstained_target_count": 2 - admitted,
        "all_target_failures_isolated": True,
        "retry_resume_or_selective_rerun": False,
        "response_country_value_or_content_persisted": False,
    }
    value["receipt_payload_sha256"] = target.runtime.payload_sha256(value)
    return target.runtime.validate_bundle_receipt(value, target_receipts=receipts)


def request_receipts(successes: tuple[bool, bool, bool, bool]) -> list[dict]:
    rows = []
    for index, ((spec, representation, url), success) in enumerate(
        zip(target._request_vector(), successes, strict=True), 1
    ):
        rows.append(
            {
                "request_index": index,
                "target_key": target.runtime.target_key(spec),
                "representation": representation,
                "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                "attempts": 1,
                "transport_success": success,
                "failure_type": None if success else "transport_error",
                "http_status": 200 if success else None,
                "elapsed_seconds": 0.01,
                "response_bytes": 100 if success else 0,
                "raw_sha256": "a" * 64 if success else None,
                "response_content_persisted": False,
            }
        )
    return rows


def singleton_rows(receipts: list[dict]) -> list[dict]:
    output = []
    for receipt in receipts:
        for row in receipt["representation_receipts"]:
            if row["schema_valid"]:
                output.append(
                    {
                        "target_key": receipt["target_key"],
                        "available_representation": row["representation"],
                        "target_admitted": True,
                        "selected_representation": row["representation"],
                        "admitted_record_count": row["record_count"],
                        "response_country_value_or_content_persisted": False,
                    }
                )
    return output


class V24742FreshResilienceGateTests(unittest.TestCase):
    def test_protocol_binds_four_once_only_requests_and_no_launch(self) -> None:
        value = fake_protocol()
        self.assertEqual(value["target_contract"]["target_count"], 2)
        self.assertEqual(value["execution"]["unique_request_count"], 4)
        self.assertEqual(value["execution"]["workers"], 4)
        self.assertFalse(value["authorization"]["transport_launch"])
        self.assertFalse(value["authorization"]["evaluator_execution"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = fake_protocol()
        value["execution"]["attempts_per_url"] = 2
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
            "role": "v24742_fresh_resilience_preactivation_audit",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 0,
            "protocol_sha256": "b" * 64,
            "tests": {"passed": True, "observed": 21, "expected": 21},
            "label_blind_audit": {"accesses": [], "evaluator_imports": [], "passed": True},
            "runtime_state": {"protected_watchers": [], "shared_api_lease_inactive": True, "runner_active": False},
            "findings": [],
            "audit_valid": True,
            "authorization": {"activation_publication": True, "transport_launch": False, "benchmark_forward": False, "evaluator_execution": False, "benchmark_dev64_or_exact220": False, "leaderboard_or_sota": False},
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with patch.object(target, "sha256", return_value="b" * 64), patch.object(target, "_watchers", return_value=[]):
            target.validate_preaudit(value)
            tampered = copy.deepcopy(value)
            tampered["tests"]["observed"] = 20
            tampered.pop("audit_payload_sha256")
            tampered["audit_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_preaudit(tampered)

    def test_hard_timeout_is_content_free(self) -> None:
        process = TimeoutProcess()
        with patch.object(target, "_terminate", side_effect=lambda item: item.wait()):
            result = target.hard_get(
                target._request_vector()[0][2],
                timeout_seconds=0.1,
                popen=lambda *_args, **_kwargs: process,
            )
        self.assertEqual(result["kind"], "hard_total_wall_timeout")
        self.assertEqual(result["body"], b"")
        self.assertNotIn("url", result)

    def test_aggregate_allows_one_failed_representation_but_not_target_loss(self) -> None:
        receipts = [target_receipt(0, (True, True)), target_receipt(1, (False, True))]
        with patch.object(target, "sha256", return_value="d" * 64):
            result, decision = target.aggregate(
                request_receipts((True, True, False, True)),
                receipts,
                bundle_receipt(receipts),
                singleton_rows(receipts),
                experiment_wall_seconds=1.0,
                attempt_claim_sha256="d" * 64,
                run_summary_sha256="d" * 64,
                now=0,
            )
        self.assertTrue(result["passed"])
        self.assertEqual(decision["status"], "fresh_resilience_go")
        claim = {
            "artifact_version": 1,
            "role": "v24742_fresh_resilience_attempt_claim",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 0,
            "execution_start_sha256": "d" * 64,
            "unique_request_count": 4,
            "attempts_per_url": 1,
            "retry_resume_or_selective_rerun": False,
            "network_model_search_benchmark_forward_or_evaluator_called_before_claim": False,
        }
        claim["claim_payload_sha256"] = target.payload_sha256(claim)
        summary = {
            "artifact_version": 1,
            "role": "v24742_fresh_resilience_run_summary",
            "protocol_id": target.PROTOCOL_ID,
            "attempt_claim_sha256": "d" * 64,
            "requests": 4,
            "request_successes": 3,
            "targets": 2,
            "admitted_targets": 2,
            "schema_valid_representations": 3,
            "experiment_wall_seconds": 1.0,
            "retry_resume_or_selective_rerun": False,
            "response_country_value_or_content_persisted": False,
            "benchmark_forward_or_evaluator_called": False,
        }
        summary["summary_payload_sha256"] = target.payload_sha256(summary)
        tampered = copy.deepcopy(result)
        tampered["request_successes"] -= 1
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = target.payload_sha256(tampered)
        with (
            patch.object(target, "sha256", return_value="d" * 64),
            patch.object(
                target,
                "_read",
                side_effect=lambda _root, path: (
                    claim if path == target.ATTEMPT_CLAIM else summary
                ),
            ),
        ):
            with self.assertRaises(RuntimeError):
                target.validate_result(tampered)
        lost = [target_receipt(0, (True, True)), target_receipt(1, (False, False))]
        with patch.object(target, "sha256", return_value="d" * 64):
            result, decision = target.aggregate(
                request_receipts((True, True, False, False)),
                lost,
                bundle_receipt(lost),
                singleton_rows(lost),
                experiment_wall_seconds=1.0,
                attempt_claim_sha256="d" * 64,
                run_summary_sha256="d" * 64,
                now=0,
            )
        self.assertFalse(result["passed"])
        self.assertEqual(decision["status"], "fresh_resilience_no_go")

    def test_ast_label_blind_and_request_vector_are_exact(self) -> None:
        self.assertEqual(target.ast_findings(ROOT), ([], []))
        self.assertEqual({row[2] for row in target._request_vector()}, set(target.helper.ALLOWED_URLS))
        self.assertFalse(any(fake_protocol()["source_policy"].values()))


if __name__ == "__main__":
    unittest.main()
