#!/usr/bin/env python3
"""Fetch one strictly shaped World Bank JSON target with bounded retries."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24826_worldbank_exact_api_transport import (  # noqa: E402
    HELPER_ROLE,
    MAX_HELPER_ATTEMPTS,
    exact_target_key,
    payload_sha256,
    validate_helper_result,
)


ATTEMPT_CONNECT_TIMEOUT_SECONDS = 5.0
ATTEMPT_READ_TIMEOUT_SECONDS = 15.0
MAX_RESPONSE_BYTES = 1_048_576
BACKOFF_SECONDS = (0.25, 0.5)
RETRYABLE_STATUS = frozenset({408, 425, 429})


def _read_response(response: Any) -> bytes:
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=65_536):
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise ValueError("response_too_large")
        chunks.append(bytes(chunk))
    raw = b"".join(chunks)
    if not raw:
        raise ValueError("empty_body")
    return raw


def fetch_exact_json(
    url: str,
    *,
    session: Any | None = None,
    monotonic: Any = time.monotonic,
    sleeper: Any = time.sleep,
) -> dict[str, Any]:
    exact_target_key(url)
    client = session or requests.Session()
    attempts: list[dict[str, Any]] = []
    started = float(monotonic())
    terminal_raw = b""
    for attempt_index in range(1, MAX_HELPER_ATTEMPTS + 1):
        attempt_started = float(monotonic())
        status: int | None = None
        raw = b""
        error_type: str | None = None
        retryable = False
        response = None
        try:
            response = client.get(
                url,
                headers={"User-Agent": "deepwide-v24826/1"},
                timeout=(
                    ATTEMPT_CONNECT_TIMEOUT_SECONDS,
                    ATTEMPT_READ_TIMEOUT_SECONDS,
                ),
                allow_redirects=False,
                stream=True,
            )
            status = int(response.status_code)
            if status != 200:
                error_type = f"http_{status}"
                retryable = status in RETRYABLE_STATUS or 500 <= status <= 599
            else:
                content_type = str(response.headers.get("Content-Type", ""))
                media_type = content_type.split(";", 1)[0].strip().casefold()
                if media_type not in {"application/json", "text/json", ""}:
                    error_type = "invalid_content_type"
                else:
                    try:
                        raw = _read_response(response)
                        decoded = raw.decode("utf-8")
                        json.loads(decoded)
                    except UnicodeDecodeError:
                        error_type = "invalid_utf8"
                    except json.JSONDecodeError:
                        error_type = "invalid_json"
                    except ValueError as exc:
                        error_type = str(exc)
                    if error_type is None:
                        terminal_raw = raw
        except requests.Timeout:
            error_type = "timeout"
            retryable = True
        except requests.ConnectionError:
            error_type = "connection_error"
            retryable = True
        except requests.RequestException:
            error_type = "request_error"
            retryable = False
        finally:
            if response is not None:
                response.close()
        success = error_type is None and bool(terminal_raw)
        attempts.append(
            {
                "attempt": attempt_index,
                "outcome": "success" if success else "failure",
                "http_status": status,
                "error_type": None if success else str(error_type or "unknown_failure"),
                "retryable": False if success else bool(retryable),
                "elapsed_seconds": round(
                    max(0.0, float(monotonic()) - attempt_started), 6
                ),
                "response_bytes": len(terminal_raw) if success else len(raw),
                "response_sha256": (
                    hashlib.sha256(terminal_raw).hexdigest()
                    if success
                    else hashlib.sha256(raw).hexdigest()
                    if raw
                    else None
                ),
            }
        )
        if success or not retryable or attempt_index == MAX_HELPER_ATTEMPTS:
            break
        sleeper(BACKOFF_SECONDS[attempt_index - 1])
    success = bool(terminal_raw)
    value = {
        "artifact_version": 1,
        "role": HELPER_ROLE,
        "status": "ok" if success else "exhausted",
        "url": url,
        "raw_content": terminal_raw.decode("utf-8") if success else "",
        "attempt_count": len(attempts),
        "attempts": attempts,
        "elapsed_seconds": round(max(0.0, float(monotonic()) - started), 6),
        "response_bytes": len(terminal_raw),
        "response_sha256": (
            hashlib.sha256(terminal_raw).hexdigest() if success else None
        ),
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_helper_result(value)


def main() -> None:
    value = json.loads(sys.stdin.read(16_384))
    if not isinstance(value, dict) or set(value) != {"url"}:
        raise ValueError("V2.48.26 helper input schema drifted")
    url = value.get("url")
    if not isinstance(url, str) or len(url) > 8_192:
        raise ValueError("V2.48.26 helper URL drifted")
    print(json.dumps(fetch_exact_json(url), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
