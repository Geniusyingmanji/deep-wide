#!/usr/bin/env python3
"""Run the V2.49.75 shared raw-authority paired forward."""

from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import canonicalize_url  # noqa: E402
from deepwide_agent import v24974_raw_authority_compact_fields as compact  # noqa: E402
from deepwide_agent import v24975_raw_authority_quality_contract as contract  # noqa: E402
from scripts import run_v24973_identity_bound_field_quality as base  # noqa: E402


def _fetch_exact(
    url: str, *, kind: str, repository: str, deadline: float
) -> tuple[dict[str, str], int]:
    del repository
    remaining = deadline - time.monotonic() - 5.0
    if remaining <= 0:
        raise TimeoutError("V2.49.75 exact fetch deadline exhausted")
    with requests.get(
        url,
        headers={"User-Agent": "DeepWideResearch/1.0 (+raw-authority external gate)"},
        timeout=(min(contract.FETCH_TIMEOUT[0], remaining), min(contract.FETCH_TIMEOUT[1], remaining)),
        allow_redirects=False,
        stream=True,
    ) as response:
        status = int(response.status_code)
        response.raise_for_status()
        final = canonicalize_url(str(response.url))
        if final != canonicalize_url(url):
            raise ValueError("V2.49.75 exact public response address drifted")
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=1 << 20):
            if not chunk:
                continue
            size += len(chunk)
            if size > contract.MAX_RESPONSE_BYTES:
                raise ValueError("V2.49.75 exact public response exceeds hard cap")
            chunks.append(bytes(chunk))
        raw = b"".join(chunks)
        encoding = response.encoding or "utf-8"
    decoded = raw.decode(encoding, errors="replace")
    if kind == "pypi_json":
        value = json.loads(decoded)
        if not isinstance(value, Mapping) or not isinstance(value.get("info"), Mapping):
            raise ValueError("V2.49.75 PyPI JSON schema drifted")
    elif kind == "github_html":
        if "<title" not in decoded.casefold():
            raise ValueError("V2.49.75 GitHub HTML title is absent")
    else:
        raise ValueError("V2.49.75 exact fetch kind drifted")
    if not decoded:
        raise ValueError("V2.49.75 exact public response is empty")
    return {"url": final, "text": decoded}, status


def configure() -> None:
    contract.configure_parent()
    base.contract = contract
    base.compact = compact
    base._fetch_exact = _fetch_exact
    base._MODEL_SEMAPHORE = threading.BoundedSemaphore(contract.MODEL_CONCURRENCY)


def _raw_balanced_evidence(pages: Any) -> str:
    configure()
    return base._raw_balanced_evidence(pages)


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return base.validate_task_row(value)


def aggregate(rows: Any) -> dict[str, Any]:
    configure()
    return base.aggregate(rows)


def mechanism_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return base.mechanism_decision(value)


def run_forward() -> dict[str, Any]:
    configure()
    return base.run_forward()


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "role": value["role"],
                "wall_seconds": value["wall_seconds"],
                "aggregate": value["aggregate"],
                "mechanism_decision": value["mechanism_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
