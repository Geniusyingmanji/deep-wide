#!/usr/bin/env python3
"""Fresh one-wave external gate for proof-carrying targeted support.

The eight public-document questions and 64 entities are literal/canonical
disjoint from all 308 questions and 2,464 entities consumed by prior external
gates.  Runtime input is exactly ``opaque_id`` and ``question``.  This module
contains protocol, audit, activation and runner surfaces, but protocol
publication alone authorizes no network or benchmark effect.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24397_failure_observability import (  # noqa: E402
    aggregate_observations,
    validate_observation_aggregate,
)
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
)
from deepwide_agent.v24461_proof_carrying_adaptive_timed_runner import (  # noqa: E402
    aggregate_stage_timings,
    validate_stage_timing_aggregate,
)
from deepwide_agent.v24470_bounded_adaptive_integration import (  # noqa: E402
    aggregate_supervision_receipts,
    build_hard_total_wall_model,
    validate_supervision_aggregate,
)
from deepwide_agent.v24476_bounded_nominal_search_integration import (  # noqa: E402
    build_bounded_nominal_hard_total_wall_search,
)
from deepwide_agent import v24480_separated_effect_validation_budget as phase_budget  # noqa: E402
from deepwide_agent import v24482_separated_budget_worker_integration as worker_budget  # noqa: E402
from deepwide_agent.v24491_proof_carrying_targeted_support import (  # noqa: E402
    POLICY_ID as TARGETED_PROOF_POLICY_ID,
    aggregate_projections,
    validate_aggregate as validate_targeted_aggregate,
)
from deepwide_agent.v24492_targeted_timed_parent import (  # noqa: E402
    POLICY_ID as TARGETED_PARENT_POLICY_ID,
    run_targeted_parent_with_separated_budget,
    run_targeted_worker,
    supervise_targeted_worker_with_separated_budget,
)
from scripts import audit_v24491_proof_carrying_targeted_build as build_audit  # noqa: E402
from scripts import v24488_memoized_external_gate as history  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24492_fresh_targeted_support_external_gate_v1"
PROTOCOL = Path(f"results/v24492_targeted_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24492_targeted_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24492_targeted_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24492_targeted_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24492_targeted_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24492_targeted_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24492_targeted_external_postresult_audit_v1_{DATE}.json")
PARENT = Path("results/v24491_proof_carrying_targeted_build_audit_v1_20260804.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_targeted_support_external_gate"
RUNNER_MARKER = "scripts/v24492_targeted_external_gate.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
SELECTED = 8
EXECUTOR_COUNT = 8
MODEL_SLOT_CAP = 2
EFFECT_DEADLINE_SECONDS = phase_budget.REMOTE_EFFECT_SECONDS
WORKER_TIMEOUT_SECONDS = phase_budget.WORKER_TOTAL_SECONDS
PARENT_TIMEOUT_SECONDS = phase_budget.PARENT_TOTAL_SECONDS
BATCH_WALL_CEILING_SECONDS = phase_budget.BATCH_WALL_CEILING_SECONDS
PARENT_VALIDATION_P95_CEILING_SECONDS = 1.0
LIMITS = ScoreFirstLimits(
    wall_seconds=EFFECT_DEADLINE_SECONDS,
    model_calls=3,
    search_queries=4,
    fetch_targets=10,
    search_results_per_query=3,
    evidence_chars=60_000,
    page_chars=5_000,
    plan_output_tokens=4_000,
    synthesis_output_tokens=30_000,
    repair_output_tokens=12_000,
)
GATES = {
    "minimum_worker_success_tasks": SELECTED,
    "maximum_worker_hard_timeout_tasks": 0,
    "maximum_worker_nonzero_tasks": 0,
    "minimum_complete_validation_returned_tasks": SELECTED,
    "minimum_target_plan_tasks": 1,
    "minimum_safe_change_improvement_tasks": 1,
    "minimum_positive_decision_credit_tasks": 1,
    "minimum_total_decision_credit_nats": 1e-12,
    "maximum_additional_model_acquisitions": 0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 3,
    "maximum_fetch_helper_failures": 3,
    "maximum_parent_validation_p95_seconds": PARENT_VALIDATION_P95_CEILING_SECONDS,
}
ENTITY_GROUPS = (
    (
        "Malmö University", "Södertörn University", "University West",
        "Kristianstad University", "Mälardalen University", "University of Skövde",
        "Dalarna University", "University of Gävle",
    ),
    (
        "LUT University", "University of Vaasa", "University of Lapland",
        "Åbo Akademi University", "Hanken School of Economics",
        "University of the Arts Helsinki", "National Defence University Finland",
        "Police University College Finland",
    ),
    (
        "Tallinn University", "Tallinn University of Technology",
        "Estonian University of Life Sciences", "Riga Technical University",
        "Rīga Stradiņš University", "Latvia University of Life Sciences and Technologies",
        "Vilnius Gediminas Technical University", "Vytautas Magnus University",
    ),
    (
        "University of Mostar", "University of East Sarajevo",
        "International Burch University", "Sarajevo School of Science and Technology",
        "Mediterranean University Montenegro", "University of Donja Gorica",
        "University for Business and Technology Kosovo", "RIT Kosovo",
    ),
    (
        "Nazarbayev University", "Astana IT University", "KIMEP University",
        "Al-Farabi Kazakh National University", "Satbayev University",
        "L. N. Gumilyov Eurasian National University", "Ala-Too International University",
        "Kyrgyz State Technical University",
    ),
    (
        "University of the West Indies", "University of the Commonwealth Caribbean",
        "Caribbean Maritime University", "Mico University College",
        "College of Science Technology and Applied Arts of Trinidad and Tobago",
        "University College of the Cayman Islands", "Bermuda College",
        "University of Saint Martin",
    ),
    (
        "University of Technology and Applied Sciences Oman", "Muscat University",
        "Majan University College", "Modern College of Business and Science",
        "Middle East College Oman", "Scientific College of Design",
        "Sur University College", "Mazoon College",
    ),
    (
        "Capilano University", "Kwantlen Polytechnic University",
        "Vancouver Island University", "Thompson Rivers University",
        "Royal Roads University", "Mount Royal University", "MacEwan University",
        "University of the Fraser Valley",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.44.92 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
SOURCE_FILES = (
    "src/deepwide_agent/v24490_entropy_targeted_support_search.py",
    "src/deepwide_agent/v24491_proof_carrying_targeted_support.py",
    "src/deepwide_agent/v24492_targeted_timed_parent.py",
    "tests/test_v24490_entropy_targeted_support_search.py",
    "tests/test_v24491_proof_carrying_targeted_support.py",
    "tests/test_v24492_targeted_timed_parent.py",
    "scripts/audit_v24491_proof_carrying_targeted_build.py",
    str(PARENT),
    RUNNER_MARKER,
    "tests/test_v24492_targeted_external_gate.py",
)
TEST_SUITES = (
    ("tests/test_v24491_proof_carrying_targeted_support.py", 10, 180),
    ("tests/test_v24492_targeted_timed_parent.py", 3, 120),
    ("tests/test_v24492_targeted_external_gate.py", 8, 120),
)
EXPECTED_TEST_COUNT = 21
SECRET = history.SECRET
OPAQUE = history.OPAQUE
URL = history.URL
EXPECTED_WATCHERS = build_audit.EXPECTED_WATCHERS


def _expected_watchers() -> list[dict[str, Any]]:
    return [
        {"pid": pid, "marker": marker, "start_ticks": ticks}
        for pid, ticks, marker in EXPECTED_WATCHERS
    ]


def _ordinary(root: Path, relative: str | Path) -> Path:
    rel = Path(relative)
    path = root / rel
    if (
        rel.is_absolute()
        or ".." in rel.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.44.92 nonordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.92 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    history._write_new(path, value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    history.publish(path, value)


def _future(root: Path, paths: Sequence[Path]) -> bool:
    return history._future(root, paths)


def _git(root: Path, *args: str) -> str:
    return history._git(root, *args)


def _port_listening() -> bool:
    return history._port_listening()


def _prior_questions() -> tuple[str, ...]:
    return history._prior_questions() + history.QUESTIONS


def _fresh_entity_vector_valid() -> bool:
    parser = history.history.previous_gate.history.history.history.parent
    current = {
        entity for question in QUESTIONS for entity in parser._question_entity_vector(question)
    }
    prior_questions = _prior_questions()
    prior = {
        entity
        for question in prior_questions
        for entity in parser._question_entity_vector(question)
    }
    return (
        len(current) == 64
        and len({parser._canonical_entity(entity) for entity in current}) == 64
        and len(prior_questions) == 308
        and len(prior) == 2464
        and len({parser._canonical_entity(entity) for entity in prior}) == 2464
        and current.isdisjoint(prior)
        and {parser._canonical_entity(entity) for entity in current}.isdisjoint(
            {parser._canonical_entity(entity) for entity in prior}
        )
    )


def neutral_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED:
        raise ValueError("V2.44.92 neutral ordinal is invalid")
    return validate_visible_task(
        {
            "opaque_id": "task_"
            + hashlib.sha256(
                f"{PROTOCOL_ID}|fresh-task|{ordinal}".encode()
            ).hexdigest()[:24],
            "question": QUESTIONS[ordinal - 1],
        }
    )


def partition_seed(ordinal: int) -> str:
    neutral_task(ordinal)
    return hashlib.sha256(
        f"{PROTOCOL_ID}|targeted-entropy|{ordinal}".encode()
    ).hexdigest()


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.44.92 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    if (
        value.get("role") != "v24491_proof_carrying_targeted_build_audit"
        or value.get("findings") != []
        or value.get("authorization", {}).get("v24491_build_go") is not True
        or value.get("authorization", {}).get("new_external_gate_design") is not True
        or value.get("authorization", {}).get("new_external_gate_launch") is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.92 build parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": SELECTED,
        "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_308_prior_external_questions": _fresh_entity_vector_valid(),
        "prior_external_question_count": 308,
        "prior_external_entity_count": 2464,
        "all_prior_external_populations_rerun": False,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_targeted_external_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    LIMITS.validate()
    if not _fresh_entity_vector_valid():
        raise RuntimeError("V2.44.92 external entity vector overlaps history")
    if require_pristine and not _future(
        root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.44.92 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24492_targeted_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "scope": "fresh_nonbenchmark_targeted_entropy_decision_credit_gate",
        "task_contract": _task_contract(),
        "mechanism": {
            "targeted_proof_policy": TARGETED_PROOF_POLICY_ID,
            "targeted_parent_policy": TARGETED_PARENT_POLICY_ID,
            "one_complete_targeted_validation_per_successful_child": True,
            "parent_recursive_historical_replay": False,
            "targeted_queries_use_only_frozen_row_column_and_leading_alternative": True,
            "targeted_sources_disjoint_from_proposal_active_and_adaptive_sources": True,
            "targeted_pages_enter_model_prompt": False,
            "source_count_posterior_margin_and_credit_rules_relaxed": False,
            "memo_receipt_bound_into_exact_byte_certificate": True,
        },
        "provider": {
            "proxy_url": f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "max_retries_per_batch": 2,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
            "maximum_provider_effect_seconds": MAXIMUM_PROVIDER_EFFECT_SECONDS,
        },
        "budget": {
            "effect_deadline_seconds": EFFECT_DEADLINE_SECONDS,
            "worker_timeout_seconds": WORKER_TIMEOUT_SECONDS,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "maximum_batch_wall_seconds": BATCH_WALL_CEILING_SECONDS,
            "one_wave": True,
            "maximum_targeted_search_batches_per_task": 1,
            "maximum_targeted_logical_queries_per_task": 2,
            "maximum_targeted_fetches_per_task": 3,
            "single_batch_no_resume_retry_skip_or_selective_rerun": True,
        },
        "gates": dict(GATES),
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_text_identifier_query_url_page_prediction_response_candidate_value_or_private_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": _protocol_authorization(),
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value=value)


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    copied = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = copied.get("surface_manifest")
    task = copied.get("task_contract")
    mechanism = copied.get("mechanism")
    budget = copied.get("budget")
    source = copied.get("source_policy")
    if (
        copied.get("role") != "v24492_targeted_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope") != "fresh_nonbenchmark_targeted_entropy_decision_credit_gate"
        or copied.get("parent") != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or not isinstance(task, Mapping)
        or task != _task_contract()
        or not isinstance(mechanism, Mapping)
        or mechanism.get("targeted_proof_policy") != TARGETED_PROOF_POLICY_ID
        or mechanism.get("targeted_parent_policy") != TARGETED_PARENT_POLICY_ID
        or mechanism.get("one_complete_targeted_validation_per_successful_child") is not True
        or mechanism.get("parent_recursive_historical_replay") is not False
        or mechanism.get("targeted_pages_enter_model_prompt") is not False
        or mechanism.get("source_count_posterior_margin_and_credit_rules_relaxed") is not False
        or not isinstance(budget, Mapping)
        or budget.get("effect_deadline_seconds") != 150.0
        or budget.get("worker_timeout_seconds") != 220.0
        or budget.get("parent_timeout_seconds") != 245.0
        or budget.get("maximum_targeted_search_batches_per_task") != 1
        or budget.get("maximum_targeted_logical_queries_per_task") != 2
        or budget.get("maximum_targeted_fetches_per_task") != 3
        or copied.get("gates") != GATES
        or not isinstance(manifest, Mapping)
        or copied.get("surface_manifest_sha256") != payload_sha256(manifest)
        or dict(manifest) != _manifest(root)
        or not isinstance(source, Mapping)
        or any(source.get(name) is not False for name in source)
        or copied.get("authorization") != _protocol_authorization()
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.44.92 protocol drifted")
    return copied


def _run_tests() -> dict[str, Any]:
    suites = []
    for relative, count, timeout_seconds in TEST_SUITES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-q"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
        )
        suites.append({"path": relative, "test_count": count, "passed": completed.returncode == 0})
    return {
        "suites": suites,
        "test_count": sum(item["test_count"] for item in suites),
        "passed": all(item["passed"] for item in suites)
        and sum(item["test_count"] for item in suites) == EXPECTED_TEST_COUNT,
        "network_model_search_fetch_or_evaluator_called": False,
    }


def _all_sources_tracked(root: Path) -> bool:
    return all(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        ).returncode == 0
        for relative in SOURCE_FILES
    )


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_targeted_external_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    tests = _run_tests()
    accesses, imports = build_audit.ast_findings(Path(RUNNER_MARKER))
    lease = lease_observation(root, Path("/proc"))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    tracked = _all_sources_tracked(root)
    watchers = protected_watcher_snapshot()
    pristine = _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT))
    findings = []
    if not tests["passed"]:
        findings.append("focused_tests_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_runtime")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if head != remote:
        findings.append("protocol_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if not tracked:
        findings.append("protocol_source_not_tracked")
    if watchers != _expected_watchers():
        findings.append("protected_watcher_identity_drifted")
    if not pristine:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24492_targeted_external_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "fresh_64_entity_vector_frozen": True,
            "prior_external_questions_and_entities_exactly_308_and_2464": True,
            "one_wave_capacity_frozen": SELECTED == EXECUTOR_COUNT == 8,
            "phase_deadlines_exactly_150_220_245": True,
            "focused_tests": tests,
            "keyless_proxy_listening_without_api_request": _port_listening(),
            "shared_api_lease_inactive": lease.get("active") is False,
            "protocol_commit_pushed": head == remote,
            "worktree_clean": clean,
            "all_protocol_sources_tracked": tracked,
            "future_surface_pristine": pristine,
            "protected_watchers_unchanged": not any(
                finding == "protected_watcher_identity_drifted" for finding in findings
            ),
            "benchmark_or_evaluator_surface_authorized": False,
        },
        "protected_watchers": watchers,
        "privileged_field_accesses": accesses,
        "evaluator_imports": imports,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "parent_sha256": sha256(root / PARENT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
            "head": head,
            "target_main": remote,
        },
        "authorization": _activation_authorization(),
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.44.92 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    checks = value.get("checks")
    provenance = value.get("provenance")
    if (
        value.get("role") != "v24492_targeted_external_preactivation_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or not isinstance(checks, Mapping)
        or any(checks.get(name) is not True for name in (
            "protocol_valid_and_sealed", "fresh_64_entity_vector_frozen",
            "prior_external_questions_and_entities_exactly_308_and_2464",
            "one_wave_capacity_frozen", "phase_deadlines_exactly_150_220_245",
            "keyless_proxy_listening_without_api_request", "shared_api_lease_inactive",
            "protocol_commit_pushed", "worktree_clean", "all_protocol_sources_tracked",
            "future_surface_pristine", "protected_watchers_unchanged",
        ))
        or not isinstance(checks.get("focused_tests"), Mapping)
        or checks["focused_tests"].get("passed") is not True
        or checks.get("benchmark_or_evaluator_surface_authorized") is not False
        or value.get("privileged_field_accesses") != []
        or value.get("evaluator_imports") != []
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or not isinstance(provenance, Mapping)
        or provenance.get("protocol_sha256") != sha256(root / PROTOCOL)
        or provenance.get("surface_manifest_sha256") != validate_protocol(root)["surface_manifest_sha256"]
        or provenance.get("head") != provenance.get("target_main")
        or value.get("authorization") != _activation_authorization()
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.92 preaudit drifted")
    return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    audit = validate_preaudit(root)
    findings = []
    if not _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        findings.append("activation_or_execution_surface_not_pristine")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24492_targeted_external_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "selected": SELECTED,
        "executor_count": EXECUTOR_COUNT,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {**_activation_authorization(), "one_fresh_targeted_external_probe_launch": not findings},
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.44.92 activation failed")
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, ACTIVATION)
    if (
        value.get("role") != "v24492_targeted_external_activation"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("surface_manifest_sha256") != validate_protocol(root)["surface_manifest_sha256"]
        or value.get("selected") != SELECTED
        or value.get("executor_count") != EXECUTOR_COUNT
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("authorization") != _activation_authorization()
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.44.92 activation drifted")
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.44.92 execution surface is not pristine")
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    findings = []
    if head != remote:
        findings.append("activation_commit_not_pushed")
    if _git(root, "status", "--porcelain") != "":
        findings.append("worktree_not_clean")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24492_targeted_external_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "ready" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected": SELECTED,
        "executor_count": EXECUTOR_COUNT,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": activation["protected_watchers"],
        "api_called_before_execution_start": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_or_evaluator_authorized": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.44.92 execution start failed: " + ",".join(findings))
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    value = _read(root.resolve(), EXECUTION_START)
    if (
        value.get("role") != "v24492_targeted_external_execution_start"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("activation_base_commit") != value.get("target_main_at_start")
        or value.get("selected") != SELECTED
        or value.get("executor_count") != EXECUTOR_COUNT
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("api_called_before_execution_start") is not False
        or value.get("runtime_input_exactly_opaque_id_and_question") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_or_evaluator_authorized") is not False
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.44.92 execution start drifted")
    return value


def _worker(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal)
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    slots = Path(args.slots)
    manifest = validate_protocol(ROOT)["surface_manifest_sha256"]
    effect_deadline = worker_budget.remote_effect_deadline(args.deadline_origin_monotonic)

    def model_factory(callback):
        return build_hard_total_wall_model(
            url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            model_name="gpt-5.6-sol", reasoning_effort="low", service_tier="priority",
            static_timeout_seconds=MAXIMUM_PROVIDER_EFFECT_SECONDS, max_retries=2,
            slot_directory=slots, output_root=output_root, slot_cap=MODEL_SLOT_CAP,
            absolute_deadline=effect_deadline, cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05, stage_callback=callback,
        )

    def search_factory(callback):
        return build_bounded_nominal_hard_total_wall_search(
            url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            model_name="gpt-5.6-sol", reasoning_effort="low", service_tier="priority",
            static_timeout_seconds=MAXIMUM_PROVIDER_EFFECT_SECONDS, max_retries=2,
            absolute_deadline=effect_deadline, cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05, stage_callback=callback, max_workers=1,
            batch_size=8, search_context_size="medium", max_output_tokens=4_000,
            fetch_pages=False, fetch_workers=8, fetch_timeout=20,
            max_page_chars=LIMITS.page_chars, hard_fetch_deadline_seconds=25,
        )

    run_targeted_worker(
        neutral_task(ordinal), ordinal=ordinal,
        expected_supervisor_pid=int(os.environ["DEEPWIDE_EXPECTED_SUPERVISOR_PID"]),
        checkpoint_directory=checkpoint, output_root=output_root, directory=directory,
        model_factory=model_factory, search_factory=search_factory,
        partition_seed_sha256=partition_seed(ordinal), limits=LIMITS,
        monotonic=time.monotonic, expected_model_cap=MODEL_SLOT_CAP,
        writer=lambda name, value: _write_new(directory / name, value),
        validator_manifest_sha256=manifest,
    )


def _supervisor(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal)
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    command = [
        str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / RUNNER_MARKER),
        "worker", "--ordinal", str(ordinal), "--output-root", str(output_root),
        "--directory", str(directory), "--checkpoint-directory", str(checkpoint),
        "--slots", str(args.slots),
    ]
    supervise_targeted_worker_with_separated_budget(
        ordinal=ordinal, cwd=ROOT, output_root=output_root, directory=directory,
        checkpoint_directory=checkpoint, worker_command=command,
        deadline_origin=args.deadline_origin_monotonic,
        expected_model_cap=MODEL_SLOT_CAP,
        writer=lambda name, value: _write_new(directory / name, value),
    )


def _run_one(
    root: Path, output_root: Path, slots: Path, directory: Path,
    checkpoint: Path, ordinal: int,
) -> dict[str, Any]:
    protocol = validate_protocol(root)
    outcome = run_targeted_parent_with_separated_budget(
        ordinal=ordinal, cwd=root, output_root=output_root, directory=directory,
        checkpoint_directory=checkpoint,
        supervisor_command=[
            str(root / ".venv-eval/bin/python"), "-I", "-B", str(root / RUNNER_MARKER),
            "supervisor", "--ordinal", str(ordinal), "--output-root", str(output_root),
            "--directory", str(directory), "--checkpoint-directory", str(checkpoint),
            "--slots", str(slots),
        ],
        expected_model_cap=MODEL_SLOT_CAP,
        expected_validator_manifest_sha256=protocol["surface_manifest_sha256"],
    )
    return {
        "mechanism": outcome.proof.adaptive_projection,
        "observation": outcome.proof.observation,
        "timing": outcome.proof.timing_receipt,
        "supervision": outcome.supervision_receipt,
    }


def _mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        value.get("passed_tasks") == SELECTED
        and value.get("target_plan_tasks", 0) >= GATES["minimum_target_plan_tasks"]
        and value.get("safe_change_improvement_tasks", 0)
        >= GATES["minimum_safe_change_improvement_tasks"]
        and value.get("positive_decision_credit_tasks", 0)
        >= GATES["minimum_positive_decision_credit_tasks"]
        and float(value.get("total_decision_credit_nats", 0.0))
        >= GATES["minimum_total_decision_credit_nats"]
        and value.get("total_additional_model_acquisitions")
        <= GATES["maximum_additional_model_acquisitions"]
        and value.get("all_effects_conserved") is True
        and value.get("all_memos_fail_closed") is True
        and value.get("all_single_validations_attested") is True
    )


def _reliability_passed(observation: Mapping[str, Any], supervision: Mapping[str, Any]) -> bool:
    return (
        supervision.get("worker_success_tasks") == SELECTED
        and supervision.get("worker_hard_timeout_tasks") == 0
        and supervision.get("worker_nonzero_tasks") == 0
        and supervision.get("complete_validation_returned_tasks") == SELECTED
        and observation.get("slot_timeouts_lower_bound") == 0
        and observation.get("provider_deadline_failures_lower_bound") == 0
        and observation.get("hosted_search_deadline_failures_lower_bound") == 0
        and observation.get("hard_fetch_deadline_failures_lower_bound", 0) <= 3
        and observation.get("fetch_helper_failures_lower_bound", 0) <= 3
    )


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    mechanism = validate_targeted_aggregate(copied.get("mechanism_aggregate", {}))
    observation = validate_observation_aggregate(
        copied.get("observation_aggregate", {}), expected_selected=SELECTED
    )
    timing = validate_stage_timing_aggregate(copied.get("stage_timing_aggregate", {}))
    supervision = validate_supervision_aggregate(copied.get("supervision_aggregate", {}))
    mechanism_go = _mechanism_passed(mechanism)
    reliability = _reliability_passed(observation, supervision)
    parent_validation = (
        timing.get("parent_success_tasks") == SELECTED
        and timing.get("certificate_validation_invocations") == SELECTED
        and timing.get("recursive_historical_semantic_replay_tasks") == 0
        and float(timing.get("parent_certificate_validation_wall_p95_seconds", math.inf))
        <= PARENT_VALIDATION_P95_CEILING_SECONDS
    )
    batch = copied.get("batch_wall_seconds")
    latency = (
        isinstance(batch, (int, float)) and not isinstance(batch, bool)
        and math.isfinite(float(batch)) and 0 <= float(batch) <= BATCH_WALL_CEILING_SECONDS
        and float(supervision.get("worker_wall_max_seconds", math.inf)) <= WORKER_TIMEOUT_SECONDS + 1
    )
    encoded = json.dumps(copied, ensure_ascii=False)
    if (
        copied.get("role") != "v24492_targeted_external_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("selected") != SELECTED
        or copied.get("executor_count") != EXECUTOR_COUNT
        or copied.get("model_slot_cap") != MODEL_SLOT_CAP
        or copied.get("one_wave") is not True
        or copied.get("mechanism_passed") is not mechanism_go
        or copied.get("reliability_passed") is not reliability
        or copied.get("parent_validation_passed") is not parent_validation
        or copied.get("latency_passed") is not latency
        or copied.get("passed") is not (mechanism_go and reliability and parent_validation and latency)
        or copied.get("temporary_execution_directory_remaining") is not False
        or copied.get("private_task_or_web_content_persisted") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or copied.get("official_evaluator_called") is not False
        or copied.get("resume_retry_skip_or_revaluation") is not False
        or not _sealed(copied, "result_payload_sha256")
        or OPAQUE.search(encoded) or URL.search(encoded) or SECRET.search(encoded)
    ):
        raise RuntimeError("V2.44.92 public result drifted or contains content")
    return copied


def _git_ready(root: Path) -> bool:
    return (
        _git(root, "rev-parse", "HEAD") == _git(root, "rev-parse", "target/main")
        and _git(root, "status", "--porcelain") == ""
        and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(EXECUTION_START)], cwd=root,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            check=False,
        ).returncode == 0
    )


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    if not _future(root, (RESULT, DECISION, POSTAUDIT)) or not _git_ready(root):
        raise RuntimeError("V2.44.92 result/git surface is not ready")
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            work = []
            for ordinal in range(1, SELECTED + 1):
                directory = output_root / f"task_{ordinal:02d}"
                checkpoint = output_root / f"checkpoint_{ordinal:02d}"
                directory.mkdir(); checkpoint.mkdir()
                work.append((ordinal, directory, checkpoint))
            started = time.monotonic()
            with concurrent.futures.ThreadPoolExecutor(max_workers=EXECUTOR_COUNT) as pool:
                outcomes = list(pool.map(
                    lambda item: _run_one(root, output_root, slots, item[1], item[2], item[0]),
                    work,
                ))
            batch_wall = max(0.0, time.monotonic() - started)
            mechanism = aggregate_projections(
                [item["mechanism"] for item in outcomes], selected=SELECTED
            )
            observation = aggregate_observations(
                [item["observation"] for item in outcomes], selected=SELECTED
            )
            timing = aggregate_stage_timings(
                [item["timing"] for item in outcomes], selected=SELECTED
            )
            supervision = aggregate_supervision_receipts(
                [item["supervision"] for item in outcomes], selected=SELECTED
            )
        mechanism_go = _mechanism_passed(mechanism)
        reliability = _reliability_passed(observation, supervision)
        parent_validation = (
            timing["parent_success_tasks"] == SELECTED
            and timing["certificate_validation_invocations"] == SELECTED
            and timing["recursive_historical_semantic_replay_tasks"] == 0
            and timing["parent_certificate_validation_wall_p95_seconds"] <= 1.0
        )
        latency = batch_wall <= BATCH_WALL_CEILING_SECONDS and supervision["worker_wall_max_seconds"] <= WORKER_TIMEOUT_SECONDS + 1
        value = {
            "artifact_version": 1,
            "role": "v24492_targeted_external_result",
            "protocol_id": PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": SELECTED,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
            "one_wave": True,
            "batch_wall_seconds": round(batch_wall, 6),
            "mechanism_aggregate": mechanism,
            "observation_aggregate": observation,
            "stage_timing_aggregate": timing,
            "supervision_aggregate": supervision,
            "mechanism_passed": mechanism_go,
            "reliability_passed": reliability,
            "parent_validation_passed": parent_validation,
            "latency_passed": latency,
            "passed": mechanism_go and reliability and parent_validation and latency,
            "temporary_execution_directory_remaining": False,
            "private_task_or_web_content_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "provenance": {
                "protocol_sha256": sha256(root / PROTOCOL),
                "preactivation_audit_sha256": sha256(root / PREAUDIT),
                "activation_sha256": sha256(root / ACTIVATION),
                "execution_start_sha256": sha256(root / EXECUTION_START),
                "surface_manifest_sha256": protocol["surface_manifest_sha256"],
            },
        }
        value["result_payload_sha256"] = payload_sha256(value)
        validate_public_result(value)
        publish(root / RESULT, value)
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        raise RuntimeError("V2.44.92 protected watcher identity drifted")
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = validate_public_result(_read(root, RESULT))
    passed = result["passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v24492_targeted_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "fresh_targeted_external_go" if passed else "fresh_targeted_external_no_go",
        "passed": passed,
        "result_sha256": sha256(root / RESULT),
        "claim_scope": {
            "fresh_nonbenchmark_targeted_mechanism_measured": True,
            "benchmark_quality_measured": False,
            "sota_supported": False,
        },
        "authorization": {
            "diagnostic_successor_design": not passed,
            "fresh_paired_dev64_design": passed,
            "fresh_paired_dev64_launch": False,
            "new_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return value


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    decision = build_decision(root, now=now) if not (root / DECISION).exists() else _read(root, DECISION)
    lease_active = lease_observation(root, Path("/proc")).get("active") is not False
    watchers = protected_watcher_snapshot()
    expected = _read(root, EXECUTION_START)["protected_watchers"]
    findings = []
    if lease_active: findings.append("shared_api_lease_active")
    if watchers != expected: findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24492_targeted_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision["status"],
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "private_task_or_web_content_persisted": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=(
        "protocol", "preaudit", "activation", "start", "run", "finalize",
        "supervisor", "worker",
    ))
    parser.add_argument("--ordinal")
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--checkpoint-directory")
    parser.add_argument("--slots")
    parser.add_argument(worker_budget.DEADLINE_ORIGIN_ARGUMENT)
    args = parser.parse_args()
    if args.command == "protocol": publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit": publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation": publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start": publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run": run_probe()
    elif args.command == "finalize":
        publish(ROOT / DECISION, build_decision())
        publish(ROOT / POSTAUDIT, build_postaudit())
    elif args.command == "worker": _worker(args)
    else: _supervisor(args)


if __name__ == "__main__":
    main()
