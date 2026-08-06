#!/usr/bin/env python3
"""Publish the design-only V2.46.51 external protocol.

This control surface only publishes an inert protocol.  It cannot preaudit,
activate, start, run, evaluate, resume, retry, or selectively rerun.  It reads
visible task surfaces and content-free public parent audits, but never opens or
hashes the private population, gold, provenance, or evaluator.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24651_ror_external_contract import (  # noqa: E402
    ACTIVATION,
    ARM_COUNT,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PARENT_TIMEOUT_SECONDS,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    SEARCH,
    SELECTED_COUNT,
    TREATMENT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    task_vector,
)


DATE = "20260806"
ZERO_INTERVENTION = Path(
    f"results/v24647_v24645_zero_intervention_diagnosis_v1_{DATE}.json"
)
MECHANISM_BUILD = Path(
    f"results/v24649_unknown_target_structured_build_audit_v2_{DATE}.json"
)
POPULATION_DESIGN = Path(f"results/v24650_ror_population_design_v1_{DATE}.json")
PACKAGE_BUILD = Path(f"results/v24652_external_package_build_audit_v1_{DATE}.json")
DEPENDENCIES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24468_total_wall_transport.py",
    "src/deepwide_agent/v24630_thin_backfill_search.py",
    "src/deepwide_agent/v24637_objective_alignment_runtime.py",
    "src/deepwide_agent/v24639_ror_objective_runtime.py",
    "src/deepwide_agent/v24640_evidence_constrained_runtime.py",
    "src/deepwide_agent/v24642_deterministic_pair_runtime.py",
    "src/deepwide_agent/v24644_primary_identity_pair_runtime.py",
    "src/deepwide_agent/v24648_unknown_target_structured_runtime.py",
    "src/deepwide_agent/v24651_ror_external_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/v24468_total_wall_http_helper.py",
    "scripts/run_v24651_ror_task.py",
    "scripts/run_v24651_unknown_target_structured.py",
    "scripts/audit_v24651_unknown_target_forward.py",
    "tests/test_v24648_unknown_target_structured_runtime.py",
    "tests/test_v24651_external_package.py",
    "tests/test_v24651_forward_package.py",
    str(ZERO_INTERVENTION),
    str(MECHANISM_BUILD),
    str(POPULATION_DESIGN),
    str(PACKAGE_BUILD),
)
FORBIDDEN_DEPENDENCY_MARKERS = (
    "evaluation/",
    "external_evaluator",
    "ror_population_private",
    "ror_gold_v1",
    "ror_gold_provenance",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.51 preregistration expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.51 preregistration expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parents() -> dict[str, dict[str, Any]]:
    diagnosis = _read(ROOT / ZERO_INTERVENTION)
    mechanism = _read(ROOT / MECHANISM_BUILD)
    population = _read(ROOT / POPULATION_DESIGN)
    package = _read(ROOT / PACKAGE_BUILD)
    if (
        diagnosis.get("role")
        != "v24647_v24645_zero_intervention_postfreeze_diagnosis"
        or not _sealed(diagnosis, "diagnosis_sha256")
        or diagnosis.get("diagnosis", {}).get(
            "current_bottleneck_is_unknown_target_structured_pair_acquisition"
        )
        is not True
        or diagnosis.get("authorization", {}).get("fresh_external_successor_launch")
        is not False
        or mechanism.get("role") != "v24649_unknown_target_structured_build_audit"
        or not _sealed(mechanism, "audit_payload_sha256")
        or mechanism.get("audit_valid") is not True
        or mechanism.get("findings") != []
        or mechanism.get("supersedes", {}).get("v1_authorizes_successor_use")
        is not False
        or population.get("role") != "v24650_ror_population_design"
        or not _sealed(population, "design_sha256")
        or population.get("selected_count") != 48
        or population.get("historical_entity_count") != 4_480
        or population.get("historical_canonical_count") != 4_480
        or population.get("authorization", {}).get("activation_or_launch") is not False
        or package.get("role") != "v24652_external_package_build_audit"
        or not _sealed(package, "audit_payload_sha256")
        or package.get("audit_valid") is not True
        or package.get("findings") != []
        or package.get("authorization", {}).get("external_protocol_publication")
        is not True
        or package.get("authorization", {}).get("preactivation_audit") is not False
        or package.get("authorization", {}).get("activation_or_launch") is not False
    ):
        raise RuntimeError("V2.46.51 preregistration parent drifted")
    return {
        "zero_intervention_diagnosis": diagnosis,
        "mechanism_build": mechanism,
        "population_design": population,
        "package_build": package,
    }


def build_protocol(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.46.51 preregistration requires clean pushed HEAD")
    future = (
        PROTOCOL,
        PREAUDIT,
        ACTIVATION,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.46.51 future surface not pristine")
    parents = _parents()
    if any(
        marker in dependency
        for dependency in DEPENDENCIES
        for marker in FORBIDDEN_DEPENDENCY_MARKERS
    ):
        raise RuntimeError("V2.46.51 forward dependency contains evaluator surface")
    manifest = {path: sha256(ROOT / path) for path in DEPENDENCIES}
    tasks = task_vector()
    identifiers = [task["opaque_id"] for task in tasks]
    questions = [task["question"] for task in tasks]
    population = parents["population_design"]
    value = {
        "artifact_version": 1,
        "role": "v24651_unknown_target_structured_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "zero_intervention_diagnosis_path": str(ZERO_INTERVENTION),
            "zero_intervention_diagnosis_sha256": sha256(ROOT / ZERO_INTERVENTION),
            "mechanism_build_path": str(MECHANISM_BUILD),
            "mechanism_build_sha256": sha256(ROOT / MECHANISM_BUILD),
            "population_design_path": str(POPULATION_DESIGN),
            "population_design_sha256": sha256(ROOT / POPULATION_DESIGN),
            "package_build_path": str(PACKAGE_BUILD),
            "package_build_sha256": sha256(ROOT / PACKAGE_BUILD),
            "v24645_population_consumed_and_strict_no_go": True,
            "v24645_retry_resume_selective_rerun_or_revaluation": False,
        },
        "population": {
            "immutable_ror_commit": population["commit"],
            "immutable_ror_tree": population["directory_tree_sha1"],
            "lexicographic_slice_start_inclusive": population[
                "slice_start_inclusive"
            ],
            "lexicographic_slice_stop_exclusive": population[
                "slice_stop_exclusive"
            ],
            "historical_entity_count": population["historical_entity_count"],
            "historical_canonical_count": population["historical_canonical_count"],
            "fresh_entity_count": population["selected_count"],
            "fresh_country_count": population["selected_country_count"],
            "selected_country_max": population["selected_country_max"],
            "selection_rule": population["selection_rule"],
            "selected_visible_vector_sha256": population[
                "selected_visible_vector_sha256"
            ],
            "selected_record_vector_sha256": population[
                "selected_record_vector_sha256"
            ],
            "literal_and_canonical_overlap_with_history": 0,
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_tasks": SELECTED_COUNT,
            "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
            "entities_per_task": 4,
            "selected_ids": identifiers,
            "selected_ids_sha256": payload_sha256(identifiers),
            "visible_question_vector_sha256": payload_sha256(questions),
            "private_population_gold_provenance_and_evaluator_absent_from_forward_manifest": True,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "output_root": str(OUTPUT_ROOT),
            "protected_watchers": protected_watcher_snapshot(),
            "one_wave_no_resume_retry_skip_or_selective_rerun": True,
            "failure_as_zero": True,
        },
        "mechanism": {
            "runtime_policy": "v24648_unknown_target_official_structured_lookup_v1",
            "shared_plan_search_generic_fetch_baseline_prefix": True,
            "baseline_precedes_unknown_target_lookup": True,
            "exact_provider_model_calls_per_valid_task": 2,
            "hosted_search_query_cap": 4,
            "generic_fetch_cap": TREATMENT["generic_fetch_cap"],
            "unknown_target_lookup_cap": TREATMENT["unknown_target_lookup_cap"],
            "total_fetch_cap": LIMITS["fetch_targets"],
            "candidate_consumes_only_new_lookup_projection": True,
            "official_query_mode": TREATMENT["official_query_mode"],
            "targeted_lookup_max_page_chars": TREATMENT[
                "targeted_lookup_max_page_chars"
            ],
            "full_response_required_before_uniqueness_claim": True,
            "unique_normalized_ror_display_required": True,
            "structured_parse_or_pagination_failure_abstains": True,
            "nonunknown_ror_and_all_country_cells_immutable": True,
            "quality_cost_pareto_gate_not_equal_effect_causal_ablation": True,
        },
        "limits": LIMITS,
        "model": MODEL,
        "search": SEARCH,
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
        },
        "evaluation_separation": {
            "all_predictions_frozen_before_gold_provenance_or_evaluator_open": True,
            "forward_dependency_manifest_excludes_private_population_gold_provenance_and_evaluator": True,
            "mechanism_gate_before_gold_open": "at_least_one_admitted_identity_bound_unknown_target_replacement",
            "zero_admission_stops_without_gold_or_evaluator": True,
            "fixed_denominator_failure_as_zero": True,
            "primary_metric": "exact_table_successes",
            "go_rule": "strict_candidate_exact_table_gain_nonnegative_composite_and_nonnegative_item_f1",
            "guardrails": [
                "candidate_composite_not_lower",
                "candidate_item_f1_not_lower",
            ],
            "unknown_value_cells_diagnostic_only": True,
            "official_deepwidebench_evaluator": False,
        },
        "entropy_credit_scope": {
            "primary_identity_binding_precedes_target_value_binding": True,
            "target_value_binding_precedes_information_gain": True,
            "information_gain_shadow_only_during_forward": True,
            "zero_intervention_or_zero_outer_utility_receives_positive_task_credit": False,
            "positive_task_credit_requires_postfreeze_outer_utility": True,
            "entropy_or_credit_assignment_validated_by_protocol": False,
        },
        "source_policy": {
            "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read_by_forward": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "deepwidebench_task_gold_or_error_pattern_used": False,
        },
        "authorization": {
            "protocol_published": True,
            "preactivation_audit": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    protocol = build_protocol()
    publish(ROOT / PROTOCOL, protocol)
    print(
        json.dumps(
            {
                "path": str(PROTOCOL),
                "protocol_id": protocol["protocol_id"],
                "launch_authorized": protocol["authorization"][
                    "one_external_forward_launch"
                ],
                "protocol_sha256": protocol["protocol_sha256"],
            },
            sort_keys=True,
        )
    )
