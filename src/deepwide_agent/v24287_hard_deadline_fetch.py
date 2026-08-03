"""Hard one-process wall deadline for each V2.42.87 public-page fetch."""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .native_search import AzureNativeSearchClient
from .v24287_forward_contract import FETCH_HELPER_MARKER, SEARCH


FETCH_RESULT_KEYS = frozenset({"status", "url", "title", "text", "links"})
TRANSPORT_HEALTH_KEYS = frozenset(
    {"hard_fetch_helper_calls", "hard_fetch_deadline_failures", "fetch_helper_failures"}
)


def _failure(status: str) -> dict[str, Any]:
    return {"status": status, "url": "", "title": "", "text": "", "links": []}


def validate_fetch_result(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("V2.42.87 fetch helper result is not an object")
    copied = dict(value)
    copied.setdefault("links", [])
    if (
        set(copied) != FETCH_RESULT_KEYS
        or not isinstance(copied.get("status"), str)
        or not copied["status"]
        or not isinstance(copied.get("url"), str)
        or not isinstance(copied.get("title"), str)
        or not isinstance(copied.get("text"), str)
        or not isinstance(copied.get("links"), list)
        or len(copied["url"]) > 8_192
        or len(copied["title"]) > 2_000
        or len(copied["text"]) > 5_000
        or len(copied["links"]) > 256
        or any(
            not isinstance(item, dict)
            or set(item) != {"url", "text"}
            or not isinstance(item.get("url"), str)
            or not isinstance(item.get("text"), str)
            or len(item["url"]) > 8_192
            or len(item["text"]) > 1_000
            for item in copied["links"]
        )
    ):
        raise ValueError("V2.42.87 fetch helper result schema drifted")
    return copied


def validate_transport_health(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != TRANSPORT_HEALTH_KEYS:
        raise ValueError("V2.42.87 transport health schema drifted")
    copied = {name: value[name] for name in TRANSPORT_HEALTH_KEYS}
    if (
        any(isinstance(number, bool) or not isinstance(number, int) or number < 0 for number in copied.values())
        or copied["hard_fetch_deadline_failures"] + copied["fetch_helper_failures"]
        > copied["hard_fetch_helper_calls"]
    ):
        raise ValueError("V2.42.87 transport health counter drifted")
    return copied


class HardDeadlineNativeSearchClient(AzureNativeSearchClient):
    def __init__(
        self,
        *args: Any,
        hard_fetch_deadline_seconds: float,
        helper_path: Path | None = None,
        python_executable: str | None = None,
        popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        deadline = float(hard_fetch_deadline_seconds)
        if (
            not math.isfinite(deadline)
            or deadline <= 0
            or deadline != float(SEARCH["hard_fetch_deadline_seconds"])
        ):
            raise ValueError("V2.42.87 hard fetch deadline drifted")
        root = Path(__file__).resolve().parents[2]
        helper = (helper_path or root / FETCH_HELPER_MARKER).resolve()
        if (
            helper.is_symlink()
            or not helper.is_file()
            or helper != (root / FETCH_HELPER_MARKER).resolve()
            or not helper.is_relative_to(root)
        ):
            raise ValueError("V2.42.87 fetch helper identity drifted")
        executable = python_executable or sys.executable
        if not executable or not Path(executable).is_file():
            raise ValueError("V2.42.87 helper Python is unavailable")
        self.hard_fetch_deadline_seconds = deadline
        self.fetch_helper_path = helper
        self.fetch_python_executable = executable
        self._fetch_popen = popen
        self.hard_fetch_helper_calls = 0
        self.hard_fetch_deadline_failures = 0
        self.fetch_helper_failures = 0

    @staticmethod
    def _terminate_group(process: Any) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=1)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.wait(timeout=1)

    def _fetch_url(self, url: str) -> dict[str, Any]:
        self._increment("fetch_calls")
        self._increment("hard_fetch_helper_calls")
        process = self._fetch_popen(
            [self.fetch_python_executable, "-I", "-B", str(self.fetch_helper_path)],
            cwd=self.fetch_helper_path.parents[1],
            env={
                "HOME": os.environ.get("HOME", str(Path.home())),
                "USER": os.environ.get("USER", "azureuser"),
                "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )
        try:
            stdout, _ = process.communicate(
                json.dumps({"url": str(url)}, ensure_ascii=False),
                timeout=self.hard_fetch_deadline_seconds,
            )
        except subprocess.TimeoutExpired:
            self._terminate_group(process)
            self._increment("fetch_failures")
            self._increment("hard_fetch_deadline_failures")
            return _failure("hard_deadline_exceeded")
        if process.returncode != 0:
            self._increment("fetch_failures")
            self._increment("fetch_helper_failures")
            return _failure("helper_nonzero_exit")
        try:
            result = validate_fetch_result(json.loads(stdout))
        except (json.JSONDecodeError, TypeError, ValueError):
            self._increment("fetch_failures")
            self._increment("fetch_helper_failures")
            return _failure("helper_invalid_result")
        if result["status"] != "ok":
            self._increment("fetch_failures")
        return result


__all__ = [
    "HardDeadlineNativeSearchClient",
    "validate_fetch_result",
    "validate_transport_health",
]
