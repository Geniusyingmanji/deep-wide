from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25004_identity_bound_detail_fields as projection  # noqa: E402
from deepwide_agent.v25005_detail_field_fetch import (  # noqa: E402
    HELPER as PARENT_HELPER,
    DetailFieldLatePageBoundSearchClient,
)
from deepwide_agent.v25009_detail_stage_observer_fetch import (  # noqa: E402
    HELPER,
    DetailStageObservedSearchClient,
    build_helper_envelope,
    validate_observer_receipt,
    validate_search_class,
)
from scripts.run_v25009_detail_stage_observer_fetch_helper import observed_output  # noqa: E402


QUESTION = (
    "Use the official Acme Package Index public page. Include one row for "
    "<PACKAGE>AlphaKit</PACKAGE>. Column names: Package, Version, Published, License."
)
URL = "https://packages.acme.example/web/packages/AlphaKit/index.html"


class Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class Process:
    def __init__(self, payload: dict, *, returncode: int = 0) -> None:
        self.pid = 123456789
        self.returncode = returncode
        self.payload = payload
        self.command = None
        self.stdin_value = None

    def communicate(self, value: str, timeout: float | None = None):
        del timeout
        self.stdin_value = json.loads(value)
        return json.dumps(self.payload), ""

    def wait(self, timeout: float | None = None):
        del timeout
        return self.returncode


def raw_text() -> str:
    return "\n".join(
        (
            "Acme: Package AlphaKit",
            "AlphaKit: synthetic package detail",
            "Version: | 2.4.1",
            "Published: | 2026-07-08",
            "License: | Apache-2.0",
            *("Additional public documentation line." for _ in range(30)),
        )
    )


def raw_result(*, text: str | None = None, url: str = URL, title: str = "Acme: Package AlphaKit") -> dict:
    return {
        "status": "ok",
        "url": url,
        "title": title,
        "text": raw_text() if text is None else text,
        "links": [{"url": URL + "?doc=1", "text": "documentation"}],
    }


def parent_payload(raw: dict) -> dict:
    projected = projection.build_projection(
        QUESTION,
        {"title": raw["title"], "url": raw["url"], "text": raw["text"]},
    )
    return {
        "status": "ok",
        "url": raw["url"],
        "title": raw["title"],
        "text": projected["projection"],
        "links": copy.deepcopy(raw["links"]),
        "projection_receipt": projected["content_free_receipt"],
        "parent_prefix": raw["text"][:5_000],
    }


def detail_payload(raw: dict) -> dict:
    projected = projection.build_projection(
        QUESTION,
        {"title": raw["title"], "url": raw["url"], "text": raw["text"]},
    )
    return build_helper_envelope(parent_payload(raw), projected["detail_field_receipt"])


def parent_client(process: Process) -> DetailFieldLatePageBoundSearchClient:
    def launch(command, **kwargs):
        del kwargs
        process.command = command
        return process

    return DetailFieldLatePageBoundSearchClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        visible_question=QUESTION,
        timeout=65,
        max_retries=2,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=5_000,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=200.0,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        monotonic=Clock(),
        late_page_fetch_popen=launch,
    )


def observed_client(process: Process) -> DetailStageObservedSearchClient:
    def launch(command, **kwargs):
        del kwargs
        process.command = command
        return process

    return DetailStageObservedSearchClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        visible_question=QUESTION,
        timeout=65,
        max_retries=2,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=5_000,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=200.0,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        monotonic=Clock(),
        detail_stage_observer_popen=launch,
    )


class DetailStageObserverFetchTests(unittest.TestCase):
    def test_observed_helper_parent_result_is_exact_parent_output(self) -> None:
        raw = raw_result()
        envelope = observed_output(raw, requested_url=URL, question=QUESTION)
        self.assertEqual(envelope["parent_result"], parent_payload(raw))
        self.assertEqual(
            envelope["detail_field_receipt"],
            projection.build_projection(
                QUESTION,
                {"title": raw["title"], "url": raw["url"], "text": raw["text"]},
            )["detail_field_receipt"],
        )

    def test_parent_fetch_result_and_parent_receipt_are_identical(self) -> None:
        raw = raw_result()
        parent_process = Process(parent_payload(raw))
        observed_process = Process(detail_payload(raw))
        baseline = parent_client(parent_process)
        candidate = observed_client(observed_process)
        self.assertEqual(baseline._fetch_url(URL), candidate._fetch_url(URL))
        self.assertEqual(
            baseline.late_page_projection_receipt(),
            candidate.late_page_projection_receipt(),
        )
        self.assertEqual(Path(parent_process.command[-1]).resolve(), PARENT_HELPER.resolve())
        self.assertEqual(Path(observed_process.command[-1]).resolve(), HELPER.resolve())
        self.assertEqual(parent_process.stdin_value, observed_process.stdin_value)

    def test_stage_signature_and_counts_are_content_free(self) -> None:
        target = observed_client(Process(detail_payload(raw_result())))
        target._fetch_url(URL)
        receipt = target.detail_stage_observer_receipt()
        self.assertEqual(receipt["observed_detail_receipt_count"], 1)
        self.assertEqual(receipt["stage_signature_counts"], {"c1p1a1s1f1d1r1": 1})
        self.assertEqual(receipt["discovered_record_page_count"], 1)
        self.assertEqual(receipt["retained_record_page_count"], 1)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("AlphaKit", serialized)
        self.assertNotIn("https://", serialized)

    def test_failed_stage_is_localized_without_surface_retention(self) -> None:
        raw = raw_result(
            url="https://packages.acme.example/web/packages/Other/index.html",
            title="Other package",
            text="Narrative without the target fields. " * 50,
        )
        target = observed_client(Process(detail_payload(raw)))
        target._fetch_url(URL)
        receipt = target.detail_stage_observer_receipt()
        self.assertEqual(receipt["observed_detail_receipt_count"], 1)
        self.assertEqual(receipt["stage_signature_counts"], {"c1p0a1s0f0d0r0": 1})
        self.assertEqual(receipt["identity_url_path_bound_page_count"], 0)
        self.assertEqual(receipt["authority_url_token_bound_page_count"], 1)
        self.assertEqual(receipt["all_target_fields_unique_page_count"], 0)

    def test_invalid_envelope_fails_parent_closed_and_is_counted(self) -> None:
        raw = raw_result()
        envelope = detail_payload(raw)
        envelope["detail_field_receipt"]["identity_url_path_match_count"] = 0
        target = observed_client(Process(envelope))
        self.assertEqual(target._fetch_url(URL)["status"], "helper_invalid_result")
        receipt = target.detail_stage_observer_receipt()
        self.assertEqual(receipt["invalid_observer_envelope_count"], 1)
        self.assertEqual(receipt["observed_detail_receipt_count"], 0)

    def test_nonzero_and_timeout_preserve_parent_failure_behavior(self) -> None:
        nonzero = observed_client(Process({}, returncode=2))
        self.assertEqual(nonzero._fetch_url(URL)["status"], "helper_nonzero_exit")

        class SlowProcess(Process):
            def communicate(self, value, timeout=None):
                del value
                raise subprocess.TimeoutExpired("helper", timeout)

        slow = observed_client(SlowProcess({}))
        slow._terminate_group = lambda _process: None
        self.assertEqual(slow._fetch_url(URL)["status"], "hard_deadline_exceeded")

    def test_tampered_observer_receipt_is_rejected(self) -> None:
        target = observed_client(Process(detail_payload(raw_result())))
        target._fetch_url(URL)
        receipt = target.detail_stage_observer_receipt()
        receipt["stage_signature_counts"] = {"c1p1a1s1f1d1r0": 1}
        unsigned = dict(receipt)
        unsigned.pop("receipt_payload_sha256")
        from deepwide_agent.v24263_global_model_limiter import payload_sha256

        receipt["receipt_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaises(ValueError):
            validate_observer_receipt(receipt)

    def test_search_class_preserves_frozen_fetch_owner(self) -> None:
        validate_search_class()
        owner = next(
            base for base in DetailStageObservedSearchClient.__mro__ if "_fetch_url" in base.__dict__
        )
        from deepwide_agent.v24981_late_page_bound_fetch import LatePageBoundFetchMixin

        self.assertIs(owner, LatePageBoundFetchMixin)


if __name__ == "__main__":
    unittest.main()
