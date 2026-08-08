#!/usr/bin/env python3
"""Staged control plane for the V2.49.25 external gate."""

from __future__ import annotations

import argparse
import ast
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24925_sparse_target_value_external_contract as contract  # noqa: E402


SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
PRIVILEGED = frozenset(
    {
        "category",
        "question_type",
        "task_category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)
TEST_SUITES = (
    (Path("tests/test_v24925_sparse_target_value_external.py"), 10),
    (Path("tests/test_v24924_visible_row_table_compactor.py"), 10),
    (Path("tests/test_v24921_target_value_coverage_projector.py"), 9),
    (Path("tests/test_v24842_atomic_table_header_closure.py"), 11),
)


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


def _historical_hits(key: str) -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-F",
            key,
            contract.HISTORICAL_BOUNDARY_COMMIT,
            "--",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RuntimeError("V2.49.25 historical scan failed")
    return [line for line in completed.stdout.splitlines() if line]


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.25 requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.25 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.25 expected JSON object")
    return value


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


def _ordinary_tracked(relative: Path) -> Path:
    path = ROOT / relative
    tracked = subprocess.run(
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
        or relative.parts[:1] == ("evaluation",)
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not tracked
    ):
        raise RuntimeError(f"V2.49.25 dependency drifted: {relative}")
    return path


def dependency_manifest() -> dict[str, str]:
    return {
        str(relative): contract.sha256(_ordinary_tracked(relative))
        for relative in contract.BUILD_SOURCES
    }


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TEST_SUITES:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                path.name,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": contract.payload_sha256(completed.stdout),
            }
        )
    return sum(row["observed"] for row in rows), all(
        row["passed"] for row in rows
    ), rows


def _ast_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    secrets: list[str] = []
    evaluator_imports: list[str] = []
    for relative in contract.RUNTIME_SOURCES:
        source = _ordinary_tracked(relative).read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            if any("evaluate_v24925" in name for name in names):
                evaluator_imports.append(f"{relative}:{node.lineno}")
            key = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value.casefold()
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value.casefold()
            if key in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
    return sorted(fields), sorted(secrets), sorted(evaluator_imports)


def _endpoint() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _future_paths() -> tuple[Path, ...]:
    return (
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _read(ROOT / contract.PARENT_BUILD_AUDIT)
    tests_observed, tests_passed, suites = _run_tests()
    fields, secrets, evaluator_imports = _ast_findings()
    _git("cat-file", "-e", f"{contract.HISTORICAL_BOUNDARY_COMMIT}^{{commit}}")
    historical_hits = {key: _historical_hits(key) for key in contract.TARGET_KEYS}
    checks = {
        "v24924_parent_build_audit_valid": parent.get("audit_valid") is True
        and parent.get("findings") == [],
        "focused_tests_exact40": tests_passed and tests_observed == 40,
        "runtime_privileged_field_access_zero": not fields,
        "runtime_evaluator_import_zero": not evaluator_imports,
        "credential_literal_zero": not secrets,
        "confirmatory_target_literals_absent_at_historical_boundary": not any(
            bool(paths) for paths in historical_hits.values()
        ),
        "confirmatory_targets_fixed_before_response_read": True,
        "prior_entity_exclusion_artifact_exists": (ROOT / contract.EXCLUSION_TASKS).is_file(),
        "same_30k_5k_model_prompt_and_budget": True,
        "entropy_information_gain_shadow_only": True,
        "gpt56_endpoint_reachable_without_provider_request": _endpoint(),
        "shared_api_lease_inactive": _lease_inactive(),
        "protected_watchers_unchanged": bool(contract.protected_watcher_snapshot()),
        "future_surface_pristine": _pristine(_future_paths()),
    }
    manifest = dependency_manifest()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24925_sparse_target_value_external_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "historical_boundary_commit": contract.HISTORICAL_BOUNDARY_COMMIT,
        "confirmatory_targets_fixed_unread": list(contract.TARGET_KEYS),
        "historical_target_literal_hits": historical_hits,
        "parent_build_audit_sha256": contract.sha256(
            ROOT / contract.PARENT_BUILD_AUDIT
        ),
        "prior_entity_exclusion_artifact_sha256": contract.sha256(
            ROOT / contract.EXCLUSION_TASKS
        ),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": contract.payload_sha256(manifest),
        "tests": {
            "expected": 40,
            "observed": tests_observed,
            "passed": tests_passed,
            "suites": suites,
        },
        "runtime_semantic_audit": {
            "privileged_runtime_field_accesses": fields,
            "evaluator_imports": evaluator_imports,
            "credential_literal_hits": secrets,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question", "frozen_public_pages"],
            "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "same_page_bytes_for_both_arms": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "protocol_publication": all(checks.values()),
            "confirmatory_target_fetch_or_model": False,
            "external_launch": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
            "sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    audit = _read(ROOT / contract.BUILD_AUDIT)
    manifest = dependency_manifest()
    checks = {
        "build_audit_valid": audit.get("audit_valid") is True
        and audit.get("findings") == []
        and contract.sealed(audit, "audit_payload_sha256"),
        "manifest_unchanged": audit.get("dependency_manifest") == manifest,
        "confirmatory_targets_equal_build_freeze": audit.get(
            "confirmatory_targets_fixed_unread"
        )
        == list(contract.TARGET_KEYS),
        "future_surface_pristine": _pristine(_future_paths()),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24925_sparse_target_value_external_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "population": {
            "confirmatory_target_keys": list(contract.TARGET_KEYS),
            "selection_seed_sha256": contract.payload_sha256(
                contract.SELECTION_SEED
            ),
            "selected_tasks": contract.SELECTED_COUNT,
            "rows_per_task": contract.ROWS_PER_TASK,
            "selected_entities": contract.SELECTED_ENTITY_COUNT,
            "prior_v24923_entities_excluded": True,
            "task_entities_disjoint": True,
            "complete_record_intersection_required": True,
            "selection_fixed_before_target_response_read": True,
        },
        "shared_prefix": {
            "official_requests": 1 + len(contract.TARGETS),
            "responses_fetched_once_before_arm_branch": True,
            "same_frozen_page_bytes_for_both_arms": True,
            "no_search_provider_or_tavily_required": True,
        },
        "execution": {
            "arms": list(contract.ARMS),
            "only_treatment": "exact_visible_row_sparse_table_compaction_before_target_value_projection",
            "total_character_cap_both_arms": 30_000,
            "per_page_character_cap_both_arms": 5_000,
            "same_model_prompt_output_cap_attempt_count_and_concurrency": True,
            "model": contract.MODEL,
            "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
            "model_slot_cap": contract.MODEL_SLOT_CAP,
            "task_wall_seconds": contract.TASK_WALL_SECONDS,
            "failure_as_zero": True,
            "no_resume_retry_skip_or_selective_rerun": True,
            "prediction_freeze_before_evaluator": True,
            "mechanism_gate_before_evaluator": {
                "minimum_projection_unequal_tasks": 8,
                "minimum_dropped_table_rows": 1,
                "failure_as_zero_tasks": 0,
            },
            "protected_watchers": contract.protected_watcher_snapshot(),
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": contract.payload_sha256(manifest),
        "forward_dependency_manifest": {
            str(path): manifest[str(path)] for path in contract.RUNTIME_SOURCES
        },
        "evaluator_absent_from_forward_dependency_manifest": str(
            contract.EVALUATOR
        )
        not in {str(path) for path in contract.RUNTIME_SOURCES},
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question", "frozen_public_pages"],
            "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "preactivation_audit_generation": all(checks.values()),
            "confirmatory_target_fetch_or_model": False,
            "single_external_forward": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    observed, passed, suites = _run_tests()
    fields, secrets, evaluator_imports = _ast_findings()
    manifest = dependency_manifest()
    checks = {
        "protocol_sealed": contract.sealed(protocol, "protocol_payload_sha256"),
        "protocol_findings_empty": protocol.get("findings") == [],
        "manifest_unchanged": protocol.get("dependency_manifest") == manifest,
        "focused_tests_exact40": passed and observed == 40,
        "runtime_privileged_field_access_zero": not fields,
        "runtime_evaluator_import_zero": not evaluator_imports,
        "credential_literal_zero": not secrets,
        "gpt56_endpoint_reachable_without_provider_request": _endpoint(),
        "shared_api_lease_inactive": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "future_surface_pristine": _pristine(_future_paths()[1:]),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24925_sparse_target_value_external_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "tests": {"expected": 40, "observed": observed, "passed": passed, "suites": suites},
        "runtime_semantic_audit": {
            "privileged_runtime_field_accesses": fields,
            "evaluator_imports": evaluator_imports,
            "credential_literal_hits": secrets,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "first_confirmatory_target_fetch_or_model_effect_started": False,
        "authorization": {
            "execution_start_generation": all(checks.values()),
            "single_external_forward": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    audit = _read(ROOT / contract.PREAUDIT)
    checks = {
        "protocol_sealed": contract.sealed(protocol, "protocol_payload_sha256"),
        "preactivation_audit_valid": audit.get("audit_valid") is True
        and audit.get("findings") == []
        and contract.sealed(audit, "audit_payload_sha256"),
        "endpoint_reachable": _endpoint(),
        "lease_inactive": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "future_surface_pristine": _pristine(_future_paths()[2:]),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24925_sparse_target_value_external_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized_not_started" if all(checks.values()) else "rejected",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "first_confirmatory_target_fetch_or_model_effect_started": False,
        "authorization": {
            "single_external_forward": all(checks.values()),
            "retry_resume_skip_or_selective_rerun": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start"))
    args = parser.parse_args()
    _clean_pushed()
    if args.command == "build-audit":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    else:
        value, path = build_start(), contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(f"V2.49.25 {args.command} failed: {value['findings']}")
    _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "audit_valid": value.get("audit_valid"), "status": value.get("status"), "findings": value.get("findings"), "authorization": value.get("authorization")}, sort_keys=True))


if __name__ == "__main__":
    main()
