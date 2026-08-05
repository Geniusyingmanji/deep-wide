#!/usr/bin/env python3
"""Fresh one-wave external gate for page-to-observation diagnostics.

V2.45.17 established that the neutral discovery worker can fetch usable pages
without producing a safe observation.  V2.45.18--21 add a fixed-vocabulary
reason partition and a proof-carrying bounded parent.  This gate runs that
pipeline once on eight new public-document questions whose 64 entities are
literal/canonical disjoint from all 356 prior external questions and 2,848
entities.

Successful task rows are aggregated only from the opaque V2.45.19 capability.
The public success dictionary is never accepted back as proof.  A short-lived
in-process collector holds capabilities between parent validation and batch
aggregation, then destroys its references before the temporary execution
directory is removed.  Only content-free fixed-vocabulary counts persist.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent import v24518_conversion_observability as observability  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v24519_proof_carrying_conversion_observability as conversion_proof,
)
from deepwide_agent import v24520_total_conversion_projection as total  # noqa: E402
from deepwide_agent import v24521_bounded_conversion_parent as conversion_parent  # noqa: E402
from scripts import v24445_serialized_narrative_external_gate as population  # noqa: E402
from scripts import v24517_neutral_discovery_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24522_fresh_conversion_diagnostic_external_gate_v1"
PROTOCOL = Path(f"results/v24522_conversion_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24522_conversion_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24522_conversion_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24522_conversion_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24522_conversion_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24522_conversion_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24522_conversion_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(f"results/v24521_bounded_conversion_parent_build_audit_v1_{DATE}.json")
RUNNER_MARKER = "scripts/v24522_conversion_diagnostic_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_page_observation_conversion_diagnostic_external_gate"
PRIOR_QUESTION_COUNT = 356
PRIOR_ENTITY_COUNT = 2848
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS
PREVIOUS_RESULT = predecessor.RESULT
PREVIOUS_DECISION = predecessor.DECISION
PREVIOUS_POSTAUDIT = predecessor.POSTAUDIT
PREVIOUS_PROTOCOL_ID = predecessor.PROTOCOL_ID

ENTITY_GROUPS = (
    (
        "Haverford College",
        "Bryn Mawr College",
        "Saint Joseph's University",
        "La Salle University",
        "Arcadia University",
        "Widener University",
        "Immaculata University",
        "Cabrini University",
    ),
    (
        "SUNY Geneseo",
        "SUNY New Paltz",
        "SUNY Oneonta",
        "SUNY Oswego",
        "SUNY Plattsburgh",
        "SUNY Potsdam",
        "SUNY Fredonia",
        "SUNY Cortland",
    ),
    (
        "Trent University",
        "Brock University",
        "Laurentian University",
        "Lakehead University",
        "Acadia University",
        "St. Francis Xavier University",
        "University of Prince Edward Island",
        "University of New Brunswick",
    ),
    (
        "University of Chester",
        "University of Derby",
        "University of Gloucestershire",
        "University of Huddersfield",
        "University of Northampton",
        "University of Worcester",
        "York St John University",
        "University of Suffolk",
    ),
    (
        "University of Hildesheim",
        "University of Paderborn",
        "University of Vechta",
        "Chemnitz University of Technology",
        "Brandenburg University of Technology",
        "University of Erfurt",
        "University of Flensburg",
        "University of Trier",
    ),
    (
        "University of Girona",
        "University of Lleida",
        "University of Jaén",
        "University of Huelva",
        "University of Burgos",
        "University of La Rioja",
        "Pablo de Olavide University",
        "Miguel Hernández University of Elche",
    ),
    (
        "University of Toyama",
        "University of Fukui",
        "University of Yamanashi",
        "University of Shizuoka",
        "Shimane University",
        "Tottori University",
        "Saga University",
        "Oita University",
    ),
    (
        "University of Canberra",
        "Edith Cowan University",
        "University of Southern Queensland",
        "University of New England",
        "Victoria University",
        "University of Tasmania",
        "CQUniversity",
        "Murdoch University",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.22 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
GATES = {
    "minimum_worker_success_tasks": 8,
    "maximum_worker_hard_timeout_tasks": 0,
    "maximum_worker_nonzero_tasks": 0,
    "minimum_complete_validation_returned_tasks": 8,
    "minimum_conversion_capability_success_tasks": 8,
    "maximum_conversion_failure_as_zero_tasks": 0,
    "minimum_conversion_any_usable_page_tasks": 1,
    "minimum_total_conversion_page_target_pair_count": 1,
    "maximum_additional_external_effects": 0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 3,
    "maximum_fetch_helper_failures": 3,
    "maximum_parent_validation_p95_seconds": 1.0,
}
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *predecessor.SOURCE_FILES,
            "src/deepwide_agent/v24518_conversion_observability.py",
            "tests/test_v24518_conversion_observability.py",
            "src/deepwide_agent/v24519_proof_carrying_conversion_observability.py",
            "tests/test_v24519_proof_carrying_conversion_observability.py",
            "scripts/audit_v24519_conversion_observability_build.py",
            "tests/test_audit_v24519_conversion_observability_build.py",
            "results/v24519_conversion_observability_build_audit_v1_20260805.json",
            "src/deepwide_agent/v24520_total_conversion_projection.py",
            "tests/test_v24520_total_conversion_projection.py",
            "src/deepwide_agent/v24521_bounded_conversion_parent.py",
            "tests/test_v24521_bounded_conversion_parent.py",
            "scripts/audit_v24521_bounded_conversion_parent_build.py",
            "tests/test_audit_v24521_bounded_conversion_parent_build.py",
            str(PARENT),
            str(PREVIOUS_RESULT),
            str(PREVIOUS_DECISION),
            str(PREVIOUS_POSTAUDIT),
            RUNNER_MARKER,
            "tests/test_v24522_conversion_diagnostic_external_gate.py",
        )
    )
)
TEST_SUITES = (
    ("tests/test_v24480_separated_effect_validation_budget.py", 6, 120),
    ("tests/test_v24482_separated_budget_worker_integration.py", 7, 180),
    ("tests/test_v24513_terminal_record_bound_projection.py", 7, 180),
    ("tests/test_v24515_neutral_cell_discovery_planner.py", 7, 120),
    ("tests/test_v24518_conversion_observability.py", 6, 120),
    ("tests/test_v24519_proof_carrying_conversion_observability.py", 8, 240),
    ("tests/test_v24520_total_conversion_projection.py", 6, 120),
    ("tests/test_v24521_bounded_conversion_parent.py", 5, 180),
    ("tests/test_audit_v24521_bounded_conversion_parent_build.py", 5, 60),
    ("tests/test_v24522_conversion_diagnostic_external_gate.py", 12, 300),
)
EXPECTED_TEST_COUNT = 69


_ORIGINAL_PATCHED_CORE = predecessor._patched_core
_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start
_ORIGINAL_TASK_PROJECTION = total.task_projection
_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING = copy.deepcopy(
    predecessor._record_bound_binding()
)
_COLLECTOR_GUARD = threading.Lock()
_ACTIVE_COLLECTOR: _CapabilityCollector | None = None


def _base() -> Any:
    return predecessor.predecessor.predecessor.predecessor.base


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.22 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


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


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24521_bounded_conversion_parent_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or authorization.get(
            "fresh_disjoint_conversion_diagnostic_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.22 build parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_356_prior_external_questions": _fresh_entity_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_prior_external_populations_rerun": False,
        "v24517_population_rerun": False,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _previous_closed() -> bool:
    result = _read(PREVIOUS_RESULT)
    decision = _read(PREVIOUS_DECISION)
    postaudit = _read(PREVIOUS_POSTAUDIT)
    return (
        result.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and decision.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and postaudit.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and result.get("passed") is False
        and decision.get("status") == "fresh_targeted_external_no_go"
        and postaudit.get("audit_valid") is True
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("findings") == []
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
    )


def _record_bound_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.22 V2.45.17 closure drifted")
    return {
        **copy.deepcopy(_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING),
        "conversion_observability_policy": observability.POLICY_ID,
        "proof_carrying_conversion_observability_policy": conversion_proof.POLICY_ID,
        "total_conversion_projection_policy": total.POLICY_ID,
        "bounded_conversion_parent_policy": conversion_parent.POLICY_ID,
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "new_population_reuses_prior_question_or_entity": False,
        "v24517_population_rerun": False,
        "v24517_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24517_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24517_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "conversion_diagnostic_complete_not_quality_threshold": True,
        "opaque_capability_aggregated_before_destruction": True,
        "expanded_public_success_row_reingestion_allowed": False,
        "reason_partition_route_and_signal_conservation_required": True,
        "historical_private_page_opened": False,
        "source_count_posterior_margin_leave_one_out_and_credit_rules_relaxed": False,
        "additional_query_search_batch_model_request_or_fetch": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


class _CapabilityCollector:
    """One-shot bridge from parent validation to opaque batch aggregation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._capabilities: dict[
            int, conversion_proof.ValidatedProofCarryingConversionObservability
        ] = {}
        self._rows: dict[int, dict[str, Any]] = {}
        self._consumed = False

    def project(
        self,
        ordinal: int,
        capability: conversion_proof.ValidatedProofCarryingConversionObservability,
    ) -> dict[str, Any]:
        row = _ORIGINAL_TASK_PROJECTION(ordinal, capability)
        with self._lock:
            if self._consumed or ordinal in self._capabilities:
                raise RuntimeError("V2.45.22 duplicate or late capability")
            self._capabilities[ordinal] = capability
            self._rows[ordinal] = copy.deepcopy(row)
        return row

    def aggregate(
        self, values: Sequence[Mapping[str, Any]], *, selected: int
    ) -> dict[str, Any]:
        if len(values) != selected:
            raise ValueError("V2.45.22 aggregate selection drifted")
        with self._lock:
            if self._consumed:
                raise RuntimeError("V2.45.22 capabilities already consumed")
            capabilities = dict(self._capabilities)
            rows = copy.deepcopy(self._rows)
            self._consumed = True
            self._capabilities.clear()
            self._rows.clear()
        proof_inputs: list[Any] = []
        for ordinal, raw in enumerate(values, start=1):
            row = total.validate_total_row(raw)
            capability = capabilities.pop(ordinal, None)
            captured = rows.pop(ordinal, None)
            if row["status"] == "validated_capability":
                if capability is None or captured != row:
                    raise RuntimeError("V2.45.22 success lacks captured capability")
                if _ORIGINAL_TASK_PROJECTION(ordinal, capability) != row:
                    raise RuntimeError("V2.45.22 capability/public row mismatch")
                proof_inputs.append(capability)
            else:
                if capability is not None or captured is not None:
                    raise RuntimeError("V2.45.22 failure unexpectedly has capability")
                proof_inputs.append(row)
        if capabilities or rows:
            raise RuntimeError("V2.45.22 unconsumed capability vector")
        return total.aggregate_projections(proof_inputs, selected=selected)

    def destroy(self) -> None:
        with self._lock:
            self._capabilities.clear()
            self._rows.clear()
            self._consumed = True


@contextmanager
def capability_collection() -> Iterator[_CapabilityCollector]:
    global _ACTIVE_COLLECTOR
    if not _COLLECTOR_GUARD.acquire(blocking=False):
        raise RuntimeError("V2.45.22 capability collector is already active")
    collector = _CapabilityCollector()
    original = conversion_parent.task_projection
    if _ACTIVE_COLLECTOR is not None:
        _COLLECTOR_GUARD.release()
        raise RuntimeError("V2.45.22 active collector drifted")
    _ACTIVE_COLLECTOR = collector
    conversion_parent.task_projection = collector.project
    try:
        yield collector
    finally:
        conversion_parent.task_projection = original
        collector.destroy()
        _ACTIVE_COLLECTOR = None
        _COLLECTOR_GUARD.release()


def aggregate_conversion_projections(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    collector = _ACTIVE_COLLECTOR
    if collector is None:
        raise RuntimeError("V2.45.22 opaque capability collector is absent")
    return collector.aggregate(values, selected=selected)


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        value.get("success_tasks")
        == GATES["minimum_conversion_capability_success_tasks"]
        and value.get("failure_as_zero_tasks")
        == GATES["maximum_conversion_failure_as_zero_tasks"]
        and value.get("passed_success_tasks") == 8
        and value.get("conversion_any_usable_page_tasks", 0)
        >= GATES["minimum_conversion_any_usable_page_tasks"]
        and value.get("total_conversion_page_target_pair_count", 0)
        >= GATES["minimum_total_conversion_page_target_pair_count"]
        and sum(value.get("conversion_reason_pair_counts", {}).values())
        == value.get("total_conversion_page_target_pair_count")
        and value.get("total_conversion_signal_counts", {}).get(
            "grammar_projection_pair_count"
        )
        + value.get("total_conversion_signal_counts", {}).get(
            "zero_projection_pair_count"
        )
        == value.get("total_conversion_page_target_pair_count")
        and value.get("all_success_rows_consumed_conversion_capabilities") is True
        and value.get(
            "all_failure_rows_are_content_free_conversion_zero_projections"
        )
        is True
        and value.get("conversion_failure_rows_claim_zero_private_effects") is False
        and value.get("all_terminal_states_consumed_validated_capabilities") is True
        and value.get("total_additional_external_effects_success_rows")
        == GATES["maximum_additional_external_effects"]
        and value.get("total_validation_memo_mismatches") == 0
        and value.get("conversion_private_task_content_emitted") is False
        and value.get("conversion_privileged_evaluator_content_read") is False
    )


REASON_FAMILIES = {
    "anchor_absence_or_misbinding": (
        "no_projection_unique_title_anchor_bound_to_other_visible_row",
        "no_projection_exact_entity_and_unique_title_anchor_absent_or_ambiguous",
    ),
    "relation_or_year_absence": (
        "no_projection_explicit_relation_absent",
        "no_projection_relation_present_but_candidate_year_absent",
    ),
    "conservative_safety_rejection": (
        "projection_rejected_post_projection_safety",
        "no_projection_unsupported_column_kind",
        "no_projection_multiple_distinct_candidate_years",
        "no_projection_candidate_year_present_but_safety_rejected",
    ),
    "source_ambiguity": ("projection_rejected_source_ambiguity",),
    "observation_or_parent_duplicate": (
        "new_observation_emitted",
        "projection_duplicate_parent_observation",
    ),
}
FAMILY_ROUTES = {
    "anchor_absence_or_misbinding": "conservative_alias_title_anchoring_successor",
    "relation_or_year_absence": "source_ranking_fetch_selection_successor",
    "conservative_safety_rejection": "conservative_parser_grammar_successor",
    "source_ambiguity": "dedup_source_selection_successor",
    "observation_or_parent_duplicate": "observation_support_credit_successor",
}


def reason_family_counts(value: Mapping[str, Any]) -> dict[str, int]:
    reasons = value.get("conversion_reason_pair_counts", {})
    return {
        family: sum(int(reasons.get(name, 0)) for name in names)
        for family, names in REASON_FAMILIES.items()
    }


def diagnostic_route(
    mechanism: Mapping[str, Any],
    supervision: Mapping[str, Any],
    *,
    diagnostic: bool,
    reliability: bool,
    parent_validation: bool,
    latency: bool,
) -> str:
    if int(supervision.get("worker_hard_timeout_tasks", 0)) > 0:
        return "bounded_worker_stage_successor"
    if int(supervision.get("worker_nonzero_tasks", 0)) > 0:
        return "worker_exception_successor"
    if int(mechanism.get("success_tasks", 0)) < 8:
        return "proof_capability_coverage_successor"
    if int(mechanism.get("conversion_any_usable_page_tasks", 0)) == 0:
        return "source_ranking_fetch_selection_successor"
    if not diagnostic:
        return "conversion_partition_observability_successor"
    if not reliability:
        return "provider_or_fetch_reliability_successor"
    if not parent_validation:
        return "parent_validation_successor"
    if not latency:
        return "latency_capacity_successor"
    counts = reason_family_counts(mechanism)
    # Dict insertion order is the frozen tie-break order.
    family = max(counts, key=lambda name: counts[name])
    return FAMILY_ROUTES[family]


def _patched_core() -> dict[str, Any]:
    value = dict(_ORIGINAL_PATCHED_CORE())
    value.update(
        {
            "PROTOCOL_ID": PROTOCOL_ID,
            "PROTOCOL": PROTOCOL,
            "PREAUDIT": PREAUDIT,
            "ACTIVATION": ACTIVATION,
            "EXECUTION_START": EXECUTION_START,
            "RESULT": RESULT,
            "DECISION": DECISION,
            "POSTAUDIT": POSTAUDIT,
            "PARENT": PARENT,
            "LEASE_OWNER": LEASE_OWNER,
            "LEASE_PURPOSE": LEASE_PURPOSE,
            "RUNNER_MARKER": RUNNER_MARKER,
            "SOURCE_FILES": SOURCE_FILES,
            "TEST_SUITES": TEST_SUITES,
            "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
            "ENTITY_GROUPS": ENTITY_GROUPS,
            "QUESTIONS": QUESTIONS,
            "GATES": GATES,
            "TARGETED_PROOF_POLICY_ID": conversion_proof.POLICY_ID,
            "TARGETED_PARENT_POLICY_ID": conversion_parent.POLICY_ID,
            "_prior_questions": _prior_questions,
            "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
            "_parent": _parent,
            "_task_contract": _task_contract,
            "run_targeted_worker": conversion_parent.run_conversion_worker,
            "supervise_targeted_worker_with_separated_budget": conversion_parent.supervise_conversion_worker_with_separated_budget,
            "run_targeted_parent_with_separated_budget": conversion_parent.run_conversion_parent_with_separated_budget,
            "aggregate_projections": aggregate_conversion_projections,
            "validate_targeted_aggregate": total.validate_aggregate,
            "_mechanism_passed": mechanism_passed,
            "_diagnostic_route": diagnostic_route,
        }
    )
    return value


@contextmanager
def configured_predecessor(*, validators: bool = False) -> Iterator[None]:
    patches: dict[str, Any] = {
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
        "PREVIOUS_RESULT": PREVIOUS_RESULT,
        "PREVIOUS_DECISION": PREVIOUS_DECISION,
        "PREVIOUS_POSTAUDIT": PREVIOUS_POSTAUDIT,
        "PREVIOUS_PROTOCOL_ID": PREVIOUS_PROTOCOL_ID,
        "ENTITY_GROUPS": ENTITY_GROUPS,
        "QUESTIONS": QUESTIONS,
        "GATES": GATES,
        "SOURCE_FILES": SOURCE_FILES,
        "TEST_SUITES": TEST_SUITES,
        "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
        "_prior_questions": _prior_questions,
        "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
        "_parent": _parent,
        "_task_contract": _task_contract,
        "_previous_closed": _previous_closed,
        "_record_bound_binding": _record_bound_binding,
        "_patched_core": _patched_core,
    }
    if validators:
        patches.update(
            {
                "validate_protocol": validate_protocol,
                "validate_preaudit": validate_preaudit,
                "validate_activation": validate_activation,
                "validate_execution_start": validate_execution_start,
            }
        )
    missing = object()
    originals = {name: getattr(predecessor, name, missing) for name in patches}
    try:
        for name, value in patches.items():
            setattr(predecessor, name, value)
        yield
    finally:
        for name, value in originals.items():
            if value is missing:
                delattr(predecessor, name)
            else:
                setattr(predecessor, name, value)


@contextmanager
def _protocol_validator_bridge() -> Iterator[None]:
    modules = (predecessor, predecessor.predecessor)
    originals = [(module, module.validate_protocol) for module in modules]
    try:
        for module in modules:
            module.validate_protocol = validate_protocol
        yield
    finally:
        for module, original in originals:
            module.validate_protocol = original


def build_protocol(
    *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.22 predecessor is not closed")
    with configured_predecessor():
        value = predecessor.build_protocol(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_nonbenchmark_page_observation_conversion_diagnostic_gate"
    value["mechanism"].update(
        {
            "conversion_observability_policy": observability.POLICY_ID,
            "proof_carrying_conversion_observability_policy": conversion_proof.POLICY_ID,
            "total_conversion_projection_policy": total.POLICY_ID,
            "bounded_conversion_parent_policy": conversion_parent.POLICY_ID,
            "diagnostic_complete_not_quality_threshold": True,
            "public_success_row_reingestion_allowed": False,
            "fresh_paired_dev64_directly_authorized": False,
        }
    )
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value)


def validate_protocol(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_nonbenchmark_absolute_terminal_entropy_credit_gate"
    for name in (
        "conversion_observability_policy",
        "proof_carrying_conversion_observability_policy",
        "total_conversion_projection_policy",
        "bounded_conversion_parent_policy",
        "diagnostic_complete_not_quality_threshold",
        "public_success_row_reingestion_allowed",
        "fresh_paired_dev64_directly_authorized",
    ):
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    mechanism = copied.get("mechanism", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_nonbenchmark_page_observation_conversion_diagnostic_gate"
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("conversion_observability_policy") != observability.POLICY_ID
        or mechanism.get("proof_carrying_conversion_observability_policy")
        != conversion_proof.POLICY_ID
        or mechanism.get("total_conversion_projection_policy") != total.POLICY_ID
        or mechanism.get("bounded_conversion_parent_policy")
        != conversion_parent.POLICY_ID
        or mechanism.get("diagnostic_complete_not_quality_threshold") is not True
        or mechanism.get("public_success_row_reingestion_allowed") is not False
        or mechanism.get("fresh_paired_dev64_directly_authorized") is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.22 conversion diagnostic protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(), _protocol_validator_bridge():
        value = predecessor.build_preaudit(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_348_prior_external_questions",
        None,
    )
    checks.pop("prior_external_questions_and_entities_exactly_348_and_2784", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_356_prior_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_356_and_2848"] = True
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.45.22 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    core_checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_356_prior_external_questions",
        None,
    )
    core_checks.pop("prior_external_questions_and_entities_exactly_356_and_2848", None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_348_prior_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_348_and_2784"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor(), _protocol_validator_bridge():
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or checks.get(
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_356_prior_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_356_and_2848")
        is not True
        or checks.get("focused_tests", {}).get("test_count")
        != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.22 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_predecessor(validators=True):
        return predecessor.build_activation(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_predecessor(validators=True):
        return predecessor.build_execution_start(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.validate_public_result(value)


def run_probe() -> dict[str, Any]:
    with capability_collection(), configured_predecessor(validators=True):
        return predecessor.run_probe()


def _decision_authorization(passed: bool) -> dict[str, bool]:
    return {
        "selected_mechanism_successor_design": passed,
        "diagnostic_repair_successor_design": not passed,
        "fresh_mechanism_external_gate_launch": False,
        "fresh_paired_dev64_design": False,
        "fresh_paired_dev64_launch": False,
        "new_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def build_decision(*, now: int | None = None) -> dict[str, Any]:
    result = validate_public_result(_read(RESULT))
    mechanism = result["mechanism_aggregate"]
    route = diagnostic_route(
        mechanism,
        result["supervision_aggregate"],
        diagnostic=result["mechanism_passed"],
        reliability=result["reliability_passed"],
        parent_validation=result["parent_validation_passed"],
        latency=result["latency_passed"],
    )
    passed = result["passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v24522_conversion_diagnostic_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": _base().time.time() if now is None else int(now),
        "status": (
            "fresh_conversion_diagnostic_go"
            if passed
            else "fresh_conversion_diagnostic_no_go"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "reason_family_pair_counts": reason_family_counts(mechanism),
        "claim_scope": {
            "fresh_nonbenchmark_conversion_diagnostic_measured": True,
            "benchmark_quality_measured": False,
            "paired_dev64_or_exact220_authorized": False,
            "sota_supported": False,
        },
        "authorization": _decision_authorization(passed),
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return validate_decision(value=value)


def validate_decision(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(DECISION)
    result = validate_public_result(_read(RESULT))
    passed = result["passed"] is True
    expected_route = diagnostic_route(
        result["mechanism_aggregate"],
        result["supervision_aggregate"],
        diagnostic=result["mechanism_passed"],
        reliability=result["reliability_passed"],
        parent_validation=result["parent_validation_passed"],
        latency=result["latency_passed"],
    )
    if (
        copied.get("role") != "v24522_conversion_diagnostic_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != (
            "fresh_conversion_diagnostic_go"
            if passed
            else "fresh_conversion_diagnostic_no_go"
        )
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != expected_route
        or copied.get("reason_family_pair_counts")
        != reason_family_counts(result["mechanism_aggregate"])
        or copied.get("claim_scope")
        != {
            "fresh_nonbenchmark_conversion_diagnostic_measured": True,
            "benchmark_quality_measured": False,
            "paired_dev64_or_exact220_authorized": False,
            "sota_supported": False,
        }
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.22 decision drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    decision = validate_decision()
    base = _base()
    lease_active = (
        base.lease_observation(ROOT, Path("/proc")).get("active") is not False
    )
    watchers = base.protected_watcher_snapshot()
    expected = _read(EXECUTION_START)["protected_watchers"]
    findings: list[str] = []
    if lease_active:
        findings.append("shared_api_lease_active")
    if watchers != expected:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24522_conversion_diagnostic_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(base.time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "decision_sha256": sha256(ROOT / DECISION),
        "decision_status": decision["status"],
        "diagnostic_route": decision["diagnostic_route"],
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "private_task_or_web_content_persisted": False,
        "opaque_capability_references_destroyed_after_aggregation": True,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_postaudit(value=value)


def validate_postaudit(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(POSTAUDIT)
    decision = validate_decision()
    if (
        copied.get("role")
        != "v24522_conversion_diagnostic_external_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status") != decision["status"]
        or copied.get("diagnostic_route") != decision["diagnostic_route"]
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers")
        != _base().protected_watcher_snapshot()
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or copied.get("private_task_or_web_content_persisted") is not False
        or copied.get("opaque_capability_references_destroyed_after_aggregation")
        is not True
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.22 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_predecessor(validators=True):
        predecessor.run_process_subcommand(args)


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
    parser.add_argument(_base().worker_budget.DEADLINE_ORIGIN_ARGUMENT)
    args = parser.parse_args()
    base = _base()
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
