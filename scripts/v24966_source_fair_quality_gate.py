#!/usr/bin/env python3
"""Fresh paired quality gate for cumulative registrable-source ordering.

The two arms replay the same hosted-search responses, fetch one task-local URL
union exactly once, receive the same fixed evidence-character budget, and use
the same GPT-5.6 synthesis prompt and output cap.  All predictions are frozen
before the evaluator opens the predeclared PyPI JSON endpoints.  No
DeepWideBench artifact, label, mapping, gold, evaluator, score, or historical
per-task outcome is available to the forward path.
"""

from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import SearchRequestError, canonicalize_url  # noqa: E402
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    parse_task_union_single_shot,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24959_source_fair_discovery import (  # noqa: E402
    order_source_fair_leads,
)
from deepwide_agent.v24961_cumulative_source_fair import (  # noqa: E402
    compare_cumulative_prefixes,
)
from scripts import v24962_cumulative_source_fair_live_gate as source_gate  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260809"
PROTOCOL_ID = "v24966_fresh_pypi_cumulative_source_fair_quality_gate_v1"
BUILD_AUDIT = Path(f"results/v24966_source_fair_quality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24966_source_fair_quality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24966_source_fair_quality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24966_source_fair_quality_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24966_source_fair_quality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24966_source_fair_quality_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(
    f"results/v24966_source_fair_quality_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v24966_source_fair_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24966_source_fair_quality_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24966_source_fair_quality_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_pypi_gold.json"
LEASE_PATH = source_gate.LEASE_PATH
SCRIPT = Path("scripts/v24966_source_fair_quality_gate.py")

ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
CONTROL = "stable_first_seen"
CANDIDATE = "cumulative_source_fair"
ARMS = (CONTROL, CANDIDATE)
TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_CONCURRENCY = 8
QUERIES_PER_WAVE = 2
WAVE_FETCH_CAPS = (6, 4)
RESULTS_PER_QUERY = 3
EVIDENCE_CHARS = 24_000
MIN_USABLE_PAGES_PER_ARM = 6
TASK_DEADLINE_SECONDS = 240.0
MODEL_TIMEOUT_SECONDS = 90.0
MODEL_OUTPUT_TOKENS = 2_400
PYPI_TIMEOUT_SECONDS = 30.0

PACKAGES = (
    "pydantic-settings",
    "rich",
    "httpx",
    "typer",
    "hatchling",
    "poetry-core",
    "twine",
    "virtualenv",
    "pipx",
    "cibuildwheel",
    "maturin",
    "meson-python",
    "scikit-build-core",
    "pytest-xdist",
    "pytest-cov",
    "hypothesis",
    "cattrs",
    "msgspec",
    "orjson",
    "rapidfuzz",
)
QUERY_PATTERNS = (
    "{package} PyPI latest version release date Requires-Python",
    "{package} Python package latest release metadata",
    "{package} Requires-Python official package documentation",
    "{package} PyPI release history latest",
)
COLUMNS = (
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
)
FALLBACK_TABLE = (
    "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
    "|---|---|---|---|\n"
    "| Unknown | Unknown | Unknown | Unknown |"
)

SOURCES = (
    SCRIPT,
    Path("tests/test_v24966_source_fair_quality_gate.py"),
    Path("scripts/v24962_cumulative_source_fair_live_gate.py"),
    Path("scripts/v24960_source_fair_live_gate.py"),
    Path("src/deepwide_agent/v24961_cumulative_source_fair.py"),
    Path("src/deepwide_agent/v24959_source_fair_discovery.py"),
    Path("src/deepwide_agent/v24957_action_fair_discovery.py"),
    Path("src/deepwide_agent/v24280_task_union_single_shot.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24287_hard_deadline_fetch.py"),
    Path("scripts/deepwide_api_lease.py"),
)
TEST = Path("tests/test_v24966_source_fair_quality_gate.py")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)
FORBIDDEN_FORWARD_NAMES = frozenset(
    {
        "category",
        "question_type",
        "ground_truth",
        "answer_key",
        "benchmark_mapping",
        "benchmark_score",
        "historical_result",
        "_fetch_gold",
        "pypi_endpoint_vector",
        "evaluate_prediction",
        "evaluate_rows",
        "quality_decision",
        "run_evaluation",
        "gold_snapshot",
    }
)
_MODEL_SEMAPHORE = threading.BoundedSemaphore(MODEL_CONCURRENCY)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    value.pop(field, None)
    value[field] = payload_sha256(value)
    return value


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.66 requires clean pushed HEAD")


def _tracked(relative: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _ordinary(relative: Path, *, tracked: bool = False) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or tracked
        and not _tracked(relative)
    ):
        raise RuntimeError(f"V2.49.66 expected ordinary repository file: {relative}")
    return path


def _manifest(*, tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = _ordinary(relative, tracked=tracked)
        text = path.read_text(encoding="utf-8")
        if SECRET.search(text):
            raise RuntimeError(f"V2.49.66 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _read(relative: Path, *, tracked: bool = False) -> dict[str, Any]:
    value = json.loads(_ordinary(relative, tracked=tracked).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.66 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in _ordinary(relative, tracked=tracked)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.49.66 expected JSONL objects")
    return rows


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def expected_watchers() -> list[dict[str, Any]]:
    return source_gate.expected_watchers()


def _watchers() -> list[dict[str, Any]]:
    return source_gate._watchers()


def _lease_inactive() -> bool:
    return source_gate._lease_inactive()


def task_vector() -> tuple[dict[str, str], ...]:
    if len(PACKAGES) != TASK_COUNT or len(set(PACKAGES)) != TASK_COUNT:
        raise RuntimeError("V2.49.66 package population drifted")
    tasks: list[dict[str, str]] = []
    for package in PACKAGES:
        opaque = "task_" + hashlib.sha256(
            f"v24966-pypi-quality:{package}".encode("utf-8")
        ).hexdigest()[:24]
        question = (
            "Using only the supplied fetched pages, return exactly one Markdown "
            "table and no prose. Include exactly one row for the Python package "
            f"{package}. Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Use the canonical PyPI project name in Package. Latest release "
            "date means the earliest file upload date in the latest release, in "
            "YYYY-MM-DD form. Preserve the Requires-Python expression while "
            "collapsing whitespace. Use Unknown only when the supplied pages do "
            "not establish a value."
        )
        tasks.append({"opaque_id": opaque, "question": question})
    return tuple(tasks)


def arm_order_vector() -> tuple[tuple[str, str], ...]:
    """Freeze an exactly balanced order without inspecting task outcomes."""

    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: (
            hashlib.sha256(
                f"v24966-arm-order:{tasks[index]['opaque_id']}".encode()
            ).hexdigest(),
            index,
        ),
    )
    control_first = set(ranked[: TASK_COUNT // 2])
    return tuple(
        ARMS if index in control_first else ARMS[::-1]
        for index in range(TASK_COUNT)
    )


def query_vector() -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(pattern.format(package=package) for pattern in QUERY_PATTERNS)
        for package in PACKAGES
    )


def pypi_endpoint_vector() -> tuple[str, ...]:
    return tuple(f"https://pypi.org/pypi/{package}/json" for package in PACKAGES)


def source_policy() -> dict[str, bool]:
    return {
        "fresh_benchmark_external_pypi_population_only": True,
        "same_provider_payload_replayed_by_both_arms": True,
        "same_task_local_union_fetch_bytes_for_shared_urls": True,
        "same_evidence_character_budget_model_prompt_and_output_cap": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "forward_persists_no_query_url_host_title_page_or_provider_payload": True,
        "deepwidebench_manifest_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "pypi_gold_endpoint_opened_only_after_prediction_freeze": True,
        "credential_value_environment_or_keyring_read": False,
        "entropy_or_information_gain_used_for_selection_or_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
    }


def gates() -> dict[str, Any]:
    return {
        "task_count": TASK_COUNT,
        "logical_query_rows": TASK_COUNT * len(QUERY_PATTERNS),
        "search_provider_attempts": TASK_COUNT * 2,
        "search_provider_response_calls": TASK_COUNT * 2,
        "search_http_2xx": TASK_COUNT * 2,
        "minimum_selected_leads_per_arm": 180,
        "minimum_selected_leads_per_task_per_arm": 8,
        "minimum_selection_changed_tasks": 16,
        "minimum_source_gain_tasks": 12,
        "minimum_candidate_registrable_sources": 80,
        "minimum_candidate_over_control_source_ratio": 1.25,
        "minimum_usable_pages_per_arm": 120,
        "minimum_candidate_over_control_usable_page_ratio": 0.90,
        "evidence_chars_per_task_per_arm": EVIDENCE_CHARS,
        "model_attempts_per_arm": TASK_COUNT,
        "maximum_candidate_over_control_model_token_ratio": 1.10,
        "minimum_prediction_changed_tasks": 10,
        "maximum_failure_as_zero_tasks": 0,
        "maximum_transport_failures": 0,
        "maximum_search_deadline_failures": 0,
        "maximum_fetch_deadline_failures": 0,
        "maximum_fetch_helper_failures": 0,
        "maximum_fetch_deadline_rejections": 0,
        "gold_valid_tasks": TASK_COUNT,
        "quality_rule": (
            "candidate_exact_strictly_greater_and_entity_row_item_column_"
            "composite_all_nonregressing"
        ),
    }


def _run_tests() -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, "-I", "-B", str(TEST), "-v"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", process.stdout)
    return {
        "returncode": process.returncode,
        "observed": int(match.group(1)) if match else 0,
        "passed": process.returncode == 0,
    }


def _forward_ast_safe() -> bool:
    source = _ordinary(SCRIPT).read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"_run_task", "run_forward"}
    ]
    names = {
        node.id.casefold()
        for function in functions
        for node in ast.walk(function)
        if isinstance(node, ast.Name)
    }
    return len(functions) == 2 and not names.intersection(FORBIDDEN_FORWARD_NAMES)


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    manifest = _manifest(tracked=require_clean)
    tests = _run_tests()
    checks = {
        "focused_tests_pass": tests["passed"] and tests["observed"] >= 10,
        "source_manifest_complete": len(manifest) == len(SOURCES),
        "forward_ast_has_no_privileged_runtime_names": _forward_ast_safe(),
        "credential_literal_scan_clean": True,
        "fresh_task_and_query_vectors_fixed": len(task_vector()) == TASK_COUNT
        and len(query_vector()) == TASK_COUNT,
        "public_benchmark_launch_not_authorized": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "tests": tests,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": source_policy(),
        "authorization": {
            "protocol_publication": not findings,
            "external_forward": False,
            "evaluator": False,
            "public_exact220_or_sota": False,
        },
    }
    return _seal(value, "audit_payload_sha256")


def validate_build_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24966_source_fair_quality_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("public_exact220_or_sota") is not False
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 build audit drifted")
    return copied


def build_protocol(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_pristine: bool = True,
    require_build: bool = True,
) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    if require_build:
        validate_build_audit(_read(BUILD_AUDIT, tracked=require_clean))
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            PROTOCOL,
            PREAUDIT,
            EXECUTION_START,
            FORWARD_RESULT,
            FORWARD_AUDIT,
            EVALUATOR_PROTOCOL,
            RESULT,
            POSTAUDIT,
            OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.49.66 future surface is not pristine")
    manifest = _manifest(tracked=require_clean)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "population": {
            "kind": "fresh_public_pypi_metadata_tasks",
            "task_count": TASK_COUNT,
            "package_vector_sha256": payload_sha256(PACKAGES),
            "task_vector_sha256": payload_sha256(task_vector()),
            "query_vector_sha256": payload_sha256(query_vector()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "postfreeze_gold_endpoint_vector_sha256": payload_sha256(
                pypi_endpoint_vector()
            ),
            "disjoint_from_v24958_v24960_v24962_v24963_query_vectors": True,
        },
        "execution": {
            "control": CONTROL,
            "candidate": CANDIDATE,
            "only_treatment": "stable_first_seen_vs_cumulative_registrable_source_fair_order",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": MODEL_CONCURRENCY,
            "queries_per_wave": QUERIES_PER_WAVE,
            "wave_fetch_caps": list(WAVE_FETCH_CAPS),
            "same_search_response_replayed": True,
            "same_task_local_fetch_union": True,
            "same_fetched_bytes_for_shared_urls": True,
            "evidence_chars_per_arm": EVIDENCE_CHARS,
            "model": MODEL,
            "reasoning_effort": "low",
            "service_tier": "priority",
            "model_attempts_per_arm": 1,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "arm_call_order_exactly_balanced_by_preoutcome_opaque_hash_rank": True,
            "fixed_denominator_failure_as_zero": True,
        },
        "gates": gates(),
        "protected_watchers": expected_watchers(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_external_forward_after_preactivation_and_start": True,
            "evaluator_only_after_prediction_freeze_and_pushed_forward_audit": True,
            "public_exact220_or_other_benchmark_launch": False,
            "retry_resume_selective_rerun_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return _seal(value, "protocol_payload_sha256")


def validate_protocol(value: Mapping[str, Any], *, require_manifest: bool = True) -> dict[str, Any]:
    copied = dict(value)
    manifest = _manifest(tracked=True) if require_manifest else copied.get("source_manifest")
    execution = copied.get("execution") or {}
    population = copied.get("population") or {}
    if (
        copied.get("role") != "v24966_source_fair_quality_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or population.get("task_vector_sha256") != payload_sha256(task_vector())
        or population.get("query_vector_sha256") != payload_sha256(query_vector())
        or population.get("arm_order_vector_sha256")
        != payload_sha256(arm_order_vector())
        or population.get("postfreeze_gold_endpoint_vector_sha256")
        != payload_sha256(pypi_endpoint_vector())
        or execution.get("only_treatment")
        != "stable_first_seen_vs_cumulative_registrable_source_fair_order"
        or execution.get("same_search_response_replayed") is not True
        or execution.get("same_task_local_fetch_union") is not True
        or execution.get("evidence_chars_per_arm") != EVIDENCE_CHARS
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != expected_watchers()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get(
            "public_exact220_or_other_benchmark_launch"
        )
        is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL, tracked=True))
    validate_build_audit(_read(BUILD_AUDIT, tracked=True))
    tests = _run_tests()
    pristine = not any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            PREAUDIT,
            EXECUTION_START,
            FORWARD_RESULT,
            FORWARD_AUDIT,
            EVALUATOR_PROTOCOL,
            RESULT,
            POSTAUDIT,
            OUTPUT_ROOT,
        )
    )
    checks = {
        "protocol_valid": True,
        "focused_tests_pass": tests["passed"] and tests["observed"] >= 10,
        "future_surface_pristine": pristine,
        "protected_watchers_exact": _watchers() == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "forward_ast_has_no_privileged_runtime_names": _forward_ast_safe(),
        "gold_endpoints_not_opened": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "tests": tests,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "execution_start_generation": not findings,
            "external_forward": False,
            "evaluator": False,
            "public_exact220_or_sota": False,
        },
    }
    return _seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24966_source_fair_quality_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("execution_start_generation") is not True
        or copied.get("authorization", {}).get("public_exact220_or_sota") is not False
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL, tracked=True))
    preaudit = validate_preaudit(_read(PREAUDIT, tracked=True))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            EXECUTION_START,
            FORWARD_RESULT,
            FORWARD_AUDIT,
            EVALUATOR_PROTOCOL,
            RESULT,
            POSTAUDIT,
            OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.49.66 execution surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preactivation_audit_sha256": sha256(ROOT / PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "query_vector_sha256": protocol["population"]["query_vector_sha256"],
        "gold_endpoint_vector_sha256": protocol["population"][
            "postfreeze_gold_endpoint_vector_sha256"
        ],
        "prediction_output_surface_pristine": True,
        "gold_surface_pristine_and_unopened": True,
        "protected_watchers": _watchers(),
        "authorization": {
            "one_external_forward": True,
            "evaluator": False,
            "public_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return _seal(value, "execution_start_payload_sha256")


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24966_source_fair_quality_execution_start"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("authorization", {}).get("one_external_forward") is not True
        or copied.get("authorization", {}).get("evaluator") is not False
        or copied.get("authorization", {}).get("retry_resume_selective_rerun")
        is not False
        or copied.get("protected_watchers") != expected_watchers()
        or not _sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 execution start drifted")
    return copied


def _endpoint_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
        return False


def _client(deadline: float) -> Any:
    return source_gate.parent._client(deadline)


def _registrable_sources(leads: Sequence[Mapping[str, Any]]) -> set[str]:
    return source_gate.parent._registrable_sources(leads)


def _fetch_map(batches: object) -> dict[str, dict[str, Any]]:
    return source_gate.parent.base._fetch_map(batches)


def _extract_text(response: Mapping[str, Any]) -> str:
    chunks: list[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, Mapping):
            continue
        for content in item.get("content") or []:
            if (
                isinstance(content, Mapping)
                and content.get("type") in {"output_text", "text"}
                and isinstance(content.get("text"), str)
                and content["text"].strip()
            ):
                chunks.append(content["text"].strip())
    direct = response.get("output_text")
    if not chunks and isinstance(direct, str) and direct.strip():
        chunks.append(direct.strip())
    if not chunks:
        raise ValueError("V2.49.66 synthesis response contained no text")
    return "\n".join(chunks)


def _prompt(question: str, evidence: str) -> str:
    return (
        "Follow the visible task using only the supplied fetched-page text. "
        "Return exactly one Markdown table and no prose. Do not cite URLs. "
        "Do not add columns or rows.\n\nVISIBLE TASK:\n"
        + question
        + "\n\nFIXED-BUDGET FETCHED PAGES:\n"
        + evidence
    )


def _synthesize(
    question: str, evidence: str, *, absolute_deadline: float
) -> tuple[str, dict[str, int]]:
    payload = {
        "model": MODEL,
        "input": _prompt(question, evidence),
        "reasoning": {"effort": "low"},
        "service_tier": "priority",
        "max_output_tokens": MODEL_OUTPUT_TOKENS,
        "store": False,
    }
    started = time.monotonic()
    remaining = absolute_deadline - time.monotonic() - 5.0
    if remaining <= 0 or not _MODEL_SEMAPHORE.acquire(timeout=remaining):
        raise TimeoutError("V2.49.66 model slot deadline exhausted")
    try:
        remaining = absolute_deadline - time.monotonic() - 5.0
        if remaining <= 0:
            raise TimeoutError("V2.49.66 model request deadline exhausted")
        response = requests.post(
            ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=(min(5.0, remaining), min(MODEL_TIMEOUT_SECONDS, remaining)),
        )
    finally:
        _MODEL_SEMAPHORE.release()
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, Mapping):
        raise ValueError("V2.49.66 synthesis response drifted")
    usage = value.get("usage") if isinstance(value.get("usage"), Mapping) else {}
    return _extract_text(value), {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
        "provider_attempts": 1,
    }


def _build_evidence(
    leads: Sequence[Mapping[str, Any]], fetched: Mapping[str, Mapping[str, Any]]
) -> tuple[str, int, int]:
    sections: list[str] = []
    raw_chars = 0
    usable = 0
    for lead in leads:
        url = canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
        result = fetched.get(url) or {}
        text = str(result.get("raw_content") or result.get("content") or "").strip()
        if not text:
            continue
        usable += 1
        raw_chars += len(text)
        title = " ".join(str(result.get("title") or "Fetched page").split())
        sections.append(f"[PAGE {usable}]\nTITLE: {title}\nCONTENT:\n{text}\n")
    joined = "\n".join(sections)
    if usable < MIN_USABLE_PAGES_PER_ARM or len(joined) < EVIDENCE_CHARS:
        raise RuntimeError("V2.49.66 arm lacks fixed-budget usable evidence")
    return joined[:EVIDENCE_CHARS], usable, raw_chars


def _arm_order(opaque_id: str) -> tuple[str, str]:
    tasks = task_vector()
    indices = {
        str(task["opaque_id"]): index for index, task in enumerate(tasks)
    }
    if opaque_id not in indices:
        raise ValueError("V2.49.66 unknown arm-order key")
    return arm_order_vector()[indices[opaque_id]]


def _run_task(index: int) -> dict[str, Any]:
    task = task_vector()[index]
    deadline = time.monotonic() + TASK_DEADLINE_SECONDS
    client = _client(deadline)
    started = time.monotonic()
    selected: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    prior_urls: dict[str, set[str]] = {arm: set() for arm in ARMS}
    cumulative_sources: dict[str, set[str]] = {arm: set() for arm in ARMS}
    query_rows = 0
    completed_retrieval = True
    raw_action_groups = raw_action_sources = 0
    try:
        queries = query_vector()[index]
        for wave_index, cap in enumerate(WAVE_FETCH_CAPS):
            wave_queries = list(
                queries[
                    wave_index * QUERIES_PER_WAVE : (wave_index + 1)
                    * QUERIES_PER_WAVE
                ]
            )
            payload = client._request(wave_queries)
            batches, _complete, _normalized, _attachments = (
                parse_task_union_single_shot(
                    client, wave_queries, payload, max_results=RESULTS_PER_QUERY
                )
            )
            value = compare_cumulative_prefixes(
                batches,
                cap=cap,
                prior_control_urls=prior_urls[CONTROL],
                prior_candidate_urls=prior_urls[CANDIDATE],
                prior_control_sources=cumulative_sources[CONTROL],
                prior_candidate_sources=cumulative_sources[CANDIDATE],
            )
            _ordered, observation, _private = order_source_fair_leads(
                batches, prior_sources=cumulative_sources[CANDIDATE]
            )
            raw_action_groups += int(observation["raw_action_group_count"])
            raw_action_sources += int(observation["raw_action_source_count"])
            query_rows += len(wave_queries)
            for arm, key, source_key in (
                (CONTROL, "stable", "control_cumulative_sources"),
                (CANDIDATE, "candidate", "candidate_cumulative_sources"),
            ):
                leads = list(value[key])
                selected[arm].extend(leads)
                prior_urls[arm].update(
                    canonicalize_url(str(lead.get("url", ""))) for lead in leads
                )
                cumulative_sources[arm] = set(value[source_key])
    except (SearchRequestError, ValueError, RuntimeError, OSError):
        completed_retrieval = False

    union: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for arm in ARMS:
        for lead in selected[arm]:
            url = canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            union.append(
                {
                    "url": str(lead.get("fetch_url") or lead.get("url") or ""),
                    "query": "shared paired external quality fetch",
                    "title": str(lead.get("title", "")),
                    "member_label": "",
                }
            )
    fetched_batches: object = []
    if completed_retrieval and union:
        try:
            fetched_batches = client.fetch_urls(union)
        except (ValueError, RuntimeError, OSError):
            completed_retrieval = False
    fetched = _fetch_map(fetched_batches)
    evidence: dict[str, str] = {}
    usable_pages = {arm: 0 for arm in ARMS}
    usable_chars = {arm: 0 for arm in ARMS}
    if completed_retrieval:
        try:
            for arm in ARMS:
                evidence[arm], usable_pages[arm], usable_chars[arm] = _build_evidence(
                    selected[arm], fetched
                )
        except RuntimeError:
            completed_retrieval = False

    final_sources = {arm: _registrable_sources(selected[arm]) for arm in ARMS}
    if completed_retrieval and (
        final_sources[CONTROL] != cumulative_sources[CONTROL]
        or final_sources[CANDIDATE] != cumulative_sources[CANDIDATE]
        or len(final_sources[CANDIDATE]) < len(final_sources[CONTROL])
    ):
        completed_retrieval = False

    predictions: dict[str, str] = {}
    model_usage: dict[str, dict[str, int]] = {}
    model_success = {arm: False for arm in ARMS}
    if completed_retrieval:
        for arm in _arm_order(str(task["opaque_id"])):
            try:
                predictions[arm], model_usage[arm] = _synthesize(
                    str(task["question"]), evidence[arm], absolute_deadline=deadline
                )
                model_success[arm] = True
            except TimeoutError:
                model_usage[arm] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "elapsed_milliseconds": 0,
                    "provider_attempts": 0,
                }
            except (requests.RequestException, ValueError, RuntimeError, OSError):
                model_usage[arm] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "elapsed_milliseconds": 0,
                    "provider_attempts": 1,
                }
    completed = completed_retrieval and all(model_success.values())
    if not completed:
        predictions = {arm: FALLBACK_TABLE for arm in ARMS}

    health = validate_transport_health(client.transport_health())
    statuses = dict(client.status_counts)
    selected_urls = {
        arm: [
            canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
            for lead in selected[arm]
        ]
        for arm in ARMS
    }
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_task_result",
        "protocol_id": PROTOCOL_ID,
        "opaque_id": task["opaque_id"],
        "status": "completed" if completed else "failure_as_zero",
        "runtime_input_keys": ["opaque_id", "question"],
        "terminal": True,
        "completed": completed,
        "failure_as_zero": not completed,
        "logical_query_rows": query_rows,
        "search_provider_attempts": int(client.hosted_search_attempts),
        "search_provider_response_calls": int(client.calls),
        "search_http_2xx": sum(
            count for status, count in statuses.items() if 200 <= status < 300
        ),
        "transport_failures": int(client.transport_failures),
        "hosted_search_deadline_failures": int(
            client.transport_health()["hosted_search_deadline_failures"]
        ),
        "raw_action_group_count": raw_action_groups,
        "raw_action_source_count": raw_action_sources,
        "selected_leads": {arm: len(selected[arm]) for arm in ARMS},
        "selection_changed": selected_urls[CONTROL] != selected_urls[CANDIDATE],
        "registrable_sources": {arm: len(final_sources[arm]) for arm in ARMS},
        "source_coverage_gain": max(
            0, len(final_sources[CANDIDATE]) - len(final_sources[CONTROL])
        ),
        "usable_pages": usable_pages,
        "usable_chars": usable_chars,
        "evidence_chars": {
            arm: len(evidence.get(arm, "")) if completed_retrieval else 0
            for arm in ARMS
        },
        "planned_union_fetches": len(union),
        "actual_hard_fetch_helper_calls": int(health["hard_fetch_helper_calls"]),
        "hard_fetch_deadline_failures": int(health["hard_fetch_deadline_failures"]),
        "fetch_helper_failures": int(health["fetch_helper_failures"]),
        "fetch_deadline_rejections": int(
            client.transport_health()["fetch_deadline_rejections"]
        ),
        "search_usage": {
            "input_tokens": int(client.input_tokens),
            "output_tokens": int(client.output_tokens),
            "total_tokens": int(client.total_tokens),
        },
        "model_success": model_success,
        "model_usage": model_usage,
        "predictions": predictions,
        "prediction_sha256": {
            arm: payload_sha256(predictions[arm]) for arm in ARMS
        },
        "prediction_changed": predictions[CONTROL] != predictions[CANDIDATE],
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "same_provider_payload_replayed_by_both_arms": True,
        "same_task_local_union_fetch_bytes_for_shared_urls": True,
        "same_evidence_character_budget_model_prompt_and_output_cap": True,
        "model_attempt_count_matched": int(
            (model_usage.get(CONTROL) or {}).get("provider_attempts", 0)
        )
        == int((model_usage.get(CANDIDATE) or {}).get("provider_attempts", 0)),
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "pypi_gold_endpoint_opened": False,
        "entropy_or_information_gain_assigns_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
        "contains_query_url_host_title_page_or_provider_payload": False,
    }
    row["result_payload_sha256"] = payload_sha256(row)
    return row


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(
        0,
        min(len(ordered) - 1, int(probability * len(ordered) + 0.999999) - 1),
    )
    return round(ordered[index], 6)


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, batch_wall_seconds: float
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    walls: list[float] = []
    minimum_selected = {arm: [] for arm in ARMS}
    for row in rows:
        walls.append(float(row.get("wall_seconds", 0.0)))
        selected = row.get("selected_leads") or {}
        for arm in ARMS:
            minimum_selected[arm].append(int(selected.get(arm, 0)))
        counters["terminal"] += int(bool(row.get("terminal")))
        counters["completed"] += int(bool(row.get("completed")))
        counters["failure_as_zero"] += int(bool(row.get("failure_as_zero")))
        counters["logical_query_rows"] += int(row.get("logical_query_rows", 0))
        for name in (
            "search_provider_attempts",
            "search_provider_response_calls",
            "search_http_2xx",
            "transport_failures",
            "hosted_search_deadline_failures",
            "raw_action_group_count",
            "raw_action_source_count",
            "planned_union_fetches",
            "actual_hard_fetch_helper_calls",
            "hard_fetch_deadline_failures",
            "fetch_helper_failures",
            "fetch_deadline_rejections",
        ):
            counters[name] += int(row.get(name, 0))
        counters["selection_changed"] += int(bool(row.get("selection_changed")))
        counters["prediction_changed"] += int(bool(row.get("prediction_changed")))
        counters["source_gain_task"] += int(int(row.get("source_coverage_gain", 0)) > 0)
        counters["source_coverage_gain"] += int(row.get("source_coverage_gain", 0))
        for arm in ARMS:
            counters[f"{arm}_selected_leads"] += int(
                (row.get("selected_leads") or {}).get(arm, 0)
            )
            counters[f"{arm}_registrable_sources"] += int(
                (row.get("registrable_sources") or {}).get(arm, 0)
            )
            counters[f"{arm}_usable_pages"] += int(
                (row.get("usable_pages") or {}).get(arm, 0)
            )
            counters[f"{arm}_usable_chars"] += int(
                (row.get("usable_chars") or {}).get(arm, 0)
            )
            counters[f"{arm}_evidence_chars"] += int(
                (row.get("evidence_chars") or {}).get(arm, 0)
            )
            counters[f"{arm}_model_success"] += int(
                bool((row.get("model_success") or {}).get(arm))
            )
            usage = (row.get("model_usage") or {}).get(arm) or {}
            counters[f"{arm}_model_attempts"] += int(
                usage.get("provider_attempts", 0)
            )
            counters[f"{arm}_model_input_tokens"] += int(
                usage.get("input_tokens", 0)
            )
            counters[f"{arm}_model_output_tokens"] += int(
                usage.get("output_tokens", 0)
            )
        search_usage = row.get("search_usage") or {}
        counters["search_input_tokens"] += int(search_usage.get("input_tokens", 0))
        counters["search_output_tokens"] += int(search_usage.get("output_tokens", 0))
    return {
        **{name: int(counters[name]) for name in sorted(counters)},
        "terminal_task_count": int(counters["terminal"]),
        "completed_task_count": int(counters["completed"]),
        "failure_as_zero_task_count": int(counters["failure_as_zero"]),
        "selection_changed_task_count": int(counters["selection_changed"]),
        "prediction_changed_task_count": int(counters["prediction_changed"]),
        "source_coverage_gain_task_count": int(counters["source_gain_task"]),
        "minimum_selected_leads_per_task": {
            arm: min(values, default=0) for arm, values in minimum_selected.items()
        },
        "task_wall_p50_seconds": _percentile(walls, 0.50),
        "task_wall_p95_seconds": _percentile(walls, 0.95),
        "task_wall_max_seconds": round(max(walls, default=0.0), 6),
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "contains_query_url_host_title_page_answer_provider_payload_selection_or_per_task_score": False,
    }


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    gate = gates()
    control_sources = float(aggregate.get(f"{CONTROL}_registrable_sources", 0))
    candidate_sources = float(aggregate.get(f"{CANDIDATE}_registrable_sources", 0))
    control_pages = float(aggregate.get(f"{CONTROL}_usable_pages", 0))
    candidate_pages = float(aggregate.get(f"{CANDIDATE}_usable_pages", 0))
    control_model_tokens = float(
        aggregate.get(f"{CONTROL}_model_input_tokens", 0)
    ) + float(aggregate.get(f"{CONTROL}_model_output_tokens", 0))
    candidate_model_tokens = float(
        aggregate.get(f"{CANDIDATE}_model_input_tokens", 0)
    ) + float(aggregate.get(f"{CANDIDATE}_model_output_tokens", 0))
    checks = {
        "all_tasks_terminal": aggregate.get("terminal_task_count") == TASK_COUNT,
        "all_tasks_completed": aggregate.get("completed_task_count") == TASK_COUNT,
        "no_failure_as_zero": aggregate.get("failure_as_zero_task_count")
        <= gate["maximum_failure_as_zero_tasks"],
        "all_logical_queries_committed": aggregate.get("logical_query_rows")
        == gate["logical_query_rows"],
        "exact_search_attempts": aggregate.get("search_provider_attempts")
        == gate["search_provider_attempts"],
        "exact_search_responses": aggregate.get("search_provider_response_calls")
        == gate["search_provider_response_calls"],
        "all_search_responses_2xx": aggregate.get("search_http_2xx")
        == gate["search_http_2xx"],
        "no_transport_failures": aggregate.get("transport_failures", 1) == 0,
        "no_search_deadline_failures": aggregate.get(
            "hosted_search_deadline_failures", 1
        )
        == 0,
        "matched_total_selection": all(
            aggregate.get(f"{arm}_selected_leads", 0)
            >= gate["minimum_selected_leads_per_arm"]
            for arm in ARMS
        ),
        "matched_minimum_selection": all(
            int((aggregate.get("minimum_selected_leads_per_task") or {}).get(arm, 0))
            >= gate["minimum_selected_leads_per_task_per_arm"]
            for arm in ARMS
        ),
        "selection_changed_enough_tasks": aggregate.get(
            "selection_changed_task_count", 0
        )
        >= gate["minimum_selection_changed_tasks"],
        "source_gain_reaches_enough_tasks": aggregate.get(
            "source_coverage_gain_task_count", 0
        )
        >= gate["minimum_source_gain_tasks"],
        "candidate_absolute_source_capability": candidate_sources
        >= gate["minimum_candidate_registrable_sources"],
        "candidate_source_ratio": candidate_sources
        >= control_sources * gate["minimum_candidate_over_control_source_ratio"],
        "both_arms_have_usable_pages": all(
            aggregate.get(f"{arm}_usable_pages", 0)
            >= gate["minimum_usable_pages_per_arm"]
            for arm in ARMS
        ),
        "candidate_usable_pages_bounded": candidate_pages
        >= control_pages * gate["minimum_candidate_over_control_usable_page_ratio"],
        "fixed_evidence_character_budget": all(
            aggregate.get(f"{arm}_evidence_chars", 0) == TASK_COUNT * EVIDENCE_CHARS
            for arm in ARMS
        ),
        "exact_model_attempts_and_successes": all(
            aggregate.get(f"{arm}_model_attempts", 0) == TASK_COUNT
            and aggregate.get(f"{arm}_model_success", 0) == TASK_COUNT
            for arm in ARMS
        ),
        "candidate_model_token_cost_bounded": control_model_tokens > 0
        and candidate_model_tokens
        <= control_model_tokens
        * gate["maximum_candidate_over_control_model_token_ratio"],
        "prediction_changes_enough_tasks": aggregate.get(
            "prediction_changed_task_count", 0
        )
        >= gate["minimum_prediction_changed_tasks"],
        "planned_union_equals_actual_helpers": aggregate.get(
            "planned_union_fetches"
        )
        == aggregate.get("actual_hard_fetch_helper_calls"),
        "no_fetch_failures": aggregate.get("hard_fetch_deadline_failures", 1) == 0
        and aggregate.get("fetch_helper_failures", 1) == 0
        and aggregate.get("fetch_deadline_rejections", 1) == 0,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "mechanism_gate_passed": passed,
        "postfreeze_external_evaluator_authorized": passed,
        "public_exact220_authorized": False,
    }


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    predictions = copied.get("predictions") or {}
    completed = copied.get("completed") is True
    expected_attempt_match = int(
        ((copied.get("model_usage") or {}).get(CONTROL) or {}).get(
            "provider_attempts", 0
        )
    ) == int(
        ((copied.get("model_usage") or {}).get(CANDIDATE) or {}).get(
            "provider_attempts", 0
        )
    )
    if (
        copied.get("role") != "v24966_source_fair_quality_task_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("runtime_input_keys") != ["opaque_id", "question"]
        or copied.get("terminal") is not True
        or set(predictions) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or copied.get("same_provider_payload_replayed_by_both_arms") is not True
        or copied.get("same_task_local_union_fetch_bytes_for_shared_urls") is not True
        or copied.get("same_evidence_character_budget_model_prompt_and_output_cap")
        is not True
        or copied.get("model_attempt_count_matched") is not expected_attempt_match
        or completed
        and copied.get("model_attempt_count_matched") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read")
        is not False
        or copied.get("pypi_gold_endpoint_opened") is not False
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get("retry_resume_skip_or_selective_rerun") is not False
        or copied.get("contains_query_url_host_title_page_or_provider_payload") is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 task result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL, tracked=True))
    validate_start(_read(EXECUTION_START, tracked=True))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            FORWARD_RESULT,
            FORWARD_AUDIT,
            EVALUATOR_PROTOCOL,
            RESULT,
            POSTAUDIT,
            OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.49.66 forward surface is not pristine")
    if not _endpoint_reachable():
        raise RuntimeError("V2.49.66 keyless GPT-5.6 endpoint unavailable")
    watchers_before = _watchers()
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v24966_source_fair_quality",
        purpose="fresh_paired_external_source_fair_quality_gate",
        path=ROOT / LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_run_task, range(TASK_COUNT)))
    batch_wall = time.monotonic() - started
    rows = [validate_task_row(row) for row in rows]
    rows.sort(key=lambda row: str(row["opaque_id"]))
    aggregate = aggregate_rows(rows, batch_wall_seconds=batch_wall)
    decision = mechanism_decision(aggregate)
    _publish_jsonl(ROOT / TASK_ROWS, rows)
    freeze: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "task_rows_sha256": sha256(ROOT / TASK_ROWS),
        "terminal_tasks": len(rows),
        "terminal_arm_predictions": len(rows) * len(ARMS),
        "all_predictions_terminal_before_pypi_gold_or_evaluator_open": True,
        "pypi_gold_endpoint_calls_before_freeze": 0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    _seal(freeze, "freeze_payload_sha256")
    _publish(ROOT / PREDICTION_FREEZE, freeze)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "task_rows_sha256": sha256(ROOT / TASK_ROWS),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "aggregate": aggregate,
        "mechanism_decision": decision,
        "protected_watchers_before": watchers_before,
        "protected_watchers_after": _watchers(),
        "all_predictions_terminal_before_pypi_gold_or_evaluator_open": True,
        "source_policy": protocol["source_policy"],
        "authorization": {
            "forward_audit_generation": True,
            "postfreeze_external_evaluator_protocol": False,
            "public_exact220_or_other_benchmark_launch": False,
            "retry_resume_selective_rerun_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    _seal(value, "result_payload_sha256")
    _publish(ROOT / FORWARD_RESULT, value)
    return value


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24966_source_fair_quality_forward_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("all_predictions_terminal_before_pypi_gold_or_evaluator_open")
        is not True
        or copied.get("protected_watchers_before") != expected_watchers()
        or copied.get("protected_watchers_after") != expected_watchers()
        or copied.get("mechanism_decision")
        != mechanism_decision(copied.get("aggregate") or {})
        or copied.get("authorization", {}).get(
            "public_exact220_or_other_benchmark_launch"
        )
        is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 forward result drifted")
    return copied


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL, tracked=True))
    forward = validate_forward_result(_read(FORWARD_RESULT))
    rows = [validate_task_row(row) for row in _read_jsonl(TASK_ROWS)]
    aggregate = aggregate_rows(
        rows, batch_wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
    )
    decision = mechanism_decision(aggregate)
    forbidden_keys = {
        "query",
        "url",
        "host",
        "title",
        "page",
        "provider_payload",
        "category",
        "question_type",
        "gold",
        "score",
        "reward",
    }
    row_keys = {key for row in rows for key in row}
    freeze = _read(PREDICTION_FREEZE)
    checks = {
        "protocol_and_forward_validate": True,
        "exact_task_denominator": len(rows) == TASK_COUNT
        and len({row["opaque_id"] for row in rows}) == TASK_COUNT,
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision
        == forward["mechanism_decision"],
        "task_rows_contain_no_forbidden_content_keys": not row_keys.intersection(
            forbidden_keys
        ),
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == sha256(ROOT / TASK_ROWS),
        "prediction_freeze_valid": _sealed(freeze, "freeze_payload_sha256"),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == sha256(ROOT / PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256")
        == sha256(ROOT / TASK_ROWS),
        "gold_surface_absent": not (ROOT / GOLD_SNAPSHOT).exists()
        and not (ROOT / GOLD_SNAPSHOT).is_symlink(),
        "protected_watchers_unchanged": _watchers()
        == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "no_public_benchmark_authority": forward["authorization"][
            "public_exact220_or_other_benchmark_launch"
        ]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    audit_valid = not findings
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_forward_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "task_rows_sha256": sha256(ROOT / TASK_ROWS),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "checks": checks,
        "mechanism_decision": decision,
        "findings": findings,
        "audit_valid": audit_valid,
        "source_policy": source_policy(),
        "authorization": {
            "postfreeze_external_evaluator_protocol": audit_valid
            and decision["mechanism_gate_passed"],
            "public_exact220_or_other_benchmark_launch": False,
            "retry_resume_selective_rerun_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return _seal(value, "audit_payload_sha256")


def validate_forward_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    expected_evaluator_authority = (
        copied.get("audit_valid") is True
        and copied.get("mechanism_decision", {}).get("mechanism_gate_passed") is True
    )
    if (
        copied.get("role") != "v24966_source_fair_quality_forward_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol"
        )
        is not expected_evaluator_authority
        or copied.get("authorization", {}).get(
            "public_exact220_or_other_benchmark_launch"
        )
        is not False
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 forward audit drifted")
    return copied


def build_evaluator_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_protocol(_read(PROTOCOL, tracked=True))
    forward = validate_forward_result(_read(FORWARD_RESULT, tracked=True))
    audit = validate_forward_audit(_read(FORWARD_AUDIT, tracked=True))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (EVALUATOR_PROTOCOL, RESULT, POSTAUDIT, GOLD_SNAPSHOT)
    ):
        raise RuntimeError("V2.49.66 evaluator surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_evaluator_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "task_rows_sha256": forward["task_rows_sha256"],
        "gold_endpoint_vector_sha256": payload_sha256(pypi_endpoint_vector()),
        "gold_rule": {
            "latest_version": "pypi_info_version",
            "latest_release_date": "earliest_upload_date_among_files_under_info_version",
            "requires_python": "pypi_info_requires_python_or_Unknown",
            "one_http_attempt_per_package": True,
            "fixed_denominator_failure_as_zero": True,
        },
        "primary_comparison": f"{CANDIDATE}_minus_{CONTROL}",
        "go_rule": gates()["quality_rule"],
        "authorization": {
            "one_postfreeze_external_evaluation": True,
            "public_exact220_or_other_benchmark_launch": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    if audit["mechanism_decision"]["mechanism_gate_passed"] is not True:
        raise RuntimeError("V2.49.66 mechanism gate did not authorize evaluation")
    if (
        audit["authorization"]["postfreeze_external_evaluator_protocol"]
        is not True
    ):
        raise RuntimeError("V2.49.66 forward audit withheld evaluator authority")
    return _seal(value, "protocol_payload_sha256")


def validate_evaluator_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24966_source_fair_quality_evaluator_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("gold_endpoint_vector_sha256")
        != payload_sha256(pypi_endpoint_vector())
        or copied.get("go_rule") != gates()["quality_rule"]
        or copied.get("authorization", {}).get("one_postfreeze_external_evaluation")
        is not True
        or copied.get("authorization", {}).get(
            "public_exact220_or_other_benchmark_launch"
        )
        is not False
        or copied.get("authorization", {}).get("selective_retry_or_revaluation")
        is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 evaluator protocol drifted")
    return copied


def _normalize_package(value: object) -> str:
    return re.sub(r"[-_.]+", "-", " ".join(str(value).split()).casefold())


def _normalize_value(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _normalize_requires_python(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).casefold()


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [
        line.strip()
        for line in str(text).splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(lines) < 2:
        return [], []
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    columns = cells[0]
    rows = [row for row in cells[2:] if len(row) == len(columns)]
    return columns, rows


def evaluate_prediction(prediction: str, gold: Mapping[str, str]) -> dict[str, float | int]:
    columns, rows = _matrix(prediction)
    exact_columns = columns == list(COLUMNS)
    if not exact_columns:
        rows = []
    expected_key = _normalize_package(gold["package"])
    predicted = {
        _normalize_package(row[0]): row
        for row in rows
        if len(row) == len(COLUMNS) and _normalize_package(row[0])
    }
    true_entities = int(expected_key in predicted)
    entity_precision = true_entities / len(predicted) if predicted else 0.0
    entity_recall = float(true_entities)
    row_f1 = (
        2 * entity_precision * entity_recall / (entity_precision + entity_recall)
        if entity_precision + entity_recall
        else 0.0
    )
    item_true = 0
    if expected_key in predicted:
        row = predicted[expected_key]
        item_true += int(_normalize_value(row[1]) == _normalize_value(gold["version"]))
        item_true += int(_normalize_value(row[2]) == _normalize_value(gold["date"]))
        item_true += int(
            _normalize_requires_python(row[3])
            == _normalize_requires_python(gold["requires_python"])
        )
    predicted_items = len(predicted) * 3
    precision = item_true / predicted_items if predicted_items else 0.0
    recall = item_true / 3
    item_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    exact = int(
        exact_columns
        and len(rows) == 1
        and list(predicted) == [expected_key]
        and item_true == 3
    )
    column_f1 = 1.0 if exact_columns else 0.0
    return {
        "exact_table_success": exact,
        "entity_recall": entity_recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": (entity_recall + row_f1 + item_f1 + column_f1) / 4,
    }


def _fetch_gold(index: int) -> dict[str, Any]:
    package = PACKAGES[index]
    opaque_id = task_vector()[index]["opaque_id"]
    endpoint = pypi_endpoint_vector()[index]
    try:
        response = requests.get(
            endpoint,
            headers={"User-Agent": "deepwide-v24966/1.0"},
            timeout=(5.0, PYPI_TIMEOUT_SECONDS),
        )
        raw = bytes(response.content)
        response.raise_for_status()
        value = response.json()
        info = value.get("info") if isinstance(value, Mapping) else None
        releases = value.get("releases") if isinstance(value, Mapping) else None
        if not isinstance(info, Mapping) or not isinstance(releases, Mapping):
            raise ValueError("PyPI response schema drifted")
        version = str(info.get("version") or "").strip()
        files = releases.get(version)
        if not version or not isinstance(files, list) or not files:
            raise ValueError("PyPI latest release files absent")
        dates = sorted(
            str(item.get("upload_time_iso_8601") or item.get("upload_time") or "")[:10]
            for item in files
            if isinstance(item, Mapping)
            and str(item.get("upload_time_iso_8601") or item.get("upload_time") or "")[:10]
        )
        if not dates or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dates[0]):
            raise ValueError("PyPI latest release date absent")
        canonical_name = str(info.get("name") or package).strip()
        requires_python = str(info.get("requires_python") or "Unknown").strip()
        return {
            "opaque_id": opaque_id,
            "requested_package": package,
            "package": canonical_name,
            "version": version,
            "date": dates[0],
            "requires_python": requires_python,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "http_status": int(response.status_code),
            "valid": True,
            "provider_attempts": 1,
        }
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError):
        return {
            "opaque_id": opaque_id,
            "requested_package": package,
            "package": package,
            "version": "Unknown",
            "date": "Unknown",
            "requires_python": "Unknown",
            "response_sha256": "",
            "http_status": 0,
            "valid": False,
            "provider_attempts": 1,
        }


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], gold_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    gold = {str(row["opaque_id"]): dict(row) for row in gold_rows}
    if len(gold) != TASK_COUNT:
        raise RuntimeError("V2.49.66 gold denominator drifted")
    metrics = {arm: [] for arm in ARMS}
    seen: set[str] = set()
    invalid = 0
    for raw in rows:
        row = validate_task_row(raw)
        opaque = str(row["opaque_id"])
        if opaque in seen or opaque not in gold:
            raise RuntimeError("V2.49.66 prediction/gold identity drifted")
        seen.add(opaque)
        if not gold[opaque]["valid"]:
            invalid += 1
            zero = {
                "exact_table_success": 0,
                "entity_recall": 0.0,
                "row_f1": 0.0,
                "item_f1": 0.0,
                "column_f1": 0.0,
                "composite": 0.0,
            }
            for arm in ARMS:
                metrics[arm].append(dict(zero))
        else:
            for arm in ARMS:
                metrics[arm].append(
                    evaluate_prediction(str(row["predictions"][arm]), gold[opaque])
                )
    if len(seen) != TASK_COUNT:
        raise RuntimeError("V2.49.66 evaluation denominator drifted")
    aggregate: dict[str, Any] = {}
    for arm in ARMS:
        aggregate[arm] = {
            "tasks": TASK_COUNT,
            "evaluator_valid": TASK_COUNT - invalid,
            "evaluator_invalid_or_not_run": invalid,
            "exact_table_successes": sum(
                int(row["exact_table_success"]) for row in metrics[arm]
            ),
            **{
                key: sum(float(row[key]) for row in metrics[arm]) / TASK_COUNT
                for key in (
                    "entity_recall",
                    "row_f1",
                    "item_f1",
                    "column_f1",
                    "composite",
                )
            },
        }
    delta = {
        key: aggregate[CANDIDATE][key] - aggregate[CONTROL][key]
        for key in (
            "exact_table_successes",
            "entity_recall",
            "row_f1",
            "item_f1",
            "column_f1",
            "composite",
            "evaluator_invalid_or_not_run",
        )
    }
    return {"arms": aggregate, f"{CANDIDATE}_minus_{CONTROL}": delta}


def quality_decision(
    metrics: Mapping[str, Any], mechanism: Mapping[str, Any]
) -> dict[str, Any]:
    delta = metrics.get(f"{CANDIDATE}_minus_{CONTROL}") or {}
    arms = metrics.get("arms") or {}
    checks = {
        "mechanism_gate_passed": mechanism.get("mechanism_gate_passed") is True,
        "all_gold_tasks_valid": all(
            (arms.get(arm) or {}).get("evaluator_valid") == TASK_COUNT for arm in ARMS
        ),
        "candidate_exact_strictly_improves": float(
            delta.get("exact_table_successes", -1)
        )
        > 0,
        "entity_nonregression": float(delta.get("entity_recall", -1)) >= 0,
        "row_nonregression": float(delta.get("row_f1", -1)) >= 0,
        "item_nonregression": float(delta.get("item_f1", -1)) >= 0,
        "column_nonregression": float(delta.get("column_f1", -1)) >= 0,
        "composite_nonregression": float(delta.get("composite", -1)) >= 0,
        "evaluator_invalid_not_increased": float(
            delta.get("evaluator_invalid_or_not_run", 1)
        )
        <= 0,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "source_fair_quality_gate_go": passed,
        "public_exact220_candidate_design_authorized": passed,
        "public_exact220_launch_authorized": False,
    }


def run_evaluation() -> dict[str, Any]:
    _clean_pushed()
    evaluator = validate_evaluator_protocol(_read(EVALUATOR_PROTOCOL, tracked=True))
    forward = validate_forward_result(_read(FORWARD_RESULT, tracked=True))
    audit = validate_forward_audit(_read(FORWARD_AUDIT, tracked=True))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (RESULT, POSTAUDIT, GOLD_SNAPSHOT)
    ):
        raise RuntimeError("V2.49.66 evaluation surface is not pristine")
    rows = _read_jsonl(TASK_ROWS, tracked=True)
    with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
        gold_rows = list(pool.map(_fetch_gold, range(TASK_COUNT)))
    gold_rows.sort(key=lambda row: str(row["opaque_id"]))
    gold_snapshot: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_postfreeze_pypi_gold_snapshot",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "endpoint_vector_sha256": evaluator["gold_endpoint_vector_sha256"],
        "rows": gold_rows,
        "valid_rows": sum(bool(row["valid"]) for row in gold_rows),
        "provider_attempts": sum(int(row["provider_attempts"]) for row in gold_rows),
        "created_only_after_prediction_freeze_and_pushed_forward_audit": True,
        "retry_or_selective_refetch": False,
    }
    _seal(gold_snapshot, "snapshot_payload_sha256")
    _publish(ROOT / GOLD_SNAPSHOT, gold_snapshot)
    metrics = evaluate_rows(rows, gold_rows)
    decision = quality_decision(metrics, audit["mechanism_decision"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": (
            "source_fair_quality_gate_go"
            if decision["source_fair_quality_gate_go"]
            else "source_fair_quality_gate_no_go"
        ),
        "passed": decision["source_fair_quality_gate_go"],
        "evaluator_protocol_sha256": sha256(ROOT / EVALUATOR_PROTOCOL),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "gold_snapshot_sha256": sha256(ROOT / GOLD_SNAPSHOT),
        "metrics": metrics,
        "mechanism": audit["mechanism_decision"],
        "decision": decision,
        "fixed_denominator_failure_as_zero": True,
        "claim_scope": {
            "benchmark_external_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "same_state_entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
            "independent_model_generation_variation_remains_a_limitation": True,
        },
        "authorization": {
            "public_exact220_candidate_design": decision[
                "public_exact220_candidate_design_authorized"
            ],
            "public_exact220_launch": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    _seal(value, "result_payload_sha256")
    _publish(ROOT / RESULT, value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    computed = quality_decision(
        copied.get("metrics") or {}, copied.get("mechanism") or {}
    )
    if (
        copied.get("role") != "v24966_source_fair_quality_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("decision") != computed
        or copied.get("passed") is not computed["source_fair_quality_gate_go"]
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get("authorization", {}).get("public_exact220_launch") is not False
        or copied.get("authorization", {}).get("selective_retry_or_revaluation")
        is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.66 result drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    result = validate_result(_read(RESULT))
    gold = _read(GOLD_SNAPSHOT)
    checks = {
        "result_valid": True,
        "gold_snapshot_sealed": _sealed(gold, "snapshot_payload_sha256"),
        "gold_snapshot_bound_to_prediction_freeze": gold.get(
            "prediction_freeze_sha256"
        )
        == result["prediction_freeze_sha256"],
        "gold_exactly_one_attempt_per_task": gold.get("provider_attempts") == TASK_COUNT,
        "decision_recomputes_exactly": result["decision"]
        == quality_decision(result["metrics"], result["mechanism"]),
        "fixed_denominator_failure_as_zero": result[
            "fixed_denominator_failure_as_zero"
        ]
        is True,
        "protected_watchers_unchanged": _watchers() == expected_watchers(),
        "shared_api_lease_inactive": _lease_inactive(),
        "no_selective_retry_or_revaluation": result["authorization"][
            "selective_retry_or_revaluation"
        ]
        is False,
        "no_public_launch_or_sota_authority": result["authorization"][
            "public_exact220_launch"
        ]
        is False
        and result["authorization"]["leaderboard_or_sota"] is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    audit_valid = not findings
    passed = audit_valid and result["passed"] is True
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24966_source_fair_quality_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "gold_snapshot_sha256": sha256(ROOT / GOLD_SNAPSHOT),
        "checks": checks,
        "findings": findings,
        "audit_valid": audit_valid,
        "source_fair_quality_gate_go": passed,
        "source_policy": source_policy(),
        "authorization": {
            "public_exact220_candidate_design": passed,
            "public_exact220_launch": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return _seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "build-audit",
            "protocol",
            "preaudit",
            "start",
            "run",
            "forward-audit",
            "evaluator-protocol",
            "evaluate",
            "postaudit",
        ),
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        _clean_pushed()
        if (ROOT / BUILD_AUDIT).exists() or (ROOT / BUILD_AUDIT).is_symlink():
            raise RuntimeError("V2.49.66 build audit surface is not pristine")
        value = build_audit()
        if value["findings"]:
            raise RuntimeError(value["findings"])
        path = BUILD_AUDIT
    elif args.command == "protocol":
        value = build_protocol()
        path = PROTOCOL
    elif args.command == "preaudit":
        value = build_preaudit()
        if value["findings"]:
            raise RuntimeError(value["findings"])
        path = PREAUDIT
    elif args.command == "start":
        value = build_start()
        path = EXECUTION_START
    elif args.command == "run":
        value = run_forward()
        path = FORWARD_RESULT
    elif args.command == "forward-audit":
        if (ROOT / FORWARD_AUDIT).exists() or (ROOT / FORWARD_AUDIT).is_symlink():
            raise RuntimeError("V2.49.66 forward audit surface is not pristine")
        value = build_forward_audit()
        path = FORWARD_AUDIT
    elif args.command == "evaluator-protocol":
        value = build_evaluator_protocol()
        path = EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
        value = run_evaluation()
        path = RESULT
    else:
        if (ROOT / POSTAUDIT).exists() or (ROOT / POSTAUDIT).is_symlink():
            raise RuntimeError("V2.49.66 postaudit surface is not pristine")
        value = build_postaudit()
        path = POSTAUDIT
    if args.command not in {"run", "evaluate"}:
        _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "passed": value.get("passed"),
                "audit_valid": value.get("audit_valid"),
                "status": value.get("status"),
                "decision": value.get("decision")
                or value.get("mechanism_decision"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
