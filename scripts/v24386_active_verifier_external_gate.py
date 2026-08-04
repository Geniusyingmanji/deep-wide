#!/usr/bin/env python3
"""Fresh benchmark-external gate for the V2.43.83--84 successor.

Sixteen fixed public-document tasks, with 128 entities disjoint from all 736
entities in the six earlier external populations, run once through two
non-recursive proposal-search batches.  After candidate and support freeze,
at most two entropy-ranked cells generate one additional non-recursive active
verifier batch.  Task-private text, queries, URLs, pages, candidates, and
verification records exist only in a temporary directory and are
replay-validated before deletion.  Only exact, content-free aggregate counts
and booleans persist.

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
from deepwide_agent.v24384_active_verifier_query_runner import (  # noqa: E402
    ActiveVerifierDeadlineAwareNativeSearchClient,
    build_envelope,
    run_v24384_task,
    validate_envelope,
    validate_observed_bundle,
)
from deepwide_agent.v24383_active_verifier_query_runtime import (  # noqa: E402
    POLICY_ID as ACTIVE_VERIFIER_RUNTIME_POLICY_ID,
)
from deepwide_agent.v24384_active_verifier_query_runner import (  # noqa: E402
    POLICY_ID as ACTIVE_VERIFIER_RUNNER_POLICY_ID,
)
from scripts import v24345_semantic_active_natural_admission as population_1  # noqa: E402
from scripts import v24364_two_verifier_external_gate as population_2  # noqa: E402
from scripts import v24370_target_segment_external_gate as population_3  # noqa: E402
from scripts import v24374_batch_stratified_external_gate as population_4  # noqa: E402
from scripts import v24377_projection_safe_external_gate as population_5  # noqa: E402
from scripts import v24381_adaptive_heldout_external_gate as population_6  # noqa: E402
from scripts import v24386_active_verifier_projection as projection  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24386_fresh_active_verifier_query_external_gate_v1"
PROTOCOL = Path(f"results/v24386_active_verifier_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24386_active_verifier_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24386_active_verifier_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24386_active_verifier_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24386_active_verifier_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24386_active_verifier_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24386_active_verifier_external_postresult_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24385_active_verifier_query_build_audit_v1_{DATE}.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_active_verifier_query_entropy_gate"
RUNNER_MARKER = "scripts/v24386_active_verifier_external_gate.py"
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
    "minimum_exact_proposal_two_batch_tasks": SELECTED,
    "minimum_zero_recursive_split_tasks": SELECTED,
    "minimum_full_proposal_partition_tasks": 12,
    "minimum_proposal_source_count_total": 96,
    "minimum_parent_semantic_catalog_tasks": 12,
    "minimum_parent_candidate_tasks": 1,
    "minimum_active_query_tasks": 1,
    "minimum_selected_bound_candidate_tasks": 1,
    "minimum_active_selected_sources": 1,
    "minimum_active_verifier_pages": 1,
    "minimum_selected_verified_candidate_changes": 1,
    "minimum_utility_aligned_tasks": 1,
    "minimum_final_nonidentity_tasks": 1,
    "minimum_active_retained_candidate_changed_cells": 1,
    "minimum_selected_proposal_entropy_nats": 1e-12,
    "minimum_utility_aligned_entropy_nats": 1e-12,
}
QUESTIONS = (
    "Use public web sources to return one Markdown table about RustDesk, Remmina, NoMachine, AnyDesk, TeamViewer, TigerVNC, xrdp, and Apache Guacamole. The column names are: Remote desktop software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about fish, Nushell, Z shell, Elvish, Xonsh, Oil shell, Ion shell, and Tcsh. The column names are: Command shell, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Ghost, Strapi, Directus, KeystoneJS, Payload CMS, Sanity, Contentful, and Umbraco. The column names are: Content management system, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Ardour, LMMS, Rosegarden, Qtractor, Mixxx, MuseScore, Hydrogen, and Renoise. The column names are: Audio production software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about aria2, GNU Wget, Wget2, uGet, Motrix, Persepolis Download Manager, Xtreme Download Manager, and KGet. The column names are: Download manager, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about SimpleScreenRecorder, vokoscreenNG, Kazam, Peek, recordMyDesktop, ShareX, ScreenToGif, and Flameshot. The column names are: Screen utility, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about DBeaver, HeidiSQL, pgAdmin, Adminer, Beekeeper Studio, TablePlus, DataGrip, and phpMyAdmin. The column names are: Database client, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Dolphin, Nautilus, Thunar, PCManFM, Nemo, Krusader, Double Commander, and ranger. The column names are: File manager, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about HexChat, WeeChat, Irssi, Konversation, Quassel IRC, KVIrc, XChat, and mIRC. The column names are: IRC client, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Calibre, Sigil, KOReader, Foliate, FBReader, Okular, Evince, and Sumatra PDF. The column names are: Document reader, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about KiCad, LibreCAD, SolveSpace, BRL-CAD, QCAD, OpenModelica, Fritzing, and gEDA. The column names are: Engineering design software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Matomo, Plausible Analytics, Umami, Open Web Analytics, GoatCounter, Ackee, Fathom Analytics, and PostHog. The column names are: Web analytics software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about MediaWiki, DokuWiki, TiddlyWiki, XWiki, TWiki, PmWiki, BookStack, and Wiki.js. The column names are: Wiki software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Discourse, Flarum, phpBB, MyBB, Vanilla Forums, NodeBB, Simple Machines Forum, and FluxBB. The column names are: Forum software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about WireGuard, OpenVPN, strongSwan, SoftEther VPN, Tailscale, ZeroTier, Nebula, and Headscale. The column names are: VPN software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Navidrome, Airsonic, Subsonic, Ampache, Funkwhale, Mopidy, Jellyfin, and Emby. The column names are: Music server software, Initial release year. Return one table only.",
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
    "src/deepwide_agent/v24383_active_verifier_query_runtime.py",
    "src/deepwide_agent/v24384_active_verifier_query_runner.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/v24345_semantic_active_natural_admission.py",
    "scripts/v24374_batch_stratified_external_gate.py",
    "scripts/v24375_batch_stratified_projection_recovery.py",
    "scripts/audit_v24376_projection_recovery_build.py",
    "scripts/v24377_projection_safe_external_gate.py",
    "scripts/v24381_adaptive_heldout_external_gate.py",
    "scripts/audit_v24385_active_verifier_query_build.py",
    "scripts/v24386_active_verifier_projection.py",
    "scripts/v24386_active_verifier_external_gate.py",
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
    "tests/test_v24383_active_verifier_query_runtime.py",
    "tests/test_v24384_active_verifier_query_runner.py",
    "tests/test_v24386_active_verifier_external_gate.py",
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
    "tests/test_v24383_active_verifier_query_runtime.py",
    "tests/test_v24384_active_verifier_query_runner.py",
    "tests/test_v24386_active_verifier_external_gate.py",
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
        "one_fresh_external_active_verifier_probe_design",
        "external_probe_launch",
        "benchmark_launch",
        "additional_dev64_or_exact220",
        "evaluator",
        "leaderboard_or_sota",
    }
)
LAUNCH_AUTHORIZATION_KEYS = frozenset(
    {
        "one_fresh_external_active_verifier_probe_launch",
        "benchmark_launch",
        "additional_dev64_or_exact220",
        "evaluator",
    }
)


_ordinary = population_6._ordinary
_read = population_6._read
_sealed = population_6._sealed
publish = population_6.publish
_write_new = population_6._write_new
_git = population_6._git
_future = population_6._future
_port_listening = population_6._port_listening
_environment = population_6._environment
_integer = population_6._integer
_number = population_6._number


def _question_entity_vector(question: str) -> tuple[str, ...]:
    prefix = "Use public web sources to return one Markdown table about "
    suffix = ". The column names are:"
    if not question.startswith(prefix) or suffix not in question:
        raise ValueError("V2.43.86 external task template drifted")
    body = question[len(prefix) : question.index(suffix)]
    values = tuple(
        item.strip().casefold()
        for item in body.replace(", and ", ", ").split(", ")
    )
    if len(values) != 8 or any(not item for item in values):
        raise ValueError("V2.43.86 external entity vector drifted")
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
            population_5.QUESTIONS,
            population_6.QUESTIONS,
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
        and len(prior_questions) == 92
        and len(prior) == 736
        and current.isdisjoint(prior)
    )


def neutral_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED:
        raise ValueError("V2.43.86 neutral ordinal is invalid")
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
        f"{PROTOCOL_ID}|active-verifier-eight-plus-two|{ordinal}".encode("utf-8")
    ).hexdigest()


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.43.86 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    if (
        value.get("role") != "v24385_active_verifier_query_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("fresh_external_gate_design")
        is not True
        or value.get("authorization", {}).get("fresh_external_gate_launch")
        is not False
        or value.get("authorization", {}).get(
            "same_v24381_task_rerun_or_revaluation"
        )
        is not False
        or value.get("authorization", {}).get("new_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.86 parent audit drifted")
    return value


def _task_contract() -> dict[str, Any]:
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    return {
        "selected": SELECTED,
        "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
        "task_vector_validated_in_memory_before_protocol": len(tasks) == SELECTED,
        "fresh_128_entity_vector_disjoint_from_all_prior_external_gates": _fresh_entity_vector_valid(),
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_content_hash_persisted": False,
    }


def _mechanism_contract() -> dict[str, Any]:
    return {
        "active_verifier_runtime_policy": ACTIVE_VERIFIER_RUNTIME_POLICY_ID,
        "active_verifier_runner_policy": ACTIVE_VERIFIER_RUNNER_POLICY_ID,
        "projection_reads_v24384_envelope_v24383_result_v24349_parent": True,
        "three_stage_entropy_and_verification_accounting": True,
        "verifier_can_only_retain_or_revert_frozen_candidate": True,
        "minimum_active_retained_candidate_changed_cells": GATES[
            "minimum_active_retained_candidate_changed_cells"
        ],
        "selected_verification_status_counts_persisted_content_free": True,
    }


def _discovery_contract(seeds: Sequence[str]) -> dict[str, Any]:
    return {
        "logical_query_count": 4,
        "deterministic_batch_query_counts": [2, 2],
        "recursive_query_local_split_allowed": False,
        "full_capacity_proposal_batch_host_counts": [4, 4],
        "maximum_active_verifier_logical_queries": 2,
        "maximum_active_verifier_search_batches": 1,
        "proposal_selection_precedes_fetch_candidate_and_entropy": True,
        "active_query_generation_follows_candidate_and_support_freeze": True,
        "active_queries_use_only_frozen_row_column_value": True,
        "seed_sha256_vector": list(seeds),
        "seed_depends_only_on_protocol_and_fixed_ordinal": True,
        "proposal_source_cap": 8,
        "verifier_source_cap": 2,
        "selected_fetch_source_cap": 10,
        "parent_support_set_and_evidence_ids_reused_without_rebuild": True,
        "active_verifiers_can_only_retain_or_revert": True,
        "same_target_independent_conflict_reverts": True,
        "cross_target_relation_cannot_create_conflict": True,
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
    }


def _budget_contract() -> dict[str, Any]:
    return {
        "task_wall_seconds": TASK_WALL_SECONDS,
        "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
        "model_calls": 3,
        "maximum_logical_search_queries": 6,
        "maximum_hosted_search_batches": 3,
        "fetch_targets_total": 10,
        "page_characters": LIMITS.page_chars,
        "single_batch_no_resume_retry_skip_or_selective_rerun": True,
    }


def _lease_contract() -> dict[str, Any]:
    return {
        "path": str(LEASE_PATH),
        "owner": LEASE_OWNER,
        "purpose": LEASE_PURPOSE,
        "nonblocking_single_owner": True,
    }


def _protocol_source_policy() -> dict[str, bool]:
    return {
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "official_evaluator_called": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_external_active_verifier_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "additional_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


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
        raise RuntimeError("V2.43.86 external entity vector overlaps its parents")
    if require_pristine and not _future(
        root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.86 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24386_active_verifier_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "scope": "fresh_benchmark_external_active_verifier_query_entropy_gate",
        "task_contract": _task_contract(),
        "mechanism": _mechanism_contract(),
        "discovery_partition": _discovery_contract(seeds),
        "provider": _provider_contract(),
        "budget": _budget_contract(),
        "gates": dict(GATES),
        "lease": _lease_contract(),
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": _protocol_source_policy(),
        "authorization": _protocol_authorization(),
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
    encoded = json.dumps(protocol, ensure_ascii=False)
    if (
        set(protocol) != PROTOCOL_KEYS
        or protocol.get("artifact_version") != 1
        or protocol.get("role") != "v24386_active_verifier_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or isinstance(protocol.get("created_at_unix"), bool)
        or not isinstance(protocol.get("created_at_unix"), int)
        or protocol["created_at_unix"] < 0
        or protocol.get("gates") != GATES
        or protocol.get("scope")
        != "fresh_benchmark_external_active_verifier_query_entropy_gate"
        or protocol.get("task_contract") != _task_contract()
        or protocol.get("mechanism") != _mechanism_contract()
        or protocol.get("discovery_partition") != _discovery_contract(seeds)
        or protocol.get("provider") != _provider_contract()
        or protocol.get("budget") != _budget_contract()
        or protocol.get("lease") != _lease_contract()
        or protocol.get("source_policy") != _protocol_source_policy()
        or protocol.get("authorization") != _protocol_authorization()
        or not _fresh_entity_vector_valid()
        or len(set(seeds)) != SELECTED
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or any(
            task["opaque_id"] in encoded or task["question"] in encoded
            for task in tasks
        )
        or SECRET.search(encoded)
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.86 protocol drifted")
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
        "role": "v24386_active_verifier_external_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "fresh_external_task_and_active_verifier_vector_frozen": True,
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
            "one_fresh_external_active_verifier_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.86 preaudit failed: " + ",".join(findings))
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
    checks = value.get("checks")
    provenance = value.get("provenance")
    authorization = value.get("authorization")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24386_active_verifier_external_preactivation_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value["created_at_unix"] < 0
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or not isinstance(checks, Mapping)
        or set(checks)
        != {
            "protocol_valid_and_sealed",
            "fresh_external_task_and_active_verifier_vector_frozen",
            "focused_tests",
            "keyless_proxy_listening_without_api_request",
            "shared_api_lease_inactive",
            "protocol_commit_pushed",
            "worktree_clean",
            "future_surface_pristine",
            "protected_watchers_unchanged",
            "benchmark_or_evaluator_surface_authorized",
        }
        or any(
            checks.get(name) is not True
            for name in (
                "protocol_valid_and_sealed",
                "fresh_external_task_and_active_verifier_vector_frozen",
                "keyless_proxy_listening_without_api_request",
                "shared_api_lease_inactive",
                "protocol_commit_pushed",
                "worktree_clean",
                "future_surface_pristine",
                "protected_watchers_unchanged",
            )
        )
        or checks.get("benchmark_or_evaluator_surface_authorized") is not False
        or not isinstance(checks.get("focused_tests"), Mapping)
        or set(checks["focused_tests"]) != set(TEST_FILES)
        or any(item is not True for item in checks["focused_tests"].values())
        or not isinstance(provenance, Mapping)
        or set(provenance)
        != {
            "protocol_sha256",
            "parent_sha256",
            "surface_manifest_sha256",
            "head",
            "target_main",
        }
        or provenance.get("protocol_sha256") != sha256(root / PROTOCOL)
        or provenance.get("parent_sha256") != sha256(root / PARENT)
        or provenance.get("surface_manifest_sha256")
        != validate_protocol(root)["surface_manifest_sha256"]
        or re.fullmatch(r"[0-9a-f]{40}", str(provenance.get("head"))) is None
        or provenance.get("head") != provenance.get("target_main")
        or not isinstance(authorization, Mapping)
        or set(authorization) != LAUNCH_AUTHORIZATION_KEYS
        or authorization.get("one_fresh_external_active_verifier_probe_launch")
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
        raise RuntimeError("V2.43.86 preaudit drifted")
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
        "role": "v24386_active_verifier_external_activation",
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
            "one_fresh_external_active_verifier_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.86 activation failed")
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
        or value.get("role") != "v24386_active_verifier_external_activation"
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
        or authorization.get("one_fresh_external_active_verifier_probe_launch")
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
        raise RuntimeError("V2.43.86 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.43.86 execution surface is not pristine")
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
        "role": "v24386_active_verifier_external_execution_start",
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
        raise RuntimeError("V2.43.86 execution start failed: " + ",".join(findings))
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
        or value.get("role") != "v24386_active_verifier_external_execution_start"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value["created_at_unix"] < 0
        or value.get("status") != "ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or re.fullmatch(
            r"[0-9a-f]{40}", str(value.get("activation_base_commit"))
        )
        is None
        or value.get("activation_base_commit")
        != value.get("target_main_at_start")
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
        raise RuntimeError("V2.43.86 execution-start drifted")
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
        search = ActiveVerifierDeadlineAwareNativeSearchClient(
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
        outcome = run_v24384_task(
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

TASK_CHECK_NAMES = projection.TASK_CHECK_NAMES
TASK_KEYS = projection.TASK_KEYS
AGGREGATE_CHECK_NAMES = projection.AGGREGATE_CHECK_NAMES
AGGREGATE_KEYS = projection.AGGREGATE_KEYS
_task_checks = projection.task_checks
validate_task_projection = projection.validate_task_projection
_local_failure = projection.local_failure


def _task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return projection.task_projection(ordinal, parent, envelope)


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]], batch_wall_seconds: float
) -> dict[str, Any]:
    return projection.aggregate_tasks(tasks, batch_wall_seconds, GATES)


def _aggregate_checks(summary: Mapping[str, Any]) -> dict[str, bool]:
    return projection.aggregate_checks(summary, GATES)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    return projection.validate_aggregate(value, GATES)


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
        model_receipt_validator=lambda value: validate_model_receipt(
            value, expected_cap=MODEL_SLOT_CAP
        ),
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
        or value.get("role") != "v24386_active_verifier_external_result"
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
        or value.get(
            "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
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
        raise RuntimeError("V2.43.86 public result drifted or contains task content")
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
        raise RuntimeError("V2.43.86 result/git surface is not ready")
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
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=EXECUTOR_COUNT
            ) as pool:
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
            "role": "v24386_active_verifier_external_result",
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
        raise RuntimeError("V2.43.86 protected watcher identity drifted")
    return value


DECISION_OBSERVED_KEYS = (
    "selected",
    "terminal_success_tasks",
    "structurally_passed_tasks",
    "batch_wall_seconds",
    "throughput_tasks_per_minute",
    "completion_kinds",
    "exact_proposal_two_batch_tasks",
    "zero_recursive_split_tasks",
    "full_proposal_partition_tasks",
    "active_query_tasks",
    "active_search_tasks",
    "proposal_logical_queries",
    "active_verifier_logical_queries",
    "total_logical_queries",
    "proposal_search_batches",
    "active_verifier_search_batches",
    "total_search_batches",
    "parent_provider_search_calls",
    "active_provider_search_calls",
    "total_provider_search_calls",
    "proposal_sources",
    "proposal_unselected_sources",
    "active_discovered_sources",
    "active_selected_sources",
    "active_verifier_pages",
    "parent_eligible_support_tasks",
    "parent_eligible_support_set_count",
    "parent_candidate_tasks",
    "entropy_ranked_target_tasks",
    "selected_bound_candidate_tasks",
    "utility_aligned_tasks",
    "final_nonidentity_tasks",
    "candidate_changed_cells_before_active_verifier",
    "candidate_changed_cells_after_active_verifier",
    "active_verifier_reverted_cells",
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
        "role": "v24386_active_verifier_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_active_verifier_external_go"
            if passed
            else "fresh_active_verifier_external_no_go"
        ),
        "passed": passed,
        "failed_checks": sorted(
            name for name, check in aggregate["checks"].items() if not check
        ),
        "observed": {key: aggregate[key] for key in DECISION_OBSERVED_KEYS},
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
        },
        "claim_scope": {
            "fresh_benchmark_external_real_web_active_verifier_measured": True,
            "postcandidate_active_query_and_cell_retention_measured": True,
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
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "passed",
        "failed_checks",
        "observed",
        "provenance",
        "claim_scope",
        "authorization",
        "decision_payload_sha256",
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
    status = (
        "fresh_active_verifier_external_go"
        if passed
        else "fresh_active_verifier_external_no_go"
    )
    if (
        set(decision) != expected
        or decision.get("artifact_version") != 1
        or decision.get("role") != "v24386_active_verifier_external_decision"
        or decision.get("protocol_id") != PROTOCOL_ID
        or isinstance(decision.get("created_at_unix"), bool)
        or not isinstance(decision.get("created_at_unix"), int)
        or decision["created_at_unix"] < 0
        or decision.get("passed") is not passed
        or decision.get("status") != status
        or decision.get("failed_checks")
        != sorted(name for name, check in aggregate["checks"].items() if not check)
        or decision.get("observed")
        != {key: aggregate[key] for key in DECISION_OBSERVED_KEYS}
        or decision.get("provenance") != expected_provenance
        or not isinstance(claim_scope, Mapping)
        or set(claim_scope)
        != {
            "fresh_benchmark_external_real_web_active_verifier_measured",
            "postcandidate_active_query_and_cell_retention_measured",
            "proposal_entropy_verifier_outcome_and_utility_credit_measured",
            "benchmark_quality_measured",
            "entropy_quality_improvement_proven",
            "future_population_or_sota_supported",
        }
        or any(
            claim_scope.get(name) is not True
            for name in (
                "fresh_benchmark_external_real_web_active_verifier_measured",
                "postcandidate_active_query_and_cell_retention_measured",
                "proposal_entropy_verifier_outcome_and_utility_credit_measured",
            )
        )
        or any(
            claim_scope.get(name) is not False
            for name in (
                "benchmark_quality_measured",
                "entropy_quality_improvement_proven",
                "future_population_or_sota_supported",
            )
        )
        or not isinstance(authorization, Mapping)
        or set(authorization)
        != {
            "fresh_paired_dev64_design",
            "fresh_paired_dev64_launch",
            "new_exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or authorization.get("fresh_paired_dev64_design") is not passed
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
        raise RuntimeError("V2.43.86 decision drifted")
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
        "role": "v24386_active_verifier_external_postresult_audit",
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
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "result_sha256",
        "decision_sha256",
        "decision_status",
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
    findings = audit.get("findings")
    authorization = audit.get("authorization")
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
        or audit.get("role") != "v24386_active_verifier_external_postresult_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or isinstance(audit.get("created_at_unix"), bool)
        or not isinstance(audit.get("created_at_unix"), int)
        or audit["created_at_unix"] < 0
        or audit.get("result_sha256") != sha256(root / RESULT)
        or audit.get("decision_sha256") != sha256(root / DECISION)
        or audit.get("decision_status") != decision["status"]
        or audit.get("temporary_execution_directory_remaining") is not False
        or not isinstance(audit.get("shared_api_lease_active"), bool)
        or audit.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or audit.get(
            "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted"
        )
        is not False
        or audit.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or not isinstance(findings, list)
        or findings != expected_findings
        or audit.get("audit_valid") is not (not expected_findings)
        or not isinstance(authorization, Mapping)
        or set(authorization)
        != {
            "fresh_paired_dev64_design",
            "fresh_paired_dev64_launch",
            "new_exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or authorization.get("fresh_paired_dev64_design")
        is not (decision["passed"] and not expected_findings)
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
        raise RuntimeError("V2.43.86 postresult audit drifted")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "protocol",
            "preaudit",
            "activation",
            "start",
            "run",
            "finalize",
            "child",
        ),
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
            parser.error(
                "child requires ordinal, output-root, directory, and slots"
            )
        _child(args)


if __name__ == "__main__":
    main()
