from __future__ import annotations

import copy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import native_search as native  # noqa: E402
from deepwide_agent import v24468_total_wall_transport as transport  # noqa: E402
from deepwide_agent.v24606_content_free_title_provenance import (  # noqa: E402
    ContentFreeTitleProvenanceObserver,
    validate_receipt,
)


def payload() -> dict:
    return {
        "id": "synthetic-response",
        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        "output": [
            {
                "type": "web_search_call",
                "id": "synthetic-call",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": ["synthetic"],
                    "sources": [
                        {
                            "type": "web_source",
                            "url": "https://same.example/record",
                            "title": "",
                        },
                        {
                            "type": "web_source",
                            "url": "https://action.example/record",
                            "title": "Action title",
                        },
                    ],
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "[[QUERY Q0001]]\nsynthetic evidence\n[[END Q0001]]\n",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://same.example/record",
                                "title": "Citation title",
                                "start_index": 18,
                                "end_index": 36,
                            }
                        ],
                    }
                ],
            },
        ],
    }


def client() -> transport.HardTotalWallNativeSearchClient:
    return transport.HardTotalWallNativeSearchClient(
        "http://127.0.0.1:9/responses",
        "synthetic",
        reasoning_effort="",
        service_tier="",
        timeout=70,
        max_retries=1,
        max_workers=1,
        batch_size=8,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=5_000,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=300,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.01,
        monotonic=lambda: 0.0,
        sleeper=lambda _seconds: None,
    )


class V24606ContentFreeTitleProvenanceTests(unittest.TestCase):
    def test_action_citation_and_fetch_boundaries_are_counted(self) -> None:
        search = client()

        def fake_fetch(_instance, url):
            if "empty-page-title" in url:
                return {
                    "status": "ok",
                    "url": url,
                    "title": "",
                    "text": "usable page",
                    "links": [],
                }
            return {
                "status": "ok",
                "url": url,
                "title": "Fetched page title",
                "text": "usable page",
                "links": [],
            }

        search._fetch_url = types.MethodType(fake_fetch, search)
        response = {
            "kind": "response",
            "status_code": 200,
            "retry_after": "",
            "payload": payload(),
            "payload_is_object": True,
        }
        with patch.object(transport, "run_total_wall_post", return_value=response):
            with ContentFreeTitleProvenanceObserver() as observer:
                returned = search._request(["synthetic"])
                fetched = search.fetch_urls(
                    [
                        {
                            "url": "https://fetched.example/record",
                            "query": "synthetic",
                            "title": "",
                        },
                        {
                            "url": "https://empty-page-title.example/record",
                            "query": "synthetic",
                            "title": "Seed title",
                        },
                    ]
                )
        self.assertEqual(returned, payload())
        self.assertEqual(
            [batch["results"][0]["title"] for batch in fetched],
            ["Fetched page title", "Seed title"],
        )
        receipt = validate_receipt(observer.content_free_receipt())
        self.assertEqual(receipt["provider_response_count"], 1)
        self.assertEqual(receipt["action_source_count"], 2)
        self.assertEqual(receipt["action_source_empty_title_count"], 1)
        self.assertEqual(receipt["action_source_nonempty_title_count"], 1)
        self.assertEqual(receipt["query_local_citation_count"], 1)
        self.assertEqual(
            receipt["same_url_action_empty_citation_nonempty_count"], 1
        )
        self.assertEqual(receipt["effective_fetch_request_count"], 2)
        self.assertEqual(receipt["fetch_request_empty_title_count"], 1)
        self.assertEqual(receipt["fetched_result_nonempty_title_count"], 2)
        self.assertEqual(
            receipt["empty_fetch_request_to_nonempty_result_title_count"], 1
        )
        self.assertEqual(
            receipt["nonempty_fetch_request_to_nonempty_result_title_count"], 1
        )

    def test_empty_execution_is_valid_and_effect_surface_is_false(self) -> None:
        with ContentFreeTitleProvenanceObserver() as observer:
            pass
        receipt = validate_receipt(observer.content_free_receipt())
        self.assertTrue(receipt["provider_payload_and_fetch_batches_returned_exactly"])
        self.assertFalse(receipt["query_search_fetch_model_process_or_evaluator_effect_added"])
        self.assertFalse(
            receipt["ranking_validator_evidence_posterior_entropy_or_credit_changed"]
        )

    def test_nested_context_fails_closed_and_bindings_restore(self) -> None:
        request = transport.HardTotalWallNativeSearchClient._request
        fetch = native.AzureNativeSearchClient.fetch_urls
        with ContentFreeTitleProvenanceObserver():
            with self.assertRaisesRegex(RuntimeError, "already active"):
                ContentFreeTitleProvenanceObserver().__enter__()
        self.assertIs(transport.HardTotalWallNativeSearchClient._request, request)
        self.assertIs(native.AzureNativeSearchClient.fetch_urls, fetch)

    def test_resealed_tamper_fails_closed(self) -> None:
        with ContentFreeTitleProvenanceObserver() as observer:
            pass
        receipt = observer.content_free_receipt()
        cases = (
            ("action_source_count", 1),
            ("raw_task_question_query_url_title_page_prediction_or_credential_emitted", True),
            ("query_search_fetch_model_process_or_evaluator_effect_added", True),
        )
        for name, value in cases:
            changed = copy.deepcopy(receipt)
            changed[name] = value
            with self.assertRaises(ValueError):
                validate_receipt(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24606_content_free_title_provenance.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
