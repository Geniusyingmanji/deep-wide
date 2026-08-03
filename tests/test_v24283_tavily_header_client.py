from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from deepwide_agent.v24283_tavily_header_client import (
    ENDPOINT,
    TavilyHeaderClient,
)


def response(status: int, payload: dict | None = None) -> Mock:
    value = Mock()
    value.status_code = status
    value.json.return_value = payload or {}
    value.raise_for_status.return_value = None
    return value


class V24283TavilyHeaderClientTests(unittest.TestCase):
    def test_credentials_are_header_only_and_transport_is_hardened(self) -> None:
        post = Mock(
            return_value=response(
                200,
                {
                    "results": [
                        {
                            "title": "A",
                            "url": "https://a.example/page",
                            "content": "snippet",
                        }
                    ]
                },
            )
        )
        client = TavilyHeaderClient(["secret-one"], max_workers=1, post=post)
        result = client.search("query", max_results=3)
        self.assertEqual(result["results"][0]["url"], "https://a.example/page")
        kwargs = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0], ENDPOINT)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret-one")
        self.assertNotIn("secret-one", kwargs["data"])
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(kwargs["verify"])
        self.assertFalse(json.loads(kwargs["data"])["include_answer"])

    def test_quota_key_is_disabled_and_error_never_contains_credentials(self) -> None:
        post = Mock(side_effect=[response(432), response(401)])
        client = TavilyHeaderClient(
            ["secret-one", "secret-two"], max_workers=1, post=post
        )
        with self.assertRaises(Exception) as caught:
            client.search("query", max_results=3)
        message = str(caught.exception)
        self.assertNotIn("secret-one", message)
        self.assertNotIn("secret-two", message)
        self.assertIn("disabled_keys=2/2", message)

    def test_search_many_returns_safe_failure_without_provider_or_key_text(self) -> None:
        post = Mock(return_value=response(500))
        client = TavilyHeaderClient(["secret-one"], max_workers=2, post=post)
        rows = client.search_many(["one", "two"], max_results=3)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["error"] == "direct search request failed" for row in rows))
        encoded = json.dumps(rows)
        self.assertNotIn("secret-one", encoded)

    def test_direct_credential_echo_is_rejected_before_value_return(self) -> None:
        post = Mock(
            return_value=response(
                200,
                {"answer": "secret-one", "results": []},
            )
        )
        client = TavilyHeaderClient(["secret-one"], max_workers=1, post=post)
        with self.assertRaisesRegex(Exception, "echoed"):
            client.search("query", max_results=3)


if __name__ == "__main__":
    unittest.main()
