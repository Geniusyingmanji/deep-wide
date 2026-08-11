#!/usr/bin/env python3
"""Freeze and run the V2.50.41 adaptive single-request capability probe."""

from __future__ import annotations

import argparse
import ast
import copy
import fcntl
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25041_adaptive_single_request as adaptive  # noqa: E402
from deepwide_agent.v25036_source_only_hosted_search import (  # noqa: E402
    SourceOnlyRobustLatePageBoundSearchClient,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260811"
PROTOCOL_ID = "v25041_adaptive_single_request_capability_v1"
BUILD_AUDIT = Path(f"results/v25041_adaptive_single_request_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25041_adaptive_single_request_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25041_adaptive_single_request_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25041_adaptive_single_request_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v25041_adaptive_single_request_development_probe_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25041_adaptive_single_request_postresult_audit_v1_{DATE}.json")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
SOURCE = Path("src/deepwide_agent/v25041_adaptive_single_request.py")
RUNNER = Path("scripts/v25041_adaptive_single_request_probe.py")
TEST = Path("tests/test_v25041_adaptive_single_request.py")
PARENT_PROTOCOL = Path("results/v24281_single_shot_pair_preregistration_v1_20260803.json")
PARENT_RESULT = Path("results/v24281_single_shot_pair_result_v1_20260803.json")
V25036_RESULT = Path("results/v25036_source_only_development_probe_v1_20260810.json")
V25037_RESULT = Path("results/v25037_source_only_width_development_probe_v1_20260810.json")
EXPECTED_PARENT_PROTOCOL_SHA256 = "1ca846151ab5a2ba5b771344497dab91c7488c78a42557914e5614aa78a6d356"
EXPECTED_PARENT_RESULT_SHA256 = "835b3dfa0025e70486763576016d5cfa8fbf7a97980b9f833dc542d38add8db0"
EXPECTED_V25036_RESULT_SHA256 = "08f1bc286adfaa46a1bfedae4f218720162aa679c6f6842d8f808ec7b273f13e"
EXPECTED_V25037_RESULT_SHA256 = "513e4099d536858514c8ff98f0e815e1a37d9af69f432d7c8856972ca1b689ec"
NEUTRAL_SOURCE = Path("scripts/preregister_v24281_single_shot_pair.py")
EXPECTED_NEUTRAL_SOURCE_SHA256 = "13cd498e5182932c7252925a906461828e43dfd9ad21092dca047cc3fd221a80"
PAIR_INDICES = (4, 5, 6, 7)
PAIR_NUMBERS = tuple(index + 1 for index in PAIR_INDICES)
TASK_COUNT = len(PAIR_INDICES)
ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
TASK_DEADLINE_SECONDS = 240.0
EXECUTOR_CONCURRENCY = 4
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
TEST_SUITES = (
    ("test_v25041_adaptive_single_request.py", 8),
    ("test_v25041_adaptive_single_request_probe.py", 5),
    ("test_v25036_source_only_hosted_search.py", 5),
    ("test_v24985_robust_late_page_fetch.py", 2),
    ("test_v24316_deadline_search.py", 7),
    ("test_v24468_total_wall_transport.py", 8),
    ("test_v24269_task_union_discovery.py", 5),
    ("test_v24280_task_union_single_shot.py", 4),
)
EXPECTED_TESTS = sum(count for _name, count in TEST_SUITES)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
CONFLICT = re.compile(
    r"scripts/(?:run|probe|evaluate|finalize|recover|v\d+[^ ]*probe)[^ ]*\.py"
    r"|scripts/run_official_eval_local\.py"
)
SOURCE_POLICY = {
    "scope": "development_capability_only_consumed_neutral_public_documentation",
    "selected_pairs_previously_executed_and_permanently_excluded_from_confirmation": True,
    "candidate_generates_followups_before_control_uses_same_in_memory_query_vector": True,
    "query_title_url_page_provider_payload_or_credential_persisted": False,
    "benchmark_manifest_question_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    "page_fetch_standalone_generation_model_or_evaluator_called": False,
    "entropy_or_information_gain_assigns_signed_credit": False,
    "paired_quality_or_causal_effect_measured": False,
}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value))
    observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def ordinary(relative: Path, *, tracked: bool) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.50.41 expected ordinary repository file: {relative}")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"V2.50.41 expected tracked file: {relative}")
    return path


def read_object(relative: Path, *, tracked: bool) -> dict[str, Any]:
    value = json.loads(ordinary(relative, tracked=tracked).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.41 expected JSON object")
    return value


def publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
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


def clean_pushed() -> str:
    head = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--untracked-files=all") or head != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.50.41 requires clean pushed HEAD")
    return head


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, ticks, marker in EXPECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.50.41 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or int(suffix[19]) != ticks or marker not in command:
            raise RuntimeError("V2.50.41 protected watcher identity drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def lease_inactive() -> bool:
    path = ROOT / LEASE
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and parts[0].isdigit()
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and CONFLICT.search(parts[2])
        ):
            pid = int(parts[0])
            try:
                cwd = (Path("/proc") / str(pid) / "cwd").resolve()
            except OSError:
                continue
            if cwd == ROOT.resolve():
                output.append(pid)
    return sorted(set(output))


def endpoint_ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
        return False


def _import_candidates(relative: Path, tree: ast.AST) -> list[Path]:
    output: list[Path] = []
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
                if module:
                    output.append(
                        Path("src/deepwide_agent")
                        / Path(*module.split(".")).with_suffix(".py")
                    )
                else:
                    output.extend(
                        Path("src/deepwide_agent") / f"{alias.name}.py"
                        for alias in node.names
                    )
                continue
            modules.append(module)
            if module == "deepwide_agent":
                output.extend(
                    Path("src/deepwide_agent") / f"{alias.name}.py"
                    for alias in node.names
                )
            elif module == "scripts":
                output.extend(Path("scripts") / f"{alias.name}.py" for alias in node.names)
        for module in modules:
            if module.startswith("deepwide_agent."):
                output.append(Path("src") / Path(*module.split(".")).with_suffix(".py"))
            elif module.startswith("scripts."):
                output.append(Path(*module.split(".")).with_suffix(".py"))
    return output


def dependency_closure() -> tuple[Path, ...]:
    pending = [RUNNER, SOURCE]
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = ordinary(relative, tracked=False)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for candidate in _import_candidates(relative, tree):
            if (ROOT / candidate).is_file() and not (ROOT / candidate).is_symlink():
                pending.append(candidate)
    return tuple(sorted(observed, key=str))


def source_manifest(*, tracked: bool) -> dict[str, str]:
    paths = {
        *dependency_closure(),
        TEST,
        PARENT_PROTOCOL,
        PARENT_RESULT,
        V25036_RESULT,
        V25037_RESULT,
        NEUTRAL_SOURCE,
    }
    output: dict[str, str] = {}
    for relative in sorted(paths, key=str):
        path = ordinary(relative, tracked=tracked)
        if path.suffix in {".py", ".json"} and SECRET.search(
            path.read_text(encoding="utf-8")
        ):
            raise RuntimeError(f"V2.50.41 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def parent_binding() -> dict[str, Any]:
    expected = {
        PARENT_PROTOCOL: EXPECTED_PARENT_PROTOCOL_SHA256,
        PARENT_RESULT: EXPECTED_PARENT_RESULT_SHA256,
        V25036_RESULT: EXPECTED_V25036_RESULT_SHA256,
        V25037_RESULT: EXPECTED_V25037_RESULT_SHA256,
    }
    for relative, digest in expected.items():
        if sha256(ordinary(relative, tracked=True)) != digest:
            raise RuntimeError("V2.50.41 consumed parent artifact drifted")
    protocol = read_object(PARENT_PROTOCOL, tracked=True)
    result = read_object(PARENT_RESULT, tracked=True)
    unsigned_protocol = dict(protocol)
    protocol_seal = unsigned_protocol.pop("protocol_payload_sha256", None)
    unsigned_result = dict(result)
    result_seal = unsigned_result.pop("result_payload_sha256", None)
    arms = result.get("arms")
    selected = [
        row
        for row in arms or []
        if isinstance(row, Mapping) and row.get("pair") in set(PAIR_NUMBERS)
    ] if isinstance(arms, list) else []
    if (
        protocol.get("role") != "v24281_neutral_single_shot_pair_preregistration"
        or protocol_seal != payload_sha256(unsigned_protocol)
        or result.get("role") != "v24281_neutral_single_shot_pair_result"
        or result_seal != payload_sha256(unsigned_result)
        or len(selected) != TASK_COUNT * 2
        or any(row.get("terminal") is not True for row in selected)
        or any(row.get("failure_type") is not None for row in selected)
        or result.get("source_policy", {}).get(
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read"
        )
        is not False
    ):
        raise RuntimeError("V2.50.41 consumed neutral parent invalid")
    return {
        "parent_protocol_sha256": EXPECTED_PARENT_PROTOCOL_SHA256,
        "parent_result_sha256": EXPECTED_PARENT_RESULT_SHA256,
        "v25036_result_sha256": EXPECTED_V25036_RESULT_SHA256,
        "v25037_result_sha256": EXPECTED_V25037_RESULT_SHA256,
        "neutral_source_sha256": EXPECTED_NEUTRAL_SOURCE_SHA256,
        "selected_pair_numbers": list(PAIR_NUMBERS),
        "selected_terminal_parent_rows": len(selected),
        "selected_pairs_previously_consumed": True,
        "selected_pairs_excluded_from_future_confirmation": True,
    }


def selected_queries() -> tuple[tuple[str, str], ...]:
    path = ordinary(NEUTRAL_SOURCE, tracked=True)
    if sha256(path) != EXPECTED_NEUTRAL_SOURCE_SHA256:
        raise RuntimeError("V2.50.41 neutral source drifted")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    raw: object | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "NEUTRAL_QUERY_PAIRS"
                for target in node.targets
            )
        ):
            raw = ast.literal_eval(node.value)
            break
    if not isinstance(raw, tuple) or len(raw) != 16:
        raise RuntimeError("V2.50.41 neutral query vector absent")
    values = tuple(raw[index] for index in PAIR_INDICES)
    if len(values) != TASK_COUNT:
        raise RuntimeError("V2.50.41 neutral pair denominator drifted")
    return tuple(adaptive.validate_seed_queries(pair) for pair in values)


def gates() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "all_tasks_terminal": True,
        "all_candidate_trace_capability_passed": True,
        "exact_candidate_provider_calls": TASK_COUNT,
        "exact_control_provider_calls": TASK_COUNT * 2,
        "provider_attempts_equal_calls": True,
        "exact_distinct_action_queries_per_candidate_task": 4,
        "exact_followup_queries_per_candidate_task": 2,
        "all_followups_have_seed_anchor_and_seed_title_novel_token": True,
        "all_control_query_vectors_observed_exactly": True,
        "minimum_candidate_distinct_action_sources": 12,
        "minimum_candidate_over_control_distinct_action_sources": 0.85,
        "maximum_candidate_over_control_input_tokens": 0.85,
        "maximum_candidate_over_control_total_tokens": 0.85,
        "zero_fetch_recursive_split_transport_or_hard_timeout": True,
    }


def run_tests() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for pattern, expected in TEST_SUITES:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"),
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                pattern,
                "-v",
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            check=False,
        )
        observed = completed.stdout.count(" ... ok")
        rows.append(
            {
                "pattern": pattern,
                "expected": expected,
                "observed": observed,
                "returncode": completed.returncode,
            }
        )
        total += observed
    return {
        "suites": rows,
        "expected": EXPECTED_TESTS,
        "observed": total,
        "passed": total == EXPECTED_TESTS
        and all(row["returncode"] == 0 and row["observed"] == row["expected"] for row in rows),
    }


def semantic_audit() -> dict[str, Any]:
    privileged_fields = {
        "benchmark_question_type", "question_type", "category", "task_category",
        "ground_truth", "answer_key", "mapping", "split", "reward",
    }
    privileged: list[str] = []
    evaluator: list[str] = []
    for relative in dependency_closure():
        path = ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            key: str | None = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value if isinstance(node.slice.value, str) else None
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            if key in privileged_fields:
                privileged.append(f"{relative}:{getattr(node, 'lineno', 0)}:{key}")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                text = ast.unparse(node).casefold()
                if any(term in text for term in ("official_eval", "evaluator", "ground_truth")):
                    evaluator.append(f"{relative}:{getattr(node, 'lineno', 0)}:{text}")
    return {
        "unexpected_privileged_field_accesses": privileged,
        "evaluator_capabilities": evaluator,
    }


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    if require_clean:
        clean_pushed()
    future = (BUILD_AUDIT, PROTOCOL, PREAUDIT, EXECUTION_START, RESULT, POSTAUDIT)
    tests = run_tests()
    semantic = semantic_audit()
    manifest = source_manifest(tracked=require_clean)
    checks = {
        "future_surface_pristine": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink() for path in future
        ),
        "consumed_parent_valid": bool(parent_binding()),
        "focused_and_parent_tests_pass": tests["passed"],
        "source_manifest_complete": set(manifest)
        == {
            *(str(path) for path in dependency_closure()),
            str(TEST), str(PARENT_PROTOCOL), str(PARENT_RESULT),
            str(V25036_RESULT), str(V25037_RESULT), str(NEUTRAL_SOURCE),
        },
        "unexpected_privileged_field_access_zero": not semantic[
            "unexpected_privileged_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": True,
        "protected_watchers_exact": bool(watcher_snapshot()),
        "shared_api_lease_inactive": lease_inactive(),
        "zero_network_model_search_fetch_or_evaluator_effect_before_activation": True,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25041_adaptive_single_request_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "tests": tests,
        "semantic_audit": semantic,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "parent_binding": parent_binding(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "protocol_generation": not findings,
            "external_effect": False,
            "benchmark_dev64_exact220_evaluator_or_sota": False,
        },
    }
    return seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25041_adaptive_single_request_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("source_manifest") != source_manifest(tracked=True)
        or copied.get("parent_binding") != parent_binding()
        or not sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.41 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    head = clean_pushed()
    build = validate_build(read_object(BUILD_AUDIT, tracked=True))
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, RESULT, POSTAUDIT)
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.41 protocol surface is not pristine")
    manifest = source_manifest(tracked=True)
    value = {
        "artifact_version": 1,
        "role": "v25041_adaptive_single_request_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "build_audit_sha256": sha256(ROOT / BUILD_AUDIT),
        "build_head": head,
        "parent_binding": build["parent_binding"],
        "population": {
            "task_count": TASK_COUNT,
            "selected_pair_numbers": list(PAIR_NUMBERS),
            "selected_seed_query_vector_sha256": payload_sha256(selected_queries()),
            "previously_consumed_and_excluded_from_confirmation": True,
        },
        "execution": {
            "candidate": "one_response_two_exact_seed_then_two_title_conditioned_followups",
            "control": "candidate_generated_same_four_queries_split_2_plus_2",
            "candidate_always_executes_before_dependent_control": True,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "candidate_provider_calls_per_task": 1,
            "control_provider_calls_per_task": 2,
            "max_retries": 1,
            "fetch_calls": 0,
            "standalone_generation_model_calls": 0,
            "evaluator_calls": 0,
            "endpoint": ENDPOINT,
            "model": MODEL,
            "search_context_size": "medium",
        },
        "gates": gates(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": SOURCE_POLICY,
        "authorization": {
            "one_development_capability_probe_after_separate_clean_pushed_start": True,
            "fresh_external_gate_design_only_if_all_gates_pass": True,
            "fresh_external_effect": False,
            "benchmark_dev64_exact220_evaluator_leaderboard_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = source_manifest(tracked=True)
    if (
        copied.get("role") != "v25041_adaptive_single_request_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("build_audit_sha256") != sha256(ROOT / BUILD_AUDIT)
        or copied.get("parent_binding") != parent_binding()
        or copied.get("population", {}).get("selected_seed_query_vector_sha256")
        != payload_sha256(selected_queries())
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization", {}).get(
            "benchmark_dev64_exact220_evaluator_leaderboard_or_sota"
        )
        is not False
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.41 protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    clean_pushed()
    protocol = validate_protocol(read_object(PROTOCOL, tracked=True))
    validate_build(read_object(BUILD_AUDIT, tracked=True))
    future = (PREAUDIT, EXECUTION_START, RESULT, POSTAUDIT)
    tests = run_tests()
    semantic = semantic_audit()
    conflicts = active_conflicts()
    checks = {
        "protocol_and_build_valid": True,
        "focused_and_parent_tests_pass": tests["passed"],
        "future_surface_pristine": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink() for path in future
        ),
        "source_manifest_unchanged": protocol["source_manifest"]
        == source_manifest(tracked=True),
        "protected_watchers_exact": protocol["protected_watchers"]
        == watcher_snapshot(),
        "shared_api_lease_inactive": lease_inactive(),
        "no_conflicting_experiment": not conflicts,
        "loopback_gpt56_endpoint_reachable": endpoint_ready(),
        "unexpected_privileged_field_access_zero": not semantic[
            "unexpected_privileged_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": True,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25041_adaptive_single_request_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "tests": tests,
        "semantic_audit": semantic,
        "active_conflict_pids": conflicts,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "execution_start_generation": not findings,
            "development_capability_effect": False,
            "benchmark_dev64_exact220_evaluator_or_sota": False,
        },
    }
    return seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v25041_adaptive_single_request_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("execution_start_generation")
        is not True
        or not sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.41 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    clean_pushed()
    protocol = validate_protocol(read_object(PROTOCOL, tracked=True))
    preaudit = validate_preaudit(read_object(PREAUDIT, tracked=True))
    future = (EXECUTION_START, RESULT, POSTAUDIT)
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.41 execution surface is not pristine")
    value = {
        "artifact_version": 1,
        "role": "v25041_adaptive_single_request_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preactivation_audit_sha256": sha256(ROOT / PREAUDIT),
        "selected_seed_query_vector_sha256": protocol["population"][
            "selected_seed_query_vector_sha256"
        ],
        "protected_watchers": watcher_snapshot(),
        "authorization": {
            "one_development_capability_probe": True,
            "retry_resume_selective_rerun": False,
            "fresh_external_or_benchmark_effect": False,
            "evaluator_or_sota": False,
        },
    }
    if preaudit["authorization"]["execution_start_generation"] is not True:
        raise RuntimeError("V2.50.41 preaudit withheld start authority")
    return seal(value, "execution_start_payload_sha256")


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25041_adaptive_single_request_execution_start"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("authorization", {}).get("one_development_capability_probe")
        is not True
        or copied.get("authorization", {}).get("retry_resume_selective_rerun")
        is not False
        or not sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.41 execution start drifted")
    return copied


def _client(arm: str, *, deadline: float) -> Any:
    if arm == "candidate":
        cls = adaptive.AdaptiveSingleRequestSearchClient
    elif arm == "control":
        cls = SourceOnlyRobustLatePageBoundSearchClient
    else:
        raise ValueError("V2.50.41 arm drifted")
    return cls(
        ENDPOINT,
        MODEL,
        visible_question="Consumed neutral public-documentation capability probe.",
        reasoning_effort="low",
        service_tier="priority",
        timeout=65,
        max_retries=1,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        max_workers=1,
        batch_size=8,
        search_context_size="medium",
        max_output_tokens=7_000,
        fetch_pages=False,
        fetch_workers=8,
        fetch_timeout=20,
        max_page_chars=5_000,
        hard_fetch_deadline_seconds=25,
        stage_callback=lambda _event: None,
    )


def _client_counters(client: Any) -> dict[str, int]:
    return {
        name: int(getattr(client, name, 0) or 0)
        for name in (
            "calls", "hosted_search_attempts", "tool_calls", "input_tokens",
            "output_tokens", "total_tokens", "fetch_calls", "fetch_failures",
            "recursive_split_requests", "transport_failures",
            "hard_total_wall_timeouts",
        )
    }


def run_pair(index: int) -> dict[str, Any]:
    if index not in PAIR_INDICES:
        raise ValueError("V2.50.41 pair index drifted")
    seeds = selected_queries()[PAIR_INDICES.index(index)]
    started = time.monotonic()
    deadline = started + TASK_DEADLINE_SECONDS
    candidate = _client("candidate", deadline=deadline)
    control = _client("control", deadline=deadline)
    failure_stage: str | None = None
    analysis: dict[str, Any] = {
        "followup_queries": tuple(),
        "distinct_source_urls": tuple(),
        "receipt": {
            "web_search_action_count": 0,
            "nonquery_action_count": 0,
            "distinct_action_query_count": 0,
            "seed_exact_first_order": False,
            "mixed_seed_followup_action_count": 0,
            "seed_action_after_followup_count": 0,
            "followup_query_count": 0,
            "followups_with_seed_anchor": 0,
            "followups_with_seed_title_novel_token": 0,
            "seed_source_count": 0,
            "seed_source_title_count": 0,
            "total_distinct_action_sources": 0,
            "trace_capability_passed": False,
            "query_title_url_payload_or_credential_persisted": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
    }
    control_exact_vectors = 0
    control_sources: set[str] = set()
    same_four_queries = False
    try:
        payload = candidate._request(list(seeds))
        analysis = adaptive.analyze_adaptive_trace(payload, seeds)
        followups = tuple(analysis["followup_queries"])
        if len(followups) == adaptive.FOLLOWUP_QUERY_COUNT:
            query_vector = (*seeds, *followups)
            same_four_queries = len(query_vector) == adaptive.TOTAL_QUERY_COUNT
            for chunk in (query_vector[:2], query_vector[2:]):
                observed = adaptive.observe_fixed_trace(
                    control._request(list(chunk)), chunk
                )
                control_exact_vectors += int(observed["exact_query_vector_observed"])
                control_sources.update(observed["distinct_source_urls"])
        else:
            failure_stage = "candidate_trace_not_replayable"
    except Exception as exc:
        failure_stage = f"{type(exc).__name__}"
    row = {
        "artifact_version": 1,
        "role": "v25041_adaptive_single_request_task_result",
        "protocol_id": PROTOCOL_ID,
        "pair": index + 1,
        "terminal": True,
        "failure_stage": failure_stage,
        "candidate_trace": dict(analysis["receipt"]),
        "candidate_provider": _client_counters(candidate),
        "control_provider": _client_counters(control),
        "control_exact_query_vectors": control_exact_vectors,
        "candidate_distinct_action_sources": len(analysis["distinct_source_urls"]),
        "control_distinct_action_sources": len(control_sources),
        "same_candidate_generated_four_query_vector_used_by_control": same_four_queries,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "query_title_url_page_provider_payload_or_credential_persisted": False,
        "benchmark_manifest_question_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "page_fetch_generation_model_or_evaluator_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    return validate_row(seal(row, "row_payload_sha256"))


def validate_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    candidate = copied.get("candidate_provider")
    control = copied.get("control_provider")
    receipt = copied.get("candidate_trace")
    provider_keys = {
        "calls", "hosted_search_attempts", "tool_calls", "input_tokens",
        "output_tokens", "total_tokens", "fetch_calls", "fetch_failures",
        "recursive_split_requests", "transport_failures", "hard_total_wall_timeouts",
    }
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "pair", "terminal",
            "failure_stage", "candidate_trace", "candidate_provider",
            "control_provider", "control_exact_query_vectors",
            "candidate_distinct_action_sources", "control_distinct_action_sources",
            "same_candidate_generated_four_query_vector_used_by_control",
            "wall_seconds", "query_title_url_page_provider_payload_or_credential_persisted",
            "benchmark_manifest_question_mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
            "page_fetch_generation_model_or_evaluator_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "retry_resume_skip_or_selective_rerun", "row_payload_sha256",
        }
        or copied.get("role") != "v25041_adaptive_single_request_task_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("pair") not in PAIR_NUMBERS
        or copied.get("terminal") is not True
        or copied.get("failure_stage") is not None
        and not isinstance(copied.get("failure_stage"), str)
        or not isinstance(receipt, Mapping)
        or adaptive.validate_capability_receipt(receipt) != receipt
        or not isinstance(candidate, Mapping)
        or not isinstance(control, Mapping)
        or not isinstance(
            copied.get("same_candidate_generated_four_query_vector_used_by_control"),
            bool,
        )
        or set(candidate) != provider_keys
        or set(control) != provider_keys
        or any(
            isinstance(provider.get(name), bool)
            or not isinstance(provider.get(name), int)
            or provider[name] < 0
            for provider in (candidate, control)
            for name in provider_keys
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in (
                "control_exact_query_vectors", "candidate_distinct_action_sources",
                "control_distinct_action_sources",
            )
        )
        or isinstance(copied.get("wall_seconds"), bool)
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or not math.isfinite(float(copied["wall_seconds"]))
        or float(copied["wall_seconds"]) < 0
        or any(
            copied.get(name) is not False
            for name in (
                "query_title_url_page_provider_payload_or_credential_persisted",
                "benchmark_manifest_question_mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "page_fetch_generation_model_or_evaluator_called",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_or_selective_rerun",
            )
        )
        or not sealed(copied, "row_payload_sha256")
    ):
        raise RuntimeError("V2.50.41 task result drifted")
    return copied


def aggregate(rows: Sequence[Mapping[str, Any]], *, wall_seconds: float) -> dict[str, Any]:
    checked = [validate_row(row) for row in rows]
    if len(checked) != TASK_COUNT or {row["pair"] for row in checked} != set(PAIR_NUMBERS):
        raise RuntimeError("V2.50.41 task denominator drifted")
    output: dict[str, Any] = {
        "tasks": TASK_COUNT,
        "terminal": sum(row["terminal"] for row in checked),
        "failures": sum(row["failure_stage"] is not None for row in checked),
        "candidate_trace_capability_passed": sum(
            row["candidate_trace"]["trace_capability_passed"] for row in checked
        ),
        "candidate_distinct_action_queries": sum(
            row["candidate_trace"]["distinct_action_query_count"] for row in checked
        ),
        "candidate_followup_queries": sum(
            row["candidate_trace"]["followup_query_count"] for row in checked
        ),
        "candidate_followups_with_seed_anchor": sum(
            row["candidate_trace"]["followups_with_seed_anchor"] for row in checked
        ),
        "candidate_followups_with_seed_title_novel_token": sum(
            row["candidate_trace"]["followups_with_seed_title_novel_token"]
            for row in checked
        ),
        "candidate_seed_sources": sum(
            row["candidate_trace"]["seed_source_count"] for row in checked
        ),
        "candidate_seed_source_titles": sum(
            row["candidate_trace"]["seed_source_title_count"] for row in checked
        ),
        "control_exact_query_vectors": sum(
            row["control_exact_query_vectors"] for row in checked
        ),
        "same_four_query_vector_tasks": sum(
            row["same_candidate_generated_four_query_vector_used_by_control"]
            for row in checked
        ),
        "candidate_distinct_action_sources": sum(
            row["candidate_distinct_action_sources"] for row in checked
        ),
        "control_distinct_action_sources": sum(
            row["control_distinct_action_sources"] for row in checked
        ),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_query_title_url_page_payload_or_credential": False,
    }
    for arm in ("candidate", "control"):
        for name in next(iter(checked))[f"{arm}_provider"]:
            output[f"{arm}_{name}"] = sum(
                row[f"{arm}_provider"][name] for row in checked
            )
    return output


def _ratio(candidate: float, control: float) -> float | None:
    return round(candidate / control, 12) if control else None


def decision(value: Mapping[str, Any]) -> dict[str, Any]:
    gate = gates()
    ratios = {
        "input_tokens": _ratio(
            float(value.get("candidate_input_tokens", 0)),
            float(value.get("control_input_tokens", 0)),
        ),
        "total_tokens": _ratio(
            float(value.get("candidate_total_tokens", 0)),
            float(value.get("control_total_tokens", 0)),
        ),
        "distinct_action_sources": _ratio(
            float(value.get("candidate_distinct_action_sources", 0)),
            float(value.get("control_distinct_action_sources", 0)),
        ),
    }
    checks = {
        "all_tasks_terminal": value.get("terminal") == TASK_COUNT,
        "zero_failures": value.get("failures") == 0,
        "all_candidate_trace_capability_passed": value.get(
            "candidate_trace_capability_passed"
        )
        == TASK_COUNT,
        "exact_provider_calls_and_attempts": value.get("candidate_calls")
        == value.get("candidate_hosted_search_attempts")
        == TASK_COUNT
        and value.get("control_calls")
        == value.get("control_hosted_search_attempts")
        == TASK_COUNT * 2,
        "exact_candidate_query_and_followup_counts": value.get(
            "candidate_distinct_action_queries"
        )
        == TASK_COUNT * 4
        and value.get("candidate_followup_queries") == TASK_COUNT * 2,
        "all_followups_have_seed_anchor_and_title_novelty": value.get(
            "candidate_followups_with_seed_anchor"
        )
        == value.get("candidate_followups_with_seed_title_novel_token")
        == TASK_COUNT * 2,
        "all_control_query_vectors_observed_exactly": value.get(
            "control_exact_query_vectors"
        )
        == TASK_COUNT * 2
        and value.get("same_four_query_vector_tasks") == TASK_COUNT,
        "candidate_absolute_source_yield": value.get(
            "candidate_distinct_action_sources", 0
        )
        >= gate["minimum_candidate_distinct_action_sources"],
        "candidate_relative_source_yield": ratios["distinct_action_sources"]
        is not None
        and ratios["distinct_action_sources"]
        >= gate["minimum_candidate_over_control_distinct_action_sources"],
        "candidate_input_cost": ratios["input_tokens"] is not None
        and ratios["input_tokens"]
        <= gate["maximum_candidate_over_control_input_tokens"],
        "candidate_total_cost": ratios["total_tokens"] is not None
        and ratios["total_tokens"]
        <= gate["maximum_candidate_over_control_total_tokens"],
        "zero_fetch_recursive_transport_or_timeout": all(
            value.get(f"{arm}_{name}") == 0
            for arm in ("candidate", "control")
            for name in (
                "fetch_calls", "fetch_failures", "recursive_split_requests",
                "transport_failures", "hard_total_wall_timeouts",
            )
        ),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "ratios": ratios,
        "capability_cost_source_gate_passed": passed,
        "fresh_external_gate_design_authorized": passed,
        "fresh_external_or_benchmark_effect_authorized": False,
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    rows = copied.get("rows")
    aggregate_value = copied.get("aggregate")
    recomputed = (
        aggregate(
            rows,
            wall_seconds=float(aggregate_value.get("batch_wall_seconds", -1)),
        )
        if isinstance(rows, list) and isinstance(aggregate_value, Mapping)
        else None
    )
    if (
        copied.get("role") != "v25041_adaptive_single_request_development_probe"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(rows, list)
        or len(rows) != TASK_COUNT
        or any(validate_row(row) != row for row in rows)
        or not isinstance(aggregate_value, Mapping)
        or recomputed != aggregate_value
        or copied.get("decision") != decision(aggregate_value)
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("protected_watchers_before") != watcher_snapshot()
        or copied.get("protected_watchers_after") != watcher_snapshot()
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization", {}).get(
            "fresh_external_or_benchmark_effect"
        )
        is not False
        or copied.get("authorization", {}).get("retry_resume_selective_rerun")
        is not False
        or not sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.41 development result drifted")
    return copied


def run_probe() -> dict[str, Any]:
    clean_pushed()
    protocol = validate_protocol(read_object(PROTOCOL, tracked=True))
    start = validate_start(read_object(EXECUTION_START, tracked=True))
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (RESULT, POSTAUDIT)):
        raise RuntimeError("V2.50.41 result surface is not pristine")
    if active_conflicts():
        raise RuntimeError("V2.50.41 conflicting experiment active")
    if protocol["protected_watchers"] != watcher_snapshot():
        raise RuntimeError("V2.50.41 protected watcher drifted")
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25041_adaptive_single_request_probe_v1",
        purpose="consumed_neutral_adaptive_single_request_capability_probe",
        path=ROOT / LEASE,
    ):
        if active_conflicts():
            raise RuntimeError("V2.50.41 conflict appeared after lease")
        with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(run_pair, PAIR_INDICES))
    rows.sort(key=lambda row: int(row["pair"]))
    aggregate_value = aggregate(rows, wall_seconds=time.monotonic() - started)
    result_decision = decision(aggregate_value)
    value = seal(
        {
            "artifact_version": 1,
            "role": "v25041_adaptive_single_request_development_probe",
            "protocol_id": PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "protocol_sha256": sha256(ROOT / PROTOCOL),
            "execution_start_sha256": sha256(ROOT / EXECUTION_START),
            "rows": rows,
            "aggregate": aggregate_value,
            "decision": result_decision,
            "protected_watchers_before": start["protected_watchers"],
            "protected_watchers_after": watcher_snapshot(),
            "source_policy": SOURCE_POLICY,
            "authorization": {
                "fresh_external_gate_design": result_decision[
                    "fresh_external_gate_design_authorized"
                ],
                "fresh_external_or_benchmark_effect": False,
                "dev64_exact220_evaluator_leaderboard_or_sota": False,
                "retry_resume_selective_rerun": False,
            },
        },
        "result_payload_sha256",
    )
    validate_result(value)
    publish(RESULT, value)
    return value


def _forbidden_keys(value: object) -> set[str]:
    forbidden = {"query", "queries", "title", "url", "page", "payload", "credential"}
    hits: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in forbidden:
                hits.add(str(key))
            hits.update(_forbidden_keys(item))
    elif isinstance(value, list):
        for item in value:
            hits.update(_forbidden_keys(item))
    return hits


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    clean_pushed()
    protocol = validate_protocol(read_object(PROTOCOL, tracked=True))
    result = validate_result(read_object(RESULT, tracked=True))
    checks = {
        "protocol_and_result_valid": True,
        "result_contains_no_forbidden_content_keys": not _forbidden_keys(result),
        "decision_recomputes_exactly": result["decision"]
        == decision(result["aggregate"]),
        "source_manifest_unchanged": protocol["source_manifest"]
        == source_manifest(tracked=True),
        "protected_watchers_unchanged": result["protected_watchers_before"]
        == result["protected_watchers_after"]
        == watcher_snapshot(),
        "shared_api_lease_inactive": lease_inactive(),
        "no_active_probe_process": not active_conflicts(),
        "no_retry_resume_or_selective_rerun": result["authorization"][
            "retry_resume_selective_rerun"
        ]
        is False,
        "no_external_benchmark_evaluator_or_sota_authority": result[
            "authorization"
        ]["fresh_external_or_benchmark_effect"]
        is False
        and result["authorization"][
            "dev64_exact220_evaluator_leaderboard_or_sota"
        ]
        is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    passed = not findings and result["decision"][
        "capability_cost_source_gate_passed"
    ]
    value = {
        "artifact_version": 1,
        "role": "v25041_adaptive_single_request_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "capability_cost_source_gate_passed": passed,
        "source_policy": SOURCE_POLICY,
        "authorization": {
            "fresh_external_gate_design": passed,
            "fresh_external_or_benchmark_effect": False,
            "dev64_exact220_evaluator_leaderboard_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("build-audit", "protocol", "preaudit", "start", "run", "postaudit"),
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), PREAUDIT
    elif args.command == "start":
        value, path = build_start(), EXECUTION_START
    elif args.command == "run":
        value, path = run_probe(), RESULT
        print(json.dumps({"path": str(path), "decision": value["decision"], "aggregate": value["aggregate"]}, sort_keys=True))
        return
    else:
        value, path = build_postaudit(), POSTAUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
