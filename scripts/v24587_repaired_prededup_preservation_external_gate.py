#!/usr/bin/env python3
"""Fresh pre-dedup preservation gate with an immutable collector.

V2.45.83 is permanently quarantined and its 8-task/64-entity population is
counted as consumed.  This successor starts after 460 external questions and
3,680 entities, uses a literal/canonical-disjoint population, and retains the
same model, query, search, fetch, page, source, and decision budgets.

The only execution repair is V2.45.85: the parent uses its instance-local
collector and aggregate entrypoint.  The inherited V2.45.67 shared
``_ORIGINAL_TASK_PROJECTION`` global is never rebound by this controller.
Runtime input remains exactly ``opaque_id`` and ``question``.
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
from scripts import audit_v24584_invalid_recursive_collector_run as quarantine  # noqa: E402
from scripts import audit_v24586_nested_collector_repair_build as build_gate  # noqa: E402
from scripts import v24583_prededup_preservation_external_gate as invalid  # noqa: E402
from scripts import v24585_nested_collector_projection_repair as collector_repair  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24587_fresh_repaired_prededup_preservation_external_gate_v1"
PROTOCOL = Path(
    f"results/v24587_repaired_prededup_preservation_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24587_repaired_prededup_preservation_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24587_repaired_prededup_preservation_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24587_repaired_prededup_preservation_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24587_repaired_prededup_preservation_external_result_v1_{DATE}.json"
)
DECISION = Path(
    f"results/v24587_repaired_prededup_preservation_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24587_repaired_prededup_preservation_external_postresult_audit_v1_{DATE}.json"
)
PARENT = build_gate.AUDIT
QUARANTINE = quarantine.AUDIT
INVALID_PROTOCOL = invalid.PROTOCOL
INVALID_PREAUDIT = invalid.PREAUDIT
INVALID_ACTIVATION = invalid.ACTIVATION
INVALID_EXECUTION_START = invalid.EXECUTION_START
RUNNER_MARKER = "scripts/v24587_repaired_prededup_preservation_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_repaired_prededup_preservation_external_gate"
PRIOR_QUESTION_COUNT = 460
PRIOR_ENTITY_COUNT = 3680
PRIOR_QUESTIONS = invalid._prior_questions() + invalid.QUESTIONS

previous = invalid.previous
runtime = invalid.runtime
base = invalid.base
population = invalid.population
repair = invalid.repair
alias_projection = invalid.alias_projection
acquisition = invalid.acquisition
surface = invalid.surface
planner = invalid.planner
proof = invalid.proof
total = invalid.total
bounded = invalid.bounded
STRICT_TASK_FIELD = invalid.STRICT_TASK_FIELD


ENTITY_GROUPS = (
    (
        "University of Hertfordshire",
        "University of Italian Switzerland",
        "University of Roehampton",
        "University of Sunderland",
        "University of Winchester",
        "Oxford Brookes University",
        "Queen Margaret University Edinburgh",
        "Robert Gordon University Aberdeen",
    ),
    (
        "Solent University Southampton",
        "Staffordshire University",
        "Teesside University Middlesbrough",
        "Ulster University Northern Ireland",
        "University of Abertay Dundee",
        "University of Bedfordshire",
        "University of Chichester",
        "University of Lincoln England",
    ),
    (
        "Atlantic Technological University Ireland",
        "Dublin City University Ireland",
        "South East Technological University Ireland",
        "University of Limerick Ireland",
        "Maynooth University Ireland",
        "Dublin Business School",
        "University College Cork Ireland",
        "Mary Immaculate College Limerick",
    ),
    (
        "University of Applied Sciences Utrecht",
        "Hanze University of Applied Sciences",
        "Fontys University of Applied Sciences",
        "Saxion University of Applied Sciences",
        "Avans University of Applied Sciences",
        "NHL Stenden University of Applied Sciences",
        "Rotterdam University of Applied Sciences",
        "Windesheim University of Applied Sciences",
    ),
    (
        "Zuyd University of Applied Sciences",
        "Thomas More University of Applied Sciences Belgium",
        "Odisee University of Applied Sciences",
        "University Colleges Leuven Limburg",
        "KdG University of Applied Sciences and Arts",
        "EPHEC University College",
        "VIVES University of Applied Sciences",
        "Haute Ecole Leonard de Vinci",
    ),
    (
        "University of Klagenfurt Austria",
        "University of Graz Austria",
        "University of Innsbruck Austria",
        "Vienna University of Economics and Business",
        "University of Salzburg Austria",
        "St Polten University of Applied Sciences",
        "Kufstein University of Applied Sciences",
        "IMC Krems University of Applied Sciences",
    ),
    (
        "MCI Management Center Innsbruck",
        "University of Lucerne Switzerland",
        "University of Fribourg Switzerland",
        "University of Neuchatel Switzerland",
        "University of St Gallen Switzerland",
        "Bern University of Applied Sciences",
        "University of Applied Sciences and Arts Northwestern Switzerland",
        "University of Teacher Education Zurich",
    ),
    (
        "University of Vaasa Finland",
        "University of Lapland Finland",
        "Tampere University Finland",
        "Abo Akademi University Finland",
        "Jyvaskyla University of Applied Sciences",
        "LAB University of Applied Sciences",
        "University West Sweden",
        "Malmo University Sweden",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.87 entity group drifted")
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
GATES = copy.deepcopy(invalid.GATES)
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *invalid.SOURCE_FILES,
            str(INVALID_PROTOCOL),
            str(INVALID_PREAUDIT),
            str(INVALID_ACTIVATION),
            str(INVALID_EXECUTION_START),
            "scripts/audit_v24584_invalid_recursive_collector_run.py",
            "tests/test_audit_v24584_invalid_recursive_collector_run.py",
            str(QUARANTINE),
            "scripts/v24585_nested_collector_projection_repair.py",
            "tests/test_v24585_nested_collector_projection_repair.py",
            "scripts/audit_v24586_nested_collector_repair_build.py",
            "tests/test_audit_v24586_nested_collector_repair_build.py",
            str(PARENT),
            RUNNER_MARKER,
            "tests/test_v24587_repaired_prededup_preservation_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *invalid.TEST_SUITES,
    ("tests/test_v24585_nested_collector_projection_repair.py", 7, 360),
    ("tests/test_audit_v24586_nested_collector_repair_build.py", 8, 180),
    ("tests/test_v24587_repaired_prededup_preservation_external_gate.py", 16, 600),
)
EXPECTED_TEST_COUNT = invalid.EXPECTED_TEST_COUNT + 31


_PREVIOUS_BUILD_PROTOCOL = invalid._PREVIOUS_BUILD_PROTOCOL
_PREVIOUS_VALIDATE_PROTOCOL = invalid._PREVIOUS_VALIDATE_PROTOCOL
_PREVIOUS_BUILD_PREAUDIT = invalid._PREVIOUS_BUILD_PREAUDIT
_PREVIOUS_VALIDATE_PREAUDIT = invalid._PREVIOUS_VALIDATE_PREAUDIT
_PREVIOUS_BUILD_ACTIVATION = invalid._PREVIOUS_BUILD_ACTIVATION
_PREVIOUS_VALIDATE_ACTIVATION = invalid._PREVIOUS_VALIDATE_ACTIVATION
_PREVIOUS_BUILD_EXECUTION_START = invalid._PREVIOUS_BUILD_EXECUTION_START
_PREVIOUS_VALIDATE_EXECUTION_START = invalid._PREVIOUS_VALIDATE_EXECUTION_START
_PREVIOUS_VALIDATE_PUBLIC_RESULT = invalid._PREVIOUS_VALIDATE_PUBLIC_RESULT
_PREVIOUS_RUN_PROBE = invalid._PREVIOUS_RUN_PROBE
_PREVIOUS_RUN_PROCESS_SUBCOMMAND = invalid._PREVIOUS_RUN_PROCESS_SUBCOMMAND
_FROZEN_PREVIOUS_PROTOCOL_ID = previous.PROTOCOL_ID
_INHERITED_MECHANISM_PASSED = invalid._INHERITED_MECHANISM_PASSED
_INHERITED_DIAGNOSTIC_ROUTE = invalid._INHERITED_DIAGNOSTIC_ROUTE
_INHERITED_ORIGINAL_TASK_PROJECTION = runtime._ORIGINAL_TASK_PROJECTION
_MISSING = object()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.87 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    baseline = value.get("freshness_baseline", {})
    stress = value.get("repair", {}).get("stress", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24586_nested_collector_repair_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 27
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or stress.get("workers") != 8
        or stress.get("validations") != 8
        or stress.get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or baseline.get("prior_external_question_count") != PRIOR_QUESTION_COUNT
        or baseline.get("prior_external_entity_count") != PRIOR_ENTITY_COUNT
        or baseline.get("v24583_population_resume_retry_rerun_or_evaluation_authorized")
        is not False
        or authorization.get(
            "fresh_disjoint_prededup_preservation_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.87 build parent drifted")
    return value


def _quarantine_valid() -> bool:
    return build_gate._quarantine_valid() and _parent(ROOT).get("audit_valid") is True


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


def _alias_surface_vector_valid() -> bool:
    if len(ALIAS_TITLE_GROUPS) != len(ENTITY_GROUPS):
        return False
    all_surfaces: list[str] = []
    matched = 0
    for entities, titles in zip(ENTITY_GROUPS, ALIAS_TITLE_GROUPS, strict=True):
        if len(entities) != 8 or len(titles) != 8:
            return False
        baseline = (
            "```markdown\n| University | Founding year |\n| --- | --- |\n"
            + "\n".join(f"| {entity} | Unknown |" for entity in entities)
            + "\n```"
        )
        cells = _baseline_cells(baseline)
        for entity, raw_title in zip(entities, titles, strict=True):
            primary = acquisition.primary_alias_surface(entity)
            anchor = alias_projection.unique_alias_title_row(raw_title, cells)
            classified = surface.classify_alias_surface(
                {
                    "title": raw_title,
                    "url": "https://generic.example/history",
                    "query": "generic history",
                },
                entity,
            )
            if (
                primary is None
                or anchor is None
                or anchor.row_key != entity
                or classified["surface_hit"] is not True
                or classified["query_only"] is not False
            ):
                return False
            all_surfaces.append(primary.casefold())
            matched += 1
    return matched == 64 and len(set(all_surfaces)) == 64


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_460_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_surfaces_globally_unique_and_query_blind": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_populations_through_invalid_v24583_counted_as_consumed": True,
        "prior_population_resume_retry_rerun_or_evaluation": False,
        "population_selection_uses_visible_names_and_frozen_alias_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_repaired_prededup_preservation_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_repaired_prededup_preservation_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def _successor_binding() -> dict[str, Any]:
    if not _quarantine_valid():
        raise RuntimeError("V2.45.87 V2.45.83 quarantine drifted")
    return {
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "v24583_quarantine_path": str(QUARANTINE),
        "v24583_quarantine_sha256": sha256(ROOT / QUARANTINE),
        "v24583_protocol_sha256": sha256(ROOT / INVALID_PROTOCOL),
        "v24583_preaudit_sha256": sha256(ROOT / INVALID_PREAUDIT),
        "v24583_activation_sha256": sha256(ROOT / INVALID_ACTIVATION),
        "v24583_execution_start_sha256": sha256(ROOT / INVALID_EXECUTION_START),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "same_or_prior_population_resume_retry_rerun_or_evaluation": False,
        "new_population_reuses_prior_question_or_entity": False,
        "decision_reachability_planner_policy": planner.POLICY_ID,
        "proof_carrying_prededup_preservation_policy": proof.POLICY_ID,
        "total_prededup_preservation_projection_policy": total.POLICY_ID,
        "bounded_prededup_preservation_parent_policy": bounded.POLICY_ID,
        "serialized_protocol_validator_repair_policy": repair.POLICY_ID,
        "immutable_collector_repair_policy": collector_repair.POLICY_ID,
        "collector_projector_is_module_load_unbound_v24580_function": True,
        "controller_rebinds_inherited_original_task_projection": False,
        "complete_nested_protocol_validation_critical_section_serialized": True,
        "task_execution_remains_parallel_after_protocol_validation": True,
        "logical_query_search_batch_fetch_source_or_page_cap_changed": False,
        "source_posterior_margin_leave_one_out_safe_change_or_decision_credit_rules_relaxed": False,
        "same_task_preservation_and_replacement_claim_lead_level_causality": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        _INHERITED_MECHANISM_PASSED(value)
        and value.get("prededup_preservation_activity_tasks", 0)
        >= GATES["minimum_prededup_preservation_activity_tasks"]
        and value.get("prededup_preserved_candidate_tasks", 0)
        >= GATES["minimum_prededup_preserved_candidate_tasks"]
        and value.get("prededup_and_title_replacement_cooccurrence_tasks", 0)
        >= GATES["minimum_prededup_title_replacement_cooccurrence_tasks"]
        and value.get(
            "all_prededup_preservation_success_rows_consumed_validated_capabilities"
        )
        is True
        and value.get(
            "all_prededup_preservation_failure_rows_are_content_free_zero_projections"
        )
        is True
        and value.get("prededup_preservation_failure_rows_claim_zero_private_effects")
        is False
        and value.get("prededup_preservation_private_task_content_emitted") is False
        and value.get("prededup_preservation_privileged_evaluator_content_read")
        is False
        and value.get(
            "prededup_preservation_projection_claims_candidate_or_effect_causality"
        )
        is False
        and value.get(
            "prededup_preservation_same_task_cooccurrence_claims_lead_level_causality"
        )
        is False
        and value.get("prededup_preservation_preserved_url_received_credit") is False
        and value.get("prededup_preservation_query_search_fetch_or_page_budget_changed")
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
    if int(mechanism.get("prededup_preservation_activity_tasks", 0)) == 0:
        return "prededup_projection_reachability_successor"
    if int(mechanism.get("prededup_preserved_candidate_tasks", 0)) == 0:
        return "same_source_candidate_coverage_successor"
    if int(mechanism.get("prededup_and_title_replacement_cooccurrence_tasks", 0)) == 0:
        return "validator_aligned_title_replacement_successor"
    inherited = _INHERITED_DIAGNOSTIC_ROUTE(
        mechanism,
        supervision,
        diagnostic=True,
        reliability=reliability,
        parent_validation=parent_validation,
        latency=latency,
    )
    if inherited != "fresh_paired_dev64_design":
        return inherited
    return "fresh_paired_dev64_design" if diagnostic else "prededup_effect_successor"


@contextmanager
def configured_previous(*, validator_names: Sequence[str] = ()) -> Iterator[None]:
    """Bind the V2.45.79--85 chain without touching the inherited projector."""

    if runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION:
        raise RuntimeError("V2.45.87 inherited original projector drifted")
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
        "_quarantine_valid": _quarantine_valid,
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
            raise RuntimeError("V2.45.87 inherited original projector was rebound")


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    if not _quarantine_valid():
        raise RuntimeError("V2.45.87 predecessor quarantine is not closed")
    _parent(ROOT)
    with configured_previous():
        value = _PREVIOUS_BUILD_PROTOCOL(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["scope"] = "fresh_repaired_prededup_preservation_external_gate"
    value["mechanism"].update(
        {
            "prededup_candidate_preservation_policy": proof.preservation_policy.POLICY_ID,
            "proof_carrying_prededup_preservation_policy": proof.POLICY_ID,
            "total_prededup_preservation_projection_policy": total.POLICY_ID,
            "bounded_prededup_preservation_parent_policy": bounded.POLICY_ID,
            "immutable_collector_repair_policy": collector_repair.POLICY_ID,
            "collector_projector_is_module_load_unbound_v24580_function": True,
            "controller_rebinds_inherited_original_task_projection": False,
            "exact_url_distinct_candidates_preserved_before_registrable_source_selection": True,
            "same_task_preservation_and_title_replacement_required": True,
            "same_task_preservation_and_replacement_claim_lead_level_causality": False,
            "logical_query_search_batch_fetch_source_or_page_cap_changed": False,
            "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
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
        raise RuntimeError("V2.45.87 protocol root drifted")
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_post_quarantine_serialized_strict_reachability_gate"
    for name in (
        "prededup_candidate_preservation_policy",
        "proof_carrying_prededup_preservation_policy",
        "total_prededup_preservation_projection_policy",
        "bounded_prededup_preservation_parent_policy",
        "immutable_collector_repair_policy",
        "collector_projector_is_module_load_unbound_v24580_function",
        "controller_rebinds_inherited_original_task_projection",
        "exact_url_distinct_candidates_preserved_before_registrable_source_selection",
        "same_task_preservation_and_title_replacement_required",
        "same_task_preservation_and_replacement_claim_lead_level_causality",
        "logical_query_search_batch_fetch_source_or_page_cap_changed",
        "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit",
    ):
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
        or copied.get("scope") != "fresh_repaired_prededup_preservation_external_gate"
        or copied.get("parent") != {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}
        or copied.get("successor_binding") != _successor_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("targeted_proof_policy") != proof.POLICY_ID
        or mechanism.get("targeted_parent_policy") != bounded.POLICY_ID
        or mechanism.get("prededup_candidate_preservation_policy")
        != proof.preservation_policy.POLICY_ID
        or mechanism.get("proof_carrying_prededup_preservation_policy")
        != proof.POLICY_ID
        or mechanism.get("total_prededup_preservation_projection_policy")
        != total.POLICY_ID
        or mechanism.get("bounded_prededup_preservation_parent_policy")
        != bounded.POLICY_ID
        or mechanism.get("immutable_collector_repair_policy")
        != collector_repair.POLICY_ID
        or mechanism.get("collector_projector_is_module_load_unbound_v24580_function")
        is not True
        or mechanism.get("controller_rebinds_inherited_original_task_projection")
        is not False
        or mechanism.get(
            "exact_url_distinct_candidates_preserved_before_registrable_source_selection"
        )
        is not True
        or mechanism.get("same_task_preservation_and_title_replacement_required")
        is not True
        or mechanism.get(
            "same_task_preservation_and_replacement_claim_lead_level_causality"
        )
        is not False
        or mechanism.get("logical_query_search_batch_fetch_source_or_page_cap_changed")
        is not False
        or mechanism.get(
            "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit"
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
        raise RuntimeError("V2.45.87 protocol drifted")
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
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_460_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_460_and_3680"] = True
    checks["v24583_invalid_population_resume_retry_rerun_or_evaluation"] = False
    checks["v24584_quarantine_validated"] = True
    checks["v24586_nested_collector_repair_build_audit_validated"] = True
    checks["v24585_instance_local_immutable_collector_bound"] = True
    checks["controller_rebinds_inherited_original_task_projection"] = False
    checks["prededup_preservation_and_title_replacement_are_runtime_reachable"] = True
    checks["same_task_preservation_and_replacement_claim_lead_level_causality"] = False
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.45.87 preaudit root drifted")
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.45.87 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_460_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_460_and_3680",
        "v24583_invalid_population_resume_retry_rerun_or_evaluation",
        "v24584_quarantine_validated",
        "v24586_nested_collector_repair_build_audit_validated",
        "v24585_instance_local_immutable_collector_bound",
        "controller_rebinds_inherited_original_task_projection",
        "prededup_preservation_and_title_replacement_are_runtime_reachable",
        "same_task_preservation_and_replacement_claim_lead_level_causality",
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
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_460_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_460_and_3680",
        "v24584_quarantine_validated",
        "v24586_nested_collector_repair_build_audit_validated",
        "v24585_instance_local_immutable_collector_bound",
        "prededup_preservation_and_title_replacement_are_runtime_reachable",
        "complete_nested_protocol_validation_critical_section_serialized",
        "task_execution_remains_parallel_after_protocol_validation",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("launch_authorized") is not True
        or any(checks.get(name) is not True for name in required_true)
        or checks.get("v24583_invalid_population_resume_retry_rerun_or_evaluation")
        is not False
        or checks.get("controller_rebinds_inherited_original_task_projection")
        is not False
        or checks.get(
            "same_task_preservation_and_replacement_claim_lead_level_causality"
        )
        is not False
        or checks.get("focused_tests", {}).get("test_count")
        != EXPECTED_TEST_COUNT
        or checks.get("focused_tests", {}).get("passed") is not True
        or copied.get("authorization") != _activation_authorization()
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.87 preactivation audit drifted")
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
        raise RuntimeError("V2.45.87 activation root drifted")
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_BUILD_EXECUTION_START(now=now)


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.45.87 execution-start root drifted")
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    mechanism = value.get("mechanism_aggregate")
    required = (
        "prededup_preservation_activity_tasks",
        "prededup_preserved_candidate_tasks",
        "prededup_and_title_replacement_cooccurrence_tasks",
        "total_prededup_preservation_count_fields",
        "all_prededup_preservation_success_rows_consumed_validated_capabilities",
    )
    if not isinstance(mechanism, Mapping) or any(
        name not in mechanism for name in required
    ):
        raise RuntimeError("V2.45.87 pre-dedup aggregate schema is absent")
    total.validate_aggregate(mechanism)
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_VALIDATE_PUBLIC_RESULT(value)


def run_probe() -> dict[str, Any]:
    with configured_previous(validator_names=_ALL_VALIDATORS):
        return _PREVIOUS_RUN_PROBE()


def _decision_authorization(passed: bool) -> dict[str, bool]:
    return {
        "diagnostic_successor_design": not passed,
        "fresh_paired_dev64_design": passed,
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
        "role": "v24587_repaired_prededup_preservation_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_repaired_prededup_preservation_go"
            if passed
            else "fresh_repaired_prededup_preservation_no_go"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_prededup_preservation_measured": True,
            "preservation_or_replacement_lead_level_causality_claimed": False,
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
        "fresh_repaired_prededup_preservation_go"
        if passed
        else "fresh_repaired_prededup_preservation_no_go"
    )
    if (
        copied.get("role")
        != "v24587_repaired_prededup_preservation_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope", {}).get(
            "preservation_or_replacement_lead_level_causality_claimed"
        )
        is not False
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.87 decision drifted")
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
        "role": "v24587_repaired_prededup_preservation_external_postresult_audit",
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
        "preservation_or_replacement_lead_level_causality_claimed": False,
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
        != "v24587_repaired_prededup_preservation_external_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status") != decision["status"]
        or copied.get("diagnostic_route") != decision["diagnostic_route"]
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != base.protected_watcher_snapshot()
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or copied.get("private_task_or_web_content_persisted") is not False
        or copied.get("opaque_capability_references_destroyed_after_aggregation")
        is not True
        or copied.get("inherited_original_task_projection_rebound") is not False
        or copied.get("preservation_or_replacement_lead_level_causality_claimed")
        is not False
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.87 postresult audit drifted")
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
