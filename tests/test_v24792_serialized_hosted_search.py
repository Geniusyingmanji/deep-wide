from __future__ import annotations

import concurrent.futures
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24792_serialized_hosted_search import (  # noqa: E402
    SerializedThinHostedSearchClient,
    prepare_slot_directory,
    validate_receipt,
    validate_search_class,
)


def response_payload(identifier: str = "search") -> dict:
    return {
        "kind": "response",
        "status_code": 200,
        "retry_after": "",
        "payload": {
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "output": [
                {
                    "type": "web_search_call",
                    "id": identifier,
                    "action": {"type": "search", "sources": []},
                }
            ],
        },
    }


class V24792SerializedHostedSearchTests(unittest.TestCase):
    def client(self, directory: Path, **kwargs) -> SerializedThinHostedSearchClient:
        return SerializedThinHostedSearchClient(
            "http://127.0.0.1:9878/responses",
            "gpt-5.6-sol",
            timeout=5,
            max_retries=2,
            fetch_pages=False,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=time.monotonic() + 20,
            search_slot_directory=directory,
            output_root=directory.parent,
            **kwargs,
        )

    def test_class_is_append_only_thin_search_successor(self) -> None:
        validate_search_class()

    def test_create_only_slot_directory(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            path = Path(raw) / "slots"
            prepare_slot_directory(path)
            self.assertTrue((path / "slot_01.lock").is_file())
            with self.assertRaises(FileExistsError):
                prepare_slot_directory(path)

    def test_concurrent_effects_are_serialized(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_slot_directory(slots)
            active = 0
            maximum = 0
            lock = threading.Lock()

            def post(**_kwargs):
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(0.03)
                with lock:
                    active -= 1
                return response_payload()

            clients = [self.client(slots) for _ in range(4)]
            with patch(
                "deepwide_agent.v24792_serialized_hosted_search.run_total_wall_post",
                side_effect=post,
            ):
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    rows = list(pool.map(lambda client: client._request(["neutral"]), clients))
            self.assertEqual(len(rows), 4)
            self.assertEqual(maximum, 1)
            self.assertEqual(sum(client.search_slot_acquisitions for client in clients), 4)

    def test_missing_action_is_retried_within_frozen_attempt_cap(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_slot_directory(slots)
            client = self.client(slots, sleeper=lambda _seconds: None)
            missing = response_payload()
            missing["payload"]["output"] = []
            with patch(
                "deepwide_agent.v24792_serialized_hosted_search.run_total_wall_post",
                side_effect=[missing, response_payload("second")],
            ):
                value = client._request(["neutral"])
            self.assertEqual(value["output"][0]["id"], "second")
            self.assertEqual(client.calls, 2)
            receipt = client.search_slot_receipt()
            self.assertEqual(receipt["acquisitions"], 2)
            self.assertEqual(receipt["no_action_responses"], 1)
            self.assertEqual(receipt["no_action_retries"], 1)
            validate_receipt(receipt)

    def test_receipt_is_content_free_and_label_blind(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_slot_directory(slots)
            value = self.client(slots).search_slot_receipt()
            self.assertTrue(value["label_blind"])
            self.assertFalse(
                value[
                    "contains_question_query_url_page_prediction_answer_opaque_id_or_credential"
                ]
            )
            self.assertFalse(
                value[
                    "mapping_gold_category_question_type_split_evaluator_score_reward_read"
                ]
            )


if __name__ == "__main__":
    unittest.main()
