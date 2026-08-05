#!/usr/bin/env python3
"""Fresh strict-reachability successor after the V2.45.67 quarantine.

V2.45.67's population is conservatively consumed.  This successor uses a
fresh 8-task/64-entity population after the 444-question/3,552-entity history
and owns a re-entrant lock around the complete nested predecessor protocol
validation context.  Task execution remains parallel after validation.
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
from scripts import v24567_strict_reachability_conversion_external_gate as predecessor  # noqa: E402
from scripts import v24569_serialized_protocol_validator_repair as repair  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24571_fresh_serialized_strict_reachability_external_gate_v1"
PROTOCOL = Path(
    f"results/v24571_serialized_strict_reachability_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24571_serialized_strict_reachability_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24571_serialized_strict_reachability_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24571_serialized_strict_reachability_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24571_serialized_strict_reachability_external_result_v1_{DATE}.json"
)
DECISION = Path(
    f"results/v24571_serialized_strict_reachability_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24571_serialized_strict_reachability_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24570_serialized_protocol_validator_build_audit_v1_{DATE}.json"
)
QUARANTINE = Path(
    f"results/DO_NOT_USE_invalid_v24567_concurrent_protocol_context_{DATE}/invalid_run_audit.json"
)
RUNNER_MARKER = "scripts/v24571_serialized_strict_reachability_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_serialized_strict_reachability_external_gate"
PRIOR_QUESTION_COUNT = 444
PRIOR_ENTITY_COUNT = 3552
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS

population = predecessor.population
acquisition = predecessor.acquisition
alias_projection = predecessor.alias_projection
surface = predecessor.surface
planner = predecessor.planner
proof = predecessor.proof
total = predecessor.total
bounded = predecessor.bounded
base = predecessor.base


ENTITY_GROUPS = (
    (
        "Rochester Christian University Michigan",
        "Concordia University Ann Arbor",
        "College for Creative Studies Detroit",
        "Kuyper College Michigan",
        "Ashland University Ohio",
        "Cedarville University Ohio",
        "Xavier University Ohio",
        "University of Dayton Ohio",
    ),
    (
        "Mount Vernon Nazarene University Ohio",
        "Ohio Dominican University",
        "Lourdes University Ohio",
        "Arcadia University Pennsylvania",
        "Delaware Valley University Pennsylvania",
        "Duquesne University Pennsylvania",
        "Elizabethtown College Pennsylvania",
        "Gannon University Pennsylvania",
    ),
    (
        "Grove City College Pennsylvania",
        "Juniata College Pennsylvania",
        "La Roche University Pennsylvania",
        "Lebanon Valley College Pennsylvania",
        "Lycoming College Pennsylvania",
        "Muhlenberg College Pennsylvania",
        "Neumann University Pennsylvania",
        "Point Park University Pennsylvania",
    ),
    (
        "Saint Francis University Pennsylvania",
        "Saint Vincent College Pennsylvania",
        "Seton Hill University Pennsylvania",
        "Susquehanna University Pennsylvania",
        "Thiel College Pennsylvania",
        "University of Scranton Pennsylvania",
        "Westminster College Pennsylvania",
        "York College Pennsylvania",
    ),
    (
        "Bard College New York",
        "Elmira College New York",
        "Houghton University New York",
        "Iona University New York",
        "Ithaca College New York",
        "Keuka College New York",
        "Le Moyne College New York",
        "Pace University New York",
    ),
    (
        "Roberts Wesleyan University New York",
        "Russell Sage College New York",
        "Saint Bonaventure University New York",
        "Saint John Fisher University New York",
        "St Lawrence University New York",
        "Utica University New York",
        "Wagner College New York",
        "Assumption University Massachusetts",
    ),
    (
        "Babson College Massachusetts",
        "Bentley University Massachusetts",
        "Clark University Massachusetts",
        "Curry College Massachusetts",
        "Dean College Massachusetts",
        "Gordon College Massachusetts",
        "Lasell University Massachusetts",
        "Merrimack College Massachusetts",
    ),
    (
        "Nichols College Massachusetts",
        "Regis College Massachusetts",
        "Wentworth Institute of Technology Massachusetts",
        "Western New England University Massachusetts",
        "Wheaton College Massachusetts",
        "Bryant University Rhode Island",
        "Johnson and Wales University Rhode Island",
        "Providence College Rhode Island",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.71 entity group drifted")
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
GATES = copy.deepcopy(predecessor.GATES)
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *predecessor.SOURCE_FILES,
            "scripts/audit_v24568_invalid_concurrent_protocol_context.py",
            "tests/test_audit_v24568_invalid_concurrent_protocol_context.py",
            str(QUARANTINE),
            "scripts/v24569_serialized_protocol_validator_repair.py",
            "tests/test_v24569_serialized_protocol_validator_repair.py",
            "scripts/audit_v24570_serialized_protocol_validator_build.py",
            "tests/test_audit_v24570_serialized_protocol_validator_build.py",
            str(PARENT),
            RUNNER_MARKER,
            "tests/test_v24571_serialized_strict_reachability_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *predecessor.TEST_SUITES,
    ("tests/test_audit_v24568_invalid_concurrent_protocol_context.py", 5, 120),
    ("tests/test_v24569_serialized_protocol_validator_repair.py", 5, 180),
    ("tests/test_audit_v24570_serialized_protocol_validator_build.py", 7, 240),
    ("tests/test_v24571_serialized_strict_reachability_external_gate.py", 13, 600),
)
EXPECTED_TEST_COUNT = predecessor.EXPECTED_TEST_COUNT + 30


_ORIGINAL_BUILD_PROTOCOL = predecessor.build_protocol
_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_BUILD_PREAUDIT = predecessor.build_preaudit
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_BUILD_ACTIVATION = predecessor.build_activation
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_BUILD_EXECUTION_START = predecessor.build_execution_start
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start
_ORIGINAL_VALIDATE_PUBLIC_RESULT = predecessor.validate_public_result
_ORIGINAL_RUN_PROBE = predecessor.run_probe
_ORIGINAL_RUN_PROCESS_SUBCOMMAND = predecessor.run_process_subcommand
_FROZEN_PREDECESSOR_PROTOCOL_ID = predecessor.PROTOCOL_ID
_PROTOCOL_VALIDATOR_LOCK = threading.RLock()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.71 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _quarantine_valid() -> bool:
    value = _read(QUARANTINE)
    incident = value.get("incident", {})
    population_state = value.get("population", {})
    authorization = value.get("authorization", {})
    return (
        value.get("role")
        == "v24568_invalid_concurrent_protocol_context_run_audit"
        and value.get("protocol_id") == _FROZEN_PREDECESSOR_PROTOCOL_ID
        and value.get("status") == "invalid_quarantined_no_public_result"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and incident.get(
            "threaded_run_one_protocol_validators_shared_mutable_base_context"
        )
        is True
        and incident.get("external_effect_counts_recoverable") is False
        and incident.get("public_result_published") is False
        and population_state.get(
            "same_population_resume_retry_rerun_or_evaluation_allowed"
        )
        is False
        and population_state.get("next_prior_question_count")
        == PRIOR_QUESTION_COUNT
        and population_state.get("next_prior_entity_count") == PRIOR_ENTITY_COUNT
        and authorization.get(
            "same_population_resume_retry_rerun_or_evaluation"
        )
        is False
        and authorization.get("ordinary_v24567_result_decision_or_postaudit")
        is False
        and authorization.get("fresh_successor_activation_or_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    quarantine_state = value.get("v24568_quarantine", {})
    repair_state = value.get("repair", {})
    stress = repair_state.get("stress", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24570_serialized_protocol_validator_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 29
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or quarantine_state.get("valid") is not True
        or quarantine_state.get("next_prior_question_count")
        != PRIOR_QUESTION_COUNT
        or quarantine_state.get("next_prior_entity_count") != PRIOR_ENTITY_COUNT
        or quarantine_state.get(
            "same_population_resume_retry_rerun_or_evaluation_authorized"
        )
        is not False
        or repair_state.get("policy_id") != repair.POLICY_ID
        or repair_state.get("reentrant_protocol_validator_lock_present") is not True
        or stress.get("passed") is not True
        or stress.get("validations") != 200
        or authorization.get(
            "fresh_disjoint_strict_reachability_conversion_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.71 build parent drifted")
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
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_444_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_surfaces_globally_unique_and_query_blind": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_populations_through_invalid_v24567_counted_as_consumed": True,
        "prior_population_resume_retry_rerun_or_evaluation": False,
        "population_selection_uses_visible_names_and_frozen_alias_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_serialized_strict_reachability_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_serialized_strict_reachability_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def _successor_binding() -> dict[str, Any]:
    if not _quarantine_valid():
        raise RuntimeError("V2.45.71 V2.45.67 quarantine drifted")
    return {
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "v24567_quarantine_path": str(QUARANTINE),
        "v24567_quarantine_sha256": sha256(ROOT / QUARANTINE),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "same_or_prior_population_resume_retry_rerun_or_evaluation": False,
        "new_population_reuses_prior_question_or_entity": False,
        "decision_reachability_planner_policy": planner.POLICY_ID,
        "proof_carrying_decision_reachability_policy": proof.POLICY_ID,
        "strict_reachability_conversion_projection_policy": total.POLICY_ID,
        "bounded_strict_reachability_conversion_parent_policy": bounded.POLICY_ID,
        "serialized_protocol_validator_repair_policy": repair.POLICY_ID,
        "complete_nested_protocol_validation_critical_section_serialized": True,
        "task_execution_remains_parallel_after_protocol_validation": True,
        "source_posterior_margin_leave_one_out_safe_change_or_decision_credit_rules_relaxed": False,
        "strict_joint_claims_call_query_lead_source_or_page_level_causality": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


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
        "_previous_closed": _quarantine_valid,
        "_task_contract": _task_contract,
        "_protocol_authorization": _protocol_authorization,
        "_activation_authorization": _activation_authorization,
        "_successor_binding": _successor_binding,
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
        "validate_public_result": validate_public_result,
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
    if not _quarantine_valid():
        raise RuntimeError("V2.45.71 V2.45.67 quarantine is not closed")
    _parent(ROOT)
    with configured_predecessor():
        value = _ORIGINAL_BUILD_PROTOCOL(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_post_quarantine_serialized_strict_reachability_gate"
    value["mechanism"].update(
        {
            "v24567_invalid_population_resume_retry_rerun_or_evaluation": False,
            "v24570_serialized_validator_build_audit_bound": True,
            "serialized_protocol_validator_repair_policy": repair.POLICY_ID,
            "complete_nested_protocol_validation_critical_section_serialized": True,
            "task_execution_remains_parallel_after_protocol_validation": True,
        }
    )
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value)


def _validate_protocol_unlocked(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_nonbenchmark_strict_reachability_conversion_gate"
    for name in (
        "v24567_invalid_population_resume_retry_rerun_or_evaluation",
        "v24570_serialized_validator_build_audit_bound",
        "serialized_protocol_validator_repair_policy",
        "complete_nested_protocol_validation_critical_section_serialized",
        "task_execution_remains_parallel_after_protocol_validation",
    ):
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    mechanism = copied.get("mechanism", {})
    budget = copied.get("budget", {})
    provider = copied.get("provider", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_post_quarantine_serialized_strict_reachability_gate"
        or copied.get("parent")
        != {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}
        or copied.get("successor_binding") != _successor_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get(
            "v24567_invalid_population_resume_retry_rerun_or_evaluation"
        )
        is not False
        or mechanism.get("v24570_serialized_validator_build_audit_bound")
        is not True
        or mechanism.get("serialized_protocol_validator_repair_policy")
        != repair.POLICY_ID
        or mechanism.get(
            "complete_nested_protocol_validation_critical_section_serialized"
        )
        is not True
        or mechanism.get("task_execution_remains_parallel_after_protocol_validation")
        is not True
        or mechanism.get(
            "strict_same_task_one_observation_changed_legacy_full_conversion_required"
        )
        is not True
        or mechanism.get(
            "strict_joint_claims_call_query_lead_source_or_page_level_causality"
        )
        is not False
        or provider.get("executor_count") != 8
        or provider.get("model_slot_cap") != 2
        or budget.get("effect_deadline_seconds") != 150.0
        or budget.get("worker_timeout_seconds") != 220.0
        or budget.get("parent_timeout_seconds") != 245.0
        or budget.get("maximum_batch_wall_seconds") != 255.0
        or copied.get("authorization") != _protocol_authorization()
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.71 protocol drifted")
    return copied


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.45.71 protocol root drifted")
    with _PROTOCOL_VALIDATOR_LOCK:
        return _validate_protocol_unlocked(value=value)


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(), _outer_validators("validate_protocol"):
        value = _ORIGINAL_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_436_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_436_and_3488",
        "all_prior_populations_resume_retry_rerun_or_evaluation",
        "v24566_strict_reachability_conversion_build_audit_validated",
    ):
        checks.pop(name, None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_444_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_444_and_3552"] = True
    checks["v24567_invalid_population_resume_retry_rerun_or_evaluation"] = False
    checks["v24568_quarantine_validated"] = True
    checks["v24570_serialized_protocol_validator_build_audit_validated"] = True
    checks["complete_nested_protocol_validation_critical_section_serialized"] = True
    checks["task_execution_remains_parallel_after_protocol_validation"] = True
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.45.71 preaudit root drifted")
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.45.71 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_444_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_444_and_3552",
        "v24567_invalid_population_resume_retry_rerun_or_evaluation",
        "v24568_quarantine_validated",
        "v24570_serialized_protocol_validator_build_audit_validated",
        "complete_nested_protocol_validation_critical_section_serialized",
        "task_execution_remains_parallel_after_protocol_validation",
    ):
        core_checks.pop(name, None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_436_consumed_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_436_and_3488"] = True
    core_checks["all_prior_populations_resume_retry_rerun_or_evaluation"] = False
    core_checks["v24566_strict_reachability_conversion_build_audit_validated"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor(validators=True):
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    required_true = (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_444_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_444_and_3552",
        "v24568_quarantine_validated",
        "v24570_serialized_protocol_validator_build_audit_validated",
        "complete_nested_protocol_validation_critical_section_serialized",
        "task_execution_remains_parallel_after_protocol_validation",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("launch_authorized") is not True
        or any(checks.get(name) is not True for name in required_true)
        or checks.get("v24567_invalid_population_resume_retry_rerun_or_evaluation")
        is not False
        or checks.get("focused_tests", {}).get("test_count")
        != EXPECTED_TEST_COUNT
        or checks.get("focused_tests", {}).get("passed") is not True
        or copied.get("authorization") != _activation_authorization()
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.71 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_predecessor(validators=True):
        value = _ORIGINAL_BUILD_ACTIVATION(now=now)
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.45.71 activation root drifted")
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_predecessor(validators=True):
        return _ORIGINAL_BUILD_EXECUTION_START(now=now)


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.45.71 execution-start root drifted")
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_PUBLIC_RESULT(value)


def run_probe() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_RUN_PROBE()


mechanism_passed = predecessor.mechanism_passed
diagnostic_route = predecessor.diagnostic_route


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
        "role": "v24571_serialized_strict_reachability_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_serialized_strict_reachability_go"
            if passed
            else "fresh_serialized_strict_reachability_no_go"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
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
        "fresh_serialized_strict_reachability_go"
        if passed
        else "fresh_serialized_strict_reachability_no_go"
    )
    if (
        copied.get("role") != "v24571_serialized_strict_reachability_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope", {}).get(
            "call_query_lead_source_or_page_level_causality_claimed"
        )
        is not False
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.71 decision drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    decision = validate_decision()
    lease_active = (
        base.lease_observation(ROOT, Path("/proc")).get("active") is not False
    )
    watchers = base.protected_watcher_snapshot()
    expected = base._read(ROOT, EXECUTION_START)["protected_watchers"]
    findings: list[str] = []
    if lease_active:
        findings.append("shared_api_lease_active")
    if watchers != expected:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24571_serialized_strict_reachability_external_postresult_audit",
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
        "strict_joint_claims_call_query_lead_source_or_page_level_causality": False,
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
        != "v24571_serialized_strict_reachability_external_postresult_audit"
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
        raise RuntimeError("V2.45.71 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_predecessor(validators=True):
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
