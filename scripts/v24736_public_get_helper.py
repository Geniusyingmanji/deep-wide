#!/usr/bin/env python3
"""Credential-free bounded GET helper for V2.47.35 visible targets."""

from __future__ import annotations

import base64
import ctypes
import json
import math
import os
import signal
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as wb  # noqa: E402
from deepwide_agent.v24648_unknown_target_structured_runtime import exact_lookup_url  # noqa: E402
from deepwide_agent.v24733_dual_namespace_contract import ROR_ENTITY_GROUPS  # noqa: E402


MAX_STDIN_BYTES = 16_384
MAX_RESPONSE_BYTES = 4_000_000
INPUT_KEYS = frozenset({"url", "socket_timeout_seconds"})
OUTPUT_KEYS = frozenset(
    {"kind", "status_code", "content_type", "final_url", "body_base64"}
)
ROR_URLS = frozenset(
    exact_lookup_url(entity) for group in ROR_ENTITY_GROUPS for entity in group
)
WORLD_BANK_URLS = frozenset(
    wb.endpoint_url(target, wb.PRIMARY_REPRESENTATION) for target in wb.TARGETS
)
ALLOWED_URLS = ROR_URLS | WORLD_BANK_URLS


def _bind_parent() -> None:
    expected = os.environ.get("DEEPWIDE_EXPECTED_PARENT_PID", "")
    if not expected.isdigit() or int(expected) <= 1:
        raise ValueError("V2.47.36 parent PID absent")
    parent = int(expected)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL) != 0:
        raise OSError(ctypes.get_errno(), "V2.47.36 prctl failed")
    if os.getppid() != parent:
        raise RuntimeError("V2.47.36 parent exited")


def _validate_url(url: str) -> None:
    if url not in ALLOWED_URLS:
        raise ValueError("V2.47.36 URL is outside exact allowlist")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("V2.47.36 URL authority drifted")
    if url in ROR_URLS:
        if (
            parsed.hostname != "api.ror.org"
            or parsed.path.rstrip("/") != "/v2/organizations"
            or dict(parse_qsl(parsed.query)).get("filter") != "status:active"
        ):
            raise ValueError("V2.47.36 ROR URL drifted")
    elif (
        parsed.hostname != wb.WORLD_BANK_HOST
        or parsed.query != "downloadformat=csv"
    ):
        raise ValueError("V2.47.36 World Bank URL drifted")


def _output(
    kind: str,
    *,
    status_code: int | None = None,
    content_type: str = "",
    final_url: str = "",
    body: bytes = b"",
) -> dict[str, object]:
    value = {
        "kind": kind,
        "status_code": status_code,
        "content_type": content_type[:256],
        "final_url": final_url[:8192],
        "body_base64": base64.b64encode(body).decode("ascii") if body else "",
    }
    if set(value) != OUTPUT_KEYS:
        raise AssertionError("V2.47.36 output drifted")
    return value


def main() -> None:
    try:
        _bind_parent()
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
        value = json.loads(raw.decode("utf-8"))
        if (
            len(raw) > MAX_STDIN_BYTES
            or not isinstance(value, Mapping)
            or set(value) != INPUT_KEYS
        ):
            raise ValueError("V2.47.36 input drifted")
        url = value.get("url")
        timeout = value.get("socket_timeout_seconds")
        if (
            not isinstance(url, str)
            or isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(float(timeout))
            or not 0 < float(timeout) <= 120
        ):
            raise ValueError("V2.47.36 URL or timeout drifted")
        _validate_url(url)
        with requests.get(
            url,
            headers={"User-Agent": "deepwide-v24736-reachability/1"},
            timeout=float(timeout),
            stream=True,
            allow_redirects=False,
        ) as response:
            chunks = []
            size = 0
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    print(
                        json.dumps(
                            _output("response_too_large"), separators=(",", ":")
                        )
                    )
                    return
                chunks.append(chunk)
            print(
                json.dumps(
                    _output(
                        "response",
                        status_code=int(response.status_code),
                        content_type=str(response.headers.get("Content-Type", "")),
                        final_url=str(response.url),
                        body=b"".join(chunks),
                    ),
                    separators=(",", ":"),
                )
            )
    except (requests.ConnectionError, requests.Timeout, OSError):
        print(json.dumps(_output("transport_error"), separators=(",", ":")))
    except (RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        print(json.dumps(_output("invalid_input"), separators=(",", ":")))


if __name__ == "__main__":
    main()
