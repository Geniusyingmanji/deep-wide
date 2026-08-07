#!/usr/bin/env python3
"""Public-only freeze audit for the V2.47.89 fresh population.

The evaluator-only population is checked only with ``lstat`` and git path
membership.  Its bytes are never opened, parsed, copied, imported, or hashed.
The audit validates the public receipt, visible-only contract, full visible
history exclusion, failed-V2.47.87 pristine boundary, source accounting,
tests, clean-pushed repository state, protected watchers, and inactive lease.
It performs no network/model/search/fetch/benchmark/evaluator effect.
"""

from __future__ import annotations

import ast
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import stat
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
from scripts import design_v24789_cross_tab_population as design  # noqa: E402


DATE = "20260807"
AUDIT = Path(f"results/v24789_cross_tab_population_freeze_audit_v1_{DATE}.json")
PUBLIC = design.OUTPUT
VISIBLE = design.CONTRACT
PRIVATE = design.PRIVATE
SOURCE = Path("scripts/audit_v24789_cross_tab_population_freeze.py")
TEST = Path("tests/test_audit_v24789_cross_tab_population_freeze.py")
PUBLIC_SOURCES = (
    Path("scripts/design_v24789_cross_tab_population.py"),
    Path("tests/test_design_v24789_cross_tab_population.py"),
    Path("scripts/diagnose_v24788_v24787_population_capacity.py"),
    Path("tests/test_diagnose_v24788_v24787_population_capacity.py"),
    Path("src/deepwide_agent/v24786_projection_support_cross_tab_observer.py"),
    Path("tests/test_v24786_projection_support_cross_tab_observer.py"),
    PUBLIC,
    VISIBLE,
    design.PARENT,
    SOURCE,
    TEST,
)
TEST_SUITES = (
    (Path("tests/test_design_v24789_cross_tab_population.py"), 8, 120),
    (Path("tests/test_diagnose_v24788_v24787_population_capacity.py"), 6, 120),
    (Path("tests/test_v24786_projection_support_cross_tab_observer.py"), 9, 120),
    (TEST, 7, 120),
)
EXPECTED_TEST_COUNT = 30
RUNNER_MARKERS = (
    "scripts/run_v24784_projection_funnel",
    "scripts/run_v24787",
    "scripts/run_v24789",
    "scripts/run_v24790",
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
        raise RuntimeError(f"V2.47.89 freeze audit expected public file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    if relative == PRIVATE:
        raise RuntimeError("V2.47.89 private population bytes are audit-inaccessible")
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_public(relative: Path) -> dict[str, Any]:
    if relative == PRIVATE:
        raise RuntimeError("V2.47.89 private population is audit-inaccessible")
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.89 freeze audit expected JSON object")
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


def _public_scope_clean() -> bool:
    return (
        _git("status", "--porcelain", "--", *(str(path) for path in PUBLIC_SOURCES))
        == ""
    )


def _private_path_receipt() -> dict[str, Any]:
    path = ROOT / PRIVATE
    try:
        mode = os.lstat(path).st_mode
    except OSError:
        mode = 0
    return {
        "relative_path": str(PRIVATE),
        "under_evaluation_directory": PRIVATE.parts[:1] == ("evaluation",),
        "tracked": _tracked(PRIVATE),
        "ordinary_file_by_lstat_without_content_read": stat.S_ISREG(mode),
        "symlink": stat.S_ISLNK(mode),
        "bytes_opened_parsed_imported_copied_or_hashed_by_audit": False,
    }


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _visible_tasks() -> list[dict[str, str]]:
    spec = importlib.util.spec_from_file_location(
        "v24789_cross_tab_visible_freeze_audit", _ordinary(VISIBLE)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("V2.47.89 visible contract import spec drifted")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tasks = module.task_vector()
    if not isinstance(tasks, list):
        raise RuntimeError("V2.47.89 visible task vector drifted")
    return tasks


def _entities(tasks: list[dict[str, str]]) -> list[str]:
    pattern = re.compile(r"<ENTITIES>\n(.*?)\n</ENTITIES>", flags=re.DOTALL)
    entities: list[str] = []
    for task in tasks:
        match = pattern.search(str(task.get("question", "")))
        if match is None:
            raise RuntimeError("V2.47.89 visible entity block drifted")
        lines = match.group(1).splitlines()
        if len(lines) != design.TASK_SIZE:
            raise RuntimeError("V2.47.89 visible row count drifted")
        for index, line in enumerate(lines, 1):
            prefix = f"{index}. "
            if not line.startswith(prefix) or not line[len(prefix) :].strip():
                raise RuntimeError("V2.47.89 visible entity numbering drifted")
            entities.append(line[len(prefix) :].strip())
    return entities


def label_blind_contract_findings() -> tuple[list[str], list[str], list[str]]:
    source = _ordinary(VISIBLE).read_text(encoding="utf-8")
    tree = ast.parse(source)
    fields: list[str] = []
    imports: list[str] = []
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
            fields.append(f"{VISIBLE}:{node.lineno}:{key}")
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        else:
            names = []
        imports.extend(
            f"{VISIBLE}:{node.lineno}:{name}"
            for name in names
            if any(token in name.casefold() for token in ("evaluator", "gold"))
        )
    secrets = [
        str(path)
        for path in PUBLIC_SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    return tuple(sorted(set(values)) for values in (fields, imports, secrets))  # type: ignore[return-value]


def population_contract() -> dict[str, Any]:
    public = _read_public(PUBLIC)
    design.validate_public(public)
    tasks = _visible_tasks()
    entities = _entities(tasks)
    historical_visible, historical_canonical = design.historical_entities()
    canonical = {design._normalizer()(entity) for entity in entities}
    task_keys = sorted({key for task in tasks for key in task})
    failed_surfaces_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (design.failed.OUTPUT, design.failed.PRIVATE, design.failed.CONTRACT)
    )
    target = public.get("future_target_selection_contract", {})
    value = {
        "public_design_valid": True,
        "public_role": public.get("role"),
        "public_selection_rule": public.get("eligibility_and_selection", {}).get("rule"),
        "public_current_tree_reads": public.get("network", {}).get("current_immutable_ror_tree_reads"),
        "public_current_record_reads": public.get("network", {}).get("current_immutable_ror_record_reads"),
        "public_cumulative_tree_reads": public.get("network", {}).get("cumulative_capacity_plus_generation_tree_reads"),
        "public_cumulative_record_reads": public.get("network", {}).get("cumulative_capacity_plus_generation_record_reads"),
        "failed_v24787_surfaces_pristine": failed_surfaces_pristine,
        "task_count": len(tasks),
        "task_keys": task_keys,
        "all_task_keysets_exact": all(set(task) == {"opaque_id", "question"} for task in tasks),
        "opaque_id_count": len({task.get("opaque_id") for task in tasks}),
        "entity_count": len(entities),
        "unique_entity_count": len(set(entities)),
        "unique_canonical_entity_count": len(canonical),
        "historical_visible_entity_count": len(historical_visible),
        "historical_canonical_entity_count": len(historical_canonical),
        "literal_overlap_with_history": len(set(entities) & historical_visible),
        "canonical_overlap_with_history": len(canonical & historical_canonical),
        "visible_identity_vector_matches_public_hash": contract.payload_sha256(entities)
        == public.get("visible_identity_vector_sha256"),
        "visible_contract_matches_public_hash": _sha256(VISIBLE)
        == public.get("visible_contract_sha256"),
        "parent_diagnosis_matches_public_hash": _sha256(design.PARENT)
        == public.get("parent_v24788_diagnosis_sha256"),
        "one_unknown_target_future_contract_frozen": target
        == {
            "implemented_by_population_design": False,
            "baseline_prediction_must_be_frozen_before_target_selection": True,
            "maximum_selected_baseline_unknown_target_per_task": 1,
            "selection_order": "canonical_table_row_major_value_cells",
            "zero_baseline_unknown_target_disposition": "no_target_mechanism_failure",
            "private_truth_provenance_quality_or_evaluator_used_for_selection": False,
            "target_selection_uses_only_current_visible_task_and_frozen_baseline": True,
            "two_independent_same_value_safety_gate_relaxed": False,
            "cross_task_or_cross_group_aggregation_used_as_joint": False,
        },
        "private_file_hash_from_public_receipt_recomputed_by_audit": False,
        "valid": False,
    }
    value["valid"] = bool(
        value["public_role"] == "v24789_cross_tab_population_design"
        and value["public_selection_rule"] == design.SELECTION_RULE
        and value["public_current_tree_reads"] == 1
        and value["public_current_record_reads"] == 3_482
        and value["public_cumulative_tree_reads"] == 6
        and value["public_cumulative_record_reads"] == 20_892
        and value["failed_v24787_surfaces_pristine"]
        and value["task_count"] == 8
        and value["task_keys"] == ["opaque_id", "question"]
        and value["all_task_keysets_exact"]
        and value["opaque_id_count"] == 8
        and value["entity_count"] == 32
        and value["unique_entity_count"] == 32
        and value["unique_canonical_entity_count"] == 32
        and value["historical_visible_entity_count"] == 4_816
        and value["historical_canonical_entity_count"] == 4_816
        and value["literal_overlap_with_history"] == 0
        and value["canonical_overlap_with_history"] == 0
        and value["visible_identity_vector_matches_public_hash"]
        and value["visible_contract_matches_public_hash"]
        and value["parent_diagnosis_matches_public_hash"]
        and value["one_unknown_target_future_contract_frozen"]
    )
    return value


def _run_test(path: Path, timeout: int) -> tuple[bool, int, str]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", path.name, "-v"],
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
    return completed.returncode == 0, observed, hashlib.sha256(completed.stdout.encode()).hexdigest()


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
        if len(parts) >= 3 and "python" in parts[1].casefold() and any(marker in parts[2] for marker in RUNNER_MARKERS):
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in PUBLIC_SOURCES}
    private = _private_path_receipt()
    population = population_contract()
    fields, imports, secrets = label_blind_contract_findings()
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed, output_sha = _run_test(path, timeout)
        suites.append({"path": str(path), "expected": expected, "observed": observed, "output_sha256": output_sha, "passed": passed and observed == expected})
    observed = sum(row["observed"] for row in suites)
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    public_clean = _public_scope_clean()
    public_tracked = all(_tracked(path) for path in PUBLIC_SOURCES)
    watchers = contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    runners = _active_runners()
    future_paths = (
        AUDIT,
        Path(f"results/v24790_cross_tab_external_preregistration_v1_{DATE}.json"),
        Path(f"outputs/v24790_cross_tab_external_v1_{DATE}"),
    )
    future_pristine = all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in future_paths)
    findings: list[str] = []
    if head != remote:
        findings.append("v24789_freeze_source_commit_not_pushed")
    if not public_clean:
        findings.append("v24789_public_source_scope_not_clean")
    if not public_tracked:
        findings.append("v24789_public_source_not_tracked")
    if not all((private["under_evaluation_directory"], private["tracked"], private["ordinary_file_by_lstat_without_content_read"], not private["symlink"], not private["bytes_opened_parsed_imported_copied_or_hashed_by_audit"])):
        findings.append("v24789_private_path_separation_drifted")
    if not population["valid"]:
        findings.append("v24789_public_population_contract_drifted")
    if fields:
        findings.append("visible_contract_privileged_field_access")
    if imports:
        findings.append("visible_contract_evaluator_or_gold_import")
    if secrets:
        findings.append("credential_literal_in_public_source")
    if any(not row["passed"] for row in suites) or observed != EXPECTED_TEST_COUNT:
        findings.append("v24789_freeze_regression_failed_or_count_drifted")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24784_v24789_or_v24790_runner_active")
    if not future_pristine:
        findings.append("v24789_v24790_future_surface_not_pristine")
    audit_valid = not findings
    value = {
        "artifact_version": 1,
        "role": "v24789_cross_tab_population_freeze_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "public_population_contract": population,
        "private_population_path_receipt": private,
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "git": {"head": head, "target_main": remote, "head_equals_target_main": head == remote, "public_source_scope_clean": public_clean, "all_public_sources_tracked": public_tracked},
        "tests": {"expected": EXPECTED_TEST_COUNT, "observed": observed, "suites": suites, "passed": all(row["passed"] for row in suites) and observed == EXPECTED_TEST_COUNT, "network_model_search_fetch_benchmark_or_evaluator_called": False},
        "label_blind_audit": {"visible_contract_privileged_field_accesses": fields, "visible_contract_evaluator_or_gold_imports": imports, "credential_literal_hits": secrets, "passed": not fields and not imports and not secrets},
        "runtime_state": {"protected_watchers": watchers, "shared_api_lease_inactive": lease, "active_runner_pids": runners, "future_surface_pristine": future_pristine, "external_forward_launched_by_audit": False, "evaluator_called_by_audit": False},
        "source_policy": {
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "v24789_private_population_bytes_opened_parsed_imported_copied_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": audit_valid,
        "authorization": {
            "inert_v24790_protocol_publication": audit_valid,
            "trusted_child_integration_or_runner_build": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
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
    private = copied.get("private_population_path_receipt", {})
    if (
        copied.get("role") != "v24789_cross_tab_population_freeze_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("public_population_contract", {}).get("valid") is not True
        or private.get("tracked") is not True
        or private.get("ordinary_file_by_lstat_without_content_read") is not True
        or private.get("symlink") is not False
        or private.get("bytes_opened_parsed_imported_copied_or_hashed_by_audit") is not False
        or copied.get("git", {}).get("head_equals_target_main") is not True
        or copied.get("git", {}).get("public_source_scope_clean") is not True
        or copied.get("git", {}).get("all_public_sources_tracked") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("active_runner_pids") != []
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("source_policy")
        != {
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "v24789_private_population_bytes_opened_parsed_imported_copied_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        }
        or copied.get("authorization")
        != {
            "inert_v24790_protocol_publication": True,
            "trusted_child_integration_or_runner_build": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.89 population freeze audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = validate_audit(build_audit())
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"], "findings": audit["findings"], "test_count": audit["tests"]["observed"], "private_population_bytes_opened_or_hashed": False, "inert_protocol_authorized": audit["authorization"]["inert_v24790_protocol_publication"]}, sort_keys=True))
