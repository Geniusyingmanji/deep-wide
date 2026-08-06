from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24269_task_union_discovery import (  # noqa: E402
    TaskUnionDiscoverySearchClient,
)
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    TaskUnionSingleShotNativeSearchClient,
    validate_receipt as validate_legacy_receipt,
)
from deepwide_agent.v24627_same_response_citation_title_backfill import (  # noqa: E402
    SameResponseCitationTitleBackfillNativeSearchClient,
    validate_compatibility_successor,
    validate_receipt,
)


def response(
    *,
    marker_count: int,
    action_sources: list[dict],
    citations: list[tuple[str, str]],
    response_id: str = "response",
) -> dict:
    text = "".join(
        f"[[QUERY Q{index:04d}]]\nsummary\n[[END Q{index:04d}]]\n"
        for index in range(1, marker_count + 1)
    )
    if not text:
        text = "provider summary without query markers"
    annotations = []
    # Put citations inside the first mapped query section when markers exist;
    # without markers they remain valid response annotations but cannot be
    # assigned to a logical query by the native parser.
    citation_start = text.find("summary") if marker_count else 0
    for url, title in citations:
        annotations.append(
            {
                "type": "url_citation",
                "url": url,
                "title": title,
                "start_index": citation_start,
                "end_index": citation_start + 1,
            }
        )
    return {
        "id": response_id,
        "output": [
            {
                "type": "web_search_call",
                "id": f"call-{response_id}",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": ["one", "two"],
                    "sources": action_sources,
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                        "annotations": annotations,
                    }
                ],
            },
        ],
    }


class FakeBackfill(SameResponseCitationTitleBackfillNativeSearchClient):
    def __init__(self, payloads: list[dict]) -> None:
        super().__init__(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            batch_size=8,
        )
        self.payloads = copy.deepcopy(payloads)
        self.requests: list[list[str]] = []
        self.enrich_calls = 0

    def _request(self, queries):  # type: ignore[override]
        self.requests.append(list(queries))
        return copy.deepcopy(self.payloads.pop(0))

    def _enrich_pages(self, batches):  # type: ignore[override]
        self.enrich_calls += 1


class FakeLegacy(TaskUnionSingleShotNativeSearchClient):
    def __init__(self, payload: dict) -> None:
        super().__init__(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            batch_size=8,
        )
        self.payload = copy.deepcopy(payload)

    def _request(self, queries):  # type: ignore[override]
        return copy.deepcopy(self.payload)


def union_results(client, payload_count: int = 1):
    union = TaskUnionDiscoverySearchClient(client)
    rows = []
    for _ in range(payload_count):
        rows.append(union.search_many(["one", "two"], max_results=8))
    return rows


class V24627SameResponseCitationTitleBackfillTests(unittest.TestCase):
    def test_unmapped_citation_backfills_a_surviving_union_lead(self) -> None:
        payload = response(
            marker_count=0,
            action_sources=[
                {
                    "type": "web_source",
                    "url": "https://a.example/page#fragment",
                    "title": "",
                }
            ],
            citations=[("https://a.example/page", "Alpha History")],
        )
        original = copy.deepcopy(payload)
        client = FakeBackfill([payload])
        rows = union_results(client)[0]

        self.assertEqual(rows[0]["results"][0]["title"], "Alpha History")
        self.assertEqual(payload, original)
        receipt = client.citation_title_backfill_receipt()
        self.assertEqual(receipt["backfilled_action_source_count"], 1)
        self.assertEqual(receipt["backfilled_unique_url_count"], 1)
        self.assertEqual(receipt["surviving_backfilled_union_lead_count"], 1)
        self.assertEqual(receipt["query_local_shadowed_backfilled_url_count"], 0)

    def test_mapped_citation_backfill_is_counted_as_shadowed_not_improvement(self) -> None:
        payload = response(
            marker_count=2,
            action_sources=[
                {"type": "web_source", "url": "https://a.example/page", "title": ""}
            ],
            citations=[("https://a.example/page", "Alpha")],
        )
        successor = FakeBackfill([payload])
        successor_rows = union_results(successor)[0]
        legacy_rows = union_results(FakeLegacy(payload))[0]

        self.assertEqual(successor_rows, legacy_rows)
        receipt = successor.citation_title_backfill_receipt()
        self.assertEqual(receipt["backfilled_action_source_count"], 1)
        self.assertEqual(receipt["surviving_backfilled_union_lead_count"], 0)
        self.assertEqual(receipt["query_local_shadowed_backfilled_url_count"], 1)

    def test_existing_action_title_is_preserved_even_when_citation_differs(self) -> None:
        payload = response(
            marker_count=0,
            action_sources=[
                {
                    "type": "web_source",
                    "url": "https://a.example/page",
                    "title": "Provider Title",
                }
            ],
            citations=[("https://a.example/page", "Citation Title")],
        )
        client = FakeBackfill([payload])
        rows = union_results(client)[0]
        self.assertEqual(rows[0]["results"][0]["title"], "Provider Title")
        receipt = client.citation_title_backfill_receipt()
        self.assertEqual(receipt["nonempty_action_source_preserved_count"], 1)
        self.assertEqual(receipt["backfilled_action_source_count"], 0)

    def test_conflicting_citation_titles_fail_closed(self) -> None:
        payload = response(
            marker_count=0,
            action_sources=[
                {"type": "web_source", "url": "https://a.example/page", "title": ""}
            ],
            citations=[
                ("https://a.example/page", "Alpha"),
                ("https://a.example/page#same", "Different Alpha"),
            ],
        )
        client = FakeBackfill([payload])
        rows = union_results(client)[0]
        self.assertEqual(rows[0]["results"][0]["title"], "")
        receipt = client.citation_title_backfill_receipt()
        self.assertEqual(receipt["conflicting_citation_url_count"], 1)
        self.assertEqual(receipt["backfilled_action_source_count"], 0)

    def test_cross_response_title_is_never_reused(self) -> None:
        first = response(
            marker_count=0,
            action_sources=[],
            citations=[("https://a.example/page", "Alpha")],
            response_id="first",
        )
        second = response(
            marker_count=0,
            action_sources=[
                {"type": "web_source", "url": "https://a.example/page", "title": ""}
            ],
            citations=[],
            response_id="second",
        )
        client = FakeBackfill([first, second])
        rows = union_results(client, payload_count=2)
        self.assertEqual(rows[0], [])
        self.assertEqual(rows[1][0]["results"][0]["title"], "")
        self.assertEqual(
            client.citation_title_backfill_receipt()["backfilled_action_source_count"],
            0,
        )

    def test_earlier_action_source_wins_and_backfill_does_not_survive(self) -> None:
        payload = response(
            marker_count=0,
            action_sources=[
                {
                    "type": "web_source",
                    "url": "https://a.example/page",
                    "title": "Earlier",
                },
                {
                    "type": "web_source",
                    "url": "https://a.example/page#later",
                    "title": "",
                },
            ],
            citations=[("https://a.example/page", "Alpha")],
        )
        client = FakeBackfill([payload])
        rows = union_results(client)[0]
        self.assertEqual(rows[0]["results"][0]["title"], "Earlier")
        receipt = client.citation_title_backfill_receipt()
        self.assertEqual(receipt["backfilled_action_source_count"], 1)
        self.assertEqual(receipt["earlier_action_shadowed_backfilled_url_count"], 1)
        self.assertEqual(receipt["surviving_backfilled_union_lead_count"], 0)

    def test_no_extra_request_fetch_or_enrichment_effect_is_added(self) -> None:
        payload = response(
            marker_count=0,
            action_sources=[
                {"type": "web_source", "url": "https://a.example/page", "title": ""}
            ],
            citations=[("https://a.example/page", "Alpha")],
        )
        client = FakeBackfill([payload])
        union_results(client)
        self.assertEqual(client.requests, [["one", "two"]])
        self.assertEqual(client.enrich_calls, 1)
        self.assertEqual(client.fetch_calls, 0)
        self.assertFalse(
            client.citation_title_backfill_receipt()[
                "additional_search_fetch_model_process_evaluator_or_credit_effect"
            ]
        )

    def test_legacy_receipt_schema_is_unchanged(self) -> None:
        payload = response(
            marker_count=0,
            action_sources=[
                {"type": "web_source", "url": "https://a.example/page", "title": ""}
            ],
            citations=[("https://a.example/page", "Alpha")],
        )
        client = FakeBackfill([payload])
        union_results(client)
        legacy = client.single_shot_receipt()
        validate_legacy_receipt(legacy)
        self.assertNotIn("backfill", json.dumps(legacy))
        validate_receipt(client.citation_title_backfill_receipt())

    def test_single_query_path_is_unchanged_and_unobserved(self) -> None:
        payload = response(
            marker_count=0,
            action_sources=[
                {"type": "web_source", "url": "https://a.example/page", "title": ""}
            ],
            citations=[("https://a.example/page", "Alpha")],
        )
        client = FakeBackfill([payload])
        rows = client.search_many(["one"], max_results=8)
        self.assertEqual(rows[0]["results"][0]["title"], "Alpha")
        receipt = client.citation_title_backfill_receipt()
        self.assertEqual(receipt["multi_query_payload_count"], 0)
        self.assertEqual(receipt["backfilled_action_source_count"], 0)

    def test_receipt_tamper_and_privileged_fields_fail_closed(self) -> None:
        client = FakeBackfill([])
        receipt = client.citation_title_backfill_receipt()
        receipt["surviving_backfilled_union_lead_count"] = 1
        with self.assertRaisesRegex(ValueError, "receipt drifted"):
            validate_receipt(receipt)
        receipt = client.citation_title_backfill_receipt()
        receipt["category"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "receipt drifted"):
            validate_receipt(receipt)

    def test_current_bounded_search_mro_remains_hard_total_wall_compatible(self) -> None:
        validate_compatibility_successor()


if __name__ == "__main__":
    unittest.main()
