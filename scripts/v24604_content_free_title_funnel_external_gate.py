#!/usr/bin/env python3
"""Fresh external gate for same-budget content-free title-funnel observation.

The V2.45.96 population is closed and consumed.  This successor starts after
476 external questions and 3,808 entities, uses a literal/canonical-disjoint
8-task/64-entity population, and requires both query surfaces to be uniquely
reachable through the unchanged exact-title and alias-title validators.

Runtime input remains exactly ``opaque_id`` and ``question``.  V2.45.98--
V2.46.01 provide the observer, proof, total projection, and bounded parent;
V2.46.02 provides the instance-local immutable V2.46.00 collector.  The probe
only measures fixed-vocabulary title-funnel counts.  Query/search/fetch,
ranking, title validator, page/source/model, evidence, posterior, margin,
leave-one-out, safe-change, decision-credit, and evaluator rules are unchanged.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent.v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    _baseline_cells,
)
from deepwide_agent import v24589_validator_aligned_title_query as query_policy  # noqa: E402
from deepwide_agent import v24599_proof_carrying_title_funnel as proof  # noqa: E402
from deepwide_agent import v24600_total_title_funnel_projection as total  # noqa: E402
from deepwide_agent import v24601_bounded_title_funnel_parent as bounded  # noqa: E402
from scripts import audit_v24603_title_funnel_build as build_gate  # noqa: E402
from scripts import v24596_validator_aligned_title_query_external_gate as previous_run  # noqa: E402
from scripts import v24602_title_funnel_collector_repair as collector_repair  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24604_fresh_content_free_title_funnel_external_gate_v1"
PROTOCOL = Path(
    f"results/v24604_content_free_title_funnel_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24604_content_free_title_funnel_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24604_content_free_title_funnel_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24604_content_free_title_funnel_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24604_content_free_title_funnel_external_result_v1_{DATE}.json"
)
DECISION = Path(
    f"results/v24604_content_free_title_funnel_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24604_content_free_title_funnel_external_postresult_audit_v1_{DATE}.json"
)
PARENT = build_gate.AUDIT
PREVIOUS_RESULT = previous_run.RESULT
PREVIOUS_DECISION = previous_run.DECISION
PREVIOUS_POSTAUDIT = previous_run.POSTAUDIT
RUNNER_MARKER = "scripts/v24604_content_free_title_funnel_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_content_free_title_funnel_external_gate"
PRIOR_QUESTION_COUNT = 476
PRIOR_ENTITY_COUNT = 3808
PRIOR_QUESTIONS = previous_run._prior_questions() + previous_run.QUESTIONS

previous = previous_run.previous
runtime = previous_run.runtime
base = previous_run.base
population = previous_run.population
repair = previous_run.repair
alias_projection = previous_run.alias_projection
acquisition = previous_run.acquisition
surface = previous_run.surface
planner = previous_run.planner
STRICT_TASK_FIELD = previous_run.STRICT_TASK_FIELD


ENTITY_GROUPS = (
    (
        "Limkokwing University of Creative Technology Eswatini",
        "Lesotho College of Education",
        "Mulungushi University",
        "Zambia Catholic University",
        "Midlands State University",
        "Africa University Zimbabwe",
        "Chinhoyi University of Technology",
        "Great Zimbabwe University",
    ),
    (
        "Lupane State University",
        "Womens University in Africa",
        "Catholic University of Malawi",
        "Somali National University",
        "Catholic University of Angola",
        "Catholic University of Congo",
        "University of Yaounde I",
        "Nazi Boni University",
    ),
    (
        "University of Nouakchott Al Aasriya",
        "Fourah Bay College",
        "Khesar Gyalpo University of Medical Sciences of Bhutan",
        "Maldives National University",
        "Islamic University of Maldives",
        "Sultan Sharif Ali Islamic University",
        "Souphanouvong University",
        "Savannakhet University",
    ),
    (
        "University of Health Sciences Laos",
        "University of Health Sciences Cambodia",
        "Build Bright University",
        "Pannasastra University of Cambodia",
        "National University of Management Cambodia",
        "Yangon Technological University",
        "Yezin Agricultural University",
        "National University of East Timor",
    ),
    (
        "Dili Institute of Technology",
        "Mongolian National University of Medical Sciences",
        "University of Finance and Economics Mongolia",
        "Otgontenger University",
        "Kyrgyz National University",
        "Kyrgyz Russian Slavic University",
        "Tajik National University",
        "Russian Tajik Slavonic University",
    ),
    (
        "Technological University of Tajikistan",
        "Turkmen State University",
        "Turkmenistan State Institute of Economics and Management",
        "Tashkent State University of Economics",
        "Bukhara State University",
        "Urgench State University",
        "Karakalpak State University",
        "LN Gumilyov Eurasian National University",
    ),
    (
        "Suleyman Demirel University Kazakhstan",
        "Abylai Khan University",
        "French University in Armenia",
        "Russian Armenian University",
        "Free University of Tbilisi",
        "Azerbaijan State University of Economics",
        "Azerbaijan Technical University",
        "Western Caspian University",
    ),
    (
        "Nakhchivan State University",
        "College of Micronesia FSM",
        "College of the Marshall Islands",
        "Pacific Adventist University",
        "Papua New Guinea University of Technology",
        "Ross University School of Medicine",
        "All Saints University Dominica",
        "National University of Itapua",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.46.04 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
ALIAS_TITLE_GROUPS = tuple(
    tuple(
        f"{acquisition.primary_alias_surface(entity)} history" for entity in group
    )
    for group in ENTITY_GROUPS
)
GATES = {
    **copy.deepcopy(previous_run.GATES),
    "minimum_validator_aligned_title_query_activity_tasks": 0,
    "minimum_validator_aligned_title_query_full_surface_tasks": 0,
    "minimum_title_query_and_title_replacement_cooccurrence_tasks": 0,
    "minimum_content_free_title_funnel_activity_tasks": 1,
    "minimum_content_free_title_funnel_visible_input_lead_count": 1,
}
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *previous_run.SOURCE_FILES,
            str(PREVIOUS_RESULT),
            str(PREVIOUS_DECISION),
            str(PREVIOUS_POSTAUDIT),
            "scripts/diagnose_v24597_v24596_title_transport.py",
            "tests/test_diagnose_v24597_v24596_title_transport.py",
            "results/v24597_v24596_title_transport_diagnosis_v1_20260805.json",
            "src/deepwide_agent/v24598_content_free_title_funnel.py",
            "tests/test_v24598_content_free_title_funnel.py",
            "src/deepwide_agent/v24599_proof_carrying_title_funnel.py",
            "tests/test_v24599_proof_carrying_title_funnel.py",
            "src/deepwide_agent/v24600_total_title_funnel_projection.py",
            "tests/test_v24600_total_title_funnel_projection.py",
            "src/deepwide_agent/v24601_bounded_title_funnel_parent.py",
            "tests/test_v24601_bounded_title_funnel_parent.py",
            "scripts/v24602_title_funnel_collector_repair.py",
            "tests/test_v24602_title_funnel_collector_repair.py",
            "scripts/audit_v24603_title_funnel_build.py",
            "tests/test_audit_v24603_title_funnel_build.py",
            str(PARENT),
            RUNNER_MARKER,
            "tests/test_v24604_content_free_title_funnel_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *previous_run.TEST_SUITES,
    ("tests/test_diagnose_v24597_v24596_title_transport.py", 7, 120),
    ("tests/test_v24598_content_free_title_funnel.py", 7, 120),
    ("tests/test_v24599_proof_carrying_title_funnel.py", 7, 300),
    ("tests/test_v24600_total_title_funnel_projection.py", 6, 300),
    ("tests/test_v24601_bounded_title_funnel_parent.py", 5, 300),
    ("tests/test_v24602_title_funnel_collector_repair.py", 7, 360),
    ("tests/test_audit_v24603_title_funnel_build.py", 8, 180),
    ("tests/test_v24604_content_free_title_funnel_external_gate.py", 16, 600),
)
EXPECTED_TEST_COUNT = previous_run.EXPECTED_TEST_COUNT + 63


_PREVIOUS_BUILD_PROTOCOL = previous_run._PREVIOUS_BUILD_PROTOCOL
_PREVIOUS_VALIDATE_PROTOCOL = previous_run._PREVIOUS_VALIDATE_PROTOCOL
_PREVIOUS_BUILD_PREAUDIT = previous_run._PREVIOUS_BUILD_PREAUDIT
_PREVIOUS_VALIDATE_PREAUDIT = previous_run._PREVIOUS_VALIDATE_PREAUDIT
_PREVIOUS_BUILD_ACTIVATION = previous_run._PREVIOUS_BUILD_ACTIVATION
_PREVIOUS_VALIDATE_ACTIVATION = previous_run._PREVIOUS_VALIDATE_ACTIVATION
_PREVIOUS_BUILD_EXECUTION_START = previous_run._PREVIOUS_BUILD_EXECUTION_START
_PREVIOUS_VALIDATE_EXECUTION_START = previous_run._PREVIOUS_VALIDATE_EXECUTION_START
_PREVIOUS_VALIDATE_PUBLIC_RESULT = previous_run._PREVIOUS_VALIDATE_PUBLIC_RESULT
_PREVIOUS_RUN_PROBE = previous_run._PREVIOUS_RUN_PROBE
_PREVIOUS_RUN_PROCESS_SUBCOMMAND = previous_run._PREVIOUS_RUN_PROCESS_SUBCOMMAND
_INHERITED_MECHANISM_PASSED = previous_run.mechanism_passed
_INHERITED_DIAGNOSTIC_ROUTE = previous_run.diagnostic_route
_INHERITED_ORIGINAL_TASK_PROJECTION = runtime._ORIGINAL_TASK_PROJECTION
_MISSING = object()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.04 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    baseline = value.get("freshness_baseline", {})
    stress = value.get("collector", {}).get("stress", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24603_title_funnel_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 73
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or stress.get("workers") != 8
        or stress.get("validations") != 8
        or stress.get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or baseline.get("prior_external_question_count") != PRIOR_QUESTION_COUNT
        or baseline.get("prior_external_entity_count") != PRIOR_ENTITY_COUNT
        or baseline.get("v24596_population_resume_retry_rerun_or_evaluation_authorized")
        is not False
        or authorization.get(
            "fresh_disjoint_content_free_title_funnel_external_protocol_design"
        )
        is not True
        or authorization.get("query_policy_or_title_validator_change") is not False
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.04 build parent drifted")
    return value


def _previous_closed() -> bool:
    result = _read(PREVIOUS_RESULT)
    decision = _read(PREVIOUS_DECISION)
    postaudit = _read(PREVIOUS_POSTAUDIT)
    mechanism = result.get("mechanism_aggregate", {})
    return (
        _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
        and result.get("protocol_id") == previous_run.PROTOCOL_ID
        and result.get("selected") == 8
        and result.get("passed") is False
        and result.get("mechanism_passed") is False
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and mechanism.get("success_tasks") == 8
        and mechanism.get("failure_as_zero_tasks") == 0
        and mechanism.get("validator_aligned_title_query_activity_tasks") == 7
        and mechanism.get("validator_aligned_title_query_full_surface_tasks") == 7
        and mechanism.get("prededup_and_title_replacement_cooccurrence_tasks") == 0
        and mechanism.get("validator_aligned_title_replacement_tasks") == 0
        and decision.get("status")
        == "fresh_validator_aligned_title_query_no_go"
        and decision.get("diagnostic_route")
        == "validator_aligned_title_acquisition_successor"
        and decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is False
        and decision.get("authorization", {}).get("new_exact220") is False
        and postaudit.get("audit_valid") is True
        and postaudit.get("findings") == []
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("inherited_original_task_projection_rebound") is False
        and _parent(ROOT).get("audit_valid") is True
    )


def _prior_questions() -> tuple[str, ...]:
    return PRIOR_QUESTIONS


def _fresh_entity_vector_valid() -> bool:
    current = {
        entity
        for question in QUESTIONS
        for entity in population._question_entity_vector(question)
    }
    prior = {
        entity
        for question in _prior_questions()
        for entity in population._question_entity_vector(question)
    }
    current_canonical = {population._canonical_entity(item) for item in current}
    prior_canonical = {population._canonical_entity(item) for item in prior}
    return (
        len(QUESTIONS) == 8
        and len(current) == 64
        and len(current_canonical) == 64
        and len(_prior_questions()) == PRIOR_QUESTION_COUNT
        and len(prior) == PRIOR_ENTITY_COUNT
        and len(prior_canonical) == PRIOR_ENTITY_COUNT
        and current.isdisjoint(prior)
        and current_canonical.isdisjoint(prior_canonical)
    )


def _title_query_surface_vector_valid() -> bool:
    all_primary: list[str] = []
    for entities in ENTITY_GROUPS:
        baseline = (
            "```markdown\n| University | Founding year |\n| --- | --- |\n"
            + "\n".join(f"| {entity} | Unknown |" for entity in entities)
            + "\n```"
        )
        cells = _baseline_cells(baseline)
        for entity in entities:
            primary = acquisition.primary_alias_surface(entity)
            full, second, _mode = query_policy._surface_vector(entity)
            exact = alias_projection.title._unique_title_row(
                f"{full} history", cells
            )
            alias = alias_projection.unique_alias_title_row(
                f"{second} history", cells
            )
            queries = query_policy.validator_aligned_query_vector(
                entity, "Founding year"
            )
            if (
                primary is None
                or exact is None
                or exact[0] != entity
                or alias is None
                or alias.row_key != entity
                or f'"{full}"' not in queries[0]
                or f'"{second}"' not in queries[1]
            ):
                return False
            all_primary.append(primary.casefold())
    return len(all_primary) == 64 and len(set(all_primary)) == 64


def _alias_surface_vector_valid() -> bool:
    return _title_query_surface_vector_valid()


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_476_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_primary_alias_surfaces_globally_unique": _title_query_surface_vector_valid(),
        "all_64_full_surfaces_uniquely_reachable_by_unchanged_exact_title_parent": _title_query_surface_vector_valid(),
        "all_64_second_surfaces_uniquely_reachable_by_unchanged_alias_title_validator": _title_query_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_populations_through_v24596_counted_as_consumed": True,
        "prior_population_resume_retry_rerun_or_evaluation": False,
        "population_selection_uses_visible_names_and_frozen_validator_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_content_free_title_funnel_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_content_free_title_funnel_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def _successor_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.46.04 V2.45.96 closure drifted")
    return {
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "v24596_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24596_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24596_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "same_or_prior_population_resume_retry_rerun_or_evaluation": False,
        "new_population_reuses_prior_question_or_entity": False,
        "validator_aligned_title_query_policy": query_policy.POLICY_ID,
        "proof_carrying_validator_aligned_title_query_policy": proof.parent_proof.POLICY_ID,
        "total_validator_aligned_title_query_projection_policy": total.parent.POLICY_ID,
        "bounded_validator_aligned_title_query_parent_policy": bounded.frozen.POLICY_ID,
        "content_free_title_funnel_policy": proof.funnel_policy.POLICY_ID,
        "proof_carrying_content_free_title_funnel_policy": proof.POLICY_ID,
        "total_content_free_title_funnel_projection_policy": total.POLICY_ID,
        "bounded_content_free_title_funnel_parent_policy": bounded.POLICY_ID,
        "immutable_title_funnel_collector_policy": collector_repair.POLICY_ID,
        "collector_projector_is_module_load_unbound_v24600_function": True,
        "controller_rebinds_inherited_original_task_projection": False,
        "complete_nested_protocol_validation_critical_section_serialized": True,
        "task_execution_remains_parallel_after_protocol_validation": True,
        "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
        "query_ranking_title_validator_or_evidence_projection_changed": False,
        "source_posterior_margin_leave_one_out_safe_change_or_decision_credit_rules_relaxed": False,
        "title_funnel_claims_retrieval_effect_quality_or_causality": False,
        "raw_title_query_url_or_page_text_emitted": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        value.get("content_free_title_funnel_activity_tasks", 0)
        >= GATES["minimum_content_free_title_funnel_activity_tasks"]
        and value.get("total_content_free_title_funnel_count_fields", {}).get(
            "visible_input_lead_count", 0
        )
        >= GATES["minimum_content_free_title_funnel_visible_input_lead_count"]
        and value.get(
            "all_content_free_title_funnel_success_rows_consumed_validated_capabilities"
        )
        is True
        and value.get(
            "all_content_free_title_funnel_failure_rows_are_content_free_zero_projections"
        )
        is True
        and value.get(
            "content_free_title_funnel_failure_rows_claim_zero_private_effects"
        )
        is False
        and value.get("content_free_title_funnel_private_content_emitted") is False
        and value.get("content_free_title_funnel_privileged_evaluator_content_read")
        is False
        and value.get(
            "content_free_title_funnel_projection_claims_retrieval_effect_or_causality"
        )
        is False
        and value.get("content_free_title_funnel_changes_effect_or_credit_surface")
        is False
    )


def diagnostic_route(
    mechanism: Mapping[str, Any],
    supervision: Mapping[str, Any],
    *,
    diagnostic: bool,
    reliability: bool,
    parent_validation: bool,
    latency: bool,
) -> str:
    if not reliability:
        return "title_funnel_reliability_successor"
    if not parent_validation:
        return "title_funnel_parent_validation_successor"
    if not latency:
        return "title_funnel_latency_successor"
    if int(mechanism.get("content_free_title_funnel_activity_tasks", 0)) == 0:
        return "title_funnel_runtime_successor"
    counts = mechanism.get("total_content_free_title_funnel_count_fields", {})
    if int(counts.get("visible_input_lead_count", 0)) == 0:
        return "title_funnel_visible_lead_successor"
    if int(counts.get("nonempty_title_lead_count", 0)) == 0:
        return "search_title_transport_successor"
    if int(counts.get("canonical_row_token_anywhere_title_lead_count", 0)) == 0:
        return "title_entity_surface_acquisition_successor"
    if int(counts.get("alias_surface_anywhere_title_lead_count", 0)) == 0:
        return "title_alias_surface_acquisition_successor"
    if int(counts.get("surface_rejected_only_by_maximum_start_lead_count", 0)) > 0:
        return "title_match_start_policy_diagnosis"
    if int(counts.get("surface_rejected_only_by_type_compatibility_lead_count", 0)) > 0:
        return "title_type_compatibility_policy_diagnosis"
    if int(counts.get("strict_validator_aligned_title_lead_count", 0)) > 0:
        return "title_selection_conversion_diagnosis"
    return "title_funnel_unresolved_successor"


@contextmanager
def configured_previous(*, validator_names: Sequence[str] = ()) -> Iterator[None]:
    if runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION:
        raise RuntimeError("V2.46.04 inherited original projector drifted")
    previous_patches: dict[str, Any] = {
        "PROTOCOL_ID": PROTOCOL_ID,
        "PROTOCOL": PROTOCOL,
        "PREAUDIT": PREAUDIT,
        "ACTIVATION": ACTIVATION,
        "EXECUTION_START": EXECUTION_START,
        "RESULT": RESULT,
        "DECISION": DECISION,
        "POSTAUDIT": POSTAUDIT,
        "PARENT": PARENT,
        "RUNNER_MARKER": RUNNER_MARKER,
        "LEASE_OWNER": LEASE_OWNER,
        "LEASE_PURPOSE": LEASE_PURPOSE,
        "PRIOR_QUESTION_COUNT": PRIOR_QUESTION_COUNT,
        "PRIOR_ENTITY_COUNT": PRIOR_ENTITY_COUNT,
        "PRIOR_QUESTIONS": PRIOR_QUESTIONS,
        "ENTITY_GROUPS": ENTITY_GROUPS,
        "ALIAS_TITLE_GROUPS": ALIAS_TITLE_GROUPS,
        "QUESTIONS": QUESTIONS,
        "GATES": GATES,
        "SOURCE_FILES": SOURCE_FILES,
        "TEST_SUITES": TEST_SUITES,
        "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
        "proof": proof,
        "total": total,
        "bounded": bounded,
        "_prior_questions": _prior_questions,
        "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
        "_alias_surface_vector_valid": _alias_surface_vector_valid,
        "_parent": _parent,
        "_quarantine_valid": _previous_closed,
        "_task_contract": _task_contract,
        "_protocol_authorization": _protocol_authorization,
        "_activation_authorization": _activation_authorization,
        "_successor_binding": _successor_binding,
        "mechanism_passed": mechanism_passed,
        "diagnostic_route": diagnostic_route,
    }
    validators = {
        "validate_protocol": validate_protocol,
        "validate_preaudit": validate_preaudit,
        "validate_activation": validate_activation,
        "validate_execution_start": validate_execution_start,
        "validate_public_result": validate_public_result,
    }
    for name in validator_names:
        previous_patches[name] = validators[name]
    runtime_patches = {
        "proof": proof,
        "total": total,
        "bounded": bounded,
        "capability_collection": collector_repair.capability_collection,
        "aggregate_strict_projections": collector_repair.aggregate_projections,
        "mechanism_passed": mechanism_passed,
        "diagnostic_route": diagnostic_route,
    }
    previous_originals = {
        name: getattr(previous, name, _MISSING) for name in previous_patches
    }
    runtime_originals = {
        name: getattr(runtime, name, _MISSING) for name in runtime_patches
    }
    task_field_original = getattr(total, "TASK_FIELD", _MISSING)
    try:
        for name, value in previous_patches.items():
            setattr(previous, name, value)
        for name, value in runtime_patches.items():
            setattr(runtime, name, value)
        total.TASK_FIELD = STRICT_TASK_FIELD
        yield
    finally:
        if task_field_original is _MISSING:
            delattr(total, "TASK_FIELD")
        else:
            total.TASK_FIELD = task_field_original
        for owner, originals in (
            (runtime, runtime_originals),
            (previous, previous_originals),
        ):
            for name, value in originals.items():
                if value is _MISSING:
                    delattr(owner, name)
                else:
                    setattr(owner, name, value)
        if runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION:
            raise RuntimeError("V2.46.04 inherited original projector was rebound")


_MECHANISM_FIELDS = (
    "prededup_candidate_preservation_policy",
    "proof_carrying_prededup_preservation_policy",
    "total_prededup_preservation_projection_policy",
    "bounded_prededup_preservation_parent_policy",
    "validator_aligned_title_query_policy",
    "proof_carrying_validator_aligned_title_query_policy",
    "total_validator_aligned_title_query_projection_policy",
    "bounded_validator_aligned_title_query_parent_policy",
    "content_free_title_funnel_policy",
    "proof_carrying_content_free_title_funnel_policy",
    "total_content_free_title_funnel_projection_policy",
    "bounded_content_free_title_funnel_parent_policy",
    "immutable_title_funnel_collector_policy",
    "collector_projector_is_module_load_unbound_v24600_function",
    "controller_rebinds_inherited_original_task_projection",
    "exact_url_distinct_candidates_preserved_before_registrable_source_selection",
    "title_funnel_observation_required",
    "title_funnel_claims_retrieval_effect_quality_or_causality",
    "raw_title_query_url_or_page_text_emitted",
    "logical_query_search_batch_fetch_page_source_or_model_budget_changed",
    "query_ranking_title_validator_or_evidence_projection_changed",
    "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit",
)


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.46.04 predecessor is not closed")
    _parent(ROOT)
    with configured_previous():
        value = _PREVIOUS_BUILD_PROTOCOL(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["scope"] = "fresh_content_free_title_funnel_external_gate"
    value["mechanism"].update(
        {
            "prededup_candidate_preservation_policy": proof.parent_proof.parent_proof.preservation_policy.POLICY_ID,
            "proof_carrying_prededup_preservation_policy": proof.parent_proof.parent_proof.POLICY_ID,
            "total_prededup_preservation_projection_policy": total.parent.parent.POLICY_ID,
            "bounded_prededup_preservation_parent_policy": bounded.frozen.frozen.POLICY_ID,
            "validator_aligned_title_query_policy": query_policy.POLICY_ID,
            "proof_carrying_validator_aligned_title_query_policy": proof.parent_proof.POLICY_ID,
            "total_validator_aligned_title_query_projection_policy": total.parent.POLICY_ID,
            "bounded_validator_aligned_title_query_parent_policy": bounded.frozen.POLICY_ID,
            "content_free_title_funnel_policy": proof.funnel_policy.POLICY_ID,
            "proof_carrying_content_free_title_funnel_policy": proof.POLICY_ID,
            "total_content_free_title_funnel_projection_policy": total.POLICY_ID,
            "bounded_content_free_title_funnel_parent_policy": bounded.POLICY_ID,
            "immutable_title_funnel_collector_policy": collector_repair.POLICY_ID,
            "collector_projector_is_module_load_unbound_v24600_function": True,
            "controller_rebinds_inherited_original_task_projection": False,
            "exact_url_distinct_candidates_preserved_before_registrable_source_selection": True,
            "title_funnel_observation_required": True,
            "title_funnel_claims_retrieval_effect_quality_or_causality": False,
            "raw_title_query_url_or_page_text_emitted": False,
            "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
            "query_ranking_title_validator_or_evidence_projection_changed": False,
            "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
        }
    )
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value)


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.04 protocol root drifted")
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_post_quarantine_serialized_strict_reachability_gate"
    for name in _MECHANISM_FIELDS:
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_previous():
        _PREVIOUS_VALIDATE_PROTOCOL(value=core)
    mechanism = copied.get("mechanism", {})
    budget = copied.get("budget", {})
    provider = copied.get("provider", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope") != "fresh_content_free_title_funnel_external_gate"
        or copied.get("parent") != {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}
        or copied.get("successor_binding") != _successor_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("targeted_proof_policy") != proof.POLICY_ID
        or mechanism.get("targeted_parent_policy") != bounded.POLICY_ID
        or mechanism.get("validator_aligned_title_query_policy") != query_policy.POLICY_ID
        or mechanism.get("proof_carrying_validator_aligned_title_query_policy")
        != proof.parent_proof.POLICY_ID
        or mechanism.get("total_validator_aligned_title_query_projection_policy")
        != total.parent.POLICY_ID
        or mechanism.get("bounded_validator_aligned_title_query_parent_policy")
        != bounded.frozen.POLICY_ID
        or mechanism.get("proof_carrying_content_free_title_funnel_policy")
        != proof.POLICY_ID
        or mechanism.get("total_content_free_title_funnel_projection_policy")
        != total.POLICY_ID
        or mechanism.get("bounded_content_free_title_funnel_parent_policy")
        != bounded.POLICY_ID
        or mechanism.get("content_free_title_funnel_policy")
        != proof.funnel_policy.POLICY_ID
        or mechanism.get("immutable_title_funnel_collector_policy")
        != collector_repair.POLICY_ID
        or mechanism.get("collector_projector_is_module_load_unbound_v24600_function")
        is not True
        or mechanism.get("controller_rebinds_inherited_original_task_projection")
        is not False
        or mechanism.get(
            "exact_url_distinct_candidates_preserved_before_registrable_source_selection"
        )
        is not True
        or mechanism.get("title_funnel_observation_required") is not True
        or mechanism.get(
            "title_funnel_claims_retrieval_effect_quality_or_causality"
        )
        is not False
        or mechanism.get("raw_title_query_url_or_page_text_emitted") is not False
        or mechanism.get(
            "logical_query_search_batch_fetch_page_source_or_model_budget_changed"
        )
        is not False
        or mechanism.get("query_ranking_title_validator_or_evidence_projection_changed")
        is not False
        or mechanism.get(
            "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit"
        )
        is not False
        or provider.get("executor_count") != 8
        or provider.get("model_slot_cap") != 2
        or budget.get("effect_deadline_seconds") != 150.0
        or budget.get("worker_timeout_seconds") != 220.0
        or budget.get("parent_timeout_seconds") != 245.0
        or budget.get("maximum_batch_wall_seconds") != 255.0
        or budget.get("maximum_targeted_search_batches_per_task") != 1
        or budget.get("maximum_targeted_logical_queries_per_task") != 2
        or budget.get("maximum_targeted_fetches_per_task") != 3
        or copied.get("authorization") != _protocol_authorization()
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.46.04 protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_previous(validator_names=("validate_protocol",)):
        value = _PREVIOUS_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_444_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_444_and_3552",
        "v24567_invalid_population_resume_retry_rerun_or_evaluation",
        "v24568_quarantine_validated",
        "v24570_serialized_protocol_validator_build_audit_validated",
    ):
        checks.pop(name, None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_476_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_476_and_3808"] = True
    checks["v24596_population_resume_retry_rerun_or_evaluation"] = False
    checks["v24596_result_decision_and_postaudit_closed"] = True
    checks["v24603_title_funnel_build_audit_validated"] = True
    checks["all_64_full_and_second_query_surfaces_validator_reachable"] = True
    checks["v24602_instance_local_immutable_collector_bound"] = True
    checks["controller_rebinds_inherited_original_task_projection"] = False
    checks["title_funnel_claims_retrieval_effect_quality_or_causality"] = False
    checks["raw_title_query_url_or_page_text_emitted"] = False
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.04 preaudit root drifted")
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.46.04 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_476_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_476_and_3808",
        "v24596_population_resume_retry_rerun_or_evaluation",
        "v24596_result_decision_and_postaudit_closed",
        "v24603_title_funnel_build_audit_validated",
        "all_64_full_and_second_query_surfaces_validator_reachable",
        "v24602_instance_local_immutable_collector_bound",
        "controller_rebinds_inherited_original_task_projection",
        "title_funnel_claims_retrieval_effect_quality_or_causality",
        "raw_title_query_url_or_page_text_emitted",
    ):
        core_checks.pop(name, None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_444_consumed_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_444_and_3552"] = True
    core_checks["v24567_invalid_population_resume_retry_rerun_or_evaluation"] = False
    core_checks["v24568_quarantine_validated"] = True
    core_checks["v24570_serialized_protocol_validator_build_audit_validated"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_previous(validator_names=("validate_protocol",)):
        _PREVIOUS_VALIDATE_PREAUDIT(value=core)
    required_true = (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_476_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_476_and_3808",
        "v24596_result_decision_and_postaudit_closed",
        "v24603_title_funnel_build_audit_validated",
        "all_64_full_and_second_query_surfaces_validator_reachable",
        "v24602_instance_local_immutable_collector_bound",
        "complete_nested_protocol_validation_critical_section_serialized",
        "task_execution_remains_parallel_after_protocol_validation",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("launch_authorized") is not True
        or any(checks.get(name) is not True for name in required_true)
        or checks.get("v24596_population_resume_retry_rerun_or_evaluation")
        is not False
        or checks.get("controller_rebinds_inherited_original_task_projection")
        is not False
        or checks.get("title_funnel_claims_retrieval_effect_quality_or_causality")
        is not False
        or checks.get("raw_title_query_url_or_page_text_emitted") is not False
        or checks.get("focused_tests", {}).get("test_count")
        != EXPECTED_TEST_COUNT
        or checks.get("focused_tests", {}).get("passed") is not True
        or copied.get("authorization") != _activation_authorization()
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.04 preactivation audit drifted")
    return copied


_ALL_VALIDATORS = (
    "validate_protocol",
    "validate_preaudit",
    "validate_activation",
    "validate_execution_start",
    "validate_public_result",
)


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_BUILD_ACTIVATION(now=now)


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.04 activation root drifted")
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_BUILD_EXECUTION_START(now=now)


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.04 execution-start root drifted")
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    mechanism = value.get("mechanism_aggregate")
    required = (
        "content_free_title_funnel_activity_tasks",
        "content_free_title_funnel_nonempty_title_tasks",
        "total_content_free_title_funnel_count_fields",
        "all_content_free_title_funnel_success_rows_consumed_validated_capabilities",
    )
    if not isinstance(mechanism, Mapping) or any(
        name not in mechanism for name in required
    ):
        raise RuntimeError("V2.46.04 title-funnel aggregate schema is absent")
    total.validate_aggregate(mechanism)
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_VALIDATE_PUBLIC_RESULT(value)


def run_probe() -> dict[str, Any]:
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_RUN_PROBE()


def _decision_authorization(passed: bool) -> dict[str, bool]:
    return {
        "title_funnel_diagnostic_successor_design": passed,
        "reliability_successor_design": not passed,
        "fresh_paired_dev64_design": False,
        "fresh_paired_dev64_launch": False,
        "new_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def build_decision(*, now: int | None = None) -> dict[str, Any]:
    result = validate_public_result(_read(RESULT))
    route = diagnostic_route(
        result["mechanism_aggregate"],
        result["supervision_aggregate"],
        diagnostic=result["mechanism_passed"],
        reliability=result["reliability_passed"],
        parent_validation=result["parent_validation_passed"],
        latency=result["latency_passed"],
    )
    passed = result["passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v24604_content_free_title_funnel_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_content_free_title_funnel_observed"
            if passed
            else "fresh_content_free_title_funnel_incomplete"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_title_funnel_measured": True,
            "retrieval_effect_quality_or_causality_claimed": False,
            "benchmark_quality_measured": False,
            "paired_dev64_launch_authorized": False,
            "sota_supported": False,
        },
        "authorization": _decision_authorization(passed),
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return validate_decision(value=value)


def validate_decision(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(DECISION)
    result = validate_public_result(_read(RESULT))
    passed = result["passed"] is True
    route = diagnostic_route(
        result["mechanism_aggregate"],
        result["supervision_aggregate"],
        diagnostic=result["mechanism_passed"],
        reliability=result["reliability_passed"],
        parent_validation=result["parent_validation_passed"],
        latency=result["latency_passed"],
    )
    expected_status = (
        "fresh_content_free_title_funnel_observed"
        if passed
        else "fresh_content_free_title_funnel_incomplete"
    )
    if (
        copied.get("role") != "v24604_content_free_title_funnel_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope", {}).get(
            "retrieval_effect_quality_or_causality_claimed"
        )
        is not False
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.46.04 decision drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    decision = validate_decision()
    lease_active = base.lease_observation(ROOT, Path("/proc")).get("active") is not False
    watchers = base.protected_watcher_snapshot()
    expected = base._read(ROOT, EXECUTION_START)["protected_watchers"]
    findings: list[str] = []
    if lease_active:
        findings.append("shared_api_lease_active")
    if watchers != expected:
        findings.append("protected_watcher_identity_drifted")
    if runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION:
        findings.append("inherited_original_task_projection_rebound")
    value = {
        "artifact_version": 1,
        "role": "v24604_content_free_title_funnel_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "decision_sha256": sha256(ROOT / DECISION),
        "decision_status": decision["status"],
        "diagnostic_route": decision["diagnostic_route"],
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "private_task_or_web_content_persisted": False,
        "opaque_capability_references_destroyed_after_aggregation": True,
        "inherited_original_task_projection_rebound": False,
        "retrieval_effect_quality_or_causality_claimed": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_postaudit(value=value)


def validate_postaudit(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(POSTAUDIT)
    decision = validate_decision()
    if (
        copied.get("role")
        != "v24604_content_free_title_funnel_external_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status") != decision["status"]
        or copied.get("diagnostic_route") != decision["diagnostic_route"]
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != base.protected_watcher_snapshot()
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or copied.get("private_task_or_web_content_persisted") is not False
        or copied.get("opaque_capability_references_destroyed_after_aggregation")
        is not True
        or copied.get("inherited_original_task_projection_rebound") is not False
        or copied.get("retrieval_effect_quality_or_causality_claimed") is not False
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.04 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_previous(validator_names=_ALL_VALIDATORS):
        _PREVIOUS_RUN_PROCESS_SUBCOMMAND(args)


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
            "decision",
            "postaudit",
            "finalize",
            "supervisor",
            "worker",
        ),
    )
    parser.add_argument("--ordinal")
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--checkpoint-directory")
    parser.add_argument("--slots")
    parser.add_argument(base.worker_budget.DEADLINE_ORIGIN_ARGUMENT)
    args = parser.parse_args()
    if args.command == "protocol":
        base.publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        base.publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        base.publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        base.publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe()
    elif args.command == "decision":
        base.publish(ROOT / DECISION, build_decision())
    elif args.command == "postaudit":
        base.publish(ROOT / POSTAUDIT, build_postaudit())
    elif args.command == "finalize":
        base.publish(ROOT / DECISION, build_decision())
        base.publish(ROOT / POSTAUDIT, build_postaudit())
    else:
        run_process_subcommand(args)


if __name__ == "__main__":
    main()
