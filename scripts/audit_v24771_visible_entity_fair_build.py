#!/usr/bin/env python3
"""Clean-build audit for V2.47.70 visible-entity fair recovery.

The audit reads repository sources, the public V2.47.69 diagnosis, git/process
identity, and the shared lease lock.  It does not open V2.47.65 task results,
questions, queries, URLs, pages, predictions, private population, mapping,
gold, evaluator, score, or credential surfaces and performs no external
network, model, search, fetch, benchmark, or evaluator effect.
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

from deepwide_agent import v24765_zero_effect_execution_contract as contract  # noqa: E402
from scripts import diagnose_v24769_zero_effect_reachability as diagnosis  # noqa: E402


AUDIT = Path("results/v24771_visible_entity_fair_build_audit_v1_20260807.json")
RUNTIME = Path(
    "src/deepwide_agent/v24770_visible_entity_fair_semantic_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v24770_visible_entity_fair_semantic_runtime.py"
)
SOURCES = (
    RUNTIME,
    RUNTIME_TEST,
    Path("scripts/audit_v24771_visible_entity_fair_build.py"),
    Path("tests/test_audit_v24771_visible_entity_fair_build.py"),
    diagnosis.OUTPUT,
    Path("scripts/diagnose_v24769_zero_effect_reachability.py"),
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("src/deepwide_agent/v24754_generic_structured_page_adapter.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("src/deepwide_agent/v24365_entity_segment_projection.py"),
    Path("src/deepwide_agent/v24339_active_evidence_support.py"),
    Path("src/deepwide_agent/v24333_programmatic_support_catalog.py"),
    Path("src/deepwide_agent/v24547_alias_surface_observability.py"),
    Path("src/deepwide_agent/v24668_visible_surface_information_gain_runtime.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
)
RUNTIME_SOURCES = (
    RUNTIME,
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("src/deepwide_agent/v24754_generic_structured_page_adapter.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("src/deepwide_agent/v24365_entity_segment_projection.py"),
    Path("src/deepwide_agent/v24547_alias_surface_observability.py"),
    Path("src/deepwide_agent/v24668_visible_surface_information_gain_runtime.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
)
TEST_SUITES = (
    (RUNTIME_TEST, 14, 180, False),
    (Path("tests/test_v24365_entity_segment_projection.py"), 9, 180, False),
    (Path("tests/test_v24756_zero_effect_structured_integration.py"), 6, 180, False),
    (Path("tests/test_v24743_generic_record_binding.py"), 12, 180, False),
    (Path("tests/test_v24754_generic_structured_page_adapter.py"), 9, 180, False),
    (Path("tests/test_v24668_visible_surface_information_gain_runtime.py"), 8, 180, False),
    (Path("tests/test_v24765_zero_effect_package.py"), 10, 180, False),
    (Path("tests/test_prototype_v24202_label_blind_webswarm_adapter.py"), 18, 120, True),
    (Path("tests/test_audit_v24202_label_blind_webswarm_adapter.py"), 4, 120, True),
    (Path("tests/test_audit_v24771_visible_entity_fair_build.py"), 5, 120, False),
)
EXPECTED_TEST_COUNT = 95
RUNNER_MARKERS = (
    "scripts/run_v24765_zero_effect_external.py",
    "scripts/run_v24765_zero_effect_task.py",
    "scripts/run_v24770",
)
PRIVILEGED = frozenset(
    {
        "answer",
        "answer_key",
        "category",
        "evaluator",
        "gold",
        "ground_truth",
        "mapping",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
EVALUATOR_IMPORT_MARKERS = (
    "official_eval",
    "official_evaluator",
    "evaluator_mapping",
    "finalize_v24",
)
FORBIDDEN_SOURCE_MARKERS = (
    "evaluation" + "/",
    "overall_20250916" + ".jsonl",
    "population_" + "private",
    "private_" + "truth",
    "evaluator_" + "mapping",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.71 expected repository file: {relative}")
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
        raise RuntimeError("V2.47.71 expected JSON object")
    return value


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = diagnosis.validate_diagnosis(_read(diagnosis.OUTPUT))
    parents = value.get("parents")
    return bool(
        isinstance(parents, Mapping)
        and all(
            isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
            for digest in parents.values()
        )
        and value.get("status")
        == "target_fair_acquisition_is_the_next_necessary_falsification"
        and value.get("diagnosis", {}).get("current_primary_bottleneck")
        == "target_fair_retrieval_reachability_and_same_value_support_conversion_before_unchanged_two_source_gate"
        and value.get("authorization", {}).get(
            "append_only_visible_entity_scheduler_implementation"
        )
        is True
        and value.get("authorization", {}).get(
            "same_population_forward_retry_resume_or_rerun"
        )
        is False
        and value.get("authorization", {}).get("fresh_external_protocol_design")
        is False
    )


def ast_findings() -> tuple[list[str], list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    markers: list[str] = []
    secrets: list[str] = []
    for relative in RUNTIME_SOURCES:
        source = _ordinary(relative).read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        markers.extend(
            f"{relative}:{marker}"
            for marker in FORBIDDEN_SOURCE_MARKERS
            if marker in source
        )
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value
            if key is not None and key.casefold() in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            else:
                names = []
            imports.extend(
                f"{relative}:{node.lineno}:{name}"
                for name in names
                if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS)
            )
    return (
        sorted(set(fields)),
        sorted(set(imports)),
        sorted(set(markers)),
        sorted(set(secrets)),
    )


def implementation_contract() -> dict[str, Any]:
    source = _ordinary(RUNTIME).read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    classes = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    value = {
        "runtime_input_keys": ["opaque_id", "question"],
        "visible_entity_count": 4,
        "logical_query_count": 4,
        "fetch_target_cap": 10,
        "model_call_cap": 2,
        "search_results_per_query": 3,
        "visible_schema": ["Organization", "Founded", "Country"],
        "required_functions_present": all(
            name in functions
            for name in (
                "extract_visible_entities",
                "visible_entity_query_vector",
                "select_visible_entity_fair_leads",
                "run_v24770_task",
                "validate_result",
            )
        ),
        "search_wrapper_present": "VisibleEntityFairSearchClient" in classes,
        "parent_runtime_called_once_in_source": source.count("run_v24756_task(") == 1,
        "semantic_projector_called_in_runtime": "build_target_segment_catalog(" in source,
        "query_self_proof_disabled": '"query": ""' in source,
        "unknown_only_writeback_guard_present": 'support["baseline_cell_unknown"] is not True' in source,
        "two_source_projection_binding_present": "support_sources.issubset(projection_sources[pair])" in source,
        "parent_semantic_conflict_abstention_present": "semantic_has_conflict or len(values) > 1" in source,
        "positive_credit_disabled": '"positive_entropy_or_task_credit_assigned": False' in source,
        "evaluator_authority_disabled": '"benchmark_launch_or_evaluator_authorized": False' in source,
        "valid": False,
    }
    value["valid"] = bool(
        value["required_functions_present"]
        and value["search_wrapper_present"]
        and value["parent_runtime_called_once_in_source"]
        and value["semantic_projector_called_in_runtime"]
        and value["query_self_proof_disabled"]
        and value["unknown_only_writeback_guard_present"]
        and value["two_source_projection_binding_present"]
        and value["parent_semantic_conflict_abstention_present"]
        and value["positive_credit_disabled"]
        and value["evaluator_authority_disabled"]
    )
    return value


def _run_test(
    path: Path, timeout: int, needs_repo_pythonpath: bool
) -> tuple[bool, int, str]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    if needs_repo_pythonpath:
        environment["PYTHONPATH"] = str(ROOT)
        command = [str(ROOT / ".venv-eval/bin/python"), "-B", str(ROOT / path), "-v"]
    else:
        command = [
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
        ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return (
        completed.returncode == 0,
        observed,
        hashlib.sha256(completed.stdout.encode()).hexdigest(),
    )


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
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
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        cwd=ROOT,
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
        if len(parts) < 3 or "python" not in parts[1].casefold():
            continue
        if any(marker in parts[2] for marker in RUNNER_MARKERS):
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    fields, imports, markers, secrets = ast_findings()
    implementation = implementation_contract()
    suites = []
    for path, expected, timeout, needs_repo_pythonpath in TEST_SUITES:
        passed, observed, output_sha = _run_test(
            path, timeout, needs_repo_pythonpath
        )
        suites.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "output_sha256": output_sha,
                "passed": passed and observed == expected,
            }
        )
    observed = sum(row["observed"] for row in suites)
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    parent_valid = _parent_valid()
    watchers = contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    runners = _active_runners()
    future_paths = (
        AUDIT,
        Path("results/v24772_visible_entity_fair_external_preregistration_v1_20260807.json"),
        Path("results/v24772_visible_entity_fair_preactivation_audit_v1_20260807.json"),
        Path("results/v24772_visible_entity_fair_activation_v1_20260807.json"),
        Path("results/v24772_visible_entity_fair_execution_start_v1_20260807.json"),
        Path("results/v24772_visible_entity_fair_forward_result_v1_20260807.json"),
        Path("outputs/v24772_visible_entity_fair_external_v1_20260807"),
    )
    future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in future_paths
    )
    findings: list[str] = []
    if head != remote:
        findings.append("v24771_source_commit_not_pushed")
    if not clean:
        findings.append("v24771_source_worktree_not_clean")
    if not tracked:
        findings.append("v24771_source_not_tracked")
    if not parent_valid:
        findings.append("v24769_parent_drifted")
    if not implementation["valid"]:
        findings.append("v24770_implementation_contract_drifted")
    if fields:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if markers:
        findings.append("private_or_evaluator_marker_in_runtime")
    if secrets:
        findings.append("credential_literal_in_runtime")
    if any(not row["passed"] for row in suites) or observed != EXPECTED_TEST_COUNT:
        findings.append("regression_failed_or_count_drifted")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24765_or_v24770_runner_active")
    if not future_pristine:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24771_visible_entity_fair_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "diagnosis_sha256": _sha256(diagnosis.OUTPUT),
            "valid": parent_valid,
        },
        "implementation_contract": implementation,
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "expected": EXPECTED_TEST_COUNT,
            "observed": observed,
            "suites": suites,
            "passed": all(row["passed"] for row in suites)
            and observed == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_input_keys": ["opaque_id", "question"],
            "privileged_runtime_field_accesses": fields,
            "evaluator_imports": imports,
            "private_or_evaluator_marker_hits": markers,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not markers and not secrets,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": lease,
            "active_runner_pids": runners,
            "future_surface_pristine": future_pristine,
            "external_forward_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "source_policy": {
            "v24765_private_task_result_page_prediction_or_visible_task_opened_or_hashed": False,
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_external_protocol_design": not findings,
            "fresh_external_preactivation_audit": False,
            "fresh_external_activation_or_launch": False,
            "same_population_forward_retry_resume_or_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v24771_visible_entity_fair_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parent", {}).get("valid") is not True
        or copied.get("implementation_contract", {}).get("valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive")
        is not True
        or copied.get("runtime_state", {}).get("active_runner_pids") != []
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("authorization")
        != {
            "fresh_disjoint_external_protocol_design": True,
            "fresh_external_preactivation_audit": False,
            "fresh_external_activation_or_launch": False,
            "same_population_forward_retry_resume_or_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.71 build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    validate_audit(audit)
    publish_new(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "test_count": audit["tests"]["observed"],
                "external_protocol_design_authorized": audit["authorization"][
                    "fresh_disjoint_external_protocol_design"
                ],
            },
            sort_keys=True,
        )
    )
