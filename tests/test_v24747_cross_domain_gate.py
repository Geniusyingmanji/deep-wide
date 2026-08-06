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

from scripts import v24747_cross_domain_gate as target  # noqa: E402


def fake_protocol() -> dict:
    with (
        patch.object(target, "_population", return_value={}),
        patch.object(target, "_manifest", return_value={"x": "a" * 64}),
        patch.object(target, "_watchers", return_value=[]),
        patch.object(target, "sha256", return_value="b" * 64),
        patch.object(
            target, "validate_protocol", side_effect=lambda root, value: value
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


def request_receipts() -> list[dict]:
    return [
        {
            "request_index": index,
            "source_host": target.urlsplit(url).hostname,
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


def task_receipts(*, ordinary_full_rows: int = 1) -> list[dict]:
    modes = [
        "ror_official_exact",
        "ror_official_exact",
        "crossref_official_exact",
        "crossref_official_exact",
        "crossref_openalex_ordinary",
        "crossref_openalex_ordinary",
    ]
    rows = []
    for position, mode in enumerate(modes, 1):
        trigger = position in {1, 3, 5}
        full_rows = ordinary_full_rows if position == 5 else int(trigger)
        admitted = full_rows * 2
        ordinary = mode == "crossref_openalex_ordinary"
        expected = 8 if ordinary else 4
        rows.append(
            {
                "position": position,
                "mode": mode,
                "runtime_valid": True,
                "prediction_changed": admitted > 0,
                "changed_cell_count": admitted,
                "fully_admitted_row_count": full_rows,
                "official_admitted_cell_count": 0 if ordinary else admitted,
                "corroborated_admitted_cell_count": admitted if ordinary else 0,
                "conflicting_cell_count": 0,
                "validated_record_count": expected,
                "adapter_failure_count": 0,
                "response_or_prediction_content_persisted_in_public_aggregate": False,
            }
        )
    return rows


class V24747CrossDomainGateTests(unittest.TestCase):
    def test_protocol_binds_6_tasks_32_requests_and_no_launch(self) -> None:
        value = fake_protocol()
        self.assertEqual(value["task_contract"]["task_count"], 6)
        self.assertEqual(value["execution"]["unique_request_count"], 32)
        self.assertEqual(value["execution"]["workers"], 32)
        self.assertFalse(value["authorization"]["external_launch"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertNotIn(
            "evaluation/v24744_cross_domain_population_private_v1_20260806.json",
            value["dependency_manifest"],
        )

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

    def test_hard_timeout_is_content_free(self) -> None:
        process = TimeoutProcess()
        with patch.object(target, "_terminate", side_effect=lambda item: item.wait()):
            result = target.hard_get(
                target._request_vector()[0],
                timeout_seconds=0.1,
                popen=lambda *_args, **_kwargs: process,
            )
        self.assertEqual(result["kind"], "hard_total_wall_timeout")
        self.assertEqual(result["body"], b"")
        self.assertNotIn("url", result)

    def test_aggregate_requires_all_three_paths_and_ordinary_full_row(self) -> None:
        with patch.object(target, "sha256", return_value="d" * 64):
            result, decision = target.aggregate(
                task_receipts(),
                request_receipts(),
                experiment_wall_seconds=1.0,
                predictions_sha256="d" * 64,
                freeze_sha256="d" * 64,
                now=0,
            )
            target.validate_result(result)
            target.validate_decision(decision, result=result)
        self.assertTrue(result["passed"])
        self.assertEqual(decision["status"], "cross_domain_mechanism_go")
        with patch.object(target, "sha256", return_value="d" * 64):
            no_go, decision = target.aggregate(
                task_receipts(ordinary_full_rows=0),
                request_receipts(),
                experiment_wall_seconds=1.0,
                predictions_sha256="d" * 64,
                freeze_sha256="d" * 64,
                now=0,
            )
        self.assertFalse(no_go["passed"])
        self.assertEqual(decision["status"], "cross_domain_mechanism_no_go")

    def test_resealed_result_count_tamper_fails_closed(self) -> None:
        with patch.object(target, "sha256", return_value="d" * 64):
            result, _decision = target.aggregate(
                task_receipts(),
                request_receipts(),
                experiment_wall_seconds=1.0,
                predictions_sha256="d" * 64,
                freeze_sha256="d" * 64,
                now=0,
            )
            altered = copy.deepcopy(result)
            altered["task_receipts"][0]["validated_record_count"] = 3
            altered.pop("result_payload_sha256")
            altered["result_payload_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                target.validate_result(altered)

    def test_ast_label_blind_and_request_vector_are_exact(self) -> None:
        self.assertEqual(target.ast_findings(ROOT), ([], []))
        self.assertEqual(len(target._request_vector()), 32)
        self.assertEqual(len(set(target._request_vector())), 32)
        self.assertEqual(set(target._request_vector()), target.helper.ALLOWED_URLS)

    def test_resealed_preaudit_tamper_fails_closed(self) -> None:
        value = {
            "role": "v24747_cross_domain_preactivation_audit",
            "protocol_id": target.PROTOCOL_ID,
            "protocol_sha256": "b" * 64,
            "tests": {"passed": True, "observed": 32, "expected": 32},
            "label_blind_audit": {
                "accesses": [],
                "evaluator_or_private_imports": [],
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
                "external_launch": False,
                "evaluator": False,
                "paired_dev64": False,
                "exact220": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with (
            patch.object(target, "sha256", return_value="b" * 64),
            patch.object(target, "_watchers", return_value=[]),
        ):
            target.validate_preaudit(value)
            altered = copy.deepcopy(value)
            altered["tests"]["observed"] = 31
            altered.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                target.validate_preaudit(altered)


if __name__ == "__main__":
    unittest.main()
