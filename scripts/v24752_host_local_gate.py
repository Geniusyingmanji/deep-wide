#!/usr/bin/env python3
"""Fresh cross-domain gate with a fixed host-local Crossref scheduler."""

from __future__ import annotations

import concurrent.futures
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24745_cross_domain_adapters as runtime  # noqa: E402
from deepwide_agent import v24750_host_local_contract as contract  # noqa: E402
from scripts import v24748_cross_domain_gate as prior_gate  # noqa: E402
from scripts import v24751_public_get_helper as helper  # noqa: E402


base = prior_gate.base
DATE = "20260806"
PROTOCOL_ID = "v24752_host_local_cross_domain_gate_v1"
SCRIPT = Path("scripts/v24752_host_local_gate.py")
SCRIPT_TEST = Path("tests/test_v24752_host_local_gate.py")
POLICY = Path(f"results/v24751_host_local_scheduler_policy_v1_{DATE}.json")
POPULATION = Path(f"results/v24750_host_local_population_design_v1_{DATE}.json")
PARENT_DIAGNOSIS = Path(
    f"results/v24749_v24748_host_rate_limit_diagnosis_v1_{DATE}.json"
)
PRIOR_RESULT = Path(f"results/v24748_cross_domain_result_v1_{DATE}.json")
PRIOR_DECISION = Path(f"results/v24748_cross_domain_decision_v1_{DATE}.json")
PRIOR_AUDIT = Path(f"results/v24748_cross_domain_postresult_audit_v1_{DATE}.json")
SCHEDULE_RECEIPT_NAME = "schedule_receipt.json"
CROSSREF_START_INTERVAL_SECONDS = 1.1
HOST_MAX_INFLIGHT = {
    runtime.ROR_HOST: 8,
    runtime.CROSSREF_HOST: 1,
    runtime.OPENALEX_HOST: 8,
}
HOST_MINIMUM_START_INTERVAL = {
    runtime.ROR_HOST: 0.0,
    runtime.CROSSREF_HOST: CROSSREF_START_INTERVAL_SECONDS,
    runtime.OPENALEX_HOST: 0.0,
}
HOST_HARD_WALL_SECONDS = {
    runtime.ROR_HOST: 20.0,
    runtime.CROSSREF_HOST: 1.0,
    runtime.OPENALEX_HOST: 20.0,
}
HELPER_TERMINATION_ALLOWANCE_SECONDS = 1.0
SCHEDULER_AND_PROCESS_LAUNCH_SLACK_SECONDS = 1.0
DERIVED_NETWORK_WAVE_CEILING_SECONDS = 33.0
SCHEDULE_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "policy_file_sha256",
        "request_count",
        "event_count",
        "events",
        "host_summaries",
        "all_requests_submitted_once",
        "crossref_start_interval_compliant",
        "host_inflight_limits_compliant",
        "response_url_body_identity_value_or_prediction_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "schedule_payload_sha256",
    }
)
EVENT_KEYS = frozenset(
    {
        "request_index",
        "source_host",
        "started_offset_seconds",
        "completed_offset_seconds",
        "started_sequence",
        "completed_sequence",
    }
)


def _configure() -> None:
    base.PROTOCOL_ID = PROTOCOL_ID
    base.PROTOCOL = Path(f"results/v24752_host_local_preregistration_v1_{DATE}.json")
    base.PREAUDIT = Path(
        f"results/v24752_host_local_preactivation_audit_v1_{DATE}.json"
    )
    base.ACTIVATION = Path(f"results/v24752_host_local_activation_v1_{DATE}.json")
    base.EXECUTION_START = Path(
        f"results/v24752_host_local_execution_start_v1_{DATE}.json"
    )
    base.RESULT = Path(f"results/v24752_host_local_result_v1_{DATE}.json")
    base.DECISION = Path(f"results/v24752_host_local_decision_v1_{DATE}.json")
    base.POSTAUDIT = Path(
        f"results/v24752_host_local_postresult_audit_v1_{DATE}.json"
    )
    base.POPULATION = POPULATION
    base.CONTRACT_SOURCE = Path("src/deepwide_agent/v24750_host_local_contract.py")
    base.HELPER_SOURCE = Path("scripts/v24751_public_get_helper.py")
    base.SCRIPT = SCRIPT
    base.OUTPUT_ROOT = Path(f"outputs/v24752_host_local_gate_v1_{DATE}")
    base.PREDICTIONS = base.OUTPUT_ROOT / "frozen_predictions.jsonl"
    base.PREDICTION_FREEZE = base.OUTPUT_ROOT / "prediction_freeze.json"
    base.RUN_SUMMARY = base.OUTPUT_ROOT / "run_summary.json"
    base.ATTEMPT_CLAIM = base.OUTPUT_ROOT / "attempt_claim.json"
    base.LEASE_OWNER = PROTOCOL_ID
    base.LEASE_PURPOSE = "benchmark_external_fresh_host_local_cross_domain_gate"
    base.RUNNER_MARKER = "scripts/v24752_host_local_gate.py run"
    base.WORKERS = 17
    base.contract = contract
    base.runtime = runtime
    base.helper = helper
    base.DESIGN_TEST = Path("tests/test_design_v24750_host_local_population.py")
    base.HELPER_TEST = Path("tests/test_v24751_public_get_helper.py")
    base.SCRIPT_TEST = SCRIPT_TEST
    base.EXPECTED_TESTS = 41
    base.TEST_SUITES = (
        (base.BINDER_TEST, 12),
        (base.DESIGN_TEST, 3),
        (base.RUNTIME_TEST, 6),
        (base.HELPER_TEST, 3),
        (Path("tests/test_v24747_cross_domain_gate.py"), 7),
        (Path("tests/test_v24748_cross_domain_gate.py"), 2),
        (SCRIPT_TEST, 8),
    )
    base.CONTROL_SURFACE = (
        base.RUNTIME_SOURCE,
        base.BINDER_SOURCE,
        base.CONTRACT_SOURCE,
        base.HELPER_SOURCE,
        Path("scripts/v24747_cross_domain_gate.py"),
        Path("scripts/v24748_cross_domain_gate.py"),
        SCRIPT,
        base.LEASE_SOURCE,
        base.RUNTIME_TEST,
        base.BINDER_TEST,
        base.DESIGN_TEST,
        base.HELPER_TEST,
        Path("tests/test_v24747_cross_domain_gate.py"),
        Path("tests/test_v24748_cross_domain_gate.py"),
        SCRIPT_TEST,
        POPULATION,
        POLICY,
        PARENT_DIAGNOSIS,
        PRIOR_RESULT,
        PRIOR_DECISION,
        PRIOR_AUDIT,
    )
    base.FORWARD_AST_SURFACE = (
        base.RUNTIME_SOURCE,
        base.BINDER_SOURCE,
        base.CONTRACT_SOURCE,
        base.HELPER_SOURCE,
        Path("scripts/v24747_cross_domain_gate.py"),
        Path("scripts/v24748_cross_domain_gate.py"),
        SCRIPT,
    )


_configure()


def _policy() -> dict[str, Any]:
    value = base._read(ROOT, POLICY)
    expected_hosts = {
        runtime.CROSSREF_HOST: {
            "request_count": 16,
            "max_inflight": 1,
            "minimum_start_interval_seconds": 1.1,
        },
        runtime.OPENALEX_HOST: {
            "request_count": 8,
            "max_inflight": 8,
            "minimum_start_interval_seconds": 0.0,
        },
        runtime.ROR_HOST: {
            "request_count": 8,
            "max_inflight": 8,
            "minimum_start_interval_seconds": 0.0,
        },
    }
    if (
        value.get("role") != "v24751_host_local_scheduler_policy"
        or value.get("parent_diagnosis_path") != str(PARENT_DIAGNOSIS)
        or value.get("population_path") != str(POPULATION)
        or value.get("request_contract")
        != {
            "total_unique_urls": 32,
            "attempts_per_url": 1,
            "global_executor_capacity": 17,
            "single_wave_submission": True,
            "resume_retry_or_selective_rerun": False,
        }
        or value.get("host_policy") != expected_hosts
        or value.get("wall_contract")
        != {
            "per_host_hard_wall_seconds": dict(HOST_HARD_WALL_SECONDS),
            "helper_termination_allowance_seconds": (
                HELPER_TERMINATION_ALLOWANCE_SECONDS
            ),
            "socket_timeout_seconds": 15.0,
            "scheduler_and_process_launch_slack_seconds": (
                SCHEDULER_AND_PROCESS_LAUNCH_SLACK_SECONDS
            ),
            "derived_network_wave_ceiling_seconds": (
                DERIVED_NETWORK_WAVE_CEILING_SECONDS
            ),
            "experiment_wall_ceiling_seconds": 40.0,
        }
        or _derived_network_wave_ceiling_seconds()
        != DERIVED_NETWORK_WAVE_CEILING_SECONDS
        or value.get("selection_timing")
        != {
            "policy_fixed_before_fresh_population_endpoint_outcome": True,
            "prior_response_body_url_doi_entity_value_or_prediction_read": False,
            "only_prior_content_free_host_status_counts_used": True,
        }
        or value.get("authorization")
        != {
            "scheduler_and_gate_build": True,
            "external_launch": False,
            "same_or_prior_population_retry": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not base._sealed(value, "policy_payload_sha256")
    ):
        raise RuntimeError("V2.47.52 scheduler policy drifted")
    return value


def _derived_network_wave_ceiling_seconds() -> float:
    crossref_count = 16
    crossref_step = max(
        CROSSREF_START_INTERVAL_SECONDS,
        HOST_HARD_WALL_SECONDS[runtime.CROSSREF_HOST]
        + HELPER_TERMINATION_ALLOWANCE_SECONDS,
    )
    crossref_ceiling = crossref_count * crossref_step
    parallel_ceiling = max(
        HOST_HARD_WALL_SECONDS[runtime.ROR_HOST],
        HOST_HARD_WALL_SECONDS[runtime.OPENALEX_HOST],
    ) + HELPER_TERMINATION_ALLOWANCE_SECONDS
    return round(
        max(crossref_ceiling, parallel_ceiling)
        + SCHEDULER_AND_PROCESS_LAUNCH_SLACK_SECONDS,
        6,
    )


def _population(root: Path = ROOT) -> dict[str, Any]:
    value = base._read(root, POPULATION)
    if (
        value.get("role") != "v24750_host_local_population_design"
        or value.get("parent_diagnosis_file_sha256")
        != base.sha256(root / PARENT_DIAGNOSIS)
        or value.get("task_shape")
        != {
            "ror_tasks": 2,
            "official_crossref_tasks": 2,
            "ordinary_dual_source_tasks": 2,
            "total_tasks": 6,
            "total_rows": 24,
        }
        or value.get("visible_contract_sha256")
        != base.sha256(root / base.CONTRACT_SOURCE)
        or value.get("authorization")
        != {
            "host_local_scheduler_and_gate_build": True,
            "external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        }
        or not base._sealed(value, "design_payload_sha256")
    ):
        raise RuntimeError("V2.47.52 population design drifted")
    return value


base._population = _population


def _run_tests() -> tuple[bool, int, str]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    outputs = []
    total = 0
    passed = True
    python = ROOT / ".venv-eval/bin/python"
    for suite, expected in base.TEST_SUITES:
        completed = subprocess.run(
            [
                str(python),
                "-I",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                suite.name,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            check=False,
        )
        outputs.append(completed.stdout)
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        total += observed
        passed = passed and completed.returncode == 0 and observed == expected
    output = "\n".join(outputs)
    return passed and total == base.EXPECTED_TESTS, total, output


base._run_tests = _run_tests


_old_build_protocol = base.build_protocol
_old_validate_protocol = base.validate_protocol


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else base._read(root, base.PROTOCOL)
    scheduler = copied.get("host_local_scheduler")
    if (
        scheduler
        != {
            "policy_file_sha256": base.sha256(root / POLICY),
            "schedule_receipt_relative_path": str(
                base.OUTPUT_ROOT / SCHEDULE_RECEIPT_NAME
            ),
            "host_max_inflight": dict(HOST_MAX_INFLIGHT),
            "host_minimum_start_interval_seconds": dict(
                HOST_MINIMUM_START_INTERVAL
            ),
            "host_hard_wall_seconds": dict(HOST_HARD_WALL_SECONDS),
            "derived_network_wave_ceiling_seconds": (
                DERIVED_NETWORK_WAVE_CEILING_SECONDS
            ),
            "schedule_is_outcome_independent": True,
            "one_attempt_per_url": True,
        }
        or not base._sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.52 protocol scheduler binding drifted")
    _policy()
    legacy = copy.deepcopy(copied)
    legacy.pop("host_local_scheduler", None)
    legacy.pop("protocol_payload_sha256", None)
    legacy["protocol_payload_sha256"] = base.payload_sha256(legacy)
    _old_validate_protocol(root, value=legacy)
    return copied


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    _policy()
    current = base.validate_protocol
    try:
        base.validate_protocol = _old_validate_protocol
        value = _old_build_protocol(root, now=now)
    finally:
        base.validate_protocol = current
    value.pop("protocol_payload_sha256")
    value["host_local_scheduler"] = {
        "policy_file_sha256": base.sha256(root / POLICY),
        "schedule_receipt_relative_path": str(
            base.OUTPUT_ROOT / SCHEDULE_RECEIPT_NAME
        ),
        "host_max_inflight": dict(HOST_MAX_INFLIGHT),
        "host_minimum_start_interval_seconds": dict(
            HOST_MINIMUM_START_INTERVAL
        ),
        "host_hard_wall_seconds": dict(HOST_HARD_WALL_SECONDS),
        "derived_network_wave_ceiling_seconds": (
            DERIVED_NETWORK_WAVE_CEILING_SECONDS
        ),
        "schedule_is_outcome_independent": True,
        "one_attempt_per_url": True,
    }
    value["protocol_payload_sha256"] = base.payload_sha256(value)
    return validate_protocol(root, value=value)


base.build_protocol = build_protocol
base.validate_protocol = validate_protocol


class _InflightTracker:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.current: Counter[str] = Counter()
        self.maximum: Counter[str] = Counter()
        self.sequence = 0

    def enter(self, host: str) -> int:
        with self.lock:
            self.sequence += 1
            self.current[host] += 1
            self.maximum[host] = max(self.maximum[host], self.current[host])
            return self.sequence

    def leave(self, host: str) -> int:
        with self.lock:
            self.current[host] -= 1
            if self.current[host] < 0:
                raise RuntimeError("V2.47.52 inflight accounting drifted")
            self.sequence += 1
            return self.sequence


def _instrumented_request(
    index_url: tuple[int, str],
    *,
    origin: float,
    tracker: _InflightTracker,
    request_one: Callable[[tuple[int, str]], tuple[dict[str, Any], bytes]],
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    index, url = index_url
    host = urlsplit(url).hostname or ""
    started = monotonic()
    started_sequence = tracker.enter(host)
    try:
        receipt, body = request_one(index_url)
    finally:
        completed_sequence = tracker.leave(host)
    completed = monotonic()
    event = {
        "request_index": index,
        "source_host": host,
        "started_offset_seconds": round(started - origin, 9),
        "completed_offset_seconds": round(completed - origin, 9),
        "started_sequence": started_sequence,
        "completed_sequence": completed_sequence,
    }
    return receipt, body, event


def _crossref_lane(
    rows: Sequence[tuple[int, str]],
    *,
    origin: float,
    tracker: _InflightTracker,
    request_one: Callable[[tuple[int, str]], tuple[dict[str, Any], bytes]],
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> list[tuple[dict[str, Any], bytes, dict[str, Any]]]:
    output = []
    last_start: float | None = None
    for row in rows:
        if last_start is not None:
            deadline = last_start + CROSSREF_START_INTERVAL_SECONDS
            remaining = deadline - monotonic()
            while remaining > 0:
                sleep(remaining)
                remaining = deadline - monotonic()
        result = _instrumented_request(
            row,
            origin=origin,
            tracker=tracker,
            request_one=request_one,
            monotonic=monotonic,
        )
        output.append(result)
        last_start = origin + float(result[2]["started_offset_seconds"])
    return output


def _observed_max_inflight(events: Sequence[Mapping[str, Any]], host: str) -> int:
    points = []
    for event in events:
        if event.get("source_host") != host:
            continue
        points.append((int(event["started_sequence"]), 1))
        points.append((int(event["completed_sequence"]), -1))
    current = maximum = 0
    for _sequence, delta in sorted(points):
        current += delta
        maximum = max(maximum, current)
    return maximum


def _host_local_request_one(
    index_url: tuple[int, str],
) -> tuple[dict[str, Any], bytes]:
    index, url = index_url
    host = urlsplit(url).hostname or ""
    if host not in HOST_HARD_WALL_SECONDS:
        raise ValueError("V2.47.52 request host drifted")
    response = base.hard_get(
        url, timeout_seconds=HOST_HARD_WALL_SECONDS[host]
    )
    body = response.pop("body")
    success = (
        response["kind"] == "response"
        and response["status_code"] == 200
        and response["final_url"] == url
        and bool(body)
    )
    failure_type = None
    if not success:
        failure_type = (
            "http_or_content_invalid"
            if response["kind"] == "response"
            else response["kind"]
        )
    receipt = {
        "request_index": index,
        "source_host": host,
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "attempts": 1,
        "transport_success": success,
        "failure_type": failure_type,
        "http_status": response["status_code"],
        "elapsed_seconds": response["elapsed_seconds"],
        "response_bytes": len(body),
        "raw_sha256": hashlib.sha256(body).hexdigest() if success else None,
        "response_content_persisted": False,
    }
    return receipt, body if success else b""


def _schedule_receipt(
    events: Sequence[Mapping[str, Any]], *, tracker: _InflightTracker
) -> dict[str, Any]:
    ordered = sorted(
        (dict(event) for event in events), key=lambda item: item["request_index"]
    )
    summaries = {}
    for host in sorted(HOST_MAX_INFLIGHT):
        host_events = sorted(
            (event for event in ordered if event["source_host"] == host),
            key=lambda item: item["started_offset_seconds"],
        )
        intervals = [
            round(
                host_events[index]["started_offset_seconds"]
                - host_events[index - 1]["started_offset_seconds"],
                9,
            )
            for index in range(1, len(host_events))
        ]
        observed_max = _observed_max_inflight(ordered, host)
        summaries[host] = {
            "request_count": len(host_events),
            "configured_max_inflight": HOST_MAX_INFLIGHT[host],
            "observed_max_inflight": observed_max,
            "tracker_max_inflight": int(tracker.maximum[host]),
            "configured_minimum_start_interval_seconds": HOST_MINIMUM_START_INTERVAL[
                host
            ],
            "observed_minimum_start_interval_seconds": (
                min(intervals) if intervals else None
            ),
        }
    value = {
        "artifact_version": 1,
        "role": "v24752_host_local_schedule_receipt",
        "protocol_id": PROTOCOL_ID,
        "policy_file_sha256": base.sha256(ROOT / POLICY),
        "request_count": base.REQUEST_COUNT,
        "event_count": len(ordered),
        "events": ordered,
        "host_summaries": summaries,
        "all_requests_submitted_once": (
            len(ordered) == base.REQUEST_COUNT
            and {event["request_index"] for event in ordered}
            == set(range(1, base.REQUEST_COUNT + 1))
        ),
        "crossref_start_interval_compliant": (
            summaries[runtime.CROSSREF_HOST][
                "observed_minimum_start_interval_seconds"
            ]
            is not None
            and summaries[runtime.CROSSREF_HOST][
                "observed_minimum_start_interval_seconds"
            ]
            + 0.000000001
            >= CROSSREF_START_INTERVAL_SECONDS
        ),
        "host_inflight_limits_compliant": all(
            summaries[host]["observed_max_inflight"] <= HOST_MAX_INFLIGHT[host]
            and summaries[host]["tracker_max_inflight"] <= HOST_MAX_INFLIGHT[host]
            for host in HOST_MAX_INFLIGHT
        ),
        "response_url_body_identity_value_or_prediction_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["schedule_payload_sha256"] = base.payload_sha256(value)
    return validate_schedule_receipt(value)


def validate_schedule_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    events = copied.get("events")
    summaries = copied.get("host_summaries")
    if (
        set(copied) != SCHEDULE_RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24752_host_local_schedule_receipt"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("policy_file_sha256") != base.sha256(ROOT / POLICY)
        or copied.get("request_count") != base.REQUEST_COUNT
        or copied.get("event_count") != base.REQUEST_COUNT
        or not isinstance(events, Sequence)
        or isinstance(events, (str, bytes))
        or len(events) != base.REQUEST_COUNT
        or any(
            not isinstance(event, Mapping)
            or set(event) != EVENT_KEYS
            or event.get("request_index") != index
            or event.get("source_host")
            != urlsplit(base._request_vector()[index - 1]).hostname
            or not isinstance(event.get("started_offset_seconds"), (int, float))
            or isinstance(event.get("started_offset_seconds"), bool)
            or not isinstance(event.get("completed_offset_seconds"), (int, float))
            or isinstance(event.get("completed_offset_seconds"), bool)
            or not isinstance(event.get("started_sequence"), int)
            or isinstance(event.get("started_sequence"), bool)
            or not isinstance(event.get("completed_sequence"), int)
            or isinstance(event.get("completed_sequence"), bool)
            or not 0
            <= float(event.get("started_offset_seconds"))
            <= float(event.get("completed_offset_seconds"))
            or not 0
            < int(event.get("started_sequence"))
            < int(event.get("completed_sequence"))
            or not math.isfinite(float(event.get("completed_offset_seconds")))
            for index, event in enumerate(events, 1)
        )
        or {
            int(event[key])
            for event in events
            for key in ("started_sequence", "completed_sequence")
        }
        != set(range(1, base.REQUEST_COUNT * 2 + 1))
        or not isinstance(summaries, Mapping)
        or set(summaries) != set(HOST_MAX_INFLIGHT)
    ):
        raise RuntimeError("V2.47.52 schedule receipt envelope drifted")
    expected_counts = Counter(urlsplit(url).hostname for url in base._request_vector())
    for host in HOST_MAX_INFLIGHT:
        row = summaries.get(host)
        host_events = sorted(
            (event for event in events if event["source_host"] == host),
            key=lambda event: event["started_offset_seconds"],
        )
        intervals = [
            round(
                host_events[index]["started_offset_seconds"]
                - host_events[index - 1]["started_offset_seconds"],
                9,
            )
            for index in range(1, len(host_events))
        ]
        expected_minimum = min(intervals) if intervals else None
        observed_max = _observed_max_inflight(events, host)
        if (
            not isinstance(row, Mapping)
            or row.get("request_count") != expected_counts[host]
            or row.get("configured_max_inflight") != HOST_MAX_INFLIGHT[host]
            or row.get("observed_max_inflight") != observed_max
            or not isinstance(row.get("tracker_max_inflight"), int)
            or isinstance(row.get("tracker_max_inflight"), bool)
            or row.get("tracker_max_inflight") != observed_max
            or row.get("configured_minimum_start_interval_seconds")
            != HOST_MINIMUM_START_INTERVAL[host]
            or row.get("observed_minimum_start_interval_seconds")
            != expected_minimum
        ):
            raise RuntimeError("V2.47.52 host schedule summary drifted")
    crossref_minimum = summaries[runtime.CROSSREF_HOST][
        "observed_minimum_start_interval_seconds"
    ]
    expected_inflight_compliant = all(
        summaries[host]["observed_max_inflight"] <= HOST_MAX_INFLIGHT[host]
        for host in HOST_MAX_INFLIGHT
    )
    if (
        copied.get("all_requests_submitted_once") is not True
        or copied.get("crossref_start_interval_compliant")
        is not (
            crossref_minimum is not None
            and crossref_minimum + 0.000000001
            >= CROSSREF_START_INTERVAL_SECONDS
        )
        or copied.get("crossref_start_interval_compliant") is not True
        or copied.get("host_inflight_limits_compliant")
        is not expected_inflight_compliant
        or copied.get("host_inflight_limits_compliant") is not True
        or copied.get(
            "response_url_body_identity_value_or_prediction_persisted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or not base._sealed(copied, "schedule_payload_sha256")
    ):
        raise RuntimeError("V2.47.52 schedule receipt drifted")
    return copied


def schedule_requests(
    *,
    request_one: Callable[
        [tuple[int, str]], tuple[dict[str, Any], bytes]
    ] = _host_local_request_one,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[tuple[dict[str, Any], bytes]], dict[str, Any]]:
    rows = list(enumerate(base._request_vector(), 1))
    crossref = [row for row in rows if urlsplit(row[1]).hostname == runtime.CROSSREF_HOST]
    other = [row for row in rows if urlsplit(row[1]).hostname != runtime.CROSSREF_HOST]
    if len(crossref) != 16 or len(other) != 16:
        raise RuntimeError("V2.47.52 scheduler request partition drifted")
    origin = monotonic()
    tracker = _InflightTracker()
    outputs: list[tuple[dict[str, Any], bytes, dict[str, Any]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=17) as executor:
        crossref_future = executor.submit(
            _crossref_lane,
            crossref,
            origin=origin,
            tracker=tracker,
            request_one=request_one,
            monotonic=monotonic,
            sleep=sleep,
        )
        other_futures = [
            executor.submit(
                _instrumented_request,
                row,
                origin=origin,
                tracker=tracker,
                request_one=request_one,
                monotonic=monotonic,
            )
            for row in other
        ]
        for future in other_futures:
            outputs.append(future.result())
        outputs.extend(crossref_future.result())
    outputs.sort(key=lambda item: item[0]["request_index"])
    receipt = _schedule_receipt([item[2] for item in outputs], tracker=tracker)
    return [(item[0], item[1]) for item in outputs], receipt


_old_aggregate = base.aggregate
_old_validate_result = base.validate_result


def aggregate(
    task_rows: Sequence[Mapping[str, Any]],
    request_receipts: Sequence[Mapping[str, Any]],
    *,
    experiment_wall_seconds: float,
    predictions_sha256: str,
    freeze_sha256: str,
    now: int | None = None,
    schedule_receipt_sha256: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, decision = _old_aggregate(
        task_rows,
        request_receipts,
        experiment_wall_seconds=experiment_wall_seconds,
        predictions_sha256=predictions_sha256,
        freeze_sha256=freeze_sha256,
        now=now,
    )
    if schedule_receipt_sha256 is None:
        return result, decision
    if re.fullmatch(r"[0-9a-f]{64}", schedule_receipt_sha256) is None:
        raise RuntimeError("V2.47.52 schedule receipt hash drifted")
    result.pop("result_payload_sha256")
    result["schedule_receipt_sha256"] = schedule_receipt_sha256
    result["result_payload_sha256"] = base.payload_sha256(result)
    decision.pop("decision_payload_sha256")
    decision["result_payload_sha256"] = result["result_payload_sha256"]
    decision["decision_payload_sha256"] = base.payload_sha256(decision)
    return result, decision


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if "schedule_receipt_sha256" not in copied:
        return _old_validate_result(copied)
    outer_unsigned = dict(copied)
    outer_seal = outer_unsigned.pop("result_payload_sha256", None)
    schedule_hash = outer_unsigned.get("schedule_receipt_sha256")
    schedule_path = ROOT / base.OUTPUT_ROOT / SCHEDULE_RECEIPT_NAME
    if (
        outer_seal != base.payload_sha256(outer_unsigned)
        or schedule_hash != base.sha256(schedule_path)
    ):
        raise RuntimeError("V2.47.52 result schedule binding drifted")
    schedule = validate_schedule_receipt(
        json.loads(schedule_path.read_text(encoding="utf-8"))
    )
    if (
        schedule.get("all_requests_submitted_once") is not True
        or schedule.get("crossref_start_interval_compliant") is not True
        or schedule.get("host_inflight_limits_compliant") is not True
    ):
        raise RuntimeError("V2.47.52 result schedule gate drifted")
    legacy = copy.deepcopy(copied)
    legacy.pop("schedule_receipt_sha256")
    legacy.pop("result_payload_sha256")
    legacy["result_payload_sha256"] = base.payload_sha256(legacy)
    _old_validate_result(legacy)
    return copied


base.aggregate = aggregate
base.validate_result = validate_result


def run_experiment() -> tuple[dict[str, Any], dict[str, Any]]:
    base.validate_attempt_claim(base._read(ROOT, base.ATTEMPT_CLAIM))
    started = time.monotonic()
    urls = base._request_vector()
    outputs, schedule = schedule_requests()
    request_receipts = [item[0] for item in outputs]
    responses = {
        url: output[1]
        for url, output in zip(urls, outputs, strict=True)
    }
    schedule_path = ROOT / base.OUTPUT_ROOT / SCHEDULE_RECEIPT_NAME
    base._publish(schedule_path, schedule)
    prediction_rows = []
    task_rows = []
    for position, task in enumerate(base._tasks(), 1):
        mode = runtime.visible_contract(task)["mode"]
        task_urls = runtime.request_urls(task)
        subset = {url: responses[url] for url in task_urls}
        runtime_valid = True
        try:
            value = runtime.run_task(task, subset)
        except (KeyError, TypeError, ValueError):
            runtime_valid = False
            value = base._failure_projection(task)
        receipt = value["receipt"]
        binding = receipt["binding_receipt"]
        failures = receipt.get("failure_type_counts", {})
        prediction_rows.append(
            {
                "opaque_id": task["opaque_id"],
                "predictions": {
                    "baseline": value["baseline"],
                    "candidate": value["candidate"],
                },
                "runtime_result_sha256": value.get("result_payload_sha256"),
                "runtime_result_valid": runtime_valid,
            }
        )
        task_rows.append(
            {
                "position": position,
                "mode": mode,
                "runtime_valid": runtime_valid,
                "prediction_changed": bool(receipt["prediction_changed"]),
                "changed_cell_count": int(binding["changed_cell_count"]),
                "fully_admitted_row_count": int(receipt["fully_admitted_row_count"]),
                "official_admitted_cell_count": int(
                    binding["official_admitted_cell_count"]
                ),
                "corroborated_admitted_cell_count": int(
                    binding["corroborated_admitted_cell_count"]
                ),
                "conflicting_cell_count": int(binding["conflicting_cell_count"]),
                "validated_record_count": int(receipt["validated_record_count"]),
                "adapter_failure_count": sum(
                    int(amount) for amount in failures.values()
                ),
                "response_or_prediction_content_persisted_in_public_aggregate": False,
            }
        )
    if (ROOT / base.OUTPUT_ROOT).is_symlink() or not (ROOT / base.OUTPUT_ROOT).is_dir():
        raise RuntimeError("V2.47.52 attempt claim directory drifted")
    base._publish_jsonl(ROOT / base.PREDICTIONS, prediction_rows)
    summary = {
        "artifact_version": 1,
        "role": "v24752_host_local_run_summary",
        "attempt_claim_sha256": base.sha256(ROOT / base.ATTEMPT_CLAIM),
        "schedule_receipt_sha256": base.sha256(schedule_path),
        "selected_tasks": base.TASK_COUNT,
        "terminal_prediction_rows": len(prediction_rows),
        "terminal_arm_predictions": len(prediction_rows) * 2,
        "request_attempts": len(request_receipts),
        "runtime_valid_tasks": sum(row["runtime_valid"] for row in task_rows),
        "experiment_wall_seconds": round(time.monotonic() - started, 6),
        "resume_retry_skip_or_selective_rerun": False,
        "private_population_provenance_evaluator_or_quality_opened": False,
    }
    summary["summary_payload_sha256"] = base.payload_sha256(summary)
    base._publish(ROOT / base.RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24752_host_local_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "selected_tasks": base.TASK_COUNT,
        "terminal_arm_predictions": base.TASK_COUNT * 2,
        "predictions_sha256": base.sha256(ROOT / base.PREDICTIONS),
        "run_summary_sha256": base.sha256(ROOT / base.RUN_SUMMARY),
        "schedule_receipt_sha256": base.sha256(schedule_path),
        "all_predictions_terminal_before_private_population_evaluator_or_quality_read": True,
        "private_population_provenance_path_opened_or_hashed": False,
        "evaluator_called": False,
    }
    freeze["freeze_payload_sha256"] = base.payload_sha256(freeze)
    base._publish(ROOT / base.PREDICTION_FREEZE, freeze)
    return aggregate(
        task_rows,
        request_receipts,
        experiment_wall_seconds=summary["experiment_wall_seconds"],
        predictions_sha256=base.sha256(ROOT / base.PREDICTIONS),
        freeze_sha256=base.sha256(ROOT / base.PREDICTION_FREEZE),
        schedule_receipt_sha256=base.sha256(schedule_path),
    )


base.run_experiment = run_experiment


def successor_bindings() -> dict[str, Any]:
    diagnosis = base._read(ROOT, PARENT_DIAGNOSIS)
    population = _population(ROOT)
    policy = _policy()
    return {
        "parent_diagnosis_sha256": base.sha256(ROOT / PARENT_DIAGNOSIS),
        "parent_diagnosis_seal_valid": base._sealed(
            diagnosis, "diagnosis_payload_sha256"
        ),
        "same_population_retry_authorized": diagnosis.get(
            "authorization", {}
        ).get("same_population_retry_resume_or_selective_rerun"),
        "fresh_scheduler_design_authorized": diagnosis.get(
            "authorization", {}
        ).get("fresh_host_local_scheduler_successor_design"),
        "population_sha256": base.sha256(ROOT / POPULATION),
        "population_seal_valid": base._sealed(population, "design_payload_sha256"),
        "policy_sha256": base.sha256(ROOT / POLICY),
        "policy_seal_valid": base._sealed(policy, "policy_payload_sha256"),
        "task_count": len(base._tasks()),
        "request_count": len(base._request_vector()),
        "fresh_url_vector_disjoint_from_v24748": set(base._request_vector()).isdisjoint(
            helper.PRIOR_ALLOWED_URLS
        ),
        "crossref_max_inflight": HOST_MAX_INFLIGHT[runtime.CROSSREF_HOST],
        "crossref_minimum_start_interval_seconds": HOST_MINIMUM_START_INTERVAL[
            runtime.CROSSREF_HOST
        ],
        "attempts_per_url": 1,
        "experiment_wall_ceiling_seconds": base.EXPERIMENT_WALL_CEILING_SECONDS,
    }


COMMANDS = base.COMMANDS


if __name__ == "__main__":
    bindings = successor_bindings()
    if (
        bindings["parent_diagnosis_seal_valid"] is not True
        or bindings["same_population_retry_authorized"] is not False
        or bindings["fresh_scheduler_design_authorized"] is not True
        or bindings["population_seal_valid"] is not True
        or bindings["policy_seal_valid"] is not True
        or bindings["fresh_url_vector_disjoint_from_v24748"] is not True
        or bindings["task_count"] != 6
        or bindings["request_count"] != 32
        or bindings["crossref_max_inflight"] != 1
        or bindings["crossref_minimum_start_interval_seconds"] != 1.1
        or bindings["attempts_per_url"] != 1
        or bindings["experiment_wall_ceiling_seconds"] != 40.0
    ):
        raise RuntimeError("V2.47.52 successor binding drifted")
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(
            "usage: v24752_host_local_gate.py "
            "{protocol|preaudit|activate|start|run|postaudit}"
        )
    COMMANDS[sys.argv[1]]()
