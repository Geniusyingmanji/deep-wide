from __future__ import annotations

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import SearchRequestError
from deepwide_agent.native_search import (
    AzureNativeSearchClient,
    _public_http_url,
    decode_web_text,
    html_to_document,
    html_to_text,
)


def payload_for(sections: list[tuple[str, str, str]]) -> dict:
    text_parts: list[str] = []
    annotations: list[dict] = []
    for index, (summary, url, title) in enumerate(sections, start=1):
        marker = f"[[QUERY Q{index:04d}]]\n"
        text_parts.append(marker)
        start = sum(len(value) for value in text_parts) + len(summary)
        citation = f" [{title}]"
        text_parts.append(summary + citation + f"\n[[END Q{index:04d}]]\n")
        annotations.append(
            {
                "type": "url_citation",
                "url": url,
                "title": title,
                "start_index": start,
                "end_index": start + len(citation),
            }
        )
    return {
        "id": "resp_test",
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        "output": [
            {
                "type": "web_search_call",
                "id": "ws_test",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": [summary for summary, _, _ in sections],
                    "sources": [
                        {"type": "web_source", "url": url, "title": title}
                        for _, url, title in sections
                    ],
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "".join(text_parts),
                        "annotations": annotations,
                    }
                ],
            },
        ],
    }


class NativeSearchTests(unittest.TestCase):
    def client(self, **kwargs) -> AzureNativeSearchClient:
        return AzureNativeSearchClient(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            **kwargs,
        )

    def test_query_local_citations_are_not_broadcast(self) -> None:
        client = self.client()
        payload = payload_for(
            [
                ("alpha fact", "https://a.example/page", "Alpha"),
                ("beta fact", "https://b.example/page", "Beta"),
            ]
        )
        batches, complete = client._parse_batch(
            ["alpha query", "beta query"], payload, max_results=8
        )
        self.assertTrue(complete)
        self.assertEqual([row["query"] for row in batches], ["alpha query", "beta query"])
        self.assertEqual(
            [[item["url"] for item in row["results"]] for row in batches],
            [["https://a.example/page"], ["https://b.example/page"]],
        )
        self.assertNotIn("beta fact", batches[0]["answer"])
        self.assertNotIn("alpha fact", batches[1]["answer"])

    def test_complete_sources_fallback_is_single_query_only(self) -> None:
        payload = payload_for([("fact", "https://a.example/page", "Alpha")])
        payload["output"][1]["content"][0]["annotations"] = []
        client = self.client()
        batches, complete = client._parse_batch(["query"], payload, max_results=8)
        self.assertTrue(complete)
        self.assertEqual(batches[0]["results"][0]["source_type"], "web_source")

    def test_missing_marker_splits_only_after_a_successful_response(self) -> None:
        class SplitClient(AzureNativeSearchClient):
            def __init__(self) -> None:
                super().__init__(
                    "http://unused", "model", fetch_pages=False, max_workers=1
                )
                self.requests: list[list[str]] = []

            def _request(self, queries):  # type: ignore[override]
                self.requests.append(list(queries))
                if len(queries) > 1:
                    value = payload_for([("only first", "https://a.example", "A")])
                    return value
                return payload_for([(queries[0], f"https://{queries[0]}.example", queries[0])])

        client = SplitClient()
        rows = client._run_chunk(["one", "two"], 4)
        self.assertEqual([row["query"] for row in rows], ["one", "two"])
        self.assertEqual(client.requests, [["one", "two"], ["one"], ["two"]])

    def test_request_failure_does_not_recursively_amplify_calls(self) -> None:
        class FailingClient(AzureNativeSearchClient):
            def __init__(self) -> None:
                super().__init__(
                    "http://unused", "model", fetch_pages=False, max_workers=1
                )
                self.requests = 0

            def _request(self, queries):  # type: ignore[override]
                self.requests += 1
                raise SearchRequestError("failed")

        client = FailingClient()
        rows = client._run_chunk(["one", "two", "three"], 4)
        self.assertEqual(client.requests, 1)
        self.assertEqual(client.failures, 3)
        self.assertTrue(all(row["error"] == "failed" for row in rows))

    def test_final_rate_limit_attempt_does_not_sleep(self) -> None:
        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "90"}
        session = Mock()
        session.post.return_value = response
        client = self.client(max_retries=1)
        client._thread_local.session = session

        with patch("deepwide_agent.native_search.time.sleep") as sleep:
            with self.assertRaises(SearchRequestError):
                client._request(["query"])

        sleep.assert_not_called()
        self.assertEqual(client.status_counts, {429: 1})

    def test_html_extractor_removes_scripts_and_preserves_table_cells(self) -> None:
        title, text = html_to_text(
            "<html><head><title>Example</title><script>bad()</script></head>"
            "<body><h1>Heading</h1><table><tr><th>A</th><th>B</th></tr>"
            "<tr><td>1</td><td>2</td></tr></table></body></html>"
        )
        self.assertEqual(title, "Example")
        self.assertIn("Heading", text)
        self.assertIn("A", text)
        self.assertIn("2", text)
        self.assertNotIn("bad()", text)

    def test_html_extractor_keeps_one_line_per_table_record(self) -> None:
        _, text = html_to_text(
            "<table><tr><th>Season</th><th>Episode</th><th>Singer</th>"
            "<th>Song</th></tr><tr><td>S1</td><td>E1</td><td>Alpha</td>"
            "<td>Song A</td></tr><tr><td>S1</td><td>E1</td><td>Beta</td>"
            "<td>Song B</td></tr></table>"
        )
        rows = [line for line in text.splitlines() if " | " in line]
        self.assertEqual(
            rows,
            [
                "Season | Episode | Singer | Song",
                "S1 | E1 | Alpha | Song A",
                "S1 | E1 | Beta | Song B",
            ],
        )

    def test_html_document_resolves_visible_links_and_deduplicates(self) -> None:
        title, text, links = html_to_document(
            "<html><head><title>Directory</title></head><body>"
            '<a href="/subject/math"> Mathematics </a>'
            '<a href="https://example.com/subject/math#top">Mathematics</a>'
            '<a href="../subject/physics">Physics</a>'
            '<a href="javascript:alert(1)">Bad</a>'
            "</body></html>",
            "https://example.com/rankings/2024/",
        )
        self.assertEqual(title, "Directory")
        self.assertIn("Mathematics", text)
        self.assertEqual(
            links,
            [
                {"url": "https://example.com/subject/math", "text": "Mathematics"},
                {"url": "https://example.com/rankings/subject/physics", "text": "Physics"},
            ],
        )

    def test_direct_fetch_preserves_requested_member_identity(self) -> None:
        client = self.client()
        with patch.object(
            client,
            "_fetch_url",
            return_value={
                "status": "ok",
                "url": "https://example.com/final/",
                "title": "Final",
                "text": "1 | Alpha\n2 | Beta\n3 | Gamma",
                "links": [],
            },
        ):
            batches = client.fetch_urls(
                [
                    {
                        "url": "https://example.com/member",
                        "query": "directory-member:test",
                        "member_label": "Test Subject",
                    }
                ]
            )
        result = batches[0]["results"][0]
        self.assertEqual(result["url"], "https://example.com/final")
        self.assertEqual(result["requested_url"], "https://example.com/member")
        self.assertEqual(result["directory_member_label"], "Test Subject")

    def test_decode_web_text_uses_meta_charset_after_streaming(self) -> None:
        raw = '<meta charset="gbk"><p>中文正文</p>'.encode("gbk")
        self.assertIn("中文正文", decode_web_text(raw, "ISO-8859-1"))

    def test_private_and_embedded_credential_urls_are_rejected(self) -> None:
        self.assertEqual(_public_http_url("file:///etc/passwd"), (False, "unsupported_url"))
        self.assertEqual(_public_http_url("http://127.0.0.1/private"), (False, "private_address"))
        self.assertEqual(
            _public_http_url("https://user:password@example.com/private"),
            (False, "embedded_credentials"),
        )

    def test_redirect_is_revalidated_before_second_request(self) -> None:
        response = Mock()
        response.status_code = 302
        response.headers = {"Location": "http://127.0.0.1/private"}
        response.close = Mock()
        session = Mock()
        session.get.return_value = response
        client = self.client()
        client._thread_local.session = session
        with patch(
            "deepwide_agent.native_search._public_http_url",
            side_effect=[(True, "ok"), (False, "private_address")],
        ):
            result = client._fetch_url("https://example.com/start")
        self.assertEqual(result["status"], "private_address")
        self.assertEqual(session.get.call_count, 1)

    def test_fetch_preserves_trailing_slash_needed_by_origin(self) -> None:
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.encoding = "utf-8"
        response.iter_content.return_value = [b"<html><body>page body</body></html>"]
        response.close = Mock()
        session = Mock()
        session.get.return_value = response
        client = self.client()
        client._thread_local.session = session
        with patch(
            "deepwide_agent.native_search._public_http_url",
            return_value=(True, "ok"),
        ):
            result = client._fetch_url("https://example.com/about/")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            session.get.call_args.args[0],
            "https://example.com/about/",
        )

    def test_page_enrichment_uses_exact_fetch_url_but_stores_canonical_url(self) -> None:
        client = self.client()
        client.fetch_pages = True
        batches = [
            {
                "query": "q",
                "results": [
                    {
                        "url": "https://example.com/about",
                        "fetch_url": "https://example.com/about/",
                        "raw_content": "",
                    }
                ],
            }
        ]
        with patch.object(
            client,
            "_fetch_url",
            return_value={
                "status": "ok",
                "url": "https://example.com/about/",
                "title": "About",
                "text": "page body",
            },
        ) as fetch:
            client._enrich_pages(batches)

        fetch.assert_called_once_with("https://example.com/about/")
        result = batches[0]["results"][0]
        self.assertEqual(result["url"], "https://example.com/about")
        self.assertEqual(result["raw_content"], "page body")

    def test_request_requires_web_search_and_complete_sources(self) -> None:
        response = Mock()
        response.status_code = 200
        response.json.return_value = payload_for(
            [("fact", "https://a.example/page", "Alpha")]
        )
        response.raise_for_status = Mock()
        session = Mock()
        session.post.return_value = response
        client = self.client(max_retries=1)
        client._thread_local.session = session
        client._request(["query"])
        body = session.post.call_args.kwargs["json"]
        self.assertEqual(body["tools"], [{"type": "web_search", "search_context_size": "medium"}])
        self.assertEqual(body["tool_choice"], "required")
        self.assertEqual(body["include"], ["web_search_call.action.sources"])
        self.assertEqual(client.total_tokens, 30)
        self.assertEqual(client.tool_calls, 1)


if __name__ == "__main__":
    unittest.main()
