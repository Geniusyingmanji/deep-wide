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
from deepwide_agent.v24468_total_wall_transport import HardTotalWallNativeSearchClient  # noqa: E402
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    ThinSameResponseCitationTitleBackfillMixin,
    ThinSameResponseCitationTitleBackfillSearchClient,
    validate_thin_search_class,
)


def response() -> dict:
    return {
        "kind": "response", "status_code": 200, "retry_after": "",
        "payload_is_object": True,
        "payload": {
            "id": "r",
            "output": [
                {"type": "web_search_call", "id": "s", "status": "completed",
                 "action": {"type": "search", "sources": [
                     {"type": "web_source", "url": "https://a.invalid/x", "title": ""}
                 ]}},
                {"type": "message", "content": [{"type": "output_text", "text": "x",
                 "annotations": [{"type": "url_citation", "url": "https://a.invalid/x",
                                  "title": "Alpha", "start_index": 0, "end_index": 1}]}]},
            ],
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        },
    }


class V24630ThinBackfillSearchTests(unittest.TestCase):
    def client(self):
        return ThinSameResponseCitationTitleBackfillSearchClient(
            "http://127.0.0.1:9/responses", "synthetic",
            reasoning_effort="low", service_tier="", timeout=30, max_retries=1,
            fetch_pages=False, hard_fetch_deadline_seconds=25,
            absolute_deadline=time.monotonic() + 120,
            cleanup_reserve_seconds=5, minimum_attempt_seconds=0.05,
        )

    def test_mro_is_thin_hard_total_wall_and_backfill_owned(self) -> None:
        validate_thin_search_class()
        cls = ThinSameResponseCitationTitleBackfillSearchClient
        self.assertIs(next(base for base in cls.__mro__ if "_request" in base.__dict__), HardTotalWallNativeSearchClient)
        self.assertIs(next(base for base in cls.__mro__ if "_run_chunk" in base.__dict__), ThinSameResponseCitationTitleBackfillMixin)

    def test_real_parse_path_backfills_without_extra_request(self) -> None:
        client = self.client()
        with patch.object(transport, "run_total_wall_post", return_value=response()) as post:
            rows = client.search_many(["one", "two"], max_results=3)
        self.assertEqual(rows[0]["hosted_search_trace"]["actions"][0]["sources"][0]["title"], "Alpha")
        self.assertEqual(post.call_count, 1)
        receipt = client.citation_title_backfill_receipt()
        self.assertEqual(receipt["backfilled_action_source_count"], 1)
        self.assertEqual(receipt["surviving_backfilled_union_lead_count"], 1)
        encoded = json.dumps(receipt)
        self.assertNotIn("a.invalid", encoded)
        self.assertNotIn("Alpha", encoded)


if __name__ == "__main__":
    unittest.main()
