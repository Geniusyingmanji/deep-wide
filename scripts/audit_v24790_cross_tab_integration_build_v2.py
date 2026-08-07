#!/usr/bin/env python3
"""Clean-pushed build audit for corrected V2.47.90 integration.

The audit consumes tracked public protocol/source/tests only.  It never opens
V2.47.84 outputs or the V2.47.89 private population and performs no network,
model, search, fetch, benchmark-forward, quality, or evaluator effect.  A GO
freezes the integration build and authorizes only an append-only execution
contract/runner build; package, activation, launch, evaluator, dev64, and 220
remain closed.
"""

from __future__ import annotations

import ast
import copy
import fcntl
import hashlib
import json
import os
import re
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

from deepwide_agent import v24784_projection_funnel_execution_contract as old_contract  # noqa: E402
from deepwide_agent import v24790_cross_tab_integration as integration  # noqa: E402
from deepwide_agent import v24790_full_catalog_selected_target as selected  # noqa: E402
from scripts import preregister_v24790_cross_tab_external_v2 as protocol  # noqa: E402


DATE = "20260807"
OUTPUT = Path(f"results/v24790_cross_tab_integration_build_audit_v2_{DATE}.json")
PROTOCOL = protocol.OUTPUT
INTEGRATION = Path("src/deepwide_agent/v24790_cross_tab_integration.py")
INTEGRATION_TEST = Path("tests/test_v24790_cross_tab_integration.py")
SELECTED = Path("src/deepwide_agent/v24790_full_catalog_selected_target.py")
SELECTED_TEST = Path("tests/test_v24790_full_catalog_selected_target.py")
SOURCE = Path("scripts/audit_v24790_cross_tab_integration_build_v2.py")
TEST = Path("tests/test_audit_v24790_cross_tab_integration_build_v2.py")
RUNTIME_SOURCES = (INTEGRATION, SELECTED)
SOURCES = (
    PROTOCOL,
    Path("scripts/preregister_v24790_cross_tab_external_v2.py"),
    Path("tests/test_preregister_v24790_cross_tab_external_v2.py"),
    INTEGRATION,
    INTEGRATION_TEST,
    SELECTED,
    SELECTED_TEST,
    Path("src/deepwide_agent/v24365_entity_segment_projection.py"),
    Path("tests/test_v24365_entity_segment_projection.py"),
    Path("src/deepwide_agent/v24786_projection_support_cross_tab_observer.py"),
    Path("tests/test_v24786_projection_support_cross_tab_observer.py"),
    Path("src/deepwide_agent/v24778_staged_fetch_fallback_runtime.py"),
    Path("tests/test_v24778_staged_fetch_fallback_runtime.py"),
    SOURCE,
    TEST,
)
TEST_SUITES = (
    (INTEGRATION_TEST, 6, 180),
    (SELECTED_TEST, 7, 120),
    (Path("tests/test_v24365_entity_segment_projection.py"), 9, 120),
    (Path("tests/test_v24786_projection_support_cross_tab_observer.py"), 9, 120),
    (Path("tests/test_v24778_staged_fetch_fallback_runtime.py"), 13, 180),
    (Path("tests/test_preregister_v24790_cross_tab_external_v2.py"), 7, 120),
    (TEST, 7, 120),
)
EXPECTED_TEST_COUNT = 58
PRIVILEGED = frozenset(
    {"answer", "answer_key", "category", "evaluator", "gold", "ground_truth", "mapping", "question_type", "reward", "score", "split", "task_category"}
)
FORBIDDEN_IMPORT_ROOTS = {"httpx", "os", "pathlib", "requests", "socket", "subprocess"}
FORBIDDEN_MARKERS = (
    "evaluation" + "/",
    "outputs" + "/",
    "population_" + "private",
    "private_" + "truth",
    "frozen_" + "predictions.jsonl",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(value) for value in SECRET_PREFIXES) + r")[A-Za-z0-9_-]{16,}")


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink() or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.90 build audit expected public file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.90 build audit expected JSON object")
    return value


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20, check=True).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=False).returncode == 0


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == old_contract.payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(PROTOCOL)
    try:
        protocol.validate_protocol(value)
    except RuntimeError:
        return False
    return bool(
        value.get("protocol_id") == protocol.PROTOCOL_ID
        and value.get("authorization", {}).get("v1_integration_build") is False
        and value.get("authorization", {}).get(
            "append_only_full_catalog_selected_target_integration_build"
        ) is True
        and value.get("authorization", {}).get("runner_or_control_plane_build") is False
        and value.get("authorization", {}).get("one_external_forward_launch") is False
        and value.get("source_policy", {}).get(
            "v24789_private_population_truth_provenance_or_quality_opened_or_hashed"
        ) is False
        and value.get("parent_v1", {}).get(
            "runner_lease_model_search_fetch_or_forward_effect_before_revocation"
        ) is False
        and _sealed(value, "protocol_payload_sha256")
    )


def ast_findings() -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    effects: list[str] = []
    markers: list[str] = []
    secrets: list[str] = []
    for relative in RUNTIME_SOURCES:
        source = _ordinary(relative).read_text(encoding="utf-8")
        markers.extend(f"{relative}:{marker}" for marker in FORBIDDEN_MARKERS if marker in source)
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key: str | None = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                key = node.slice.value
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"get", "pop", "setdefault"} and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                key = node.args[0].value
            if key is not None and key.casefold() in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            else:
                names = []
            imports.extend(f"{relative}:{node.lineno}:{name}" for name in names if any(token in name.casefold() for token in ("evaluator", "gold")))
            effects.extend(f"{relative}:{node.lineno}:{name}" for name in names if name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS)
    return tuple(sorted(set(values)) for values in (fields, imports, effects, markers, secrets))  # type: ignore[return-value]


def implementation_contract() -> dict[str, Any]:
    integration_source = _ordinary(INTEGRATION).read_text(encoding="utf-8")
    selected_source = _ordinary(SELECTED).read_text(encoding="utf-8")
    value = {
        "integration_statuses": list(integration.STATUSES),
        "public_result_keys": sorted(integration.PUBLIC_RESULT_KEYS),
        "base_runtime_call_count": integration_source.count("base.run_v24778_task("),
        "selected_observer_call_count": integration_source.count("selected.build_selected_target_cross_tab("),
        "one_target_catalog_builder_call_count": selected_source.count("build_target_segment_catalog("),
        "full_catalog_validator_call_count": selected_source.count("segment.validate_target_segment_catalog(catalog)"),
        "row_major_selector_present": "select_first_unknown_target" in selected_source,
        "other_entity_boundary_attestation_present": '"other_visible_entities_retained_as_segment_boundaries": True' in selected_source,
        "catalog_mutation_disabled": '"full_target_catalog_and_projection_vector_mutated": False' in selected_source,
        "single_target_rebuild_disabled": '"single_target_catalog_rebuilt": False' in selected_source,
        "prediction_change_disabled": '"prediction_bytes_changed_by_observer": False' in selected_source,
        "additional_effect_frozen_zero": '"additional_model_search_fetch_or_evaluator_effect": 0' in integration_source,
        "positive_credit_disabled": '"positive_entropy_or_task_credit_assigned": False' in integration_source,
        "valid": False,
    }
    value["valid"] = bool(
        value["integration_statuses"] == list(protocol.v1.STATUSES)
        and value["base_runtime_call_count"] == 1
        and value["selected_observer_call_count"] == 1
        and value["one_target_catalog_builder_call_count"] == 0
        and value["full_catalog_validator_call_count"] == 1
        and all(value[name] for name in (
            "row_major_selector_present", "other_entity_boundary_attestation_present",
            "catalog_mutation_disabled", "single_target_rebuild_disabled",
            "prediction_change_disabled", "additional_effect_frozen_zero",
            "positive_credit_disabled",
        ))
    )
    return value


def _run_test(path: Path, timeout: int) -> tuple[bool, int, str]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", path.name, "-v"],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())), "USER": os.environ.get("USER", "azureuser"), "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=timeout, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return completed.returncode == 0, observed, hashlib.sha256(completed.stdout.encode()).hexdigest()


def _lease_inactive() -> bool:
    path = ROOT / old_contract.LEASE_PATH
    if path.is_symlink():
        return False
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_runners() -> list[int]:
    completed = subprocess.run(["ps", "-eo", "pid=,comm=,args="], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20, check=False)
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 3 and "python" in parts[1].casefold() and any(marker in parts[2] for marker in ("run_v24784_projection_funnel", "run_v24790_cross_tab")):
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    fields, imports, effects, markers, secrets = ast_findings()
    implementation = implementation_contract()
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed, output_sha = _run_test(path, timeout)
        suites.append({"path": str(path), "expected": expected, "observed": observed, "output_sha256": output_sha, "passed": passed and observed == expected})
    observed = sum(row["observed"] for row in suites)
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    parent_valid = _parent_valid()
    watchers = old_contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    runners = _active_runners()
    future_paths = (
        OUTPUT,
        Path(f"results/v24790_cross_tab_execution_contract_v2_{DATE}.json"),
        Path(f"results/v24790_cross_tab_package_audit_v2_{DATE}.json"),
        Path(f"results/v24790_cross_tab_preactivation_audit_v2_{DATE}.json"),
        Path(f"results/v24790_cross_tab_activation_v2_{DATE}.json"),
        Path(f"outputs/v24790_cross_tab_external_v2_{DATE}"),
    )
    future_pristine = all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in future_paths)
    findings: list[str] = []
    if head != remote: findings.append("v24790_integration_source_commit_not_pushed")
    if not clean: findings.append("v24790_integration_source_worktree_not_clean")
    if not tracked: findings.append("v24790_integration_source_not_tracked")
    if not parent_valid: findings.append("v24790_corrected_protocol_drifted")
    if not implementation["valid"]: findings.append("v24790_integration_contract_drifted")
    if fields: findings.append("privileged_runtime_field_access")
    if imports: findings.append("evaluator_or_gold_import_in_runtime")
    if effects: findings.append("direct_external_effect_capability_in_runtime")
    if markers: findings.append("private_output_or_evaluator_marker_in_runtime")
    if secrets: findings.append("credential_literal_in_runtime")
    if any(not row["passed"] for row in suites) or observed != EXPECTED_TEST_COUNT: findings.append("v24790_integration_regression_failed_or_count_drifted")
    if not lease: findings.append("shared_api_lease_active")
    if runners: findings.append("v24784_or_v24790_runner_active")
    if not future_pristine: findings.append("v24790_future_surface_not_pristine")
    valid = not findings
    value = {
        "artifact_version": 2,
        "role": "v24790_cross_tab_integration_build_audit_v2",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"protocol_sha256": _sha256(PROTOCOL), "valid": parent_valid},
        "implementation_contract": implementation,
        "source_manifest": manifest,
        "source_manifest_sha256": old_contract.payload_sha256(manifest),
        "git": {"head": head, "target_main": remote, "head_equals_target_main": head == remote, "worktree_clean": clean, "all_sources_tracked": tracked},
        "tests": {"expected": EXPECTED_TEST_COUNT, "observed": observed, "suites": suites, "passed": all(row["passed"] for row in suites) and observed == EXPECTED_TEST_COUNT, "network_model_search_fetch_benchmark_or_evaluator_called": False},
        "label_blind_audit": {"privileged_runtime_field_accesses": fields, "evaluator_or_gold_imports": imports, "direct_external_effect_capability_imports": effects, "private_output_or_evaluator_marker_hits": markers, "credential_literal_hits": secrets, "passed": not fields and not imports and not effects and not markers and not secrets},
        "runtime_state": {"protected_watchers": watchers, "shared_api_lease_inactive": lease, "active_runner_pids": runners, "future_surface_pristine": future_pristine, "external_forward_launched_by_audit": False, "evaluator_called_by_audit": False},
        "source_policy": {
            "v24784_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24789_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": valid,
        "authorization": {
            "append_only_execution_contract_and_runner_build": valid,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "paired_dev64": False, "exact220": False,
            "entropy_or_credit_experiment": False, "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = old_contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v24790_cross_tab_integration_build_audit_v2"
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or copied.get("parent", {}).get("valid") is not True
        or copied.get("implementation_contract", {}).get("valid") is not True
        or copied.get("git", {}).get("head_equals_target_main") is not True
        or copied.get("git", {}).get("worktree_clean") is not True
        or copied.get("git", {}).get("all_sources_tracked") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("active_runner_pids") != []
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("source_policy") != {
            "v24784_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24789_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        }
        or copied.get("authorization") != {
            "append_only_execution_contract_and_runner_build": True,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "paired_dev64": False, "exact220": False,
            "entropy_or_credit_experiment": False, "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.90 integration build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = validate_audit(build_audit())
    publish_new(ROOT / OUTPUT, audit)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": audit["audit_valid"], "findings": audit["findings"], "test_count": audit["tests"]["observed"], "runner_build_authorized": audit["authorization"]["append_only_execution_contract_and_runner_build"], "external_launch_authorized": False}, sort_keys=True))
