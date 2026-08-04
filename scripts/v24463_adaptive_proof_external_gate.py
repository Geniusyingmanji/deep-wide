#!/usr/bin/env python3
"""Fresh label-blind external gate for proof-carrying adaptive support.

Sixteen fixed public-document tasks use 128 entities that are literally and
canonically disjoint from all 2,016 entities in the sixteen preceding
external populations.  Runtime input is exactly ``opaque_id`` and
``question``.  V2.44.57 may fetch at most three already-discovered,
source-disjoint leads and may not add a model request, logical query, search
batch, or hosted search request.

The child performs the complete adaptive semantic validation before writing
the V2.44.59 certificate and terminal receipt.  The parent validates exact
files and compact receipts, projects only through the V2.44.59 capability,
retains partial-effect lower bounds on failure, and records zero recursive
historical replay.  Private execution directories are deleted before the
public result is published.

This is benchmark-external.  It never opens benchmark manifests, mappings,
gold answers, labels, evaluator state, rewards, or scores.  A GO can authorize
only design of a fresh paired dev64, never its launch or an exact220 run.
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
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    UncertaintyDeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24397_failure_observability import (  # noqa: E402
    aggregate_observations,
    validate_observation_aggregate,
)
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    RESULT_NAME as CHILD_RESULT_NAME,
)
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
)
from deepwide_agent.v24457_adaptive_entropy_support import (  # noqa: E402
    MAXIMUM_ACTIVE_SOURCES,
    MAXIMUM_ADDITIONAL_FETCHES,
    MAXIMUM_TOTAL_FETCHES,
    POLICY_ID as ADAPTIVE_POLICY_ID,
)
from deepwide_agent.v24459_proof_carrying_adaptive_entropy_support import (  # noqa: E402
    POLICY_ID as PROOF_POLICY_ID,
    run_and_persist_proof_carrying_v24457_task,
)
from deepwide_agent.v24460_adaptive_capability_projection import (  # noqa: E402
    POLICY_ID as PROJECTION_POLICY_ID,
    aggregate_projections,
    validate_aggregate as validate_mechanism_aggregate,
)
from deepwide_agent.v24461_proof_carrying_adaptive_timed_runner import (  # noqa: E402
    POLICY_ID as TIMED_RUNNER_POLICY_ID,
    aggregate_stage_timings,
    run_proof_carrying_adaptive_timed_subprocess,
    validate_stage_timing_aggregate,
)
from scripts import audit_v24462_proof_carrying_adaptive_build as build_audit  # noqa: E402
from scripts import v24452_third_source_timing_external_gate as history  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24463_fresh_proof_carrying_adaptive_external_gate_v1"
PROTOCOL = Path(f"results/v24463_adaptive_proof_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24463_adaptive_proof_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24463_adaptive_proof_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24463_adaptive_proof_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24463_adaptive_proof_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24463_adaptive_proof_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24463_adaptive_proof_external_postresult_audit_v1_{DATE}.json"
)
PARENT = build_audit.AUDIT
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_proof_carrying_adaptive_entropy_support_gate"
RUNNER_MARKER = "scripts/v24463_adaptive_proof_external_gate.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
SELECTED = 16
EXECUTOR_COUNT = 8
MODEL_SLOT_CAP = 2
TASK_WALL_SECONDS = 235
PARENT_TIMEOUT_SECONDS = 255
BATCH_WALL_CEILING_SECONDS = 480.0
PARENT_VALIDATION_P95_CEILING_SECONDS = 1.0
LIMITS = ScoreFirstLimits(
    wall_seconds=TASK_WALL_SECONDS,
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
    "minimum_safe_change_count": 1,
    "minimum_decision_credit_nats": 1e-12,
    "maximum_parent_validation_p95_seconds": PARENT_VALIDATION_P95_CEILING_SECONDS,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 5,
    "maximum_fetch_helper_failures": 5,
}

ENTITY_GROUPS = (
    ("University of Alabama", "Auburn University", "University of Arkansas", "Colorado State University", "University of Connecticut", "University of Delaware", "Florida State University", "University of Hawaii at Manoa"),
    ("University of Idaho", "University of Kansas", "Kansas State University", "University of Kentucky", "University of Louisville", "Louisiana State University", "Tulane University", "University of Maine"),
    ("University of Massachusetts Amherst", "University of Minnesota", "University of Mississippi", "Mississippi State University", "University of Missouri", "University of Montana", "University of Nebraska–Lincoln", "University of Nevada Reno"),
    ("University of New Hampshire", "University of New Mexico", "North Carolina State University", "University of North Dakota", "University of Oklahoma", "Oklahoma State University", "University of Oregon", "Oregon State University"),
    ("University of Rhode Island", "University of South Carolina", "University of South Dakota", "University of Tennessee", "University of Vermont", "Virginia Tech", "Washington State University", "West Virginia University"),
    ("University of Wisconsin–Madison", "University of Wyoming", "University at Buffalo", "Universidad de Chile", "University of the Republic Uruguay", "University of Havana", "University of San Carlos of Guatemala", "National Autonomous University of Honduras"),
    ("University of El Salvador", "University of Panama", "Central University of Venezuela", "State University of Campinas", "University of Brasília", "Federal University of Paraná", "Federal University of Pernambuco", "Federal University of Bahia"),
    ("National University of San Marcos", "Chiang Mai University", "Thammasat University", "Universiti Sains Malaysia", "Universiti Kebangsaan Malaysia", "Airlangga University", "Diponegoro University", "IPB University"),
    ("De La Salle University", "University of Santo Tomas", "Hanoi University of Science and Technology", "Royal University of Phnom Penh", "National University of Laos", "University of Yangon", "University of Dhaka", "Bangladesh University of Engineering and Technology"),
    ("University of Peradeniya", "University of Karachi", "Tribhuvan University", "University of Florence", "University of Turin", "University of Naples Federico II", "Autonomous University of Madrid", "University of Granada"),
    ("University of Seville", "University of Valencia", "University of Salamanca", "University of Zaragoza", "Vilnius University", "University of Latvia", "University of Alaska Fairbanks", "University of Alaska Anchorage"),
    ("University of Central Florida", "University of South Florida", "Florida International University", "University of North Florida", "Florida Atlantic University", "University of West Florida", "University of Central Arkansas", "Arkansas State University"),
    ("University of Arkansas at Little Rock", "University of South Alabama", "University of Alabama at Birmingham", "University of Alabama in Huntsville", "Troy University", "Samford University", "University of Northern Colorado", "University of Denver"),
    ("University of Colorado Denver", "University of Colorado Colorado Springs", "Sacred Heart University", "Fairfield University", "Central Connecticut State University", "Southern Connecticut State University", "University of New Haven", "Delaware State University"),
    ("George Mason University", "Old Dominion University", "Virginia Commonwealth University", "James Madison University", "University of Richmond", "Marshall University", "University of Wisconsin–Milwaukee", "Marquette University"),
    ("University of Wisconsin–La Crosse", "University of Wisconsin–Eau Claire", "University of Wisconsin–Green Bay", "University of Wisconsin–Stevens Point", "Montana State University", "Boise State University", "Idaho State University", "University of Nevada Las Vegas"),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.44.63 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
SOURCE_FILES = (
    "src/deepwide_agent/v24457_adaptive_entropy_support.py",
    "src/deepwide_agent/v24459_proof_carrying_adaptive_entropy_support.py",
    "src/deepwide_agent/v24460_adaptive_capability_projection.py",
    "src/deepwide_agent/v24461_proof_carrying_adaptive_timed_runner.py",
    "scripts/audit_v24462_proof_carrying_adaptive_build.py",
    "tests/test_v24459_proof_carrying_adaptive_entropy_support.py",
    "tests/test_v24461_proof_carrying_adaptive_timed_runner.py",
    "tests/test_audit_v24462_proof_carrying_adaptive_build.py",
    RUNNER_MARKER,
    "tests/test_v24463_adaptive_proof_external_gate.py",
)
TEST_FILES = (
    "tests/test_v24459_proof_carrying_adaptive_entropy_support.py",
    "tests/test_v24461_proof_carrying_adaptive_timed_runner.py",
    "tests/test_audit_v24462_proof_carrying_adaptive_build.py",
    "tests/test_v24463_adaptive_proof_external_gate.py",
)
SECRET = build_audit.SECRET
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
URL = re.compile(r"https?://", re.IGNORECASE)
PROTOCOL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "parent",
        "scope",
        "task_contract",
        "mechanism",
        "discovery_partition",
        "provider",
        "budget",
        "gates",
        "lease",
        "surface_manifest",
        "surface_manifest_sha256",
        "source_policy",
        "authorization",
        "protocol_payload_sha256",
    }
)


_ordinary = history._ordinary
_read = history._read
_sealed = history._sealed
publish = history.publish
_write_new = history._write_new
_git = history._git
_future = history._future
_port_listening = history._port_listening
_environment = history._environment


def _build_parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    if (
        value.get("role") != "v24462_proof_carrying_adaptive_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("fresh_external_protocol_design")
        is not True
        or any(
            value.get("authorization", {}).get(name) is not False
            for name in (
                "external_probe_launch",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.63 build parent drifted")
    return value


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.44.63 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _prior_questions() -> tuple[str, ...]:
    old = history.parent
    populations = (
        old.population_1,
        old.population_2,
        old.population_3,
        old.population_4,
        old.population_5,
        old.population_6,
        old.population_7,
        old.population_8,
        old.population_9,
        old.population_10,
        old.population_11,
        old.population_12,
        old.population_13,
        old.population_14,
        old,
        history,
    )
    return tuple(question for population in populations for question in population.QUESTIONS)


def _fresh_entity_vector_valid() -> bool:
    parser = history.parent
    current = {
        entity for question in QUESTIONS for entity in parser._question_entity_vector(question)
    }
    prior_questions = _prior_questions()
    prior = {
        entity
        for question in prior_questions
        for entity in parser._question_entity_vector(question)
    }
    current_canonical = {parser._canonical_entity(entity) for entity in current}
    prior_canonical = {parser._canonical_entity(entity) for entity in prior}
    return (
        len(current) == 128
        and len(current_canonical) == 128
        and len(prior_questions) == 252
        and len(prior) == 2016
        and len(prior_canonical) == 2016
        and current.isdisjoint(prior)
        and current_canonical.isdisjoint(prior_canonical)
    )


def neutral_task(ordinal: int) -> dict[str, str]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= SELECTED
    ):
        raise ValueError("V2.44.63 neutral ordinal is invalid")
    return validate_visible_task(
        {
            "opaque_id": "task_"
            + hashlib.sha256(
                f"{PROTOCOL_ID}|fresh-task|{ordinal}".encode("utf-8")
            ).hexdigest()[:24],
            "question": QUESTIONS[ordinal - 1],
        }
    )


def partition_seed(ordinal: int) -> str:
    neutral_task(ordinal)
    return hashlib.sha256(
        f"{PROTOCOL_ID}|adaptive-entropy|{ordinal}".encode("utf-8")
    ).hexdigest()


def _task_contract() -> dict[str, Any]:
    return {
        "selected": SELECTED,
        "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
        "fresh_128_entity_vector_literal_and_canonical_disjoint_from_sixteen_prior_external_populations": _fresh_entity_vector_valid(),
        "prior_external_entity_count": 2016,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _mechanism_contract() -> dict[str, Any]:
    return {
        "adaptive_policy": ADAPTIVE_POLICY_ID,
        "proof_policy": PROOF_POLICY_ID,
        "projection_policy": PROJECTION_POLICY_ID,
        "timed_runner_policy": TIMED_RUNNER_POLICY_ID,
        "active_source_cap": MAXIMUM_ACTIVE_SOURCES,
        "parent_fetch_cap": 10,
        "total_fetch_cap": MAXIMUM_TOTAL_FETCHES,
        "maximum_additional_fetches": MAXIMUM_ADDITIONAL_FETCHES,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_provider_search_calls": 0,
        "safe_change_thresholds_preserved": True,
        "complete_child_semantic_validation_before_certificate": True,
        "parent_exact_surface_certificate_and_terminal_validation": True,
        "projection_consumes_only_validated_capability": True,
        "failure_preserves_partial_effect_lower_bounds": True,
        "parent_recursive_historical_replay": False,
        "public_projection_contains_lead_page_or_hash": False,
    }


def _provider_contract() -> dict[str, Any]:
    return {
        "proxy_url": f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "service_tier": "priority",
        "max_retries_per_batch": 2,
        "executor_count": EXECUTOR_COUNT,
        "model_slot_cap": MODEL_SLOT_CAP,
        "maximum_provider_effect_seconds": MAXIMUM_PROVIDER_EFFECT_SECONDS,
    }


def _budget_contract() -> dict[str, Any]:
    return {
        "task_wall_seconds": TASK_WALL_SECONDS,
        "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
        "maximum_batch_wall_seconds": BATCH_WALL_CEILING_SECONDS,
        "model_calls": 3,
        "maximum_logical_search_queries": 5,
        "maximum_hosted_search_batches": 3,
        "parent_fetch_targets": 10,
        "maximum_additional_fetch_targets": MAXIMUM_ADDITIONAL_FETCHES,
        "total_fetch_targets": MAXIMUM_TOTAL_FETCHES,
        "single_batch_no_resume_retry_skip_or_selective_rerun": True,
    }


def _source_policy() -> dict[str, bool]:
    return {
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "task_text_identifier_query_url_page_prediction_response_candidate_value_or_private_hash_persisted": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "official_evaluator_called": False,
    }


def _lease_contract() -> dict[str, Any]:
    return {
        "path": str(LEASE_PATH),
        "owner": LEASE_OWNER,
        "purpose": LEASE_PURPOSE,
        "nonblocking_single_owner": True,
    }


def _discovery_contract(seeds: Sequence[str]) -> dict[str, Any]:
    return {
        "seed_sha256_vector": list(seeds),
        "seed_depends_only_on_protocol_and_fixed_ordinal": True,
        "frozen_source_disjoint_lead_pool_reused": True,
        "later_fetch_priority_uses_current_validated_entropy": True,
        "additional_provider_search_calls": 0,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_adaptive_proof_external_probe_design": True,
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
    _build_parent(root)
    LIMITS.validate()
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    seeds = [partition_seed(index) for index in range(1, SELECTED + 1)]
    if not _fresh_entity_vector_valid():
        raise RuntimeError("V2.44.63 external entity vector overlaps its parents")
    if require_pristine and not _future(
        root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.44.63 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24463_adaptive_proof_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "scope": "fresh_nonbenchmark_proof_carrying_adaptive_entropy_support_gate",
        "task_contract": _task_contract(),
        "mechanism": _mechanism_contract(),
        "discovery_partition": _discovery_contract(seeds),
        "provider": _provider_contract(),
        "budget": _budget_contract(),
        "gates": dict(GATES),
        "lease": _lease_contract(),
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": _source_policy(),
        "authorization": _protocol_authorization(),
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    encoded = json.dumps(value, ensure_ascii=False)
    if any(task["opaque_id"] in encoded or task["question"] in encoded for task in tasks):
        raise RuntimeError("V2.44.63 protocol persisted task content")
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = protocol.get("surface_manifest")
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    seeds = [partition_seed(index) for index in range(1, SELECTED + 1)]
    encoded = json.dumps(protocol, ensure_ascii=False)
    if (
        set(protocol) != PROTOCOL_KEYS
        or protocol.get("artifact_version") != 1
        or protocol.get("role") != "v24463_adaptive_proof_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or isinstance(protocol.get("created_at_unix"), bool)
        or not isinstance(protocol.get("created_at_unix"), int)
        or protocol["created_at_unix"] < 0
        or protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or protocol.get("scope")
        != "fresh_nonbenchmark_proof_carrying_adaptive_entropy_support_gate"
        or protocol.get("task_contract") != _task_contract()
        or protocol.get("mechanism") != _mechanism_contract()
        or protocol.get("discovery_partition") != _discovery_contract(seeds)
        or protocol.get("provider") != _provider_contract()
        or protocol.get("budget") != _budget_contract()
        or protocol.get("gates") != GATES
        or protocol.get("lease") != _lease_contract()
        or protocol.get("source_policy") != _source_policy()
        or protocol.get("authorization") != _protocol_authorization()
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or not _fresh_entity_vector_valid()
        or any(task["opaque_id"] in encoded or task["question"] in encoded for task in tasks)
        or SECRET.search(encoded)
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.44.63 protocol drifted")
    _build_parent(root)
    return protocol


def _run_tests() -> dict[str, bool]:
    output: dict[str, bool] = {}
    for relative in TEST_FILES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-q"],
            cwd=ROOT,
            env=_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=420,
            check=False,
        )
        output[relative] = completed.returncode == 0
    return output


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    pristine = _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT))
    tests = _run_tests()
    privileged, imports = build_audit.base._ast_findings(Path(RUNNER_MARKER))
    lease = lease_observation(root, Path("/proc"))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    watchers = protected_watcher_snapshot()
    parent_watchers = _build_parent(root)["closure"]["protected_watchers"]
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not all(tests.values()):
        findings.append("focused_tests_failed")
    if privileged:
        findings.append("privileged_field_access_in_v24463_runtime")
    if imports:
        findings.append("evaluator_import_in_v24463_runtime")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if head != remote:
        findings.append("protocol_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if watchers != parent_watchers:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24463_adaptive_proof_external_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "fresh_128_entity_vector_frozen": True,
            "focused_tests": tests,
            "keyless_proxy_listening_without_api_request": _port_listening(),
            "shared_api_lease_inactive": lease.get("active") is False,
            "protocol_commit_pushed": head == remote,
            "worktree_clean": clean,
            "future_surface_pristine": pristine,
            "protected_watchers_unchanged": watchers == parent_watchers,
            "benchmark_or_evaluator_surface_authorized": False,
        },
        "protected_watchers": watchers,
        "privileged_field_accesses": privileged,
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
        "authorization": {
            "one_fresh_adaptive_proof_external_probe_launch": not findings,
            "benchmark_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.44.63 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    checks = value.get("checks")
    provenance = value.get("provenance")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24463_adaptive_proof_external_preactivation_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or not isinstance(checks, Mapping)
        or checks.get("protocol_valid_and_sealed") is not True
        or checks.get("fresh_128_entity_vector_frozen") is not True
        or not isinstance(checks.get("focused_tests"), Mapping)
        or not all(checks["focused_tests"].values())
        or checks.get("keyless_proxy_listening_without_api_request") is not True
        or checks.get("shared_api_lease_inactive") is not True
        or checks.get("protocol_commit_pushed") is not True
        or checks.get("worktree_clean") is not True
        or checks.get("future_surface_pristine") is not True
        or checks.get("protected_watchers_unchanged") is not True
        or checks.get("benchmark_or_evaluator_surface_authorized") is not False
        or value.get("privileged_field_accesses") != []
        or value.get("evaluator_imports") != []
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or not isinstance(provenance, Mapping)
        or provenance.get("protocol_sha256") != sha256(root / PROTOCOL)
        or provenance.get("parent_sha256") != sha256(root / PARENT)
        or provenance.get("surface_manifest_sha256")
        != validate_protocol(root)["surface_manifest_sha256"]
        or provenance.get("head") != provenance.get("target_main")
        or not isinstance(authorization, Mapping)
        or authorization.get("one_fresh_adaptive_proof_external_probe_launch")
        is not True
        or any(
            authorization.get(name) is not False
            for name in ("benchmark_launch", "paired_dev64_or_exact220", "evaluator")
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.63 preaudit drifted")
    return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    audit = validate_preaudit(root)
    findings: list[str] = []
    if not _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        findings.append("activation_or_execution_surface_not_pristine")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24463_adaptive_proof_external_activation",
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
        "authorization": {
            "one_fresh_adaptive_proof_external_probe_launch": not findings,
            "benchmark_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.44.63 activation failed")
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, ACTIVATION)
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24463_adaptive_proof_external_activation"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("surface_manifest_sha256")
        != validate_protocol(root)["surface_manifest_sha256"]
        or value.get("selected") != SELECTED
        or value.get("executor_count") != EXECUTOR_COUNT
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or not isinstance(authorization, Mapping)
        or authorization.get("one_fresh_adaptive_proof_external_probe_launch")
        is not True
        or any(
            authorization.get(name) is not False
            for name in ("benchmark_launch", "paired_dev64_or_exact220", "evaluator")
        )
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.44.63 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.44.63 execution surface is not pristine")
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    findings: list[str] = []
    if head != remote:
        findings.append("activation_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24463_adaptive_proof_external_execution_start",
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
        raise RuntimeError("V2.44.63 execution start failed: " + ",".join(findings))
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, EXECUTION_START)
    if (
        value.get("role") != "v24463_adaptive_proof_external_execution_start"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("activation_base_commit") != value.get("target_main_at_start")
        or re.fullmatch(r"[0-9a-f]{40}", str(value.get("activation_base_commit")))
        is None
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("selected") != SELECTED
        or value.get("executor_count") != EXECUTOR_COUNT
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("api_called_before_execution_start") is not False
        or value.get("runtime_input_exactly_opaque_id_and_question") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_or_evaluator_authorized") is not False
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.44.63 execution start drifted")
    validate_activation(root)
    return value


def _child(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal)
    task = neutral_task(ordinal)
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    validator_manifest = validate_protocol(ROOT)["surface_manifest_sha256"]

    def action() -> None:
        deadline = time.monotonic() + TASK_WALL_SECONDS

        def model_factory():
            return build_deadline_model(
                url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
                model_name="gpt-5.6-sol",
                reasoning_effort="low",
                service_tier="priority",
                static_timeout_seconds=MAXIMUM_PROVIDER_EFFECT_SECONDS,
                max_retries=2,
                slot_directory=Path(args.slots),
                output_root=output_root,
                slot_cap=MODEL_SLOT_CAP,
                pool_id=POOL_ID,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=5.0,
                minimum_attempt_seconds=0.05,
            )

        def search_factory():
            return UncertaintyDeadlineAwareNativeSearchClient(
                f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
                "gpt-5.6-sol",
                reasoning_effort="low",
                service_tier="priority",
                timeout=MAXIMUM_PROVIDER_EFFECT_SECONDS,
                max_retries=2,
                max_workers=1,
                batch_size=8,
                search_context_size="medium",
                max_output_tokens=4_000,
                fetch_pages=False,
                fetch_workers=8,
                fetch_timeout=20,
                max_page_chars=LIMITS.page_chars,
                hard_fetch_deadline_seconds=25,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=5.0,
                minimum_attempt_seconds=0.05,
            )

        run_and_persist_proof_carrying_v24457_task(
            task,
            model_factory=model_factory,
            search_factory=search_factory,
            partition_seed_sha256=partition_seed(ordinal),
            limits=LIMITS,
            monotonic=time.monotonic,
            expected_model_cap=MODEL_SLOT_CAP,
            directory=directory,
            writer=lambda name, value: _write_new(directory / name, value),
            validator_manifest_sha256=validator_manifest,
        )

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=CHILD_RESULT_NAME,
        model_receipt_name="model_slot_receipt.json",
        transport_receipt_name="transport_health.json",
        terminal_name="child_terminal_receipt.json",
    )


def _run_one(
    root: Path,
    output_root: Path,
    slots: Path,
    directory: Path,
    ordinal: int,
) -> dict[str, Any]:
    protocol = validate_protocol(root)
    outcome = run_proof_carrying_adaptive_timed_subprocess(
        ordinal=ordinal,
        cwd=root,
        output_root=output_root,
        directory=directory,
        command=[
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / RUNNER_MARKER),
            "child",
            "--ordinal",
            str(ordinal),
            "--output-root",
            str(output_root),
            "--directory",
            str(directory),
            "--slots",
            str(slots),
        ],
        environment=_environment(),
        timeout_seconds=PARENT_TIMEOUT_SECONDS,
        expected_model_cap=MODEL_SLOT_CAP,
        expected_validator_manifest_sha256=protocol["surface_manifest_sha256"],
    )
    return {
        "mechanism": outcome.adaptive_projection,
        "observation": outcome.observation,
        "timing": outcome.timing_receipt,
    }


def _diagnostic_complete(
    mechanism: Mapping[str, Any],
    observation: Mapping[str, Any],
    timing: Mapping[str, Any],
) -> bool:
    return (
        mechanism.get("selected") == SELECTED
        and mechanism.get("exact_ordinal_vector") is True
        and mechanism.get("passed_tasks") == SELECTED
        and mechanism.get("failed_tasks") == 0
        and mechanism.get("all_threshold_partitions_exact") is True
        and mechanism.get("all_effects_conserved") is True
        and mechanism.get("all_single_validation_attested") is True
        and mechanism.get("all_projections_consumed_validated_capabilities") is True
        and observation.get("selected") == SELECTED
        and observation.get("exact_ordinal_vector") is True
        and observation.get("success_tasks") == SELECTED
        and observation.get("failure_tasks") == 0
        and observation.get("fully_observed_effect_tasks") == SELECTED
        and timing.get("selected") == SELECTED
        and timing.get("exact_ordinal_vector") is True
        and timing.get("parent_success_tasks") == SELECTED
        and timing.get("certificate_validation_invocations") == SELECTED
        and timing.get("adaptive_projection_invocations") == SELECTED
        and timing.get("capability_observation_tasks") == SELECTED
        and timing.get("capability_adaptive_projection_tasks") == SELECTED
        and timing.get("failure_lower_bound_observation_tasks") == 0
        and timing.get("recursive_historical_semantic_replay_tasks") == 0
    )


def _mechanism_passed(mechanism: Mapping[str, Any]) -> bool:
    return (
        int(mechanism.get("total_adaptive_safe_change_count", 0))
        >= GATES["minimum_safe_change_count"]
        and float(
            mechanism.get("total_adaptive_final_decision_credit_total_nats", 0.0)
        )
        >= GATES["minimum_decision_credit_nats"]
    )


def _reliability_passed(observation: Mapping[str, Any]) -> bool:
    return (
        int(observation.get("slot_timeouts_lower_bound", -1))
        <= GATES["maximum_slot_timeouts"]
        and int(observation.get("provider_deadline_failures_lower_bound", -1))
        <= GATES["maximum_provider_deadline_failures"]
        and int(observation.get("hosted_search_deadline_failures_lower_bound", -1))
        <= GATES["maximum_hosted_search_deadline_failures"]
        and int(observation.get("hard_fetch_deadline_failures_lower_bound", -1))
        <= GATES["maximum_hard_fetch_deadline_failures"]
        and int(observation.get("fetch_helper_failures_lower_bound", -1))
        <= GATES["maximum_fetch_helper_failures"]
        and int(observation.get("unobserved_effect_tasks", -1)) == 0
    )


def _parent_validation_passed(timing: Mapping[str, Any]) -> bool:
    value = timing.get("parent_certificate_validation_wall_p95_seconds")
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0 <= float(value) <= GATES["maximum_parent_validation_p95_seconds"]
        and timing.get("recursive_historical_semantic_replay_tasks") == 0
    )


def _diagnostic_route(
    mechanism: Mapping[str, Any],
    *,
    diagnostic_complete: bool,
    reliability_passed: bool,
    parent_validation_passed: bool,
    latency_passed: bool,
) -> str:
    if not diagnostic_complete:
        return "runtime_validation_or_observability_repair"
    if int(mechanism.get("total_adaptive_additional_fetch_calls", 0)) == 0:
        return "frozen_lead_coverage_successor"
    if int(mechanism.get("total_adaptive_safe_change_count", 0)) == 0:
        return "adaptive_support_coverage_successor"
    if float(mechanism.get("total_adaptive_final_decision_credit_total_nats", 0.0)) <= 0:
        return "entropy_to_decision_alignment_successor"
    if not reliability_passed:
        return "provider_or_fetch_reliability_successor"
    if not parent_validation_passed:
        return "parent_validation_successor"
    if not latency_passed:
        return "latency_capacity_successor"
    return "fresh_paired_dev64_design"


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    mechanism = copied.get("mechanism_aggregate")
    observation = copied.get("observation_aggregate")
    timing = copied.get("stage_timing_aggregate")
    if not all(isinstance(item, Mapping) for item in (mechanism, observation, timing)):
        raise RuntimeError("V2.44.63 result aggregate is absent")
    validate_mechanism_aggregate(mechanism)
    validate_observation_aggregate(observation, expected_selected=SELECTED)
    validate_stage_timing_aggregate(timing)
    diagnostic = _diagnostic_complete(mechanism, observation, timing)
    mechanism_go = _mechanism_passed(mechanism)
    reliability = _reliability_passed(observation)
    parent_validation = _parent_validation_passed(timing)
    batch = copied.get("batch_wall_seconds")
    latency = (
        isinstance(batch, (int, float))
        and not isinstance(batch, bool)
        and math.isfinite(float(batch))
        and 0 <= float(batch) <= BATCH_WALL_CEILING_SECONDS
    )
    encoded = json.dumps(copied, ensure_ascii=False)
    if (
        copied.get("role") != "v24463_adaptive_proof_external_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("selected") != SELECTED
        or copied.get("executor_count") != EXECUTOR_COUNT
        or copied.get("model_slot_cap") != MODEL_SLOT_CAP
        or copied.get("mechanism_failure_as_zero_rows") != observation.get("failure_tasks")
        or copied.get("mechanism_passed") is not mechanism_go
        or copied.get("reliability_passed") is not reliability
        or copied.get("parent_validation_passed") is not parent_validation
        or copied.get("latency_passed") is not latency
        or copied.get("diagnostic_complete") is not diagnostic
        or copied.get("passed")
        is not (diagnostic and mechanism_go and reliability and parent_validation and latency)
        or copied.get("temporary_execution_directory_remaining") is not False
        or copied.get("private_task_or_web_content_persisted") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or copied.get("official_evaluator_called") is not False
        or copied.get("resume_retry_skip_or_revaluation") is not False
        or not isinstance(copied.get("provenance"), Mapping)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(item)) is None
            for item in copied["provenance"].values()
        )
        or seal != payload_sha256(unsigned)
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
    ):
        raise RuntimeError("V2.44.63 public result drifted or contains content")
    return copied


def _git_ready(root: Path) -> bool:
    try:
        return (
            _git(root, "rev-parse", "HEAD") == _git(root, "rev-parse", "target/main")
            and _git(root, "status", "--porcelain") == ""
            and subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(EXECUTION_START)],
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            ).returncode
            == 0
        )
    except subprocess.SubprocessError:
        return False


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    if not _future(root, (RESULT, DECISION, POSTAUDIT)) or not _git_ready(root):
        raise RuntimeError("V2.44.63 result/git surface is not ready")
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            directories: list[Path] = []
            for ordinal in range(1, SELECTED + 1):
                directory = output_root / f"task_{ordinal:02d}"
                directory.mkdir()
                directories.append(directory)
            started = time.monotonic()
            outcomes: list[dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=EXECUTOR_COUNT) as pool:
                futures = [
                    pool.submit(_run_one, root, output_root, slots, directory, ordinal)
                    for ordinal, directory in enumerate(directories, start=1)
                ]
                for future in futures:
                    outcomes.append(future.result())
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
            diagnostic = _diagnostic_complete(mechanism, observation, timing)
        mechanism_go = _mechanism_passed(mechanism)
        reliability = _reliability_passed(observation)
        parent_validation = _parent_validation_passed(timing)
        latency = batch_wall <= BATCH_WALL_CEILING_SECONDS
        value = {
            "artifact_version": 1,
            "role": "v24463_adaptive_proof_external_result",
            "protocol_id": PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": SELECTED,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
            "batch_wall_seconds": round(batch_wall, 6),
            "mechanism_aggregate": mechanism,
            "observation_aggregate": observation,
            "stage_timing_aggregate": timing,
            "mechanism_failure_as_zero_rows": observation["failure_tasks"],
            "mechanism_passed": mechanism_go,
            "reliability_passed": reliability,
            "parent_validation_passed": parent_validation,
            "latency_passed": latency,
            "diagnostic_complete": diagnostic,
            "passed": diagnostic
            and mechanism_go
            and reliability
            and parent_validation
            and latency,
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
        raise RuntimeError("V2.44.63 protected watcher identity drifted")
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = validate_public_result(_read(root, RESULT))
    route = _diagnostic_route(
        result["mechanism_aggregate"],
        diagnostic_complete=result["diagnostic_complete"],
        reliability_passed=result["reliability_passed"],
        parent_validation_passed=result["parent_validation_passed"],
        latency_passed=result["latency_passed"],
    )
    value = {
        "artifact_version": 1,
        "role": "v24463_adaptive_proof_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "fresh_adaptive_proof_external_mechanism_go"
        if result["passed"]
        else "fresh_adaptive_proof_external_no_go",
        "passed": result["passed"],
        "diagnostic_route": route,
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
        },
        "claim_scope": {
            "fresh_nonbenchmark_mechanism_and_parent_timing_measured": True,
            "benchmark_quality_measured": False,
            "future_population_or_sota_supported": False,
        },
        "authorization": {
            "diagnostic_successor_design": not result["passed"],
            "fresh_paired_dev64_design": result["passed"],
            "fresh_paired_dev64_launch": False,
            "new_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return validate_decision(root, value=value)


def validate_decision(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    decision = dict(value) if value is not None else _read(root, DECISION)
    result = validate_public_result(_read(root, RESULT))
    route = _diagnostic_route(
        result["mechanism_aggregate"],
        diagnostic_complete=result["diagnostic_complete"],
        reliability_passed=result["reliability_passed"],
        parent_validation_passed=result["parent_validation_passed"],
        latency_passed=result["latency_passed"],
    )
    authorization = decision.get("authorization")
    if (
        decision.get("role") != "v24463_adaptive_proof_external_decision"
        or decision.get("protocol_id") != PROTOCOL_ID
        or decision.get("status")
        != (
            "fresh_adaptive_proof_external_mechanism_go"
            if result["passed"]
            else "fresh_adaptive_proof_external_no_go"
        )
        or decision.get("passed") is not result["passed"]
        or decision.get("diagnostic_route") != route
        or decision.get("provenance")
        != {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
        }
        or decision.get("claim_scope")
        != {
            "fresh_nonbenchmark_mechanism_and_parent_timing_measured": True,
            "benchmark_quality_measured": False,
            "future_population_or_sota_supported": False,
        }
        or not isinstance(authorization, Mapping)
        or authorization.get("diagnostic_successor_design") is not (not result["passed"])
        or authorization.get("fresh_paired_dev64_design") is not result["passed"]
        or any(
            authorization.get(name) is not False
            for name in (
                "fresh_paired_dev64_launch",
                "new_exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not _sealed(decision, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.44.63 decision drifted")
    return decision


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    decision = validate_decision(root)
    lease_active = lease_observation(root, Path("/proc")).get("active") is not False
    watchers = protected_watcher_snapshot()
    start_watchers = _read(root, EXECUTION_START)["protected_watchers"]
    findings: list[str] = []
    if lease_active:
        findings.append("shared_api_lease_active")
    if watchers != start_watchers:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24463_adaptive_proof_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision["status"],
        "diagnostic_route": decision["diagnostic_route"],
        "temporary_execution_directory_remaining": False,
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "private_task_or_web_content_persisted": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "diagnostic_successor_design": decision["authorization"][
                "diagnostic_successor_design"
            ]
            and not findings,
            "fresh_paired_dev64_design": decision["authorization"][
                "fresh_paired_dev64_design"
            ]
            and not findings,
            "fresh_paired_dev64_launch": False,
            "new_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_postaudit(root, value=value)


def validate_postaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else _read(root, POSTAUDIT)
    decision = validate_decision(root)
    expected_findings: list[str] = []
    if audit.get("shared_api_lease_active") is True:
        expected_findings.append("shared_api_lease_active")
    if audit.get("protected_watchers") != _read(root, EXECUTION_START).get(
        "protected_watchers"
    ):
        expected_findings.append("protected_watcher_identity_drifted")
    authorization = audit.get("authorization")
    if (
        audit.get("role") != "v24463_adaptive_proof_external_postresult_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or audit.get("result_sha256") != sha256(root / RESULT)
        or audit.get("decision_sha256") != sha256(root / DECISION)
        or audit.get("decision_status") != decision["status"]
        or audit.get("diagnostic_route") != decision["diagnostic_route"]
        or audit.get("temporary_execution_directory_remaining") is not False
        or audit.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or audit.get("private_task_or_web_content_persisted") is not False
        or audit.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or audit.get("findings") != expected_findings
        or audit.get("audit_valid") is not (not expected_findings)
        or not isinstance(authorization, Mapping)
        or authorization.get("diagnostic_successor_design")
        is not (
            decision["authorization"]["diagnostic_successor_design"]
            and not expected_findings
        )
        or authorization.get("fresh_paired_dev64_design")
        is not (
            decision["authorization"]["fresh_paired_dev64_design"]
            and not expected_findings
        )
        or any(
            authorization.get(name) is not False
            for name in (
                "fresh_paired_dev64_launch",
                "new_exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.63 postresult audit drifted")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("protocol", "preaudit", "activation", "start", "run", "finalize", "child"),
    )
    parser.add_argument("--ordinal")
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--slots")
    args = parser.parse_args()
    if args.command == "protocol":
        publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe()
    elif args.command == "finalize":
        publish(ROOT / DECISION, build_decision())
        publish(ROOT / POSTAUDIT, build_postaudit())
    elif args.command == "child":
        if not all((args.ordinal, args.output_root, args.directory, args.slots)):
            parser.error("child requires ordinal, output-root, directory, and slots")
        _child(args)


if __name__ == "__main__":
    main()
