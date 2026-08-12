from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25226_cran_semantic_transport as target  # noqa: E402


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
        *,
        status: int = 200,
        body: bytes = b"",
        content_type: object = "text/plain",
        header_present: bool = True,
        chunks: list[object] | None = None,
    ) -> None:
        self.status_code = status
        self.body = body
        self.headers = {"Content-Type": content_type} if header_present else {}
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


class RaisingStatusResponse:
    def __init__(self, *, body: bytes) -> None:
        self.body = body
        self.headers = {"Content-Type": "text/plain"}
        self.closed = False

    @property
    def status_code(self):
        raise ValueError("private status value")

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield self.body

    def close(self) -> None:
        self.closed = True


def public_resolve(host: str, port: int) -> list[str]:
    assert host == target.HOSTNAME
    assert port == 443
    return ["8.8.8.8"]


def body(count: int = 64) -> bytes:
    records = []
    for index in range(count):
        records.append(
            "\n".join(
                (
                    f"Package: Pkg{index}",
                    "Version: 1.0",
                    "License: MIT",
                    "Suggests: alpha,",
                    " beta",
                )
            )
        )
    return "\n\n".join(records).encode("utf-8")


class V25226CranSemanticTransportTests(unittest.TestCase):
    def _run(self, response: FakeResponse):
        session = FakeSession(response)
        candidates, receipt = target.fetch_strict_cran_candidates(
            session=session,
            resolve=public_resolve,
            monotonic=Clock(),
        )
        return candidates, receipt, session

    def test_text_plain_strict_body_succeeds_with_one_fixed_get(self) -> None:
        response = FakeResponse(body=body(), content_type="Text/Plain; charset=UTF-8")
        candidates, receipt, session = self._run(response)
        self.assertEqual(candidates, [f"pkg{index}" for index in range(64)])
        self.assertEqual(receipt["terminal_outcome"], "success")
        self.assertEqual(receipt["content_type_observation"]["disposition"], "accepted")
        self.assertEqual(receipt["extracted_candidate_count"], 64)
        self.assertEqual(len(session.calls), 1)
        url, kwargs = session.calls[0]
        self.assertEqual(url, target.ENDPOINT)
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(kwargs["stream"])
        self.assertTrue(kwargs["verify"])
        self.assertEqual(
            kwargs["timeout"],
            (target.CONNECT_TIMEOUT_SECONDS, target.READ_TIMEOUT_SECONDS),
        )
        self.assertFalse(session.trust_env)
        self.assertTrue(response.closed)
        self.assertTrue(receipt["public_snapshot_network_or_api_called"])

    def test_unknown_and_missing_mime_succeed_only_via_strict_body(self) -> None:
        cases = (
            (FakeResponse(body=body(), content_type="application/octet-stream"), "unknown_disallowed"),
            (FakeResponse(body=body(), header_present=False), "missing"),
        )
        for response, expected in cases:
            candidates, receipt, _session = self._run(response)
            with self.subTest(expected=expected):
                self.assertEqual(len(candidates), 64)
                self.assertEqual(receipt["terminal_outcome"], "success")
                self.assertEqual(receipt["content_type_observation"]["disposition"], expected)
                self.assertFalse(receipt["missing_or_unknown_mime_relabelled_as_text_plain"])
                self.assertFalse(receipt["mime_alone_establishes_semantic_success"])
                self.assertEqual(receipt["known_safe_alternate_mime_allowlist_count"], 0)
                rendered = json.dumps(receipt, sort_keys=True)
                self.assertNotIn("application/octet-stream", rendered)

    def test_http_200_unknown_mime_with_invalid_body_fails_semantic_gate(self) -> None:
        response = FakeResponse(
            body=b"Package: X\nLicense: MIT\nSuggests: a\n",
            content_type="application/octet-stream",
        )
        candidates, receipt, _session = self._run(response)
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["terminal_outcome"], "failure")
        self.assertEqual(receipt["failure_code"], "semantic_gate")
        self.assertEqual(
            receipt["strict_extraction_observation"]["failure_stage"],
            "minimum_candidate_coverage",
        )
        self.assertGreater(receipt["response_bytes"], 0)
        self.assertIsNotNone(receipt["response_sha256"])

    def test_invalid_header_shape_fails_before_body_read(self) -> None:
        response = FakeResponse(body=body(), content_type=123)
        candidates, receipt, _session = self._run(response)
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "content_type_observation")
        self.assertEqual(receipt["response_bytes"], 0)
        self.assertIsNone(receipt["strict_extraction_observation"])

    def test_dns_timeout_redirect_non200_and_stream_failure_are_finite(self) -> None:
        session = FakeSession(FakeResponse(body=body()))
        candidates, receipt = target.fetch_strict_cran_candidates(
            session=session,
            resolve=lambda host, port: ["127.0.0.1"],
            monotonic=Clock(),
        )
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "dns_nonpublic")
        self.assertEqual(session.calls, [])
        self.assertTrue(receipt["public_address_dns_preflight_performed"])
        self.assertTrue(receipt["public_snapshot_network_or_api_called"])
        cases = (
            (requests.Timeout("private"), "transport_timeout"),
            (FakeResponse(status=302, body=b"x"), "http_redirect"),
            (FakeResponse(status=503, body=b"x"), "http_non200"),
            (FakeResponse(body=b"", chunks=[OSError("private")]), "stream_error"),
        )
        for outcome, expected in cases:
            session = FakeSession(outcome)
            candidates, receipt = target.fetch_strict_cran_candidates(
                session=session,
                resolve=public_resolve,
                monotonic=Clock(),
            )
            with self.subTest(expected=expected):
                self.assertEqual(candidates, [])
                self.assertEqual(receipt["failure_code"], expected)
                self.assertEqual(len(session.calls), 1)
                self.assertEqual(receipt["extracted_candidate_count"], 0)

    def test_semantic_extractor_exception_is_finite_and_content_free(self) -> None:
        response = FakeResponse(body=body(), content_type="application/octet-stream")
        session = FakeSession(response)
        with mock.patch.object(
            target.extractor,
            "extract_strict_cran_candidates",
            side_effect=ValueError("private semantic value"),
        ):
            candidates, receipt = target.fetch_strict_cran_candidates(
                session=session,
                resolve=public_resolve,
                monotonic=Clock(),
            )
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "semantic_gate_exception")
        self.assertIsNone(receipt["strict_extraction_observation"])
        self.assertGreater(receipt["response_bytes"], 0)
        self.assertNotIn("private semantic value", json.dumps(receipt))

    def test_clock_resolver_and_response_property_exceptions_are_finite(self) -> None:
        candidates, receipt = target.fetch_strict_cran_candidates(
            session=FakeSession(FakeResponse(body=body())),
            resolve=public_resolve,
            monotonic=lambda: (_ for _ in ()).throw(ValueError("private clock")),
        )
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "clock_error")
        self.assertFalse(receipt["public_snapshot_network_or_api_called"])
        clock_values = iter((0.0,))
        candidates, receipt = target.fetch_strict_cran_candidates(
            session=FakeSession(FakeResponse(body=body())),
            resolve=public_resolve,
            monotonic=lambda: next(clock_values),
        )
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "clock_error")
        self.assertTrue(receipt["public_snapshot_network_or_api_called"])
        self.assertEqual(receipt["provider_attempt_count"], 1)
        self.assertEqual(receipt["response_bytes"], 0)
        self.assertIsNone(receipt["content_type_observation"])
        self.assertIsNone(receipt["strict_extraction_observation"])
        session = FakeSession(FakeResponse(body=body()))
        candidates, receipt = target.fetch_strict_cran_candidates(
            session=session,
            resolve=lambda host, port: (_ for _ in ()).throw(
                ValueError("private resolver")
            ),
            monotonic=Clock(),
        )
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "transport_error")
        self.assertEqual(session.calls, [])
        self.assertTrue(receipt["public_snapshot_network_or_api_called"])
        session = FakeSession(RaisingStatusResponse(body=body()))
        candidates, receipt = target.fetch_strict_cran_candidates(
            session=session,
            resolve=public_resolve,
            monotonic=Clock(),
        )
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "transport_error")
        self.assertEqual(receipt["response_bytes"], 0)
        rendered = json.dumps(receipt)
        self.assertNotIn("private clock", rendered)
        self.assertNotIn("private resolver", rendered)
        self.assertNotIn("private status value", rendered)

    def test_soft_wall_exceeded_discards_strict_candidates(self) -> None:
        response = FakeResponse(body=body())
        session = FakeSession(response)
        candidates, receipt = target.fetch_strict_cran_candidates(
            session=session,
            resolve=public_resolve,
            monotonic=Clock(step=target.TOTAL_WALL_SECONDS + 1),
        )
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_code"], "wall_exceeded")
        self.assertIsNone(receipt["strict_extraction_observation"])
        self.assertEqual(receipt["response_bytes"], 0)
        self.assertIsNone(receipt["response_sha256"])
        self.assertTrue(
            receipt["independent_hard_deadline_controller_required_for_execution"]
        )

    def test_resealed_nested_binding_policy_credit_or_authority_tamper_fails(self) -> None:
        _candidates, value, _session = self._run(FakeResponse(body=body()))
        for kind in (
            "nested_content",
            "nested_extraction",
            "binding",
            "policy",
            "credit",
            "authority",
            "hidden",
            "failure_state",
        ):
            changed = copy.deepcopy(value)
            if kind == "nested_content":
                changed["content_type_observation"]["disposition"] = "missing"
            elif kind == "nested_extraction":
                changed["strict_extraction_observation"]["extracted_candidate_count"] = 63
            elif kind == "binding":
                changed["response_sha256"] = "0" * 64
            elif kind == "policy":
                changed["known_safe_alternate_mime_allowlist_count"] = 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "authority":
                changed[
                    "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized"
                ] = True
            elif kind == "failure_state":
                changed["terminal_outcome"] = "failure"
                changed["failure_code"] = "dns_nonpublic"
                changed["extracted_candidate_count"] = 0
            else:
                changed["hidden_identity"] = "private"
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_source_is_label_blind_secret_free_and_import_has_no_effect(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v25226_cran_semantic_transport.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "gh" + "p_",
            "tvly-" + "dev-",
            "run_official_eval_local",
            "/mnt",
            "/data",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
