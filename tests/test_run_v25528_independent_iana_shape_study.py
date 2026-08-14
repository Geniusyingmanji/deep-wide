from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v25528_independent_iana_shape_study as target  # noqa: E402


class Response:
    def __init__(self, url: str, identity: str, *, status: int = 200) -> None:
        self.url = url
        self.status_code = status
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"
        self.content = (
            "<html><head><title>"
            + identity
            + " Domain Delegation Data</title></head><body>"
            + "<h1>Delegation Record for "
            + identity
            + "</h1><dl><dt>TLD Type</dt><dd>generic</dd>"
            + "<dt>TLD Manager</dt><dd>Example Registry</dd></dl>"
            + "</body></html>"
        ).encode()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class V25528IndependentIanaShapeStudyRunnerTests(unittest.TestCase):
    def test_fetch_vector_attempts_each_exact_url_once_without_redirect(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        def get(url: str, **kwargs):
            calls.append((url, kwargs))
            identity = "." + url.rsplit("/", 1)[-1].removesuffix(".html")
            return Response(url, identity)

        rows = target.fetch_vector(get=get, workers=4)
        self.assertEqual(len(calls), len(target.contract.STUDY_IDENTITIES))
        self.assertEqual([url for url, _kwargs in calls], target.contract.url_vector())
        self.assertTrue(all(kwargs["allow_redirects"] is False for _url, kwargs in calls))
        self.assertTrue(all(row["http_attempt_count"] == 1 for row in rows))
        self.assertTrue(all(row["production_extraction_valid"] for row in rows))
        self.assertTrue(all(row["identity_surface_bound"] for row in rows))

    def test_http_failure_is_fixed_denominator_not_retried(self) -> None:
        attempts = 0

        def get(url: str, **_kwargs):
            nonlocal attempts
            attempts += 1
            identity = "." + url.rsplit("/", 1)[-1].removesuffix(".html")
            return Response(url, identity, status=503 if attempts == 1 else 200)

        rows = target.fetch_vector(get=get, workers=1)
        self.assertEqual(attempts, len(target.contract.STUDY_IDENTITIES))
        self.assertFalse(rows[0]["production_extraction_valid"])
        self.assertEqual(rows[0]["error"], "http_503")
        self.assertTrue(all(row["http_attempt_count"] == 1 for row in rows))

    def test_snapshot_seals_fixed_pages_and_zero_privileged_effect(self) -> None:
        def get(url: str, **_kwargs):
            identity = "." + url.rsplit("/", 1)[-1].removesuffix(".html")
            return Response(url, identity)

        value = target.build_snapshot(
            target.fetch_vector(get=get), now=1, head="a" * 40
        )
        self.assertEqual(target.validate_snapshot(value), value)
        self.assertEqual(value["aggregate"]["http_attempt_count"], 8)
        self.assertEqual(value["aggregate"]["production_extraction_valid_count"], 8)
        self.assertEqual(
            value["effect_receipt"][
                "search_model_fetch_provider_evaluator_benchmark_or_api_call_count"
            ],
            0,
        )
        self.assertEqual(value["effect_receipt"]["positive_signed_credit_count"], 0)

    def test_snapshot_tamper_fails(self) -> None:
        def get(url: str, **_kwargs):
            identity = "." + url.rsplit("/", 1)[-1].removesuffix(".html")
            return Response(url, identity)

        value = target.build_snapshot(target.fetch_vector(get=get), now=1)
        for kind in ("content", "attempt", "launch"):
            changed = copy.deepcopy(value)
            if kind == "content":
                changed["pages"][0]["content"] += "x"
            elif kind == "attempt":
                changed["pages"][0]["http_attempt_count"] = 2
            else:
                changed["authorization"]["deepwidebench_forward_or_evaluator"] = True
            changed.pop("snapshot_payload_sha256")
            changed["snapshot_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_snapshot(changed)


if __name__ == "__main__":
    unittest.main()
