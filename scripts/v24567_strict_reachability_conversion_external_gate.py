#!/usr/bin/env python3
"""Fresh one-wave external gate for strict reachability conversion.

The 64 visible entities are literal/canonical disjoint from all 436 external
questions and 3,488 entities consumed through V2.45.54.  Runtime input is
exactly ``opaque_id`` and ``question``.  A successful public row can be minted
only from a V2.45.57 opaque capability and is projected once through V2.45.64
by the bounded V2.45.65 parent.

The strict mechanism gate requires the same task to contain a one-observation
reachable plan, a changed legacy entropy-first choice, a selected alias
surface, a new observation, positive information gain/action credit, a safe
change, and positive decision credit.  This task-level joint does not claim
call-, query-, lead-, source-, or page-level causality.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import threading
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
from deepwide_agent import v24523_conservative_alias_title_projection as alias_projection  # noqa: E402
from deepwide_agent import v24529_alias_seeded_target_acquisition as acquisition  # noqa: E402
from deepwide_agent import v24547_alias_surface_observability as surface  # noqa: E402
from deepwide_agent import v24555_decision_reachability_planner as planner  # noqa: E402
from deepwide_agent import v24557_proof_carrying_decision_reachability as proof  # noqa: E402
from deepwide_agent import v24564_strict_reachability_conversion_joint as total  # noqa: E402
from deepwide_agent import v24565_bounded_strict_reachability_conversion_parent as bounded  # noqa: E402
from scripts import v24492_targeted_external_gate as base  # noqa: E402
from scripts import v24554_alias_joint_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24567_fresh_strict_reachability_conversion_external_gate_v1"
PROTOCOL = Path(
    f"results/v24567_strict_reachability_conversion_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24567_strict_reachability_conversion_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24567_strict_reachability_conversion_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24567_strict_reachability_conversion_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24567_strict_reachability_conversion_external_result_v1_{DATE}.json"
)
DECISION = Path(
    f"results/v24567_strict_reachability_conversion_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24567_strict_reachability_conversion_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24566_strict_reachability_conversion_build_audit_v1_{DATE}.json"
)
PREVIOUS_RESULT = predecessor.RESULT
PREVIOUS_DECISION = predecessor.DECISION
PREVIOUS_POSTAUDIT = predecessor.POSTAUDIT
RUNNER_MARKER = "scripts/v24567_strict_reachability_conversion_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_strict_reachability_conversion_external_gate"
PRIOR_QUESTION_COUNT = 436
PRIOR_ENTITY_COUNT = 3488
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS
population = predecessor.predecessor.population


ENTITY_GROUPS = (
    (
        "Albion College Michigan",
        "Beloit College Wisconsin",
        "Berea College Kentucky",
        "Centre College Kentucky",
        "Coe College Iowa",
        "Earlham College Indiana",
        "Hendrix College Arkansas",
        "Millsaps College Mississippi",
    ),
    (
        "Rhodes College Tennessee",
        "Sewanee University of the South",
        "Wofford College South Carolina",
        "Presbyterian College South Carolina",
        "Berry College Georgia",
        "Austin College Texas",
        "Southwestern University Texas",
        "Trinity University Texas",
    ),
    (
        "Hardin-Simmons University",
        "Abilene Christian University",
        "Lewis and Clark College Oregon",
        "Whitworth University Washington",
        "Northwest University Washington",
        "Warner Pacific University",
        "Bushnell University Oregon",
        "Multnomah University Oregon",
    ),
    (
        "Eastern Oregon University",
        "Western Oregon University",
        "Southern Oregon University",
        "Evergreen State College Washington",
        "Saint Martins University Washington",
        "Central Washington University",
        "Eastern Washington University",
        "Northwest Nazarene University",
    ),
    (
        "Rocky Mountain College Montana",
        "Carroll College Montana",
        "University of Great Falls Montana",
        "Providence University Montana",
        "Minot State University North Dakota",
        "Dakota State University",
        "Northern State University South Dakota",
        "Chadron State College Nebraska",
    ),
    (
        "Doane University Nebraska",
        "Hastings College Nebraska",
        "Mount Mercy University Iowa",
        "Morningside University Iowa",
        "Wartburg College Iowa",
        "Drake University Iowa",
        "Loras College Iowa",
        "Saint Ambrose University Iowa",
    ),
    (
        "Graceland University Iowa",
        "Dakota Wesleyan University South Dakota",
        "Viterbo University Wisconsin",
        "Marian University Wisconsin",
        "Lakeland University Wisconsin",
        "Concordia University Wisconsin",
        "Edgewood College Wisconsin",
        "Carthage College Wisconsin",
    ),
    (
        "Ripon College Wisconsin",
        "Silver Lake College Wisconsin",
        "Finlandia University Michigan",
        "Calvin University Michigan",
        "Davenport University Michigan",
        "Ferris State University Michigan",
        "Kettering University Michigan",
        "Madonna University Michigan",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.67 entity group drifted")
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
    **copy.deepcopy(predecessor.GATES),
    "minimum_decision_reachability_any_plan_tasks": 1,
    "minimum_decision_reachability_one_observation_plan_tasks": 1,
    "minimum_decision_reachability_changed_legacy_choice_tasks": 1,
    "minimum_strict_reachability_full_conversion_joint_tasks": 1,
}
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *predecessor.SOURCE_FILES,
            "src/deepwide_agent/v24555_decision_reachability_planner.py",
            "tests/test_v24555_decision_reachability_planner.py",
            "src/deepwide_agent/v24557_proof_carrying_decision_reachability.py",
            "tests/test_v24557_proof_carrying_decision_reachability.py",
            "src/deepwide_agent/v24558_total_decision_reachability_projection.py",
            "tests/test_v24558_total_decision_reachability_projection.py",
            "src/deepwide_agent/v24561_decision_reachability_conversion_joint.py",
            "tests/test_v24561_decision_reachability_conversion_joint.py",
            "src/deepwide_agent/v24562_bounded_reachability_conversion_joint_parent.py",
            "tests/test_v24562_bounded_reachability_conversion_joint_parent.py",
            "src/deepwide_agent/v24564_strict_reachability_conversion_joint.py",
            "tests/test_v24564_strict_reachability_conversion_joint.py",
            "src/deepwide_agent/v24565_bounded_strict_reachability_conversion_parent.py",
            "tests/test_v24565_bounded_strict_reachability_conversion_parent.py",
            "scripts/audit_v24560_bounded_decision_reachability_build.py",
            "tests/test_audit_v24560_bounded_decision_reachability_build.py",
            "results/v24560_bounded_decision_reachability_build_audit_v1_20260805.json",
            "scripts/audit_v24563_reachability_conversion_joint_build.py",
            "tests/test_audit_v24563_reachability_conversion_joint_build.py",
            "results/v24563_reachability_conversion_joint_build_audit_v1_20260805.json",
            "scripts/audit_v24566_strict_reachability_conversion_build.py",
            "tests/test_audit_v24566_strict_reachability_conversion_build.py",
            str(PARENT),
            str(PREVIOUS_RESULT),
            str(PREVIOUS_DECISION),
            str(PREVIOUS_POSTAUDIT),
            RUNNER_MARKER,
            "tests/test_v24567_strict_reachability_conversion_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *predecessor.TEST_SUITES,
    ("tests/test_v24555_decision_reachability_planner.py", 7, 120),
    ("tests/test_v24557_proof_carrying_decision_reachability.py", 7, 300),
    ("tests/test_v24558_total_decision_reachability_projection.py", 6, 300),
    ("tests/test_v24561_decision_reachability_conversion_joint.py", 6, 300),
    ("tests/test_v24562_bounded_reachability_conversion_joint_parent.py", 4, 300),
    ("tests/test_v24564_strict_reachability_conversion_joint.py", 5, 300),
    ("tests/test_v24565_bounded_strict_reachability_conversion_parent.py", 5, 300),
    ("tests/test_audit_v24566_strict_reachability_conversion_build.py", 7, 120),
    ("tests/test_v24567_strict_reachability_conversion_external_gate.py", 12, 480),
)
EXPECTED_TEST_COUNT = predecessor.EXPECTED_TEST_COUNT + 59


_BASE_BUILD_PROTOCOL = base.build_protocol
_BASE_VALIDATE_PROTOCOL = base.validate_protocol
_BASE_BUILD_PREAUDIT = base.build_preaudit
_BASE_VALIDATE_ACTIVATION = base.validate_activation
_BASE_VALIDATE_EXECUTION_START = base.validate_execution_start
_BASE_VALIDATE_PUBLIC_RESULT = base.validate_public_result
_ORIGINAL_TASK_PROJECTION = total.task_projection
_PREDECESSOR_MECHANISM_PASSED = predecessor.mechanism_passed
_PREDECESSOR_DIAGNOSTIC_ROUTE = predecessor.diagnostic_route
_COLLECTOR_GUARD = threading.Lock()
_ACTIVE_COLLECTOR: _CapabilityCollector | None = None


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.67 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    baseline = value.get("freshness_baseline", {})
    if (
        not isinstance(value, dict)
        or value.get("role")
        != "v24566_strict_reachability_conversion_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 27
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or baseline.get("prior_external_question_count") != PRIOR_QUESTION_COUNT
        or baseline.get("prior_external_entity_count") != PRIOR_ENTITY_COUNT
        or baseline.get(
            "v24554_population_resume_retry_rerun_or_evaluation_authorized"
        )
        is not False
        or authorization.get(
            "fresh_disjoint_bounded_strict_reachability_conversion_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.67 build parent drifted")
    return value


def _previous_closed() -> bool:
    result = predecessor.validate_public_result(_read(PREVIOUS_RESULT))
    decision = predecessor.validate_decision(value=_read(PREVIOUS_DECISION))
    postaudit = predecessor.validate_postaudit(value=_read(PREVIOUS_POSTAUDIT))
    mechanism = result.get("mechanism_aggregate", {})
    return (
        result.get("selected") == 8
        and result.get("passed") is False
        and result.get("mechanism_passed") is False
        and mechanism.get("success_tasks") == 8
        and mechanism.get("failure_as_zero_tasks") == 0
        and mechanism.get(
            "selected_alias_surface_hit_new_observation_and_positive_information_gain_count_tasks"
        )
        == 1
        and mechanism.get("alias_joint_safe_change_improvement_tasks") == 0
        and mechanism.get("alias_joint_action_positive_decision_credit_tasks") == 0
        and decision.get("status") == "fresh_alias_joint_no_go"
        and decision.get("diagnostic_route") == "action_safe_change_successor"
        and decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is False
        and decision.get("authorization", {}).get("new_exact220") is False
        and postaudit.get("audit_valid") is True
        and postaudit.get("findings") == []
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get(
            "opaque_capability_references_destroyed_after_aggregation"
        )
        is True
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
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_436_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_surfaces_globally_unique_and_query_blind": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_populations_through_v24554_counted_as_consumed": True,
        "prior_population_resume_retry_rerun_or_evaluation": False,
        "population_selection_uses_visible_names_and_frozen_alias_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_strict_reachability_conversion_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_strict_reachability_conversion_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def _successor_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.67 V2.45.54 closure drifted")
    return {
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "v24554_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24554_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24554_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "same_or_prior_population_resume_retry_rerun_or_evaluation": False,
        "new_population_reuses_prior_question_or_entity": False,
        "decision_reachability_planner_policy": planner.POLICY_ID,
        "proof_carrying_decision_reachability_policy": proof.POLICY_ID,
        "strict_reachability_conversion_projection_policy": total.POLICY_ID,
        "bounded_strict_reachability_conversion_parent_policy": bounded.POLICY_ID,
        "minimum_independent_observations_is_primary_priority": True,
        "optimistic_information_gain_per_observation_is_secondary_priority": True,
        "source_posterior_margin_leave_one_out_safe_change_or_decision_credit_rules_relaxed": False,
        "strict_joint_claims_call_query_lead_source_or_page_level_causality": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


class _CapabilityCollector:
    """One-shot bridge from V2.45.57 capabilities to V2.45.64 aggregate."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._capabilities: dict[
            int, proof.ValidatedProofCarryingDecisionReachability
        ] = {}
        self._rows: dict[int, dict[str, Any]] = {}
        self._consumed = False

    def project(
        self,
        ordinal: int,
        capability: proof.ValidatedProofCarryingDecisionReachability,
    ) -> dict[str, Any]:
        row = _ORIGINAL_TASK_PROJECTION(ordinal, capability)
        with self._lock:
            if self._consumed or ordinal in self._capabilities:
                raise RuntimeError("V2.45.67 duplicate or late capability")
            self._capabilities[ordinal] = capability
            self._rows[ordinal] = copy.deepcopy(row)
        return row

    def aggregate(
        self, values: Sequence[Mapping[str, Any]], *, selected: int
    ) -> dict[str, Any]:
        if len(values) != selected:
            raise ValueError("V2.45.67 aggregate selection drifted")
        with self._lock:
            if self._consumed:
                raise RuntimeError("V2.45.67 capabilities already consumed")
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
                    raise RuntimeError("V2.45.67 success lacks captured capability")
                if _ORIGINAL_TASK_PROJECTION(ordinal, capability) != row:
                    raise RuntimeError("V2.45.67 capability/public row mismatch")
                proof_inputs.append(capability)
            else:
                if capability is not None or captured is not None:
                    raise RuntimeError("V2.45.67 failure unexpectedly has capability")
                proof_inputs.append(row)
        if capabilities or rows:
            raise RuntimeError("V2.45.67 unconsumed capability vector")
        installed = total.task_projection
        if (
            getattr(installed, "__self__", None) is not self
            or getattr(installed, "__func__", None) is not type(self).project
        ):
            raise RuntimeError("V2.45.67 capability projector binding drifted")
        total.task_projection = _ORIGINAL_TASK_PROJECTION
        try:
            return total.aggregate_projections(proof_inputs, selected=selected)
        finally:
            drifted = total.task_projection is not _ORIGINAL_TASK_PROJECTION
            total.task_projection = installed
            if drifted:
                raise RuntimeError("V2.45.67 aggregate projector drifted")

    def destroy(self) -> None:
        with self._lock:
            self._capabilities.clear()
            self._rows.clear()
            self._consumed = True


@contextmanager
def capability_collection() -> Iterator[_CapabilityCollector]:
    global _ACTIVE_COLLECTOR
    if not _COLLECTOR_GUARD.acquire(blocking=False):
        raise RuntimeError("V2.45.67 capability collector is already active")
    collector = _CapabilityCollector()
    original = total.task_projection
    if _ACTIVE_COLLECTOR is not None:
        _COLLECTOR_GUARD.release()
        raise RuntimeError("V2.45.67 active collector drifted")
    _ACTIVE_COLLECTOR = collector
    total.task_projection = collector.project
    try:
        yield collector
    finally:
        total.task_projection = original
        collector.destroy()
        _ACTIVE_COLLECTOR = None
        _COLLECTOR_GUARD.release()


def aggregate_strict_projections(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    collector = _ACTIVE_COLLECTOR
    if collector is None:
        raise RuntimeError("V2.45.67 opaque capability collector is absent")
    return collector.aggregate(values, selected=selected)


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        _PREDECESSOR_MECHANISM_PASSED(value)
        and value.get("decision_reachability_any_plan_tasks", 0)
        >= GATES["minimum_decision_reachability_any_plan_tasks"]
        and value.get("decision_reachability_one_observation_plan_tasks", 0)
        >= GATES["minimum_decision_reachability_one_observation_plan_tasks"]
        and value.get("decision_reachability_changed_legacy_choice_tasks", 0)
        >= GATES["minimum_decision_reachability_changed_legacy_choice_tasks"]
        and value.get(total.TASK_FIELD, 0)
        >= GATES["minimum_strict_reachability_full_conversion_joint_tasks"]
        and value.get(
            "all_decision_reachability_success_rows_consumed_validated_capabilities"
        )
        is True
        and value.get(
            "all_decision_reachability_failure_rows_are_content_free_zero_projections"
        )
        is True
        and value.get(
            "decision_reachability_failure_rows_claim_zero_private_effects"
        )
        is False
        and value.get("decision_reachability_private_task_content_emitted") is False
        and value.get("decision_reachability_privileged_evaluator_content_read")
        is False
        and value.get(
            "decision_reachability_projection_claims_expected_utility_or_causality"
        )
        is False
        and value.get(
            "decision_reachability_conversion_joint_claims_call_or_lead_level_causality"
        )
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
    inherited = _PREDECESSOR_DIAGNOSTIC_ROUTE(
        mechanism,
        supervision,
        diagnostic=True,
        reliability=reliability,
        parent_validation=parent_validation,
        latency=latency,
    )
    if inherited != "fresh_paired_dev64_design":
        return inherited
    if int(mechanism.get("decision_reachability_any_plan_tasks", 0)) == 0:
        return "decision_reachability_plan_coverage_successor"
    if int(mechanism.get("decision_reachability_one_observation_plan_tasks", 0)) == 0:
        return "one_observation_reachability_successor"
    if int(mechanism.get("decision_reachability_changed_legacy_choice_tasks", 0)) == 0:
        return "legacy_choice_change_successor"
    if int(mechanism.get(total.TASK_FIELD, 0)) == 0:
        return "strict_reachability_conversion_joint_successor"
    return "fresh_paired_dev64_design" if diagnostic else "strict_joint_successor"


def _patched_base(*, validators: bool) -> dict[str, Any]:
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
        "LEASE_OWNER": LEASE_OWNER,
        "LEASE_PURPOSE": LEASE_PURPOSE,
        "RUNNER_MARKER": RUNNER_MARKER,
        "ENTITY_GROUPS": ENTITY_GROUPS,
        "QUESTIONS": QUESTIONS,
        "GATES": GATES,
        "SOURCE_FILES": SOURCE_FILES,
        "TEST_SUITES": TEST_SUITES,
        "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
        "TARGETED_PROOF_POLICY_ID": proof.POLICY_ID,
        "TARGETED_PARENT_POLICY_ID": bounded.POLICY_ID,
        "_prior_questions": _prior_questions,
        "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
        "_parent": _parent,
        "_task_contract": _task_contract,
        "_protocol_authorization": _protocol_authorization,
        "_activation_authorization": _activation_authorization,
        "run_targeted_worker": bounded.run_worker,
        "supervise_targeted_worker_with_separated_budget": bounded.supervise_worker_with_separated_budget,
        "run_targeted_parent_with_separated_budget": bounded.run_parent_with_separated_budget,
        "aggregate_projections": aggregate_strict_projections,
        "validate_targeted_aggregate": total.validate_aggregate,
        "_mechanism_passed": mechanism_passed,
    }
    if validators:
        patches.update(
            {
                "validate_protocol": validate_protocol,
                "validate_preaudit": validate_preaudit,
                "validate_activation": validate_activation,
                "validate_execution_start": validate_execution_start,
                "validate_public_result": validate_public_result,
            }
        )
    return patches


@contextmanager
def configured_base(*, validators: bool = True) -> Iterator[None]:
    patches = _patched_base(validators=validators)
    missing = object()
    originals = {name: getattr(base, name, missing) for name in patches}
    try:
        for name, value in patches.items():
            setattr(base, name, value)
        yield
    finally:
        for name, value in originals.items():
            if value is missing:
                delattr(base, name)
            else:
                setattr(base, name, value)


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    if not _previous_closed():
        raise RuntimeError("V2.45.67 predecessor is not closed")
    _parent(root)
    with configured_base(validators=False):
        value = _BASE_BUILD_PROTOCOL(
            root, now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_nonbenchmark_strict_reachability_conversion_gate"
    value["successor_binding"] = _successor_binding()
    value["mechanism"].update(
        {
            "decision_reachability_planner_policy": planner.POLICY_ID,
            "proof_carrying_decision_reachability_policy": proof.POLICY_ID,
            "strict_reachability_conversion_projection_policy": total.POLICY_ID,
            "bounded_strict_reachability_conversion_parent_policy": bounded.POLICY_ID,
            "minimum_independent_observations_is_primary_priority": True,
            "optimistic_information_gain_per_observation_is_secondary_priority": True,
            "strict_same_task_one_observation_changed_legacy_full_conversion_required": True,
            "strict_joint_claims_call_query_lead_source_or_page_level_causality": False,
            "source_count_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_relaxed": False,
            "pure_total_projector_restored_only_during_aggregate": True,
            "same_run_credit_used_for_routing_training_or_policy_update": False,
        }
    )
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(root, value=value)


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    copied = dict(value) if value is not None else base._read(root, PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_nonbenchmark_targeted_entropy_decision_credit_gate"
    core.pop("successor_binding", None)
    added = (
        "decision_reachability_planner_policy",
        "proof_carrying_decision_reachability_policy",
        "strict_reachability_conversion_projection_policy",
        "bounded_strict_reachability_conversion_parent_policy",
        "minimum_independent_observations_is_primary_priority",
        "optimistic_information_gain_per_observation_is_secondary_priority",
        "strict_same_task_one_observation_changed_legacy_full_conversion_required",
        "strict_joint_claims_call_query_lead_source_or_page_level_causality",
        "source_count_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_relaxed",
        "pure_total_projector_restored_only_during_aggregate",
        "same_run_credit_used_for_routing_training_or_policy_update",
    )
    for name in added:
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_base(validators=False):
        _BASE_VALIDATE_PROTOCOL(root, value=core)
    mechanism = copied.get("mechanism", {})
    budget = copied.get("budget", {})
    provider = copied.get("provider", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_nonbenchmark_strict_reachability_conversion_gate"
        or copied.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or copied.get("successor_binding") != _successor_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("targeted_proof_policy") != proof.POLICY_ID
        or mechanism.get("targeted_parent_policy") != bounded.POLICY_ID
        or mechanism.get("decision_reachability_planner_policy")
        != planner.POLICY_ID
        or mechanism.get("proof_carrying_decision_reachability_policy")
        != proof.POLICY_ID
        or mechanism.get("strict_reachability_conversion_projection_policy")
        != total.POLICY_ID
        or mechanism.get("bounded_strict_reachability_conversion_parent_policy")
        != bounded.POLICY_ID
        or mechanism.get("minimum_independent_observations_is_primary_priority")
        is not True
        or mechanism.get(
            "optimistic_information_gain_per_observation_is_secondary_priority"
        )
        is not True
        or mechanism.get(
            "strict_same_task_one_observation_changed_legacy_full_conversion_required"
        )
        is not True
        or mechanism.get(
            "strict_joint_claims_call_query_lead_source_or_page_level_causality"
        )
        is not False
        or mechanism.get(
            "source_count_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_relaxed"
        )
        is not False
        or mechanism.get("pure_total_projector_restored_only_during_aggregate")
        is not True
        or mechanism.get("same_run_credit_used_for_routing_training_or_policy_update")
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
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.67 protocol drifted")
    return copied


def build_preaudit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    with configured_base(validators=True):
        value = _BASE_BUILD_PREAUDIT(root, now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop("prior_external_questions_and_entities_exactly_308_and_2464", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_436_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_436_and_3488"] = True
    checks["all_prior_populations_resume_retry_rerun_or_evaluation"] = False
    checks["v24566_strict_reachability_conversion_build_audit_validated"] = True
    checks["strict_joint_claims_call_query_lead_source_or_page_level_causality"] = False
    checks["module_global_projector_patch_or_shared_parent_context_used"] = False
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(root, value=value)


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    copied = dict(value) if value is not None else base._read(root, PREAUDIT)
    checks = copied.get("checks")
    provenance = copied.get("provenance")
    required_true = (
        "protocol_valid_and_sealed",
        "fresh_64_entity_vector_frozen",
        "one_wave_capacity_frozen",
        "phase_deadlines_exactly_150_220_245",
        "keyless_proxy_listening_without_api_request",
        "shared_api_lease_inactive",
        "protocol_commit_pushed",
        "worktree_clean",
        "all_protocol_sources_tracked",
        "future_surface_pristine",
        "protected_watchers_unchanged",
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_436_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_436_and_3488",
        "v24566_strict_reachability_conversion_build_audit_validated",
    )
    if (
        copied.get("role") != "v24492_targeted_external_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or not isinstance(checks, Mapping)
        or any(checks.get(name) is not True for name in required_true)
        or checks.get("all_prior_populations_resume_retry_rerun_or_evaluation")
        is not False
        or checks.get(
            "strict_joint_claims_call_query_lead_source_or_page_level_causality"
        )
        is not False
        or checks.get("module_global_projector_patch_or_shared_parent_context_used")
        is not False
        or checks.get("benchmark_or_evaluator_surface_authorized") is not False
        or not isinstance(checks.get("focused_tests"), Mapping)
        or checks["focused_tests"].get("passed") is not True
        or checks["focused_tests"].get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("privileged_field_accesses") != []
        or copied.get("evaluator_imports") != []
        or copied.get("protected_watchers") != base.protected_watcher_snapshot()
        or not isinstance(provenance, Mapping)
        or provenance.get("protocol_sha256") != sha256(root / PROTOCOL)
        or provenance.get("parent_sha256") != sha256(root / PARENT)
        or provenance.get("surface_manifest_sha256")
        != validate_protocol(root)["surface_manifest_sha256"]
        or provenance.get("head") != provenance.get("target_main")
        or copied.get("authorization") != _activation_authorization()
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.67 preactivation audit drifted")
    return copied


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    with configured_base(validators=True):
        value = base.build_activation(root, now=now)
    value = copy.deepcopy(value)
    authorization = value.get("authorization")
    if not isinstance(authorization, Mapping):
        raise RuntimeError("V2.45.67 activation authorization is absent")
    authorization = dict(authorization)
    if authorization.pop("one_fresh_targeted_external_probe_launch", None) is not True:
        raise RuntimeError("V2.45.67 inherited activation authorization drifted")
    if authorization != _activation_authorization():
        raise RuntimeError("V2.45.67 activation authorization drifted")
    value["authorization"] = authorization
    value["activation_payload_sha256"] = payload_sha256(
        {
            key: item
            for key, item in value.items()
            if key != "activation_payload_sha256"
        }
    )
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    with configured_base(validators=True):
        return _BASE_VALIDATE_ACTIVATION(root)


def build_execution_start(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    with configured_base(validators=True):
        return base.build_execution_start(root, now=now)


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    with configured_base(validators=True):
        return _BASE_VALIDATE_EXECUTION_START(root)


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    mechanism = value.get("mechanism_aggregate")
    required = (
        "decision_reachability_any_plan_tasks",
        "decision_reachability_one_observation_plan_tasks",
        "decision_reachability_changed_legacy_choice_tasks",
        total.TASK_FIELD,
        "total_decision_reachability_count_fields",
        "total_decision_reachability_conversion_joint_count_fields",
    )
    if not isinstance(mechanism, Mapping) or any(
        name not in mechanism for name in required
    ):
        raise RuntimeError("V2.45.67 strict aggregate schema is absent")
    total.validate_aggregate(mechanism)
    with configured_base(validators=False):
        return _BASE_VALIDATE_PUBLIC_RESULT(value)


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    with capability_collection(), configured_base(validators=True):
        return base.run_probe(root)


def _decision_authorization(passed: bool) -> dict[str, bool]:
    return {
        "diagnostic_successor_design": not passed,
        "fresh_paired_dev64_design": passed,
        "fresh_paired_dev64_launch": False,
        "new_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def build_decision(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    result = validate_public_result(base._read(root, RESULT))
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
        "role": "v24567_strict_reachability_conversion_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_strict_reachability_conversion_go"
            if passed
            else "fresh_strict_reachability_conversion_no_go"
        ),
        "passed": passed,
        "result_sha256": sha256(root / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_strict_reachability_conversion_measured": True,
            "call_query_lead_source_or_page_level_causality_claimed": False,
            "benchmark_quality_measured": False,
            "paired_dev64_launch_authorized": False,
            "sota_supported": False,
        },
        "authorization": _decision_authorization(passed),
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return validate_decision(root, value=value)


def validate_decision(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    copied = dict(value) if value is not None else base._read(root, DECISION)
    result = validate_public_result(base._read(root, RESULT))
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
        "fresh_strict_reachability_conversion_go"
        if passed
        else "fresh_strict_reachability_conversion_no_go"
    )
    if (
        copied.get("role")
        != "v24567_strict_reachability_conversion_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(root / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope", {}).get(
            "call_query_lead_source_or_page_level_causality_claimed"
        )
        is not False
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.67 decision drifted")
    return copied


def build_postaudit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    decision = validate_decision(root)
    lease_active = (
        base.lease_observation(root, Path("/proc")).get("active") is not False
    )
    watchers = base.protected_watcher_snapshot()
    expected = base._read(root, EXECUTION_START)["protected_watchers"]
    findings: list[str] = []
    if lease_active:
        findings.append("shared_api_lease_active")
    if watchers != expected:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24567_strict_reachability_conversion_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision["status"],
        "diagnostic_route": decision["diagnostic_route"],
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "private_task_or_web_content_persisted": False,
        "opaque_capability_references_destroyed_after_aggregation": True,
        "strict_joint_claims_call_query_lead_source_or_page_level_causality": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_postaudit(root, value=value)


def validate_postaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    copied = dict(value) if value is not None else base._read(root, POSTAUDIT)
    decision = validate_decision(root)
    if (
        copied.get("role")
        != "v24567_strict_reachability_conversion_external_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(root / RESULT)
        or copied.get("decision_sha256") != sha256(root / DECISION)
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
        or copied.get(
            "strict_joint_claims_call_query_lead_source_or_page_level_causality"
        )
        is not False
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.67 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_base(validators=True):
        base._worker(args) if args.command == "worker" else base._supervisor(args)


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
