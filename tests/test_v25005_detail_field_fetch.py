from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25004_identity_bound_detail_fields as projection  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    LatePageBoundFetchMixin,
    LatePageBoundSearchClient,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
)
from deepwide_agent.v25005_detail_field_fetch import (  # noqa: E402
    HELPER,
    DetailFieldLatePageBoundSearchClient,
    validate_search_class,
)


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


def projected_payload() -> dict:
    raw = raw_text()
    value = projection.build_projection(
        QUESTION, {"title": "Acme: Package AlphaKit", "url": URL, "text": raw}
    )
    return {
        "status": "ok",
        "url": URL,
        "title": "Acme: Package AlphaKit",
        "text": value["projection"],
        "links": [{"url": URL + "?doc=1", "text": "documentation"}],
        "projection_receipt": value["content_free_receipt"],
        "parent_prefix": raw[:5_000],
    }


def client(process: Process) -> DetailFieldLatePageBoundSearchClient:
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


class DetailFieldFetchTests(unittest.TestCase):
    def test_helper_is_ordinary_repo_local_file(self) -> None:
        self.assertTrue(HELPER.is_file())
        self.assertFalse(HELPER.is_symlink())
        self.assertTrue(HELPER.resolve().is_relative_to(ROOT))

    def test_search_class_preserves_complete_parent_boundary(self) -> None:
        validate_search_class()
        self.assertTrue(
            issubclass(
                DetailFieldLatePageBoundSearchClient,
                RobustLatePageBoundSearchClient,
            )
        )
        self.assertTrue(
            issubclass(DetailFieldLatePageBoundSearchClient, LatePageBoundSearchClient)
        )
        owner = next(
            base
            for base in DetailFieldLatePageBoundSearchClient.__mro__
            if "_fetch_url" in base.__dict__
        )
        self.assertIs(owner, LatePageBoundFetchMixin)

    def test_bound_helper_result_is_forwarded_under_parent_caps(self) -> None:
        process = Process(projected_payload())
        target = client(process)
        result = target._fetch_url(URL)
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(len(result["text"]), 5_000)
        self.assertEqual(Path(process.command[-1]).resolve(), HELPER.resolve())
        self.assertEqual(process.stdin_value, {"url": URL, "question": QUESTION})
        self.assertEqual(len(result["links"]), 1)
        receipt = target.late_page_projection_receipt()
        self.assertEqual(receipt["fetch_calls_snapshot"], 1)
        self.assertEqual(receipt["projected_page_count"], 1)
        self.assertEqual(receipt["mechanism_engaged_page_count"], 1)
        self.assertEqual(receipt["retained_record_count"], 1)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_nonzero_timeout_and_bad_payload_fail_closed(self) -> None:
        nonzero = client(Process({}, returncode=2))
        self.assertEqual(nonzero._fetch_url(URL)["status"], "helper_nonzero_exit")

        class SlowProcess(Process):
            def communicate(self, value, timeout=None):
                del value
                raise subprocess.TimeoutExpired("helper", timeout)

        slow = client(SlowProcess({}))
        slow._terminate_group = lambda _process: None
        self.assertEqual(slow._fetch_url(URL)["status"], "hard_deadline_exceeded")

        invalid = projected_payload()
        invalid["text"] += "x"
        self.assertEqual(client(Process(invalid))._fetch_url(URL)["status"], "helper_invalid_result")


if __name__ == "__main__":
    unittest.main()
