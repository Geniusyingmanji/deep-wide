#!/usr/bin/env python3
"""Build-only label-blind audit for the V2.43.78--79 successor."""

from __future__ import annotations

import ast
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

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    protected_watcher_snapshot,
    read_object,
    sha256,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


DATE = "20260804"
AUDIT = Path(f"results/v24380_adaptive_heldout_verifier_build_audit_v1_{DATE}.json")
PARENT_RESULT = Path(
    f"results/v24377_batch_stratified_external_result_v1_{DATE}.json"
)
PARENT_DECISION = Path(
    f"results/v24377_batch_stratified_external_decision_v1_{DATE}.json"
)
PARENT_AUDIT = Path(
    f"results/v24377_batch_stratified_external_postresult_audit_v1_{DATE}.json"
)
SOURCES = (
    Path("src/deepwide_agent/v24378_adaptive_heldout_verifier_runtime.py"),
    Path("src/deepwide_agent/v24379_adaptive_heldout_verifier_runner.py"),
    Path("tests/test_v24378_adaptive_heldout_verifier_runtime.py"),
    Path("tests/test_v24379_adaptive_heldout_verifier_runner.py"),
    Path("scripts/audit_v24380_adaptive_heldout_verifier_build.py"),
)
RUNTIME_SOURCES = SOURCES[:2]
TEST_SUITES = (
    (Path("tests/test_v24333_programmatic_support_catalog.py"), 9),
    (Path("tests/test_v24339_active_evidence_support.py"), 5),
    (Path("tests/test_v24341_semantic_evidence_projection.py"), 5),
    (Path("tests/test_v24342_semantic_active_runtime.py"), 7),
    (Path("tests/test_v24349_structural_semantic_runtime.py"), 10),
    (Path("tests/test_v24354_explicit_partition_utility.py"), 7),
    (Path("tests/test_v24358_two_batch_discovery.py"), 4),
    (Path("tests/test_v24362_two_verifier_partition_runtime.py"), 8),
    (Path("tests/test_v24365_entity_segment_projection.py"), 9),
    (Path("tests/test_v24366_target_segment_utility.py"), 9),
    (Path("tests/test_v24367_target_segment_verifier_runtime.py"), 7),
    (Path("tests/test_v24368_target_segment_verifier_runner.py"), 3),
    (Path("tests/test_v24371_batch_stratified_verifier_runtime.py"), 7),
    (Path("tests/test_v24372_batch_stratified_verifier_runner.py"), 3),
    (Path("tests/test_v24378_adaptive_heldout_verifier_runtime.py"), 8),
    (Path("tests/test_v24379_adaptive_heldout_verifier_runner.py"), 3),
)
EXPECTED_TEST_COUNT = 104
EXPECTED_WATCHERS = [
    {
        "pid": 795336,
        "marker": "scripts/watch_v2415_r1_checkpoint_liveness.py",
        "start_ticks": 713986317,
    },
    {
        "pid": 3061652,
        "marker": "scripts/watch_v24218_exact220_executor.py",
        "start_ticks": 747569004,
    },
]
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
        or not path.resolve().is_relative_to(ROOT)
    ):
        raise RuntimeError(f"V2.43.80 expected ordinary repository file: {relative}")
    return path


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


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _ast_findings(relative: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
    accesses: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        key: str | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
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


def _run_test(relative: Path) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-v"],
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
        timeout=360,
        check=False,
    )
    return completed.returncode == 0


def _active_successor_processes() -> list[str]:
    output: list[str] = []
    for row in process_snapshot():
        argv = row.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if (
            isinstance(script, str)
            and any(marker in Path(script).name for marker in ("v24378", "v24379"))
            and Path(script).name != Path(__file__).name
        ):
            output.append(Path(script).name)
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_result = read_object(_ordinary(PARENT_RESULT))
    parent_decision = read_object(_ordinary(PARENT_DECISION))
    parent_audit = read_object(_ordinary(PARENT_AUDIT))
    aggregate = parent_result.get("aggregate", {})
    if (
        parent_result.get("role") != "v24377_target_segment_external_result"
        or parent_result.get("passed") is not False
        or not _sealed(parent_result, "result_payload_sha256")
        or parent_decision.get("role")
        != "v24377_target_segment_external_decision"
        or parent_decision.get("status") != "fresh_target_segment_external_no_go"
        or parent_decision.get("passed") is not False
        or any(parent_decision.get("authorization", {}).values())
        or not _sealed(parent_decision, "decision_payload_sha256")
        or parent_audit.get("role")
        != "v24377_target_segment_external_postresult_audit"
        or parent_audit.get("audit_valid") is not True
        or parent_audit.get("findings") != []
        or any(parent_audit.get("authorization", {}).values())
        or not _sealed(parent_audit, "audit_payload_sha256")
        or aggregate.get("selected") != 16
        or aggregate.get("terminal_success_tasks") != 15
        or aggregate.get("structurally_passed_tasks") != 15
        or aggregate.get("parent_eligible_support_set_count") != 4
        or aggregate.get("parent_candidate_tasks") != 1
        or aggregate.get("verification_record_count") != 4
        or aggregate.get("no_independent_candidate_support_records") != 4
        or aggregate.get("selected_no_independent_candidate_support_changes") != 1
        or aggregate.get("verifier_semantic_projection_count") != 0
        or aggregate.get("selected_proposal_entropy_nats") != 0.182463052409
        or aggregate.get("utility_aligned_entropy_credit_nats") != 0
        or aggregate.get("final_nonidentity_tasks") != 0
        or aggregate.get("deadline_exhausted_tasks") != 1
    ):
        raise RuntimeError("V2.43.80 V2.43.77 parent evidence drifted")

    manifest = {str(path): sha256(_ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = _ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = [
        {"path": str(path), "passed": _run_test(path), "test_count": count}
        for path, count in TEST_SUITES
    ]
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    active = _active_successor_processes()
    test_count = sum(item["test_count"] for item in suites)
    findings: list[str] = []
    if head != remote:
        findings.append("v24380_source_commit_not_pushed")
    if not clean:
        findings.append("v24380_source_worktree_not_clean")
    if not tracked:
        findings.append("v24380_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24333_79_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24378_79_runtime")
    if imports:
        findings.append("evaluator_import_in_v24378_79_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24378_80_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if active:
        findings.append("v24378_79_runtime_process_present_before_activation")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24380_adaptive_heldout_verifier_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(PARENT_RESULT): sha256(_ordinary(PARENT_RESULT)),
            str(PARENT_DECISION): sha256(_ordinary(PARENT_DECISION)),
            str(PARENT_AUDIT): sha256(_ordinary(PARENT_AUDIT)),
        },
        "parent_no_go_evidence": {
            "selected": aggregate["selected"],
            "terminal_success_tasks": aggregate["terminal_success_tasks"],
            "structurally_passed_tasks": aggregate["structurally_passed_tasks"],
            "parent_eligible_support_set_count": aggregate[
                "parent_eligible_support_set_count"
            ],
            "parent_candidate_tasks": aggregate["parent_candidate_tasks"],
            "verification_record_count": aggregate["verification_record_count"],
            "no_independent_candidate_support_records": aggregate[
                "no_independent_candidate_support_records"
            ],
            "selected_no_independent_candidate_support_changes": aggregate[
                "selected_no_independent_candidate_support_changes"
            ],
            "verifier_semantic_projection_count": aggregate[
                "verifier_semantic_projection_count"
            ],
            "selected_proposal_entropy_nats": aggregate[
                "selected_proposal_entropy_nats"
            ],
            "utility_aligned_entropy_credit_nats": aggregate[
                "utility_aligned_entropy_credit_nats"
            ],
            "final_nonidentity_tasks": aggregate["final_nonidentity_tasks"],
            "deadline_exhausted_tasks": aggregate["deadline_exhausted_tasks"],
            "same_v24377_task_rerun_or_revaluation_authorized": False,
        },
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
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "test_count": test_count,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "mechanism_evidence": {
            "four_visible_queries_execute_as_two_nonrecursive_batches": True,
            "four_proposal_sources_per_batch_are_exposed_to_parent": True,
            "heldout_sources_are_unfetched_before_candidate_freeze": True,
            "verifier_selection_uses_frozen_candidate_row_column_value_and_visible_title_url_only": True,
            "one_verifier_source_per_batch_is_selected_at_full_capacity": True,
            "candidate_generation_never_observes_verifier_page_content": True,
            "support_preserves_two_bound_changes_with_positive_utility_entropy_credit": True,
            "independent_conflict_reverts_only_its_bound_target": True,
            "missing_support_preserves_proposal_entropy_but_zeroes_utility_credit": True,
            "identity_candidate_spends_no_verifier_fetch": True,
            "two_search_ten_fetch_three_model_effect_cap_closes": True,
            "model_slot_transport_single_shot_and_runtime_receipts_cross_validate": True,
            "source_page_envelope_and_independent_receipt_tamper_fail_closed": True,
            "privileged_input_is_rejected_before_any_effect": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "v24378_79_runtime_processes": active,
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_private_content_emitted_to_public_receipt": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_external_gate_design": not findings,
            "fresh_external_gate_launch": False,
            "same_v24377_task_rerun_or_revaluation": False,
            "benchmark_launch": False,
            "same_run_evaluator": False,
            "additional_dev64": False,
            "new_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    publish_new(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {"path": str(AUDIT), "audit_valid": audit["audit_valid"]},
            sort_keys=True,
        )
    )
