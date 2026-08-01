#!/usr/bin/env python3
"""Create-exclusive no-network audit for V2.42.44 strict JSON parsing."""

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
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    AzureResponsesAttemptValue,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (  # noqa: E402
    RetryDeadlineEffectScheduler,
    build_retry_deadline_contract,
)
from deepwide_agent.v24244_strict_json_parser_boundary import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DUPLICATE_KEY_REJECTION_IMPLEMENTED,
    EPHEMERAL_TEXT_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED,
    EXACT_OBJECT_OR_WHOLE_FENCE_ONLY_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    INTERNAL_REPAIR_PROVIDER_EFFECT_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NESTED_PRIVILEGED_METADATA_REJECTION_IMPLEMENTED,
    NONFINITE_NUMBER_REJECTION_IMPLEMENTED,
    POST_DURABLE_SETTLEMENT_PARSE_BOUNDARY_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SEARCH_OR_PAGE_PARSER_INTEGRATION_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    STRUCTURAL_BUDGET_IMPLEMENTED,
    StrictJsonParserBoundaryError,
    build_strict_json_parser_contract,
    parse_settled_model_json,
    validate_strict_json_parser_receipt,
)


ROLE = "v24244_strict_json_parser_boundary_candidate_audit"
OUTPUT = Path(
    "results/v24244_strict_json_parser_boundary_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24243_retry_deadline_scheduler_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "a15825d8343511b27e508ae011a5579dff71d3687cfff44ea602b84e66fcaffa"
)
PARENT_PAYLOAD_SHA256 = (
    "6400bc8ed8d1fb7a61beacb76d2f90e1b6973d764de2ea0e93755db23b94e062"
)
PARENT_MANIFEST_SHA256 = (
    "f26af43875ed51cc6de5b1441fef78fc9f7c4091b2629996227ed3e964a31280"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24243_retry_deadline_scheduler.py"),
    Path("tests/test_v24243_retry_deadline_scheduler.py"),
    Path("scripts/audit_v24243_retry_deadline_scheduler.py"),
    Path("tests/test_audit_v24243_retry_deadline_scheduler.py"),
)
MODULE = Path("src/deepwide_agent/v24244_strict_json_parser_boundary.py")
MODULE_TEST = Path("tests/test_v24244_strict_json_parser_boundary.py")
AUDIT = Path("scripts/audit_v24244_strict_json_parser_boundary.py")
AUDIT_TEST = Path("tests/test_audit_v24244_strict_json_parser_boundary.py")
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
        "json",
        "math",
        "re",
        "unicodedata",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24236_azure_responses_single_attempt",
        "deepwide_agent.v24243_retry_deadline_scheduler",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "StrictJsonParserBoundaryError",
        "StrictJsonParseResult",
        "build_strict_json_parser_contract",
        "validate_strict_json_parser_contract",
        "validate_strict_json_parser_receipt",
        "parse_settled_model_json",
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
        "sleep",
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
        raise RuntimeError("V2.42.44 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.44 expected ordinary repository file: {relative}")
    return path


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    symbols: set[str] = set()
    forbidden_calls: list[str] = []
    expansive_calls: list[str] = []
    json_load_sites = 0
    scheduler_validation_sites = 0
    repair_or_provider_call_sites = 0
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
                if node.func.id == "validate_retry_deadline_execution_receipt":
                    scheduler_validation_sites += 1
                if node.func.id in {"callback", "complete", "single_attempt"}:
                    repair_or_provider_call_sites += 1
            elif isinstance(node.func, ast.Attribute):
                attribute = node.func.attr
                if attribute in FORBIDDEN_ATTRIBUTES:
                    expansive_calls.append(attribute)
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "json"
                    and attribute == "loads"
                ):
                    json_load_sites += 1
                if attribute in {"complete", "single_attempt", "run_effect"}:
                    repair_or_provider_call_sites += 1
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    missing = sorted(REQUIRED_PUBLIC_SYMBOLS - symbols)
    if (
        disallowed_imports
        or forbidden_calls
        or expansive_calls
        or missing
        or json_load_sites != 1
        or scheduler_validation_sites != 1
        or repair_or_provider_call_sites != 0
    ):
        raise RuntimeError(
            "V2.42.44 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"expansive={expansive_calls}, missing={missing}, "
            f"json_loads={json_load_sites}, scheduler_validation="
            f"{scheduler_validation_sites}, provider={repair_or_provider_call_sites}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "json_load_call_site_count": json_load_sites,
        "scheduler_receipt_validation_call_site_count": scheduler_validation_sites,
        "repair_or_provider_effect_call_site_count": repair_or_provider_call_sites,
        "direct_network_environment_file_process_subprocess_or_dynamic_code_capability": False,
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


class _Clock:
    def __init__(self) -> None:
        self.now_ns = 10_000_000_000

    def monotonic_ns(self) -> int:
        return self.now_ns

    def sleep(self, seconds: float) -> None:
        self.now_ns += int(round(seconds * 1_000_000_000))

    def advance_ms(self, milliseconds: int) -> None:
        self.now_ns += milliseconds * 1_000_000


def replay_fake_parser() -> dict[str, Any]:
    initial, shared = _parent()
    meter = build_provider_meter_contract(
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
            wall_milliseconds=1000,
        ),
    )
    schedule = build_retry_deadline_contract(
        meter_contract=meter,
        total_deadline_milliseconds=500,
        minimum_attempt_window_milliseconds=50,
        initial_backoff_milliseconds=10,
        backoff_multiplier=2,
        maximum_backoff_milliseconds=100,
    )
    parser_contract = build_strict_json_parser_contract(
        maximum_text_characters=1000,
        maximum_utf8_bytes=2000,
        maximum_depth=8,
        maximum_nodes=100,
        maximum_object_members=20,
        maximum_array_items=20,
        maximum_string_characters=500,
    )
    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        coordinator = DurablePreauthorizedEffectCoordinator.initialize(
            root=Path(directory).resolve(),
            journal_namespace_sha256=_digest("v24244-audit-journal"),
            initial_state=initial,
            **shared,
        )
        clock = _Clock()
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=coordinator,
            monotonic_ns=clock.monotonic_ns,
            sleeper=clock.sleep,
        )

        def callback(invocation):
            clock.advance_ms(1)
            observation = build_provider_attempt_observation(
                invocation=invocation,
                outcome="success",
                http_status=200,
                provider_response_ref_sha256=_digest("v24244-audit-response"),
                token_usage_state=USAGE_OBSERVED,
                input_tokens=20,
                output_tokens=5,
                provider_tool_usage_state=USAGE_NOT_APPLICABLE,
                provider_tool_calls=None,
                request_body_bytes=64,
                response_body_bytes=52,
            )
            return ProviderAttemptResult(
                observation=observation,
                value=AzureResponsesAttemptValue(
                    text='{"rows":[{"name":"synthetic private row"}],"ready":true}',
                    usage={"input_tokens": 20, "output_tokens": 5},
                    response_id="synthetic-response",
                    output_truncated=False,
                ),
            )

        scheduled = scheduler.run_effect(
            meter_contract=meter,
            scheduler_contract=schedule,
            invocation_ref_sha256=_digest("v24244-audit-invocation"),
            callback=callback,
        )
        parsed = parse_settled_model_json(
            scheduled,
            parser_contract=parser_contract,
        )
        validate_strict_json_parser_receipt(parsed.receipt)
        if "synthetic private" in json.dumps(parsed.receipt, ensure_ascii=False):
            raise RuntimeError("V2.42.44 raw parsed content entered receipt")
        before_failure = coordinator.journal.load()
        rejected = 0
        for text in (
            '{"x":1,"x":2}',
            '{"outer":{"groundTruth":"private"}}',
            '{"x":NaN}',
        ):
            substituted = type(scheduled)(
                receipt=scheduled.receipt,
                value=AzureResponsesAttemptValue(
                    text=text,
                    usage=scheduled.value.usage,
                    response_id=scheduled.value.response_id,
                    output_truncated=False,
                ),
            )
            try:
                parse_settled_model_json(
                    substituted,
                    parser_contract=parser_contract,
                )
            except StrictJsonParserBoundaryError:
                rejected += 1
        after_failure = coordinator.journal.load()
        return {
            "local_tempdir_virtual_time_and_ephemeral_synthetic_value_only": True,
            "network_socket_model_search_fetch_or_api_called": False,
            "durable_parent_settled_before_parse": before_failure[
                "settled_permit_count"
            ]
            == 1,
            "parsed_top_level_member_count": parsed.receipt[
                "top_level_member_count"
            ],
            "duplicate_privileged_and_nonfinite_cases_rejected": rejected == 3,
            "parse_rejection_created_no_new_journal_event": before_failure[
                "state_sha256"
            ]
            == after_failure["state_sha256"],
            "internal_repair_provider_effect_called": parsed.receipt[
                "internal_repair_provider_effect_called"
            ],
            "raw_provider_or_parsed_string_in_receipt": False,
            "ephemeral_text_to_parent_response_binding_independently_verified": parsed.receipt[
                "ephemeral_text_to_parent_response_binding_independently_verified"
            ],
            "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
        }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.44 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.44 parent receipt bytes drifted")
    parent_value = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24243_retry_deadline_scheduler_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.44 parent receipt semantics drifted")
    parent_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.44 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.44 parent manifest seal drifted")
    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.44 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24244_strict_json_parser_boundary"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.44 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time())
        if created_at_unix is None
        else int(created_at_unix),
        "label_blind_runtime": True,
        "candidate_runtime_parser_boundary": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24243_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24243_control_files_rehashed": len(parent_manifest),
            "v24243_candidate_parent_validated": True,
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
        "fake_parser_replay": replay_fake_parser(),
        "scientific_scope": {
            "post_durable_settlement_parse_boundary_implemented": POST_DURABLE_SETTLEMENT_PARSE_BOUNDARY_IMPLEMENTED,
            "exact_object_or_whole_fence_only_implemented": EXACT_OBJECT_OR_WHOLE_FENCE_ONLY_IMPLEMENTED,
            "duplicate_key_rejection_implemented": DUPLICATE_KEY_REJECTION_IMPLEMENTED,
            "nonfinite_number_rejection_implemented": NONFINITE_NUMBER_REJECTION_IMPLEMENTED,
            "structural_budget_implemented": STRUCTURAL_BUDGET_IMPLEMENTED,
            "nested_privileged_metadata_rejection_implemented": NESTED_PRIVILEGED_METADATA_REJECTION_IMPLEMENTED,
            "internal_repair_provider_effect_implemented": INTERNAL_REPAIR_PROVIDER_EFFECT_IMPLEMENTED,
            "search_or_page_parser_integration_implemented": SEARCH_OR_PAGE_PARSER_INTEGRATION_IMPLEMENTED,
            "ephemeral_text_to_parent_response_binding_independently_verified": EPHEMERAL_TEXT_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED,
            "schema_resealing_without_secret_cryptographically_excluded": False,
            "real_provider_traffic_observed": False,
            "active_client_or_runner_integrated": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_synthetic_ephemeral_value_and_local_tempdir_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "pure_ephemeral_parser_capability": True,
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
            "candidate_post_settlement_strict_json_parser_available": True,
            "hidden_parser_repair_effect_available": False,
            "search_or_page_parser_available": False,
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
        raise RuntimeError("V2.42.44 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.44 audit output path is noncanonical")
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
                "candidate_runtime_parser_boundary": value[
                    "candidate_runtime_parser_boundary"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
