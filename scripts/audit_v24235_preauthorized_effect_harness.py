#!/usr/bin/env python3
"""Create-exclusive candidate audit for the V2.42.35 effect harness."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24231_webswarm_guidance_baseline import (  # noqa: E402
    build_guidance_arm,
    build_guidance_policy,
    build_scout_process_trace,
    build_sibling_process_experience,
    build_web_probe_receipt,
)
from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    build_cost_vector,
    build_shared_total_budget_contract,
    initialize_arm_budget_ledger,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
    validate_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (  # noqa: E402
    USAGE_NOT_APPLICABLE,
    USAGE_OBSERVED,
    build_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLBACK_CONCURRENCY_BETWEEN_PERMITS_IMPLEMENTED,
    CALLBACK_SINGLE_PROVIDER_ATTEMPT_SEMANTICS_INDEPENDENTLY_VERIFIED,
    CALLBACK_TIMEOUT_IMPLEMENTED,
    CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED,
    CRASH_DURABLE_JOURNAL_IMPLEMENTED,
    CROSS_PROCESS_COMPARE_AND_SWAP_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_EFFECT_AFTER_PERMIT_INDEPENDENTLY_VERIFIED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    RETRY_BACKOFF_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SINGLE_PROCESS_SERIAL_ADMISSION_AND_SETTLEMENT_IMPLEMENTED,
    PreauthorizedEffectExecutionError,
    PreauthorizedEffectHarness,
    ProviderAttemptResult,
    build_provider_attempt_observation,
    validate_effect_execution_receipt,
    validate_effect_failure_receipt,
)


ROLE = "v24235_preauthorized_effect_harness_candidate_audit"
OUTPUT = Path(
    "results/v24235_preauthorized_effect_harness_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24234_provider_cost_meter_build_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "bc8d819c7ac506211ccac66b838fabeadd7e483c753afe85a88546ecbcf4144e"
)
PARENT_PAYLOAD_SHA256 = (
    "7dca1ae5897b61963763973db72337ddb9a4311e8f687e15553ffb33a9cb23b7"
)
PARENT_MANIFEST_SHA256 = (
    "f800894c52616037cdaea613385d4a4fc35a73c092c7c3a57db81c266505be97"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24234_provider_cost_meter.py"),
    Path("tests/test_v24234_provider_cost_meter.py"),
    Path("scripts/audit_v24234_provider_cost_meter.py"),
    Path("tests/test_audit_v24234_provider_cost_meter.py"),
)
MODULE = Path("src/deepwide_agent/v24235_preauthorized_effect_harness.py")
MODULE_TEST = Path("tests/test_v24235_preauthorized_effect_harness.py")
AUDIT = Path("scripts/audit_v24235_preauthorized_effect_harness.py")
AUDIT_TEST = Path("tests/test_audit_v24235_preauthorized_effect_harness.py")
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
        "copy",
        "dataclasses",
        "math",
        "secrets",
        "threading",
        "time",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24233_webswarm_effect_preauthorization",
        "deepwide_agent.v24234_provider_cost_meter",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "getattr",
        "globals",
        "input",
        "locals",
        "open",
        "setattr",
        "vars",
    }
)
FORBIDDEN_ATTRIBUTE_ROOTS = frozenset(
    {
        "aiohttp",
        "asyncio",
        "builtins",
        "http",
        "httpx",
        "importlib",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "urllib",
    }
)
FORBIDDEN_ATTRIBUTE_CALLS = frozenset(
    {
        "connect",
        "fork",
        "getenv",
        "glob",
        "open",
        "popen",
        "read_bytes",
        "read_text",
        "request",
        "rglob",
        "spawn",
        "system",
        "urlopen",
        "walk",
        "write_bytes",
        "write_text",
    }
)
FORBIDDEN_METADATA_ACCESS_KEYS = frozenset(
    {
        "answer",
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
        "question",
        "question_type",
        "raw_page",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "task_id",
        "url",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "EffectExecutionResult",
        "PreauthorizedEffectExecutionError",
        "PreauthorizedEffectHarness",
        "ProviderAttemptResult",
        "build_provider_attempt_observation",
        "validate_effect_execution_receipt",
        "validate_effect_failure_receipt",
        "run_effect",
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
        raise RuntimeError("V2.42.35 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.35 expected ordinary repository file: {relative}")
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def _attribute_root(node: ast.Attribute) -> str | None:
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    symbols: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attributes: list[str] = []
    privileged_reads: list[str] = []
    callback_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALL_NAMES:
                    forbidden_calls.append(node.func.id)
                if node.func.id == "callback":
                    callback_calls += 1
            elif isinstance(node.func, ast.Attribute):
                root = _attribute_root(node.func)
                if (
                    root in FORBIDDEN_ATTRIBUTE_ROOTS
                    or node.func.attr in FORBIDDEN_ATTRIBUTE_CALLS
                ):
                    forbidden_attributes.append(
                        f"{root}.{node.func.attr}" if root else node.func.attr
                    )
                if node.func.attr == "get" and node.args:
                    key = _literal_key(node.args[0])
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    missing = sorted(REQUIRED_PUBLIC_SYMBOLS - symbols)
    if (
        disallowed_imports
        or forbidden_calls
        or forbidden_attributes
        or privileged_reads
        or missing
        or callback_calls != 1
    ):
        raise RuntimeError(
            "V2.42.35 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(set(forbidden_attributes))}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing}, callback_calls={callback_calls}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "caller_supplied_callback_call_site_count": callback_calls,
        "caller_supplied_callback_invocation_capability": True,
        "direct_file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
        "privileged_metadata_read_count": 0,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _signal(kind: str, tactic: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": tactic, "value_sha256": _digest(label)}


def _build_parent() -> tuple[dict[str, Any], dict[str, Any]]:
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
            _signal("workflow_hint", "verify_with_independent_source", "workflow")
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
    ledger = initialize_arm_budget_ledger(
        contract=budget,
        guidance_policy=policy,
        arm=arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charge_ref_sha256=_digest("overhead"),
        method_overhead_model_attempts=arm["probe_extractor_cost"]["model_calls"],
        method_overhead_other_tool_calls=0,
        method_overhead_orchestrator_calls=1,
    )
    shared = {
        "contract": budget,
        "guidance_policy": policy,
        "guidance_arm": arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    state = initialize_effect_preauthorization_state(
        initial_budget_ledger=ledger,
        **shared,
    )
    validate_effect_preauthorization_state(state, **shared)
    harness_shared = {
        "guidance_contract": budget,
        "guidance_policy": policy,
        "guidance_arm": arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    return state, {"state_shared": shared, "harness_shared": harness_shared}


def _meter(*, attempts: int) -> dict[str, Any]:
    return build_provider_meter_contract(
        provider_kind="azure_responses_model",
        charge_kind="renderer",
        max_attempts=attempts,
        reserved_cost=build_cost_vector(
            model_calls=1,
            model_attempts=attempts,
            search_calls=0,
            fetch_calls=0,
            other_tool_calls=0,
            orchestrator_calls=0,
            input_tokens=1000,
            output_tokens=200,
            wall_milliseconds=30_000,
        ),
    )


def _observation(
    invocation: dict[str, Any], *, retry: bool = False
) -> dict[str, Any]:
    return build_provider_attempt_observation(
        invocation=invocation,
        outcome="retryable_http" if retry else "success",
        http_status=429 if retry else 200,
        provider_response_ref_sha256=_digest(
            f"response-{invocation['attempt_ref_sha256']}"
        ),
        token_usage_state=USAGE_OBSERVED,
        input_tokens=0 if retry else 100,
        output_tokens=0 if retry else 20,
        provider_tool_usage_state=USAGE_NOT_APPLICABLE,
        provider_tool_calls=None,
        request_body_bytes=128,
        response_body_bytes=256,
    )


def replay_synthetic_harness() -> dict[str, Any]:
    initial, parent = _build_parent()
    harness = PreauthorizedEffectHarness(initial, **parent["harness_shared"])
    meter = _meter(attempts=2)
    callback_calls = 0
    permit_seen_before_callback = True

    def retry_callback(invocation: dict[str, Any]) -> ProviderAttemptResult:
        nonlocal callback_calls, permit_seen_before_callback
        callback_calls += 1
        snapshot = harness.snapshot_state()
        permit_seen_before_callback = permit_seen_before_callback and (
            _digest("permit-retry") in snapshot["pending_permit_refs"]
        )
        return ProviderAttemptResult(
            observation=_observation(invocation, retry=callback_calls == 1),
            value="ephemeral-value-not-persisted",
        )

    result = harness.run_effect(
        meter_contract=meter,
        invocation_ref_sha256=_digest("invocation-retry"),
        permit_ref_sha256=_digest("permit-retry"),
        charge_ref_sha256=_digest("charge-retry"),
        callback=retry_callback,
    )
    validate_effect_execution_receipt(result.receipt)
    if result.receipt["attempt_count"] != 2 or callback_calls != 2:
        raise RuntimeError("V2.42.35 bounded retry replay drifted")
    if "ephemeral-value-not-persisted" in json.dumps(result.receipt):
        raise RuntimeError("V2.42.35 persisted raw callback value")

    parallel_meter = _meter(attempts=1)
    barrier = threading.Barrier(2)

    def parallel_run(suffix: str):
        def callback(invocation: dict[str, Any]) -> ProviderAttemptResult:
            barrier.wait(timeout=5)
            return ProviderAttemptResult(observation=_observation(invocation))

        return harness.run_effect(
            meter_contract=parallel_meter,
            invocation_ref_sha256=_digest(f"invocation-{suffix}"),
            permit_ref_sha256=_digest(f"permit-{suffix}"),
            charge_ref_sha256=_digest(f"charge-{suffix}"),
            callback=callback,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(parallel_run, suffix) for suffix in ("a", "b")]
        parallel = [future.result(timeout=10) for future in futures]
    parallel_receipts = sorted(
        (dict(item.receipt) for item in parallel),
        key=lambda item: item["admission_sequence"],
    )
    overlap_observed = (
        parallel_receipts[1]["admission_sequence"]
        < parallel_receipts[0]["settlement_sequence"]
    )
    if not overlap_observed:
        raise RuntimeError("V2.42.35 concurrent callback replay did not overlap")

    failure_invoked = False

    def failure_callback(_invocation: dict[str, Any]) -> ProviderAttemptResult:
        nonlocal failure_invoked
        failure_invoked = True
        raise RuntimeError("synthetic raw provider exception")

    try:
        harness.run_effect(
            meter_contract=parallel_meter,
            invocation_ref_sha256=_digest("invocation-failure"),
            permit_ref_sha256=_digest("permit-failure"),
            charge_ref_sha256=_digest("charge-failure"),
            callback=failure_callback,
        )
    except PreauthorizedEffectExecutionError as error:
        failure_receipt = dict(error.receipt)
    else:
        raise RuntimeError("V2.42.35 callback failure did not fail closed")
    validate_effect_failure_receipt(failure_receipt)
    final = harness.snapshot_state()
    validate_effect_preauthorization_state(final, **parent["state_shared"])
    failure_pending = _digest("permit-failure") in final["pending_permit_refs"]
    if not failure_pending or not failure_invoked:
        raise RuntimeError("V2.42.35 failure reservation was not preserved")

    return {
        "synthetic_callback_only": True,
        "real_provider_model_search_fetch_or_network_called": False,
        "retry_callback_call_count": callback_calls,
        "permit_seen_before_every_retry_callback": permit_seen_before_callback,
        "retry_execution_receipt_validated": True,
        "raw_callback_value_not_persisted_hashed_or_emitted": True,
        "two_permit_callback_overlap_observed": overlap_observed,
        "admission_and_settlement_serialized_by_single_process_lock": True,
        "callback_exception_failure_receipt_validated": True,
        "failed_effect_reservation_remains_charged_and_pending": failure_pending,
        "automatic_whole_effect_replay_authorized": False,
        "final_issued_permit_count": final["issued_permit_count"],
        "final_settled_permit_count": final["settled_permit_count"],
        "final_pending_permit_count": len(final["pending_permit_refs"]),
        "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.35 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent = ordinary(root, PARENT_RECEIPT)
    if sha256(parent) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.35 V2.42.34 parent receipt bytes drifted")
    parent_value = json.loads(parent.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role") != "v24234_provider_cost_meter_build_audit"
        or parent_value.get("audit_valid") is not True
        or parent_value.get("build_only") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.35 parent receipt semantics drifted")
    parent_control_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_control_manifest = {
        name: sha256(path) for name, path in parent_control_paths.items()
    }
    if parent_control_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.35 V2.42.34 parent control files drifted")
    if payload_sha256(parent_control_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.35 V2.42.34 parent manifest seal drifted")

    sources = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.35 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS
    }
    module_name = "v24235_preauthorized_effect_harness"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.35 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind_runtime": True,
        "build_only": False,
        "candidate_runtime_harness": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24234_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24234_control_files_rehashed": len(parent_control_manifest),
            "v24234_build_only_parent_validated": True,
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
        "synthetic_harness_replay": replay_synthetic_harness(),
        "scientific_scope": {
            "permit_committed_before_process_local_callback_invocation": True,
            "settlement_committed_after_callback_completion": True,
            "different_permit_callbacks_can_overlap": True,
            "same_effect_retry_callbacks_are_sequential_and_bounded": True,
            "callback_failure_keeps_reservation_charged_and_permit_pending": True,
            "automatic_whole_effect_replay_authorized": False,
            "raw_callback_value_persisted_hashed_or_emitted": False,
            "caller_supplied_callback_may_have_external_effects": True,
            "callback_is_exactly_one_provider_attempt_independently_verified": CALLBACK_SINGLE_PROVIDER_ATTEMPT_SEMANTICS_INDEPENDENTLY_VERIFIED,
            "external_effect_after_permit_independently_verified": EXTERNAL_EFFECT_AFTER_PERMIT_INDEPENDENTLY_VERIFIED,
            "provider_challenge_consumption_independently_verified": PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
            "cross_process_compare_and_swap_implemented": CROSS_PROCESS_COMPARE_AND_SWAP_IMPLEMENTED,
            "crash_durable_journal_implemented": CRASH_DURABLE_JOURNAL_IMPLEMENTED,
            "callback_timeout_implemented": CALLBACK_TIMEOUT_IMPLEMENTED,
            "retry_backoff_implemented": RETRY_BACKOFF_IMPLEMENTED,
            "real_provider_adapter_integrated": False,
            "real_model_search_fetch_or_orchestrator_execution_observed": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "candidate_caller_supplied_effect_callback_invocation": CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED,
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "implementation": {
            "single_process_serial_admission_and_settlement": SINGLE_PROCESS_SERIAL_ADMISSION_AND_SETTLEMENT_IMPLEMENTED,
            "callback_concurrency_between_permits": CALLBACK_CONCURRENCY_BETWEEN_PERMITS_IMPLEMENTED,
            "active_provider_client_adapter": False,
            "active_runner_import": False,
        },
        "claims": {
            "candidate_preauthorized_effect_harness_available": True,
            "production_runtime_wrapper_available": False,
            "real_webswarm_budgeted_run_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.35 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.35 audit output path is noncanonical")
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
                "candidate_runtime_harness": value["candidate_runtime_harness"],
            }
        )
    )


if __name__ == "__main__":
    main()
