#!/usr/bin/env python3
"""Create-exclusive no-network audit for V2.42.41 durable journal."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    build_cost_vector,
    build_shared_total_budget_contract,
    initialize_arm_budget_ledger,
)
from deepwide_agent.v24231_webswarm_guidance_baseline import (  # noqa: E402
    build_guidance_arm,
    build_guidance_policy,
    build_scout_process_trace,
    build_sibling_process_experience,
    build_web_probe_receipt,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
    issue_effect_permit,
    settle_effect_permit,
)
from deepwide_agent.v24241_durable_preauthorization_journal import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_HARNESS_DURABILITY_INTEGRATED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CONTENT_BOUND_PENDING_RECOVERY_IMPLEMENTED,
    CRASH_RECOVERY_AFTER_INITIALIZATION_IMPLEMENTED,
    CROSS_PROCESS_CAS_FOR_COOPERATING_WRITERS_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED,
    HARDWARE_STABLE_STORAGE_INDEPENDENTLY_ATTESTED,
    IMMUTABLE_NO_CLOBBER_GENERATION_FILES_IMPLEMENTED,
    INCREMENTAL_EVENT_STORAGE_IMPLEMENTED,
    INDEPENDENT_APPEND_ONLY_TRANSPARENCY_LOG_USED,
    INITIALIZATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED,
    MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
    NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    DurableJournalCASConflict,
    DurablePreauthorizationJournal,
)
ROLE = "v24241_durable_preauthorization_journal_candidate_audit"
OUTPUT = Path(
    "results/v24241_durable_preauthorization_journal_candidate_audit_v3_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24240_anthropic_server_search_single_attempt_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "5d4b5b0861e0de2e3aa334c572c6e5a64677bb55870c30640a0c237de7d6a2ff"
)
PARENT_PAYLOAD_SHA256 = (
    "f9c5de115527ae52ebb880b4ce1084e576e5d760d09cf3001b6778ad2368cddb"
)
PARENT_MANIFEST_SHA256 = (
    "6f0ef60927beebe54a473db955c69585add0d1f8016bc88e980a0646e7d746b1"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24240_anthropic_server_search_single_attempt.py"),
    Path("tests/test_v24240_anthropic_server_search_single_attempt.py"),
    Path("scripts/audit_v24240_anthropic_server_search_single_attempt.py"),
    Path("tests/test_audit_v24240_anthropic_server_search_single_attempt.py"),
)
MODULE = Path("src/deepwide_agent/v24241_durable_preauthorization_journal.py")
MODULE_TEST = Path("tests/test_v24241_durable_preauthorization_journal.py")
AUDIT = Path("scripts/audit_v24241_durable_preauthorization_journal.py")
AUDIT_TEST = Path("tests/test_audit_v24241_durable_preauthorization_journal.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARDS = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/clients.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/anthropic_search.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)

ALLOWED_IMPORT_MODULES = frozenset(
    {
        "__future__",
        "contextlib",
        "fcntl",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "re",
        "stat",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24233_webswarm_effect_preauthorization",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "breakpoint",
        "__import__",
        "getattr",
        "vars",
    }
)
FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "getenv",
        "environ",
        "popen",
        "run",
        "system",
        "execv",
        "execve",
        "execl",
        "execlp",
        "execvp",
        "fork",
        "forkpty",
        "kill",
        "killpg",
        "posix_spawn",
        "posix_spawnp",
        "connect",
        "request",
        "urlopen",
        "get",
        "post",
        "put",
        "delete",
    }
)
FORBIDDEN_METADATA_ACCESS_KEYS = frozenset(
    {
        "answer_key",
        "benchmark_category",
        "benchmark_label",
        "benchmark_subset",
        "category",
        "correctness",
        "evaluator_payload",
        "evaluator_score",
        "gold",
        "ground_truth",
        "mapping",
        "prediction",
        "question_type",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "task_id",
    }
)
SECRET_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.41 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.41 expected ordinary repository file: {relative}")
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    forbidden_calls: list[str] = []
    privileged_reads: list[str] = []
    environment_network_or_process_calls: list[str] = []
    file_write_calls = 0
    file_read_calls = 0
    fsync_calls = 0
    flock_calls = 0
    hard_link_calls = 0
    exclusive_open_calls = 0
    nofollow_open_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
            if isinstance(node.func, ast.Attribute):
                attribute = node.func.attr
                if attribute == "get":
                    # Mapping.get is allowed except for privileged literal keys.
                    key = _literal_key(node.args[0]) if node.args else None
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
                elif attribute in {"post", "put", "delete"}:
                    environment_network_or_process_calls.append(attribute)
                elif attribute in FORBIDDEN_ATTRIBUTES:
                    environment_network_or_process_calls.append(attribute)
                if attribute in {"write", "write_bytes", "write_text", "unlink", "mkdir"}:
                    file_write_calls += 1
                if attribute in {"read", "read_bytes", "read_text", "iterdir", "lstat"}:
                    file_read_calls += 1
                if attribute == "fsync":
                    fsync_calls += 1
                if attribute == "flock":
                    flock_calls += 1
                if attribute == "link":
                    hard_link_calls += 1
                if attribute == "open" and len(node.args) >= 2:
                    flags = ast.unparse(node.args[1])
                    if "O_EXCL" in flags:
                        exclusive_open_calls += 1
                    if "O_NOFOLLOW" in flags:
                        nofollow_open_calls += 1
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
        elif isinstance(node, ast.Attribute) and node.attr == "environ":
            environment_network_or_process_calls.append("environ")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.casefold() in FORBIDDEN_METADATA_ACCESS_KEYS
        ):
            privileged_reads.append(node.value.casefold())
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    if (
        disallowed_imports
        or forbidden_calls
        or privileged_reads
        or environment_network_or_process_calls
        or file_write_calls == 0
        or file_read_calls == 0
        or fsync_calls == 0
        or flock_calls == 0
        or hard_link_calls == 0
        or exclusive_open_calls == 0
        or nofollow_open_calls == 0
    ):
        raise RuntimeError(
            "V2.42.41 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"privileged={privileged_reads}, expansive="
            f"{environment_network_or_process_calls}, file_write={file_write_calls}, "
            f"file_read={file_read_calls}, fsync={fsync_calls}, flock={flock_calls}, "
            f"link={hard_link_calls}, exclusive={exclusive_open_calls}, "
            f"nofollow={nofollow_open_calls}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "disallowed_import_count": 0,
        "privileged_metadata_read_count": 0,
        "environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
        "repository_local_file_read_call_count": file_read_calls,
        "repository_local_file_write_call_count": file_write_calls,
        "fsync_call_count": fsync_calls,
        "flock_call_count": flock_calls,
        "hard_link_call_count": hard_link_calls,
        "create_exclusive_open_call_count": exclusive_open_calls,
        "nofollow_open_call_count": nofollow_open_calls,
    }


def _cost(**overrides: int) -> dict[str, int]:
    values = {
        "model_calls": 1,
        "model_attempts": 2,
        "search_calls": 3,
        "fetch_calls": 4,
        "other_tool_calls": 1,
        "orchestrator_calls": 1,
        "input_tokens": 500,
        "output_tokens": 100,
        "wall_milliseconds": 10_000,
    }
    values.update(overrides)
    return build_cost_vector(**values)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _signal(kind: str, tactic: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": tactic, "value_sha256": _digest(label)}


def _parent() -> tuple[dict[str, Any], dict[str, Any]]:
    budget = build_shared_total_budget_contract(
        model_calls=100,
        model_attempts=120,
        search_calls=100,
        fetch_calls=200,
        other_tool_calls=100,
        orchestrator_calls=100,
        input_tokens=100_000,
        output_tokens=20_000,
        wall_milliseconds=1_000_000,
    )
    policy = build_guidance_policy(
        selection_protocol_sha256=_digest("selection"),
        model_contract_sha256=_digest("model"),
        search_fetch_contract_sha256=_digest("search-fetch"),
        total_budget_contract_sha256=budget["contract_sha256"],
        root_scope_projection_protocol_sha256=_digest("root-projection"),
        process_signal_vocabulary_sha256=_digest("process-vocabulary"),
    )
    probe = build_web_probe_receipt(
        policy=policy,
        root_scope_projection_sha256=_digest("root"),
        parent_node_ref_sha256=_digest("parent"),
        probe_run_ref_sha256=_digest("probe"),
        topology="distributed",
        probe_search_calls=3,
        probe_fetch_calls=2,
        probe_model_calls=1,
        probe_input_tokens=100,
        probe_output_tokens=20,
        probe_wall_seconds=4.0004,
    )
    scouts = [
        build_scout_process_trace(
            policy=policy,
            root_scope_projection_sha256=_digest("root"),
            parent_node_ref_sha256=_digest("parent"),
            homogeneous_group_ref_sha256=_digest("group"),
            scout_slot=slot,
            sibling_node_ref_sha256=_digest(f"sibling-{slot}"),
            sibling_mode_sha256=_digest("mode"),
            process_signals=[
                _signal(
                    "effective_query_pattern",
                    "combine_visible_entity_and_attribute_terms",
                    f"query-{slot}",
                )
            ],
            model_calls=1,
            search_calls=1,
            fetch_calls=1,
            input_tokens=10,
            output_tokens=5,
            wall_seconds=1.0,
            scout_terminal_status="completed",
        )
        for slot in (1, 2)
    ]
    experience = build_sibling_process_experience(
        policy=policy,
        scouts=scouts,
        experience_extractor_ref_sha256=_digest("extractor"),
        process_signals=[
            _signal(
                "workflow_hint",
                "verify_with_independent_source",
                "workflow",
            )
        ],
        extractor_model_calls=1,
        extractor_input_tokens=300,
        extractor_output_tokens=30,
        extractor_wall_seconds=2.0002,
    )
    arm = build_guidance_arm(
        policy=policy,
        arm_name="full",
        arm_ref_sha256=_digest("arm-full"),
        root_scope_projection_sha256=_digest("root"),
        parent_node_ref_sha256=_digest("parent"),
        homogeneous_group_ref_sha256=_digest("group"),
        sibling_count=8,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    initial_ledger = initialize_arm_budget_ledger(
        contract=budget,
        guidance_policy=policy,
        arm=arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charge_ref_sha256=_digest("overhead-full"),
        method_overhead_model_attempts=arm["probe_extractor_cost"]["model_calls"],
        method_overhead_other_tool_calls=0,
        method_overhead_orchestrator_calls=1,
    )
    shared: dict[str, Any] = {
        "contract": budget,
        "guidance_policy": policy,
        "guidance_arm": arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    return initialize_effect_preauthorization_state(
        initial_budget_ledger=initial_ledger,
        **shared,
    ), shared


class _Crash(RuntimeError):
    pass


def replay_local_journal() -> dict[str, Any]:
    initial, shared = _parent()
    issued = issue_effect_permit(
        initial,
        **shared,
        permit_ref_sha256=_digest("audit-permit"),
        charge_kind="fanout_execution",
        charge_ref_sha256=_digest("audit-charge"),
        estimate_source_sha256=_digest("audit-estimate"),
        reserved_cost=_cost(),
    )
    settled = settle_effect_permit(
        issued,
        **shared,
        permit_ref_sha256=_digest("audit-permit"),
        effect_receipt_sha256=_digest("audit-effect"),
        actual_cost_source_sha256=_digest("audit-actual"),
        actual_cost=_cost(
            model_attempts=1,
            search_calls=2,
            fetch_calls=3,
            other_tool_calls=0,
            input_tokens=400,
            output_tokens=80,
            wall_milliseconds=8_000,
        ),
    )
    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        root = Path(directory).resolve()
        journal = DurablePreauthorizationJournal(
            root=root,
            journal_namespace_sha256=_digest("audit-journal"),
            **shared,
        )
        journal.initialize(initial)
        first = journal.compare_and_append(
            expected_state_sha256=initial["state_sha256"],
            current_state=issued,
        )
        second = journal.compare_and_append(
            expected_state_sha256=issued["state_sha256"],
            current_state=settled,
        )
        loaded = journal.load()
        status = journal.status()
        stale_rejected = False
        try:
            journal.compare_and_append(
                expected_state_sha256=initial["state_sha256"],
                current_state=issued,
            )
        except DurableJournalCASConflict:
            stale_rejected = True

        crash_journal = DurablePreauthorizationJournal(
            root=root,
            journal_namespace_sha256=_digest("audit-crash-journal"),
            **shared,
        )
        crash_journal.initialize(initial)

        def crash(stage: str) -> None:
            if stage == "after_pending_directory_fsync":
                raise _Crash(stage)

        crash_observed = False
        try:
            crash_journal.compare_and_append(
                expected_state_sha256=initial["state_sha256"],
                current_state=issued,
                fault_hook=crash,
            )
        except _Crash:
            crash_observed = True
        recovered_status = crash_journal.status()
        recovered = crash_journal.load()
        entry = json.loads(
            (journal.entries_directory / f"{1:020d}.json").read_text(
                encoding="utf-8"
            )
        )
        entries = sorted(journal.entries_directory.iterdir())
        if (
            loaded != settled
            or recovered != issued
            or not stale_rejected
            or not crash_observed
            or recovered_status["recovered_pending_file_count"] != 1
            or any(path.stat().st_nlink != 1 for path in entries)
        ):
            raise RuntimeError("V2.42.41 local journal replay drifted")
        return {
            "local_posix_filesystem_only": True,
            "network_socket_or_real_provider_called": False,
            "initialized_generation_zero": True,
            "permit_and_settlement_appended": first["generation"] == 1
            and second["generation"] == 2,
            "exact_state_replay_after_two_entries": loaded == settled,
            "stale_compare_and_swap_rejected": stale_rejected,
            "crash_after_pending_fsync_observed": crash_observed,
            "unique_complete_pending_entry_recovered": recovered == issued,
            "recovered_pending_file_count": recovered_status[
                "recovered_pending_file_count"
            ],
            "clean_generation_after_recovery": recovered_status["generation"] == 1,
            "generation_files_have_one_link_after_cleanup": all(
                path.stat().st_nlink == 1 for path in entries
            ),
            "entry_contains_only_incremental_event_not_full_state": (
                entry["transition_event"] == issued["events"][-1]
                and "events" not in entry
                and "initial_state" not in entry
                and "current_budget_ledger" not in entry
            ),
            "status_is_content_free": (
                status["generation"] == 2
                and "events" not in status
                and "initial_state" not in status
            ),
            "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
        }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.41 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.41 parent receipt bytes drifted")
    parent_value = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24240_anthropic_server_search_single_attempt_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.41 parent receipt semantics drifted")
    parent_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.41 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.41 parent manifest seal drifted")

    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.41 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24241_durable_preauthorization_journal"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.41 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind_runtime": True,
        "build_only": True,
        "candidate_local_posix_store": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24240_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24240_control_files_rehashed": len(parent_manifest),
            "v24240_candidate_parent_validated": True,
        },
        "control_surface": {
            "file_count": len(control_manifest),
            "manifest": control_manifest,
            "manifest_sha256": payload_sha256(control_manifest),
        },
        "active_forward_guard": {
            "file_count": len(guard_manifest),
            "manifest": guard_manifest,
            "manifest_sha256": payload_sha256(guard_manifest),
            "module_name_hit_count_by_file": guard_hits,
            "module_absent_from_guarded_clients_and_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(literal_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "local_journal_replay": replay_local_journal(),
        "scientific_scope": {
            "local_posix_advisory_lock_implemented": LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED,
            "cross_process_cas_for_cooperating_writers_implemented": CROSS_PROCESS_CAS_FOR_COOPERATING_WRITERS_IMPLEMENTED,
            "immutable_no_clobber_generation_files_implemented": IMMUTABLE_NO_CLOBBER_GENERATION_FILES_IMPLEMENTED,
            "content_bound_pending_recovery_implemented": CONTENT_BOUND_PENDING_RECOVERY_IMPLEMENTED,
            "file_and_directory_fsync_implemented": FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED,
            "incremental_event_storage_implemented": INCREMENTAL_EVENT_STORAGE_IMPLEMENTED,
            "crash_recovery_after_initialization_implemented": CRASH_RECOVERY_AFTER_INITIALIZATION_IMPLEMENTED,
            "initialization_crash_automatic_recovery_implemented": INITIALIZATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED,
            "network_or_distributed_filesystem_semantics_proven": NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
            "hardware_stable_storage_independently_attested": HARDWARE_STABLE_STORAGE_INDEPENDENTLY_ATTESTED,
            "malicious_same_user_resealing_excluded": MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
            "independent_append_only_transparency_log_used": INDEPENDENT_APPEND_ONLY_TRANSPARENCY_LOG_USED,
            "active_harness_durability_integrated": ACTIVE_HARNESS_DURABILITY_INTEGRATED,
            "real_power_loss_or_kernel_crash_observed": False,
            "real_provider_traffic_observed": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_and_local_tempdir_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "candidate_local_posix_durable_journal_available": True,
            "active_harness_durability_available": False,
            "distributed_or_network_filesystem_safety_proven": False,
            "malicious_writer_resistance_proven": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.41 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.41 audit output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent_descriptor = os.open(
            target.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_audit()
    publish_new(target, value)
    print(
        json.dumps(
            {
                "path": str(target),
                "sha256": sha256(target),
                "audit_valid": value["audit_valid"],
                "candidate_local_posix_store": value[
                    "candidate_local_posix_store"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
