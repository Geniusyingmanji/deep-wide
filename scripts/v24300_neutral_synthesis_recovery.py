#!/usr/bin/env python3
"""Preregister, run, and decide one neutral real-provider V2.42.99 probe."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError, ResponsesClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
    validate_receipt as validate_slot_receipt,
)
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24299_synthesis_recovery import (  # noqa: E402
    run_v24299_task,
    validate_v24299_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


PROTOCOL_ID = "v24300_neutral_real_provider_bounded_synthesis_recovery_v1"
PROTOCOL = Path("results/v24300_neutral_synthesis_recovery_preregistration_v1_20260803.json")
RESULT = Path("results/v24300_neutral_synthesis_recovery_probe_v1_20260803.json")
DECISION = Path("results/v24300_neutral_synthesis_recovery_decision_v1_20260803.json")
PARENT = Path("results/v24298_v24297_paired_dev64_postterminal_diagnosis_v1_20260803.json")
SOURCE_FILES = (
    "src/deepwide_agent/v24299_synthesis_recovery.py",
    "scripts/v24300_neutral_synthesis_recovery.py",
    "tests/test_v24299_synthesis_recovery.py",
    "tests/test_v24300_neutral_synthesis_recovery.py",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
MODEL_COUNTERS = ("requests", "attempts", "input_tokens", "output_tokens", "total_tokens")
GATES = {
    "maximum_wall_seconds": 180.0,
    "required_completion_kind": "primary",
    "required_model_call_cap": 3,
    "required_total_effects_admitted": 3,
    "required_provider_requests": 3,
    "minimum_provider_attempts": 3,
    "required_plan_effects": 1,
    "required_initial_synthesis_effects": 1,
    "required_recovery_effects": 1,
    "required_repair_effects": 0,
    "required_initial_synthesis_model_request_error": True,
    "required_recovery_attempted": True,
    "required_recovery_succeeded": True,
    "required_recovery_model_request_error": False,
    "required_repair_blocked": False,
    "required_slot_acquisitions": 3,
    "required_search_calls": 0,
    "required_fetch_calls": 0,
}
NEUTRAL_TASK = {
    "opaque_id": "task_000000000000000000000000",
    "question": (
        "Return one Markdown table about this synthetic example only. "
        "The column names are: Name, Version, and Date. "
        "Use exactly one data row: NeutralWidget, 1.0, 2026-08-03."
    ),
}
NEUTRAL_PLAN = json.dumps(
    {
        "columns": ["Name", "Version", "Date"],
        "language": "English",
        "row_target_hint": "one synthetic row",
        "queries": [
            "neutral synthetic query one",
            "neutral synthetic query two",
            "neutral synthetic query three",
            "neutral synthetic query four",
        ],
    }
)


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(value: object) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.00 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.00 expected object: {relative}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.43.00 credential literal in {relative}")
        output[relative] = sha256(path)
    return output


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


class NeutralFaultInjectedModel:
    """Plan locally, fail first synthesis after slot acquisition, then go real."""

    def __init__(self, real: Any) -> None:
        self.real = real
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.calls = 0
        self.failures = 0
        self._invocations = 0
        self.plan_locally_returned = 0
        self.initial_synthesis_failures_injected = 0
        self.real_recovery_requests = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        del system, user
        self._invocations += 1
        if self._invocations == 1:
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 1
            self.output_tokens += 1
            self.total_tokens += 2
            self.calls += 1
            self.plan_locally_returned += 1
            from types import SimpleNamespace

            return SimpleNamespace(text=NEUTRAL_PLAN)
        if self._invocations == 2:
            self.requests += 1
            self.attempts += 1
            self.failures += 1
            self.initial_synthesis_failures_injected += 1
            raise ModelRequestError("neutral injected synthesis failure")
        before = {
            name: int(getattr(self.real, name, 0) or 0) for name in MODEL_COUNTERS
        }
        try:
            value = self.real.complete(
                "You create exact Markdown tables from synthetic facts only.",
                (
                    "Return only this exact 3-column Markdown table with one row. "
                    "Columns: Name, Version, Date. Values: NeutralWidget, 1.0, "
                    "2026-08-03. Do not add prose."
                ),
                max_output_tokens=min(max_output_tokens, 1024),
                json_mode=json_mode,
            )
            self.real_recovery_requests += 1
            return value
        finally:
            for name in MODEL_COUNTERS:
                delta = int(getattr(self.real, name, 0) or 0) - before[name]
                setattr(self, name, int(getattr(self, name, 0) or 0) + delta)


class NoEffectSearch:
    calls = failures = tool_calls = fetch_calls = fetch_failures = 0
    input_tokens = output_tokens = total_tokens = 0

    def search_many(self, queries, **kwargs):
        del kwargs
        if list(queries):
            raise RuntimeError("V2.43.00 neutral plan unexpectedly requested search")
        return []

    def fetch_urls(self, requests_):
        if list(requests_):
            raise RuntimeError("V2.43.00 neutral probe unexpectedly requested fetch")
        return []


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    if require_pristine:
        present = [
            str(path)
            for path in (RESULT, DECISION)
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.43.00 future surface is not pristine: {present}")
    parent = _read(root, PARENT)
    if (
        parent.get("role") != "v24298_v24297_paired_dev64_postterminal_diagnosis"
        or parent.get("conclusions", {}).get("reliability_gate_passed") is not False
        or parent.get("conclusions", {}).get("exact220_authorized") is not False
        or parent.get("next_experiment", {}).get("stage")
        != "neutral_provider_failure_recovery_before_any_new_benchmark"
        or not _sealed(parent, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.43.00 diagnosis parent drifted")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24300_neutral_synthesis_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "one_fault_injected_neutral_real_provider_synthesis_recovery_probe",
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "task_contract": {
            "synthetic_neutral_task": True,
            "visible_columns": 3,
            "local_plan_with_four_synthetic_queries_and_zero_external_search": True,
            "task_question_plan_prediction_or_hash_persisted_in_result": False,
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_opened": False,
        },
        "provider": {
            "proxy_url": "http://127.0.0.1:9878/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "timeout_seconds": 180,
            "max_retries": 2,
        },
        "fault_injection": {
            "plan_returned_locally_after_real_global_slot_acquisition": True,
            "first_synthesis_raises_model_request_error_after_real_global_slot_acquisition": True,
            "third_logical_model_call_uses_real_keyless_provider": True,
            "search_or_fetch_effects": False,
            "claim_scope": "provider_failure_recovery_mechanism_not_benchmark_quality",
        },
        "budget_contract": {
            "model_calls": 3,
            "search_queries": 4,
            "fetch_targets": 10,
            "recovery_may_use_only_unused_third_model_call": True,
            "fourth_model_effect_allowed": False,
        },
        "gates": dict(GATES),
        "lease": {
            "path": "outputs/deepwide_benchmark_api.lease.lock",
            "owner": "v24300_neutral_synthesis_recovery_probe_v1",
            "purpose": "neutral_real_provider_bounded_synthesis_recovery",
            "nonblocking_single_owner": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_prompt_response_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_neutral_probe": True,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = protocol.get("surface_manifest")
    source = protocol.get("source_policy")
    auth = protocol.get("authorization")
    if (
        protocol.get("role") != "v24300_neutral_synthesis_recovery_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "one_fault_injected_neutral_real_provider_synthesis_recovery_probe"
        or protocol.get("gates") != GATES
        or protocol.get("budget_contract", {}).get("model_calls") != 3
        or protocol.get("budget_contract", {}).get("fourth_model_effect_allowed")
        is not False
        or not _sealed(protocol, "protocol_payload_sha256")
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(SOURCE_FILES)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(
            sha256(_ordinary(root, relative)) != digest
            for relative, digest in manifest.items()
        )
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(auth, Mapping)
        or auth.get("one_neutral_probe") is not True
        or any(value_ for key, value_ in auth.items() if key != "one_neutral_probe")
    ):
        raise RuntimeError("V2.43.00 protocol drifted")
    parent = _read(root, PARENT)
    if (
        protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or not _sealed(parent, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.43.00 parent binding drifted")
    return protocol


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.43.00 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.43.00 {label} is invalid")
    return number


def project(
    result: Mapping[str, Any],
    *,
    model: NeutralFaultInjectedModel,
    slot_receipt: Mapping[str, Any],
    search: NoEffectSearch,
    wall_seconds: float,
    now: int | None = None,
) -> dict[str, Any]:
    validate_v24299_result(result, "candidate")
    recovery = result["synthesis_recovery"]
    value = {
        "artifact_version": 1,
        "role": "v24300_neutral_synthesis_recovery_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "fault_injected_neutral_real_provider_synthesis_recovery_only",
        "provider": "azure-native-keyless-gpt-5.6-sol",
        "wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "completion_kind": result["completion_kind"],
        "model_budget": {
            "limit": result["budget"]["limits"]["model_calls"],
            "admitted": result["budget"]["admitted_model_calls"],
            "provider_requests": result["cost"]["model"]["requests"],
            "provider_attempts": result["cost"]["model"]["attempts"],
            "slot_acquisitions": slot_receipt["acquisitions"],
            "fourth_provider_effect": False,
        },
        "recovery": {
            "effects_by_stage": dict(recovery["effects_by_stage"]),
            "total_effects_admitted": recovery["total_effects_admitted"],
            "initial_synthesis_model_request_error": recovery[
                "synthesis_initial_model_request_error"
            ],
            "recovery_eligible": recovery["synthesis_recovery_eligible"],
            "recovery_admitted": recovery["synthesis_recovery_admitted"],
            "recovery_attempted": recovery["synthesis_recovery_attempted"],
            "recovery_succeeded": recovery["synthesis_recovery_succeeded"],
            "recovery_model_request_error": recovery[
                "synthesis_recovery_model_request_error"
            ],
            "repair_blocked_after_recovery": recovery[
                "repair_blocked_after_recovery"
            ],
            "local_plan_returns": model.plan_locally_returned,
            "injected_initial_synthesis_failures": model.initial_synthesis_failures_injected,
            "real_recovery_requests": model.real_recovery_requests,
        },
        "search": {
            "calls": search.calls,
            "fetch_calls": search.fetch_calls,
        },
        "source_policy": {
            "synthetic_neutral_task_used_but_not_persisted_or_hashed": True,
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_prompt_response_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired": True,
        },
        "authorization": {
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    budget = value.get("model_budget")
    recovery = value.get("recovery")
    search = value.get("search")
    source = value.get("source_policy")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24300_neutral_synthesis_recovery_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("scope")
        != "fault_injected_neutral_real_provider_synthesis_recovery_only"
        or value.get("provider") != "azure-native-keyless-gpt-5.6-sol"
        or not _sealed(value, "result_payload_sha256")
        or not isinstance(budget, Mapping)
        or not isinstance(recovery, Mapping)
        or not isinstance(search, Mapping)
        or not isinstance(source, Mapping)
        or source.get("synthetic_neutral_task_used_but_not_persisted_or_hashed")
        is not True
        or source.get("shared_api_lease_acquired") is not True
        or any(
            value_
            for key, value_ in source.items()
            if key
            not in {
                "synthetic_neutral_task_used_but_not_persisted_or_hashed",
                "shared_api_lease_acquired",
            }
        )
        or not isinstance(auth, Mapping)
        or any(auth.values())
    ):
        raise RuntimeError("V2.43.00 projection drifted")
    _finite(value.get("wall_seconds"), "wall seconds")
    if (
        budget.get("limit") != 3
        or budget.get("admitted") != 3
        or budget.get("provider_requests") != 3
        or budget.get("slot_acquisitions") != 3
        or budget.get("fourth_provider_effect") is not False
        or recovery.get("total_effects_admitted") != 3
        or recovery.get("effects_by_stage")
        != {"plan": 1, "synthesis_initial": 1, "synthesis_recovery": 1, "repair": 0}
        or recovery.get("initial_synthesis_model_request_error") is not True
        or recovery.get("recovery_attempted") is not True
        or recovery.get("recovery_succeeded") is not True
        or recovery.get("recovery_model_request_error") is not False
        or recovery.get("repair_blocked_after_recovery") is not False
        or recovery.get("local_plan_returns") != 1
        or recovery.get("injected_initial_synthesis_failures") != 1
        or recovery.get("real_recovery_requests") != 1
        or search != {"calls": 0, "fetch_calls": 0}
    ):
        raise RuntimeError("V2.43.00 neutral effect accounting drifted")


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    if (root / RESULT).exists() or (root / RESULT).is_symlink():
        raise FileExistsError(root / RESULT)
    provider = protocol["provider"]
    real = ResponsesClient(
        provider["proxy_url"],
        provider["model"],
        reasoning_effort=provider["reasoning_effort"],
        service_tier=provider["service_tier"],
        timeout=provider["timeout_seconds"],
        max_retries=provider["max_retries"],
    )
    injected = NeutralFaultInjectedModel(real)
    output_root = root / "outputs"
    started = time.monotonic()
    lease = protocol["lease"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / lease["path"],
    ):
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            slots = Path(directory)
            for index in range(1, 3):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            model = GlobalModelSlotLimiter(
                injected,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=2,
                pool_id=POOL_ID,
            )
            search = NoEffectSearch()
            result = run_v24299_task(
                NEUTRAL_TASK,
                arm="candidate",
                model=model,
                search=search,
                limits=ScoreFirstLimits(
                    wall_seconds=180,
                    model_calls=3,
                    search_queries=4,
                    fetch_targets=10,
                    search_results_per_query=3,
                    evidence_chars=60_000,
                    page_chars=5_000,
                ),
                two_wave_policy=TwoWavePolicy(),
                reserve_policy=StagedReservePolicy(),
            )
            slot_receipt = validate_slot_receipt(
                model.receipt(), expected_cap=2, expected_acquisitions=3
            )
    value = project(
        result,
        model=injected,
        slot_receipt=slot_receipt,
        search=search,
        wall_seconds=max(0.0, time.monotonic() - started),
    )
    publish(root / RESULT, value)
    return value


def _checks(result: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    budget = result["model_budget"]
    recovery = result["recovery"]
    effects = recovery["effects_by_stage"]
    search = result["search"]
    return {
        "wall_seconds": float(result["wall_seconds"])
        <= gates["maximum_wall_seconds"],
        "completion_kind": result["completion_kind"]
        == gates["required_completion_kind"],
        "model_call_cap": budget["limit"] == gates["required_model_call_cap"],
        "total_effects_admitted": budget["admitted"]
        == gates["required_total_effects_admitted"],
        "provider_requests": budget["provider_requests"]
        == gates["required_provider_requests"],
        "provider_attempts": budget["provider_attempts"]
        >= gates["minimum_provider_attempts"],
        "plan_effects": effects["plan"] == gates["required_plan_effects"],
        "initial_synthesis_effects": effects["synthesis_initial"]
        == gates["required_initial_synthesis_effects"],
        "recovery_effects": effects["synthesis_recovery"]
        == gates["required_recovery_effects"],
        "repair_effects": effects["repair"] == gates["required_repair_effects"],
        "initial_synthesis_model_request_error": recovery[
            "initial_synthesis_model_request_error"
        ]
        is gates["required_initial_synthesis_model_request_error"],
        "recovery_attempted": recovery["recovery_attempted"]
        is gates["required_recovery_attempted"],
        "recovery_succeeded": recovery["recovery_succeeded"]
        is gates["required_recovery_succeeded"],
        "recovery_model_request_error": recovery["recovery_model_request_error"]
        is gates["required_recovery_model_request_error"],
        "repair_blocked": recovery["repair_blocked_after_recovery"]
        is gates["required_repair_blocked"],
        "slot_acquisitions": budget["slot_acquisitions"]
        == gates["required_slot_acquisitions"],
        "search_calls": search["calls"] == gates["required_search_calls"],
        "fetch_calls": search["fetch_calls"] == gates["required_fetch_calls"],
        "no_fourth_provider_effect": budget["fourth_provider_effect"] is False,
    }


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    result = _read(root, RESULT)
    validate_projection(result)
    checks = _checks(result, protocol["gates"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    value = {
        "artifact_version": 1,
        "role": "v24300_neutral_synthesis_recovery_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_mechanism_go" if passed else "neutral_mechanism_no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {
            "wall_seconds": result["wall_seconds"],
            "completion_kind": result["completion_kind"],
            "model_budget": result["model_budget"],
            "recovery": result["recovery"],
            "search": result["search"],
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "fault_injected_real_provider_recovery_robustness": True,
            "natural_failure_frequency_measured": False,
            "benchmark_quality_measured": False,
            "causal_quality_improvement_proven": False,
            "sota_supported": False,
        },
        "authorization": {
            "successor_dev64_design": passed,
            "successor_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> None:
    checks = value.get("checks")
    failed = value.get("failed_checks")
    claim = value.get("claim_scope")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24300_neutral_synthesis_recovery_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "decision_payload_sha256")
        or not isinstance(checks, Mapping)
        or not isinstance(failed, list)
        or value.get("passed") is not all(checks.values())
        or failed != sorted(name for name, passed in checks.items() if not passed)
        or value.get("status")
        != ("neutral_mechanism_go" if value["passed"] else "neutral_mechanism_no_go")
        or not isinstance(claim, Mapping)
        or claim.get("fault_injected_real_provider_recovery_robustness") is not True
        or any(
            value_
            for key, value_ in claim.items()
            if key != "fault_injected_real_provider_recovery_robustness"
        )
        or not isinstance(auth, Mapping)
        or auth.get("successor_dev64_design") is not value["passed"]
        or any(
            value_
            for key, value_ in auth.items()
            if key != "successor_dev64_design"
        )
    ):
        raise RuntimeError("V2.43.00 decision drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preregister", "probe", "finalize"))
    args = parser.parse_args()
    if args.action == "preregister":
        value = build_protocol()
        path = PROTOCOL
    elif args.action == "probe":
        value = run_probe()
        print(
            json.dumps(
                {"path": str(RESULT), "wall_seconds": value["wall_seconds"]},
                sort_keys=True,
            )
        )
        return
    else:
        value = build_decision()
        path = DECISION
    publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
