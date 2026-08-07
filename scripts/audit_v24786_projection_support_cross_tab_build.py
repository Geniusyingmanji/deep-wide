#!/usr/bin/env python3
"""Clean-pushed build audit for the pure V2.47.86 cross-tab observer.

This audit consumes only tracked public source/tests and the tracked V2.47.85
counts-only diagnosis that explicitly authorized this build.  It never opens
V2.47.84 outputs, visible tasks, predictions, pages, private catalogs, the
V2.47.83 truth/quality population, benchmark mappings, labels, gold, scores,
rewards, or evaluator data.  It performs no network/model/search/fetch effect.

A clean audit freezes only the observer build.  It may authorize a separate
fresh-disjoint population *design*, but cannot authorize integration, runner,
preactivation, activation, external launch, evaluator access, dev64, or 220.
"""

from __future__ import annotations

import ast
import copy
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

from deepwide_agent import (  # noqa: E402
    v24784_projection_funnel_execution_contract as contract,
)
from deepwide_agent import (  # noqa: E402
    v24786_projection_support_cross_tab_observer as observer,
)
from scripts import diagnose_v24785_v24784_projection_closure as parent  # noqa: E402


DATE = "20260807"
OUTPUT = Path(
    f"results/v24786_projection_support_cross_tab_build_audit_v1_{DATE}.json"
)
PARENT = parent.OUTPUT
RUNTIME = Path(
    "src/deepwide_agent/v24786_projection_support_cross_tab_observer.py"
)
RUNTIME_TEST = Path(
    "tests/test_v24786_projection_support_cross_tab_observer.py"
)
SOURCE = Path("scripts/audit_v24786_projection_support_cross_tab_build.py")
TEST = Path("tests/test_audit_v24786_projection_support_cross_tab_build.py")
SOURCES = (
    PARENT,
    RUNTIME,
    RUNTIME_TEST,
    SOURCE,
    TEST,
    Path("src/deepwide_agent/v24781_projection_conversion_funnel.py"),
    Path("tests/test_v24781_projection_conversion_funnel.py"),
    Path("src/deepwide_agent/v24365_entity_segment_projection.py"),
    Path("tests/test_v24365_entity_segment_projection.py"),
    Path("src/deepwide_agent/v24333_programmatic_support_catalog.py"),
    Path("tests/test_v24333_programmatic_support_catalog.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("tests/test_v24743_generic_record_binding.py"),
)
RUNTIME_SOURCES = (RUNTIME,)
TEST_SUITES = (
    (RUNTIME_TEST, 9, 120),
    (Path("tests/test_v24781_projection_conversion_funnel.py"), 9, 120),
    (Path("tests/test_v24365_entity_segment_projection.py"), 9, 120),
    (Path("tests/test_v24333_programmatic_support_catalog.py"), 9, 120),
    (Path("tests/test_v24743_generic_record_binding.py"), 12, 120),
    (TEST, 7, 120),
)
EXPECTED_TEST_COUNT = 55
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
FORBIDDEN_MARKERS = (
    "evaluation" + "/",
    "outputs" + "/",
    "population_" + "private",
    "private_" + "truth",
    "frozen_" + "predictions.jsonl",
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
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.86 build audit expected public file: {relative}")
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
        raise RuntimeError("V2.47.86 build audit expected JSON object")
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
    value = _read(PARENT)
    try:
        parent.validate_diagnosis(value)
    except RuntimeError:
        return False
    return bool(
        value.get("authorization", {}).get(
            "append_only_cross_tab_observer_build"
        )
        is True
        and value.get("authorization", {}).get("activation_or_external_launch")
        is False
        and value.get("authorization", {}).get("paired_dev64") is False
        and value.get("authorization", {}).get("exact220") is False
        and value.get("source_policy", {}).get(
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed"
        )
        is False
        and value.get("next_falsification", {}).get(
            "cross_tab_observer_must_count_unknown_by_source_multiplicity_jointly"
        )
        is True
        and value.get("next_falsification", {}).get(
            "cross_tab_observer_must_count_catalog_quarantine_dispositions"
        )
        is True
        and _sealed(value, "diagnosis_payload_sha256")
    )


def ast_findings() -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    effects: list[str] = []
    markers: list[str] = []
    secrets: list[str] = []
    forbidden_imports = {
        "asyncio",
        "http",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    for relative in RUNTIME_SOURCES:
        source = _ordinary(relative).read_text(encoding="utf-8")
        markers.extend(
            f"{relative}:{marker}" for marker in FORBIDDEN_MARKERS if marker in source
        )
        if SECRET.search(source):
            secrets.append(str(relative))
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
                if any(token in name.casefold() for token in ("evaluator", "gold"))
            )
            effects.extend(
                f"{relative}:{node.lineno}:{name}"
                for name in names
                if name.split(".")[0] in forbidden_imports
            )
    return tuple(
        sorted(set(values))
        for values in (fields, imports, effects, markers, secrets)
    )  # type: ignore[return-value]


def implementation_contract() -> dict[str, Any]:
    source = _ordinary(RUNTIME).read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    value = {
        "required_functions_present": all(
            name in functions
            for name in (
                "_catalog_group_dispositions",
                "_projection_groups",
                "_table_changes",
                "_projection_backed_support_pairs",
                "_compute",
                "build_projection_support_cross_tab",
                "validate_receipt",
            )
        ),
        "fixed_catalog_dispositions": list(observer.CATALOG_DISPOSITIONS),
        "fixed_catalog_quarantine_dispositions": list(
            observer.CATALOG_QUARANTINE_DISPOSITIONS
        ),
        "fixed_proposal_dispositions": list(observer.PROPOSAL_DISPOSITIONS),
        "fixed_group_change_dispositions": list(
            observer.GROUP_CHANGE_DISPOSITIONS
        ),
        "catalog_validated_before_observation": source.count(
            "segment.validate_target_segment_catalog(catalog)"
        )
        == 1,
        "catalog_quarantine_replay_present": source.count(
            "support._candidate_support(target, pages)"
        )
        == 1,
        "target_local_projection_source_grouping_present": source.count(
            "output[(binding, str(item[\"normalized_value_sha256\"]))].add(source)"
        )
        == 1,
        "baseline_candidate_table_change_replay_present": source.count(
            "changes = _table_changes(baseline, candidate, targets)"
        )
        == 1,
        "strict_joint_rederived_by_validator": source.count(
            'copied["strict_joint_safe_change_group_count"] != strict_joint'
        )
        == 1,
        "input_nonmutation_check_present": "observer mutated its private inputs"
        in source,
        "positive_credit_disabled": (
            '"positive_entropy_or_task_credit_assigned": False' in source
        ),
        "launch_authority_disabled": (
            '"benchmark_launch_or_evaluator_authorized": False' in source
        ),
        "valid": False,
    }
    value["valid"] = all(
        value[name]
        for name in (
            "required_functions_present",
            "catalog_validated_before_observation",
            "catalog_quarantine_replay_present",
            "target_local_projection_source_grouping_present",
            "baseline_candidate_table_change_replay_present",
            "strict_joint_rederived_by_validator",
            "input_nonmutation_check_present",
            "positive_credit_disabled",
            "launch_authority_disabled",
        )
    )
    return value


def _run_test(path: Path, timeout: int) -> tuple[bool, int, str]:
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
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
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


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    fields, imports, effects, markers, secrets = ast_findings()
    implementation = implementation_contract()
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed, output_sha = _run_test(path, timeout)
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
    findings: list[str] = []
    if head != remote:
        findings.append("v24786_source_commit_not_pushed")
    if not clean:
        findings.append("v24786_source_worktree_not_clean")
    if not tracked:
        findings.append("v24786_source_not_tracked")
    if not parent_valid:
        findings.append("v24785_parent_authorization_drifted")
    if not implementation["valid"]:
        findings.append("v24786_observer_contract_drifted")
    if fields:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_or_gold_import_in_runtime")
    if effects:
        findings.append("external_effect_capability_in_runtime")
    if markers:
        findings.append("private_output_or_evaluator_marker_in_runtime")
    if secrets:
        findings.append("credential_literal_in_runtime")
    if any(not row["passed"] for row in suites) or observed != EXPECTED_TEST_COUNT:
        findings.append("v24786_regression_failed_or_count_drifted")
    audit_valid = not findings
    value = {
        "artifact_version": 1,
        "role": "v24786_projection_support_cross_tab_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "v24785_diagnosis_sha256": _sha256(PARENT),
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
            "privileged_runtime_field_accesses": fields,
            "evaluator_or_gold_imports": imports,
            "external_effect_capability_imports": effects,
            "private_output_or_evaluator_marker_hits": markers,
            "credential_literal_hits": secrets,
            "passed": not fields
            and not imports
            and not effects
            and not markers
            and not secrets,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "external_forward_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "source_policy": {
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "only_tracked_public_source_tests_and_counts_only_parent_opened": True,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        },
        "authorization": {
            "cross_tab_observer_build_frozen": audit_valid,
            "fresh_disjoint_population_design": audit_valid,
            "trusted_child_integration_or_runner_build": False,
            "package_or_preactivation_audit_generation": False,
            "activation_or_external_launch": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
        "findings": findings,
        "audit_valid": audit_valid,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v24786_projection_support_cross_tab_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parent", {}).get("valid") is not True
        or copied.get("implementation_contract", {}).get("valid") is not True
        or copied.get("git", {}).get("head_equals_target_main") is not True
        or copied.get("git", {}).get("worktree_clean") is not True
        or copied.get("git", {}).get("all_sources_tracked") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("source_policy")
        != {
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "only_tracked_public_source_tests_and_counts_only_parent_opened": True,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        }
        or copied.get("authorization")
        != {
            "cross_tab_observer_build_frozen": True,
            "fresh_disjoint_population_design": True,
            "trusted_child_integration_or_runner_build": False,
            "package_or_preactivation_audit_generation": False,
            "activation_or_external_launch": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.86 build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    audit = validate_audit(build_audit())
    publish_new(ROOT / OUTPUT, audit)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "test_count": audit["tests"]["observed"],
                "fresh_population_design_authorized": audit["authorization"][
                    "fresh_disjoint_population_design"
                ],
                "external_launch_authorized": audit["authorization"][
                    "activation_or_external_launch"
                ],
            },
            sort_keys=True,
        )
    )
