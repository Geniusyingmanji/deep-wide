from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25217_single_snapshot_transport as target  # noqa: E402


class Clock:
    def __init__(self, step: float = 0.01) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        self.value += self.step
        return self.value


class FakeResponse:
    def __init__(
        self,
        status: int = 200,
        body: bytes = b"{}",
        content_type: str = "application/json",
        chunks: list[object] | None = None,
    ) -> None:
        self.status_code = status
        self.body = body
        self.headers = {"Content-Type": content_type}
        self.chunks = chunks
        self.closed = False

    def iter_content(self, chunk_size: int):
        del chunk_size
        for value in self.chunks if self.chunks is not None else [self.body]:
            if isinstance(value, BaseException):
                raise value
            yield value

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, dict]] = []
        self.trust_env = True

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def public_resolve(host: str, port: int) -> list[str]:
    del host, port
    return ["8.8.8.8"]


class V25217SingleSnapshotTransportTests(unittest.TestCase):
    def test_each_frozen_endpoint_maps_to_one_bounded_get(self) -> None:
        for stratum, spec in target.ENDPOINTS.items():
            content_type = spec["accepted_content_types"][0]
            response = FakeResponse(content_type=content_type)
            session = FakeSession(response)
            body, receipt = target.fetch_snapshot(
                stratum,
                session=session,
                resolve=public_resolve,
                monotonic=Clock(),
            )
            with self.subTest(stratum=stratum):
                self.assertEqual(body, b"{}")
                self.assertEqual(len(session.calls), 1)
                url, kwargs = session.calls[0]
                self.assertEqual(url, spec["url"])
                self.assertFalse(kwargs["allow_redirects"])
                self.assertTrue(kwargs["stream"])
                self.assertTrue(kwargs["verify"])
                self.assertEqual(
                    kwargs["timeout"],
                    (target.CONNECT_TIMEOUT_SECONDS, target.READ_TIMEOUT_SECONDS),
                )
                self.assertFalse(session.trust_env)
                self.assertEqual(receipt["provider_attempt_count"], 1)
                self.assertEqual(receipt["retry_count"], 0)
                self.assertEqual(receipt["redirect_count"], 0)
                self.assertEqual(receipt["terminal_outcome"], "success")
                self.assertFalse(
                    receipt["dns_preflight_result_pinned_to_transport"]
                )
                self.assertFalse(
                    receipt["requests_timeout_is_hard_total_wall_deadline"]
                )
                self.assertTrue(
                    receipt[
                        "independent_hard_deadline_controller_required_for_execution"
                    ]
                )
                self.assertTrue(response.closed)

    def test_dns_failure_and_nonpublic_address_make_zero_http_attempts(self) -> None:
        for resolver, code in (
            (lambda host, port: (_ for _ in ()).throw(OSError("dns secret")), "dns_failure"),
            (lambda host, port: ["127.0.0.1"], "dns_nonpublic"),
        ):
            session = FakeSession(FakeResponse())
            body, receipt = target.fetch_snapshot(
                next(iter(target.ENDPOINTS)),
                session=session,
                resolve=resolver,
                monotonic=Clock(),
            )
            with self.subTest(code=code):
                self.assertEqual(body, b"")
                self.assertEqual(session.calls, [])
                self.assertEqual(receipt["provider_attempt_count"], 0)
                self.assertEqual(receipt["failure_code"], code)

    def test_timeout_transport_redirect_and_non200_fail_once_without_body(self) -> None:
        cases = (
            (requests.Timeout("secret"), "transport_timeout"),
            (requests.ConnectionError("secret"), "transport_error"),
            (FakeResponse(status=302), "http_redirect"),
            (FakeResponse(status=503), "http_non200"),
        )
        stratum = next(iter(target.ENDPOINTS))
        for outcome, code in cases:
            session = FakeSession(outcome)
            body, receipt = target.fetch_snapshot(
                stratum,
                session=session,
                resolve=public_resolve,
                monotonic=Clock(),
            )
            with self.subTest(code=code):
                self.assertEqual(body, b"")
                self.assertEqual(len(session.calls), 1)
                self.assertEqual(receipt["failure_code"], code)
                self.assertEqual(receipt["response_bytes"], 0)
                self.assertIsNone(receipt["response_sha256"])

    def test_content_type_empty_stream_invalid_chunk_and_oversize_fail_closed(self) -> None:
        stratum = "single_authority_exact_record"
        cap = target.ENDPOINTS[stratum]["maximum_response_bytes"]
        cases = (
            (FakeResponse(content_type="text/html"), "content_type"),
            (FakeResponse(body=b""), "empty_response"),
            (FakeResponse(chunks=["not-bytes"]), "stream_error"),
            (FakeResponse(chunks=[b"x" * cap, b"x"]), "response_oversize"),
            (FakeResponse(chunks=[RuntimeError("secret")]), "stream_error"),
        )
        for response, code in cases:
            body, receipt = target.fetch_snapshot(
                stratum,
                session=FakeSession(response),
                resolve=public_resolve,
                monotonic=Clock(),
            )
            with self.subTest(code=code):
                self.assertEqual(body, b"")
                self.assertEqual(receipt["failure_code"], code)
                self.assertEqual(receipt["response_bytes"], 0)

    def test_wall_exceeded_discards_successful_body(self) -> None:
        body, receipt = target.fetch_snapshot(
            "single_authority_exact_record",
            session=FakeSession(FakeResponse()),
            resolve=public_resolve,
            monotonic=Clock(step=181.0),
        )
        self.assertEqual(body, b"")
        self.assertEqual(receipt["failure_code"], "wall_exceeded")

    def test_success_receipt_is_content_free_and_body_hash_bound(self) -> None:
        secret = b'{"private-identity":"private-value"}'
        body, receipt = target.fetch_snapshot(
            "single_authority_exact_record",
            session=FakeSession(FakeResponse(body=secret)),
            resolve=public_resolve,
            monotonic=Clock(),
        )
        self.assertEqual(body, secret)
        self.assertEqual(receipt["response_bytes"], len(secret))
        self.assertEqual(receipt["response_sha256"], hashlib.sha256(secret).hexdigest())
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("private-identity", rendered)
        self.assertNotIn(target.ENDPOINTS["single_authority_exact_record"]["url"], rendered)

    def test_unknown_stratum_and_resealed_receipt_tamper_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            target.fetch_snapshot("unknown", session=FakeSession(FakeResponse()))
        _body, receipt = target.fetch_snapshot(
            "single_authority_exact_record",
            session=FakeSession(FakeResponse()),
            resolve=public_resolve,
            monotonic=Clock(),
        )
        for kind in ("attempts", "retry", "authority", "content"):
            changed = copy.deepcopy(receipt)
            if kind == "attempts":
                changed["provider_attempt_count"] = 0
            elif kind == "retry":
                changed["retry_count"] = 1
            elif kind == "authority":
                changed[
                    "population_freeze_external_forward_or_runtime_compatibility_authorized"
                ] = True
            else:
                changed[
                    "contains_url_body_header_identity_record_value_question_prediction_evidence_or_credential"
                ] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_import_has_no_effect_and_source_has_no_secret_or_evaluator_capability(self) -> None:
        source = (ROOT / "src/deepwide_agent/v25217_single_snapshot_transport.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("ghp_", "tvly-dev-", "run_official_eval_local", "/mnt", "/data"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
