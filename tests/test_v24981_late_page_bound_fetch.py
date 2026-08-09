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

from deepwide_agent import v24980_late_page_bound_projection as projection  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    HELPER,
    LatePageBoundSearchClient,
    validate_helper_result,
    validate_policy,
    validate_receipt,
    validate_search_class,
)


QUESTION = "Return a table. Column names: Entity | Value"


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


def projected_payload(*, changed: bool = True) -> dict:
    content = (
        "| Entity | Value |\n|---|---|\n| Late Entity | 999 |\n"
        + "padding " * 900
    )
    if changed:
        value = projection.build_projection(QUESTION, {
            "title": "Official", "url": "https://official.example/data", "text": content,
        })
    else:
        raw = "unstructured narrative " * 400
        value = projection.build_projection(QUESTION, {
            "title": "Official", "url": "https://official.example/data", "text": raw,
        })
    return {
        "status": "ok",
        "url": "https://official.example/data",
        "title": "Official",
        "text": value["projection"],
        "links": [],
        "projection_receipt": value["content_free_receipt"],
        "parent_prefix": content[:5_000] if changed else raw[:5_000],
    }


def client(process: Process, *, page_chars: int = 5_000) -> LatePageBoundSearchClient:
    def launch(command, **kwargs):
        del kwargs
        process.command = command
        return process

    return LatePageBoundSearchClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        visible_question=QUESTION,
        timeout=65,
        max_retries=2,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=page_chars,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=200.0,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        monotonic=Clock(),
        late_page_fetch_popen=launch,
    )


class V24981LatePageBoundFetchTests(unittest.TestCase):
    def test_bound_helper_result_is_forwarded_under_parent_cap(self) -> None:
        process = Process(projected_payload())
        target = client(process)
        result = target._fetch_url("https://official.example/data")
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(len(result["text"]), 5_000)
        self.assertEqual(Path(process.command[-1]).resolve(), HELPER.resolve())
        self.assertEqual(process.stdin_value["question"], QUESTION)
        self.assertTrue(target.parent_prefix_for("https://official.example/data"))
        receipt = target.late_page_projection_receipt()
        self.assertEqual(receipt["fetch_calls_snapshot"], 1)
        self.assertEqual(receipt["projected_page_count"], 1)
        self.assertEqual(receipt["mechanism_engaged_page_count"], 1)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_exact_prefix_handoff_is_accounted(self) -> None:
        process = Process(projected_payload(changed=False))
        target = client(process)
        self.assertEqual(target._fetch_url("https://official.example/data")["status"], "ok")
        receipt = target.late_page_projection_receipt()
        self.assertEqual(receipt["exact_parent_prefix_handoff_page_count"], 1)
        self.assertEqual(receipt["mechanism_engaged_page_count"], 0)

    def test_invalid_helper_result_fails_closed(self) -> None:
        payload = projected_payload()
        payload["text"] += "x"
        process = Process(payload)
        target = client(process)
        result = target._fetch_url("https://official.example/data")
        self.assertEqual(result["status"], "helper_invalid_result")
        self.assertEqual(target.fetch_helper_failures, 1)

    def test_helper_nonzero_and_timeout_remain_bounded(self) -> None:
        nonzero = client(Process({}, returncode=2))
        self.assertEqual(nonzero._fetch_url("https://official.example/data")["status"], "helper_nonzero_exit")

        class SlowProcess(Process):
            def communicate(self, value, timeout=None):
                del value
                raise subprocess.TimeoutExpired("helper", timeout)

        slow_process = SlowProcess({})
        slow = client(slow_process)
        slow._terminate_group = lambda _process: None
        self.assertEqual(slow._fetch_url("https://official.example/data")["status"], "hard_deadline_exceeded")
        self.assertEqual(slow.hard_fetch_deadline_failures, 1)

    def test_parent_cap_and_visible_question_are_required(self) -> None:
        with self.assertRaises(ValueError):
            client(Process({}), page_chars=12_000)
        with self.assertRaises(ValueError):
            LatePageBoundSearchClient(
                "http://127.0.0.1:9878/responses",
                "gpt-5.6-sol",
                visible_question="",
                max_page_chars=5_000,
                hard_fetch_deadline_seconds=25,
                absolute_deadline=200.0,
            )

    def test_failed_fetch_may_not_carry_projection_receipt(self) -> None:
        payload = projected_payload()
        payload["status"] = "http_404"
        with self.assertRaises(ValueError):
            validate_helper_result(payload)

    def test_receipt_tamper_is_rejected(self) -> None:
        target = client(Process(projected_payload()))
        target._fetch_url("https://official.example/data")
        receipt = copy.deepcopy(target.late_page_projection_receipt())
        receipt["additional_search_fetch_model_token_context_wall_or_network_byte_cap"] = True
        with self.assertRaises(ValueError):
            validate_receipt(receipt)

    def test_class_and_policy_preserve_effect_caps(self) -> None:
        validate_search_class()
        policy = validate_policy()
        self.assertEqual(policy["maximum_network_response_bytes_per_fetch"], 3_000_000)
        self.assertEqual(policy["parent_page_character_cap"], 5_000)
        self.assertFalse(policy["additional_search_fetch_model_token_context_wall_or_network_byte_cap"])


if __name__ == "__main__":
    unittest.main()
