#!/usr/bin/env python3
"""One-attempt credential-free GET helper for the V2.52.97 population freeze.

The helper accepts only the single frozen World Bank source-2 catalog URL or
an exact 2022 two-page indicator URL.  It follows no redirects, disables
environment-derived requests state, retains at most the caller-declared fixed
cap, and binds its lifetime to the supervising parent.
"""

from __future__ import annotations

import base64
import ctypes
import ipaddress
import json
import os
import signal
import socket
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25295_worldbank_monotone_fill_gate as runtime  # noqa: E402


CATALOG_URL = (
    "https://api.worldbank.org/v2/source/2/indicator"
    "?format=json&page=1&per_page=50000"
)
CATALOG_MAXIMUM_BYTES = 32 * 1024 * 1024
TARGET_MAXIMUM_BYTES = 2 * 1024 * 1024
MAXIMUM_STDIN_BYTES = 16_384
INPUT_KEYS = frozenset({"url", "socket_timeout_seconds", "maximum_response_bytes"})
OUTPUT_KEYS = frozenset(
    {
        "kind",
        "provider_attempt_count",
        "status_code",
        "content_type",
        "final_url",
        "body_base64",
    }
)


def _target_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return False
    parts = parsed.path.strip("/").split("/")
    return bool(
        parsed.scheme == "https"
        and (parsed.hostname or "").casefold() == "api.worldbank.org"
        and parsed.port is None
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
        and len(parts) == 5
        and parts[:4] == ["v2", "country", "all", "indicator"]
        and runtime.INDICATOR.fullmatch(parts[4]) is not None
        and pairs
        in (
            [
                ("date", runtime.TARGET_YEAR),
                ("format", "json"),
                ("page", "1"),
                ("per_page", str(runtime.WORLD_BANK_PER_PAGE)),
            ],
            [
                ("date", runtime.TARGET_YEAR),
                ("format", "json"),
                ("page", "2"),
                ("per_page", str(runtime.WORLD_BANK_PER_PAGE)),
            ],
        )
    )


def _url_kind(url: object, maximum_response_bytes: object) -> str | None:
    if not isinstance(url, str) or isinstance(maximum_response_bytes, bool):
        return None
    if url == CATALOG_URL and maximum_response_bytes == CATALOG_MAXIMUM_BYTES:
        return "catalog"
    if _target_url(url) and maximum_response_bytes == TARGET_MAXIMUM_BYTES:
        return "target"
    return None


def _bind_parent() -> None:
    expected = os.environ.get("DEEPWIDE_EXPECTED_PARENT_PID", "")
    if not expected.isdigit() or int(expected) <= 1:
        raise ValueError("parent PID absent")
    parent = int(expected)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL) != 0:  # PR_SET_PDEATHSIG
        raise OSError(ctypes.get_errno(), "prctl failed")
    if os.getppid() != parent:
        raise RuntimeError("parent exited")


def _public_dns(hostname: str) -> bool:
    rows = socket.getaddrinfo(
        hostname,
        443,
        family=socket.AF_UNSPEC,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    addresses = {str(row[4][0]).split("%", 1)[0] for row in rows}
    return bool(addresses) and all(ipaddress.ip_address(value).is_global for value in addresses)


def _output(
    kind: str,
    *,
    provider_attempt_count: int = 0,
    status_code: int | None = None,
    content_type: str = "",
    final_url: str = "",
    body: bytes = b"",
) -> dict[str, object]:
    value = {
        "kind": kind,
        "provider_attempt_count": provider_attempt_count,
        "status_code": status_code,
        "content_type": content_type[:256],
        "final_url": final_url[:8192],
        "body_base64": base64.b64encode(body).decode("ascii") if body else "",
    }
    if set(value) != OUTPUT_KEYS:
        raise AssertionError("V2.52.97 helper output drifted")
    return value


def main() -> None:
    attempted = 0
    try:
        _bind_parent()
        raw = sys.stdin.buffer.read(MAXIMUM_STDIN_BYTES + 1)
        if len(raw) > MAXIMUM_STDIN_BYTES:
            raise ValueError("input too large")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, Mapping) or set(value) != INPUT_KEYS:
            raise ValueError("input drifted")
        url = value.get("url")
        timeout = value.get("socket_timeout_seconds")
        maximum = value.get("maximum_response_bytes")
        if (
            _url_kind(url, maximum) is None
            or isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0 < float(timeout) <= 30
            or not _public_dns("api.worldbank.org")
        ):
            raise ValueError("request authority drifted")
        session = requests.Session()
        session.trust_env = False
        attempted = 1
        with session.get(
            str(url),
            headers={
                "Accept": "application/json",
                "User-Agent": "DeepWideResearch/2.52.97 (one-shot public population freeze)",
            },
            timeout=(5.0, float(timeout)),
            stream=True,
            allow_redirects=False,
        ) as response:
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > int(maximum):
                    print(
                        json.dumps(
                            _output("response_too_large", provider_attempt_count=attempted),
                            separators=(",", ":"),
                        )
                    )
                    return
                chunks.append(chunk)
            print(
                json.dumps(
                    _output(
                        "response",
                        provider_attempt_count=attempted,
                        status_code=int(response.status_code),
                        content_type=str(response.headers.get("Content-Type", "")),
                        final_url=str(response.url),
                        body=b"".join(chunks),
                    ),
                    separators=(",", ":"),
                )
            )
    except (requests.ConnectionError, requests.Timeout, OSError, socket.gaierror):
        print(
            json.dumps(
                _output("transport_error", provider_attempt_count=attempted),
                separators=(",", ":"),
            )
        )
    except (RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        print(
            json.dumps(
                _output("invalid_input", provider_attempt_count=attempted),
                separators=(",", ":"),
            )
        )


if __name__ == "__main__":
    main()
