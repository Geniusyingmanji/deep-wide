#!/usr/bin/env python3
"""Gate bounded synthesis recovery under eight-way real-provider concurrency."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import sys
import tempfile
import threading
import time
from collections import Counter
from collections.abc import Mapping, Sequence
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
from scripts import v24300_neutral_synthesis_recovery as parent_gate  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


PROTOCOL_ID = "v24301_neutral_concurrent_bounded_synthesis_recovery_v1"
PROTOCOL = Path(
    "results/v24301_neutral_concurrent_synthesis_recovery_preregistration_v1_20260803.json"
)
PREAUDIT = Path(
    "results/v24301_neutral_concurrent_synthesis_recovery_preactivation_audit_v1_20260803.json"
)
RESULT = Path(
    "results/v24301_neutral_concurrent_synthesis_recovery_probe_v1_20260803.json"
)
DECISION = Path(
    "results/v24301_neutral_concurrent_synthesis_recovery_decision_v1_20260803.json"
)
POSTAUDIT = Path(
    "results/v24301_neutral_concurrent_synthesis_recovery_postresult_audit_v1_20260803.json"
)
PARENT = parent_gate.DECISION
TASK_COUNT = 8
SLOT_CAP = 8
MODEL_CALLS_PER_TASK = 3
TOTAL_EFFECTS = TASK_COUNT * MODEL_CALLS_PER_TASK
SOURCE_FILES = (
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24299_synthesis_recovery.py",
    "scripts/v24300_neutral_synthesis_recovery.py",
    "scripts/v24301_neutral_concurrent_synthesis_recovery.py",
    "tests/test_v24299_synthesis_recovery.py",
    "tests/test_v24300_neutral_synthesis_recovery.py",
    "tests/test_v24301_neutral_concurrent_synthesis_recovery.py",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
CONTENT_LITERALS = (
    "NeutralWidget",
    "neutral synthetic query one",
    "neutral_concurrency_task_",
    "Return one Markdown table about this synthetic example only",
)
GATES = {
    "maximum_wall_seconds": 180.0,
    "required_task_count": TASK_COUNT,
    "required_primary_tasks": TASK_COUNT,
    "required_model_call_limit_per_task": MODEL_CALLS_PER_TASK,
    "required_total_effects_admitted": TOTAL_EFFECTS,
    "required_logical_provider_requests": TOTAL_EFFECTS,
    "minimum_provider_attempts": TOTAL_EFFECTS,
    "required_real_recovery_requests": TASK_COUNT,
    "required_plan_effects": TASK_COUNT,
    "required_initial_synthesis_effects": TASK_COUNT,
    "required_recovery_effects": TASK_COUNT,
    "required_repair_effects": 0,
    "required_initial_synthesis_failures": TASK_COUNT,
    "required_recovery_attempts": TASK_COUNT,
    "required_recovery_successes": TASK_COUNT,
    "required_recovery_provider_failures": 0,
    "required_slot_cap": SLOT_CAP,
    "required_slot_acquisitions": TOTAL_EFFECTS,
    "required_shared_slot_barrier_participants": TASK_COUNT,
    "required_shared_slot_barrier_failures": 0,
    "required_fourth_provider_effects": 0,
    "required_search_calls": 0,
    "required_fetch_calls": 0,
}


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
        raise RuntimeError(f"V2.43.01 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.01 expected object: {relative}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.43.01 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.43.01 {label} is invalid")
    return number


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.43.01 credential literal in {relative}")
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


def neutral_task(index: int) -> dict[str, str]:
    if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= TASK_COUNT:
        raise ValueError("invalid V2.43.01 neutral task index")
    return {
        "opaque_id": f"neutral_concurrency_task_{index:02d}",
        "question": str(parent_gate.NEUTRAL_TASK["question"]),
    }


class ConcurrentNeutralFaultInjectedModel(parent_gate.NeutralFaultInjectedModel):
    """Hold a real global slot until all eight recovery calls are admitted."""

    def __init__(self, real: Any, barrier: threading.Barrier) -> None:
        super().__init__(real)
        self.barrier = barrier
        self.shared_slot_barrier_arrivals = 0
        self.shared_slot_barrier_passes = 0
        self.shared_slot_barrier_failures = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        if self._invocations == 2:
            self.shared_slot_barrier_arrivals += 1
            try:
                self.barrier.wait(timeout=120.0)
            except threading.BrokenBarrierError as exc:
                self.shared_slot_barrier_failures += 1
                self._invocations += 1
                self.requests += 1
                self.attempts += 1
                self.failures += 1
                raise ModelRequestError(
                    "neutral concurrent recovery barrier failure"
                ) from exc
            self.shared_slot_barrier_passes += 1
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24300_neutral_synthesis_recovery_decision"
        or value.get("protocol_id") != parent_gate.PROTOCOL_ID
        or value.get("status") != "neutral_mechanism_go"
        or value.get("passed") is not True
        or not _sealed(value, "decision_payload_sha256")
        or not isinstance(authorization, Mapping)
        or authorization.get("successor_dev64_design") is not True
        or authorization.get("successor_dev64_launch") is not False
        or authorization.get("exact220_launch") is not False
    ):
        raise RuntimeError("V2.43.01 parent decision drifted")
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    if require_pristine:
        present = [
            str(path)
            for path in (PREAUDIT, RESULT, DECISION, POSTAUDIT)
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.43.01 future surface is not pristine: {present}")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24301_neutral_concurrent_synthesis_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "eight_independent_fault_injected_neutral_real_provider_recoveries",
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "task_contract": {
            "task_count": TASK_COUNT,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "synthetic_neutral_tasks_only": True,
            "independent_model_and_search_instances_per_task": True,
            "task_prompt_plan_response_prediction_or_hash_persisted": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_or_score_opened": False,
        },
        "concurrency_contract": {
            "executor_workers": TASK_COUNT,
            "shared_global_model_slot_cap": SLOT_CAP,
            "barrier_inside_recovery_complete_after_global_slot_acquisition": True,
            "all_workers_must_hold_one_shared_slot_before_real_recovery": True,
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
            "local_plan_effects": TASK_COUNT,
            "injected_initial_synthesis_provider_failures": TASK_COUNT,
            "real_third_slot_recovery_requests": TASK_COUNT,
            "fourth_model_effect_allowed": False,
            "search_or_fetch_effects_allowed": False,
            "claim_scope": "concurrent_provider_recovery_robustness_not_benchmark_quality",
        },
        "budget_contract": {
            "model_calls_per_task": MODEL_CALLS_PER_TASK,
            "model_calls_total": TOTAL_EFFECTS,
            "search_queries_per_task": 4,
            "fetch_targets_per_task": 10,
            "recovery_may_use_only_unused_third_model_call": True,
            "fourth_model_effect_allowed": False,
        },
        "gates": dict(GATES),
        "lease": {
            "path": "outputs/deepwide_benchmark_api.lease.lock",
            "owner": "v24301_neutral_concurrent_synthesis_recovery_probe_v1",
            "purpose": "neutral_concurrent_real_provider_bounded_synthesis_recovery",
            "nonblocking_single_owner": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "question_prompt_response_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_neutral_concurrency_probe": True,
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
    task_contract = protocol.get("task_contract")
    concurrency = protocol.get("concurrency_contract")
    if (
        protocol.get("role")
        != "v24301_neutral_concurrent_synthesis_recovery_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "eight_independent_fault_injected_neutral_real_provider_recoveries"
        or protocol.get("gates") != GATES
        or protocol.get("budget_contract", {}).get("model_calls_per_task")
        != MODEL_CALLS_PER_TASK
        or protocol.get("budget_contract", {}).get("model_calls_total")
        != TOTAL_EFFECTS
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
        or not isinstance(task_contract, Mapping)
        or task_contract.get("task_count") != TASK_COUNT
        or task_contract.get("runtime_input_keys_exactly_opaque_id_and_question")
        is not True
        or task_contract.get("synthetic_neutral_tasks_only") is not True
        or not isinstance(concurrency, Mapping)
        or concurrency.get("executor_workers") != TASK_COUNT
        or concurrency.get("shared_global_model_slot_cap") != SLOT_CAP
        or concurrency.get(
            "barrier_inside_recovery_complete_after_global_slot_acquisition"
        )
        is not True
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(auth, Mapping)
        or auth.get("one_neutral_concurrency_probe") is not True
        or any(
            setting
            for key, setting in auth.items()
            if key != "one_neutral_concurrency_probe"
        )
    ):
        raise RuntimeError("V2.43.01 protocol drifted")
    _parent(root)
    if protocol.get("parent") != {
        "path": str(PARENT),
        "sha256": sha256(root / PARENT),
    }:
        raise RuntimeError("V2.43.01 parent binding drifted")
    return protocol


def build_preactivation_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    future_pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (RESULT, DECISION, POSTAUDIT)
    )
    lease_path = root / protocol["lease"]["path"]
    lease_path_valid = (
        lease_path.resolve(strict=False).is_relative_to((root / "outputs").resolve())
        and not lease_path.is_symlink()
    )
    findings = []
    if not future_pristine:
        findings.append("future_surface_not_pristine")
    if not lease_path_valid:
        findings.append("shared_lease_path_invalid")
    value = {
        "artifact_version": 1,
        "role": "v24301_neutral_concurrent_synthesis_recovery_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "parent_single_task_gate_go": True,
            "source_manifest_exact": True,
            "credential_literal_scan_clear": True,
            "runtime_input_exactly_opaque_id_and_question": True,
            "benchmark_or_evaluator_surface_authorized": False,
            "future_surface_pristine": future_pristine,
            "shared_nonblocking_lease_path_valid": lease_path_valid,
            "lease_observation_not_used_as_lock_authority": True,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "one_neutral_concurrency_probe": not findings,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_preactivation_audit(root, value=value)
    return value


def validate_preactivation_audit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else _read(root, PREAUDIT)
    auth = audit.get("authorization")
    if (
        audit.get("role")
        != "v24301_neutral_concurrent_synthesis_recovery_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or not isinstance(auth, Mapping)
        or auth.get("one_neutral_concurrency_probe") is not True
        or any(
            setting
            for key, setting in auth.items()
            if key != "one_neutral_concurrency_probe"
        )
        or audit.get("provenance", {}).get("protocol_sha256")
        != sha256(root / PROTOCOL)
    ):
        raise RuntimeError("V2.43.01 preactivation audit drifted")
    return audit


def _worker(
    index: int,
    *,
    provider: Mapping[str, Any],
    slot_directory: Path,
    output_root: Path,
    barrier: threading.Barrier,
) -> dict[str, Any]:
    started = time.monotonic()
    real = ResponsesClient(
        str(provider["proxy_url"]),
        str(provider["model"]),
        reasoning_effort=str(provider["reasoning_effort"]),
        service_tier=str(provider["service_tier"]),
        timeout=int(provider["timeout_seconds"]),
        max_retries=int(provider["max_retries"]),
    )
    injected = ConcurrentNeutralFaultInjectedModel(real, barrier)
    model = GlobalModelSlotLimiter(
        injected,
        slot_directory=slot_directory,
        output_root=output_root,
        slot_cap=SLOT_CAP,
        pool_id=POOL_ID,
    )
    search = parent_gate.NoEffectSearch()
    result = run_v24299_task(
        neutral_task(index),
        arm="candidate",
        model=model,
        search=search,
        limits=ScoreFirstLimits(
            wall_seconds=180,
            model_calls=MODEL_CALLS_PER_TASK,
            search_queries=4,
            fetch_targets=10,
            search_results_per_query=3,
            evidence_chars=60_000,
            page_chars=5_000,
        ),
        two_wave_policy=TwoWavePolicy(),
        reserve_policy=StagedReservePolicy(),
    )
    validate_v24299_result(result, "candidate")
    receipt = validate_slot_receipt(
        model.receipt(), expected_cap=SLOT_CAP, expected_acquisitions=3
    )
    recovery = result["synthesis_recovery"]
    value = {
        "worker_index": index,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "completion_kind": result["completion_kind"],
        "model_budget": {
            "limit": result["budget"]["limits"]["model_calls"],
            "admitted": result["budget"]["admitted_model_calls"],
            "logical_provider_requests": result["cost"]["model"]["requests"],
            "provider_attempts": result["cost"]["model"]["attempts"],
            "slot_acquisitions": receipt["acquisitions"],
            "slot_acquisition_counts": receipt["slot_acquisition_counts"],
            "slot_wait_seconds": receipt["total_wait_seconds"],
            "fourth_provider_effect": result["budget"]["admitted_model_calls"] > 3,
        },
        "recovery": {
            "effects_by_stage": dict(recovery["effects_by_stage"]),
            "total_effects_admitted": recovery["total_effects_admitted"],
            "initial_synthesis_model_request_error": recovery[
                "synthesis_initial_model_request_error"
            ],
            "recovery_attempted": recovery["synthesis_recovery_attempted"],
            "recovery_succeeded": recovery["synthesis_recovery_succeeded"],
            "recovery_model_request_error": recovery[
                "synthesis_recovery_model_request_error"
            ],
            "real_recovery_requests": injected.real_recovery_requests,
        },
        "shared_slot_barrier": {
            "arrivals": injected.shared_slot_barrier_arrivals,
            "passes": injected.shared_slot_barrier_passes,
            "failures": injected.shared_slot_barrier_failures,
        },
        "search": {"calls": search.calls, "fetch_calls": search.fetch_calls},
    }
    validate_worker_projection(value)
    return value


def validate_worker_projection(value: Mapping[str, Any]) -> None:
    index = value.get("worker_index")
    budget = value.get("model_budget")
    recovery = value.get("recovery")
    barrier = value.get("shared_slot_barrier")
    search = value.get("search")
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 1 <= index <= TASK_COUNT
        or value.get("completion_kind")
        not in {"primary", "repaired", "best_effort_fallback"}
        or not isinstance(budget, Mapping)
        or not isinstance(recovery, Mapping)
        or not isinstance(barrier, Mapping)
        or search != {"calls": 0, "fetch_calls": 0}
    ):
        raise RuntimeError("V2.43.01 worker projection drifted")
    _finite(value.get("wall_seconds"), "worker wall seconds")
    admitted = budget.get("admitted")
    requests = budget.get("logical_provider_requests")
    acquisitions = budget.get("slot_acquisitions")
    counts = budget.get("slot_acquisition_counts")
    effects = recovery.get("effects_by_stage")
    if (
        budget.get("limit") != MODEL_CALLS_PER_TASK
        or isinstance(admitted, bool)
        or not isinstance(admitted, int)
        or not 0 <= admitted <= MODEL_CALLS_PER_TASK
        or requests != admitted
        or acquisitions != admitted
        or not isinstance(counts, list)
        or len(counts) != SLOT_CAP
        or any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts)
        or sum(counts) != acquisitions
        or budget.get("fourth_provider_effect") is not False
        or not isinstance(effects, Mapping)
        or set(effects) != {"plan", "synthesis_initial", "synthesis_recovery", "repair"}
        or sum(effects.values()) != admitted
        or recovery.get("total_effects_admitted") != admitted
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in effects.values()
        )
        or barrier.get("arrivals") not in (0, 1)
        or barrier.get("passes") not in (0, 1)
        or barrier.get("failures") not in (0, 1)
        or barrier.get("passes") + barrier.get("failures") > barrier.get("arrivals")
    ):
        raise RuntimeError("V2.43.01 worker effect accounting drifted")


def _aggregate(workers: Sequence[Mapping[str, Any]], *, barrier_broken: bool) -> dict[str, Any]:
    completions = Counter(str(worker["completion_kind"]) for worker in workers)
    stage_totals = {name: 0 for name in ("plan", "synthesis_initial", "synthesis_recovery", "repair")}
    slot_counts = [0] * SLOT_CAP
    for worker in workers:
        for name, count in worker["recovery"]["effects_by_stage"].items():
            stage_totals[name] += int(count)
        for index, count in enumerate(worker["model_budget"]["slot_acquisition_counts"]):
            slot_counts[index] += int(count)
    return {
        "task_count": len(workers),
        "completion_counts": dict(sorted(completions.items())),
        "primary_tasks": completions.get("primary", 0),
        "model_call_limit_per_task": MODEL_CALLS_PER_TASK,
        "total_effects_admitted": sum(int(worker["model_budget"]["admitted"]) for worker in workers),
        "logical_provider_requests": sum(int(worker["model_budget"]["logical_provider_requests"]) for worker in workers),
        "provider_attempts": sum(int(worker["model_budget"]["provider_attempts"]) for worker in workers),
        "real_recovery_requests": sum(int(worker["recovery"]["real_recovery_requests"]) for worker in workers),
        "effects_by_stage": stage_totals,
        "initial_synthesis_failures": sum(bool(worker["recovery"]["initial_synthesis_model_request_error"]) for worker in workers),
        "recovery_attempts": sum(bool(worker["recovery"]["recovery_attempted"]) for worker in workers),
        "recovery_successes": sum(bool(worker["recovery"]["recovery_succeeded"]) for worker in workers),
        "recovery_provider_failures": sum(bool(worker["recovery"]["recovery_model_request_error"]) for worker in workers),
        "slot_cap": SLOT_CAP,
        "slot_acquisitions": sum(int(worker["model_budget"]["slot_acquisitions"]) for worker in workers),
        "slot_acquisition_counts": slot_counts,
        "slot_wait_seconds": round(sum(float(worker["model_budget"]["slot_wait_seconds"]) for worker in workers), 6),
        "shared_slot_barrier_arrivals": sum(int(worker["shared_slot_barrier"]["arrivals"]) for worker in workers),
        "shared_slot_barrier_participants": sum(int(worker["shared_slot_barrier"]["passes"]) for worker in workers),
        "shared_slot_barrier_failures": sum(int(worker["shared_slot_barrier"]["failures"]) for worker in workers),
        "shared_slot_barrier_broken": bool(barrier_broken),
        "fourth_provider_effects": sum(bool(worker["model_budget"]["fourth_provider_effect"]) for worker in workers),
        "search_calls": sum(int(worker["search"]["calls"]) for worker in workers),
        "fetch_calls": sum(int(worker["search"]["fetch_calls"]) for worker in workers),
        "task_wall_sum_seconds": round(sum(float(worker["wall_seconds"]) for worker in workers), 6),
    }


def project(
    workers: Sequence[Mapping[str, Any]],
    *,
    wall_seconds: float,
    barrier_broken: bool,
    now: int | None = None,
) -> dict[str, Any]:
    ordered = [dict(worker) for worker in sorted(workers, key=lambda item: int(item["worker_index"]))]
    for worker in ordered:
        validate_worker_projection(worker)
    value = {
        "artifact_version": 1,
        "role": "v24301_neutral_concurrent_synthesis_recovery_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "eight_fault_injected_neutral_real_provider_recoveries_only",
        "provider": "azure-native-keyless-gpt-5.6-sol",
        "wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "observed": _aggregate(ordered, barrier_broken=barrier_broken),
        "workers": ordered,
        "source_policy": {
            "synthetic_neutral_tasks_used_but_not_persisted_or_hashed": True,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
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
    workers = value.get("workers")
    observed = value.get("observed")
    source = value.get("source_policy")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24301_neutral_concurrent_synthesis_recovery_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("scope")
        != "eight_fault_injected_neutral_real_provider_recoveries_only"
        or value.get("provider") != "azure-native-keyless-gpt-5.6-sol"
        or not _sealed(value, "result_payload_sha256")
        or not isinstance(workers, list)
        or len(workers) != TASK_COUNT
        or [worker.get("worker_index") for worker in workers]
        != list(range(1, TASK_COUNT + 1))
        or not isinstance(observed, Mapping)
        or not isinstance(source, Mapping)
        or source.get("synthetic_neutral_tasks_used_but_not_persisted_or_hashed")
        is not True
        or source.get("shared_api_lease_acquired") is not True
        or any(
            setting
            for key, setting in source.items()
            if key
            not in {
                "synthetic_neutral_tasks_used_but_not_persisted_or_hashed",
                "shared_api_lease_acquired",
            }
        )
        or not isinstance(auth, Mapping)
        or any(auth.values())
    ):
        raise RuntimeError("V2.43.01 projection drifted")
    _finite(value.get("wall_seconds"), "wall seconds")
    for worker in workers:
        validate_worker_projection(worker)
    expected = _aggregate(
        workers, barrier_broken=bool(observed.get("shared_slot_barrier_broken"))
    )
    if dict(observed) != expected:
        raise RuntimeError("V2.43.01 aggregate projection drifted")
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET.search(encoded) or any(literal in encoded for literal in CONTENT_LITERALS):
        raise RuntimeError("V2.43.01 result persisted prohibited content")


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preactivation_audit(root)
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.01 result surface is not pristine")
    output_root = root / "outputs"
    lease = protocol["lease"]
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        root,
        owner=str(lease["owner"]),
        purpose=str(lease["purpose"]),
        path=root / str(lease["path"]),
    ):
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            slots = Path(directory)
            for index in range(1, SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            barrier = threading.Barrier(TASK_COUNT)
            workers: list[dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=TASK_COUNT, thread_name_prefix="v24301-neutral"
            ) as executor:
                futures = {
                    executor.submit(
                        _worker,
                        index,
                        provider=protocol["provider"],
                        slot_directory=slots,
                        output_root=output_root,
                        barrier=barrier,
                    ): index
                    for index in range(1, TASK_COUNT + 1)
                }
                for future in concurrent.futures.as_completed(futures):
                    workers.append(future.result())
            barrier_broken = barrier.broken
    value = project(
        workers,
        wall_seconds=max(0.0, time.monotonic() - started),
        barrier_broken=barrier_broken,
    )
    publish(root / RESULT, value)
    return value


def _checks(result: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    observed = result["observed"]
    effects = observed["effects_by_stage"]
    workers = result["workers"]
    return {
        "wall_seconds": float(result["wall_seconds"]) <= gates["maximum_wall_seconds"],
        "task_count": observed["task_count"] == gates["required_task_count"],
        "primary_tasks": observed["primary_tasks"] == gates["required_primary_tasks"],
        "model_call_limit_per_task": all(
            worker["model_budget"]["limit"]
            == gates["required_model_call_limit_per_task"]
            for worker in workers
        ),
        "total_effects_admitted": observed["total_effects_admitted"]
        == gates["required_total_effects_admitted"],
        "logical_provider_requests": observed["logical_provider_requests"]
        == gates["required_logical_provider_requests"],
        "provider_attempts": observed["provider_attempts"]
        >= gates["minimum_provider_attempts"],
        "real_recovery_requests": observed["real_recovery_requests"]
        == gates["required_real_recovery_requests"],
        "plan_effects": effects["plan"] == gates["required_plan_effects"],
        "initial_synthesis_effects": effects["synthesis_initial"]
        == gates["required_initial_synthesis_effects"],
        "recovery_effects": effects["synthesis_recovery"]
        == gates["required_recovery_effects"],
        "repair_effects": effects["repair"] == gates["required_repair_effects"],
        "initial_synthesis_failures": observed["initial_synthesis_failures"]
        == gates["required_initial_synthesis_failures"],
        "recovery_attempts": observed["recovery_attempts"]
        == gates["required_recovery_attempts"],
        "recovery_successes": observed["recovery_successes"]
        == gates["required_recovery_successes"],
        "recovery_provider_failures": observed["recovery_provider_failures"]
        == gates["required_recovery_provider_failures"],
        "slot_cap": observed["slot_cap"] == gates["required_slot_cap"],
        "slot_acquisitions": observed["slot_acquisitions"]
        == gates["required_slot_acquisitions"],
        "shared_slot_barrier_participants": observed[
            "shared_slot_barrier_participants"
        ]
        == gates["required_shared_slot_barrier_participants"],
        "shared_slot_barrier_failures": observed["shared_slot_barrier_failures"]
        == gates["required_shared_slot_barrier_failures"],
        "shared_slot_barrier_not_broken": observed["shared_slot_barrier_broken"]
        is False,
        "fourth_provider_effects": observed["fourth_provider_effects"]
        == gates["required_fourth_provider_effects"],
        "search_calls": observed["search_calls"] == gates["required_search_calls"],
        "fetch_calls": observed["fetch_calls"] == gates["required_fetch_calls"],
    }


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preactivation_audit(root)
    result = _read(root, RESULT)
    validate_projection(result)
    checks = _checks(result, protocol["gates"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    value = {
        "artifact_version": 1,
        "role": "v24301_neutral_concurrent_synthesis_recovery_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_concurrency_go" if passed else "neutral_concurrency_no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {
            "wall_seconds": result["wall_seconds"],
            **dict(result["observed"]),
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "result_sha256": sha256(root / RESULT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "eight_way_fault_injected_real_provider_recovery_robustness": True,
            "natural_failure_frequency_measured": False,
            "benchmark_quality_measured": False,
            "causal_quality_improvement_proven": False,
            "sota_supported": False,
        },
        "authorization": {
            "successor_fresh_paired_dev64_design": passed,
            "successor_fresh_paired_dev64_launch": False,
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
        value.get("role") != "v24301_neutral_concurrent_synthesis_recovery_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "decision_payload_sha256")
        or not isinstance(checks, Mapping)
        or not isinstance(failed, list)
        or value.get("passed") is not all(checks.values())
        or failed != sorted(name for name, passed in checks.items() if not passed)
        or value.get("status")
        != ("neutral_concurrency_go" if value["passed"] else "neutral_concurrency_no_go")
        or not isinstance(claim, Mapping)
        or claim.get("eight_way_fault_injected_real_provider_recovery_robustness")
        is not True
        or any(
            setting
            for key, setting in claim.items()
            if key != "eight_way_fault_injected_real_provider_recovery_robustness"
        )
        or not isinstance(auth, Mapping)
        or auth.get("successor_fresh_paired_dev64_design") is not value["passed"]
        or any(
            setting
            for key, setting in auth.items()
            if key != "successor_fresh_paired_dev64_design"
        )
    ):
        raise RuntimeError("V2.43.01 decision drifted")


def build_postresult_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preactivation_audit(root)
    result = _read(root, RESULT)
    decision = _read(root, DECISION)
    validate_projection(result)
    validate_decision(decision)
    findings: list[str] = []
    encoded = json.dumps({"result": result, "decision": decision}, ensure_ascii=False)
    if SECRET.search(encoded):
        findings.append("credential_literal_persisted")
    if any(literal in encoded for literal in CONTENT_LITERALS):
        findings.append("task_content_or_identifier_persisted")
    if decision.get("provenance", {}).get("result_sha256") != sha256(root / RESULT):
        findings.append("decision_result_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24301_neutral_concurrent_synthesis_recovery_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "execution_closure": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_prompt_response_prediction_answer_or_hash_persisted": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "invalid_result_path": None,
        },
        "authorization": {
            "successor_fresh_paired_dev64_design": bool(decision["passed"] and not findings),
            "successor_fresh_paired_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postresult_audit(value)
    return value


def validate_postresult_audit(value: Mapping[str, Any]) -> None:
    auth = value.get("authorization")
    if (
        value.get("role")
        != "v24301_neutral_concurrent_synthesis_recovery_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "audit_payload_sha256")
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("execution_closure", {}).get("invalid_result_path") is not None
        or not isinstance(auth, Mapping)
        or auth.get("successor_fresh_paired_dev64_design") is not True
        or any(
            setting
            for key, setting in auth.items()
            if key != "successor_fresh_paired_dev64_design"
        )
    ):
        raise RuntimeError("V2.43.01 postresult audit drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("preregister", "preaudit", "probe", "finalize", "postaudit")
    )
    args = parser.parse_args()
    if args.action == "preregister":
        value, path = build_protocol(), PROTOCOL
    elif args.action == "preaudit":
        value, path = build_preactivation_audit(), PREAUDIT
    elif args.action == "probe":
        value = run_probe()
        print(
            json.dumps(
                {
                    "path": str(RESULT),
                    "wall_seconds": value["wall_seconds"],
                    "primary_tasks": value["observed"]["primary_tasks"],
                },
                sort_keys=True,
            )
        )
        return
    elif args.action == "finalize":
        value, path = build_decision(), DECISION
    else:
        value, path = build_postresult_audit(), POSTAUDIT
    publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
