#!/usr/bin/env python3
"""Fresh label-blind external gate for bounded entropy-to-decision recovery.

Sixteen fixed public-document tasks use 128 entities disjoint, both literally
and canonically, from all 1,888 entities in the fifteen prior external
populations.  Runtime input is exactly ``opaque_id`` and ``question``.  The
V2.44.47 successor may reuse the next ranked source-disjoint lead and perform
at most one additional page fetch; it performs no extra model request,
logical query, search batch, or provider search call.

V2.44.48 performs one complete serialized-envelope and independent terminal
artifact validation.  V2.44.49 receives only the resulting two content-free
receipts.  V2.44.50 separately measures child wait wall, all parent-side
validation/observation wall, and projection wall.  Private execution
artifacts exist only inside a temporary directory and are deleted before the
public result is published.

This gate does not open a benchmark manifest, mapping, gold answer, label,
evaluator, reward, or score surface.  A GO may authorize only design of a
fresh paired dev64; it cannot authorize that launch, exact220, evaluation,
leaderboard submission, or a SOTA claim.
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
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    MAXIMUM_ACTIVE_SOURCES,
    MAXIMUM_TOTAL_FETCHES,
    POLICY_ID as THIRD_SOURCE_POLICY_ID,
    run_and_persist_v24447_task,
)
from deepwide_agent.v24448_serialized_third_source_envelope import (  # noqa: E402
    POLICY_ID as SERIALIZED_THIRD_SOURCE_POLICY_ID,
)
from deepwide_agent.v24450_timed_third_source_runner import (  # noqa: E402
    POLICY_ID as TIMED_RUNNER_POLICY_ID,
    aggregate_stage_timings,
    run_timed_observed_subprocess,
    validate_stage_timing_aggregate,
)
from scripts import audit_v24451_third_source_timing_build as build_audit  # noqa: E402
from scripts import v24445_serialized_narrative_external_gate as parent  # noqa: E402
from scripts import v24449_third_source_external_projection as projection  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24452_fresh_third_source_entropy_timing_external_gate_v1"
PROTOCOL = Path(f"results/v24452_third_source_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24452_third_source_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24452_third_source_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24452_third_source_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24452_third_source_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24452_third_source_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24452_third_source_external_postresult_audit_v1_{DATE}.json")
PARENT = build_audit.AUDIT
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_third_source_entropy_to_decision_timing_gate"
RUNNER_MARKER = "scripts/v24452_third_source_timing_external_gate.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
SELECTED = 16
EXECUTOR_COUNT = 8
MODEL_SLOT_CAP = 2
TASK_WALL_SECONDS = 235
PARENT_TIMEOUT_SECONDS = 255
BATCH_WALL_CEILING_SECONDS = 480.0
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
    "minimum_third_source_safe_change_tasks": 1,
    "minimum_third_source_decision_credit_nats": 1e-12,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 5,
    "maximum_fetch_helper_failures": 5,
}
ENTITY_GROUPS = (
    ("Queen’s University", "University of Manitoba", "University of Saskatchewan", "University of Newcastle Australia", "Ludwig Maximilian University of Munich", "University of Tübingen", "University of Göttingen", "RWTH Aachen University"),
    ("Karlsruhe Institute of Technology", "University of Hamburg", "University of Cologne", "TU Dresden", "University of Münster", "University of Würzburg", "University of Zurich", "University of Geneva"),
    ("University of Basel", "University of Bern", "University of Lausanne", "University of St. Gallen", "Erasmus University Rotterdam", "University of Groningen", "Vrije Universiteit Amsterdam", "Eindhoven University of Technology"),
    ("University of Twente", "Université catholique de Louvain", "University of Antwerp", "Vrije Universiteit Brussel", "Université libre de Bruxelles", "University of Liège", "Hasselt University", "Trinity College Dublin"),
    ("University College Dublin", "University of Galway", "University College Cork", "Dublin City University", "University of Limerick", "Maynooth University", "Technological University Dublin", "University of Lisbon"),
    ("University of Porto", "University of Coimbra", "NOVA University Lisbon", "University of Minho", "University of Aveiro", "ISCTE – University Institute of Lisbon", "University of Algarve", "University of Athens"),
    ("Aristotle University of Thessaloniki", "National Technical University of Athens", "University of Crete", "University of Patras", "University of Ioannina", "University of Thessaly", "University of the Aegean", "KAIST"),
    ("POSTECH", "Sungkyunkwan University", "Hanyang University", "Kyung Hee University", "Waseda University", "Tokyo Institute of Technology", "University of Tsukuba", "Hiroshima University"),
    ("Kobe University", "Chiba University", "Kanazawa University", "Jawaharlal Nehru University", "University of Madras", "University of Hyderabad", "Panjab University", "Indian Institute of Technology Madras"),
    ("Indian Institute of Technology Kanpur", "Indian Institute of Technology Kharagpur", "Indian Institute of Technology Roorkee", "University of Cape Coast", "University of Ghana", "Makerere University", "University of Nairobi", "University of Ibadan"),
    ("Obafemi Awolowo University", "University of Lagos", "Addis Ababa University", "University of Khartoum", "University of Botswana", "University of Zambia", "University of Zimbabwe", "Eduardo Mondlane University"),
    ("University of Dar es Salaam", "University of Rwanda", "American University in Cairo", "Alexandria University", "Ain Shams University", "Mansoura University", "Assiut University", "University of Jordan"),
    ("Jordan University of Science and Technology", "Sultan Qaboos University", "United Arab Emirates University", "Khalifa University", "University of Sharjah", "Kuwait University", "University of Bahrain", "University of Baghdad"),
    ("University of Tehran", "Sharif University of Technology", "Amirkabir University of Technology", "University of Isfahan", "Ferdowsi University of Mashhad", "University of Tabriz", "Bogazici University", "Middle East Technical University"),
    ("Istanbul Technical University", "Ankara University", "Istanbul University", "Hacettepe University", "Koç University", "Sabancı University", "University of Bucharest", "Babeș-Bolyai University"),
    ("University of Sofia", "Comenius University Bratislava", "University of Sarajevo", "University of Pristina", "University of Montenegro", "University of Malta", "University of Cyprus", "University of Luxembourg"),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.44.52 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *parent.SOURCE_FILES,
            "src/deepwide_agent/v24447_third_source_entropy_to_decision.py",
            "src/deepwide_agent/v24448_serialized_third_source_envelope.py",
            "scripts/v24449_third_source_external_projection.py",
            "src/deepwide_agent/v24450_timed_third_source_runner.py",
            "scripts/audit_v24451_third_source_timing_build.py",
            "tests/test_v24447_third_source_entropy_to_decision.py",
            "tests/test_v24448_serialized_third_source_envelope.py",
            "tests/test_v24449_third_source_external_projection.py",
            "tests/test_v24450_timed_third_source_runner.py",
            "tests/test_audit_v24451_third_source_timing_build.py",
            RUNNER_MARKER,
            "tests/test_v24452_third_source_timing_external_gate.py",
        )
    )
)
TEST_FILES = (
    "tests/test_v24308_child_exit_observability.py",
    "tests/test_v24309_runner_exit_integration.py",
    "tests/test_v24397_failure_observability.py",
    "tests/test_v24447_third_source_entropy_to_decision.py",
    "tests/test_v24448_serialized_third_source_envelope.py",
    "tests/test_v24449_third_source_external_projection.py",
    "tests/test_v24450_timed_third_source_runner.py",
    "tests/test_audit_v24451_third_source_timing_build.py",
    "tests/test_v24452_third_source_timing_external_gate.py",
)
SECRET = parent.SECRET
OPAQUE = parent.OPAQUE
URL = parent.URL
PROTOCOL_KEYS = parent.PROTOCOL_KEYS
PROTOCOL_AUTHORIZATION_KEYS = frozenset(
    {
        "one_fresh_third_source_timing_external_probe_design",
        "external_probe_launch",
        "benchmark_launch",
        "paired_dev64_or_exact220",
        "evaluator",
        "leaderboard_or_sota",
    }
)
LAUNCH_AUTHORIZATION_KEYS = frozenset(
    {
        "one_fresh_third_source_timing_external_probe_launch",
        "benchmark_launch",
        "paired_dev64_or_exact220",
        "evaluator",
    }
)

_ordinary = parent._ordinary
_read = parent._read
_sealed = parent._sealed
publish = parent.publish
_write_new = parent._write_new
_git = parent._git
_future = parent._future
_port_listening = parent._port_listening
_environment = parent._environment


def _build_parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    if (
        value.get("role") != "v24451_third_source_timing_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "fresh_third_source_timing_external_probe_design"
        )
        is not True
        or any(
            value.get("authorization", {}).get(name) is not False
            for name in (
                "external_probe_launch",
                "old_v24445_rerun",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.52 build parent drifted")
    return value


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = parent._ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.44.52 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _fresh_entity_vector_valid() -> bool:
    current = {
        entity
        for question in QUESTIONS
        for entity in parent._question_entity_vector(question)
    }
    populations = (
        parent.population_1,
        parent.population_2,
        parent.population_3,
        parent.population_4,
        parent.population_5,
        parent.population_6,
        parent.population_7,
        parent.population_8,
        parent.population_9,
        parent.population_10,
        parent.population_11,
        parent.population_12,
        parent.population_13,
        parent.population_14,
        parent,
    )
    prior_questions = tuple(
        question for population in populations for question in population.QUESTIONS
    )
    prior = {
        entity
        for question in prior_questions
        for entity in parent._question_entity_vector(question)
    }
    current_canonical = {parent._canonical_entity(entity) for entity in current}
    prior_canonical = {parent._canonical_entity(entity) for entity in prior}
    return (
        len(current) == 128
        and len(current_canonical) == 128
        and len(prior_questions) == 236
        and len(prior) == 1888
        and len(prior_canonical) == 1888
        and current.isdisjoint(prior)
        and current_canonical.isdisjoint(prior_canonical)
    )


def neutral_task(ordinal: int) -> dict[str, str]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= SELECTED
    ):
        raise ValueError("V2.44.52 neutral ordinal is invalid")
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
        f"{PROTOCOL_ID}|third-source-entropy|{ordinal}".encode("utf-8")
    ).hexdigest()


def _task_contract() -> dict[str, Any]:
    return {
        "selected": SELECTED,
        "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
        "fresh_128_entity_vector_exact_and_canonical_disjoint_from_all_fifteen_prior_external_populations": _fresh_entity_vector_valid(),
        "prior_external_entity_count": 1888,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_content_hash_persisted": False,
    }


def _mechanism_contract() -> dict[str, Any]:
    return {
        "third_source_policy": THIRD_SOURCE_POLICY_ID,
        "serialized_third_source_policy": SERIALIZED_THIRD_SOURCE_POLICY_ID,
        "timed_runner_policy": TIMED_RUNNER_POLICY_ID,
        "active_source_cap": MAXIMUM_ACTIVE_SOURCES,
        "parent_fetch_cap": 10,
        "total_fetch_cap": MAXIMUM_TOTAL_FETCHES,
        "additional_fetch_cap": 1,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_provider_search_calls": 0,
        "safe_change_thresholds_preserved": True,
        "single_complete_envelope_and_terminal_artifact_validation": True,
        "projection_consumes_only_validated_content_free_receipts": True,
        "child_validation_projection_timings_nonoverlapping": True,
        "failure_as_zero_projection": True,
        "minimum_third_source_safe_change_tasks": GATES[
            "minimum_third_source_safe_change_tasks"
        ],
        "minimum_third_source_decision_credit_nats": GATES[
            "minimum_third_source_decision_credit_nats"
        ],
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
        "maximum_provider_effect_seconds": MAXIMUM_PROVIDER_EFFECT_SECONDS,
        "model_calls": 3,
        "maximum_logical_search_queries": 5,
        "maximum_hosted_search_batches": 3,
        "parent_fetch_targets": 10,
        "additional_fetch_targets": 1,
        "total_fetch_targets": 11,
        "single_batch_no_resume_retry_skip_or_selective_rerun": True,
    }


def _source_policy() -> dict[str, bool]:
    return {
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
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
        "frozen_parent_active_lead_ranking_reused": True,
        "next_source_disjoint_lead_only": True,
        "additional_provider_search_calls": 0,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_third_source_timing_external_probe_design": True,
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
        raise RuntimeError("V2.44.52 external entity vector overlaps its parents")
    if require_pristine and not _future(
        root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.44.52 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24452_third_source_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "historical_capacity_reference": parent._capacity_reference(root),
        "scope": "fresh_nonbenchmark_third_source_entropy_to_decision_timing_gate",
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
    if any(
        task["opaque_id"] in encoded or task["question"] in encoded for task in tasks
    ):
        raise RuntimeError("V2.44.52 protocol persisted task content")
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = protocol.get("surface_manifest")
    seeds = [partition_seed(index) for index in range(1, SELECTED + 1)]
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    authorization = protocol.get("authorization")
    encoded = json.dumps(protocol, ensure_ascii=False)
    if (
        set(protocol) != PROTOCOL_KEYS
        or protocol.get("artifact_version") != 1
        or protocol.get("role") != "v24452_third_source_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or isinstance(protocol.get("created_at_unix"), bool)
        or not isinstance(protocol.get("created_at_unix"), int)
        or protocol["created_at_unix"] < 0
        or protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or protocol.get("historical_capacity_reference")
        != parent._capacity_reference(root)
        or protocol.get("scope")
        != "fresh_nonbenchmark_third_source_entropy_to_decision_timing_gate"
        or protocol.get("task_contract") != _task_contract()
        or protocol.get("mechanism") != _mechanism_contract()
        or protocol.get("provider") != _provider_contract()
        or protocol.get("budget") != _budget_contract()
        or protocol.get("gates") != GATES
        or protocol.get("discovery_partition") != _discovery_contract(seeds)
        or protocol.get("lease") != _lease_contract()
        or protocol.get("source_policy") != _source_policy()
        or not isinstance(authorization, Mapping)
        or set(authorization) != PROTOCOL_AUTHORIZATION_KEYS
        or dict(authorization) != _protocol_authorization()
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or not _fresh_entity_vector_valid()
        or any(
            task["opaque_id"] in encoded or task["question"] in encoded
            for task in tasks
        )
        or SECRET.search(encoded)
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.44.52 protocol drifted")
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
    privileged_accesses, evaluator_imports = build_audit.base._ast_findings(
        Path(RUNNER_MARKER)
    )
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
    if privileged_accesses:
        findings.append("privileged_field_access_in_v24452_runtime")
    if evaluator_imports:
        findings.append("evaluator_import_in_v24452_runtime")
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
        "role": "v24452_third_source_external_preactivation_audit",
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
        "privileged_field_accesses": privileged_accesses,
        "evaluator_imports": evaluator_imports,
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
            "one_fresh_third_source_timing_external_probe_launch": not findings,
            "benchmark_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.44.52 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    authorization = value.get("authorization")
    checks = value.get("checks")
    provenance = value.get("provenance")
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "checks",
        "protected_watchers",
        "privileged_field_accesses",
        "evaluator_imports",
        "findings",
        "audit_valid",
        "launch_authorized",
        "provenance",
        "authorization",
        "audit_payload_sha256",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24452_third_source_external_preactivation_audit"
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
        or set(authorization) != LAUNCH_AUTHORIZATION_KEYS
        or authorization.get("one_fresh_third_source_timing_external_probe_launch")
        is not True
        or any(
            authorization.get(name) is not False
            for name in ("benchmark_launch", "paired_dev64_or_exact220", "evaluator")
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.52 preaudit drifted")
    validate_protocol(root)
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
        "role": "v24452_third_source_external_activation",
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
            "one_fresh_third_source_timing_external_probe_launch": not findings,
            "benchmark_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.44.52 activation failed")
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, ACTIVATION)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "findings",
        "launch_authorized",
        "protocol_sha256",
        "preactivation_audit_sha256",
        "surface_manifest_sha256",
        "selected",
        "executor_count",
        "model_slot_cap",
        "protected_watchers",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "authorization",
        "activation_payload_sha256",
    }
    authorization = value.get("authorization")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24452_third_source_external_activation"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value["created_at_unix"] < 0
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
        or set(authorization) != LAUNCH_AUTHORIZATION_KEYS
        or authorization.get("one_fresh_third_source_timing_external_probe_launch")
        is not True
        or any(
            authorization.get(name) is not False
            for name in ("benchmark_launch", "paired_dev64_or_exact220", "evaluator")
        )
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.44.52 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.44.52 execution surface is not pristine")
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
        "role": "v24452_third_source_external_execution_start",
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
        raise RuntimeError("V2.44.52 execution start failed: " + ",".join(findings))
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, EXECUTION_START)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "findings",
        "execution_authorized",
        "activation_base_commit",
        "target_main_at_start",
        "protocol_sha256",
        "activation_sha256",
        "selected",
        "executor_count",
        "model_slot_cap",
        "protected_watchers",
        "api_called_before_execution_start",
        "runtime_input_exactly_opaque_id_and_question",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_or_evaluator_authorized",
        "execution_start_payload_sha256",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24452_third_source_external_execution_start"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value["created_at_unix"] < 0
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
        raise RuntimeError("V2.44.52 execution start drifted")
    validate_activation(root)
    return value


def _child(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal)
    task = neutral_task(ordinal)
    output_root = Path(args.output_root)
    directory = Path(args.directory)

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

        run_and_persist_v24447_task(
            task,
            model_factory=model_factory,
            search_factory=search_factory,
            partition_seed_sha256=partition_seed(ordinal),
            limits=LIMITS,
            monotonic=time.monotonic,
            expected_model_cap=MODEL_SLOT_CAP,
            writer=lambda name, value: _write_new(directory / name, value),
        )

    from deepwide_agent.v24309_runner_exit_integration import run_child_with_terminal_receipt

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
    outcome = run_timed_observed_subprocess(
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
    )
    return {
        "mechanism": outcome.mechanism_projection,
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
        and mechanism.get("third_source_validated_once_tasks") == SELECTED
        and mechanism.get("all_third_source_threshold_partitions_exact") is True
        and mechanism.get("all_third_source_effects_conserved") is True
        and mechanism.get("all_third_source_source_policies_attested") is True
        and observation.get("selected") == SELECTED
        and observation.get("exact_ordinal_vector") is True
        and observation.get("success_tasks") == SELECTED
        and observation.get("failure_tasks") == 0
        and observation.get("fully_observed_effect_tasks") == SELECTED
        and timing.get("selected") == SELECTED
        and timing.get("exact_ordinal_vector") is True
        and timing.get("parent_success_tasks") == SELECTED
        and timing.get("validation_invocations") == SELECTED
        and timing.get("projection_invocations") == SELECTED
        and timing.get("complete_validation_once_tasks") == SELECTED
        and timing.get("validated_capability_projection_tasks") == SELECTED
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


def _diagnostic_route(
    mechanism: Mapping[str, Any],
    diagnostic_complete: bool,
    reliability_passed: bool,
    latency_passed: bool,
) -> str:
    if not diagnostic_complete:
        return "runtime_validation_or_observability_repair"
    if int(mechanism.get("third_source_total_candidates", 0)) == 0:
        return "frozen_lead_coverage_successor"
    if int(mechanism.get("third_source_total_usable_pages", 0)) == 0:
        return "third_source_fetch_yield_successor"
    if (
        int(mechanism.get("third_source_safe_change_tasks", 0)) == 0
        or float(mechanism.get("third_source_decision_credit_total_nats", 0.0))
        <= 0.0
    ):
        return "entropy_to_decision_threshold_successor"
    if not reliability_passed:
        return "provider_or_fetch_reliability_successor"
    if not latency_passed:
        return "latency_stage_capacity_successor"
    return "fresh_paired_dev64_design"


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    mechanism = copied.get("mechanism_aggregate")
    observation = copied.get("observation_aggregate")
    timing = copied.get("stage_timing_aggregate")
    if not all(isinstance(item, Mapping) for item in (mechanism, observation, timing)):
        raise RuntimeError("V2.44.52 result aggregate is absent")
    projection.validate_aggregate(mechanism, GATES)
    validate_observation_aggregate(observation, expected_selected=SELECTED)
    validate_stage_timing_aggregate(timing)
    diagnostic = _diagnostic_complete(mechanism, observation, timing)
    reliability = _reliability_passed(observation)
    batch = copied.get("batch_wall_seconds")
    latency = (
        isinstance(batch, (int, float))
        and not isinstance(batch, bool)
        and math.isfinite(float(batch))
        and 0 <= float(batch) <= BATCH_WALL_CEILING_SECONDS
    )
    encoded = json.dumps(copied, ensure_ascii=False)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "selected",
        "executor_count",
        "model_slot_cap",
        "batch_wall_seconds",
        "mechanism_aggregate",
        "observation_aggregate",
        "stage_timing_aggregate",
        "mechanism_failure_as_zero_rows",
        "mechanism_passed",
        "reliability_passed",
        "latency_passed",
        "diagnostic_complete",
        "passed",
        "temporary_execution_directory_remaining",
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "official_evaluator_called",
        "resume_retry_skip_or_revaluation",
        "provenance",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24452_third_source_external_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied["created_at_unix"] < 0
        or copied.get("selected") != SELECTED
        or copied.get("executor_count") != EXECUTOR_COUNT
        or copied.get("model_slot_cap") != MODEL_SLOT_CAP
        or copied.get("mechanism_failure_as_zero_rows")
        != observation.get("failure_tasks")
        or copied.get("mechanism_passed") is not mechanism.get("passed")
        or copied.get("reliability_passed") is not reliability
        or copied.get("latency_passed") is not latency
        or copied.get("diagnostic_complete") is not diagnostic
        or copied.get("passed")
        is not (
            diagnostic
            and mechanism.get("passed") is True
            and reliability
            and latency
        )
        or copied.get("temporary_execution_directory_remaining") is not False
        or copied.get("task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted")
        is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or copied.get("official_evaluator_called") is not False
        or copied.get("resume_retry_skip_or_revaluation") is not False
        or not isinstance(copied.get("provenance"), Mapping)
        or set(copied["provenance"])
        != {
            "protocol_sha256",
            "preactivation_audit_sha256",
            "activation_sha256",
            "execution_start_sha256",
            "surface_manifest_sha256",
        }
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(item)) is None
            for item in copied["provenance"].values()
        )
        or seal != payload_sha256(unsigned)
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
    ):
        raise RuntimeError("V2.44.52 public result drifted or contains content")
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
        raise RuntimeError("V2.44.52 result/git surface is not ready")
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            directories = []
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
            mechanism = projection.aggregate_tasks(
                [item["mechanism"] for item in outcomes], GATES
            )
            observation = aggregate_observations(
                [item["observation"] for item in outcomes], selected=SELECTED
            )
            timing = aggregate_stage_timings(
                [item["timing"] for item in outcomes], selected=SELECTED
            )
            diagnostic = _diagnostic_complete(mechanism, observation, timing)
        latency = batch_wall <= BATCH_WALL_CEILING_SECONDS
        reliability = _reliability_passed(observation)
        value = {
            "artifact_version": 1,
            "role": "v24452_third_source_external_result",
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
            "mechanism_passed": mechanism["passed"],
            "reliability_passed": reliability,
            "latency_passed": latency,
            "diagnostic_complete": diagnostic,
            "passed": diagnostic and mechanism["passed"] and reliability and latency,
            "temporary_execution_directory_remaining": False,
            "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
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
        raise RuntimeError("V2.44.52 protected watcher identity drifted")
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = validate_public_result(_read(root, RESULT))
    mechanism = result["mechanism_aggregate"]
    route = _diagnostic_route(
        mechanism,
        result["diagnostic_complete"],
        result["reliability_passed"],
        result["latency_passed"],
    )
    value = {
        "artifact_version": 1,
        "role": "v24452_third_source_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "fresh_third_source_external_mechanism_go"
        if result["passed"]
        else "fresh_third_source_external_no_go",
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
            "fresh_nonbenchmark_mechanism_and_stage_timing_measured": True,
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
    validate_decision(root, value=value)
    return value


def validate_decision(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    decision = dict(value) if value is not None else _read(root, DECISION)
    result = validate_public_result(_read(root, RESULT))
    route = _diagnostic_route(
        result["mechanism_aggregate"],
        result["diagnostic_complete"],
        result["reliability_passed"],
        result["latency_passed"],
    )
    authorization = decision.get("authorization")
    claim_scope = decision.get("claim_scope")
    unsigned = dict(decision)
    seal = unsigned.pop("decision_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "passed",
        "diagnostic_route",
        "provenance",
        "claim_scope",
        "authorization",
        "decision_payload_sha256",
    }
    if (
        set(decision) != expected
        or decision.get("artifact_version") != 1
        or decision.get("role") != "v24452_third_source_external_decision"
        or decision.get("protocol_id") != PROTOCOL_ID
        or isinstance(decision.get("created_at_unix"), bool)
        or not isinstance(decision.get("created_at_unix"), int)
        or decision["created_at_unix"] < 0
        or decision.get("status")
        != (
            "fresh_third_source_external_mechanism_go"
            if result["passed"]
            else "fresh_third_source_external_no_go"
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
        or not isinstance(claim_scope, Mapping)
        or claim_scope
        != {
            "fresh_nonbenchmark_mechanism_and_stage_timing_measured": True,
            "benchmark_quality_measured": False,
            "future_population_or_sota_supported": False,
        }
        or not isinstance(authorization, Mapping)
        or set(authorization)
        != {
            "diagnostic_successor_design",
            "fresh_paired_dev64_design",
            "fresh_paired_dev64_launch",
            "new_exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or authorization.get("diagnostic_successor_design")
        is not (not result["passed"])
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
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.52 decision drifted")
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
        "role": "v24452_third_source_external_postresult_audit",
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
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
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
    validate_postaudit(root, value=value)
    return value


def validate_postaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else _read(root, POSTAUDIT)
    decision = validate_decision(root)
    findings = audit.get("findings")
    authorization = audit.get("authorization")
    unsigned = dict(audit)
    seal = unsigned.pop("audit_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "result_sha256",
        "decision_sha256",
        "decision_status",
        "diagnostic_route",
        "temporary_execution_directory_remaining",
        "shared_api_lease_active",
        "protected_watchers",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted",
        "network_model_search_fetch_or_evaluator_called_by_audit",
        "findings",
        "audit_valid",
        "authorization",
        "audit_payload_sha256",
    }
    expected_findings: list[str] = []
    if audit.get("shared_api_lease_active") is True:
        expected_findings.append("shared_api_lease_active")
    if audit.get("protected_watchers") != _read(root, EXECUTION_START).get(
        "protected_watchers"
    ):
        expected_findings.append("protected_watcher_identity_drifted")
    if (
        set(audit) != expected
        or audit.get("artifact_version") != 1
        or audit.get("role") != "v24452_third_source_external_postresult_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or isinstance(audit.get("created_at_unix"), bool)
        or not isinstance(audit.get("created_at_unix"), int)
        or audit["created_at_unix"] < 0
        or audit.get("result_sha256") != sha256(root / RESULT)
        or audit.get("decision_sha256") != sha256(root / DECISION)
        or audit.get("decision_status") != decision["status"]
        or audit.get("diagnostic_route") != decision["diagnostic_route"]
        or audit.get("temporary_execution_directory_remaining") is not False
        or not isinstance(audit.get("shared_api_lease_active"), bool)
        or audit.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or audit.get("task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted")
        is not False
        or audit.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or findings != expected_findings
        or audit.get("audit_valid") is not (not expected_findings)
        or not isinstance(authorization, Mapping)
        or set(authorization)
        != {
            "diagnostic_successor_design",
            "fresh_paired_dev64_design",
            "fresh_paired_dev64_launch",
            "new_exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
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
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.52 postresult audit drifted")
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
