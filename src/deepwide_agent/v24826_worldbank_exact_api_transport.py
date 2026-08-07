"""Bounded, observable transport for visible-bound World Bank JSON lookups.

The historical page-fetch helper hides ordinary non-OK status classes and
executes all targets in a ``fetch_urls`` call concurrently.  V2.48.24 therefore
recorded 252/256 exact targets as missing without enough status information to
distinguish HTTP, transport, or extraction failures.

This append-only transport changes only exact World Bank JSON lookups:

* the caller binds the exact eight URLs generated from the visible task;
* any unbound World Bank exact URL is rejected before a network effect;
* exact targets execute sequentially within one task (task-level concurrency is
  unchanged);
* each target runs in a helper subprocess with a hard total wall, at most three
  provider attempts, no redirects, a response-size cap, and content-free status
  receipts;
* generic discovery-page fetches keep the inherited transport unchanged.

No benchmark label, gold, evaluator, score, reward, or credential is accepted.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from .v24696_worldbank_search_transport import (
    WorldBankHardTotalWallSearchClient,
)


POLICY_ID = "v24826_visible_bound_worldbank_exact_api_transport_v1"
HELPER_ROLE = "v24826_worldbank_exact_fetch_result"
RECEIPT_ROLE = "v24826_worldbank_exact_transport_receipt"
WORLD_BANK_HOST = "api.worldbank.org"
EXPECTED_TARGET_COUNT = 8
MAX_HELPER_ATTEMPTS = 3
EXACT_TARGET_TOTAL_WALL_SECONDS = 50.0
SHA256 = re.compile(r"[0-9a-f]{64}")
INDICATOR = re.compile(r"[A-Z][A-Z0-9.]{4,40}")
ISO3 = re.compile(r"[A-Z]{3}")
YEAR = re.compile(r"20[0-3][0-9]")


def payload_sha256(value: object) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def exact_target_key(url: object) -> str:
    """Validate one immutable exact API URL and return its visible target key."""

    try:
        parsed = urlsplit(str(url))
    except ValueError as exc:
        raise ValueError("V2.48.26 exact API URL is invalid") from exc
    parts = parsed.path.strip("/").split("/")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    parameters = dict(pairs)
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").casefold() != WORLD_BANK_HOST
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or len(parts) != 5
        or parts[0] != "v2"
        or parts[1] != "country"
        or parts[3] != "indicator"
        or ISO3.fullmatch(parts[2]) is None
        or INDICATOR.fullmatch(parts[4]) is None
        or pairs
        != [
            ("date", parameters.get("date", "")),
            ("format", "json"),
            ("per_page", "100"),
        ]
        or YEAR.fullmatch(parameters.get("date", "")) is None
    ):
        raise ValueError("V2.48.26 exact API URL is outside the fixed allowlist shape")
    return f"{parts[2]}|{parts[4]}|{parameters['date']}"


def _looks_like_exact_api_url(url: object) -> bool:
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return False
    return (
        (parsed.hostname or "").casefold() == WORLD_BANK_HOST
        and "/v2/country/" in parsed.path
        and "/indicator/" in parsed.path
    )


def validate_helper_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    attempts = copied.get("attempts")
    expected = {
        "artifact_version",
        "role",
        "status",
        "url",
        "raw_content",
        "attempt_count",
        "attempts",
        "elapsed_seconds",
        "response_bytes",
        "response_sha256",
        "result_payload_sha256",
    }
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != HELPER_ROLE
        or copied.get("status") not in {"ok", "exhausted"}
        or not isinstance(copied.get("url"), str)
        or exact_target_key(copied["url"]) == ""
        or not isinstance(copied.get("raw_content"), str)
        or isinstance(copied.get("attempt_count"), bool)
        or not isinstance(copied.get("attempt_count"), int)
        or not 1 <= copied["attempt_count"] <= MAX_HELPER_ATTEMPTS
        or not isinstance(attempts, list)
        or len(attempts) != copied["attempt_count"]
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or float(copied["elapsed_seconds"]) < 0
        or isinstance(copied.get("response_bytes"), bool)
        or not isinstance(copied.get("response_bytes"), int)
        or copied["response_bytes"] < 0
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.26 exact helper result drifted")
    successes = 0
    for index, attempt in enumerate(attempts, 1):
        if (
            not isinstance(attempt, Mapping)
            or set(attempt)
            != {
                "attempt",
                "outcome",
                "http_status",
                "error_type",
                "retryable",
                "elapsed_seconds",
                "response_bytes",
                "response_sha256",
            }
            or attempt.get("attempt") != index
            or attempt.get("outcome") not in {"success", "failure"}
            or (
                attempt.get("http_status") is not None
                and (
                    isinstance(attempt.get("http_status"), bool)
                    or not isinstance(attempt.get("http_status"), int)
                    or not 100 <= attempt["http_status"] <= 599
                )
            )
            or (
                attempt.get("error_type") is not None
                and not isinstance(attempt.get("error_type"), str)
            )
            or not isinstance(attempt.get("retryable"), bool)
            or isinstance(attempt.get("elapsed_seconds"), bool)
            or not isinstance(attempt.get("elapsed_seconds"), (int, float))
            or not math.isfinite(float(attempt["elapsed_seconds"]))
            or float(attempt["elapsed_seconds"]) < 0
            or isinstance(attempt.get("response_bytes"), bool)
            or not isinstance(attempt.get("response_bytes"), int)
            or attempt["response_bytes"] < 0
            or (
                attempt.get("response_sha256") is not None
                and SHA256.fullmatch(str(attempt["response_sha256"])) is None
            )
        ):
            raise ValueError("V2.48.26 exact helper attempt drifted")
        successes += int(attempt["outcome"] == "success")
    if (
        copied["status"] == "ok"
        and (
            successes != 1
            or attempts[-1]["outcome"] != "success"
            or not copied["raw_content"]
            or copied["response_bytes"] <= 0
            or SHA256.fullmatch(str(copied.get("response_sha256", ""))) is None
        )
    ):
        raise ValueError("V2.48.26 successful helper result drifted")
    if (
        copied["status"] == "exhausted"
        and (
            successes != 0
            or copied["raw_content"] != ""
            or copied["response_bytes"] != 0
            or copied["response_sha256"] is not None
        )
    ):
        raise ValueError("V2.48.26 exhausted helper result drifted")
    return copied


def validate_exact_transport_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "allowed_target_count",
        "logical_requests",
        "direct_helper_calls",
        "direct_deadline_rejections",
        "helper_total_wall_timeouts",
        "helper_nonzero_exits",
        "helper_invalid_results",
        "terminal_successes",
        "terminal_exhausted",
        "provider_attempts",
        "provider_retries",
        "response_bytes",
        "http_status_counts",
        "attempt_failure_class_counts",
        "sequential_within_task",
        "redirects_allowed",
        "unbound_exact_url_network_effect_allowed",
        "question_country_url_page_value_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "receipt_payload_sha256",
    }
    integer_fields = expected - {
        "role",
        "policy_id",
        "http_status_counts",
        "attempt_failure_class_counts",
        "sequential_within_task",
        "redirects_allowed",
        "unbound_exact_url_network_effect_allowed",
        "question_country_url_page_value_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "receipt_payload_sha256",
    }
    status_counts = copied.get("http_status_counts")
    failure_counts = copied.get("attempt_failure_class_counts")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or copied.get("allowed_target_count") != EXPECTED_TARGET_COUNT
        or copied.get("logical_requests", 0) > EXPECTED_TARGET_COUNT
        or not isinstance(status_counts, Mapping)
        or any(
            re.fullmatch(r"[1-5][0-9]{2}", str(name)) is None
            or isinstance(number, bool)
            or not isinstance(number, int)
            or number < 0
            for name, number in status_counts.items()
        )
        or not isinstance(failure_counts, Mapping)
        or any(
            not isinstance(name, str)
            or not name
            or isinstance(number, bool)
            or not isinstance(number, int)
            or number < 0
            for name, number in failure_counts.items()
        )
        or copied.get("sequential_within_task") is not True
        or copied.get("redirects_allowed") is not False
        or copied.get("unbound_exact_url_network_effect_allowed") is not False
        or copied.get(
            "question_country_url_page_value_prediction_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.26 exact transport receipt drifted")
    terminal_helper_failures = (
        copied["helper_total_wall_timeouts"]
        + copied["helper_nonzero_exits"]
        + copied["helper_invalid_results"]
    )
    if (
        copied["direct_helper_calls"] + copied["direct_deadline_rejections"]
        != copied["logical_requests"]
        or copied["terminal_successes"]
        + copied["terminal_exhausted"]
        + terminal_helper_failures
        + copied["direct_deadline_rejections"]
        != copied["logical_requests"]
        or copied["provider_retries"]
        != copied["provider_attempts"]
        - copied["terminal_successes"]
        - copied["terminal_exhausted"]
        or sum(status_counts.values()) > copied["provider_attempts"]
        or sum(failure_counts.values())
        != copied["provider_attempts"] - copied["terminal_successes"]
    ):
        raise ValueError("V2.48.26 exact transport conservation drifted")
    return copied


class WorldBankExactAPITransportSearchClient(WorldBankHardTotalWallSearchClient):
    """Route only visible-bound exact API targets through the new helper."""

    def __init__(
        self,
        *args: Any,
        allowed_exact_requests: Sequence[Mapping[str, str]],
        exact_helper_path: Path | None = None,
        exact_popen: Any = subprocess.Popen,
        exact_target_total_wall_seconds: float = EXACT_TARGET_TOTAL_WALL_SECONDS,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        root = Path(__file__).resolve().parents[2]
        helper = (
            exact_helper_path
            or root / "scripts/run_v24826_worldbank_exact_fetch_helper.py"
        ).resolve()
        expected_helper = (
            root / "scripts/run_v24826_worldbank_exact_fetch_helper.py"
        ).resolve()
        if (
            helper.is_symlink()
            or not helper.is_file()
            or helper != expected_helper
            or not helper.is_relative_to(root)
        ):
            raise ValueError("V2.48.26 exact helper identity drifted")
        wall = float(exact_target_total_wall_seconds)
        if not math.isfinite(wall) or wall != EXACT_TARGET_TOTAL_WALL_SECONDS:
            raise ValueError("V2.48.26 exact target wall drifted")
        allowed: dict[str, str] = {}
        for request in allowed_exact_requests:
            if not isinstance(request, Mapping):
                raise ValueError("V2.48.26 exact allowlist request drifted")
            url = str(request.get("url", ""))
            member = str(request.get("member_label", ""))
            key = exact_target_key(url)
            if member != key or url in allowed:
                raise ValueError("V2.48.26 exact allowlist binding drifted")
            allowed[url] = member
        if len(allowed) != EXPECTED_TARGET_COUNT:
            raise ValueError("V2.48.26 exact allowlist cardinality drifted")
        self._exact_helper_path = helper
        self._exact_popen = exact_popen
        self._exact_target_total_wall_seconds = wall
        self._allowed_exact_requests = dict(allowed)
        self._exact_lock = threading.Lock()
        self._exact_counts: Counter[str] = Counter()
        self._exact_status_counts: Counter[str] = Counter()
        self._exact_attempt_failure_counts: Counter[str] = Counter()

    @staticmethod
    def _terminate_exact_group(process: Any) -> None:
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

    def _exact_add(self, name: str, amount: int = 1) -> None:
        with self._exact_lock:
            self._exact_counts[name] += int(amount)

    def _exact_failure_batch(
        self, request: Mapping[str, str], status: str
    ) -> dict[str, Any]:
        return {
            "query": str(request.get("query", "world-bank target-value lookup")),
            "answer": "",
            "results": [],
            "error": str(status),
            "provider": "direct-worldbank-exact-json",
        }

    def _exact_fetch_one(self, request: Mapping[str, str]) -> dict[str, Any]:
        url = str(request["url"])
        member = str(request["member_label"])
        self._increment("fetch_calls")
        self._exact_add("logical_requests")
        remaining = self.remaining_effect_seconds()
        if remaining < self.minimum_attempt_seconds:
            self._increment("fetch_failures")
            self._exact_add("direct_deadline_rejections")
            return self._exact_failure_batch(request, "task_deadline_exhausted")
        self._exact_add("direct_helper_calls")
        process = self._exact_popen(
            [
                sys.executable,
                "-I",
                "-B",
                str(self._exact_helper_path),
            ],
            cwd=self._exact_helper_path.parents[1],
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
            self._terminate_exact_group(process)
            self._increment("fetch_failures")
            self._exact_add("helper_total_wall_timeouts")
            return self._exact_failure_batch(
                request, "task_deadline_exhausted_after_helper_launch"
            )
        try:
            stdout, _ = process.communicate(
                json.dumps({"url": url}, ensure_ascii=False),
                timeout=min(
                    self._exact_target_total_wall_seconds,
                    remaining_after_launch,
                ),
            )
        except subprocess.TimeoutExpired:
            self._terminate_exact_group(process)
            self._increment("fetch_failures")
            self._exact_add("helper_total_wall_timeouts")
            return self._exact_failure_batch(request, "exact_helper_total_wall_timeout")
        if process.returncode != 0:
            self._increment("fetch_failures")
            self._exact_add("helper_nonzero_exits")
            return self._exact_failure_batch(request, "exact_helper_nonzero_exit")
        try:
            helper = validate_helper_result(json.loads(stdout))
        except (json.JSONDecodeError, TypeError, ValueError):
            self._increment("fetch_failures")
            self._exact_add("helper_invalid_results")
            return self._exact_failure_batch(request, "exact_helper_invalid_result")
        if helper["url"] != url or exact_target_key(helper["url"]) != member:
            self._increment("fetch_failures")
            self._exact_add("helper_invalid_results")
            return self._exact_failure_batch(request, "exact_helper_binding_drift")
        self._exact_add("provider_attempts", helper["attempt_count"])
        self._exact_add("provider_retries", helper["attempt_count"] - 1)
        with self._exact_lock:
            for attempt in helper["attempts"]:
                if attempt["http_status"] is not None:
                    self._exact_status_counts[str(attempt["http_status"])] += 1
                if attempt["outcome"] == "failure":
                    self._exact_attempt_failure_counts[
                        str(attempt["error_type"] or "unknown_failure")
                    ] += 1
        if helper["status"] != "ok":
            self._increment("fetch_failures")
            self._exact_add("terminal_exhausted")
            return self._exact_failure_batch(request, "exact_api_exhausted")
        self._exact_add("terminal_successes")
        self._exact_add("response_bytes", helper["response_bytes"])
        return {
            "query": str(request.get("query", "world-bank target-value lookup")),
            "answer": "",
            "results": [
                {
                    "title": str(request.get("title", "")),
                    "url": url,
                    "fetch_url": url,
                    "content": "",
                    "raw_content": helper["raw_content"],
                    "page_links": [],
                    "score": None,
                    "source_type": "direct-worldbank-exact-json",
                    "requested_url": url,
                    "directory_member_label": member,
                    "fetch_status": "ok",
                }
            ],
            "error": None,
            "provider": "direct-worldbank-exact-json",
        }

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        values = list(requests_)
        allowed_flags: list[bool] = []
        for request in values:
            if not isinstance(request, Mapping):
                raise ValueError("V2.48.26 fetch request drifted")
            url = str(request.get("url", ""))
            member = str(request.get("member_label", ""))
            allowed = self._allowed_exact_requests.get(url) == member
            if _looks_like_exact_api_url(url) and not allowed:
                raise ValueError("V2.48.26 unbound exact URL rejected before effect")
            allowed_flags.append(allowed)
        if any(allowed_flags):
            if not all(allowed_flags) or len(values) > EXPECTED_TARGET_COUNT:
                raise ValueError("V2.48.26 mixed or oversized exact fetch rejected")
            if len({str(request["url"]) for request in values}) != len(values):
                raise ValueError("V2.48.26 duplicate exact fetch rejected")
            # Deliberately sequential.  The outer task executor still provides
            # the frozen task-level concurrency.
            return [self._exact_fetch_one(request) for request in values]
        return super().fetch_urls(values)

    def exact_api_transport_receipt(self) -> dict[str, Any]:
        with self._exact_lock:
            counts = dict(self._exact_counts)
            status = dict(sorted(self._exact_status_counts.items()))
            failures = dict(sorted(self._exact_attempt_failure_counts.items()))
        value = {
            "artifact_version": 1,
            "role": RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "allowed_target_count": EXPECTED_TARGET_COUNT,
            "logical_requests": int(counts.get("logical_requests", 0)),
            "direct_helper_calls": int(counts.get("direct_helper_calls", 0)),
            "direct_deadline_rejections": int(
                counts.get("direct_deadline_rejections", 0)
            ),
            "helper_total_wall_timeouts": int(
                counts.get("helper_total_wall_timeouts", 0)
            ),
            "helper_nonzero_exits": int(counts.get("helper_nonzero_exits", 0)),
            "helper_invalid_results": int(
                counts.get("helper_invalid_results", 0)
            ),
            "terminal_successes": int(counts.get("terminal_successes", 0)),
            "terminal_exhausted": int(counts.get("terminal_exhausted", 0)),
            "provider_attempts": int(counts.get("provider_attempts", 0)),
            "provider_retries": int(counts.get("provider_retries", 0)),
            "response_bytes": int(counts.get("response_bytes", 0)),
            "http_status_counts": status,
            "attempt_failure_class_counts": failures,
            "sequential_within_task": True,
            "redirects_allowed": False,
            "unbound_exact_url_network_effect_allowed": False,
            "question_country_url_page_value_prediction_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_exact_transport_receipt(value)


__all__ = [
    "EXACT_TARGET_TOTAL_WALL_SECONDS",
    "EXPECTED_TARGET_COUNT",
    "HELPER_ROLE",
    "MAX_HELPER_ATTEMPTS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "WorldBankExactAPITransportSearchClient",
    "exact_target_key",
    "payload_sha256",
    "validate_exact_transport_receipt",
    "validate_helper_result",
]
