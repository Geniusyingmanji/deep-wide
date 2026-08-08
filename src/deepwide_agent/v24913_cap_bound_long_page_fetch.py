"""Cap-bound 12k public-page fetch bridge for the V2.49.13 successor.

The historical helper is intentionally frozen at 5,000 characters.  This
module creates a separate helper/validator namespace whose input and output
caps are both fixed at 12,000 characters.  It changes neither hosted search
nor fetch counts.  The fetched page remains untrusted same-forward data.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)


POLICY_ID = "v24913_cap_bound_12000_character_fetch_v1"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/run_v24913_long_page_fetch_helper.py"
PAGE_CHARACTER_CAP = 12_000
MAXIMUM_LINKS = 256
MAXIMUM_URL_CHARACTERS = 8_192
MAXIMUM_TITLE_CHARACTERS = 2_000
MAXIMUM_LINK_TEXT_CHARACTERS = 1_000
FETCH_RESULT_KEYS = frozenset({"status", "url", "title", "text", "links"})


def _ordinary_helper(path: Path = HELPER) -> Path:
    expected = (ROOT / "scripts/run_v24913_long_page_fetch_helper.py").resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != expected
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.49.13 fetch helper identity drifted")
    return resolved


def validate_fetch_result(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.49.13 fetch helper result is not an object")
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
        or len(copied["url"]) > MAXIMUM_URL_CHARACTERS
        or len(copied["title"]) > MAXIMUM_TITLE_CHARACTERS
        or len(copied["text"]) > PAGE_CHARACTER_CAP
        or len(copied["links"]) > MAXIMUM_LINKS
        or any(
            not isinstance(item, Mapping)
            or set(item) != {"url", "text"}
            or not isinstance(item.get("url"), str)
            or not isinstance(item.get("text"), str)
            or len(item["url"]) > MAXIMUM_URL_CHARACTERS
            or len(item["text"]) > MAXIMUM_LINK_TEXT_CHARACTERS
            for item in copied["links"]
        )
    ):
        raise ValueError("V2.49.13 fetch helper result schema drifted")
    return copied


def _failure(status: str) -> dict[str, Any]:
    return {"status": status, "url": "", "title": "", "text": "", "links": []}


class CapBoundLongPageFetchMixin:
    """Replace only the inherited 5k helper boundary with a frozen 12k one."""

    def __init__(
        self,
        *args: Any,
        long_page_fetch_helper: Path = HELPER,
        long_page_fetch_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if (
            isinstance(self.max_page_chars, bool)
            or int(self.max_page_chars) != PAGE_CHARACTER_CAP
        ):
            raise ValueError("V2.49.13 transport page cap drifted")
        self.cap_bound_fetch_helper_path = _ordinary_helper(long_page_fetch_helper)
        self._cap_bound_fetch_popen = long_page_fetch_popen

    def _fetch_url(self, url: str) -> dict[str, Any]:
        self._stage_callback("public_fetch_effect_started")
        try:
            return self._fetch_url_cap_bound(url)
        finally:
            self._stage_callback("public_fetch_effect_finished")

    def _fetch_url_cap_bound(self, url: str) -> dict[str, Any]:
        self._increment("fetch_calls")
        remaining = self.remaining_effect_seconds()
        if remaining < self.minimum_attempt_seconds:
            self._increment("fetch_failures")
            self._increment("fetch_deadline_rejections")
            return _failure("task_deadline_exhausted")
        self._increment("hard_fetch_helper_calls")
        process = self._cap_bound_fetch_popen(
            [
                self.fetch_python_executable,
                "-I",
                "-B",
                str(self.cap_bound_fetch_helper_path),
            ],
            cwd=self.cap_bound_fetch_helper_path.parents[1],
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
        remaining_after_launch = self.remaining_effect_seconds()
        if remaining_after_launch < self.minimum_attempt_seconds:
            self._terminate_group(process)
            self._increment("fetch_failures")
            self._increment("hard_fetch_deadline_failures")
            return _failure("task_deadline_exhausted_after_helper_launch")
        try:
            stdout, _ = process.communicate(
                json.dumps({"url": str(url)}, ensure_ascii=False),
                timeout=min(
                    float(self.hard_fetch_deadline_seconds),
                    remaining_after_launch,
                ),
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


class CapBoundLongPageSearchClient(
    CapBoundLongPageFetchMixin,
    ThinSameResponseCitationTitleBackfillSearchClient,
):
    """Frozen hosted-search client with only the public-page cap replaced."""


def validate_search_class() -> None:
    cls = CapBoundLongPageSearchClient
    fetch_owner = next(base for base in cls.__mro__ if "_fetch_url" in base.__dict__)
    if (
        fetch_owner is not CapBoundLongPageFetchMixin
        or not issubclass(cls, ThinSameResponseCitationTitleBackfillSearchClient)
    ):
        raise RuntimeError("V2.49.13 cap-bound search MRO drifted")


def validate_policy() -> dict[str, Any]:
    value = {
        "policy_id": POLICY_ID,
        "page_character_cap": PAGE_CHARACTER_CAP,
        "helper": str(HELPER.relative_to(ROOT)),
        "same_forward_public_page_text_only": True,
        "additional_search_fetch_or_model_call": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_read": False,
    }
    if (
        value["page_character_cap"] != 12_000
        or value["additional_search_fetch_or_model_call"] is not False
        or value[
            "benchmark_label_mapping_gold_evaluator_score_reward_read"
        ]
        is not False
    ):
        raise RuntimeError("V2.49.13 cap-bound fetch policy drifted")
    return value


__all__ = [
    "CapBoundLongPageFetchMixin",
    "CapBoundLongPageSearchClient",
    "HELPER",
    "PAGE_CHARACTER_CAP",
    "POLICY_ID",
    "validate_fetch_result",
    "validate_policy",
    "validate_search_class",
]
