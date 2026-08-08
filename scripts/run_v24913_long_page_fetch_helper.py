#!/usr/bin/env python3
"""Fetch one public URL with the frozen V2.49.13 12k page cap."""

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
from deepwide_agent.v24913_cap_bound_long_page_fetch import (  # noqa: E402
    MAXIMUM_LINKS,
    MAXIMUM_LINK_TEXT_CHARACTERS,
    MAXIMUM_URL_CHARACTERS,
    PAGE_CHARACTER_CAP,
    validate_fetch_result,
)


def main() -> None:
    value = json.loads(sys.stdin.read(16_384))
    if not isinstance(value, dict) or set(value) != {"url"}:
        raise ValueError("V2.49.13 helper input schema drifted")
    url = value.get("url")
    if (
        not isinstance(url, str)
        or not url.strip()
        or len(url) > MAXIMUM_URL_CHARACTERS
    ):
        raise ValueError("V2.49.13 helper URL is invalid")
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
        max_page_chars=PAGE_CHARACTER_CAP,
    )
    result = client._fetch_url(url)
    result["links"] = [
        {
            "url": str(item.get("url", ""))[:MAXIMUM_URL_CHARACTERS],
            "text": str(item.get("text", ""))[:MAXIMUM_LINK_TEXT_CHARACTERS],
        }
        for item in (result.get("links") or [])[:MAXIMUM_LINKS]
        if isinstance(item, dict)
    ]
    print(json.dumps(validate_fetch_result(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
