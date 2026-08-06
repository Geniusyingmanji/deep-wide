#!/usr/bin/env python3
"""Credential-free GET helper for the sealed V2.47.23 fresh targets."""

from __future__ import annotations

import base64
import ctypes
import json
import os
import signal
import sys
from collections.abc import Mapping
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as runtime  # noqa: E402


MAX_STDIN_BYTES = 16_384
ALLOWED_URLS = frozenset(
    runtime.endpoint_url(target, representation)
    for target in runtime.TARGETS
    for representation in runtime.REPRESENTATIONS
)
INPUT_KEYS = frozenset({"url", "socket_timeout_seconds"})
OUTPUT_KEYS = frozenset(
    {"kind", "status_code", "content_type", "final_url", "body_base64"}
)


def _bind_parent() -> None:
    expected = os.environ.get("DEEPWIDE_EXPECTED_PARENT_PID", "")
    if not expected.isdigit() or int(expected) <= 1:
        raise ValueError("parent PID absent")
    parent = int(expected)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL) != 0:
        raise OSError(ctypes.get_errno(), "prctl failed")
    if os.getppid() != parent:
        raise RuntimeError("parent exited")


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
        raise AssertionError("V2.47.25 output drifted")
    return value


def main() -> None:
    try:
        _bind_parent()
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
        value = json.loads(raw.decode("utf-8"))
        if len(raw) > MAX_STDIN_BYTES or not isinstance(value, Mapping) or set(value) != INPUT_KEYS:
            raise ValueError("input drifted")
        url = value.get("url")
        timeout = value.get("socket_timeout_seconds")
        if (
            not isinstance(url, str)
            or url not in ALLOWED_URLS
            or isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0 < float(timeout) <= 120
        ):
            raise ValueError("URL or timeout drifted")
        with requests.get(
            url,
            headers={"User-Agent": "deepwide-v24725-fresh-transport/1"},
            timeout=float(timeout),
            stream=True,
            allow_redirects=False,
        ) as response:
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > runtime.MAX_RESPONSE_BYTES:
                    print(json.dumps(_output("response_too_large"), separators=(",", ":")))
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
