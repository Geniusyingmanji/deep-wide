#!/usr/bin/env python3
"""Create-exclusive no-network audit for V2.42.43 retry scheduling."""

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
    USAGE_NOT_APPLICABLE,
    USAGE_OBSERVED,
    build_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (  # noqa: E402
    ProviderAttemptResult,
    build_provider_attempt_observation,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ALREADY_RUNNING_CALLBACK_FORCE_CANCELLATION_IMPLEMENTED,
    BACKOFF_PREAUTHORIZED_IN_WALL_RESERVATION_IMPLEMENTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DETERMINISTIC_CAPPED_BACKOFF_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    INJECTABLE_MONOTONIC_CLOCK_AND_SLEEPER_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    POST_CALLBACK_DEADLINE_CHECK_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    REQUESTS_PER_CALL_TIMEOUT_TREATED_AS_TOTAL_DEADLINE,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    STRICT_RETRY_ADMISSION_DEADLINE_IMPLEMENTED,
    TRUSTED_HARD_TOTAL_WALL_TIMEOUT_IMPLEMENTED,
    RetryDeadlineEffectScheduler,
    RetryDeadlineExecutionError,
    build_retry_deadline_contract,
    validate_retry_deadline_execution_receipt,
    validate_retry_deadline_failure_receipt,
)


ROLE = "v24243_retry_deadline_scheduler_candidate_audit"
OUTPUT = Path(
    "results/v24243_retry_deadline_scheduler_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24242_durable_effect_coordinator_candidate_audit_v2_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "93606959b007272e1b6151a6efc60a5da50ef893e6fb0f4004c583b6c2b9100e"
)
PARENT_PAYLOAD_SHA256 = (
    "e90c354ff56dd8c6ada20ef1a8f0735f6f8f3e6113f0095427e2e84dc2c055bf"
)
PARENT_MANIFEST_SHA256 = (
    "38cc04bc40e28e3057c76d52f7cb4bfc511636cf5e3a9f8e56ae6fdea8656418"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24242_durable_effect_coordinator.py"),
    Path("tests/test_v24242_durable_effect_coordinator.py"),
    Path("scripts/audit_v24242_durable_effect_coordinator.py"),
    Path("tests/test_audit_v24242_durable_effect_coordinator.py"),
)
MODULE = Path("src/deepwide_agent/v24243_retry_deadline_scheduler.py")
MODULE_TEST = Path("tests/test_v24243_retry_deadline_scheduler.py")
AUDIT = Path("scripts/audit_v24243_retry_deadline_scheduler.py")
AUDIT_TEST = Path("tests/test_audit_v24243_retry_deadline_scheduler.py")
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
        "time",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24234_provider_cost_meter",
        "deepwide_agent.v24235_preauthorized_effect_harness",
        "deepwide_agent.v24242_durable_effect_coordinator",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "RetryDeadlineExecutionResult",
        "RetryDeadlineExecutionError",
        "RetryDeadlineEffectScheduler",
        "build_retry_deadline_contract",
        "validate_retry_deadline_contract",
        "validate_retry_deadline_execution_receipt",
        "validate_retry_deadline_failure_receipt",
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
        raise RuntimeError("V2.42.43 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.43 expected ordinary repository file: {relative}")
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
    provider_callback_call_sites = 0
    parent_run_effect_call_sites = 0
    sleep_call_sites = 0
    monotonic_default_sites = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
            if node.name == "__init__" and isinstance(node, ast.FunctionDef):
                for default in node.args.defaults + node.args.kw_defaults:
                    if (
                        isinstance(default, ast.Attribute)
                        and isinstance(default.value, ast.Name)
                        and default.value.id == "time"
                        and default.attr == "monotonic_ns"
                    ):
                        monotonic_default_sites += 1
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALL_NAMES:
                    forbidden_calls.append(node.func.id)
                if node.func.id == "callback":
                    provider_callback_call_sites += 1
            elif isinstance(node.func, ast.Attribute):
                attribute = node.func.attr
                if attribute == "get":
                    key = _literal_key(node.args[0]) if node.args else None
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
                elif attribute in FORBIDDEN_ATTRIBUTES:
                    expansive_calls.append(attribute)
                if attribute == "run_effect":
                    parent_run_effect_call_sites += 1
                elif attribute == "sleep":
                    sleep_call_sites += 1
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
        or provider_callback_call_sites != 1
        or parent_run_effect_call_sites != 1
        or sleep_call_sites != 0
        or monotonic_default_sites != 1
    ):
        raise RuntimeError(
            "V2.42.43 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"privileged={privileged_reads}, expansive={expansive_calls}, "
            f"missing={missing}, callback={provider_callback_call_sites}, "
            f"parent={parent_run_effect_call_sites}, sleep={sleep_call_sites}, "
            f"clock_default={monotonic_default_sites}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "caller_supplied_callback_call_site_count": provider_callback_call_sites,
        "parent_coordinator_run_effect_call_site_count": parent_run_effect_call_sites,
        "direct_time_sleep_call_site_count": sleep_call_sites,
        "monotonic_clock_default_site_count": monotonic_default_sites,
        "direct_network_environment_file_process_subprocess_or_dynamic_code_capability": False,
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


def _meter(*, max_attempts: int = 3) -> dict[str, Any]:
    return build_provider_meter_contract(
        provider_kind="azure_responses_model",
        charge_kind="renderer",
        max_attempts=max_attempts,
        reserved_cost=build_cost_vector(
            model_calls=1,
            model_attempts=max_attempts,
            search_calls=0,
            fetch_calls=0,
            other_tool_calls=0,
            orchestrator_calls=0,
            input_tokens=500,
            output_tokens=100,
            wall_milliseconds=1000,
        ),
    )


def _observation(
    invocation: dict[str, Any], *, outcome: str, status: int
) -> dict[str, Any]:
    return build_provider_attempt_observation(
        invocation=invocation,
        outcome=outcome,
        http_status=status,
        provider_response_ref_sha256=_digest(
            f"response-{invocation['attempt_ref_sha256']}"
        ),
        token_usage_state=USAGE_OBSERVED,
        input_tokens=20 if outcome == "success" else 0,
        output_tokens=5 if outcome == "success" else 0,
        provider_tool_usage_state=USAGE_NOT_APPLICABLE,
        provider_tool_calls=None,
        request_body_bytes=64,
        response_body_bytes=128,
    )


class _VirtualTime:
    def __init__(self) -> None:
        self.now_ns = 10_000_000_000
        self.sleep_calls: list[float] = []

    def monotonic_ns(self) -> int:
        return self.now_ns

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.now_ns += int(round(seconds * 1_000_000_000))

    def advance_ms(self, milliseconds: int) -> None:
        self.now_ns += milliseconds * 1_000_000


def replay_fake_schedule() -> dict[str, Any]:
    initial, shared = _parent()
    meter = _meter()
    schedule = build_retry_deadline_contract(
        meter_contract=meter,
        total_deadline_milliseconds=500,
        minimum_attempt_window_milliseconds=50,
        initial_backoff_milliseconds=20,
        backoff_multiplier=2,
        maximum_backoff_milliseconds=100,
    )
    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        root = Path(directory).resolve()
        coordinator = DurablePreauthorizedEffectCoordinator.initialize(
            root=root,
            journal_namespace_sha256=_digest("audit-v24243-success-journal"),
            initial_state=initial,
            **shared,
        )
        clock = _VirtualTime()
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=coordinator,
            monotonic_ns=clock.monotonic_ns,
            sleeper=clock.sleep,
        )
        callback_count = 0

        def callback(invocation):
            nonlocal callback_count
            callback_count += 1
            clock.advance_ms(5)
            if invocation["attempt_index"] < 3:
                return ProviderAttemptResult(
                    observation=_observation(
                        dict(invocation),
                        outcome="retryable_http",
                        status=429,
                    )
                )
            return ProviderAttemptResult(
                observation=_observation(
                    dict(invocation), outcome="success", status=200
                ),
                value="synthetic private provider value",
            )

        result = scheduler.run_effect(
            meter_contract=meter,
            scheduler_contract=schedule,
            invocation_ref_sha256=_digest("audit-v24243-success-invocation"),
            callback=callback,
        )
        validate_retry_deadline_execution_receipt(result.receipt)
        encoded = json.dumps(result.receipt, ensure_ascii=False)
        if "synthetic private" in encoded:
            raise RuntimeError("V2.42.43 private callback content entered receipt")

        failure_meter = _meter(max_attempts=1)
        failure_schedule = build_retry_deadline_contract(
            meter_contract=failure_meter,
            total_deadline_milliseconds=100,
            minimum_attempt_window_milliseconds=20,
            initial_backoff_milliseconds=1,
            backoff_multiplier=1,
            maximum_backoff_milliseconds=1,
        )
        failure_coordinator = DurablePreauthorizedEffectCoordinator.initialize(
            root=root,
            journal_namespace_sha256=_digest("audit-v24243-failure-journal"),
            initial_state=initial,
            **shared,
        )
        failure_clock = _VirtualTime()
        failure_scheduler = RetryDeadlineEffectScheduler(
            coordinator=failure_coordinator,
            monotonic_ns=failure_clock.monotonic_ns,
            sleeper=failure_clock.sleep,
        )
        overrun_callback_count = 0

        def overrun_callback(invocation):
            nonlocal overrun_callback_count
            overrun_callback_count += 1
            failure_clock.advance_ms(101)
            return ProviderAttemptResult(
                observation=_observation(
                    dict(invocation), outcome="success", status=200
                )
            )

        try:
            failure_scheduler.run_effect(
                meter_contract=failure_meter,
                scheduler_contract=failure_schedule,
                invocation_ref_sha256=_digest("audit-v24243-failure-invocation"),
                callback=overrun_callback,
            )
        except RetryDeadlineExecutionError as error:
            validate_retry_deadline_failure_receipt(error.receipt)
            failure = error.receipt
        else:
            raise RuntimeError("V2.42.43 callback overrun was not rejected")

        return {
            "fake_callback_local_tempdir_and_virtual_time_only": True,
            "network_socket_or_real_provider_called": False,
            "successful_attempt_count": result.receipt["attempt_count"],
            "successful_provider_callback_count": callback_count,
            "deterministic_sleep_seconds": clock.sleep_calls,
            "required_backoff_total_milliseconds": result.receipt[
                "required_backoff_total_milliseconds"
            ],
            "virtual_total_elapsed_nanoseconds": result.receipt[
                "total_elapsed_nanoseconds"
            ],
            "durable_settlement_committed_after_success": coordinator.journal.load()[
                "settled_permit_count"
            ]
            == 1,
            "callback_overrun_rejected_after_return": failure["failure_reason"]
            == "provider_callback_returned_at_or_after_deadline",
            "overrun_provider_callback_count": overrun_callback_count,
            "overrun_permit_remains_charged": failure[
                "reservation_remains_charged"
            ],
            "overrun_settlement_committed": failure[
                "settlement_durably_committed"
            ],
            "callback_force_cancellation_implemented": failure[
                "callback_force_cancellation_implemented"
            ],
            "raw_callback_value_in_receipt": False,
            "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
        }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.43 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.43 parent receipt bytes drifted")
    parent_value = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24242_durable_effect_coordinator_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.43 parent receipt semantics drifted")
    parent_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.43 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.43 parent manifest seal drifted")

    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.43 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24243_retry_deadline_scheduler"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.43 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time())
        if created_at_unix is None
        else int(created_at_unix),
        "label_blind_runtime": True,
        "candidate_runtime_scheduler": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24242_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24242_control_files_rehashed": len(parent_manifest),
            "v24242_candidate_parent_validated": True,
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
        "fake_schedule_replay": replay_fake_schedule(),
        "scientific_scope": {
            "strict_retry_admission_deadline_implemented": STRICT_RETRY_ADMISSION_DEADLINE_IMPLEMENTED,
            "deterministic_capped_backoff_implemented": DETERMINISTIC_CAPPED_BACKOFF_IMPLEMENTED,
            "backoff_preauthorized_in_wall_reservation_implemented": BACKOFF_PREAUTHORIZED_IN_WALL_RESERVATION_IMPLEMENTED,
            "injectable_monotonic_clock_and_sleeper_implemented": INJECTABLE_MONOTONIC_CLOCK_AND_SLEEPER_IMPLEMENTED,
            "post_callback_deadline_check_implemented": POST_CALLBACK_DEADLINE_CHECK_IMPLEMENTED,
            "already_running_callback_force_cancellation_implemented": ALREADY_RUNNING_CALLBACK_FORCE_CANCELLATION_IMPLEMENTED,
            "trusted_hard_total_wall_timeout_implemented": TRUSTED_HARD_TOTAL_WALL_TIMEOUT_IMPLEMENTED,
            "requests_per_call_timeout_treated_as_total_deadline": REQUESTS_PER_CALL_TIMEOUT_TREATED_AS_TOTAL_DEADLINE,
            "scheduler_state_durably_persisted": False,
            "clock_or_sleeper_independently_attested": False,
            "real_provider_traffic_observed": False,
            "active_client_or_runner_integrated": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_fake_callback_virtual_time_and_local_tempdir_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "caller_supplied_effect_callback_invocation_capability": True,
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
            "candidate_checkpoint_deadline_and_backoff_scheduler_available": True,
            "trusted_hard_total_wall_timeout_available": False,
            "hung_arbitrary_callback_cancellation_available": False,
            "production_runtime_wrapper_available": False,
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
        raise RuntimeError("V2.42.43 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.43 audit output path is noncanonical")
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
                "candidate_runtime_scheduler": value[
                    "candidate_runtime_scheduler"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
