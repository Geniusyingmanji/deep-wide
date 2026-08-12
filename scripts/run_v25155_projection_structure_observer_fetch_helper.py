#!/usr/bin/env python3
"""Fetch, project, and emit one content-free three-layer structure receipt."""

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
from deepwide_agent.v24984_robust_late_page_projection import (  # noqa: E402
    MAXIMUM_INPUT_PAGE_CHARACTERS,
    build_projection,
)
from deepwide_agent.v25155_projection_structure_observer import (  # noqa: E402
    finalize_observation,
    observe_preprojection,
)
from deepwide_agent.v25155_projection_structure_observer_fetch import (  # noqa: E402
    validate_helper_result,
)


MAXIMUM_STDIN_CHARACTERS = 300_000
MAXIMUM_QUESTION_CHARACTERS = 250_000
MAXIMUM_URL_CHARACTERS = 8_192
MAXIMUM_LINKS = 256
MAXIMUM_LINK_TEXT_CHARACTERS = 1_000


def main() -> None:
    value = json.loads(sys.stdin.read(MAXIMUM_STDIN_CHARACTERS))
    if not isinstance(value, dict) or set(value) != {"url", "question"}:
        raise ValueError("V2.51.55 helper input schema drifted")
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
        raise ValueError("V2.51.55 helper visible input drifted")
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
        content_free_structure_observer=observe_preprojection,
    )
    result = client._fetch_url(url)
    preprojection = result.pop("content_free_structure_receipt", None)
    projection_receipt = None
    structure_observation = None
    parent_prefix = None
    if result.get("status") == "ok":
        if not isinstance(preprojection, dict):
            raise RuntimeError("V2.51.55 successful fetch omitted preprojection receipt")
        extracted = str(result.get("text") or "")
        parent_prefix = extracted[:5_000]
        projection = build_projection(
            question,
            {
                "title": str(result.get("title") or ""),
                "url": str(result.get("url") or url),
                "text": extracted,
            },
        )
        result["text"] = str(projection["projection"])
        projection_receipt = projection["content_free_receipt"]
        structure_observation = finalize_observation(
            preprojection, result["text"]
        )
    output = {
        "status": str(result.get("status") or "invalid_result"),
        "url": str(result.get("url") or "")[:MAXIMUM_URL_CHARACTERS],
        "title": str(result.get("title") or "")[:2_000],
        "text": str(result.get("text") or ""),
        "links": [
            {
                "url": str(item.get("url") or "")[:MAXIMUM_URL_CHARACTERS],
                "text": str(item.get("text") or "")[
                    :MAXIMUM_LINK_TEXT_CHARACTERS
                ],
            }
            for item in (result.get("links") or [])[:MAXIMUM_LINKS]
            if isinstance(item, dict)
        ],
        "projection_receipt": projection_receipt,
        "parent_prefix": parent_prefix,
        "structure_observation": structure_observation,
    }
    print(json.dumps(validate_helper_result(output), ensure_ascii=False))


if __name__ == "__main__":
    main()
