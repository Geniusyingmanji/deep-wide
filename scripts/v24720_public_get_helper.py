#!/usr/bin/env python3
"""One-shot credential-free GET helper supervised by a hard parent wall.

The response body is returned only through stdout to the parent process.  The
helper writes no file, follows no redirect, and accepts only the exact frozen
World Bank endpoint vector from V2.47.19.
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import signal
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24719_worldbank_transport_reliability import (  # noqa: E402
    MAX_RESPONSE_BYTES,
    REPRESENTATIONS,
    TARGETS,
    endpoint_url,
)


MAX_STDIN_BYTES = 16_384
INPUT_KEYS = frozenset({"url", "socket_timeout_seconds"})
OUTPUT_KEYS = frozenset(
    {"kind", "status_code", "content_type", "final_url", "body_base64"}
)
ALLOWED_URLS = frozenset(
    endpoint_url(target, representation)
    for target in TARGETS
    for representation in REPRESENTATIONS
)


def _bind_parent_lifetime() -> None:
    expected = os.environ.get("DEEPWIDE_EXPECTED_PARENT_PID", "")
    if not expected.isdigit() or int(expected) <= 1:
        raise ValueError("expected parent PID is absent")
    parent = int(expected)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL) != 0:  # PR_SET_PDEATHSIG
        raise OSError(ctypes.get_errno(), "prctl failed")
    if os.getppid() != parent:
        raise RuntimeError("parent exited before helper initialization")


def _input() -> dict[str, object]:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        raise ValueError("request envelope is too large")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or set(value) != INPUT_KEYS:
        raise ValueError("request envelope drifted")
    url = value.get("url")
    timeout = value.get("socket_timeout_seconds")
    if (
        not isinstance(url, str)
        or url not in ALLOWED_URLS
        or isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0 < float(timeout) <= 120
    ):
        raise ValueError("request URL or timeout is invalid")
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("credential or fragment is forbidden")
    return {"url": url, "socket_timeout_seconds": float(timeout)}


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
        raise AssertionError("helper output drifted")
    return value


def main() -> None:
    try:
        _bind_parent_lifetime()
        value = _input()
        with requests.get(
            str(value["url"]),
            headers={"User-Agent": "deepwide-v24720-transport-gate/1"},
            timeout=float(value["socket_timeout_seconds"]),
            stream=True,
            allow_redirects=False,
        ) as response:
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    print(json.dumps(_output("response_too_large"), separators=(",", ":")))
                    return
                chunks.append(chunk)
            body = b"".join(chunks)
            print(
                json.dumps(
                    _output(
                        "response",
                        status_code=int(response.status_code),
                        content_type=str(response.headers.get("Content-Type", "")),
                        final_url=str(response.url),
                        body=body,
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
