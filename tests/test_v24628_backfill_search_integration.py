from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24468_total_wall_transport as transport  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallNativeSearchClient,
)
from deepwide_agent.v24627_same_response_citation_title_backfill import (  # noqa: E402
    SameResponseCitationTitleBackfillMixin,
)
from deepwide_agent.v24628_backfill_search_integration import (  # noqa: E402
    build_bounded_same_response_title_backfill_search,
)


def response() -> dict:
    payload = {
        "id": "synthetic-response",
        "output": [
            {
                "type": "web_search_call",
                "id": "synthetic-search",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": ["one", "two"],
                    "sources": [
                        {
                            "type": "web_source",
                            "url": "https://example.invalid/a",
                            "title": "",
                        }
                    ],
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "unmapped citation",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://example.invalid/a",
                                "title": "Recovered title",
                                "start_index": 0,
                                "end_index": 8,
                            }
                        ],
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
    }
    return {
        "kind": "response",
        "status_code": 200,
        "retry_after": "",
        "payload": payload,
        "payload_is_object": True,
    }


class V24628BackfillSearchIntegrationTests(unittest.TestCase):
    def build(self, events: list[str]):
        return build_bounded_same_response_title_backfill_search(
            url="http://127.0.0.1:9/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=30,
            max_retries=1,
            absolute_deadline=time.monotonic() + 120,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.05,
            stage_callback=events.append,
            fetch_pages=False,
        )

    def test_factory_preserves_hard_request_and_backfill_chunk_owner(self) -> None:
        client = self.build([])
        cls = type(client)
        request_owner = next(base for base in cls.__mro__ if "_request" in base.__dict__)
        chunk_owner = next(base for base in cls.__mro__ if "_run_chunk" in base.__dict__)
        self.assertIs(request_owner, HardTotalWallNativeSearchClient)
        self.assertIs(chunk_owner, SameResponseCitationTitleBackfillMixin)

    def test_real_parse_path_backfills_before_task_union_selection(self) -> None:
        events: list[str] = []
        client = self.build(events)
        with patch.object(transport, "run_total_wall_post", return_value=response()) as post:
            batches = client.search_many(["one", "two"], max_results=3)
        trace = batches[0]["hosted_search_trace"]
        self.assertEqual(trace["actions"][0]["sources"][0]["title"], "Recovered title")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(client.hosted_search_attempts, 1)
        self.assertEqual(client.recursive_split_requests, 0)
        receipt = client.citation_title_backfill_receipt()
        self.assertEqual(receipt["backfilled_action_source_count"], 1)
        self.assertEqual(receipt["surviving_backfilled_union_lead_count"], 1)
        self.assertEqual(
            events,
            ["hosted_search_effect_started", "hosted_search_effect_finished"],
        )

    def test_receipts_are_content_free_and_no_extra_effect_is_added(self) -> None:
        client = self.build([])
        with patch.object(transport, "run_total_wall_post", return_value=response()):
            client.search_many(["private one", "private two"], max_results=3)
        encoded = json.dumps(
            {
                "transport": client.transport_health(),
                "single_shot": client.single_shot_receipt(),
                "backfill": client.citation_title_backfill_receipt(),
            },
            sort_keys=True,
        )
        self.assertNotIn("private one", encoded)
        self.assertNotIn("example.invalid", encoded)
        self.assertNotIn("Recovered title", encoded)
        self.assertFalse(
            client.citation_title_backfill_receipt()[
                "additional_search_fetch_model_process_evaluator_or_credit_effect"
            ]
        )


if __name__ == "__main__":
    unittest.main()
