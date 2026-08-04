#!/usr/bin/env python3
"""One-shot loopback HTTP helper for V2.44.68 total-wall supervision.

The caller sends one request envelope over stdin and supervises this process
with a hard wall timeout.  Request and response content stay in anonymous
pipes; this helper writes no files and emits no exception or provider text.
"""

from __future__ import annotations

import ipaddress
import ctypes
import json
import os
import signal
import sys
from collections.abc import Mapping
from urllib.parse import urlsplit

import requests


MAX_STDIN_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
INPUT_KEYS = frozenset({"url", "body", "socket_timeout_seconds"})
OUTPUT_KEYS = frozenset(
    {"kind", "status_code", "retry_after", "payload", "payload_is_object"}
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


def _loopback_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 8_192:
        raise ValueError("invalid URL")
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("only credential-free loopback HTTP is allowed")
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
    except ValueError as error:
        raise ValueError("loopback address must be an IP literal") from error
    if not address.is_loopback or parsed.port is None:
        raise ValueError("non-loopback endpoint rejected")
    if parsed.fragment:
        raise ValueError("fragment rejected")
    return value


def _input() -> dict[str, object]:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        raise ValueError("request envelope too large")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, Mapping) or set(value) != INPUT_KEYS:
        raise ValueError("request envelope drifted")
    body = value.get("body")
    timeout = value.get("socket_timeout_seconds")
    if (
        not isinstance(body, Mapping)
        or isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0 < float(timeout) <= 300
    ):
        raise ValueError("request body or timeout invalid")
    return {
        "url": _loopback_url(value.get("url")),
        "body": dict(body),
        "socket_timeout_seconds": float(timeout),
    }


def _output(
    kind: str,
    *,
    status_code: int | None = None,
    retry_after: str = "",
    payload: object = None,
) -> dict[str, object]:
    value = {
        "kind": kind,
        "status_code": status_code,
        "retry_after": retry_after[:128],
        "payload": payload if isinstance(payload, Mapping) else None,
        "payload_is_object": isinstance(payload, Mapping),
    }
    if set(value) != OUTPUT_KEYS:
        raise AssertionError("helper output drifted")
    return value


def main() -> None:
    try:
        _bind_parent_lifetime()
        value = _input()
        with requests.post(
            str(value["url"]),
            headers={"Content-Type": "application/json"},
            json=value["body"],
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
            try:
                payload = json.loads(b"".join(chunks).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            print(
                json.dumps(
                    _output(
                        "response",
                        status_code=int(response.status_code),
                        retry_after=str(response.headers.get("Retry-After", "")),
                        payload=payload,
                    ),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
    except (requests.ConnectionError, requests.Timeout, OSError):
        print(json.dumps(_output("transport_error"), separators=(",", ":")))
    except (RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        print(json.dumps(_output("invalid_input_or_payload"), separators=(",", ":")))


if __name__ == "__main__":
    main()
