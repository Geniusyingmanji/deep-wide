#!/usr/bin/env python3
"""Fresh benchmark-external gate for the V2.43.78--79 successor.

Sixteen fixed public-document tasks, with 128 entities disjoint from all
earlier external task populations, run once through two non-recursive search
batches, an 4+4 proposal partition, and candidate-conditioned selection of
one held-out verifier source per batch. Task-private text,
queries, URLs, pages, candidates, and verification records exist only in a
temporary directory and are replay-validated before deletion.  Only exact,
content-free aggregate counts and booleans persist.

No benchmark manifest, mapping, gold, label, evaluator, reward, or score
surface is opened or authorized.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections import Counter
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
from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
    run_observed_subprocess,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24379_adaptive_heldout_verifier_runner import (  # noqa: E402
    AdaptiveHeldoutDeadlineAwareNativeSearchClient,
    build_envelope,
    run_v24379_task,
    validate_envelope,
    validate_observed_bundle,
)
from deepwide_agent.v24378_adaptive_heldout_verifier_runtime import (  # noqa: E402
    POLICY_ID as ADAPTIVE_HELDOUT_RUNTIME_POLICY_ID,
)
from deepwide_agent.v24379_adaptive_heldout_verifier_runner import (  # noqa: E402
    POLICY_ID as ADAPTIVE_HELDOUT_RUNNER_POLICY_ID,
)
from scripts import v24345_semantic_active_natural_admission as population_1  # noqa: E402
from scripts import v24364_two_verifier_external_gate as population_2  # noqa: E402
from scripts import v24370_target_segment_external_gate as population_3  # noqa: E402
from scripts import v24374_batch_stratified_external_gate as population_4  # noqa: E402
from scripts import v24377_projection_safe_external_gate as prior_gate  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24381_fresh_adaptive_heldout_external_gate_v1"
PROTOCOL = Path(f"results/v24381_adaptive_heldout_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24381_adaptive_heldout_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24381_adaptive_heldout_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24381_adaptive_heldout_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24381_adaptive_heldout_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24381_adaptive_heldout_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24381_adaptive_heldout_external_postresult_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24380_adaptive_heldout_verifier_build_audit_v1_{DATE}.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_adaptive_heldout_verifier_entropy_gate"
RUNNER_MARKER = "scripts/v24381_adaptive_heldout_external_gate.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
SELECTED = 16
EXECUTOR_COUNT = 8
MODEL_SLOT_CAP = 2
TASK_WALL_SECONDS = 210
PARENT_TIMEOUT_SECONDS = 230
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
    "selected": SELECTED,
    "executor_count": EXECUTOR_COUNT,
    "model_slot_cap": MODEL_SLOT_CAP,
    "maximum_batch_wall_seconds": BATCH_WALL_CEILING_SECONDS,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 5,
    "maximum_fetch_helper_failures": 5,
    "maximum_deadline_exhausted_tasks": 0,
    "minimum_exact_two_batch_tasks": SELECTED,
    "minimum_zero_recursive_split_tasks": SELECTED,
    "minimum_full_proposal_partition_tasks": 12,
    "minimum_proposal_source_count_total": 96,
    "minimum_heldout_pool_tasks": 12,
    "minimum_parent_semantic_catalog_tasks": 12,
    "minimum_parent_candidate_tasks": 1,
    "minimum_selected_bound_candidate_tasks": 1,
    "minimum_selected_verifier_sources": 1,
    "minimum_hidden_verifier_pages": 1,
    "minimum_selected_verified_candidate_changes": 1,
    "minimum_utility_aligned_tasks": 1,
    "minimum_final_nonidentity_tasks": 1,
    "minimum_adaptive_retained_candidate_changed_cells": 1,
    "minimum_selected_proposal_entropy_nats": 1e-12,
    "minimum_utility_aligned_entropy_nats": 1e-12,
}
QUESTIONS = (
    "Use public web sources to return one Markdown table about Alpine Linux, Void Linux, Solus, Mageia, PCLinuxOS, Slackware, Rocky Linux, and AlmaLinux. The column names are: Linux distribution, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about OCaml, F Sharp, Crystal, Nim, Zig, Reason, Idris, and Elm. The column names are: Programming language, First appeared year. Return one table only.",
    "Use public web sources to return one Markdown table about Podman, Buildah, Skopeo, containerd, CRI-O, LXC, LXD, and rkt. The column names are: Container software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Apache Spark, Apache Flink, Apache Beam, Dask, Ray, Polars, Vaex, and Modin. The column names are: Data processing framework, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about pytest, JUnit, NUnit, RSpec, Mocha, Jasmine, Cypress, and Playwright. The column names are: Testing framework, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Gin, Echo, Fiber, Koa, Hapi, NestJS, Sanic, and Tornado. The column names are: Web framework, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Elasticsearch, Apache Solr, Meilisearch, Typesense, OpenSearch, Sphinx Search, Manticore Search, and Vespa. The column names are: Search software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about BorgBackup, Restic, Duplicati, Bacula, Amanda, UrBackup, Kopia, and Rclone. The column names are: Backup software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about VirtualBox, QEMU, Xen, KVM, VMware Workstation, Parallels Desktop, Proxmox VE, and bhyve. The column names are: Virtualization software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Alacritty, Kitty, WezTerm, Terminator, Tilix, Konsole, GNOME Terminal, and iTerm2. The column names are: Terminal emulator, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about GitLab, Gogs, Gitea, Phorge, OneDev, SourceHut, Azure Repos, and AWS CodeCommit. The column names are: Source code hosting software or service, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Postman, Insomnia, SoapUI, Hoppscotch, Bruno, Paw, HTTPie, and cURL. The column names are: API development tool, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Joplin, Obsidian, Logseq, Zettlr, Standard Notes, Simplenote, Trilium Notes, and QOwnNotes. The column names are: Note taking software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about digiKam, darktable, RawTherapee, Shotwell, PhotoPrism, Immich, Piwigo, and Lychee. The column names are: Photo management software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about GNS3, ns-3, Mininet, CORE, EVE-NG, OMNeT++, Packet Tracer, and Containernet. The column names are: Network simulation software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about n8n, Apache NiFi, Prefect, Dagster, Luigi, Kestra, Temporal, and Flyte. The column names are: Workflow automation software, Initial release year. Return one table only.",
)
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24275_hard_deadline_fetch.py",
    "src/deepwide_agent/v24280_task_union_single_shot.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24320_forward_contract.py",
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24333_programmatic_support_catalog.py",
    "src/deepwide_agent/v24334_support_catalog_revision_gate.py",
    "src/deepwide_agent/v24335_programmatic_support_runtime.py",
    "src/deepwide_agent/v24339_active_evidence_support.py",
    "src/deepwide_agent/v24341_semantic_evidence_projection.py",
    "src/deepwide_agent/v24342_semantic_active_runtime.py",
    "src/deepwide_agent/v24348_structural_table_normalizer.py",
    "src/deepwide_agent/v24349_structural_semantic_runtime.py",
    "src/deepwide_agent/v24354_explicit_partition_utility.py",
    "src/deepwide_agent/v24355_explicit_partition_runtime.py",
    "src/deepwide_agent/v24358_two_batch_discovery.py",
    "src/deepwide_agent/v24362_two_verifier_partition_runtime.py",
    "src/deepwide_agent/v24363_two_verifier_partition_runner.py",
    "src/deepwide_agent/v24365_entity_segment_projection.py",
    "src/deepwide_agent/v24366_target_segment_utility.py",
    "src/deepwide_agent/v24367_target_segment_verifier_runtime.py",
    "src/deepwide_agent/v24368_target_segment_verifier_runner.py",
    "src/deepwide_agent/v24371_batch_stratified_verifier_runtime.py",
    "src/deepwide_agent/v24372_batch_stratified_verifier_runner.py",
    "src/deepwide_agent/v24378_adaptive_heldout_verifier_runtime.py",
    "src/deepwide_agent/v24379_adaptive_heldout_verifier_runner.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/v24345_semantic_active_natural_admission.py",
    "scripts/v24374_batch_stratified_external_gate.py",
    "scripts/v24375_batch_stratified_projection_recovery.py",
    "scripts/audit_v24376_projection_recovery_build.py",
    "scripts/v24377_projection_safe_external_gate.py",
    "scripts/v24381_adaptive_heldout_external_gate.py",
    "tests/test_v24342_semantic_active_runtime.py",
    "tests/test_v24343_semantic_active_runner.py",
    "tests/test_v24365_entity_segment_projection.py",
    "tests/test_v24366_target_segment_utility.py",
    "tests/test_v24367_target_segment_verifier_runtime.py",
    "tests/test_v24368_target_segment_verifier_runner.py",
    "tests/test_v24371_batch_stratified_verifier_runtime.py",
    "tests/test_v24372_batch_stratified_verifier_runner.py",
    "tests/test_v24374_batch_stratified_external_gate.py",
    "tests/test_v24375_batch_stratified_projection_recovery.py",
    "tests/test_v24378_adaptive_heldout_verifier_runtime.py",
    "tests/test_v24379_adaptive_heldout_verifier_runner.py",
    "tests/test_v24381_adaptive_heldout_external_gate.py",
)
TEST_FILES = (
    "tests/test_v24365_entity_segment_projection.py",
    "tests/test_v24366_target_segment_utility.py",
    "tests/test_v24367_target_segment_verifier_runtime.py",
    "tests/test_v24371_batch_stratified_verifier_runtime.py",
    "tests/test_v24372_batch_stratified_verifier_runner.py",
    "tests/test_v24375_batch_stratified_projection_recovery.py",
    "tests/test_v24378_adaptive_heldout_verifier_runtime.py",
    "tests/test_v24379_adaptive_heldout_verifier_runner.py",
    "tests/test_v24381_adaptive_heldout_external_gate.py",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
URL = re.compile(r"https?://", re.IGNORECASE)
COMPLETION_KINDS = frozenset(
    {"paired", "identity_no_reserve", "identity_fallback", "None"}
)
VERIFICATION_STATUSES = frozenset(
    {
        "verified_candidate",
        "no_independent_candidate_support",
        "verifier_supports_baseline",
        "independent_conflict",
        "nonpositive_proposal_entropy",
    }
)
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
PROTOCOL_AUTHORIZATION_KEYS = frozenset(
    {
        "one_fresh_external_adaptive_heldout_probe_design",
        "external_probe_launch",
        "benchmark_launch",
        "additional_dev64_or_exact220",
        "evaluator",
        "leaderboard_or_sota",
    }
)
LAUNCH_AUTHORIZATION_KEYS = frozenset(
    {
        "one_fresh_external_adaptive_heldout_probe_launch",
        "benchmark_launch",
        "additional_dev64_or_exact220",
        "evaluator",
    }
)


_ordinary = prior_gate._ordinary
_read = prior_gate._read
_sealed = prior_gate._sealed
publish = prior_gate.publish
_write_new = prior_gate._write_new
_git = prior_gate._git
_future = prior_gate._future
_port_listening = prior_gate._port_listening
_environment = prior_gate._environment
_integer = prior_gate._integer
_number = prior_gate._number


def _question_entity_vector(question: str) -> tuple[str, ...]:
    prefix = "Use public web sources to return one Markdown table about "
    suffix = ". The column names are:"
    if not question.startswith(prefix) or suffix not in question:
        raise ValueError("V2.43.81 external task template drifted")
    body = question[len(prefix) : question.index(suffix)]
    values = tuple(
        item.strip().casefold()
        for item in body.replace(", and ", ", ").split(", ")
    )
    if len(values) != 8 or any(not item for item in values):
        raise ValueError("V2.43.81 external entity vector drifted")
    return values


def _fresh_entity_vector_valid() -> bool:
    current = {
        entity for question in QUESTIONS for entity in _question_entity_vector(question)
    }
    prior_questions = tuple(
        question
        for population in (
            population_1.QUESTIONS,
            population_2.QUESTIONS,
            population_3.QUESTIONS,
            population_4.QUESTIONS,
            prior_gate.QUESTIONS,
        )
        for question in population
    )
    prior = {
        entity
        for question in prior_questions
        for entity in _question_entity_vector(question)
    }
    return (
        len(current) == 8 * SELECTED
        and len(prior_questions) == 76
        and len(prior) == 608
        and current.isdisjoint(prior)
    )


def neutral_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED:
        raise ValueError("V2.43.81 neutral ordinal is invalid")
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
        f"{PROTOCOL_ID}|target-segment-eight-plus-two|{ordinal}".encode("utf-8")
    ).hexdigest()


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.43.81 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    if (
        value.get("role") != "v24380_adaptive_heldout_verifier_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("fresh_external_gate_design")
        is not True
        or value.get("authorization", {}).get("fresh_external_gate_launch")
        is not False
        or value.get("authorization", {}).get(
            "same_v24377_task_rerun_or_revaluation"
        )
        is not False
        or value.get("authorization", {}).get("new_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.81 parent audit drifted")
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    LIMITS.validate()
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    seeds = [partition_seed(index) for index in range(1, SELECTED + 1)]
    fresh_entities = _fresh_entity_vector_valid()
    if not fresh_entities:
        raise RuntimeError("V2.43.81 external entity vector overlaps its parents")
    if require_pristine and not _future(
        root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.81 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24381_adaptive_heldout_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "scope": "fresh_benchmark_external_adaptive_heldout_verifier_entropy_gate",
        "task_contract": {
            "selected": SELECTED,
            "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
            "task_vector_validated_in_memory_before_protocol": len(tasks) == SELECTED,
            "fresh_128_entity_vector_disjoint_from_all_prior_external_gates": fresh_entities,
            "synthetic_identifiers_not_selected_from_benchmark": True,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "question_opaque_id_or_content_hash_persisted": False,
        },
        "mechanism": {
            "adaptive_heldout_runtime_policy": ADAPTIVE_HELDOUT_RUNTIME_POLICY_ID,
            "adaptive_heldout_runner_policy": ADAPTIVE_HELDOUT_RUNNER_POLICY_ID,
            "projection_reads_v24379_envelope_v24378_result_v24349_parent": True,
            "three_stage_entropy_and_verification_accounting": True,
            "verifier_can_only_retain_or_revert_frozen_candidate": True,
            "minimum_adaptive_retained_candidate_changed_cells": GATES[
                "minimum_adaptive_retained_candidate_changed_cells"
            ],
            "selected_verification_status_counts_persisted_content_free": True,
        },
        "discovery_partition": {
            "logical_query_count": 4,
            "deterministic_batch_query_counts": [2, 2],
            "recursive_query_local_split_allowed": False,
            "full_capacity_proposal_batch_host_counts": [4, 4],
            "full_capacity_verifier_batch_host_counts": [1, 1],
            "proposal_selection_precedes_fetch_candidate_and_entropy": True,
            "verifier_selection_follows_candidate_and_support_freeze": True,
            "verifier_selection_uses_frozen_target_and_visible_title_url_only": True,
            "seed_sha256_vector": seeds,
            "seed_depends_only_on_protocol_and_fixed_ordinal": True,
            "proposal_source_cap": 8,
            "verifier_source_cap": 2,
            "selected_fetch_source_cap": 10,
            "parent_support_set_and_evidence_ids_reused_without_rebuild": True,
            "hidden_verifiers_can_only_retain_or_revert": True,
            "same_target_independent_conflict_reverts": True,
            "cross_target_relation_cannot_create_conflict": True,
        },
        "provider": {
            "proxy_url": f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "max_retries_per_batch": 2,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
        },
        "budget": {
            "task_wall_seconds": TASK_WALL_SECONDS,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "model_calls": 3,
            "logical_search_queries": 4,
            "hosted_search_batches": 2,
            "fetch_targets_total": 10,
            "page_characters": LIMITS.page_chars,
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
            "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_fresh_external_adaptive_heldout_probe_design": True,
            "external_probe_launch": False,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
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
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    seeds = [partition_seed(index) for index in range(1, SELECTED + 1)]
    discovery = protocol.get("discovery_partition", {})
    mechanism = protocol.get("mechanism", {})
    authorization = protocol.get("authorization")
    source_policy = protocol.get("source_policy")
    if (
        set(protocol) != PROTOCOL_KEYS
        or protocol.get("artifact_version") != 1
        or protocol.get("role") != "v24381_adaptive_heldout_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or isinstance(protocol.get("created_at_unix"), bool)
        or not isinstance(protocol.get("created_at_unix"), int)
        or protocol["created_at_unix"] < 0
        or protocol.get("gates") != GATES
        or protocol.get("task_contract", {}).get("selected") != SELECTED
        or protocol.get("task_contract", {}).get("fixed_ordinal_vector")
        != list(range(1, SELECTED + 1))
        or protocol.get("task_contract", {}).get(
            "task_vector_validated_in_memory_before_protocol"
        )
        is not (len(tasks) == SELECTED)
        or protocol.get("task_contract", {}).get(
            "fresh_128_entity_vector_disjoint_from_all_prior_external_gates"
        )
        is not _fresh_entity_vector_valid()
        or not _fresh_entity_vector_valid()
        or mechanism.get("adaptive_heldout_runtime_policy")
        != ADAPTIVE_HELDOUT_RUNTIME_POLICY_ID
        or mechanism.get("adaptive_heldout_runner_policy")
        != ADAPTIVE_HELDOUT_RUNNER_POLICY_ID
        or mechanism.get(
            "projection_reads_v24379_envelope_v24378_result_v24349_parent"
        )
        is not True
        or mechanism.get("three_stage_entropy_and_verification_accounting")
        is not True
        or mechanism.get("verifier_can_only_retain_or_revert_frozen_candidate")
        is not True
        or mechanism.get("minimum_adaptive_retained_candidate_changed_cells")
        != GATES["minimum_adaptive_retained_candidate_changed_cells"]
        or mechanism.get("selected_verification_status_counts_persisted_content_free")
        is not True
        or discovery.get("seed_sha256_vector") != seeds
        or len(set(seeds)) != SELECTED
        or discovery.get("logical_query_count") != 4
        or discovery.get("deterministic_batch_query_counts") != [2, 2]
        or discovery.get("recursive_query_local_split_allowed") is not False
        or discovery.get("full_capacity_proposal_batch_host_counts") != [4, 4]
        or discovery.get("full_capacity_verifier_batch_host_counts") != [1, 1]
        or discovery.get("proposal_selection_precedes_fetch_candidate_and_entropy")
        is not True
        or discovery.get("verifier_selection_follows_candidate_and_support_freeze")
        is not True
        or discovery.get("verifier_selection_uses_frozen_target_and_visible_title_url_only")
        is not True
        or discovery.get("proposal_source_cap") != 8
        or discovery.get("verifier_source_cap") != 2
        or discovery.get("selected_fetch_source_cap") != 10
        or discovery.get("same_target_independent_conflict_reverts") is not True
        or discovery.get("cross_target_relation_cannot_create_conflict") is not True
        or protocol.get("provider", {}).get("executor_count") != EXECUTOR_COUNT
        or protocol.get("provider", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or protocol.get("budget", {}).get("fetch_targets_total") != 10
        or protocol.get("budget", {}).get("hosted_search_batches") != 2
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or not isinstance(source_policy, Mapping)
        or set(source_policy)
        != {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read",
            "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted",
            "credential_value_read_persisted_hashed_or_emitted",
            "official_evaluator_called",
        }
        or any(source_policy.values())
        or not isinstance(authorization, Mapping)
        or set(authorization) != PROTOCOL_AUTHORIZATION_KEYS
        or authorization.get(
            "one_fresh_external_adaptive_heldout_probe_design"
        )
        is not True
        or any(
            authorization.get(key) is not False
            for key in PROTOCOL_AUTHORIZATION_KEYS
            if key != "one_fresh_external_adaptive_heldout_probe_design"
        )
        or protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.81 protocol drifted")
    _parent(root)
    return protocol


def _run_tests() -> dict[str, bool]:
    output: dict[str, bool] = {}
    for relative in TEST_FILES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-v"],
            cwd=ROOT,
            env=_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=360,
            check=False,
        )
        output[relative] = completed.returncode == 0
    return output


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    pristine = _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT))
    tests = _run_tests()
    port = _port_listening()
    lease = lease_observation(root, Path("/proc"))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    watchers = protected_watcher_snapshot()
    parent_watchers = _parent(root)["closure"]["protected_watchers"]
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not all(tests.values()):
        findings.append("focused_tests_failed")
    if not port:
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
        "role": "v24381_adaptive_heldout_external_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "fresh_external_task_and_adaptive_heldout_vector_frozen": True,
            "focused_tests": tests,
            "keyless_proxy_listening_without_api_request": port,
            "shared_api_lease_inactive": lease.get("active") is False,
            "protocol_commit_pushed": head == remote,
            "worktree_clean": clean,
            "future_surface_pristine": pristine,
            "protected_watchers_unchanged": watchers == parent_watchers,
            "benchmark_or_evaluator_surface_authorized": False,
        },
        "protected_watchers": watchers,
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
            "one_fresh_external_adaptive_heldout_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.81 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "checks",
        "protected_watchers",
        "findings",
        "audit_valid",
        "launch_authorized",
        "provenance",
        "authorization",
        "audit_payload_sha256",
    }
    authorization = value.get("authorization")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24381_adaptive_heldout_external_preactivation_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value["created_at_unix"] < 0
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("provenance", {}).get("protocol_sha256")
        != sha256(root / PROTOCOL)
        or not isinstance(authorization, Mapping)
        or set(authorization) != LAUNCH_AUTHORIZATION_KEYS
        or authorization.get("one_fresh_external_adaptive_heldout_probe_launch")
        is not True
        or any(
            authorization.get(name) is not False
            for name in (
                "benchmark_launch",
                "additional_dev64_or_exact220",
                "evaluator",
            )
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.81 preaudit drifted")
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
        "role": "v24381_adaptive_heldout_external_activation",
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
            "one_fresh_external_adaptive_heldout_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.81 activation failed")
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
        or value.get("role") != "v24381_adaptive_heldout_external_activation"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or not isinstance(authorization, Mapping)
        or set(authorization) != LAUNCH_AUTHORIZATION_KEYS
        or authorization.get("one_fresh_external_adaptive_heldout_probe_launch")
        is not True
        or any(
            authorization.get(name) is not False
            for name in (
                "benchmark_launch",
                "additional_dev64_or_exact220",
                "evaluator",
            )
        )
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.81 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.43.81 execution surface is not pristine")
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
        "role": "v24381_adaptive_heldout_external_execution_start",
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
        raise RuntimeError("V2.43.81 execution start failed: " + ",".join(findings))
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
        or value.get("role") != "v24381_adaptive_heldout_external_execution_start"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("api_called_before_execution_start") is not False
        or value.get("runtime_input_exactly_opaque_id_and_question") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_or_evaluator_authorized") is not False
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.43.81 execution-start drifted")
    validate_activation(root)
    return value


def _child(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal)
    task = neutral_task(ordinal)
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    result_path = directory / "result.json"
    model_path = directory / "model_slot_receipt.json"
    transport_path = directory / "transport_health.json"

    def action() -> None:
        deadline = time.monotonic() + TASK_WALL_SECONDS
        model = build_deadline_model(
            url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            model_name="gpt-5.6-sol",
            reasoning_effort="low",
            service_tier="priority",
            static_timeout_seconds=TASK_WALL_SECONDS,
            max_retries=2,
            slot_directory=Path(args.slots),
            output_root=output_root,
            slot_cap=MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
        )
        search = AdaptiveHeldoutDeadlineAwareNativeSearchClient(
            f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "gpt-5.6-sol",
            reasoning_effort="low",
            service_tier="priority",
            timeout=TASK_WALL_SECONDS,
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
        outcome = run_v24379_task(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed(ordinal),
            limits=LIMITS,
            monotonic=time.monotonic,
        )
        _write_new(model_path, outcome.model_slot_receipt)
        _write_new(transport_path, outcome.transport_health)
        _write_new(result_path, build_envelope(outcome))

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name="result.json",
        model_receipt_name="model_slot_receipt.json",
        transport_receipt_name="transport_health.json",
        terminal_name="child_terminal_receipt.json",
    )


TASK_CHECK_NAMES = (
    "parent_success",
    "all_parent_artifacts_valid",
    "effect_accounting_complete",
    "structural_shared_normalization",
    "two_batch_discovery_complete",
    "recursive_split_absent",
    "transport_retry_within_frozen_budget",
    "adaptive_partition_complete",
    "source_partition_disjoint",
    "proposal_and_selected_verifier_budget_safe",
    "hidden_verifier_prompt_excluded",
    "hidden_verifier_no_new_candidate",
    "parent_support_ids_reused",
    "adaptive_verifier_final_decision",
    "adaptive_retention_conservation",
    "verification_record_conservation",
    "selected_verification_conservation",
    "entropy_credit_conservation",
    "fetch_budget_transport_conserved",
    "model_slot_conserved",
    "private_replay_valid",
    "deadline_not_exhausted",
)


def _task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    proposal = int(value.get("proposal_source_count", -1))
    heldout = int(value.get("heldout_source_count", -1))
    verifier = int(value.get("selected_verifier_source_count", -1))
    verification_total = sum(
        int(value.get(name, -1))
        for name in (
            "verified_candidate_records",
            "no_independent_candidate_support_records",
            "verifier_supports_baseline_records",
            "independent_conflict_records",
            "nonpositive_proposal_entropy_records",
        )
    )
    selected_total = sum(
        int(value.get(name, -1))
        for name in (
            "selected_verified_candidate_changes",
            "selected_no_independent_candidate_support_changes",
            "selected_verifier_supports_baseline_changes",
            "selected_independent_conflict_changes",
            "selected_nonpositive_proposal_entropy_changes",
        )
    )
    return {
        "parent_success": value.get("parent_taxonomy") == "success",
        "all_parent_artifacts_valid": value.get("all_parent_artifacts_valid") is True,
        "effect_accounting_complete": value.get("effect_accounting_complete") is True,
        "structural_shared_normalization": value.get("structural_shared_normalization") is True,
        "two_batch_discovery_complete": (
            value.get("logical_query_count") == 4
            and value.get("discovery_batch_count") == 2
            and value.get("batch_logical_query_counts") == [2, 2]
            and value.get("single_shot_multi_query_chunks") == 2
        ),
        "recursive_split_absent": value.get("recursive_split_requests") == 0,
        "transport_retry_within_frozen_budget": (
            value.get("provider_search_call_count", 0)
            <= value.get("hosted_search_attempts", -1)
            <= 2 * value.get("discovery_batch_count", 0)
        ),
        "adaptive_partition_complete": (
            value.get("raw_batch_unique_host_counts")
            == [
                proposal_batch + heldout_batch
                for proposal_batch, heldout_batch in zip(
                    value.get("proposal_batch_host_counts", []),
                    value.get("heldout_batch_host_counts", []),
                    strict=True,
                )
            ]
            and value.get("four_queries_split_two_plus_two_before_candidate") is True
            and value.get("verifier_source_selection_after_candidate_and_support_freeze") is True
        ),
        "source_partition_disjoint": value.get("source_partition_disjoint") is True,
        "proposal_and_selected_verifier_budget_safe": (
            0 <= proposal <= 8
            and 0 <= verifier <= 2
            and heldout >= verifier
            and value.get("total_fetch_calls") <= 10
        ),
        "hidden_verifier_prompt_excluded": value.get("hidden_verifier_prompt_excluded") is True,
        "hidden_verifier_no_new_candidate": value.get("hidden_verifier_no_new_candidate") is True,
        "parent_support_ids_reused": value.get("parent_support_ids_reused") is True,
        "adaptive_verifier_final_decision": (
            value.get("target_segment_entity_boundary_enforced") is True
            and value.get("hidden_verifier_no_new_candidate") is True
        ),
        "adaptive_retention_conservation": (
            value.get("adaptive_retained_candidate_changed_cells")
            == value.get("preverification_candidate_changed_cells")
            - value.get("adaptive_reverted_candidate_changed_cells")
            and value.get("adaptive_added_candidate_changed_cells") == 0
            and value.get("hidden_verifier_reverted_cells")
            == value.get("preverification_candidate_changed_cells")
            - value.get("adaptive_retained_candidate_changed_cells")
        ),
        "verification_record_conservation": verification_total
        == value.get("verification_record_count"),
        "selected_verification_conservation": (
            selected_total == value.get("selected_exactly_bound_candidate_changes")
            and value.get("selection_resolution_count")
            + value.get("candidate_changes_without_declaration")
            == value.get("parent_candidate_changed_cells")
        ),
        "entropy_credit_conservation": (
            0.0
            <= float(value.get("utility_aligned_entropy_credit_nats", -1.0))
            <= float(value.get("selected_proposal_entropy_nats", -1.0)) + 1e-12
            <= float(value.get("proposal_support_entropy_total_nats", -1.0)) + 1e-12
        ),
        "fetch_budget_transport_conserved": (
            value.get("total_fetch_calls")
            == value.get("parent_fetch_calls") + value.get("hidden_verifier_fetch_calls")
            == value.get("hard_fetch_helper_calls") + value.get("fetch_deadline_rejections")
            and 0 <= int(value.get("total_fetch_calls", -1)) <= 10
        ),
        "model_slot_conserved": value.get("model_requests") == value.get("slot_acquisitions"),
        "private_replay_valid": value.get("private_replay_valid") is True,
        "deadline_not_exhausted": value.get("deadline_exhausted") is False,
    }


def _task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("V2.43.81 successful parent is missing its envelope")
    validated_parent = validate_parent_receipt(parent)
    validated_envelope = validate_envelope(envelope)
    wrapped = validated_envelope["result"]
    adaptive = wrapped["adaptive_verifier_receipt"]
    structural_parent = wrapped["parent_result"]
    semantic = structural_parent["semantic_result"]
    core = semantic["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    structural = structural_parent["structural_receipt"]
    private = wrapped["private_replay_state"]
    selection = private["selection_state"]
    union = selection["union_receipt_after_proposal_parent"]
    proposal_catalog = semantic["semantic_active_private_state"][
        "semantic_active_catalog"
    ]
    base_catalog = proposal_catalog["active_catalog"]["base_catalog"]
    slot = validated_envelope["model_slot_receipt"]
    transport = validated_envelope["transport_health"]
    single_shot = validated_envelope["search_single_shot_receipt"]
    model_cost = core["cost"]["model"]
    search_cost = core["cost"]["search"]
    status_counts = adaptive["verification_status_counts"]
    selected_statuses = adaptive["selected_verification_status_counts"]
    raw_host_counts = list(adaptive["raw_batch_unique_host_counts"])
    before = _integer(adaptive, "candidate_changed_cells_before_hidden_verifier")
    after = _integer(adaptive, "candidate_changed_cells_after_hidden_verifier")
    value = {
        "ordinal": ordinal,
        "wall_seconds": round(float(validated_parent["elapsed_seconds"]), 6),
        "parent_taxonomy": validated_parent["failure_taxonomy"],
        "all_parent_artifacts_valid": all(
            validated_parent[name] is True
            for name in (
                "child_terminal_receipt_present",
                "child_terminal_receipt_valid",
                "result_envelope_present",
                "result_envelope_valid",
                "model_receipt_present",
                "model_receipt_valid",
                "transport_receipt_present",
                "transport_receipt_valid",
            )
        ),
        "completion_kind": core["completion_kind"],
        "effect_accounting_complete": core_receipt["effect_accounting_complete"],
        "structural_shared_normalization": structural[
            "same_normalized_baseline_for_baseline_and_candidate"
        ],
        "logical_query_count": _integer(adaptive, "logical_query_count"),
        "discovery_batch_count": _integer(adaptive, "discovery_batch_count"),
        "batch_logical_query_counts": [len(batch) for batch in selection["query_batches"]],
        "provider_search_call_count": _integer(search_cost, "calls"),
        "single_shot_multi_query_chunks": _integer(single_shot, "multi_query_chunks"),
        "recursive_split_requests": _integer(single_shot, "recursive_split_requests"),
        "pre_host_dedup_url_lead_count": _integer(union, "raw_action_source_count"),
        "registrable_host_union_count": sum(raw_host_counts),
        "registrable_host_duplicate_url_count": _integer(
            union, "raw_action_source_count"
        )
        - sum(raw_host_counts),
        "raw_batch_unique_host_counts": raw_host_counts,
        "proposal_batch_host_counts": list(adaptive["proposal_batch_host_counts"]),
        "heldout_batch_host_counts": list(adaptive["heldout_batch_host_counts"]),
        "verifier_batch_host_counts": list(adaptive["selected_verifier_batch_host_counts"]),
        "proposal_source_count": _integer(adaptive, "proposal_source_count"),
        "heldout_source_count": _integer(adaptive, "heldout_source_count"),
        "selected_verifier_source_count": _integer(adaptive, "selected_verifier_source_count"),
        "verifier_source_cap": 2,
        "source_partition_disjoint": adaptive["proposal_and_verifier_sources_disjoint"],
        "four_queries_split_two_plus_two_before_candidate": adaptive["four_queries_split_two_plus_two_before_candidate"],
        "full_proposal_partition": adaptive["eight_proposal_sources_exposed_before_candidate_at_full_capacity"],
        "heldout_metadata_only_before_candidate": adaptive["heldout_source_titles_urls_and_provenance_only_before_candidate"],
        "verifier_source_selection_after_candidate_and_support_freeze": adaptive["verifier_source_selection_after_candidate_and_support_freeze"],
        "hidden_verifier_prompt_excluded": not adaptive["verifier_pages_used_for_candidate_generation_or_model_prompt"],
        "hidden_verifier_no_new_candidate": not adaptive["new_candidate_value_generated_by_verifier"],
        "parent_support_ids_reused": adaptive["parent_support_set_ids_reused_without_rebuild"],
        "target_segment_entity_boundary_enforced": adaptive["target_segment_entity_boundary_enforced"],
        "parent_semantic_catalog_present": isinstance(proposal_catalog, Mapping),
        "parent_proposal_page_count": _integer(adaptive, "parent_proposal_page_count"),
        "hidden_verifier_page_count": _integer(adaptive, "hidden_verifier_page_count"),
        "parent_fetch_calls": _integer(adaptive, "parent_fetch_calls"),
        "hidden_verifier_fetch_calls": _integer(adaptive, "hidden_verifier_fetch_calls"),
        "total_fetch_calls": _integer(adaptive, "total_fetch_calls"),
        "parent_eligible_support_set_count": _integer(base_catalog, "eligible_support_set_count"),
        "parent_candidate_changed_cells": before,
        "preverification_candidate_changed_cells": before,
        "adaptive_retained_candidate_changed_cells": after,
        "adaptive_added_candidate_changed_cells": 0,
        "adaptive_reverted_candidate_changed_cells": before - after,
        "hidden_verifier_admitted_cells": _integer(adaptive, "hidden_verifier_admitted_cells"),
        "hidden_verifier_reverted_cells": _integer(adaptive, "hidden_verifier_reverted_cells"),
        "selection_resolution_count": _integer(adaptive, "selection_resolution_count"),
        "candidate_changes_without_declaration": _integer(adaptive, "candidate_changes_without_declaration"),
        "selected_exactly_bound_candidate_changes": _integer(adaptive, "selected_exactly_bound_candidate_changes"),
        "verification_record_count": _integer(adaptive, "verification_record_count"),
        "verified_candidate_records": int(status_counts.get("verified_candidate", 0)),
        "no_independent_candidate_support_records": int(status_counts.get("no_independent_candidate_support", 0)),
        "verifier_supports_baseline_records": int(status_counts.get("verifier_supports_baseline", 0)),
        "independent_conflict_records": int(status_counts.get("independent_conflict", 0)),
        "nonpositive_proposal_entropy_records": int(status_counts.get("nonpositive_proposal_entropy", 0)),
        "selected_verified_candidate_changes": int(selected_statuses.get("verified_candidate", 0)),
        "selected_no_independent_candidate_support_changes": int(selected_statuses.get("no_independent_candidate_support", 0)),
        "selected_verifier_supports_baseline_changes": int(selected_statuses.get("verifier_supports_baseline", 0)),
        "selected_independent_conflict_changes": int(selected_statuses.get("independent_conflict", 0)),
        "selected_nonpositive_proposal_entropy_changes": int(selected_statuses.get("nonpositive_proposal_entropy", 0)),
        "verifier_semantic_projection_count": _integer(adaptive, "verifier_semantic_projection_count"),
        "proposal_support_entropy_total_nats": _number(adaptive, "proposal_support_entropy_total_nats"),
        "selected_proposal_entropy_nats": _number(adaptive, "selected_proposal_conditional_entropy_reduction_nats"),
        "utility_aligned_entropy_credit_nats": _number(adaptive, "utility_aligned_entropy_credit_nats"),
        "model_requests": _integer(model_cost, "requests"),
        "model_attempts": _integer(model_cost, "attempts"),
        "model_total_tokens": _integer(model_cost, "total_tokens"),
        "slot_acquisitions": _integer(slot, "acquisitions"),
        "slot_timeouts": _integer(slot, "slot_timeouts"),
        "provider_deadline_failures": _integer(slot, "provider_deadline_failures"),
        "slot_total_wait_seconds": _number(slot, "total_wait_seconds"),
        "slot_max_wait_seconds": _number(slot, "max_wait_seconds"),
        "slot_acquisition_counts": list(slot["slot_acquisition_counts"]),
        "search_calls": _integer(search_cost, "calls"),
        "fetch_failures": _integer(search_cost, "fetch_failures"),
        "search_total_tokens": _integer(search_cost, "total_tokens"),
        "hosted_search_attempts": _integer(transport, "hosted_search_attempts"),
        "hosted_search_deadline_failures": _integer(transport, "hosted_search_deadline_failures"),
        "hard_fetch_helper_calls": _integer(transport, "hard_fetch_helper_calls"),
        "hard_fetch_deadline_failures": _integer(transport, "hard_fetch_deadline_failures"),
        "fetch_deadline_rejections": _integer(transport, "fetch_deadline_rejections"),
        "fetch_helper_failures": _integer(transport, "fetch_helper_failures"),
        "deadline_exhausted": transport["deadline_exhausted"] is True,
        "private_replay_valid": isinstance(private["target_segment_utility_catalog"], Mapping),
    }
    value["checks"] = _task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


COUNT_FIELDS = (
    "logical_query_count",
    "discovery_batch_count",
    "provider_search_call_count",
    "single_shot_multi_query_chunks",
    "recursive_split_requests",
    "pre_host_dedup_url_lead_count",
    "registrable_host_union_count",
    "registrable_host_duplicate_url_count",
    "proposal_source_count",
    "heldout_source_count",
    "selected_verifier_source_count",
    "verifier_source_cap",
    "parent_proposal_page_count",
    "hidden_verifier_page_count",
    "parent_fetch_calls",
    "hidden_verifier_fetch_calls",
    "total_fetch_calls",
    "parent_eligible_support_set_count",
    "parent_candidate_changed_cells",
    "preverification_candidate_changed_cells",
    "adaptive_retained_candidate_changed_cells",
    "adaptive_added_candidate_changed_cells",
    "adaptive_reverted_candidate_changed_cells",
    "hidden_verifier_admitted_cells",
    "hidden_verifier_reverted_cells",
    "selection_resolution_count",
    "candidate_changes_without_declaration",
    "selected_exactly_bound_candidate_changes",
    "verification_record_count",
    "verified_candidate_records",
    "no_independent_candidate_support_records",
    "verifier_supports_baseline_records",
    "independent_conflict_records",
    "nonpositive_proposal_entropy_records",
    "selected_verified_candidate_changes",
    "selected_no_independent_candidate_support_changes",
    "selected_verifier_supports_baseline_changes",
    "selected_independent_conflict_changes",
    "selected_nonpositive_proposal_entropy_changes",
    "verifier_semantic_projection_count",
    "model_requests",
    "model_attempts",
    "model_total_tokens",
    "slot_acquisitions",
    "slot_timeouts",
    "provider_deadline_failures",
    "search_calls",
    "fetch_failures",
    "search_total_tokens",
    "hosted_search_attempts",
    "hosted_search_deadline_failures",
    "hard_fetch_helper_calls",
    "hard_fetch_deadline_failures",
    "fetch_deadline_rejections",
    "fetch_helper_failures",
)
VECTOR_FIELDS = (
    "raw_batch_unique_host_counts",
    "proposal_batch_host_counts",
    "heldout_batch_host_counts",
    "verifier_batch_host_counts",
)
BOOLEAN_FIELDS = (
    "all_parent_artifacts_valid",
    "effect_accounting_complete",
    "structural_shared_normalization",
    "source_partition_disjoint",
    "four_queries_split_two_plus_two_before_candidate",
    "full_proposal_partition",
    "heldout_metadata_only_before_candidate",
    "verifier_source_selection_after_candidate_and_support_freeze",
    "hidden_verifier_prompt_excluded",
    "hidden_verifier_no_new_candidate",
    "parent_support_ids_reused",
    "target_segment_entity_boundary_enforced",
    "parent_semantic_catalog_present",
    "deadline_exhausted",
    "private_replay_valid",
    "passed",
)
NUMERIC_FIELDS = (
    "wall_seconds",
    "proposal_support_entropy_total_nats",
    "selected_proposal_entropy_nats",
    "utility_aligned_entropy_credit_nats",
    "slot_total_wait_seconds",
    "slot_max_wait_seconds",
)
TASK_KEYS = frozenset(
    {
        "ordinal",
        "parent_taxonomy",
        "completion_kind",
        "batch_logical_query_counts",
        "slot_acquisition_counts",
        "checks",
        *COUNT_FIELDS,
        *VECTOR_FIELDS,
        *BOOLEAN_FIELDS,
        *NUMERIC_FIELDS,
    }
)


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    verification_total = sum(
        value.get(name, -1)
        for name in (
            "verified_candidate_records",
            "no_independent_candidate_support_records",
            "verifier_supports_baseline_records",
            "independent_conflict_records",
            "nonpositive_proposal_entropy_records",
        )
    )
    selected_total = sum(
        value.get(name, -1)
        for name in (
            "selected_verified_candidate_changes",
            "selected_no_independent_candidate_support_changes",
            "selected_verifier_supports_baseline_changes",
            "selected_independent_conflict_changes",
            "selected_nonpositive_proposal_entropy_changes",
        )
    )
    if (
        set(value) != TASK_KEYS
        or isinstance(value.get("ordinal"), bool)
        or not isinstance(value.get("ordinal"), int)
        or not 1 <= int(value["ordinal"]) <= SELECTED
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in COUNT_FIELDS
        )
        or any(not isinstance(value.get(name), bool) for name in BOOLEAN_FIELDS)
        or any(
            not isinstance(value.get(name), list)
            or len(value[name]) != 2
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item < 0
                for item in value[name]
            )
            for name in VECTOR_FIELDS
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in NUMERIC_FIELDS
        )
        or value.get("completion_kind") not in {"paired", "identity_no_reserve", "identity_fallback", None}
        or not isinstance(value.get("batch_logical_query_counts"), list)
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in value["batch_logical_query_counts"]
        )
        or not isinstance(value.get("slot_acquisition_counts"), list)
        or len(value["slot_acquisition_counts"]) != MODEL_SLOT_CAP
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value["slot_acquisition_counts"])
        or sum(value["slot_acquisition_counts"]) != value["slot_acquisitions"]
        or value["registrable_host_duplicate_url_count"]
        != value["pre_host_dedup_url_lead_count"] - value["registrable_host_union_count"]
        or value["provider_search_call_count"] != value["search_calls"]
        or value["provider_search_call_count"] > value["hosted_search_attempts"]
        or value["proposal_source_count"] != sum(value["proposal_batch_host_counts"])
        or value["heldout_source_count"] != sum(value["heldout_batch_host_counts"])
        or value["selected_verifier_source_count"]
        != sum(value["verifier_batch_host_counts"])
        or value["raw_batch_unique_host_counts"]
        != [
            proposal + heldout
            for proposal, heldout in zip(
                value["proposal_batch_host_counts"],
                value["heldout_batch_host_counts"],
                strict=True,
            )
        ]
        or value["selected_verifier_source_count"] > value["verifier_source_cap"]
        or value["selected_verifier_source_count"] > value["heldout_source_count"]
        or value["verifier_source_cap"] != 2
        or value["hidden_verifier_fetch_calls"]
        != value["selected_verifier_source_count"]
        or value["total_fetch_calls"]
        != value["parent_fetch_calls"] + value["hidden_verifier_fetch_calls"]
        or value["total_fetch_calls"] > 10
        or value["verification_record_count"] != value["parent_eligible_support_set_count"]
        or verification_total != value["verification_record_count"]
        or selected_total != value["selected_exactly_bound_candidate_changes"]
        or value["selection_resolution_count"] + value["candidate_changes_without_declaration"]
        != value["parent_candidate_changed_cells"]
        or value["selected_exactly_bound_candidate_changes"] > value["selection_resolution_count"]
        or value["selected_verified_candidate_changes"]
        != value["adaptive_retained_candidate_changed_cells"]
        or value["hidden_verifier_admitted_cells"]
        != value["adaptive_retained_candidate_changed_cells"]
        or value["hidden_verifier_reverted_cells"]
        != value["parent_candidate_changed_cells"] - value["adaptive_retained_candidate_changed_cells"]
        or value["adaptive_retained_candidate_changed_cells"]
        != value["preverification_candidate_changed_cells"]
        - value["adaptive_reverted_candidate_changed_cells"]
        or value["adaptive_added_candidate_changed_cells"] != 0
        or value["selected_proposal_entropy_nats"]
        > value["proposal_support_entropy_total_nats"] + 1e-12
        or value["utility_aligned_entropy_credit_nats"]
        > value["selected_proposal_entropy_nats"] + 1e-12
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or dict(checks) != _task_checks(value)
        or value["passed"] is not all(checks.values())
    ):
        raise RuntimeError("V2.43.81 task projection drifted")
    return dict(value)


def _local_failure(ordinal: int) -> dict[str, Any]:
    value: dict[str, Any] = {
        "ordinal": ordinal,
        "wall_seconds": 0.0,
        "parent_taxonomy": "local_projection_failure",
        "completion_kind": None,
        "batch_logical_query_counts": [],
        "slot_acquisition_counts": [0] * MODEL_SLOT_CAP,
        "proposal_support_entropy_total_nats": 0.0,
        "selected_proposal_entropy_nats": 0.0,
        "utility_aligned_entropy_credit_nats": 0.0,
        "slot_total_wait_seconds": 0.0,
        "slot_max_wait_seconds": 0.0,
    }
    for name in COUNT_FIELDS:
        value[name] = 0
    for name in VECTOR_FIELDS:
        value[name] = [0, 0]
    value["verifier_source_cap"] = 2
    for name in BOOLEAN_FIELDS:
        value[name] = False
    value["deadline_exhausted"] = True
    value["checks"] = _task_checks(value)
    value["passed"] = False
    validate_task_projection(value)
    return value


def _run_one(
    root: Path,
    output_root: Path,
    slots: Path,
    directory: Path,
    ordinal: int,
) -> dict[str, Any]:
    result_path = directory / "result.json"
    model_path = directory / "model_slot_receipt.json"
    transport_path = directory / "transport_health.json"

    def result_validator(value: Mapping[str, Any]) -> object:
        envelope = validate_envelope(value)
        if model_path.is_file() and transport_path.is_file():
            validate_observed_bundle(
                envelope,
                model_slot_receipt=json.loads(model_path.read_text(encoding="utf-8")),
                transport_health=json.loads(transport_path.read_text(encoding="utf-8")),
                search_single_shot_receipt=envelope["search_single_shot_receipt"],
                expected_cap=MODEL_SLOT_CAP,
            )
        return envelope

    outcome = run_observed_subprocess(
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
        result_validator=result_validator,
        model_receipt_validator=lambda value: validate_model_receipt(value, expected_cap=MODEL_SLOT_CAP),
        transport_receipt_validator=validate_transport_health,
        result_name="result.json",
        model_receipt_name="model_slot_receipt.json",
        transport_receipt_name="transport_health.json",
        terminal_name="child_terminal_receipt.json",
        parent_name="parent_exit_receipt.json",
    )
    parent = validate_parent_receipt(outcome.receipt)
    envelope = (
        json.loads(result_path.read_text(encoding="utf-8"))
        if parent["failure_taxonomy"] == "success"
        else None
    )
    return _task_projection(ordinal, parent, envelope)


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]], batch_wall_seconds: float
) -> dict[str, Any]:
    values = [dict(task) for task in tasks]
    [validate_task_projection(task) for task in values]
    values.sort(key=lambda item: item["ordinal"])
    completion_counts = Counter(str(task["completion_kind"]) for task in values)
    summary = {
        "selected": len(values),
        "exact_ordinal_vector": [task["ordinal"] for task in values]
        == list(range(1, SELECTED + 1)),
        "terminal_success_tasks": sum(task["parent_taxonomy"] == "success" for task in values),
        "structurally_passed_tasks": sum(task["passed"] is True for task in values),
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "throughput_tasks_per_minute": round(
            len(values) / max(float(batch_wall_seconds), 1e-9) * 60, 6
        ),
        "completion_kinds": dict(sorted(completion_counts.items())),
        "exact_two_batch_tasks": sum(task["checks"]["two_batch_discovery_complete"] for task in values),
        "zero_recursive_split_tasks": sum(task["checks"]["recursive_split_absent"] for task in values),
        "union_ge_ten_host_tasks": sum(task["registrable_host_union_count"] >= 10 for task in values),
        "full_proposal_partition_tasks": sum(
            task["proposal_source_count"] == 8
            for task in values
        ),
        "heldout_pool_tasks": sum(
            task["heldout_source_count"] > 0
            for task in values
        ),
        "pre_host_dedup_url_leads": sum(task["pre_host_dedup_url_lead_count"] for task in values),
        "registrable_host_union_count": sum(task["registrable_host_union_count"] for task in values),
        "registrable_host_duplicate_url_count": sum(task["registrable_host_duplicate_url_count"] for task in values),
        "proposal_sources": sum(task["proposal_source_count"] for task in values),
        "heldout_sources": sum(task["heldout_source_count"] for task in values),
        "selected_verifier_sources": sum(task["selected_verifier_source_count"] for task in values),
        "parent_semantic_catalog_tasks": sum(task["parent_semantic_catalog_present"] for task in values),
        "parent_eligible_support_tasks": sum(task["parent_eligible_support_set_count"] > 0 for task in values),
        "parent_eligible_support_set_count": sum(task["parent_eligible_support_set_count"] for task in values),
        "parent_candidate_tasks": sum(task["parent_candidate_changed_cells"] > 0 for task in values),
        "selected_bound_candidate_tasks": sum(task["selected_exactly_bound_candidate_changes"] > 0 for task in values),
        "preverification_nonidentity_tasks": sum(task["preverification_candidate_changed_cells"] > 0 for task in values),
        "utility_aligned_tasks": sum(task["utility_aligned_entropy_credit_nats"] > 0 for task in values),
        "final_nonidentity_tasks": sum(task["adaptive_retained_candidate_changed_cells"] > 0 for task in values),
        "parent_candidate_changed_cells": sum(task["parent_candidate_changed_cells"] for task in values),
        "preverification_candidate_changed_cells": sum(task["preverification_candidate_changed_cells"] for task in values),
        "adaptive_retained_candidate_changed_cells": sum(task["adaptive_retained_candidate_changed_cells"] for task in values),
        "adaptive_added_candidate_changed_cells": sum(task["adaptive_added_candidate_changed_cells"] for task in values),
        "adaptive_reverted_candidate_changed_cells": sum(task["adaptive_reverted_candidate_changed_cells"] for task in values),
        "adaptive_net_retention_delta": sum(task["adaptive_retained_candidate_changed_cells"] - task["preverification_candidate_changed_cells"] for task in values),
        "hidden_verifier_admitted_cells": sum(task["hidden_verifier_admitted_cells"] for task in values),
        "hidden_verifier_reverted_cells": sum(task["hidden_verifier_reverted_cells"] for task in values),
        "selection_resolution_count": sum(task["selection_resolution_count"] for task in values),
        "candidate_changes_without_declaration": sum(task["candidate_changes_without_declaration"] for task in values),
        "selected_exactly_bound_candidate_changes": sum(task["selected_exactly_bound_candidate_changes"] for task in values),
        "verification_record_count": sum(task["verification_record_count"] for task in values),
        "verified_candidate_records": sum(task["verified_candidate_records"] for task in values),
        "no_independent_candidate_support_records": sum(task["no_independent_candidate_support_records"] for task in values),
        "verifier_supports_baseline_records": sum(task["verifier_supports_baseline_records"] for task in values),
        "independent_conflict_records": sum(task["independent_conflict_records"] for task in values),
        "nonpositive_proposal_entropy_records": sum(task["nonpositive_proposal_entropy_records"] for task in values),
        "selected_verified_candidate_changes": sum(task["selected_verified_candidate_changes"] for task in values),
        "selected_no_independent_candidate_support_changes": sum(task["selected_no_independent_candidate_support_changes"] for task in values),
        "selected_verifier_supports_baseline_changes": sum(task["selected_verifier_supports_baseline_changes"] for task in values),
        "selected_independent_conflict_changes": sum(task["selected_independent_conflict_changes"] for task in values),
        "selected_nonpositive_proposal_entropy_changes": sum(task["selected_nonpositive_proposal_entropy_changes"] for task in values),
        "verifier_semantic_projection_count": sum(task["verifier_semantic_projection_count"] for task in values),
        "proposal_support_entropy_total_nats": round(sum(task["proposal_support_entropy_total_nats"] for task in values), 12),
        "selected_proposal_entropy_nats": round(sum(task["selected_proposal_entropy_nats"] for task in values), 12),
        "utility_aligned_entropy_credit_nats": round(sum(task["utility_aligned_entropy_credit_nats"] for task in values), 12),
        "proposal_pages": sum(task["parent_proposal_page_count"] for task in values),
        "hidden_verifier_pages": sum(task["hidden_verifier_page_count"] for task in values),
        "model_requests": sum(task["model_requests"] for task in values),
        "model_attempts": sum(task["model_attempts"] for task in values),
        "model_total_tokens": sum(task["model_total_tokens"] for task in values),
        "slot_acquisitions": sum(task["slot_acquisitions"] for task in values),
        "slot_timeouts": sum(task["slot_timeouts"] for task in values),
        "provider_deadline_failures": sum(task["provider_deadline_failures"] for task in values),
        "slot_total_wait_seconds": round(sum(task["slot_total_wait_seconds"] for task in values), 6),
        "slot_max_wait_seconds": round(max((task["slot_max_wait_seconds"] for task in values), default=0), 6),
        "search_calls": sum(task["search_calls"] for task in values),
        "hosted_search_attempts": sum(task["hosted_search_attempts"] for task in values),
        "fetch_calls": sum(task["total_fetch_calls"] for task in values),
        "fetch_failures": sum(task["fetch_failures"] for task in values),
        "hosted_search_deadline_failures": sum(task["hosted_search_deadline_failures"] for task in values),
        "hard_fetch_helper_calls": sum(task["hard_fetch_helper_calls"] for task in values),
        "hard_fetch_deadline_failures": sum(task["hard_fetch_deadline_failures"] for task in values),
        "fetch_deadline_rejections": sum(task["fetch_deadline_rejections"] for task in values),
        "fetch_helper_failures": sum(task["fetch_helper_failures"] for task in values),
        "deadline_exhausted_tasks": sum(task["deadline_exhausted"] for task in values),
        "all_private_replay_valid": all(task["private_replay_valid"] for task in values),
        "all_source_partitions_disjoint": all(task["source_partition_disjoint"] for task in values),
        "all_hidden_pages_excluded_from_parent_prompt": all(task["hidden_verifier_prompt_excluded"] for task in values),
        "all_adaptive_verifier_final_decisions": all(task["checks"]["adaptive_verifier_final_decision"] for task in values),
        "all_fetch_budgets_conserved": all(task["checks"]["fetch_budget_transport_conserved"] for task in values),
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    checks = _aggregate_checks(summary)
    value = {**summary, "checks": checks, "passed": all(checks.values())}
    validate_aggregate(value)
    return value


AGGREGATE_CHECK_NAMES = (
    "exact_selected",
    "exact_ordinal_vector",
    "all_tasks_structurally_passed",
    "batch_wall_within_ceiling",
    "slot_timeouts",
    "provider_deadline_failures",
    "hosted_search_deadline_failures",
    "hard_fetch_deadline_failures",
    "fetch_helper_failures",
    "deadline_exhausted_tasks",
    "exact_two_batch_tasks",
    "zero_recursive_split_tasks",
    "full_proposal_partition_tasks",
    "proposal_source_count_total",
    "heldout_pool_tasks",
    "parent_semantic_catalog_tasks",
    "selected_verifier_sources",
    "hidden_verifier_pages",
    "parent_candidate_tasks",
    "selected_bound_candidate_tasks",
    "utility_aligned_tasks",
    "final_nonidentity_tasks",
    "selected_verified_candidate_changes",
    "adaptive_retained_candidate_changed_cells",
    "selected_proposal_entropy",
    "utility_aligned_entropy",
    "selected_verified_final_alignment",
    "adaptive_retention_conservation",
    "verification_record_conservation",
    "selected_verification_conservation",
    "entropy_credit_conservation",
    "all_private_replay_valid",
    "all_source_partitions_disjoint",
    "all_hidden_pages_excluded_from_parent_prompt",
    "all_adaptive_verifier_final_decisions",
    "all_fetch_budgets_conserved",
)


def _aggregate_checks(summary: Mapping[str, Any]) -> dict[str, bool]:
    value = {
        "exact_selected": summary.get("selected") == SELECTED,
        "exact_ordinal_vector": summary.get("exact_ordinal_vector") is True,
        "all_tasks_structurally_passed": summary["structurally_passed_tasks"] == SELECTED,
        "batch_wall_within_ceiling": summary["batch_wall_seconds"] <= GATES["maximum_batch_wall_seconds"],
        "slot_timeouts": summary["slot_timeouts"] <= GATES["maximum_slot_timeouts"],
        "provider_deadline_failures": summary["provider_deadline_failures"] <= GATES["maximum_provider_deadline_failures"],
        "hosted_search_deadline_failures": summary["hosted_search_deadline_failures"] <= GATES["maximum_hosted_search_deadline_failures"],
        "hard_fetch_deadline_failures": summary["hard_fetch_deadline_failures"] <= GATES["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": summary["fetch_helper_failures"] <= GATES["maximum_fetch_helper_failures"],
        "deadline_exhausted_tasks": summary["deadline_exhausted_tasks"] <= GATES["maximum_deadline_exhausted_tasks"],
        "exact_two_batch_tasks": summary["exact_two_batch_tasks"] >= GATES["minimum_exact_two_batch_tasks"],
        "zero_recursive_split_tasks": summary["zero_recursive_split_tasks"] >= GATES["minimum_zero_recursive_split_tasks"],
        "full_proposal_partition_tasks": summary["full_proposal_partition_tasks"] >= GATES["minimum_full_proposal_partition_tasks"],
        "proposal_source_count_total": summary["proposal_sources"] >= GATES["minimum_proposal_source_count_total"],
        "heldout_pool_tasks": summary["heldout_pool_tasks"] >= GATES["minimum_heldout_pool_tasks"],
        "parent_semantic_catalog_tasks": summary["parent_semantic_catalog_tasks"] >= GATES["minimum_parent_semantic_catalog_tasks"],
        "selected_verifier_sources": summary["selected_verifier_sources"] >= GATES["minimum_selected_verifier_sources"],
        "hidden_verifier_pages": summary["hidden_verifier_pages"] >= GATES["minimum_hidden_verifier_pages"],
        "parent_candidate_tasks": summary["parent_candidate_tasks"] >= GATES["minimum_parent_candidate_tasks"],
        "selected_bound_candidate_tasks": summary["selected_bound_candidate_tasks"] >= GATES["minimum_selected_bound_candidate_tasks"],
        "utility_aligned_tasks": summary["utility_aligned_tasks"] >= GATES["minimum_utility_aligned_tasks"],
        "final_nonidentity_tasks": summary["final_nonidentity_tasks"] >= GATES["minimum_final_nonidentity_tasks"],
        "selected_verified_candidate_changes": summary["selected_verified_candidate_changes"] >= GATES["minimum_selected_verified_candidate_changes"],
        "adaptive_retained_candidate_changed_cells": summary["adaptive_retained_candidate_changed_cells"] >= GATES["minimum_adaptive_retained_candidate_changed_cells"],
        "selected_proposal_entropy": summary["selected_proposal_entropy_nats"] >= GATES["minimum_selected_proposal_entropy_nats"],
        "utility_aligned_entropy": summary["utility_aligned_entropy_credit_nats"] >= GATES["minimum_utility_aligned_entropy_nats"],
        "selected_verified_final_alignment": summary["selected_verified_candidate_changes"] == summary["adaptive_retained_candidate_changed_cells"],
        "adaptive_retention_conservation": summary["adaptive_retained_candidate_changed_cells"] == summary["preverification_candidate_changed_cells"] - summary["adaptive_reverted_candidate_changed_cells"] and summary["adaptive_added_candidate_changed_cells"] == 0,
        "verification_record_conservation": summary["verification_record_count"] == summary["parent_eligible_support_set_count"] == summary["verified_candidate_records"] + summary["no_independent_candidate_support_records"] + summary["verifier_supports_baseline_records"] + summary["independent_conflict_records"] + summary["nonpositive_proposal_entropy_records"],
        "selected_verification_conservation": summary["selection_resolution_count"] + summary["candidate_changes_without_declaration"] == summary["parent_candidate_changed_cells"] and summary["selected_exactly_bound_candidate_changes"] == summary["selected_verified_candidate_changes"] + summary["selected_no_independent_candidate_support_changes"] + summary["selected_verifier_supports_baseline_changes"] + summary["selected_independent_conflict_changes"] + summary["selected_nonpositive_proposal_entropy_changes"],
        "entropy_credit_conservation": 0 <= summary["utility_aligned_entropy_credit_nats"] <= summary["selected_proposal_entropy_nats"] + 1e-12 <= summary["proposal_support_entropy_total_nats"] + 1e-12,
        "all_private_replay_valid": summary["all_private_replay_valid"] is True,
        "all_source_partitions_disjoint": summary["all_source_partitions_disjoint"] is True,
        "all_hidden_pages_excluded_from_parent_prompt": summary["all_hidden_pages_excluded_from_parent_prompt"] is True,
        "all_adaptive_verifier_final_decisions": summary["all_adaptive_verifier_final_decisions"] is True,
        "all_fetch_budgets_conserved": summary["all_fetch_budgets_conserved"] is True,
    }
    if tuple(value) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.43.81 aggregate check order drifted")
    return value


AGGREGATE_KEYS = frozenset(
    {
        "selected",
        "exact_ordinal_vector",
        "terminal_success_tasks",
        "structurally_passed_tasks",
        "batch_wall_seconds",
        "throughput_tasks_per_minute",
        "completion_kinds",
        "exact_two_batch_tasks",
        "zero_recursive_split_tasks",
        "union_ge_ten_host_tasks",
        "full_proposal_partition_tasks",
        "heldout_pool_tasks",
        "pre_host_dedup_url_leads",
        "registrable_host_union_count",
        "registrable_host_duplicate_url_count",
        "proposal_sources",
        "heldout_sources",
        "selected_verifier_sources",
        "parent_semantic_catalog_tasks",
        "parent_eligible_support_tasks",
        "parent_eligible_support_set_count",
        "parent_candidate_tasks",
        "selected_bound_candidate_tasks",
        "preverification_nonidentity_tasks",
        "utility_aligned_tasks",
        "final_nonidentity_tasks",
        "parent_candidate_changed_cells",
        "preverification_candidate_changed_cells",
        "adaptive_retained_candidate_changed_cells",
        "adaptive_added_candidate_changed_cells",
        "adaptive_reverted_candidate_changed_cells",
        "adaptive_net_retention_delta",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "selection_resolution_count",
        "candidate_changes_without_declaration",
        "selected_exactly_bound_candidate_changes",
        "verification_record_count",
        "verified_candidate_records",
        "no_independent_candidate_support_records",
        "verifier_supports_baseline_records",
        "independent_conflict_records",
        "nonpositive_proposal_entropy_records",
        "selected_verified_candidate_changes",
        "selected_no_independent_candidate_support_changes",
        "selected_verifier_supports_baseline_changes",
        "selected_independent_conflict_changes",
        "selected_nonpositive_proposal_entropy_changes",
        "verifier_semantic_projection_count",
        "proposal_support_entropy_total_nats",
        "selected_proposal_entropy_nats",
        "utility_aligned_entropy_credit_nats",
        "proposal_pages",
        "hidden_verifier_pages",
        "model_requests",
        "model_attempts",
        "model_total_tokens",
        "slot_acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
        "slot_total_wait_seconds",
        "slot_max_wait_seconds",
        "search_calls",
        "hosted_search_attempts",
        "fetch_calls",
        "fetch_failures",
        "hosted_search_deadline_failures",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
        "deadline_exhausted_tasks",
        "all_private_replay_valid",
        "all_source_partitions_disjoint",
        "all_hidden_pages_excluded_from_parent_prompt",
        "all_adaptive_verifier_final_decisions",
        "all_fetch_budgets_conserved",
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "checks",
        "passed",
    }
)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    completion = value.get("completion_kinds")
    numeric_fields = (
        "batch_wall_seconds",
        "throughput_tasks_per_minute",
        "proposal_support_entropy_total_nats",
        "selected_proposal_entropy_nats",
        "utility_aligned_entropy_credit_nats",
        "slot_total_wait_seconds",
        "slot_max_wait_seconds",
    )
    boolean_fields = (
        "exact_ordinal_vector",
        "all_private_replay_valid",
        "all_source_partitions_disjoint",
        "all_hidden_pages_excluded_from_parent_prompt",
        "all_adaptive_verifier_final_decisions",
        "all_fetch_budgets_conserved",
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "passed",
    )
    noninteger = {
        *numeric_fields,
        *boolean_fields,
        "completion_kinds",
        "checks",
        "adaptive_net_retention_delta",
    }
    integer_fields = AGGREGATE_KEYS - noninteger
    task_bounded_fields = (
        "terminal_success_tasks",
        "structurally_passed_tasks",
        "exact_two_batch_tasks",
        "zero_recursive_split_tasks",
        "union_ge_ten_host_tasks",
        "full_proposal_partition_tasks",
        "heldout_pool_tasks",
        "parent_semantic_catalog_tasks",
        "parent_eligible_support_tasks",
        "parent_candidate_tasks",
        "selected_bound_candidate_tasks",
        "preverification_nonidentity_tasks",
        "utility_aligned_tasks",
        "final_nonidentity_tasks",
        "deadline_exhausted_tasks",
    )
    if (
        set(value) != AGGREGATE_KEYS
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_fields
        )
        or isinstance(value.get("adaptive_net_retention_delta"), bool)
        or not isinstance(value.get("adaptive_net_retention_delta"), int)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in numeric_fields
        )
        or any(not isinstance(value.get(name), bool) for name in boolean_fields)
        or not isinstance(completion, Mapping)
        or any(
            name not in COMPLETION_KINDS
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for name, count in completion.items()
        )
        or sum(completion.values()) != value["selected"]
        or any(value[name] > value["selected"] for name in task_bounded_fields)
        or value["registrable_host_duplicate_url_count"]
        != value["pre_host_dedup_url_leads"] - value["registrable_host_union_count"]
        or value["proposal_sources"] > 8 * value["selected"]
        or value["selected_verifier_sources"] > 2 * value["selected"]
        or value["selected_verifier_sources"] > value["heldout_sources"]
        or value["hidden_verifier_pages"] > value["selected_verifier_sources"]
        or value["adaptive_net_retention_delta"]
        != value["adaptive_retained_candidate_changed_cells"]
        - value["preverification_candidate_changed_cells"]
        or value["adaptive_retained_candidate_changed_cells"]
        != value["preverification_candidate_changed_cells"]
        - value["adaptive_reverted_candidate_changed_cells"]
        or value["adaptive_added_candidate_changed_cells"] != 0
        or value["hidden_verifier_admitted_cells"]
        != value["adaptive_retained_candidate_changed_cells"]
        or value["hidden_verifier_reverted_cells"]
        != value["preverification_candidate_changed_cells"]
        - value["adaptive_retained_candidate_changed_cells"]
        or value["verification_record_count"]
        != value["parent_eligible_support_set_count"]
        or value["verification_record_count"]
        != value["verified_candidate_records"]
        + value["no_independent_candidate_support_records"]
        + value["verifier_supports_baseline_records"]
        + value["independent_conflict_records"]
        + value["nonpositive_proposal_entropy_records"]
        or value["selection_resolution_count"]
        + value["candidate_changes_without_declaration"]
        != value["parent_candidate_changed_cells"]
        or value["selected_exactly_bound_candidate_changes"]
        != value["selected_verified_candidate_changes"]
        + value["selected_no_independent_candidate_support_changes"]
        + value["selected_verifier_supports_baseline_changes"]
        + value["selected_independent_conflict_changes"]
        + value["selected_nonpositive_proposal_entropy_changes"]
        or value["selected_verified_candidate_changes"]
        != value["adaptive_retained_candidate_changed_cells"]
        or value["selected_proposal_entropy_nats"]
        > value["proposal_support_entropy_total_nats"] + 1e-12
        or value["utility_aligned_entropy_credit_nats"]
        > value["selected_proposal_entropy_nats"] + 1e-12
        or value["slot_acquisitions"] != value["model_requests"]
        or value["fetch_calls"]
        != value["hard_fetch_helper_calls"] + value["fetch_deadline_rejections"]
        or value["task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted"]
        is not False
        or value["mapping_gold_category_question_type_split_evaluator_score_or_reward_read"]
        is not False
        or not isinstance(checks, Mapping)
        or tuple(checks) != AGGREGATE_CHECK_NAMES
        or dict(checks) != _aggregate_checks(value)
        or value["passed"] is not all(checks.values())
    ):
        raise RuntimeError("V2.43.81 aggregate drifted")
    return dict(value)


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    encoded = json.dumps(value, ensure_ascii=False)
    aggregate = value.get("aggregate")
    provenance = value.get("provenance")
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "selected",
        "executor_count",
        "model_slot_cap",
        "aggregate",
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
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24381_adaptive_heldout_external_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value["created_at_unix"] < 0
        or not isinstance(aggregate, Mapping)
        or not isinstance(provenance, Mapping)
        or set(provenance)
        != {
            "protocol_sha256",
            "preactivation_audit_sha256",
            "activation_sha256",
            "execution_start_sha256",
            "surface_manifest_sha256",
        }
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(item)) is None
            for item in provenance.values()
        )
        or value.get("selected") != SELECTED
        or value.get("executor_count") != EXECUTOR_COUNT
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("temporary_execution_directory_remaining") is not False
        or value.get("task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("official_evaluator_called") is not False
        or value.get("resume_retry_skip_or_revaluation") is not False
        or not isinstance(value.get("passed"), bool)
        or value.get("passed") is not aggregate.get("passed")
        or seal != payload_sha256(unsigned)
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
    ):
        raise RuntimeError("V2.43.81 public result drifted or contains task content")
    validate_aggregate(aggregate)
    return dict(value)


def _git_ready(root: Path) -> bool:
    try:
        if (
            _git(root, "rev-parse", "HEAD")
            != _git(root, "rev-parse", "target/main")
            or _git(root, "status", "--porcelain")
        ):
            return False
        _git(root, "ls-files", "--error-unmatch", str(EXECUTION_START))
    except subprocess.CalledProcessError:
        return False
    return True


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    if not _future(root, (RESULT, DECISION, POSTAUDIT)) or not _git_ready(root):
        raise RuntimeError("V2.43.81 result/git surface is not ready")
    started = time.monotonic()
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
            tasks: list[dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=EXECUTOR_COUNT) as pool:
                futures = [
                    pool.submit(_run_one, root, output_root, slots, directory, ordinal)
                    for ordinal, directory in enumerate(directories, start=1)
                ]
                for ordinal, future in enumerate(futures, start=1):
                    try:
                        tasks.append(future.result())
                    except Exception:
                        tasks.append(_local_failure(ordinal))
            aggregate = aggregate_tasks(
                tasks, max(0.0, time.monotonic() - started)
            )
        value = {
            "artifact_version": 1,
            "role": "v24381_adaptive_heldout_external_result",
            "protocol_id": PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": SELECTED,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
            "aggregate": aggregate,
            "passed": aggregate["passed"],
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
        raise RuntimeError("V2.43.81 protected watcher identity drifted")
    return value


DECISION_OBSERVED_KEYS = (
    "selected",
    "terminal_success_tasks",
    "structurally_passed_tasks",
    "batch_wall_seconds",
    "throughput_tasks_per_minute",
    "completion_kinds",
    "exact_two_batch_tasks",
    "zero_recursive_split_tasks",
    "union_ge_ten_host_tasks",
    "full_proposal_partition_tasks",
    "heldout_pool_tasks",
    "registrable_host_union_count",
    "proposal_sources",
    "heldout_sources",
    "selected_verifier_sources",
    "hidden_verifier_pages",
    "parent_eligible_support_tasks",
    "parent_eligible_support_set_count",
    "parent_candidate_tasks",
    "selected_bound_candidate_tasks",
    "preverification_nonidentity_tasks",
    "utility_aligned_tasks",
    "final_nonidentity_tasks",
    "parent_candidate_changed_cells",
    "preverification_candidate_changed_cells",
    "adaptive_retained_candidate_changed_cells",
    "adaptive_added_candidate_changed_cells",
    "adaptive_reverted_candidate_changed_cells",
    "adaptive_net_retention_delta",
    "verification_record_count",
    "verified_candidate_records",
    "no_independent_candidate_support_records",
    "verifier_supports_baseline_records",
    "independent_conflict_records",
    "nonpositive_proposal_entropy_records",
    "selected_verified_candidate_changes",
    "selected_no_independent_candidate_support_changes",
    "selected_verifier_supports_baseline_changes",
    "selected_independent_conflict_changes",
    "selected_nonpositive_proposal_entropy_changes",
    "proposal_support_entropy_total_nats",
    "selected_proposal_entropy_nats",
    "utility_aligned_entropy_credit_nats",
    "model_requests",
    "slot_timeouts",
    "provider_deadline_failures",
    "search_calls",
    "hosted_search_attempts",
    "hosted_search_deadline_failures",
    "hard_fetch_deadline_failures",
    "fetch_helper_failures",
    "deadline_exhausted_tasks",
)


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = validate_public_result(_read(root, RESULT))
    passed = result["passed"] is True
    aggregate = result["aggregate"]
    value = {
        "artifact_version": 1,
        "role": "v24381_adaptive_heldout_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "fresh_adaptive_heldout_external_go" if passed else "fresh_adaptive_heldout_external_no_go",
        "passed": passed,
        "failed_checks": sorted(name for name, check in aggregate["checks"].items() if not check),
        "observed": {key: aggregate[key] for key in DECISION_OBSERVED_KEYS},
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
        },
        "claim_scope": {
            "fresh_benchmark_external_real_web_adaptive_heldout_measured": True,
            "preverification_and_adaptive_cell_retention_measured": True,
            "proposal_entropy_verifier_outcome_and_utility_credit_measured": True,
            "benchmark_quality_measured": False,
            "entropy_quality_improvement_proven": False,
            "future_population_or_sota_supported": False,
        },
        "authorization": {
            "fresh_paired_dev64_design": passed,
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
    passed = result["passed"] is True
    aggregate = result["aggregate"]
    unsigned = dict(decision)
    seal = unsigned.pop("decision_payload_sha256", None)
    expected = {
        "artifact_version", "role", "protocol_id", "created_at_unix", "status",
        "passed", "failed_checks", "observed", "provenance", "claim_scope",
        "authorization", "decision_payload_sha256",
    }
    authorization = decision.get("authorization")
    claim_scope = decision.get("claim_scope")
    expected_provenance = {
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "result_sha256": sha256(root / RESULT),
    }
    if (
        set(decision) != expected
        or decision.get("artifact_version") != 1
        or decision.get("role") != "v24381_adaptive_heldout_external_decision"
        or decision.get("protocol_id") != PROTOCOL_ID
        or isinstance(decision.get("created_at_unix"), bool)
        or not isinstance(decision.get("created_at_unix"), int)
        or decision["created_at_unix"] < 0
        or decision.get("passed") is not passed
        or decision.get("status") != ("fresh_adaptive_heldout_external_go" if passed else "fresh_adaptive_heldout_external_no_go")
        or decision.get("failed_checks") != sorted(name for name, check in aggregate["checks"].items() if not check)
        or decision.get("observed") != {key: aggregate[key] for key in DECISION_OBSERVED_KEYS}
        or decision.get("provenance") != expected_provenance
        or not isinstance(claim_scope, Mapping)
        or set(claim_scope) != {
            "fresh_benchmark_external_real_web_adaptive_heldout_measured",
            "preverification_and_adaptive_cell_retention_measured",
            "proposal_entropy_verifier_outcome_and_utility_credit_measured",
            "benchmark_quality_measured",
            "entropy_quality_improvement_proven",
            "future_population_or_sota_supported",
        }
        or any(claim_scope.get(name) is not True for name in (
            "fresh_benchmark_external_real_web_adaptive_heldout_measured",
            "preverification_and_adaptive_cell_retention_measured",
            "proposal_entropy_verifier_outcome_and_utility_credit_measured",
        ))
        or any(claim_scope.get(name) is not False for name in (
            "benchmark_quality_measured", "entropy_quality_improvement_proven", "future_population_or_sota_supported"
        ))
        or not isinstance(authorization, Mapping)
        or set(authorization) != {
            "fresh_paired_dev64_design", "fresh_paired_dev64_launch", "new_exact220", "evaluator", "leaderboard_or_sota"
        }
        or authorization.get("fresh_paired_dev64_design") is not passed
        or any(authorization.get(name) is not False for name in (
            "fresh_paired_dev64_launch", "new_exact220", "evaluator", "leaderboard_or_sota"
        ))
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.81 decision drifted")
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
        "role": "v24381_adaptive_heldout_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision["status"],
        "temporary_execution_directory_remaining": False,
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_paired_dev64_design": decision["passed"] and not findings,
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
    unsigned = dict(audit)
    seal = unsigned.pop("audit_payload_sha256", None)
    expected = {
        "artifact_version", "role", "protocol_id", "created_at_unix", "result_sha256",
        "decision_sha256", "decision_status", "temporary_execution_directory_remaining",
        "shared_api_lease_active", "protected_watchers",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted",
        "network_model_search_fetch_or_evaluator_called_by_audit", "findings", "audit_valid",
        "authorization", "audit_payload_sha256",
    }
    findings = audit.get("findings")
    authorization = audit.get("authorization")
    expected_findings: list[str] = []
    if audit.get("shared_api_lease_active") is True:
        expected_findings.append("shared_api_lease_active")
    if audit.get("protected_watchers") != _read(root, EXECUTION_START).get("protected_watchers"):
        expected_findings.append("protected_watcher_identity_drifted")
    if (
        set(audit) != expected
        or audit.get("artifact_version") != 1
        or audit.get("role") != "v24381_adaptive_heldout_external_postresult_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or isinstance(audit.get("created_at_unix"), bool)
        or not isinstance(audit.get("created_at_unix"), int)
        or audit["created_at_unix"] < 0
        or audit.get("result_sha256") != sha256(root / RESULT)
        or audit.get("decision_sha256") != sha256(root / DECISION)
        or audit.get("decision_status") != decision["status"]
        or audit.get("temporary_execution_directory_remaining") is not False
        or not isinstance(audit.get("shared_api_lease_active"), bool)
        or audit.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or audit.get("task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted") is not False
        or audit.get("network_model_search_fetch_or_evaluator_called_by_audit") is not False
        or not isinstance(findings, list)
        or findings != expected_findings
        or audit.get("audit_valid") is not (not expected_findings)
        or not isinstance(authorization, Mapping)
        or set(authorization) != {
            "fresh_paired_dev64_design", "fresh_paired_dev64_launch", "new_exact220", "evaluator", "leaderboard_or_sota"
        }
        or authorization.get("fresh_paired_dev64_design") is not (decision["passed"] and not expected_findings)
        or any(authorization.get(name) is not False for name in (
            "fresh_paired_dev64_launch", "new_exact220", "evaluator", "leaderboard_or_sota"
        ))
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.81 postresult audit drifted")
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
