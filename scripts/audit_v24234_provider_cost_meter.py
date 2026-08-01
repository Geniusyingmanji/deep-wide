#!/usr/bin/env python3
"""Create-exclusive build audit for the V2.42.34 provider cost meter."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping


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
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    USAGE_NOT_APPLICABLE,
    USAGE_OBSERVED,
    USAGE_UNAVAILABLE,
    build_provider_attempt,
    build_provider_cost_measurement,
    build_provider_meter_contract,
    issue_metered_effect_permit,
    settle_metered_effect_permit,
    validate_provider_cost_measurement,
    validate_provider_meter_contract,
)


ROLE = "v24234_provider_cost_meter_build_audit"
OUTPUT = Path("results/v24234_provider_cost_meter_build_audit_v1_20260801.json")
PARENT_RECEIPT = Path(
    "results/v24233_webswarm_effect_preauthorization_build_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "4630d2056aa7508d5b6a55257dfb4f3f7c75a6dafeff4b08c5ab05644a383cf3"
)
PARENT_PAYLOAD_SHA256 = (
    "fceafc658823913bbf200bfffd8e050f59490266052260499cd1998539874260"
)
PARENT_MANIFEST_SHA256 = (
    "77d73a9a02c7aa9ebc04f87c3b3f499cc4d356393420fac62229c3a4664dbaca"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24233_webswarm_effect_preauthorization.py"),
    Path("tests/test_v24233_webswarm_effect_preauthorization.py"),
    Path("scripts/audit_v24233_webswarm_effect_preauthorization.py"),
    Path("tests/test_audit_v24233_webswarm_effect_preauthorization.py"),
)
MODULE = Path("src/deepwide_agent/v24234_provider_cost_meter.py")
MODULE_TEST = Path("tests/test_v24234_provider_cost_meter.py")
AUDIT = Path("scripts/audit_v24234_provider_cost_meter.py")
AUDIT_TEST = Path("tests/test_audit_v24234_provider_cost_meter.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARDS = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)

PROVIDERS = (
    "azure_responses_model",
    "azure_responses_web_search",
    "anthropic_server_web_search",
    "tavily_search_api",
    "native_http_fetch",
    "local_orchestrator",
    "local_other_tool",
)
ALLOWED_IMPORT_MODULES = frozenset(
    {
        "__future__",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24233_webswarm_effect_preauthorization",
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
        "anyio",
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
REQUIRED_PUBLIC_FUNCTIONS = frozenset(
    {
        "build_provider_attempt",
        "build_provider_cost_measurement",
        "build_provider_meter_contract",
        "issue_metered_effect_permit",
        "settle_metered_effect_permit",
        "validate_provider_attempt",
        "validate_provider_cost_measurement",
        "validate_provider_meter_contract",
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
        raise RuntimeError("V2.42.34 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.34 expected ordinary repository file: {relative}")
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
    functions: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attributes: list[str] = []
    privileged_reads: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
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
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - functions)
    if (
        disallowed_imports
        or forbidden_calls
        or forbidden_attributes
        or privileged_reads
        or missing_functions
    ):
        raise RuntimeError(
            "V2.42.34 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(set(forbidden_attributes))}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "disallowed_import_count": 0,
        "forbidden_file_environment_network_process_or_dynamic_code_call_count": 0,
        "privileged_metadata_read_count": 0,
        "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _signal(kind: str, tactic: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": tactic, "value_sha256": _digest(label)}


def _build_parent_objects() -> dict[str, Any]:
    """Build V2.42.31–33 parents without importing any test helper."""

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
    return {"state": state, "shared": shared}


def _cost(**overrides: int) -> dict[str, int]:
    value = {
        "model_calls": 0,
        "model_attempts": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "other_tool_calls": 0,
        "orchestrator_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "wall_milliseconds": 10_000,
    }
    value.update(overrides)
    return build_cost_vector(**value)


def _provider_contract(provider: str) -> dict[str, Any]:
    if provider == "azure_responses_model":
        reserve = _cost(
            model_calls=1,
            model_attempts=3,
            input_tokens=500,
            output_tokens=100,
        )
        charge_kind = "renderer"
        attempts = 3
    elif provider in {
        "azure_responses_web_search",
        "anthropic_server_web_search",
    }:
        reserve = _cost(
            search_calls=3,
            other_tool_calls=6,
            input_tokens=500,
            output_tokens=100,
        )
        charge_kind = "fanout_execution"
        attempts = 3
    elif provider == "tavily_search_api":
        reserve = _cost(search_calls=3)
        charge_kind = "fanout_execution"
        attempts = 3
    elif provider == "native_http_fetch":
        reserve = _cost(fetch_calls=3)
        charge_kind = "fanout_execution"
        attempts = 3
    elif provider == "local_orchestrator":
        reserve = _cost(orchestrator_calls=1)
        charge_kind = "orchestrator"
        attempts = 1
    elif provider == "local_other_tool":
        reserve = _cost(other_tool_calls=1)
        charge_kind = "other_tool"
        attempts = 1
    else:
        raise RuntimeError("V2.42.34 unknown replay provider")
    contract = build_provider_meter_contract(
        provider_kind=provider,
        charge_kind=charge_kind,
        max_attempts=attempts,
        reserved_cost=reserve,
    )
    validate_provider_meter_contract(contract)
    return contract


def _attempt(
    contract: Mapping[str, Any],
    index: int,
    *,
    label: str,
    outcome: str,
    status: int | None,
    token_state: str,
    input_tokens: int | None,
    output_tokens: int | None,
    tool_state: str,
    tool_calls: int | None,
    wall_milliseconds: int,
    response: bool,
) -> dict[str, Any]:
    provider = str(contract["provider_kind"])
    local = provider.startswith("local_")
    transport = outcome == "transport_error"
    return build_provider_attempt(
        contract=contract,
        attempt_index=index,
        attempt_ref_sha256=_digest(f"attempt-{label}"),
        local_counter_ref_sha256=_digest(f"counter-{label}"),
        outcome=outcome,
        http_status=status,
        provider_response_ref_sha256=(
            _digest(f"response-{label}") if response else None
        ),
        token_usage_state=token_state,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider_tool_usage_state=tool_state,
        provider_tool_calls=tool_calls,
        wall_milliseconds=wall_milliseconds,
        request_body_bytes=(
            0 if local or provider == "native_http_fetch" else 128
        ),
        response_body_bytes=None if local or transport else 256,
    )


def _attempts_for(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    provider = str(contract["provider_kind"])
    observed = USAGE_OBSERVED
    na = USAGE_NOT_APPLICABLE
    if provider == "azure_responses_model":
        return [
            _attempt(
                contract,
                1,
                label=f"{provider}-1",
                outcome="retryable_http",
                status=429,
                token_state=observed,
                input_tokens=0,
                output_tokens=0,
                tool_state=na,
                tool_calls=None,
                wall_milliseconds=1000,
                response=True,
            ),
            _attempt(
                contract,
                2,
                label=f"{provider}-2",
                outcome="success",
                status=200,
                token_state=observed,
                input_tokens=100,
                output_tokens=20,
                tool_state=na,
                tool_calls=None,
                wall_milliseconds=2000,
                response=True,
            ),
        ]
    if provider == "azure_responses_web_search":
        return [
            _attempt(
                contract,
                1,
                label=provider,
                outcome="success",
                status=200,
                token_state=observed,
                input_tokens=100,
                output_tokens=20,
                tool_state=observed,
                tool_calls=2,
                wall_milliseconds=2000,
                response=True,
            )
        ]
    if provider == "anthropic_server_web_search":
        return [
            _attempt(
                contract,
                1,
                label=f"{provider}-1",
                outcome="retryable_http",
                status=429,
                token_state=USAGE_UNAVAILABLE,
                input_tokens=None,
                output_tokens=None,
                tool_state=USAGE_UNAVAILABLE,
                tool_calls=None,
                wall_milliseconds=1000,
                response=True,
            ),
            _attempt(
                contract,
                2,
                label=f"{provider}-2",
                outcome="success",
                status=200,
                token_state=observed,
                input_tokens=80,
                output_tokens=10,
                tool_state=observed,
                tool_calls=1,
                wall_milliseconds=2000,
                response=True,
            ),
        ]
    if provider == "tavily_search_api":
        return [
            _attempt(
                contract,
                1,
                label=f"{provider}-1",
                outcome="key_local_http",
                status=432,
                token_state=na,
                input_tokens=None,
                output_tokens=None,
                tool_state=na,
                tool_calls=None,
                wall_milliseconds=1000,
                response=True,
            ),
            _attempt(
                contract,
                2,
                label=f"{provider}-2",
                outcome="success",
                status=200,
                token_state=na,
                input_tokens=None,
                output_tokens=None,
                tool_state=na,
                tool_calls=None,
                wall_milliseconds=2000,
                response=True,
            ),
        ]
    if provider == "native_http_fetch":
        return [
            _attempt(
                contract,
                1,
                label=f"{provider}-1",
                outcome="transport_error",
                status=None,
                token_state=na,
                input_tokens=None,
                output_tokens=None,
                tool_state=na,
                tool_calls=None,
                wall_milliseconds=1000,
                response=False,
            ),
            _attempt(
                contract,
                2,
                label=f"{provider}-2",
                outcome="success",
                status=200,
                token_state=na,
                input_tokens=None,
                output_tokens=None,
                tool_state=na,
                tool_calls=None,
                wall_milliseconds=2000,
                response=True,
            ),
        ]
    outcome = "local_success" if provider == "local_orchestrator" else "local_error"
    return [
        _attempt(
            contract,
            1,
            label=provider,
            outcome=outcome,
            status=None,
            token_state=na,
            input_tokens=None,
            output_tokens=None,
            tool_state=na,
            tool_calls=None,
            wall_milliseconds=1000,
            response=True,
        )
    ]


def replay_synthetic_contracts() -> dict[str, Any]:
    parent = _build_parent_objects()
    state = parent["state"]
    shared = parent["shared"]
    provider_rows: list[dict[str, Any]] = []
    fallback_exact = False
    for provider in PROVIDERS:
        contract = _provider_contract(provider)
        state = issue_metered_effect_permit(
            state,
            contract=contract,
            guidance_contract=shared["contract"],
            guidance_policy=shared["guidance_policy"],
            guidance_arm=shared["guidance_arm"],
            scouts=shared["scouts"],
            probe=shared["probe"],
            experience=shared["experience"],
            permit_ref_sha256=_digest(f"permit-{provider}"),
            charge_ref_sha256=_digest(f"charge-{provider}"),
        )
        permit = next(
            event
            for event in state["events"]
            if event.get("permit_ref_sha256") == _digest(f"permit-{provider}")
        )
        attempts = _attempts_for(contract)
        measurement = build_provider_cost_measurement(
            contract=contract,
            permit=permit,
            measurement_ref_sha256=_digest(f"measurement-{provider}"),
            attempts=attempts,
        )
        validate_provider_cost_measurement(
            measurement,
            contract=contract,
            permit=permit,
        )
        if provider == "anthropic_server_web_search":
            fallback_exact = (
                measurement["reservation_fallback_dimensions"]
                == ["other_tool_calls", "input_tokens", "output_tokens"]
                and measurement["settlement_cost"]["other_tool_calls"]
                == contract["reserved_cost"]["other_tool_calls"]
                and measurement["settlement_cost"]["input_tokens"]
                == contract["reserved_cost"]["input_tokens"]
                and measurement["settlement_cost"]["output_tokens"]
                == contract["reserved_cost"]["output_tokens"]
                and measurement["settlement_cost"]["search_calls"] == 2
                and measurement["missing_applicable_usage_treated_as_zero"] is False
            )
        state = settle_metered_effect_permit(
            state,
            meter_contract=contract,
            measurement=measurement,
            guidance_contract=shared["contract"],
            guidance_policy=shared["guidance_policy"],
            guidance_arm=shared["guidance_arm"],
            scouts=shared["scouts"],
            probe=shared["probe"],
            experience=shared["experience"],
        )
        validate_effect_preauthorization_state(state, **shared)
        provider_rows.append(
            {
                "provider_kind": provider,
                "attempt_count": measurement["attempt_count"],
                "logical_status": measurement["logical_status"],
                "reservation_fallback_applied": measurement[
                    "reservation_fallback_applied"
                ],
                "settlement_eligible": measurement["settlement_eligible"],
            }
        )

    over_contract = build_provider_meter_contract(
        provider_kind="azure_responses_model",
        charge_kind="renderer",
        max_attempts=2,
        reserved_cost=_cost(
            model_calls=1,
            model_attempts=2,
            input_tokens=5,
            output_tokens=5,
        ),
    )
    over_state = issue_metered_effect_permit(
        state,
        contract=over_contract,
        guidance_contract=shared["contract"],
        guidance_policy=shared["guidance_policy"],
        guidance_arm=shared["guidance_arm"],
        scouts=shared["scouts"],
        probe=shared["probe"],
        experience=shared["experience"],
        permit_ref_sha256=_digest("permit-over"),
        charge_ref_sha256=_digest("charge-over"),
    )
    over_permit = next(
        event
        for event in over_state["events"]
        if event.get("permit_ref_sha256") == _digest("permit-over")
    )
    over_attempts = [
        _attempt(
            over_contract,
            1,
            label="over-unavailable",
            outcome="retryable_http",
            status=429,
            token_state=USAGE_UNAVAILABLE,
            input_tokens=None,
            output_tokens=None,
            tool_state=USAGE_NOT_APPLICABLE,
            tool_calls=None,
            wall_milliseconds=1000,
            response=True,
        ),
        _attempt(
            over_contract,
            2,
            label="over-observed",
            outcome="success",
            status=200,
            token_state=USAGE_OBSERVED,
            input_tokens=6,
            output_tokens=1,
            tool_state=USAGE_NOT_APPLICABLE,
            tool_calls=None,
            wall_milliseconds=1000,
            response=True,
        ),
    ]
    over_measurement = build_provider_cost_measurement(
        contract=over_contract,
        permit=over_permit,
        measurement_ref_sha256=_digest("measurement-over"),
        attempts=over_attempts,
    )
    if (
        over_measurement["observed_cost_lower_bound"]["input_tokens"] != 6
        or over_measurement["settlement_cost"]["input_tokens"] != 5
        or over_measurement["observed_lower_bound_within_reservation"] is not False
        or over_measurement["settlement_cost_within_reservation"] is not True
        or over_measurement["settlement_eligible"] is not False
    ):
        raise RuntimeError("V2.42.34 fallback masked observed over-reservation")
    observed_overrun_rejected = False
    try:
        settle_metered_effect_permit(
            over_state,
            meter_contract=over_contract,
            measurement=over_measurement,
            guidance_contract=shared["contract"],
            guidance_policy=shared["guidance_policy"],
            guidance_arm=shared["guidance_arm"],
            scouts=shared["scouts"],
            probe=shared["probe"],
            experience=shared["experience"],
        )
    except ValueError:
        observed_overrun_rejected = True
    if not observed_overrun_rejected:
        raise RuntimeError("V2.42.34 accepted an observed cost above reservation")
    if not fallback_exact:
        raise RuntimeError("V2.42.34 reservation fallback replay drifted")
    if state["settled_permit_count"] != len(PROVIDERS):
        raise RuntimeError("V2.42.34 provider settlement replay is incomplete")

    encoded = json.dumps(provider_rows, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.34 synthetic replay exposed forbidden content")
    return {
        "provider_count": len(PROVIDERS),
        "provider_kinds": list(PROVIDERS),
        "provider_rows": provider_rows,
        "all_provider_contracts_and_v24233_settlements_replayed": True,
        "model_logical_call_and_http_attempt_mapping_replayed": True,
        "hosted_search_http_attempt_and_provider_action_mapping_replayed": True,
        "tavily_and_fetch_token_usage_not_applicable_replayed": True,
        "transport_failure_has_no_synthetic_response_replayed": True,
        "failed_local_effect_remains_chargeable_replayed": True,
        "missing_applicable_usage_uses_only_dimension_local_reservation_fallback": fallback_exact,
        "missing_applicable_usage_treated_as_zero": False,
        "observed_lower_bound_above_reservation_rejected": observed_overrun_rejected,
        "provider_response_authenticity_independently_verified": False,
        "local_counter_and_clock_independently_attested": False,
        "schema_resealing_without_secret_cryptographically_excluded": False,
        "runtime_provider_wrapper_integrated": False,
        "real_model_search_fetch_or_orchestrator_execution_observed": False,
        "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.34 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent = ordinary(root, PARENT_RECEIPT)
    if sha256(parent) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.34 V2.42.33 parent receipt bytes drifted")
    parent_value = json.loads(parent.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24233_webswarm_effect_preauthorization_build_audit"
        or parent_value.get("audit_valid") is not True
        or parent_value.get("build_only") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.34 parent receipt semantics drifted")
    parent_control_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_control_manifest = {
        name: sha256(path) for name, path in parent_control_paths.items()
    }
    if parent_control_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.34 V2.42.33 parent control files drifted")
    if payload_sha256(parent_control_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.34 V2.42.33 parent manifest seal drifted")

    sources = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.34 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS
    }
    module_name = "v24234_provider_cost_meter"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.34 appears in active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "policy_id": POLICY_ID,
        "label_blind_runtime": True,
        "build_only": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24233_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24233_control_files_rehashed": len(parent_control_manifest),
            "v24233_build_only_parent_validated": True,
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
            "module_absent_from_guarded_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(literal_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "synthetic_contract_replay": replay_synthetic_contracts(),
        "scientific_scope": {
            "typed_provider_cost_contract_available": True,
            "usage_observed_unavailable_and_not_applicable_distinguished": True,
            "missing_applicable_usage_not_treated_as_zero": True,
            "missing_usage_settles_against_already_debited_reservation": True,
            "observed_cost_lower_bound_preserved": True,
            "observed_cost_above_reservation_rejected": True,
            "provider_response_hash_and_byte_count_schema_available": True,
            "transport_failure_cannot_claim_response_bytes_or_hash": True,
            "provider_response_authenticity_independently_verified": False,
            "local_counter_and_clock_independently_attested": False,
            "schema_resealing_without_secret_cryptographically_excluded": False,
            "declared_reservation_is_conservative_independently_verified": False,
            "provider_limits_enforce_reservation_independently_verified": False,
            "external_effect_occurrence_or_order_independently_verified": False,
            "runtime_provider_wrapper_integrated": False,
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
            "network_model_search_fetch_subprocess_or_api_called": False,
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
            "build_only_provider_cost_meter_available": True,
            "runtime_provider_wrapper_available": False,
            "independently_attested_provider_cost_available": False,
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
        raise RuntimeError("V2.42.34 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.34 audit output path is noncanonical")
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
                "build_only": value["build_only"],
            }
        )
    )


if __name__ == "__main__":
    main()
