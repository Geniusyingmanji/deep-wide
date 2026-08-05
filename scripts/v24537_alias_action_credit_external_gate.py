#!/usr/bin/env python3
"""Fresh disjoint one-wave gate for action-level alias acquisition credit.

The 64 visible entities are literal/canonical disjoint from all 388 external
questions and 3,104 entities consumed through V2.45.32.  Runtime input is
exactly ``opaque_id`` and ``question``.  Successful public rows can be minted
only from the opaque V2.45.34 capability and are aggregated once by V2.45.35.
No benchmark mapping, label, gold answer, evaluator state, score, reward, or
historical private page is available to the forward path.
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
from deepwide_agent.v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    _baseline_cells,
)
from deepwide_agent import (  # noqa: E402
    v24523_conservative_alias_title_projection as alias_projection,
)
from deepwide_agent import v24529_alias_seeded_target_acquisition as acquisition  # noqa: E402
from deepwide_agent import v24530_alias_seeded_bounded_worker as seeded  # noqa: E402
from deepwide_agent import v24533_alias_acquisition_entropy_credit as action  # noqa: E402
from deepwide_agent import v24534_proof_carrying_alias_acquisition as proof  # noqa: E402
from deepwide_agent import v24535_total_alias_acquisition_projection as total  # noqa: E402
from scripts import v24445_serialized_narrative_external_gate as population  # noqa: E402
from scripts import v24532_alias_seeded_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24537_fresh_alias_action_credit_external_gate_v1"
PROTOCOL = Path(
    f"results/v24537_alias_action_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24537_alias_action_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24537_alias_action_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24537_alias_action_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24537_alias_action_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24537_alias_action_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24537_alias_action_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24536_alias_acquisition_credit_build_audit_v1_{DATE}.json"
)
PREVIOUS_RESULT = predecessor.RESULT
PREVIOUS_DECISION = predecessor.DECISION
PREVIOUS_POSTAUDIT = predecessor.POSTAUDIT
PREVIOUS_PROTOCOL_ID = predecessor.PROTOCOL_ID
RUNNER_MARKER = "scripts/v24537_alias_action_credit_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_disjoint_alias_action_credit_external_gate"
PRIOR_QUESTION_COUNT = 388
PRIOR_ENTITY_COUNT = 3104
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS


ENTITY_GROUPS = (
    (
        "Stevens Institute of Technology",
        "New York Institute of Technology",
        "Florida Institute of Technology",
        "Colorado School of Mines",
        "Michigan Technological University",
        "South Dakota School of Mines and Technology",
        "Embry-Riddle Aeronautical University",
        "Oregon Health and Science University",
    ),
    (
        "University of Nebraska Medical Center",
        "University of Northern British Columbia",
        "Robert Gordon University",
        "Glasgow Caledonian University",
        "Queen Margaret University",
        "Anglia Ruskin University",
        "Birmingham City University",
        "Liverpool John Moores University",
    ),
    (
        "Manchester Metropolitan University",
        "Leeds Beckett University",
        "Sheffield Hallam University",
        "Nottingham Trent University",
        "Mid Sweden University",
        "Technical University of Denmark",
        "Central Queensland University",
        "Australian Catholic University",
    ),
    (
        "Universiti Teknologi Malaysia",
        "Tunku Abdul Rahman University of Management and Technology",
        "King Mongkuts University of Technology Thonburi",
        "King Mongkuts Institute of Technology Ladkrabang",
        "Asian Institute of Technology",
        "Prince of Songkla University",
        "National University of Civil Engineering",
        "Central Philippine University",
    ),
    (
        "University of San Carlos",
        "Visayas State University",
        "University of Education Winneba",
        "Strathmore University",
        "United States International University Africa",
        "Vaal University of Technology",
        "Mangosuthu University of Technology",
        "Sefako Makgatho Health Sciences University",
    ),
    (
        "American University in Dubai",
        "Al Ain University",
        "Abu Dhabi University",
        "Gulf Medical University",
        "Mohamed bin Zayed University of Artificial Intelligence",
        "Future University in Egypt",
        "Nile University Egypt",
        "British University in Egypt",
    ),
    (
        "Sudan University of Science and Technology",
        "Addis Ababa Science and Technology University",
        "Adama Science and Technology University",
        "Bahir Dar University",
        "Information and Communications University Zambia",
        "National University of Science and Technology Zimbabwe",
        "Harare Institute of Technology",
        "Bindura University of Science Education",
    ),
    (
        "Seoul National University of Science and Technology",
        "Korea University of Technology and Education",
        "Kumoh National Institute of Technology",
        "Korea Maritime and Ocean University",
        "Indian Institute of Technology Indore",
        "Indian Institute of Technology Ropar",
        "Indian Institute of Technology Patna",
        "Indian Institute of Technology Mandi",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.37 entity group drifted")
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
        f"{acquisition.primary_alias_surface(entity)} history"
        for entity in group
    )
    for group in ENTITY_GROUPS
)
GATES = {
    "minimum_worker_success_tasks": 8,
    "maximum_worker_hard_timeout_tasks": 0,
    "maximum_worker_nonzero_tasks": 0,
    "minimum_complete_validation_returned_tasks": 8,
    "minimum_action_capability_success_tasks": 8,
    "maximum_action_failure_as_zero_tasks": 0,
    "minimum_acquisition_plan_tasks": 1,
    "minimum_acquisition_activity_tasks": 1,
    "minimum_selected_alias_title_hit_tasks": 1,
    "minimum_acquisition_new_observation_tasks": 1,
    "minimum_positive_action_information_gain_tasks": 1,
    "minimum_positive_action_epistemic_credit_tasks": 1,
    "minimum_positive_action_decision_credit_tasks": 1,
    "minimum_safe_change_improvement_tasks": 1,
    "maximum_safe_change_regression_tasks": 0,
    "maximum_decision_credit_regression_tasks": 0,
    "maximum_alias_additional_external_effects": 0,
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
            "src/deepwide_agent/v24533_alias_acquisition_entropy_credit.py",
            "tests/test_v24533_alias_acquisition_entropy_credit.py",
            "src/deepwide_agent/v24534_proof_carrying_alias_acquisition.py",
            "tests/test_v24534_proof_carrying_alias_acquisition.py",
            "src/deepwide_agent/v24535_total_alias_acquisition_projection.py",
            "tests/test_v24535_total_alias_acquisition_projection.py",
            "scripts/audit_v24536_alias_acquisition_credit_build.py",
            "tests/test_audit_v24536_alias_acquisition_credit_build.py",
            str(PARENT),
            str(PREVIOUS_RESULT),
            str(PREVIOUS_DECISION),
            str(PREVIOUS_POSTAUDIT),
            RUNNER_MARKER,
            "tests/test_v24537_alias_action_credit_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *predecessor.TEST_SUITES,
    ("tests/test_v24533_alias_acquisition_entropy_credit.py", 5, 180),
    ("tests/test_v24534_proof_carrying_alias_acquisition.py", 8, 360),
    ("tests/test_v24535_total_alias_acquisition_projection.py", 7, 180),
    ("tests/test_audit_v24536_alias_acquisition_credit_build.py", 7, 90),
    ("tests/test_v24537_alias_action_credit_external_gate.py", 16, 360),
)
EXPECTED_TEST_COUNT = predecessor.EXPECTED_TEST_COUNT + 43


_ORIGINAL_BUILD_PROTOCOL = predecessor.build_protocol
_ORIGINAL_PATCHED_CORE = predecessor._patched_core
_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_BUILD_PREAUDIT = predecessor.build_preaudit
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_BUILD_ACTIVATION = predecessor.build_activation
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_BUILD_EXECUTION_START = predecessor.build_execution_start
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start
_ORIGINAL_TASK_PROJECTION = total.task_projection
_REQUIRED_ACTION_AGGREGATE_KEYS = frozenset(
    {
        "acquisition_plan_tasks",
        "total_acquisition_action_count_fields",
        "total_acquisition_action_number_fields",
    }
)
_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING = copy.deepcopy(
    predecessor._record_bound_binding()
)
_COLLECTOR_GUARD = threading.Lock()
_ACTIVE_COLLECTOR: _CapabilityCollector | None = None


def _base() -> Any:
    return predecessor._base()


_BASE_VALIDATE_PUBLIC_RESULT = _base().validate_public_result


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.37 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _previous_closed() -> bool:
    result = _read(PREVIOUS_RESULT)
    decision = _read(PREVIOUS_DECISION)
    postaudit = _read(PREVIOUS_POSTAUDIT)
    return (
        result.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and decision.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and postaudit.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and result.get("selected") == 8
        and result.get("passed") is False
        and result.get("mechanism_passed") is False
        and decision.get("status") == "fresh_alias_seeded_mechanism_no_go"
        and decision.get("authorization", {}).get("new_exact220") is False
        and postaudit.get("audit_valid") is True
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("findings") == []
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
    )


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    closed = value.get("v24532_closed_no_go", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24536_alias_acquisition_credit_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 57
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or closed.get("valid") is not True
        or closed.get("population_rerun_authorized") is not False
        or authorization.get("fresh_disjoint_action_credit_external_protocol_design")
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.37 build parent drifted")
    return value


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
    matched = 0
    for entities, titles in zip(ENTITY_GROUPS, ALIAS_TITLE_GROUPS, strict=True):
        if len(entities) != 8 or len(titles) != 8:
            return False
        if len({item.casefold() for item in titles}) != 8:
            return False
        baseline = (
            "```markdown\n| University | Founding year |\n| --- | --- |\n"
            + "\n".join(f"| {entity} | Unknown |" for entity in entities)
            + "\n```"
        )
        cells = _baseline_cells(baseline)
        for entity, raw_title in zip(entities, titles, strict=True):
            surface = acquisition.primary_alias_surface(entity)
            anchor = alias_projection.unique_alias_title_row(raw_title, cells)
            if surface is None or anchor is None or anchor.row_key != entity:
                return False
            matched += 1
    return matched == 64


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_388_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "v24531_and_v24532_populations_counted_as_consumed": True,
        "v24531_or_v24532_population_resume_retry_or_rerun": False,
        "population_selection_uses_visible_names_and_frozen_alias_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _record_bound_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.37 V2.45.32 closure drifted")
    return {
        **copy.deepcopy(_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING),
        "alias_acquisition_action_credit_policy": action.POLICY_ID,
        "proof_carrying_alias_acquisition_policy": proof.POLICY_ID,
        "total_alias_acquisition_projection_policy": total.POLICY_ID,
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "new_population_reuses_prior_question_or_entity": False,
        "v24531_or_v24532_population_resume_retry_or_rerun": False,
        "v24532_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24532_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24532_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "action_credit_requires_plan_query_selection_new_observation_and_positive_posterior_delta": True,
        "action_decision_credit_requires_safe_output_change": True,
        "same_run_action_credit_used_for_routing_training_or_policy_update": False,
        "frozen_v24525_task_surface_preserved": True,
        "opaque_v24534_capability_aggregated_before_destruction": True,
        "public_success_row_reingestion_allowed": False,
        "historical_private_page_opened": False,
        "source_count_posterior_margin_leave_one_out_and_credit_rules_relaxed": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


class _CapabilityCollector:
    """One-shot bridge from action proof validation to public aggregation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._capabilities: dict[
            int, proof.ValidatedProofCarryingAliasAcquisition
        ] = {}
        self._rows: dict[int, dict[str, Any]] = {}
        self._consumed = False

    def project(
        self,
        ordinal: int,
        capability: proof.ValidatedProofCarryingAliasAcquisition,
    ) -> dict[str, Any]:
        row = _ORIGINAL_TASK_PROJECTION(ordinal, capability)
        with self._lock:
            if self._consumed or ordinal in self._capabilities:
                raise RuntimeError("V2.45.37 duplicate or late capability")
            self._capabilities[ordinal] = capability
            self._rows[ordinal] = copy.deepcopy(row)
        return row

    def aggregate(
        self, values: Sequence[Mapping[str, Any]], *, selected: int
    ) -> dict[str, Any]:
        if len(values) != selected:
            raise ValueError("V2.45.37 aggregate selection drifted")
        with self._lock:
            if self._consumed:
                raise RuntimeError("V2.45.37 capabilities already consumed")
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
                    raise RuntimeError("V2.45.37 success lacks captured capability")
                if _ORIGINAL_TASK_PROJECTION(ordinal, capability) != row:
                    raise RuntimeError("V2.45.37 capability/public row mismatch")
                proof_inputs.append(capability)
            else:
                if capability is not None or captured is not None:
                    raise RuntimeError("V2.45.37 failure unexpectedly has capability")
                proof_inputs.append(row)
        if capabilities or rows:
            raise RuntimeError("V2.45.37 unconsumed capability vector")
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
        raise RuntimeError("V2.45.37 capability collector is already active")
    collector = _CapabilityCollector()
    original = total.task_projection
    if _ACTIVE_COLLECTOR is not None:
        _COLLECTOR_GUARD.release()
        raise RuntimeError("V2.45.37 active collector drifted")
    _ACTIVE_COLLECTOR = collector
    total.task_projection = collector.project
    try:
        yield collector
    finally:
        total.task_projection = original
        collector.destroy()
        _ACTIVE_COLLECTOR = None
        _COLLECTOR_GUARD.release()


def aggregate_action_projections(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    collector = _ACTIVE_COLLECTOR
    if collector is None:
        raise RuntimeError("V2.45.37 opaque capability collector is absent")
    return collector.aggregate(values, selected=selected)


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    counts = value.get("total_acquisition_action_count_fields", {})
    numbers = value.get("total_acquisition_action_number_fields", {})
    alias_counts = value.get("total_alias_stage_count_fields", {})
    additional = sum(
        int(alias_counts.get(name, -1))
        for name in (
            "additional_model_requests",
            "additional_logical_queries",
            "additional_search_batches",
            "additional_provider_search_calls",
            "additional_fetch_calls",
        )
    )
    return (
        value.get("success_tasks") == GATES["minimum_action_capability_success_tasks"]
        and value.get("failure_as_zero_tasks")
        == GATES["maximum_action_failure_as_zero_tasks"]
        and value.get("passed_success_tasks") == 8
        and value.get("acquisition_plan_tasks", 0)
        >= GATES["minimum_acquisition_plan_tasks"]
        and value.get("acquisition_activity_tasks", 0)
        >= GATES["minimum_acquisition_activity_tasks"]
        and value.get("acquisition_selected_alias_title_hit_tasks", 0)
        >= GATES["minimum_selected_alias_title_hit_tasks"]
        and value.get("acquisition_new_observation_tasks", 0)
        >= GATES["minimum_acquisition_new_observation_tasks"]
        and value.get("acquisition_positive_information_gain_tasks", 0)
        >= GATES["minimum_positive_action_information_gain_tasks"]
        and value.get("acquisition_positive_epistemic_credit_tasks", 0)
        >= GATES["minimum_positive_action_epistemic_credit_tasks"]
        and value.get("acquisition_positive_decision_credit_tasks", 0)
        >= GATES["minimum_positive_action_decision_credit_tasks"]
        and value.get("acquisition_safe_change_improvement_tasks", 0)
        >= GATES["minimum_safe_change_improvement_tasks"]
        and value.get("acquisition_safe_change_regression_tasks")
        == GATES["maximum_safe_change_regression_tasks"]
        and value.get("acquisition_decision_credit_regression_tasks")
        == GATES["maximum_decision_credit_regression_tasks"]
        and float(numbers.get("action_information_credit_nats", 0.0)) > 0
        and float(numbers.get("action_epistemic_credit_nats", 0.0)) > 0
        and float(numbers.get("action_decision_credit_nats", 0.0)) > 0
        and float(numbers.get("action_decision_credit_regression_nats", 0.0)) == 0
        and int(counts.get("targeted_new_observation_count", 0)) > 0
        and additional == GATES["maximum_alias_additional_external_effects"]
        and value.get(
            "all_acquisition_success_rows_consumed_validated_capabilities"
        )
        is True
        and value.get(
            "all_acquisition_failure_rows_are_content_free_zero_projections"
        )
        is True
        and value.get("acquisition_failure_rows_claim_zero_private_effects")
        is False
        and value.get("acquisition_private_task_content_emitted") is False
        and value.get("acquisition_privileged_evaluator_content_read") is False
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
    if int(supervision.get("worker_hard_timeout_tasks", 0)) > 0:
        return "bounded_worker_stage_successor"
    if int(supervision.get("worker_nonzero_tasks", 0)) > 0:
        return "worker_exception_successor"
    if int(mechanism.get("success_tasks", 0)) < 8:
        return "action_proof_capability_coverage_successor"
    if not reliability:
        return "provider_or_fetch_reliability_successor"
    if not parent_validation:
        return "parent_validation_successor"
    if not latency:
        return "latency_capacity_successor"
    if int(mechanism.get("acquisition_plan_tasks", 0)) == 0:
        return "target_plan_coverage_successor"
    if int(mechanism.get("acquisition_activity_tasks", 0)) == 0:
        return "alias_acquisition_activity_successor"
    if int(mechanism.get("acquisition_selected_alias_title_hit_tasks", 0)) == 0:
        return "alias_title_selection_successor"
    if int(mechanism.get("acquisition_new_observation_tasks", 0)) == 0:
        return "targeted_observation_conversion_successor"
    if int(mechanism.get("acquisition_safe_change_regression_tasks", 0)) > 0:
        return "action_safe_change_regression_successor"
    if int(mechanism.get("acquisition_decision_credit_regression_tasks", 0)) > 0:
        return "action_decision_credit_regression_successor"
    if int(mechanism.get("acquisition_positive_information_gain_tasks", 0)) == 0:
        return "action_information_gain_successor"
    if int(mechanism.get("acquisition_positive_epistemic_credit_tasks", 0)) == 0:
        return "action_epistemic_credit_successor"
    if int(mechanism.get("acquisition_safe_change_improvement_tasks", 0)) == 0:
        return "action_safe_change_successor"
    if int(mechanism.get("acquisition_positive_decision_credit_tasks", 0)) == 0:
        return "action_decision_credit_successor"
    return "fresh_paired_dev64_design" if diagnostic else "action_credit_successor"


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
            "TARGETED_PROOF_POLICY_ID": proof.POLICY_ID,
            "TARGETED_PARENT_POLICY_ID": proof.POLICY_ID,
            "_prior_questions": _prior_questions,
            "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
            "_parent": _parent,
            "_task_contract": _task_contract,
            "run_targeted_worker": proof.run_worker,
            "supervise_targeted_worker_with_separated_budget": proof.supervise_worker_with_separated_budget,
            "run_targeted_parent_with_separated_budget": proof.run_parent_with_separated_budget,
            "aggregate_projections": aggregate_action_projections,
            "validate_targeted_aggregate": total.validate_aggregate,
            "_mechanism_passed": mechanism_passed,
            "_diagnostic_route": diagnostic_route,
        }
    )
    return value


@contextmanager
def configured_base() -> Iterator[None]:
    """Install the action runtime directly on the V2.44.92 execution base.

    Successor contexts are intentionally nested for control-plane validation,
    but the actual batch aggregation happens in ``base.run_probe``.  Binding
    only an outer successor's ``_patched_core`` is therefore insufficient: a
    historical collector can otherwise restore the V2.45.26 alias aggregate
    before the bottom-level aggregation call.
    """

    base = _base()
    patches = _patched_core()
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


@contextmanager
def configured_predecessor(*, runtime_bindings: bool = True) -> Iterator[None]:
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
        "ENTITY_GROUPS": ENTITY_GROUPS,
        "ALIAS_TITLE_GROUPS": ALIAS_TITLE_GROUPS,
        "QUESTIONS": QUESTIONS,
        "GATES": GATES,
        "SOURCE_FILES": SOURCE_FILES,
        "TEST_SUITES": TEST_SUITES,
        "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
        "_prior_questions": _prior_questions,
        "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
        "_alias_surface_vector_valid": _alias_surface_vector_valid,
        "_parent": _parent,
        "_task_contract": _task_contract,
        "_quarantine_valid": _previous_closed,
        "_record_bound_binding": _record_bound_binding,
        "mechanism_passed": mechanism_passed,
        "diagnostic_route": diagnostic_route,
    }
    if runtime_bindings:
        patches["_patched_core"] = _patched_core
    else:
        # Protocol validation may run inside the worker/supervisor runtime
        # context.  Restore the frozen V2.45.32 control-plane core locally so
        # the predecessor validators do not observe V2.45.37 execution binds.
        patches["_patched_core"] = _ORIGINAL_PATCHED_CORE
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
def _outer_validators(*names: str) -> Iterator[None]:
    values = {
        "validate_protocol": validate_protocol,
        "validate_preaudit": validate_preaudit,
        "validate_activation": validate_activation,
        "validate_execution_start": validate_execution_start,
    }
    originals = {name: getattr(predecessor, name) for name in names}
    try:
        for name in names:
            setattr(predecessor, name, values[name])
        yield
    finally:
        for name, value in originals.items():
            setattr(predecessor, name, value)


@contextmanager
def _base_validators() -> Iterator[None]:
    """Route the lowest execution base to the action protocol validators."""

    base = _base()
    patches = {
        "validate_protocol": lambda _root=ROOT, value=None: validate_protocol(
            value=value
        ),
        "validate_preaudit": lambda _root=ROOT: validate_preaudit(),
        "validate_activation": lambda _root=ROOT: validate_activation(),
        "validate_execution_start": lambda _root=ROOT: validate_execution_start(),
        "validate_public_result": validate_public_result,
    }
    originals = {name: getattr(base, name) for name in patches}
    try:
        for name, value in patches.items():
            setattr(base, name, value)
        yield
    finally:
        for name, value in originals.items():
            setattr(base, name, value)


def build_protocol(
    *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.37 predecessor is not closed")
    _parent(ROOT)
    with configured_predecessor(runtime_bindings=False):
        value = _ORIGINAL_BUILD_PROTOCOL(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_disjoint_alias_action_credit_gate"
    value["mechanism"].update(
        {
            "targeted_proof_policy": proof.POLICY_ID,
            "targeted_parent_policy": proof.POLICY_ID,
            "alias_acquisition_action_credit_policy": action.POLICY_ID,
            "proof_carrying_alias_acquisition_policy": proof.POLICY_ID,
            "total_alias_acquisition_projection_policy": total.POLICY_ID,
            "action_credit_requires_target_plan_query_selection_new_observation_and_positive_posterior_delta": True,
            "action_decision_credit_requires_safe_output_change": True,
            "selected_alias_title_hit_required_for_gate": True,
            "same_run_action_credit_used_for_routing_training_or_policy_update": False,
            "frozen_v24525_task_surface_preserved": True,
            "public_success_row_reingestion_allowed": False,
            "mechanism_gate_is_benchmark_quality_threshold": False,
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
    core["scope"] = "fresh_disjoint_post_recursion_alias_seeded_entropy_credit_gate"
    mechanism = core.get("mechanism", {})
    mechanism["targeted_proof_policy"] = predecessor.alias_proof.POLICY_ID
    mechanism["targeted_parent_policy"] = seeded.POLICY_ID
    for name in (
        "alias_acquisition_action_credit_policy",
        "proof_carrying_alias_acquisition_policy",
        "total_alias_acquisition_projection_policy",
        "action_credit_requires_target_plan_query_selection_new_observation_and_positive_posterior_delta",
        "action_decision_credit_requires_safe_output_change",
        "selected_alias_title_hit_required_for_gate",
        "same_run_action_credit_used_for_routing_training_or_policy_update",
        "frozen_v24525_task_surface_preserved",
    ):
        mechanism.pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor(runtime_bindings=False):
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    current = copied.get("mechanism", {})
    budget = copied.get("budget", {})
    provider = copied.get("provider", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope") != "fresh_disjoint_alias_action_credit_gate"
        or copied.get("parent")
        != {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or current.get("targeted_proof_policy") != proof.POLICY_ID
        or current.get("targeted_parent_policy") != proof.POLICY_ID
        or current.get("alias_acquisition_action_credit_policy") != action.POLICY_ID
        or current.get("proof_carrying_alias_acquisition_policy") != proof.POLICY_ID
        or current.get("total_alias_acquisition_projection_policy") != total.POLICY_ID
        or current.get(
            "action_credit_requires_target_plan_query_selection_new_observation_and_positive_posterior_delta"
        )
        is not True
        or current.get("action_decision_credit_requires_safe_output_change")
        is not True
        or current.get("selected_alias_title_hit_required_for_gate") is not True
        or current.get(
            "same_run_action_credit_used_for_routing_training_or_policy_update"
        )
        is not False
        or current.get("frozen_v24525_task_surface_preserved") is not True
        or current.get("public_success_row_reingestion_allowed") is not False
        or current.get("mechanism_gate_is_benchmark_quality_threshold") is not False
        or current.get("fresh_paired_dev64_directly_authorized") is not False
        or provider.get("executor_count") != 8
        or provider.get("model_slot_cap") != 2
        or budget.get("effect_deadline_seconds") != 150.0
        or budget.get("worker_timeout_seconds") != 220.0
        or budget.get("parent_timeout_seconds") != 245.0
        or budget.get("maximum_batch_wall_seconds") != 255.0
        or budget.get("maximum_targeted_search_batches_per_task") != 1
        or budget.get("maximum_targeted_logical_queries_per_task") != 2
        or budget.get("maximum_targeted_fetches_per_task") != 3
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.37 protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(runtime_bindings=False), _outer_validators(
        "validate_protocol"
    ):
        value = _ORIGINAL_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_380_consumed_external_questions",
        None,
    )
    checks.pop("prior_external_questions_and_entities_exactly_380_and_3040", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_388_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_388_and_3104"] = True
    checks["v24531_and_v24532_population_resume_retry_or_rerun"] = False
    checks["action_capability_worker_supervisor_cli_binding_validated"] = True
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
        raise RuntimeError("V2.45.37 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_388_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_388_and_3104",
        "v24531_and_v24532_population_resume_retry_or_rerun",
        "action_capability_worker_supervisor_cli_binding_validated",
    ):
        core_checks.pop(name, None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_380_consumed_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_380_and_3040"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor(runtime_bindings=False), _outer_validators(
        "validate_protocol"
    ):
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or checks.get(
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_388_consumed_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_388_and_3104")
        is not True
        or checks.get("v24531_and_v24532_population_resume_retry_or_rerun")
        is not False
        or checks.get("action_capability_worker_supervisor_cli_binding_validated")
        is not True
        or checks.get("focused_tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.37 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_predecessor(runtime_bindings=False), _outer_validators(
        "validate_protocol", "validate_preaudit"
    ):
        return _ORIGINAL_BUILD_ACTIVATION(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_predecessor(runtime_bindings=False), _outer_validators(
        "validate_protocol", "validate_preaudit"
    ):
        return _ORIGINAL_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_predecessor(runtime_bindings=False), _outer_validators(
        "validate_protocol", "validate_preaudit", "validate_activation"
    ):
        return _ORIGINAL_BUILD_EXECUTION_START(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_predecessor(runtime_bindings=False), _outer_validators(
        "validate_protocol", "validate_preaudit", "validate_activation"
    ):
        return _ORIGINAL_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    mechanism = value.get("mechanism_aggregate")
    if (
        not isinstance(mechanism, Mapping)
        or not _REQUIRED_ACTION_AGGREGATE_KEYS.issubset(mechanism)
    ):
        raise RuntimeError("V2.45.37 action aggregate schema is absent")
    total.validate_aggregate(mechanism)
    with configured_base():
        return _BASE_VALIDATE_PUBLIC_RESULT(value)


def run_probe() -> dict[str, Any]:
    with capability_collection(), configured_base(), _base_validators():
        return _base().run_probe()


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
        "role": "v24537_alias_action_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(_base().time.time()) if now is None else int(now),
        "status": (
            "fresh_alias_action_credit_go"
            if passed
            else "fresh_alias_action_credit_no_go"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_action_level_entropy_credit_measured": True,
            "benchmark_quality_measured": False,
            "paired_dev64_launch_authorized": False,
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
    route = diagnostic_route(
        result["mechanism_aggregate"],
        result["supervision_aggregate"],
        diagnostic=result["mechanism_passed"],
        reliability=result["reliability_passed"],
        parent_validation=result["parent_validation_passed"],
        latency=result["latency_passed"],
    )
    expected_status = (
        "fresh_alias_action_credit_go"
        if passed
        else "fresh_alias_action_credit_no_go"
    )
    if (
        copied.get("role") != "v24537_alias_action_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope")
        != {
            "fresh_nonbenchmark_action_level_entropy_credit_measured": True,
            "benchmark_quality_measured": False,
            "paired_dev64_launch_authorized": False,
            "sota_supported": False,
        }
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.37 decision drifted")
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
        "role": "v24537_alias_action_external_postresult_audit",
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
        copied.get("role") != "v24537_alias_action_external_postresult_audit"
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
        raise RuntimeError("V2.45.37 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    base = _base()
    with configured_base(), _base_validators():
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
