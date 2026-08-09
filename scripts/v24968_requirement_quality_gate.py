#!/usr/bin/env python3
"""Fresh three-arm quality gate for requirement-aware source allocation.

Forward receives only ``opaque_id`` and a visible question containing one
PyPI project identity and one GitHub repository identity.  Stable-first-seen,
cumulative-source-fair, and requirement-aware arms replay the same hosted
search responses and consume one shared task-local fetch union.  Each arm gets
exactly 6,000 fetched-page characters and one GPT-5.6 call.  Predictions are
frozen and the forward audit is pushed before the predeclared PyPI/GitHub gold
endpoints may be opened.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
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
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24959_source_fair_discovery import (  # noqa: E402
    order_source_fair_leads,
)
from deepwide_agent.v24961_cumulative_source_fair import (  # noqa: E402
    compare_cumulative_prefixes,
)
from deepwide_agent.v24967_requirement_aware_source_allocation import (  # noqa: E402
    REQUIREMENTS,
    compose_evidence,
    select_requirement_aware,
)
from scripts import v24966_source_fair_quality_gate as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260809"
PROTOCOL_ID = "v24968_fresh_pypi_github_requirement_quality_gate_v1"
SCRIPT = Path("scripts/v24968_requirement_quality_gate.py")
TEST = Path("tests/test_v24968_requirement_quality_gate.py")
BUILD_AUDIT = Path(f"results/v24968_requirement_quality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24968_requirement_quality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24968_requirement_quality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24968_requirement_quality_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24968_requirement_quality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24968_requirement_quality_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(
    f"results/v24968_requirement_quality_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v24968_requirement_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24968_requirement_quality_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24968_requirement_quality_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_authority_gold.json"
LEASE_PATH = parent.LEASE_PATH

STABLE = "stable_first_seen"
SOURCE_FAIR = "cumulative_source_fair"
REQUIREMENT = "requirement_aware_authority"
ARMS = (STABLE, SOURCE_FAIR, REQUIREMENT)
TASKS = (
    ("fastapi", "fastapi/fastapi"),
    ("starlette", "encode/starlette"),
    ("uvicorn", "encode/uvicorn"),
    ("sqlalchemy", "sqlalchemy/sqlalchemy"),
    ("alembic", "sqlalchemy/alembic"),
    ("attrs", "python-attrs/attrs"),
    ("structlog", "hynek/structlog"),
    ("loguru", "Delgan/loguru"),
    ("tenacity", "jd/tenacity"),
    ("anyio", "agronholm/anyio"),
    ("trio", "python-trio/trio"),
    ("click", "pallets/click"),
    ("flask", "pallets/flask"),
    ("werkzeug", "pallets/werkzeug"),
    ("jinja2", "pallets/jinja"),
    ("itsdangerous", "pallets/itsdangerous"),
    ("markupsafe", "pallets/markupsafe"),
    ("black", "psf/black"),
    ("ruff", "astral-sh/ruff"),
    ("mypy", "python/mypy"),
    ("pytest-asyncio", "pytest-dev/pytest-asyncio"),
)
TASK_COUNT = len(TASKS)
EXECUTOR_CONCURRENCY = TASK_COUNT
QUERIES_PER_WAVE = 2
WAVE_FETCH_CAPS = (4, 2)
RESULTS_PER_QUERY = 3
EVIDENCE_CHARS = 6_000
REQUIREMENT_QUOTA_CHARS = 2_500
MINIMUM_REQUIREMENT_CHARS = 2_000
TASK_DEADLINE_SECONDS = 240.0
MODEL_OUTPUT_TOKENS = parent.MODEL_OUTPUT_TOKENS
MODEL = parent.MODEL
COLUMNS = (
    "Package",
    "PyPI latest version",
    "Requires-Python",
    "GitHub latest release tag",
    "GitHub latest release date (YYYY-MM-DD)",
)
FALLBACK_TABLE = (
    "| Package | PyPI latest version | Requires-Python | GitHub latest release tag | GitHub latest release date (YYYY-MM-DD) |\n"
    "|---|---|---|---|---|\n"
    "| Unknown | Unknown | Unknown | Unknown | Unknown |"
)
IDENTITY = re.compile(
    r"<PACKAGE>\s*([^<\n]+?)\s*</PACKAGE>\s*"
    r"<REPOSITORY>\s*([^<\n]+?)\s*</REPOSITORY>",
    re.S,
)
QUERY_PATTERNS = (
    "{project} latest release metadata Python package",
    "{project} {repository} release notes latest",
    "site:pypi.org/project/{project} {project} latest version Requires-Python",
    "site:github.com/{repository}/releases {project} latest release",
)
DEVELOPMENT_EXCLUSIONS = frozenset({"pydantic", "numpy"})
PRIOR_EXTERNAL_EXCLUSIONS = frozenset(parent.PACKAGES)
SOURCES = (
    SCRIPT,
    TEST,
    Path("src/deepwide_agent/v24967_requirement_aware_source_allocation.py"),
    Path("scripts/v24966_source_fair_quality_gate.py"),
    Path("scripts/v24962_cumulative_source_fair_live_gate.py"),
    Path("scripts/v24960_source_fair_live_gate.py"),
    Path("src/deepwide_agent/v24961_cumulative_source_fair.py"),
    Path("src/deepwide_agent/v24959_source_fair_discovery.py"),
    Path("src/deepwide_agent/v24957_action_fair_discovery.py"),
    Path("src/deepwide_agent/v24280_task_union_single_shot.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24287_hard_deadline_fetch.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("scripts/deepwide_api_lease.py"),
)
SECRET = parent.SECRET
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
        "gold_endpoint_vector",
        "evaluate_prediction",
        "evaluate_rows",
        "quality_decision",
        "run_evaluation",
        "gold_snapshot",
    }
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_sealed = parent._sealed
_seal = parent._seal


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
        raise RuntimeError("V2.49.68 requires clean pushed HEAD")


def _ordinary(relative: Path, *, tracked: bool = False) -> Path:
    path = ROOT / relative
    tracked_ok = not tracked or subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not tracked_ok
    ):
        raise RuntimeError(f"V2.49.68 expected ordinary repository file: {relative}")
    return path


def _manifest(*, tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = _ordinary(relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.49.68 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _read(relative: Path, *, tracked: bool = False) -> dict[str, Any]:
    value = json.loads(_ordinary(relative, tracked=tracked).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.68 expected JSON object")
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
        raise RuntimeError("V2.49.68 expected JSONL objects")
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
    return parent.expected_watchers()


def _watchers() -> list[dict[str, Any]]:
    return parent._watchers()


def _lease_inactive() -> bool:
    return parent._lease_inactive()


def task_vector() -> tuple[dict[str, str], ...]:
    if (
        TASK_COUNT != 21
        or len(set(TASKS)) != TASK_COUNT
        or {project.casefold() for project, _repo in TASKS}
        & (DEVELOPMENT_EXCLUSIONS | PRIOR_EXTERNAL_EXCLUSIONS)
    ):
        raise RuntimeError("V2.49.68 fresh population drifted")
    output: list[dict[str, str]] = []
    for project, repository in TASKS:
        opaque = "task_" + hashlib.sha256(
            f"v24968:{project}:{repository}".encode()
        ).hexdigest()[:24]
        question = (
            "Using only the supplied fetched pages, return exactly one Markdown "
            "table and no prose. Include exactly one row. The visible identities are:\n"
            f"<PACKAGE>{project}</PACKAGE><REPOSITORY>{repository}</REPOSITORY>\n"
            "Columns exactly: "
            + " | ".join(COLUMNS)
            + ". PyPI fields must describe the latest PyPI release. GitHub fields "
            "must describe the latest GitHub release for the visible repository. "
            "Dates use YYYY-MM-DD. Preserve the Requires-Python expression while "
            "collapsing whitespace. Use Unknown only when the supplied pages do not "
            "establish a value."
        )
        output.append({"opaque_id": opaque, "question": question})
    return tuple(output)


def parse_visible_identity(question: str) -> tuple[str, str]:
    if not isinstance(question, str):
        raise ValueError("V2.49.68 visible question absent")
    match = IDENTITY.search(question)
    if match is None:
        raise ValueError("V2.49.68 visible identities absent")
    project = match.group(1).strip()
    repository = match.group(2).strip()
    if (project, repository) not in TASKS:
        raise ValueError("V2.49.68 visible identity pair drifted")
    return project, repository


def query_vector() -> tuple[tuple[str, ...], ...]:
    output = []
    for task in task_vector():
        project, repository = parse_visible_identity(task["question"])
        output.append(
            tuple(
                pattern.format(project=project, repository=repository)
                for pattern in QUERY_PATTERNS
            )
        )
    return tuple(output)


def arm_order_vector() -> tuple[tuple[str, ...], ...]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: (
            hashlib.sha256(
                f"v24968-arm-order:{task_vector()[index]['opaque_id']}".encode()
            ).hexdigest(),
            index,
        ),
    )
    rotation = {index: position % len(ARMS) for position, index in enumerate(ranked)}
    return tuple(
        tuple((*ARMS[offset:], *ARMS[:offset]))
        for offset in (rotation[index] for index in range(TASK_COUNT))
    )


def _arm_order(opaque_id: str) -> tuple[str, ...]:
    indices = {
        task["opaque_id"]: index for index, task in enumerate(task_vector())
    }
    if opaque_id not in indices:
        raise ValueError("V2.49.68 unknown arm order key")
    return arm_order_vector()[indices[opaque_id]]


def gold_endpoint_vector() -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            f"https://pypi.org/pypi/{project}/json",
            f"https://api.github.com/repos/{repository}/releases/latest",
        )
        for project, repository in TASKS
    )


def source_policy() -> dict[str, bool]:
    return {
        "fresh_benchmark_external_pypi_github_population_only": True,
        "runtime_reads_only_opaque_id_and_visible_question": True,
        "same_provider_payload_replayed_by_all_arms": True,
        "same_task_local_union_fetch_bytes_for_shared_urls": True,
        "same_evidence_chars_model_prompt_output_cap_and_attempt_count": True,
        "only_treatment_is_url_identity_order_and_evidence_allocation": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "forward_persists_no_question_query_url_host_title_page_or_provider_payload": True,
        "deepwidebench_manifest_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "authority_gold_endpoints_opened_only_after_prediction_freeze": True,
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
        "minimum_selected_leads_per_task_per_arm": 5,
        "minimum_requirement_selection_changed_tasks": 12,
        "minimum_requirement_allocation_changed_tasks": 16,
        "minimum_candidate_both_requirement_quota_tasks": 16,
        "minimum_candidate_requirement_coverage_tasks": 18,
        "minimum_requirement_prediction_changed_vs_stable": 10,
        "minimum_requirement_prediction_changed_vs_source_fair": 10,
        "evidence_chars_per_task_per_arm": EVIDENCE_CHARS,
        "requirement_quota_chars": REQUIREMENT_QUOTA_CHARS,
        "minimum_requirement_chars": MINIMUM_REQUIREMENT_CHARS,
        "model_attempts_per_arm": TASK_COUNT,
        "maximum_candidate_over_each_control_model_token_ratio": 1.10,
        "maximum_failure_as_zero_tasks": 0,
        "maximum_search_transport_failures": 0,
        "maximum_search_deadline_failures": 0,
        "gold_valid_tasks": TASK_COUNT,
        "quality_rule": (
            "candidate_exact_strictly_greater_than_both_controls_and_entity_row_"
            "item_column_composite_nonregressing_against_both"
        ),
    }


def _run_tests() -> dict[str, Any]:
    suites = (
        TEST,
        Path("tests/test_v24967_requirement_aware_source_allocation.py"),
        Path("tests/test_v24966_source_fair_quality_gate.py"),
        Path("tests/test_v24961_cumulative_source_fair.py"),
    )
    observed = 0
    outputs: list[str] = []
    passed = True
    for suite in suites:
        process = subprocess.run(
            [sys.executable, "-I", "-B", str(suite), "-v"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", process.stdout)
        observed += int(match.group(1)) if match else 0
        outputs.append(f"{suite}:{process.returncode}")
        passed = passed and process.returncode == 0
    return {"passed": passed, "observed": observed, "suites": outputs}


def _forward_ast_safe() -> bool:
    tree = ast.parse(_ordinary(SCRIPT).read_text(encoding="utf-8"))
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
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
    first_positions = Counter(order[0] for order in arm_order_vector())
    checks = {
        "focused_and_regression_tests_pass": tests["passed"]
        and tests["observed"] >= 30,
        "source_manifest_complete": len(manifest) == len(SOURCES),
        "forward_ast_has_no_privileged_runtime_names": _forward_ast_safe(),
        "credential_literal_scan_clean": True,
        "fresh_population_is_disjoint": not (
            {project.casefold() for project, _repo in TASKS}
            & (DEVELOPMENT_EXCLUSIONS | PRIOR_EXTERNAL_EXCLUSIONS)
        ),
        "three_arm_first_position_exactly_balanced": first_positions
        == Counter({arm: TASK_COUNT // len(ARMS) for arm in ARMS}),
        "public_benchmark_launch_not_authorized": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_requirement_quality_build_audit",
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
        copied.get("role") != "v24968_requirement_quality_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("public_exact220_or_sota") is not False
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.68 build audit drifted")
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
        raise RuntimeError("V2.49.68 future surface is not pristine")
    manifest = _manifest(tracked=require_clean)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_requirement_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "population": {
            "kind": "fresh_public_pypi_and_github_release_metadata_tasks",
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(task_vector()),
            "query_vector_sha256": payload_sha256(query_vector()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "postfreeze_gold_endpoint_vector_sha256": payload_sha256(
                gold_endpoint_vector()
            ),
            "development_projects_permanently_excluded": sorted(
                DEVELOPMENT_EXCLUSIONS
            ),
            "v24966_projects_permanently_excluded": sorted(
                PRIOR_EXTERNAL_EXCLUSIONS
            ),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": (
                "stable_order_vs_cumulative_source_order_vs_exact_visible_"
                "authority_requirement_order_and_fixed_allocation"
            ),
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": parent.MODEL_CONCURRENCY,
            "queries_per_wave": QUERIES_PER_WAVE,
            "wave_fetch_caps": list(WAVE_FETCH_CAPS),
            "same_search_responses_for_all_arms": True,
            "same_task_local_union_fetch_for_all_arms": True,
            "same_fetched_bytes_for_shared_urls": True,
            "evidence_chars_per_arm": EVIDENCE_CHARS,
            "candidate_requirement_quota_chars": REQUIREMENT_QUOTA_CHARS,
            "model": MODEL,
            "reasoning_effort": "low",
            "service_tier": "priority",
            "model_attempts_per_arm": 1,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "arm_first_position_exactly_balanced_7_each": True,
            "fixed_denominator_failure_as_zero": True,
            "raw_union_fetch_failure_is_reliability_only_if_all_arm_budgets_remain_complete": True,
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
    population = copied.get("population") or {}
    execution = copied.get("execution") or {}
    manifest = _manifest(tracked=True) if require_manifest else copied.get("source_manifest")
    if (
        copied.get("role") != "v24968_requirement_quality_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or population.get("task_vector_sha256") != payload_sha256(task_vector())
        or population.get("query_vector_sha256") != payload_sha256(query_vector())
        or population.get("arm_order_vector_sha256")
        != payload_sha256(arm_order_vector())
        or population.get("postfreeze_gold_endpoint_vector_sha256")
        != payload_sha256(gold_endpoint_vector())
        or execution.get("arms") != list(ARMS)
        or execution.get("same_search_responses_for_all_arms") is not True
        or execution.get("same_task_local_union_fetch_for_all_arms") is not True
        or execution.get("evidence_chars_per_arm") != EVIDENCE_CHARS
        or execution.get("candidate_requirement_quota_chars")
        != REQUIREMENT_QUOTA_CHARS
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
        raise RuntimeError("V2.49.68 protocol drifted")
    return copied


def _endpoint_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
        return False


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
        "focused_and_regression_tests_pass": tests["passed"]
        and tests["observed"] >= 30,
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
        "role": "v24968_requirement_quality_preactivation_audit",
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
        copied.get("role") != "v24968_requirement_quality_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("execution_start_generation") is not True
        or copied.get("authorization", {}).get("public_exact220_or_sota") is not False
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.68 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL, tracked=True))
    validate_preaudit(_read(PREAUDIT, tracked=True))
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
        raise RuntimeError("V2.49.68 execution surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_requirement_quality_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preactivation_audit_sha256": sha256(ROOT / PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "query_vector_sha256": protocol["population"]["query_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
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
    protocol = validate_protocol(_read(PROTOCOL, tracked=True))
    if (
        copied.get("role") != "v24968_requirement_quality_execution_start"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or copied.get("query_vector_sha256")
        != protocol["population"]["query_vector_sha256"]
        or copied.get("arm_order_vector_sha256")
        != protocol["population"]["arm_order_vector_sha256"]
        or copied.get("gold_endpoint_vector_sha256")
        != protocol["population"]["postfreeze_gold_endpoint_vector_sha256"]
        or copied.get("prediction_output_surface_pristine") is not True
        or copied.get("gold_surface_pristine_and_unopened") is not True
        or copied.get("authorization", {}).get("one_external_forward") is not True
        or copied.get("authorization", {}).get("evaluator") is not False
        or copied.get("authorization", {}).get("retry_resume_selective_rerun")
        is not False
        or copied.get("protected_watchers") != expected_watchers()
        or not _sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.49.68 execution start drifted")
    return copied


def _client(deadline: float) -> Any:
    return parent._client(deadline)


def _registrable_sources(leads: Sequence[Mapping[str, Any]]) -> set[str]:
    return parent._registrable_sources(leads)


def _fetch_map(batches: object) -> dict[str, dict[str, Any]]:
    return parent._fetch_map(batches)


def _run_task(index: int) -> dict[str, Any]:
    task = task_vector()[index]
    project, repository = parse_visible_identity(task["question"])
    deadline = time.monotonic() + TASK_DEADLINE_SECONDS
    client = _client(deadline)
    started = time.monotonic()
    selected: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    prior_urls: dict[str, set[str]] = {arm: set() for arm in ARMS}
    cumulative_sources: dict[str, set[str]] = {arm: set() for arm in ARMS}
    cumulative_requirements: set[str] = set()
    query_rows = 0
    raw_action_groups = raw_action_sources = 0
    retrieval_ok = True
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
            pair = compare_cumulative_prefixes(
                batches,
                cap=cap,
                prior_control_urls=prior_urls[STABLE],
                prior_candidate_urls=prior_urls[SOURCE_FAIR],
                prior_control_sources=cumulative_sources[STABLE],
                prior_candidate_sources=cumulative_sources[SOURCE_FAIR],
            )
            requirement = select_requirement_aware(
                batches,
                cap=cap,
                project=project,
                repository=repository,
                prior_urls=prior_urls[REQUIREMENT],
                prior_sources=cumulative_sources[REQUIREMENT],
                prior_requirements=cumulative_requirements,
            )
            _ordered, observation, _private = order_source_fair_leads(
                batches, prior_sources=cumulative_sources[SOURCE_FAIR]
            )
            raw_action_groups += int(observation["raw_action_group_count"])
            raw_action_sources += int(observation["raw_action_source_count"])
            query_rows += len(wave_queries)
            for arm, leads, sources in (
                (STABLE, list(pair["stable"]), pair["control_cumulative_sources"]),
                (
                    SOURCE_FAIR,
                    list(pair["candidate"]),
                    pair["candidate_cumulative_sources"],
                ),
                (
                    REQUIREMENT,
                    list(requirement["selected"]),
                    requirement["cumulative_sources"],
                ),
            ):
                selected[arm].extend(leads)
                prior_urls[arm].update(
                    canonicalize_url(str(lead.get("url", ""))) for lead in leads
                )
                cumulative_sources[arm] = set(sources)
            cumulative_requirements = set(requirement["cumulative_requirements"])
    except (SearchRequestError, ValueError, RuntimeError, OSError):
        retrieval_ok = False

    union: list[dict[str, str]] = []
    union_seen: set[str] = set()
    for arm in ARMS:
        for lead in selected[arm]:
            url = canonicalize_url(
                str(lead.get("fetch_url") or lead.get("url") or "")
            )
            if not url or url in union_seen:
                continue
            union_seen.add(url)
            union.append(
                {
                    "url": str(lead.get("fetch_url") or lead.get("url") or ""),
                    "query": "shared three-arm requirement quality fetch",
                    "title": "",
                    "member_label": "",
                }
            )
    fetched_batches: object = []
    if retrieval_ok and union:
        try:
            fetched_batches = client.fetch_urls(union)
        except (ValueError, RuntimeError, OSError):
            retrieval_ok = False
    fetched = _fetch_map(fetched_batches)
    evidence: dict[str, str] = {}
    evidence_receipts: dict[str, dict[str, Any]] = {}
    if retrieval_ok:
        try:
            for arm in ARMS:
                evidence[arm], evidence_receipts[arm] = compose_evidence(
                    selected[arm],
                    fetched,
                    project=project,
                    repository=repository,
                    total_chars=EVIDENCE_CHARS,
                    requirement_quota_chars=REQUIREMENT_QUOTA_CHARS,
                    requirement_aware=arm == REQUIREMENT,
                )
        except (ValueError, RuntimeError):
            retrieval_ok = False

    final_sources = {arm: _registrable_sources(selected[arm]) for arm in ARMS}
    if retrieval_ok and (
        any(final_sources[arm] != cumulative_sources[arm] for arm in ARMS)
        or len(final_sources[SOURCE_FAIR]) < len(final_sources[STABLE])
    ):
        retrieval_ok = False

    predictions: dict[str, str] = {}
    model_usage: dict[str, dict[str, int]] = {}
    model_success = {arm: False for arm in ARMS}
    if retrieval_ok:
        for arm in _arm_order(task["opaque_id"]):
            try:
                predictions[arm], model_usage[arm] = parent._synthesize(
                    task["question"], evidence[arm], absolute_deadline=deadline
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
    completed = retrieval_ok and all(model_success.values())
    if not completed:
        predictions = {arm: FALLBACK_TABLE for arm in ARMS}

    health = validate_transport_health(client.transport_health())
    statuses = dict(client.status_counts)
    selected_url_vectors = {
        arm: [
            canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
            for lead in selected[arm]
        ]
        for arm in ARMS
    }
    empty_receipt = {
        "usable_page_count": 0,
        "usable_requirement_count": 0,
        "evidence_chars": 0,
        "pypi_project_evidence_chars": 0,
        "github_release_evidence_chars": 0,
        "total_requirement_evidence_chars": 0,
    }
    compact_receipts = {
        arm: {
            key: int((evidence_receipts.get(arm) or empty_receipt)[key])
            for key in empty_receipt
        }
        for arm in ARMS
    }
    attempt_counts = {
        arm: int((model_usage.get(arm) or {}).get("provider_attempts", 0))
        for arm in ARMS
    }
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_requirement_quality_task_result",
        "protocol_id": PROTOCOL_ID,
        "opaque_id": task["opaque_id"],
        "status": "completed" if completed else "failure_as_zero",
        "runtime_input_keys": ["opaque_id", "question"],
        "terminal": True,
        "completed": completed,
        "failure_as_zero": not completed,
        "logical_query_rows": query_rows,
        "search_provider_attempts": int(health["hosted_search_attempts"]),
        "search_provider_response_calls": int(client.calls),
        "search_http_2xx": sum(
            count for status, count in statuses.items() if 200 <= status < 300
        ),
        "search_transport_failures": int(client.transport_failures),
        "hosted_search_deadline_failures": int(
            health["hosted_search_deadline_failures"]
        ),
        "raw_action_group_count": raw_action_groups,
        "raw_action_source_count": raw_action_sources,
        "selected_leads": {arm: len(selected[arm]) for arm in ARMS},
        "registrable_sources": {arm: len(final_sources[arm]) for arm in ARMS},
        "requirement_cumulative_coverage": len(cumulative_requirements),
        "requirement_selection_changed_vs_stable": selected_url_vectors[REQUIREMENT]
        != selected_url_vectors[STABLE],
        "requirement_selection_changed_vs_source_fair": selected_url_vectors[
            REQUIREMENT
        ]
        != selected_url_vectors[SOURCE_FAIR],
        "evidence_receipts": compact_receipts,
        "requirement_evidence_changed_vs_stable": evidence.get(REQUIREMENT, "")
        != evidence.get(STABLE, ""),
        "requirement_evidence_changed_vs_source_fair": evidence.get(
            REQUIREMENT, ""
        )
        != evidence.get(SOURCE_FAIR, ""),
        "planned_union_fetches": len(union),
        "actual_hard_fetch_helper_calls": int(health["hard_fetch_helper_calls"]),
        "hard_fetch_deadline_failures": int(health["hard_fetch_deadline_failures"]),
        "fetch_helper_failures": int(health["fetch_helper_failures"]),
        "fetch_deadline_rejections": int(health["fetch_deadline_rejections"]),
        "search_usage": {
            "input_tokens": int(client.input_tokens),
            "output_tokens": int(client.output_tokens),
            "total_tokens": int(client.total_tokens),
        },
        "model_success": model_success,
        "model_attempt_counts": attempt_counts,
        "model_attempt_counts_matched": len(set(attempt_counts.values())) == 1,
        "model_usage": model_usage,
        "predictions": predictions,
        "prediction_sha256": {
            arm: payload_sha256(predictions[arm]) for arm in ARMS
        },
        "requirement_prediction_changed_vs_stable": predictions[REQUIREMENT]
        != predictions[STABLE],
        "requirement_prediction_changed_vs_source_fair": predictions[REQUIREMENT]
        != predictions[SOURCE_FAIR],
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "same_provider_payload_replayed_by_all_arms": True,
        "same_task_local_union_fetch_bytes_for_shared_urls": True,
        "same_evidence_chars_model_prompt_output_cap": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "authority_gold_endpoints_opened": False,
        "entropy_or_information_gain_assigns_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
        "contains_question_query_url_host_title_page_or_provider_payload": False,
    }
    return _seal(row, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    predictions = copied.get("predictions") or {}
    prediction_hashes = copied.get("prediction_sha256") or {}
    attempts = copied.get("model_attempt_counts") or {}
    model_success = copied.get("model_success") or {}
    selected = copied.get("selected_leads") or {}
    sources = copied.get("registrable_sources") or {}
    receipts = copied.get("evidence_receipts") or {}
    expected_matched = set(attempts) == set(ARMS) and len(set(attempts.values())) == 1
    completed = copied.get("completed") is True
    expected_status = "completed" if completed else "failure_as_zero"
    expected_ids = {task["opaque_id"] for task in task_vector()}
    receipt_fields = {
        "usable_page_count",
        "usable_requirement_count",
        "evidence_chars",
        "pypi_project_evidence_chars",
        "github_release_evidence_chars",
        "total_requirement_evidence_chars",
    }
    if (
        copied.get("role") != "v24968_requirement_quality_task_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("opaque_id") not in expected_ids
        or copied.get("runtime_input_keys") != ["opaque_id", "question"]
        or copied.get("terminal") is not True
        or copied.get("status") != expected_status
        or copied.get("failure_as_zero") is completed
        or set(predictions) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or set(prediction_hashes) != set(ARMS)
        or any(
            prediction_hashes.get(arm) != payload_sha256(predictions[arm])
            for arm in ARMS
        )
        or set(model_success) != set(ARMS)
        or any(not isinstance(model_success[arm], bool) for arm in ARMS)
        or set(selected) != set(ARMS)
        or set(sources) != set(ARMS)
        or set(receipts) != set(ARMS)
        or any(
            set(receipts[arm]) != receipt_fields
            or any(
                isinstance(receipts[arm].get(name), bool)
                or not isinstance(receipts[arm].get(name), int)
                or receipts[arm][name] < 0
                for name in receipt_fields
            )
            for arm in ARMS
        )
        or any(
            isinstance(selected.get(arm), bool)
            or not isinstance(selected.get(arm), int)
            or selected[arm] < 0
            or isinstance(sources.get(arm), bool)
            or not isinstance(sources.get(arm), int)
            or sources[arm] < 0
            for arm in ARMS
        )
        or isinstance(copied.get("requirement_cumulative_coverage"), bool)
        or not isinstance(copied.get("requirement_cumulative_coverage"), int)
        or not 0 <= copied["requirement_cumulative_coverage"] <= len(REQUIREMENTS)
        or copied.get("model_attempt_counts_matched") is not expected_matched
        or completed and copied.get("model_attempt_counts_matched") is not True
        or completed and not all(model_success.values())
        or copied.get("same_provider_payload_replayed_by_all_arms") is not True
        or copied.get("same_task_local_union_fetch_bytes_for_shared_urls") is not True
        or copied.get("same_evidence_chars_model_prompt_output_cap") is not True
        or copied.get("provider_narrative_or_snippet_used_as_active_evidence") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read")
        is not False
        or copied.get("authority_gold_endpoints_opened") is not False
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get("retry_resume_skip_or_selective_rerun") is not False
        or copied.get("contains_question_query_url_host_title_page_or_provider_payload")
        is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.68 task result drifted")
    return copied


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
    minima = {arm: [] for arm in ARMS}
    for row in rows:
        walls.append(float(row.get("wall_seconds", 0.0)))
        selected = row.get("selected_leads") or {}
        receipts = row.get("evidence_receipts") or {}
        model_success = row.get("model_success") or {}
        attempts = row.get("model_attempt_counts") or {}
        usage = row.get("model_usage") or {}
        counters["terminal"] += int(bool(row.get("terminal")))
        counters["completed"] += int(bool(row.get("completed")))
        counters["failure_as_zero"] += int(bool(row.get("failure_as_zero")))
        for name in (
            "logical_query_rows",
            "search_provider_attempts",
            "search_provider_response_calls",
            "search_http_2xx",
            "search_transport_failures",
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
        for flag in (
            "requirement_selection_changed_vs_stable",
            "requirement_selection_changed_vs_source_fair",
            "requirement_evidence_changed_vs_stable",
            "requirement_evidence_changed_vs_source_fair",
            "requirement_prediction_changed_vs_stable",
            "requirement_prediction_changed_vs_source_fair",
        ):
            counters[flag] += int(bool(row.get(flag)))
        counters["candidate_requirement_coverage_task"] += int(
            int(row.get("requirement_cumulative_coverage", 0)) == len(REQUIREMENTS)
        )
        requirement_receipt = receipts.get(REQUIREMENT) or {}
        counters["candidate_both_requirement_quota_task"] += int(
            int(requirement_receipt.get("pypi_project_evidence_chars", 0))
            >= MINIMUM_REQUIREMENT_CHARS
            and int(requirement_receipt.get("github_release_evidence_chars", 0))
            >= MINIMUM_REQUIREMENT_CHARS
        )
        for arm in ARMS:
            minima[arm].append(int(selected.get(arm, 0)))
            counters[f"{arm}_selected_leads"] += int(selected.get(arm, 0))
            counters[f"{arm}_evidence_chars"] += int(
                (receipts.get(arm) or {}).get("evidence_chars", 0)
            )
            counters[f"{arm}_model_success"] += int(bool(model_success.get(arm)))
            counters[f"{arm}_model_attempts"] += int(attempts.get(arm, 0))
            counters[f"{arm}_model_input_tokens"] += int(
                (usage.get(arm) or {}).get("input_tokens", 0)
            )
            counters[f"{arm}_model_output_tokens"] += int(
                (usage.get(arm) or {}).get("output_tokens", 0)
            )
    return {
        **{name: int(counters[name]) for name in sorted(counters)},
        "terminal_task_count": int(counters["terminal"]),
        "completed_task_count": int(counters["completed"]),
        "failure_as_zero_task_count": int(counters["failure_as_zero"]),
        "minimum_selected_leads_per_task": {
            arm: min(values, default=0) for arm, values in minima.items()
        },
        "task_wall_p50_seconds": _percentile(walls, 0.50),
        "task_wall_p95_seconds": _percentile(walls, 0.95),
        "task_wall_max_seconds": round(max(walls, default=0.0), 6),
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "contains_question_query_url_host_title_page_answer_provider_payload_selection_or_per_task_score": False,
    }


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    gate = gates()
    candidate_tokens = float(
        aggregate.get(f"{REQUIREMENT}_model_input_tokens", 0)
    ) + float(aggregate.get(f"{REQUIREMENT}_model_output_tokens", 0))
    control_tokens = {
        arm: float(aggregate.get(f"{arm}_model_input_tokens", 0))
        + float(aggregate.get(f"{arm}_model_output_tokens", 0))
        for arm in (STABLE, SOURCE_FAIR)
    }
    checks = {
        "all_tasks_terminal": aggregate.get("terminal_task_count") == TASK_COUNT,
        "all_tasks_completed": aggregate.get("completed_task_count") == TASK_COUNT,
        "no_failure_as_zero": aggregate.get("failure_as_zero_task_count") == 0,
        "all_logical_queries_committed": aggregate.get("logical_query_rows")
        == gate["logical_query_rows"],
        "exact_search_attempts": aggregate.get("search_provider_attempts")
        == gate["search_provider_attempts"],
        "exact_search_responses": aggregate.get("search_provider_response_calls")
        == gate["search_provider_response_calls"],
        "all_search_responses_2xx": aggregate.get("search_http_2xx")
        == gate["search_http_2xx"],
        "no_search_transport_failures": aggregate.get(
            "search_transport_failures", 1
        )
        == 0,
        "no_search_deadline_failures": aggregate.get(
            "hosted_search_deadline_failures", 1
        )
        == 0,
        "minimum_selection_per_arm": all(
            int((aggregate.get("minimum_selected_leads_per_task") or {}).get(arm, 0))
            >= gate["minimum_selected_leads_per_task_per_arm"]
            for arm in ARMS
        ),
        "candidate_selection_changes_enough_tasks": min(
            int(aggregate.get("requirement_selection_changed_vs_stable", 0)),
            int(
                aggregate.get("requirement_selection_changed_vs_source_fair", 0)
            ),
        )
        >= gate["minimum_requirement_selection_changed_tasks"],
        "candidate_allocation_changes_enough_tasks": min(
            int(aggregate.get("requirement_evidence_changed_vs_stable", 0)),
            int(
                aggregate.get("requirement_evidence_changed_vs_source_fair", 0)
            ),
        )
        >= gate["minimum_requirement_allocation_changed_tasks"],
        "candidate_requirement_coverage_enough_tasks": aggregate.get(
            "candidate_requirement_coverage_task", 0
        )
        >= gate["minimum_candidate_requirement_coverage_tasks"],
        "candidate_both_quotas_enough_tasks": aggregate.get(
            "candidate_both_requirement_quota_task", 0
        )
        >= gate["minimum_candidate_both_requirement_quota_tasks"],
        "fixed_evidence_budget_all_arms": all(
            aggregate.get(f"{arm}_evidence_chars", 0) == TASK_COUNT * EVIDENCE_CHARS
            for arm in ARMS
        ),
        "exact_model_attempts_and_successes": all(
            aggregate.get(f"{arm}_model_attempts", 0) == TASK_COUNT
            and aggregate.get(f"{arm}_model_success", 0) == TASK_COUNT
            for arm in ARMS
        ),
        "candidate_model_token_cost_bounded": all(
            control_tokens[arm] > 0
            and candidate_tokens
            <= control_tokens[arm]
            * gate["maximum_candidate_over_each_control_model_token_ratio"]
            for arm in control_tokens
        ),
        "candidate_prediction_changes_vs_stable": aggregate.get(
            "requirement_prediction_changed_vs_stable", 0
        )
        >= gate["minimum_requirement_prediction_changed_vs_stable"],
        "candidate_prediction_changes_vs_source_fair": aggregate.get(
            "requirement_prediction_changed_vs_source_fair", 0
        )
        >= gate["minimum_requirement_prediction_changed_vs_source_fair"],
        "planned_union_equals_actual_helpers_plus_deadline_rejections": aggregate.get(
            "planned_union_fetches"
        )
        == int(aggregate.get("actual_hard_fetch_helper_calls", -1))
        + int(aggregate.get("fetch_deadline_rejections", -1)),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "mechanism_gate_passed": passed,
        "postfreeze_external_evaluator_authorized": passed,
        "public_exact220_authorized": False,
    }


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
        raise RuntimeError("V2.49.68 forward surface is not pristine")
    if not _endpoint_reachable():
        raise RuntimeError("V2.49.68 keyless GPT-5.6 endpoint unavailable")
    watchers_before = _watchers()
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v24968_requirement_quality",
        purpose="fresh_three_arm_requirement_quality_gate",
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
        "role": "v24968_requirement_quality_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "task_rows_sha256": sha256(ROOT / TASK_ROWS),
        "terminal_tasks": len(rows),
        "terminal_arm_predictions": len(rows) * len(ARMS),
        "all_predictions_terminal_before_authority_gold_or_evaluator_open": True,
        "authority_gold_endpoint_calls_before_freeze": 0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    _seal(freeze, "freeze_payload_sha256")
    _publish(ROOT / PREDICTION_FREEZE, freeze)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_requirement_quality_forward_result",
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
        "all_predictions_terminal_before_authority_gold_or_evaluator_open": True,
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
        copied.get("role") != "v24968_requirement_quality_forward_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("all_predictions_terminal_before_authority_gold_or_evaluator_open")
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
        raise RuntimeError("V2.49.68 forward result drifted")
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
    freeze = _read(PREDICTION_FREEZE)
    forbidden_keys = {
        "question",
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
    checks = {
        "protocol_and_forward_validate": True,
        "execution_start_bound": forward["execution_start_sha256"]
        == sha256(ROOT / EXECUTION_START),
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
        "role": "v24968_requirement_quality_forward_audit",
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
    expected_authority = (
        copied.get("audit_valid") is True
        and copied.get("mechanism_decision", {}).get("mechanism_gate_passed") is True
    )
    if (
        copied.get("role") != "v24968_requirement_quality_forward_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol"
        )
        is not expected_authority
        or copied.get("authorization", {}).get(
            "public_exact220_or_other_benchmark_launch"
        )
        is not False
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.68 forward audit drifted")
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
        raise RuntimeError("V2.49.68 evaluator surface is not pristine")
    if (
        audit["mechanism_decision"]["mechanism_gate_passed"] is not True
        or audit["authorization"]["postfreeze_external_evaluator_protocol"]
        is not True
    ):
        raise RuntimeError("V2.49.68 mechanism gate withheld evaluator authority")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_requirement_quality_evaluator_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "task_rows_sha256": forward["task_rows_sha256"],
        "gold_endpoint_vector_sha256": payload_sha256(gold_endpoint_vector()),
        "gold_rule": {
            "pypi_version": "pypi_info_version",
            "requires_python": "pypi_info_requires_python_or_Unknown",
            "github_release_tag": "github_latest_release_tag_name",
            "github_release_date": "github_latest_release_published_at_date",
            "one_http_attempt_per_endpoint": True,
            "fixed_denominator_failure_as_zero": True,
        },
        "primary_comparisons": [
            f"{REQUIREMENT}_minus_{STABLE}",
            f"{REQUIREMENT}_minus_{SOURCE_FAIR}",
        ],
        "go_rule": gates()["quality_rule"],
        "authorization": {
            "one_postfreeze_external_evaluation": True,
            "public_exact220_or_other_benchmark_launch": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return _seal(value, "protocol_payload_sha256")


def validate_evaluator_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24968_requirement_quality_evaluator_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("gold_endpoint_vector_sha256")
        != payload_sha256(gold_endpoint_vector())
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
        raise RuntimeError("V2.49.68 evaluator protocol drifted")
    return copied


def _normalize_project(value: object) -> str:
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
    return cells[0], [row for row in cells[2:] if len(row) == len(cells[0])]


def evaluate_prediction(prediction: str, gold: Mapping[str, Any]) -> dict[str, float | int]:
    columns, rows = _matrix(prediction)
    exact_columns = columns == list(COLUMNS)
    if not exact_columns:
        rows = []
    expected_key = _normalize_project(gold["package"])
    predicted = {
        _normalize_project(row[0]): row
        for row in rows
        if len(row) == len(COLUMNS) and _normalize_project(row[0])
    }
    true_entities = int(expected_key in predicted)
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = float(true_entities)
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    item_true = 0
    if expected_key in predicted:
        row = predicted[expected_key]
        item_true += int(_normalize_value(row[1]) == _normalize_value(gold["version"]))
        item_true += int(
            _normalize_requires_python(row[2])
            == _normalize_requires_python(gold["requires_python"])
        )
        item_true += int(
            _normalize_value(row[3]) == _normalize_value(gold["github_tag"])
        )
        item_true += int(
            _normalize_value(row[4]) == _normalize_value(gold["github_date"])
        )
    predicted_items = len(predicted) * 4
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / 4
    item_f1 = (
        2 * item_precision * item_recall / (item_precision + item_recall)
        if item_precision + item_recall
        else 0.0
    )
    exact = int(
        exact_columns
        and len(rows) == 1
        and list(predicted) == [expected_key]
        and item_true == 4
    )
    column_f1 = 1.0 if exact_columns else 0.0
    return {
        "exact_table_success": exact,
        "entity_recall": recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": (recall + row_f1 + item_f1 + column_f1) / 4,
    }


def _fetch_gold(index: int) -> dict[str, Any]:
    project, repository = TASKS[index]
    opaque_id = task_vector()[index]["opaque_id"]
    pypi_url, github_url = gold_endpoint_vector()[index]
    pypi_attempt = github_attempt = 0
    pypi_hash = github_hash = ""
    pypi_status = github_status = 0
    package = project
    version = "Unknown"
    requires_python = "Unknown"
    github_tag = "Unknown"
    github_date = "Unknown"
    pypi_valid = github_valid = False
    try:
        pypi_attempt = 1
        pypi_response = requests.get(
            pypi_url,
            headers={"User-Agent": "deepwide-v24968/1.0"},
            timeout=(5.0, 30.0),
        )
        pypi_raw = bytes(pypi_response.content)
        pypi_status = int(pypi_response.status_code)
        pypi_response.raise_for_status()
        pypi_value = pypi_response.json()
        pypi_info = pypi_value.get("info") if isinstance(pypi_value, Mapping) else None
        if not isinstance(pypi_info, Mapping):
            raise ValueError("PyPI response schema drifted")
        version = str(pypi_info.get("version") or "").strip()
        package = str(pypi_info.get("name") or project).strip()
        requires_python = str(pypi_info.get("requires_python") or "Unknown").strip()
        if not version or not package:
            raise ValueError("PyPI latest metadata absent")
        pypi_hash = hashlib.sha256(pypi_raw).hexdigest()
        pypi_valid = True
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError):
        pass
    try:
        github_attempt = 1
        github_response = requests.get(
            github_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "deepwide-v24968/1.0",
            },
            timeout=(5.0, 30.0),
        )
        github_raw = bytes(github_response.content)
        github_status = int(github_response.status_code)
        github_response.raise_for_status()
        github_value = github_response.json()
        if not isinstance(github_value, Mapping):
            raise ValueError("GitHub response schema drifted")
        github_tag = str(github_value.get("tag_name") or "").strip()
        published = str(github_value.get("published_at") or "").strip()
        github_date = published[:10]
        if not github_tag or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", github_date):
            raise ValueError("GitHub latest release metadata absent")
        github_hash = hashlib.sha256(github_raw).hexdigest()
        github_valid = True
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError):
        pass
    return {
        "opaque_id": opaque_id,
        "requested_project": project,
        "requested_repository": repository,
        "package": package,
        "version": version,
        "requires_python": requires_python,
        "github_tag": github_tag,
        "github_date": github_date,
        "pypi_response_sha256": pypi_hash,
        "github_response_sha256": github_hash,
        "pypi_http_status": pypi_status,
        "github_http_status": github_status,
        "pypi_attempts": pypi_attempt,
        "github_attempts": github_attempt,
        "valid": pypi_valid and github_valid,
    }


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], gold_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    gold = {str(row["opaque_id"]): dict(row) for row in gold_rows}
    if len(gold) != TASK_COUNT:
        raise RuntimeError("V2.49.68 gold denominator drifted")
    metrics = {arm: [] for arm in ARMS}
    seen: set[str] = set()
    invalid = 0
    zero = {
        "exact_table_success": 0,
        "entity_recall": 0.0,
        "row_f1": 0.0,
        "item_f1": 0.0,
        "column_f1": 0.0,
        "composite": 0.0,
    }
    for raw in rows:
        row = validate_task_row(raw)
        opaque = str(row["opaque_id"])
        if opaque in seen or opaque not in gold:
            raise RuntimeError("V2.49.68 prediction/gold identity drifted")
        seen.add(opaque)
        if not gold[opaque]["valid"]:
            invalid += 1
            for arm in ARMS:
                metrics[arm].append(dict(zero))
        else:
            for arm in ARMS:
                metrics[arm].append(
                    evaluate_prediction(str(row["predictions"][arm]), gold[opaque])
                )
    if len(seen) != TASK_COUNT:
        raise RuntimeError("V2.49.68 evaluation denominator drifted")
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
    comparisons = {}
    for control in (STABLE, SOURCE_FAIR):
        comparisons[f"{REQUIREMENT}_minus_{control}"] = {
            key: aggregate[REQUIREMENT][key] - aggregate[control][key]
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
    return {"arms": aggregate, "comparisons": comparisons}


def quality_decision(
    metrics: Mapping[str, Any], mechanism: Mapping[str, Any]
) -> dict[str, Any]:
    arms = metrics.get("arms") or {}
    comparisons = metrics.get("comparisons") or {}
    deltas = [
        comparisons.get(f"{REQUIREMENT}_minus_{control}") or {}
        for control in (STABLE, SOURCE_FAIR)
    ]
    checks = {
        "mechanism_gate_passed": mechanism.get("mechanism_gate_passed") is True,
        "all_gold_tasks_valid": all(
            (arms.get(arm) or {}).get("evaluator_valid") == TASK_COUNT for arm in ARMS
        ),
        "candidate_exact_strictly_improves_over_both": all(
            float(delta.get("exact_table_successes", -1)) > 0 for delta in deltas
        ),
        "entity_nonregression_against_both": all(
            float(delta.get("entity_recall", -1)) >= 0 for delta in deltas
        ),
        "row_nonregression_against_both": all(
            float(delta.get("row_f1", -1)) >= 0 for delta in deltas
        ),
        "item_nonregression_against_both": all(
            float(delta.get("item_f1", -1)) >= 0 for delta in deltas
        ),
        "column_nonregression_against_both": all(
            float(delta.get("column_f1", -1)) >= 0 for delta in deltas
        ),
        "composite_nonregression_against_both": all(
            float(delta.get("composite", -1)) >= 0 for delta in deltas
        ),
        "evaluator_invalid_not_increased": all(
            float(delta.get("evaluator_invalid_or_not_run", 1)) <= 0
            for delta in deltas
        ),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "requirement_quality_gate_go": passed,
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
        raise RuntimeError("V2.49.68 evaluation surface is not pristine")
    rows = _read_jsonl(TASK_ROWS, tracked=True)
    with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
        gold_rows = list(pool.map(_fetch_gold, range(TASK_COUNT)))
    gold_rows.sort(key=lambda row: str(row["opaque_id"]))
    gold_snapshot: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_postfreeze_authority_gold_snapshot",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "endpoint_vector_sha256": evaluator["gold_endpoint_vector_sha256"],
        "rows": gold_rows,
        "valid_rows": sum(bool(row["valid"]) for row in gold_rows),
        "pypi_attempts": sum(int(row["pypi_attempts"]) for row in gold_rows),
        "github_attempts": sum(int(row["github_attempts"]) for row in gold_rows),
        "created_only_after_prediction_freeze_and_pushed_forward_audit": True,
        "retry_or_selective_refetch": False,
    }
    _seal(gold_snapshot, "snapshot_payload_sha256")
    _publish(ROOT / GOLD_SNAPSHOT, gold_snapshot)
    metrics = evaluate_rows(rows, gold_rows)
    decision = quality_decision(metrics, audit["mechanism_decision"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24968_requirement_quality_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": (
            "requirement_quality_gate_go"
            if decision["requirement_quality_gate_go"]
            else "requirement_quality_gate_no_go"
        ),
        "passed": decision["requirement_quality_gate_go"],
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
        copied.get("role") != "v24968_requirement_quality_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("decision") != computed
        or copied.get("passed") is not computed["requirement_quality_gate_go"]
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get("authorization", {}).get("public_exact220_launch") is not False
        or copied.get("authorization", {}).get("selective_retry_or_revaluation")
        is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.68 result drifted")
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
        "gold_exactly_one_attempt_per_endpoint": gold.get("pypi_attempts")
        == TASK_COUNT
        and gold.get("github_attempts") == TASK_COUNT,
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
        "role": "v24968_requirement_quality_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "gold_snapshot_sha256": sha256(ROOT / GOLD_SNAPSHOT),
        "checks": checks,
        "findings": findings,
        "audit_valid": audit_valid,
        "requirement_quality_gate_go": passed,
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
            raise RuntimeError("V2.49.68 build audit surface is not pristine")
        value = build_audit()
        path = BUILD_AUDIT
    elif args.command == "protocol":
        value = build_protocol()
        path = PROTOCOL
    elif args.command == "preaudit":
        value = build_preaudit()
        path = PREAUDIT
    elif args.command == "start":
        value = build_start()
        path = EXECUTION_START
    elif args.command == "run":
        value = run_forward()
        path = FORWARD_RESULT
    elif args.command == "forward-audit":
        if (ROOT / FORWARD_AUDIT).exists() or (ROOT / FORWARD_AUDIT).is_symlink():
            raise RuntimeError("V2.49.68 forward audit surface is not pristine")
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
            raise RuntimeError("V2.49.68 postaudit surface is not pristine")
        value = build_postaudit()
        path = POSTAUDIT
    if args.command not in {"run", "evaluate"}:
        if value.get("findings"):
            raise RuntimeError(value["findings"])
        _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "passed": value.get("passed"),
                "status": value.get("status"),
                "decision": value.get("decision")
                or value.get("mechanism_decision"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
