#!/usr/bin/env python3
"""Create-exclusive no-network audit for V2.42.42 durable effects."""

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
)
from deepwide_agent.v24234_provider_cost_meter import (  # noqa: E402
    build_provider_meter_contract,
)
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    AzureResponsesRequest,
    AzureResponsesSingleAttemptAdapter,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ATTEMPT_MEASUREMENT_DURABLY_PERSISTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLBACK_CONCURRENCY_BETWEEN_EFFECTS_IMPLEMENTED,
    CALLBACK_OR_SETTLEMENT_FAILURE_AUTOMATIC_REPLAY_IMPLEMENTED,
    CALLBACK_TIMEOUT_IMPLEMENTED,
    CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED,
    CROSS_PROCESS_CAS_IMPLEMENTED,
    DETERMINISTIC_INVOCATION_IDEMPOTENCY_BINDING_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DURABLE_PERMIT_BEFORE_CALLBACK_IMPLEMENTED,
    DURABLE_SETTLEMENT_AFTER_CALLBACK_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOCAL_POSIX_CRASH_DURABLE_EFFECT_ORDERING_IMPLEMENTED,
    NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
    PREEXISTING_PENDING_PERMIT_AUTOMATIC_REPLAY_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    RETRY_BACKOFF_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    TOTAL_WALL_DEADLINE_IMPLEMENTED,
    DurableEffectReplayRejected,
    DurablePreauthorizedEffectCoordinator,
    validate_durable_effect_execution_receipt,
    validate_durable_effect_recovery_status,
)


ROLE = "v24242_durable_effect_coordinator_candidate_audit"
OUTPUT = Path(
    "results/v24242_durable_effect_coordinator_candidate_audit_v2_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24241_durable_preauthorization_journal_candidate_audit_v3_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "0ddc8ba70d93578ff5d391c46da5a71711009b3ce349622e05f528fc899af021"
)
PARENT_PAYLOAD_SHA256 = (
    "95a3e1deb4efc78324f9f88232240f5fa3adabc8a103c26527828c992e63725b"
)
PARENT_MANIFEST_SHA256 = (
    "c4ee8e3caba5c4ed78c5d9c6ae84fb5059c632f47b1336fae2923d13e381535f"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24241_durable_preauthorization_journal.py"),
    Path("tests/test_v24241_durable_preauthorization_journal.py"),
    Path("scripts/audit_v24241_durable_preauthorization_journal.py"),
    Path("tests/test_audit_v24241_durable_preauthorization_journal.py"),
)
MODULE = Path("src/deepwide_agent/v24242_durable_effect_coordinator.py")
MODULE_TEST = Path("tests/test_v24242_durable_effect_coordinator.py")
AUDIT = Path("scripts/audit_v24242_durable_effect_coordinator.py")
AUDIT_TEST = Path("tests/test_audit_v24242_durable_effect_coordinator.py")
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
        "pathlib",
        "threading",
        "time",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24233_webswarm_effect_preauthorization",
        "deepwide_agent.v24234_provider_cost_meter",
        "deepwide_agent.v24235_preauthorized_effect_harness",
        "deepwide_agent.v24241_durable_preauthorization_journal",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "DurableEffectExecutionResult",
        "DurableEffectExecutionError",
        "DurableEffectReplayRejected",
        "DurableEffectCASExhausted",
        "DurablePreauthorizedEffectCoordinator",
        "derive_effect_references",
        "validate_durable_effect_execution_receipt",
        "validate_durable_effect_failure_receipt",
        "validate_durable_effect_recovery_status",
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
        raise RuntimeError("V2.42.42 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.42 expected ordinary repository file: {relative}")
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    symbols: set[str] = set()
    forbidden_calls: list[str] = []
    privileged_reads: list[str] = []
    expansive_calls: list[str] = []
    callback_call_sites = 0
    journal_load_call_sites = 0
    journal_append_call_sites = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALL_NAMES:
                    forbidden_calls.append(node.func.id)
                if node.func.id == "callback":
                    callback_call_sites += 1
            elif isinstance(node.func, ast.Attribute):
                attribute = node.func.attr
                if attribute == "get":
                    key = _literal_key(node.args[0]) if node.args else None
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
                elif attribute in FORBIDDEN_ATTRIBUTES:
                    expansive_calls.append(attribute)
                if attribute == "load":
                    journal_load_call_sites += 1
                elif attribute == "compare_and_append":
                    journal_append_call_sites += 1
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
        elif isinstance(node, ast.Attribute) and node.attr == "environ":
            expansive_calls.append("environ")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.casefold() in FORBIDDEN_METADATA_ACCESS_KEYS
        ):
            privileged_reads.append(node.value.casefold())
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    missing = sorted(REQUIRED_PUBLIC_SYMBOLS - symbols)
    if (
        disallowed_imports
        or forbidden_calls
        or privileged_reads
        or expansive_calls
        or missing
        or callback_call_sites != 1
        or journal_load_call_sites < 1
        or journal_append_call_sites != 2
    ):
        raise RuntimeError(
            "V2.42.42 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"privileged={privileged_reads}, expansive={expansive_calls}, "
            f"missing={missing}, callback={callback_call_sites}, "
            f"load={journal_load_call_sites}, append={journal_append_call_sites}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "caller_supplied_callback_call_site_count": callback_call_sites,
        "journal_load_call_site_count": journal_load_call_sites,
        "journal_compare_and_append_call_site_count": journal_append_call_sites,
        "direct_network_environment_process_subprocess_or_dynamic_code_capability": False,
        "privileged_metadata_read_count": 0,
    }


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
        "guidance_contract": budget,
        "guidance_policy": policy,
        "guidance_arm": arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    initial = initialize_effect_preauthorization_state(
        initial_budget_ledger=initial_ledger,
        contract=budget,
        guidance_policy=policy,
        guidance_arm=arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    return initial, shared


def _meter() -> dict[str, Any]:
    return build_provider_meter_contract(
        provider_kind="azure_responses_model",
        charge_kind="renderer",
        max_attempts=1,
        reserved_cost=build_cost_vector(
            model_calls=1,
            model_attempts=1,
            search_calls=0,
            fetch_calls=0,
            other_tool_calls=0,
            orchestrator_calls=0,
            input_tokens=500,
            output_tokens=100,
            wall_milliseconds=300_000,
        ),
    )


class _Response:
    def __init__(self, content: bytes) -> None:
        self.status_code = 200
        self.content = content
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Post:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def __call__(self, endpoint: str, **kwargs: Any) -> _Response:
        self.calls.append({"endpoint": endpoint, **kwargs})
        return self.response


class _Crash(RuntimeError):
    pass


def _coordinator(
    root: Path,
    namespace: str,
    initial: dict[str, Any],
    shared: dict[str, Any],
) -> DurablePreauthorizedEffectCoordinator:
    return DurablePreauthorizedEffectCoordinator.initialize(
        root=root,
        journal_namespace_sha256=namespace,
        initial_state=initial,
        **shared,
    )


def replay_fake_durable_effects() -> dict[str, Any]:
    initial, shared = _parent()
    meter = _meter()
    response = _Response(
        json.dumps(
            {
                "id": "synthetic-response",
                "output_text": "synthetic private answer",
                "usage": {"input_tokens": 40, "output_tokens": 8},
            }
        ).encode("utf-8")
    )
    post = _Post(response)
    adapter = AzureResponsesSingleAttemptAdapter(
        endpoint="http://127.0.0.1:9878/responses",
        model="gpt-5.6-sol",
        timeout_seconds=300,
        post=post,
    )
    bound = adapter.bind(
        AzureResponsesRequest(
            system="synthetic private system",
            user="synthetic private user",
            max_output_tokens=100,
            json_mode=False,
            reasoning_effort="high",
            service_tier="priority",
        ),
        meter_contract=meter,
    )
    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        root = Path(directory).resolve()
        success = _coordinator(
            root,
            _digest("audit-success-journal"),
            initial,
            shared,
        )
        callback_states: list[dict[str, Any]] = []

        def success_callback(invocation):
            callback_states.append(success.journal.load())
            return bound(invocation)

        success_posts_before = len(post.calls)
        result = success.run_effect(
            meter_contract=meter,
            invocation_ref_sha256=_digest("audit-success-invocation"),
            callback=success_callback,
        )
        validate_durable_effect_execution_receipt(result.receipt)
        final = success.journal.load()
        success_post_count = len(post.calls) - success_posts_before
        if (
            success_post_count != 1
            or callback_states[0]["settled_permit_count"] != 0
            or len(callback_states[0]["pending_permit_refs"]) != 1
            or final["settled_permit_count"] != 1
            or final["pending_permit_refs"]
        ):
            raise RuntimeError("V2.42.42 success replay drifted")

        cut_results: dict[str, bool] = {}
        callback_counts: dict[str, int] = {}
        for label, stage in (
            ("before_callback", "after_durable_permit_before_callback"),
            ("after_callback", "after_callback_before_observation_commit"),
            ("after_settlement", "after_durable_settlement_before_return"),
        ):
            current = _coordinator(
                root,
                _digest(f"audit-{label}-journal"),
                initial,
                shared,
            )
            count = 0

            def callback(invocation):
                nonlocal count
                count += 1
                return bound(invocation)

            def crash(current_stage: str) -> None:
                if current_stage == stage:
                    raise _Crash(stage)

            invocation_ref = _digest(f"audit-{label}-invocation")
            try:
                current.run_effect(
                    meter_contract=meter,
                    invocation_ref_sha256=invocation_ref,
                    callback=callback,
                    fault_hook=crash,
                )
            except _Crash:
                pass
            else:
                raise RuntimeError("V2.42.42 synthetic crash cut did not fire")
            reopened = DurablePreauthorizedEffectCoordinator(
                root=root,
                journal_namespace_sha256=current.journal.namespace,
                **shared,
            )
            status = reopened.recovery_status()
            validate_durable_effect_recovery_status(status)
            try:
                reopened.run_effect(
                    meter_contract=meter,
                    invocation_ref_sha256=invocation_ref,
                    callback=callback,
                )
            except DurableEffectReplayRejected:
                cut_results[label] = True
            else:
                raise RuntimeError("V2.42.42 crash replay was not rejected")
            callback_counts[label] = count

        encoded = json.dumps(result.receipt, ensure_ascii=False)
        if "synthetic private" in encoded:
            raise RuntimeError("V2.42.42 private callback content entered receipt")
        return {
            "fake_transport_and_local_tempdir_only": True,
            "network_socket_or_real_provider_called": False,
            "successful_gpt56_adapter_transport_post_count": success_post_count,
            "all_synthetic_replays_transport_post_count": len(post.calls),
            "durable_permit_visible_before_callback": True,
            "durable_settlement_visible_after_callback": True,
            "success_generation_count": final["event_count"],
            "success_pending_permit_count": len(final["pending_permit_refs"]),
            "before_callback_crash_replay_rejected": cut_results["before_callback"],
            "after_callback_crash_replay_rejected": cut_results["after_callback"],
            "after_settlement_crash_replay_rejected": cut_results[
                "after_settlement"
            ],
            "before_callback_crash_callback_count": callback_counts[
                "before_callback"
            ],
            "after_callback_crash_callback_count": callback_counts[
                "after_callback"
            ],
            "after_settlement_crash_callback_count": callback_counts[
                "after_settlement"
            ],
            "raw_prompt_answer_url_or_credential_in_receipt": False,
            "provider_response_close_attempted_by_v24236": response.closed,
            "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
        }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.42 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.42 parent receipt bytes drifted")
    parent_value = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24241_durable_preauthorization_journal_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.42 parent receipt semantics drifted")
    parent_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.42 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.42 parent manifest seal drifted")

    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.42 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24242_durable_effect_coordinator"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.42 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind_runtime": True,
        "build_only": False,
        "candidate_runtime_coordinator": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24241_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24241_control_files_rehashed": len(parent_manifest),
            "v24241_candidate_parent_validated": True,
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
        "fake_durable_effect_replay": replay_fake_durable_effects(),
        "scientific_scope": {
            "durable_permit_before_callback_implemented": DURABLE_PERMIT_BEFORE_CALLBACK_IMPLEMENTED,
            "durable_settlement_after_callback_implemented": DURABLE_SETTLEMENT_AFTER_CALLBACK_IMPLEMENTED,
            "deterministic_invocation_idempotency_binding_implemented": DETERMINISTIC_INVOCATION_IDEMPOTENCY_BINDING_IMPLEMENTED,
            "local_posix_crash_durable_effect_ordering_implemented": LOCAL_POSIX_CRASH_DURABLE_EFFECT_ORDERING_IMPLEMENTED,
            "cross_process_cas_implemented": CROSS_PROCESS_CAS_IMPLEMENTED,
            "callback_concurrency_between_effects_implemented": CALLBACK_CONCURRENCY_BETWEEN_EFFECTS_IMPLEMENTED,
            "preexisting_pending_permit_automatic_replay_implemented": PREEXISTING_PENDING_PERMIT_AUTOMATIC_REPLAY_IMPLEMENTED,
            "callback_or_settlement_failure_automatic_replay_implemented": CALLBACK_OR_SETTLEMENT_FAILURE_AUTOMATIC_REPLAY_IMPLEMENTED,
            "attempt_measurement_durably_persisted": ATTEMPT_MEASUREMENT_DURABLY_PERSISTED,
            "callback_timeout_implemented": CALLBACK_TIMEOUT_IMPLEMENTED,
            "retry_backoff_implemented": RETRY_BACKOFF_IMPLEMENTED,
            "total_wall_deadline_implemented": TOTAL_WALL_DEADLINE_IMPLEMENTED,
            "provider_challenge_consumption_independently_verified": PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
            "provider_response_authenticity_independently_verified": PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
            "network_or_distributed_filesystem_semantics_proven": NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
            "real_power_loss_or_kernel_crash_observed": False,
            "real_provider_traffic_observed": False,
            "active_client_or_runner_integrated": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_fake_transport_and_local_tempdir_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "caller_supplied_effect_callback_invocation_capability": CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED,
            "active_provider_traffic_authorized": ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
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
            "candidate_local_posix_durable_effect_coordinator_available": True,
            "production_runtime_wrapper_available": False,
            "automatic_uncertain_effect_recovery_available": False,
            "trusted_total_deadline_or_backoff_available": False,
            "real_provider_execution_evidence_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.42 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.42 audit output path is noncanonical")
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
                "candidate_runtime_coordinator": value[
                    "candidate_runtime_coordinator"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
