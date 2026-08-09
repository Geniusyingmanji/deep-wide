#!/usr/bin/env python3
"""Fetch and project one identity-bound public detail page under hard limits."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24287_forward_contract import SEARCH  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import validate_helper_result  # noqa: E402
from deepwide_agent.v25004_identity_bound_detail_fields import (  # noqa: E402
    MAXIMUM_INPUT_PAGE_CHARACTERS,
    build_projection,
)


MAXIMUM_STDIN_CHARACTERS = 300_000
MAXIMUM_QUESTION_CHARACTERS = 250_000
MAXIMUM_URL_CHARACTERS = 8_192
MAXIMUM_LINKS = 256
MAXIMUM_LINK_TEXT_CHARACTERS = 1_000


def main() -> None:
    value = json.loads(sys.stdin.read(MAXIMUM_STDIN_CHARACTERS))
    if not isinstance(value, dict) or set(value) != {"url", "question"}:
        raise ValueError("V2.50.05 helper input schema drifted")
    url = value.get("url")
    question = value.get("question")
    if (
        not isinstance(url, str)
        or not url.strip()
        or len(url) > MAXIMUM_URL_CHARACTERS
        or not isinstance(question, str)
        or not question.strip()
        or len(question) > MAXIMUM_QUESTION_CHARACTERS
        or "\x00" in question
    ):
        raise ValueError("V2.50.05 helper visible input drifted")
    client = AzureNativeSearchClient(
        SEARCH["proxy_url"],
        SEARCH["model"],
        reasoning_effort="low",
        timeout=SEARCH["timeout_seconds"],
        max_retries=1,
        max_workers=1,
        batch_size=1,
        search_context_size=SEARCH["context_size"],
        max_output_tokens=SEARCH["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=SEARCH["fetch_timeout_seconds"],
        max_page_bytes=MAXIMUM_INPUT_PAGE_CHARACTERS,
        max_page_chars=MAXIMUM_INPUT_PAGE_CHARACTERS,
    )
    result = client._fetch_url(url)
    receipt = None
    parent_prefix = None
    if result.get("status") == "ok":
        parent_prefix = str(result.get("text") or "")[:5_000]
        projection = build_projection(
            question,
            {
                "title": str(result.get("title") or ""),
                "url": str(result.get("url") or url),
                "text": str(result.get("text") or ""),
            },
        )
        result["text"] = str(projection["projection"])
        # Preserve V2.49.81's frozen helper schema and aggregate receipt.  The
        # V2.50.04 detail receipt remains reproducibly bound inside the pure
        # projection artifact tests and is not persisted by this effect seam.
        receipt = projection["content_free_receipt"]
    output = {
        "status": str(result.get("status") or "invalid_result"),
        "url": str(result.get("url") or "")[:MAXIMUM_URL_CHARACTERS],
        "title": str(result.get("title") or "")[:2_000],
        "text": str(result.get("text") or ""),
        "links": [
            {
                "url": str(item.get("url") or "")[:MAXIMUM_URL_CHARACTERS],
                "text": str(item.get("text") or "")[:MAXIMUM_LINK_TEXT_CHARACTERS],
            }
            for item in (result.get("links") or [])[:MAXIMUM_LINKS]
            if isinstance(item, dict)
        ],
        "projection_receipt": receipt,
        "parent_prefix": parent_prefix,
    }
    print(json.dumps(validate_helper_result(output), ensure_ascii=False))


if __name__ == "__main__":
    main()
