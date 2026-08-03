#!/usr/bin/env python3
"""Fetch one public URL; the V2.42.87 parent enforces a hard wall deadline."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24287_forward_contract import LIMITS, SEARCH  # noqa: E402
from deepwide_agent.v24287_hard_deadline_fetch import validate_fetch_result  # noqa: E402


def main() -> None:
    value = json.loads(sys.stdin.read(16_384))
    if not isinstance(value, dict) or set(value) != {"url"}:
        raise ValueError("V2.42.87 helper input schema drifted")
    url = value.get("url")
    if not isinstance(url, str) or not url.strip() or len(url) > 8_192:
        raise ValueError("V2.42.87 helper URL is invalid")
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
        max_page_chars=LIMITS["page_chars"],
    )
    result = client._fetch_url(url)
    result["links"] = [
        {"url": str(item.get("url", ""))[:8_192], "text": str(item.get("text", ""))[:1_000]}
        for item in (result.get("links") or [])[:256]
        if isinstance(item, dict)
    ]
    print(json.dumps(validate_fetch_result(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
