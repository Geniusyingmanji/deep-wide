from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    DeadlineTavilyThinCompatibilityClient,
    ENDPOINT,
    empty_receipt,
    prepare_key_slots,
    validate_receipt,
    validate_search_class,
)


def response(status: int, payload: dict | None = None) -> Mock:
    value = Mock()
    value.status_code = status
    value.json.return_value = payload or {}
    return value


class V24796DeadlineTavilyTests(unittest.TestCase):
    def test_empty_receipt_is_valid_content_free_baseline(self) -> None:
        value = validate_receipt(empty_receipt(12))
        self.assertEqual(value["key_slot_cap"], 12)
        self.assertEqual(value["provider_attempts"], 0)
        self.assertFalse(
            value["credential_value_persisted_hashed_emitted_or_in_error"]
        )

    def client(self, directory: Path, post, keys=("secret-one", "secret-two")):
        return DeadlineTavilyThinCompatibilityClient(
            "http://127.0.0.1:9878/responses",
            "gpt-5.6-sol",
            timeout=5,
            max_retries=2,
            fetch_pages=False,
            fetch_workers=1,
            fetch_timeout=20,
            max_page_chars=5000,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=time.monotonic() + 30,
            credentials=keys,
            key_slot_directory=directory,
            output_root=directory.parent,
            direct_timeout_seconds=5,
            direct_workers=2,
            direct_post=post,
            sleeper=lambda _seconds: None,
            slot_sleeper=lambda _seconds: None,
        )

    def test_class_preserves_frozen_runtime_type_contract(self) -> None:
        validate_search_class()

    def test_header_only_and_provider_content_is_stripped(self) -> None:
        post = Mock(
            return_value=response(
                200,
                {
                    "answer": "UNTRUSTED ANSWER",
                    "results": [
                        {
                            "title": "A",
                            "url": "https://a.example/page",
                            "content": "UNTRUSTED SNIPPET",
                            "raw_content": "UNTRUSTED RAW",
                            "score": 0.99,
                        }
                    ],
                },
            )
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_key_slots(slots, 2)
            client = self.client(slots, post)
            batch = client.search_many(
                ["visible query"], max_results=3, include_raw_content=False
            )[0]
        self.assertEqual(batch["answer"], "")
        self.assertEqual(batch["results"][0]["content"], "")
        self.assertEqual(batch["results"][0]["raw_content"], "")
        self.assertIsNone(batch["results"][0]["score"])
        call = post.call_args
        self.assertEqual(call.args[0], ENDPOINT)
        self.assertTrue(call.kwargs["headers"]["Authorization"].startswith("Bearer "))
        self.assertNotIn("secret-one", call.kwargs["data"])
        self.assertNotIn("secret-two", call.kwargs["data"])
        self.assertFalse(call.kwargs["allow_redirects"])
        self.assertTrue(call.kwargs["verify"])
        body = json.loads(call.kwargs["data"])
        self.assertFalse(body["include_answer"])
        self.assertFalse(body["include_raw_content"])

    def test_quota_disabled_slot_rotates_without_persisting_key(self) -> None:
        post = Mock(
            side_effect=[
                response(432),
                response(
                    200,
                    {"results": [{"title": "B", "url": "https://b.example/"}]},
                ),
            ]
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_key_slots(slots, 2)
            client = self.client(slots, post)
            batch = client.search_many(
                ["visible query"], max_results=3, include_raw_content=False
            )[0]
            encoded = "\n".join(
                path.read_text(encoding="utf-8") for path in slots.iterdir()
            )
            receipt = client.direct_search_receipt()
        self.assertEqual(len(batch["results"]), 1)
        self.assertEqual(receipt["key_local_disables"], 1)
        self.assertNotIn("secret-one", encoded)
        self.assertNotIn("secret-two", encoded)
        self.assertNotIn("secret-one", json.dumps(receipt))
        self.assertNotIn("secret-two", json.dumps(receipt))

    def test_credential_echo_is_rejected_and_receipt_is_content_free(self) -> None:
        post = Mock(
            return_value=response(
                200,
                {"results": [{"title": "secret-one", "url": "https://a.example/"}]},
            )
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_key_slots(slots, 2)
            client = self.client(slots, post)
            batch = client.search_many(
                ["visible query"], max_results=3, include_raw_content=False
            )[0]
            receipt = client.direct_search_receipt()
        self.assertEqual(batch["results"], [])
        self.assertEqual(receipt["credential_echo_rejections"], 1)
        self.assertEqual(post.call_count, 1)
        validate_receipt(receipt)
        self.assertFalse(
            receipt["credential_value_persisted_hashed_emitted_or_in_error"]
        )
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
        )

    def test_create_only_key_slots_reject_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_key_slots(slots, 2)
            with self.assertRaises(FileExistsError):
                prepare_key_slots(slots, 2)


if __name__ == "__main__":
    unittest.main()
