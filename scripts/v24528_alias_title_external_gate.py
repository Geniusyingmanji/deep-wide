#!/usr/bin/env python3
"""Fresh one-wave external gate for natural alias-title entropy credit.

The eight questions and 64 visible entities are literal/canonical disjoint
from all 364 earlier external questions and 2,912 entities.  Population
selection uses only visible names and the frozen alias grammar; it never reads
benchmark labels, answers, mappings, evaluator state, or prior web content.

Successful rows are aggregated from opaque V2.45.25 capabilities only.  GO
requires a naturally observed alias anchor, new observation, safe output
change, positive information gain, epistemic credit, and decision credit,
with no safe-change or decision-credit regression.
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
from deepwide_agent import v24524_alias_title_integration as alias_integration  # noqa: E402
from deepwide_agent import v24525_proof_carrying_alias_title as alias_proof  # noqa: E402
from deepwide_agent import v24526_total_alias_title_projection as total  # noqa: E402
from deepwide_agent import v24527_bounded_alias_title_parent as alias_parent  # noqa: E402
from scripts import v24445_serialized_narrative_external_gate as population  # noqa: E402
from scripts import v24522_conversion_diagnostic_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24528_fresh_alias_title_entropy_credit_external_gate_v1"
PROTOCOL = Path(f"results/v24528_alias_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24528_alias_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24528_alias_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24528_alias_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24528_alias_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24528_alias_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24528_alias_external_postresult_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24527_bounded_alias_title_parent_build_audit_v1_{DATE}.json")
RUNNER_MARKER = "scripts/v24528_alias_title_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_natural_alias_title_entropy_credit_external_gate"
PRIOR_QUESTION_COUNT = 364
PRIOR_ENTITY_COUNT = 2912
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS
PREVIOUS_RESULT = predecessor.RESULT
PREVIOUS_DECISION = predecessor.DECISION
PREVIOUS_POSTAUDIT = predecessor.POSTAUDIT
PREVIOUS_PROTOCOL_ID = predecessor.PROTOCOL_ID


ENTITY_GROUPS = (
    (
        "University of the West of Scotland",
        "University of the Highlands and Islands",
        "University of Central Lancashire",
        "University of the Arts London",
        "University for the Creative Arts",
        "University of Wales Trinity Saint David",
        "Arts University Bournemouth",
        "Norwich University of the Arts",
    ),
    (
        "University of Illinois Chicago",
        "University of Texas at El Paso",
        "University of Texas Rio Grande Valley",
        "University of Wisconsin Milwaukee",
        "University of Nebraska Omaha",
        "University of Minnesota Morris",
        "University of Michigan Flint",
        "Indiana University Indianapolis",
    ),
    (
        "University of Michigan Dearborn",
        "Indiana University South Bend",
        "Indiana University Kokomo",
        "Indiana University Northwest",
        "Pennsylvania State University Harrisburg",
        "Pennsylvania State University Erie",
        "Pennsylvania State University Altoona",
        "University of South Florida St. Petersburg",
    ),
    (
        "University of Arkansas at Pine Bluff",
        "University of Louisiana at Monroe",
        "University of Nebraska at Kearney",
        "University of Wisconsin-Stout",
        "University of North Texas at Dallas",
        "University of Houston-Clear Lake",
        "University of Houston-Downtown",
        "University of Houston-Victoria",
    ),
    (
        "National Taiwan University of Science and Technology",
        "National Taipei University of Technology",
        "National Yunlin University of Science and Technology",
        "National Kaohsiung University of Science and Technology",
        "National Chin-Yi University of Technology",
        "National Pingtung University of Science and Technology",
        "National Dong Hwa University",
        "National Chi Nan University",
    ),
    (
        "Metropolia University of Applied Sciences",
        "Haaga-Helia University of Applied Sciences",
        "Laurea University of Applied Sciences",
        "Turku University of Applied Sciences",
        "Centria University of Applied Sciences",
        "JAMK University of Applied Sciences",
        "Arcada University of Applied Sciences",
        "Novia University of Applied Sciences",
    ),
    (
        "Botswana International University of Science and Technology",
        "Botswana University of Agriculture and Natural Resources",
        "Namibia University of Science and Technology",
        "International University of Management Namibia",
        "Malawi University of Science and Technology",
        "Lilongwe University of Agriculture and Natural Resources",
        "Kwame Nkrumah University Zambia",
        "Levy Mwanawasa Medical University",
    ),
    (
        "University of the West Indies Five Islands Campus",
        "University of the West Indies Global Campus",
        "American University of Antigua",
        "University of Health Sciences Antigua",
        "Saint James School of Medicine",
        "Saba University School of Medicine",
        "University of Medicine and Health Sciences St. Kitts",
        "Medical University of the Americas",
    ),
)
ALIAS_TITLE_GROUPS = (
    ("UWS history", "UHI history", "UCL history", "UAL history", "UCA history", "UWTSD history", "AUB history", "NUA history"),
    ("UIC history", "UTEP history", "UTRGV history", "UWM history", "UNO history", "UMM history", "UMF history", "IUI history"),
    ("UMD history", "IUSB history", "IUK history", "IUN history", "PSUH history", "PSUE history", "PSUA history", "USFSP history"),
    ("UAPB history", "ULM history", "UNK history", "UWS history", "UNTD history", "UHCL history", "UHD history", "UHV history"),
    ("NTUST history", "NTUT history", "NYUST history", "NKUST history", "NCYUT history", "NPUST history", "NDHU history", "NCNU history"),
    ("MUAS history", "HHUAS history", "LUAS history", "TUAS history", "CUAS history", "JUAS history", "AUAS history", "NUAS history"),
    ("BIUST history", "BUANR history", "NUST history", "IUMN history", "MUST history", "LUANR history", "KNUZ history", "LMMU history"),
    ("UWIFIC history", "UWIGC history", "AUA history", "UHSA history", "SJSM history", "SUSM history", "UMHSSK history", "MUA history"),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.28 entity group drifted")
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
    "minimum_alias_capability_success_tasks": 8,
    "maximum_alias_failure_as_zero_tasks": 0,
    "minimum_alias_anchor_tasks": 1,
    "minimum_alias_observation_tasks": 1,
    "minimum_alias_added_observation_tasks": 1,
    "minimum_alias_safe_change_improvement_tasks": 1,
    "minimum_alias_positive_information_gain_tasks": 1,
    "minimum_alias_epistemic_credit_gain_tasks": 1,
    "minimum_alias_decision_credit_gain_tasks": 1,
    "minimum_alias_terminal_safe_change_tasks": 1,
    "maximum_alias_safe_change_regression_tasks": 0,
    "maximum_alias_decision_credit_regression_tasks": 0,
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
            "src/deepwide_agent/v24523_conservative_alias_title_projection.py",
            "tests/test_v24523_conservative_alias_title_projection.py",
            "src/deepwide_agent/v24524_alias_title_integration.py",
            "tests/test_v24524_alias_title_integration.py",
            "src/deepwide_agent/v24525_proof_carrying_alias_title.py",
            "tests/test_v24525_proof_carrying_alias_title.py",
            "results/v24525_proof_carrying_alias_title_build_audit_v1_20260805.json",
            "src/deepwide_agent/v24526_total_alias_title_projection.py",
            "tests/test_v24526_total_alias_title_projection.py",
            "src/deepwide_agent/v24527_bounded_alias_title_parent.py",
            "tests/test_v24527_bounded_alias_title_parent.py",
            "scripts/audit_v24527_bounded_alias_title_parent_build.py",
            "tests/test_audit_v24527_bounded_alias_title_parent_build.py",
            str(PARENT),
            str(PREVIOUS_RESULT),
            str(PREVIOUS_DECISION),
            str(PREVIOUS_POSTAUDIT),
            RUNNER_MARKER,
            "tests/test_v24528_alias_title_external_gate.py",
        )
    )
)
TEST_SUITES = (
    ("tests/test_v24480_separated_effect_validation_budget.py", 6, 120),
    ("tests/test_v24482_separated_budget_worker_integration.py", 7, 180),
    ("tests/test_v24523_conservative_alias_title_projection.py", 13, 180),
    ("tests/test_v24524_alias_title_integration.py", 8, 300),
    ("tests/test_v24525_proof_carrying_alias_title.py", 8, 480),
    ("tests/test_v24526_total_alias_title_projection.py", 6, 300),
    ("tests/test_v24527_bounded_alias_title_parent.py", 5, 360),
    ("tests/test_audit_v24527_bounded_alias_title_parent_build.py", 5, 90),
    ("tests/test_v24528_alias_title_external_gate.py", 12, 300),
)
EXPECTED_TEST_COUNT = 70


_ORIGINAL_PATCHED_CORE = predecessor._patched_core
_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start
_ORIGINAL_VALIDATE_PUBLIC_RESULT = predecessor.validate_public_result
_ORIGINAL_RUN_PROBE = predecessor.run_probe
_ORIGINAL_RUN_PROCESS_SUBCOMMAND = predecessor.run_process_subcommand
_ORIGINAL_TASK_PROJECTION = total.task_projection
_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING = copy.deepcopy(
    predecessor._record_bound_binding()
)
_COLLECTOR_GUARD = threading.Lock()
_ACTIVE_COLLECTOR: _CapabilityCollector | None = None


def _base() -> Any:
    return predecessor._base()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.28 expected object")
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


def _alias_surface_vector_valid() -> bool:
    if len(ALIAS_TITLE_GROUPS) != len(ENTITY_GROUPS):
        return False
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
            anchor = alias_projection.unique_alias_title_row(raw_title, cells)
            if anchor is None or anchor.row_key != entity:
                return False
            matched += 1
    return matched == 64


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24527_bounded_alias_title_parent_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or authorization.get("fresh_disjoint_alias_external_protocol_design")
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.28 build parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_364_prior_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_prior_external_populations_rerun": False,
        "v24522_population_rerun": False,
        "population_selection_uses_visible_names_and_frozen_alias_grammar_only": True,
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
        and result.get("passed") is True
        and decision.get("status") == "fresh_conversion_diagnostic_go"
        and decision.get("diagnostic_route")
        == "conservative_alias_title_anchoring_successor"
        and postaudit.get("audit_valid") is True
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("findings") == []
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
    )


def _record_bound_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.28 V2.45.22 closure drifted")
    return {
        **copy.deepcopy(_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING),
        "alias_title_projection_policy": alias_projection.POLICY_ID,
        "alias_title_integration_policy": alias_integration.POLICY_ID,
        "proof_carrying_alias_title_policy": alias_proof.POLICY_ID,
        "total_alias_title_projection_policy": total.POLICY_ID,
        "bounded_alias_title_parent_policy": alias_parent.POLICY_ID,
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "new_population_reuses_prior_question_or_entity": False,
        "v24522_population_rerun": False,
        "v24522_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24522_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24522_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "natural_alias_anchor_observation_safe_change_and_credit_required": True,
        "opaque_capability_aggregated_before_destruction": True,
        "expanded_public_success_row_reingestion_allowed": False,
        "historical_private_page_opened": False,
        "source_count_posterior_margin_leave_one_out_and_credit_rules_relaxed": False,
        "additional_query_search_batch_model_request_or_fetch_for_alias_stage": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


class _CapabilityCollector:
    """One-shot bridge from parent validation to opaque batch aggregation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._capabilities: dict[int, alias_proof.ValidatedProofCarryingAliasTitle] = {}
        self._rows: dict[int, dict[str, Any]] = {}
        self._consumed = False

    def project(
        self, ordinal: int, capability: alias_proof.ValidatedProofCarryingAliasTitle
    ) -> dict[str, Any]:
        row = _ORIGINAL_TASK_PROJECTION(ordinal, capability)
        with self._lock:
            if self._consumed or ordinal in self._capabilities:
                raise RuntimeError("V2.45.28 duplicate or late capability")
            self._capabilities[ordinal] = capability
            self._rows[ordinal] = copy.deepcopy(row)
        return row

    def aggregate(
        self, values: Sequence[Mapping[str, Any]], *, selected: int
    ) -> dict[str, Any]:
        if len(values) != selected:
            raise ValueError("V2.45.28 aggregate selection drifted")
        with self._lock:
            if self._consumed:
                raise RuntimeError("V2.45.28 capabilities already consumed")
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
                    raise RuntimeError("V2.45.28 success lacks captured capability")
                if _ORIGINAL_TASK_PROJECTION(ordinal, capability) != row:
                    raise RuntimeError("V2.45.28 capability/public row mismatch")
                proof_inputs.append(capability)
            else:
                if capability is not None or captured is not None:
                    raise RuntimeError("V2.45.28 failure unexpectedly has capability")
                proof_inputs.append(row)
        if capabilities or rows:
            raise RuntimeError("V2.45.28 unconsumed capability vector")
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
        raise RuntimeError("V2.45.28 capability collector is already active")
    collector = _CapabilityCollector()
    original = alias_parent.task_projection
    if _ACTIVE_COLLECTOR is not None:
        _COLLECTOR_GUARD.release()
        raise RuntimeError("V2.45.28 active collector drifted")
    _ACTIVE_COLLECTOR = collector
    alias_parent.task_projection = collector.project
    try:
        yield collector
    finally:
        alias_parent.task_projection = original
        collector.destroy()
        _ACTIVE_COLLECTOR = None
        _COLLECTOR_GUARD.release()


def aggregate_alias_projections(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    collector = _ACTIVE_COLLECTOR
    if collector is None:
        raise RuntimeError("V2.45.28 opaque capability collector is absent")
    return collector.aggregate(values, selected=selected)


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    count_totals = value.get("total_alias_stage_count_fields", {})
    number_totals = value.get("total_alias_stage_number_fields", {})
    additional = sum(
        int(count_totals.get(name, -1))
        for name in (
            "additional_model_requests",
            "additional_logical_queries",
            "additional_search_batches",
            "additional_provider_search_calls",
            "additional_fetch_calls",
        )
    )
    return (
        value.get("success_tasks") == GATES["minimum_alias_capability_success_tasks"]
        and value.get("failure_as_zero_tasks") == GATES["maximum_alias_failure_as_zero_tasks"]
        and value.get("passed_success_tasks") == 8
        and value.get("alias_anchor_tasks", 0) >= GATES["minimum_alias_anchor_tasks"]
        and value.get("alias_observation_tasks", 0) >= GATES["minimum_alias_observation_tasks"]
        and value.get("alias_added_observation_tasks", 0) >= GATES["minimum_alias_added_observation_tasks"]
        and value.get("alias_safe_change_improvement_tasks", 0) >= GATES["minimum_alias_safe_change_improvement_tasks"]
        and value.get("alias_positive_information_gain_tasks", 0) >= GATES["minimum_alias_positive_information_gain_tasks"]
        and value.get("alias_epistemic_credit_gain_tasks", 0) >= GATES["minimum_alias_epistemic_credit_gain_tasks"]
        and value.get("alias_decision_credit_gain_tasks", 0) >= GATES["minimum_alias_decision_credit_gain_tasks"]
        and value.get("alias_terminal_safe_change_tasks", 0) >= GATES["minimum_alias_terminal_safe_change_tasks"]
        and value.get("alias_safe_change_regression_tasks") == GATES["maximum_alias_safe_change_regression_tasks"]
        and value.get("alias_decision_credit_regression_tasks") == GATES["maximum_alias_decision_credit_regression_tasks"]
        and float(number_totals.get("positive_information_gain_gain_nats", 0.0)) > 0
        and float(number_totals.get("epistemic_credit_gain_nats", 0.0)) > 0
        and float(number_totals.get("decision_credit_gain_nats", 0.0)) > 0
        and float(number_totals.get("decision_credit_regression_nats", 0.0)) == 0
        and additional == GATES["maximum_alias_additional_external_effects"]
        and value.get("all_alias_success_rows_consumed_validated_capabilities") is True
        and value.get("all_alias_failure_rows_are_content_free_zero_projections") is True
        and value.get("alias_failure_rows_claim_zero_private_effects") is False
        and value.get("alias_private_task_content_emitted") is False
        and value.get("alias_privileged_evaluator_content_read") is False
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
        return "proof_capability_coverage_successor"
    if not reliability:
        return "provider_or_fetch_reliability_successor"
    if not parent_validation:
        return "parent_validation_successor"
    if not latency:
        return "latency_capacity_successor"
    if int(mechanism.get("alias_anchor_tasks", 0)) == 0:
        return "alias_source_title_coverage_successor"
    if int(mechanism.get("alias_observation_tasks", 0)) == 0:
        return "alias_relation_year_projection_successor"
    if int(mechanism.get("alias_added_observation_tasks", 0)) == 0:
        return "alias_observation_dedup_support_successor"
    if int(mechanism.get("alias_safe_change_regression_tasks", 0)) > 0:
        return "alias_safe_change_regression_successor"
    if int(mechanism.get("alias_decision_credit_regression_tasks", 0)) > 0:
        return "alias_decision_credit_regression_successor"
    if int(mechanism.get("alias_safe_change_improvement_tasks", 0)) == 0:
        return "alias_support_posterior_margin_successor"
    if int(mechanism.get("alias_positive_information_gain_tasks", 0)) == 0:
        return "alias_information_gain_successor"
    if int(mechanism.get("alias_epistemic_credit_gain_tasks", 0)) == 0:
        return "alias_epistemic_credit_successor"
    if int(mechanism.get("alias_decision_credit_gain_tasks", 0)) == 0:
        return "alias_decision_credit_successor"
    return "fresh_paired_dev64_design" if diagnostic else "alias_mechanism_successor"


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
            "TARGETED_PROOF_POLICY_ID": alias_proof.POLICY_ID,
            "TARGETED_PARENT_POLICY_ID": alias_parent.POLICY_ID,
            "_prior_questions": _prior_questions,
            "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
            "_parent": _parent,
            "_task_contract": _task_contract,
            "run_targeted_worker": alias_parent.run_alias_title_worker,
            "supervise_targeted_worker_with_separated_budget": alias_parent.supervise_alias_title_worker_with_separated_budget,
            "run_targeted_parent_with_separated_budget": alias_parent.run_alias_title_parent_with_separated_budget,
            "aggregate_projections": aggregate_alias_projections,
            "validate_targeted_aggregate": total.validate_aggregate,
            "_mechanism_passed": mechanism_passed,
            "_diagnostic_route": diagnostic_route,
        }
    )
    return value


@contextmanager
def configured_predecessor() -> Iterator[None]:
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
        "capability_collection": capability_collection,
        "aggregate_conversion_projections": aggregate_alias_projections,
    }
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


def build_protocol(
    *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.28 predecessor is not closed")
    with configured_predecessor():
        value = predecessor.build_protocol(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["scope"] = "fresh_nonbenchmark_natural_alias_title_entropy_credit_gate"
    mechanism = value["mechanism"]
    for name in (
        "conversion_observability_policy",
        "proof_carrying_conversion_observability_policy",
        "total_conversion_projection_policy",
        "bounded_conversion_parent_policy",
        "diagnostic_complete_not_quality_threshold",
    ):
        mechanism.pop(name, None)
    mechanism.update(
        {
            "alias_title_projection_policy": alias_projection.POLICY_ID,
            "alias_title_integration_policy": alias_integration.POLICY_ID,
            "proof_carrying_alias_title_policy": alias_proof.POLICY_ID,
            "total_alias_title_projection_policy": total.POLICY_ID,
            "bounded_alias_title_parent_policy": alias_parent.POLICY_ID,
            "natural_alias_anchor_observation_safe_change_information_epistemic_and_decision_credit_required": True,
            "alias_safe_change_or_decision_credit_regression_allowed": False,
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
    core["scope"] = "fresh_nonbenchmark_page_observation_conversion_diagnostic_gate"
    mechanism = core.get("mechanism", {})
    for name in (
        "alias_title_projection_policy",
        "alias_title_integration_policy",
        "proof_carrying_alias_title_policy",
        "total_alias_title_projection_policy",
        "bounded_alias_title_parent_policy",
        "natural_alias_anchor_observation_safe_change_information_epistemic_and_decision_credit_required",
        "alias_safe_change_or_decision_credit_regression_allowed",
        "mechanism_gate_is_benchmark_quality_threshold",
    ):
        mechanism.pop(name, None)
    mechanism.update(
        {
            "conversion_observability_policy": predecessor.observability.POLICY_ID,
            "proof_carrying_conversion_observability_policy": predecessor.conversion_proof.POLICY_ID,
            "total_conversion_projection_policy": predecessor.total.POLICY_ID,
            "bounded_conversion_parent_policy": predecessor.conversion_parent.POLICY_ID,
            "diagnostic_complete_not_quality_threshold": True,
            "public_success_row_reingestion_allowed": False,
            "fresh_paired_dev64_directly_authorized": False,
        }
    )
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    current = copied.get("mechanism", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_nonbenchmark_natural_alias_title_entropy_credit_gate"
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or current.get("alias_title_projection_policy") != alias_projection.POLICY_ID
        or current.get("alias_title_integration_policy") != alias_integration.POLICY_ID
        or current.get("proof_carrying_alias_title_policy") != alias_proof.POLICY_ID
        or current.get("total_alias_title_projection_policy") != total.POLICY_ID
        or current.get("bounded_alias_title_parent_policy") != alias_parent.POLICY_ID
        or current.get("natural_alias_anchor_observation_safe_change_information_epistemic_and_decision_credit_required") is not True
        or current.get("alias_safe_change_or_decision_credit_regression_allowed") is not False
        or current.get("public_success_row_reingestion_allowed") is not False
        or current.get("mechanism_gate_is_benchmark_quality_threshold") is not False
        or current.get("fresh_paired_dev64_directly_authorized") is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.28 alias protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(), _outer_validators("validate_protocol"):
        value = predecessor.build_preaudit(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_356_prior_external_questions",
        None,
    )
    checks.pop("prior_external_questions_and_entities_exactly_356_and_2848", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_364_prior_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_364_and_2912"] = True
    checks[
        "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule"
    ] = _alias_surface_vector_valid()
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
        raise RuntimeError("V2.45.28 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    core_checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_364_prior_external_questions",
        None,
    )
    core_checks.pop("prior_external_questions_and_entities_exactly_364_and_2912", None)
    core_checks.pop(
        "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule",
        None,
    )
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_356_prior_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_356_and_2848"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor(), _outer_validators("validate_protocol"):
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or checks.get(
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_364_prior_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_364_and_2912")
        is not True
        or checks.get(
            "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule"
        )
        is not True
        or checks.get("focused_tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.28 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_predecessor(), _outer_validators(
        "validate_protocol", "validate_preaudit"
    ):
        return predecessor.build_activation(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_predecessor(), _outer_validators(
        "validate_protocol", "validate_preaudit"
    ):
        return _ORIGINAL_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_predecessor(), _outer_validators(
        "validate_protocol", "validate_preaudit", "validate_activation"
    ):
        return predecessor.build_execution_start(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_predecessor(), _outer_validators(
        "validate_protocol", "validate_preaudit", "validate_activation"
    ):
        return _ORIGINAL_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_predecessor(), _outer_validators(
        "validate_protocol",
        "validate_preaudit",
        "validate_activation",
        "validate_execution_start",
    ):
        return _ORIGINAL_VALIDATE_PUBLIC_RESULT(value)


def run_probe() -> dict[str, Any]:
    with configured_predecessor(), _outer_validators(
        "validate_protocol",
        "validate_preaudit",
        "validate_activation",
        "validate_execution_start",
    ):
        return _ORIGINAL_RUN_PROBE()


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
        "role": "v24528_alias_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(_base().time.time()) if now is None else int(now),
        "status": "fresh_alias_mechanism_go" if passed else "fresh_alias_mechanism_no_go",
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_natural_alias_mechanism_measured": True,
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
    if (
        copied.get("role") != "v24528_alias_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != ("fresh_alias_mechanism_go" if passed else "fresh_alias_mechanism_no_go")
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope")
        != {
            "fresh_nonbenchmark_natural_alias_mechanism_measured": True,
            "benchmark_quality_measured": False,
            "paired_dev64_launch_authorized": False,
            "sota_supported": False,
        }
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.28 decision drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    decision = validate_decision()
    base = _base()
    lease_active = base.lease_observation(ROOT, Path("/proc")).get("active") is not False
    watchers = base.protected_watcher_snapshot()
    expected = _read(EXECUTION_START)["protected_watchers"]
    findings: list[str] = []
    if lease_active:
        findings.append("shared_api_lease_active")
    if watchers != expected:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24528_alias_external_postresult_audit",
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
        copied.get("role") != "v24528_alias_external_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status") != decision["status"]
        or copied.get("diagnostic_route") != decision["diagnostic_route"]
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != _base().protected_watcher_snapshot()
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or copied.get("private_task_or_web_content_persisted") is not False
        or copied.get("opaque_capability_references_destroyed_after_aggregation") is not True
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit") is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.28 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_predecessor(), _outer_validators(
        "validate_protocol",
        "validate_preaudit",
        "validate_activation",
        "validate_execution_start",
    ):
        _ORIGINAL_RUN_PROCESS_SUBCOMMAND(args)


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
