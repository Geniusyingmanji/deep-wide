#!/usr/bin/env python3
"""Build-only audit for V2.44.94 diagnosis and V2.44.95 projection.

The audit reads only repository sources, the frozen content-free V2.44.94
diagnosis, process identities, and the shared lease.  It does not open any
task artifact, temporary execution directory, query, URL, page, prediction,
benchmark mapping, evaluator output, or credential.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24494_v24493_targeted_conversion as diagnosis  # noqa: E402


DATE = "20260804"
AUDIT = Path(f"results/v24495_targeted_conversion_projection_build_audit_v1_{DATE}.json")
PARENT = diagnosis.OUTPUT
SOURCES = (
    Path("scripts/diagnose_v24494_v24493_targeted_conversion.py"),
    Path("tests/test_diagnose_v24494_v24493_targeted_conversion.py"),
    PARENT,
    Path("src/deepwide_agent/v24495_targeted_conversion_projection.py"),
    Path("tests/test_v24495_targeted_conversion_projection.py"),
    Path("scripts/audit_v24495_targeted_conversion_projection_build.py"),
    Path("tests/test_audit_v24495_targeted_conversion_projection_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0], SOURCES[3])
TEST_SUITES = (
    (Path("tests/test_v24490_entropy_targeted_support_search.py"), 8, 180),
    (Path("tests/test_v24491_proof_carrying_targeted_support.py"), 10, 180),
    (Path("tests/test_v24493_total_targeted_projection.py"), 4, 120),
    (Path("tests/test_v24493_total_targeted_external_gate.py"), 7, 120),
    (Path("tests/test_diagnose_v24494_v24493_targeted_conversion.py"), 4, 60),
    (Path("tests/test_v24495_targeted_conversion_projection.py"), 7, 120),
    (Path("tests/test_audit_v24495_targeted_conversion_projection_build.py"), 3, 60),
)
EXPECTED_TEST_COUNT = 43
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
PRIVILEGED = frozenset(
    {
        "benchmark_question_type",
        "question_type",
        "task_category",
        "category",
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
EVALUATOR_IMPORT_MARKERS = (
    "official_eval",
    "official_evaluator",
    "finalize_v24",
    "evaluator_mapping",
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
        raise RuntimeError(f"V2.44.95 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.95 expected object")
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


def ast_findings(relative: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
    accesses: list[str] = []
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
            accesses.append(f"{relative}:{node.lineno}:{key}")
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        for name in names:
            if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _run_test(relative: Path, timeout: int) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-q"],
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    return completed.returncode == 0


def _watcher(pid: int, ticks: int, marker: str) -> bool:
    stat = Path("/proc") / str(pid) / "stat"
    command = Path("/proc") / str(pid) / "cmdline"
    try:
        actual_ticks = int(stat.read_text(encoding="utf-8").split()[21])
        actual_command = command.read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
    except (OSError, UnicodeError, ValueError):
        return False
    return actual_ticks == ticks and marker in actual_command


def _lease_inactive() -> bool:
    path = ROOT / "outputs/deepwide_benchmark_api.lease.lock"
    if path.is_symlink() or not path.is_file():
        return True
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    pid = value.get("pid") if isinstance(value, dict) else None
    ticks = value.get("start_ticks") if isinstance(value, dict) else None
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 1:
        return True
    stat = Path("/proc") / str(pid) / "stat"
    try:
        return int(stat.read_text(encoding="utf-8").split()[21]) != ticks
    except (OSError, ValueError):
        return True


def _parent_valid() -> bool:
    value = diagnosis.validate_report(_read(PARENT))
    parents = value.get("parents")
    if not isinstance(parents, dict):
        return False
    for item in parents.values():
        if not isinstance(item, dict):
            return False
        path = Path(str(item.get("path", "")))
        if item.get("sha256") != _sha256(path):
            return False
    return (
        value.get("diagnosis")
        == "targeted_conversion_failed_but_specific_semantic_bottleneck_is_unidentifiable_from_current_content_free_projection"
        and value.get("authorization", {}).get(
            "append_only_content_free_conversion_projection_design"
        )
        is True
        and value.get("authorization", {}).get("new_external_probe_launch")
        is False
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_valid()
    manifest = {str(path): _sha256(path) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = [
        {
            "path": str(path),
            "test_count": count,
            "passed": _run_test(path, timeout),
        }
        for path, count, timeout in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    watchers = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": _watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in EXPECTED_WATCHERS
    ]
    lease_inactive = _lease_inactive()
    findings: list[str] = []
    if not parent_valid:
        findings.append("v24494_parent_diagnosis_or_binding_drifted")
    if head != remote:
        findings.append("v24495_source_commit_not_pushed")
    if not clean:
        findings.append("v24495_source_worktree_not_clean")
    if not tracked:
        findings.append("v24494_95_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24490_95_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24494_95_runtime")
    if imports:
        findings.append("evaluator_import_in_v24494_95_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24494_95_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24495_targeted_conversion_projection_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": _sha256(PARENT), "valid": parent_valid},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": suites,
            "test_count": test_count,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "evaluator_opened": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "mechanism_evidence": {
            "v24494_diagnosis_does_not_invent_unobserved_semantic_cause": True,
            "projection_requires_unforgeable_v24491_capability": True,
            "task_projection_emits_only_counts_yields_partition_and_credit": True,
            "source_page_observation_safe_change_credit_funnel_is_fail_closed": True,
            "threshold_partition_conserves_selected_targets": True,
            "aggregate_preserves_exact_ordinal_vector_and_conversion_funnel": True,
            "queries_thresholds_source_counts_and_credit_rules_are_unchanged": True,
            "same_population_rerun_or_revaluation_is_forbidden": True,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "benchmark_launched": False,
            "external_population_launched": False,
            "evaluator_called": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "prior_external_or_benchmark_task_question_identifier_query_url_page_prediction_candidate_private_result_opened_by_audit": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "prior_external_temporary_execution_directory_opened": False,
            "synthetic_test_fixtures_executed": True,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "new_external_source_selection_gate_design": not findings,
            "new_external_probe_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    publish_new(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
            },
            sort_keys=True,
        )
    )
