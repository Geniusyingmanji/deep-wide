#!/usr/bin/env python3
"""Fresh disjoint successor to the quarantined V2.45.31 execution.

The 64 visible entities are literal/canonical disjoint from the 380 consumed
external questions and 3,040 entities, including the invalid V2.45.31 wave.
The callback fix is frozen and tested inside the configured runtime context.
No V2.45.31 question or entity may be resumed, retried, or rerun.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Iterator, Mapping
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
from deepwide_agent import v24525_proof_carrying_alias_title as alias_proof  # noqa: E402
from deepwide_agent import v24526_total_alias_title_projection as total  # noqa: E402
from deepwide_agent import v24529_alias_seeded_target_acquisition as acquisition  # noqa: E402
from deepwide_agent import v24530_alias_seeded_bounded_worker as seeded  # noqa: E402
from scripts import audit_v24531_invalid_callback_recursion as quarantine  # noqa: E402
from scripts import v24445_serialized_narrative_external_gate as population  # noqa: E402
from scripts import v24531_alias_seeded_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24532_fresh_alias_seeded_entropy_credit_external_gate_v1"
PROTOCOL = Path(f"results/v24532_alias_seeded_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24532_alias_seeded_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24532_alias_seeded_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24532_alias_seeded_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24532_alias_seeded_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24532_alias_seeded_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24532_alias_seeded_external_postresult_audit_v1_{DATE}.json"
)
PARENT = quarantine.AUDIT
RUNNER_MARKER = "scripts/v24532_alias_seeded_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_disjoint_post_recursion_alias_seeded_external_gate"
PRIOR_QUESTION_COUNT = 380
PRIOR_ENTITY_COUNT = 3040
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS


ENTITY_GROUPS = (
    (
        "University of North Carolina Wilmington",
        "University of North Carolina Greensboro",
        "University of North Carolina Charlotte",
        "University of North Carolina Asheville",
        "University of North Carolina Pembroke",
        "University of North Carolina School of the Arts",
        "University of Maryland Eastern Shore",
        "University of Massachusetts Lowell",
    ),
    (
        "University of Wisconsin Green Bay",
        "University of Wisconsin Eau Claire",
        "University of Wisconsin Stevens Point",
        "University of Wisconsin Whitewater",
        "University of Wisconsin Oshkosh",
        "University of Wisconsin Platteville",
        "University of Wisconsin River Falls",
        "University of Wisconsin Superior",
    ),
    (
        "California State University Los Angeles",
        "California State University Northridge",
        "California State University San Bernardino",
        "California State University San Marcos",
        "California State University Monterey Bay",
        "California State University Channel Islands",
        "California State University Bakersfield",
        "California State University Dominguez Hills",
    ),
    (
        "National Taiwan Normal University",
        "National Central University",
        "National Cheng Kung University",
        "Taipei Medical University",
        "National Sun Yat-sen University",
        "National Chung Hsing University",
        "National Taiwan Ocean University",
        "Technological University of the Philippines",
    ),
    (
        "East China University of Science and Technology",
        "Nanjing University of Science and Technology",
        "Changsha University of Science and Technology",
        "Wuhan University of Technology",
        "Hefei University of Technology",
        "Nanjing University of Posts and Telecommunications",
        "Chongqing University of Posts and Telecommunications",
        "Guilin University of Electronic Technology",
    ),
    (
        "Indian Institute of Information Technology Allahabad",
        "International Institute of Information Technology Hyderabad",
        "Indraprastha Institute of Information Technology Delhi",
        "International Institute of Information Technology Bangalore",
        "Indian Institute of Information Technology Gwalior",
        "Indian Institute of Information Technology Jabalpur",
        "National Institute of Technology Durgapur",
        "National Institute of Technology Silchar",
    ),
    (
        "American University of Sharjah",
        "King Fahd University of Petroleum and Minerals",
        "Hamad Bin Khalifa University",
        "University of Doha for Science and Technology",
        "German University in Cairo",
        "Egypt-Japan University of Science and Technology",
        "Athens University of Economics and Business",
        "Malta College of Arts Science and Technology",
    ),
    (
        "Florida Gulf Coast University",
        "Florida Agricultural and Mechanical University",
        "Florida Polytechnic University",
        "Virginia Military Institute",
        "Western Carolina University",
        "Austin Peay State University",
        "University of Texas Permian Basin",
        "New Mexico State University",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.32 entity group drifted")
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
GATES = copy.deepcopy(predecessor.GATES)
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *predecessor.SOURCE_FILES,
            "scripts/audit_v24531_invalid_callback_recursion.py",
            "tests/test_audit_v24531_invalid_callback_recursion.py",
            str(PARENT),
            RUNNER_MARKER,
            "tests/test_v24532_alias_seeded_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *predecessor.TEST_SUITES,
    ("tests/test_audit_v24531_invalid_callback_recursion.py", 5, 90),
    ("tests/test_v24532_alias_seeded_external_gate.py", 12, 300),
)
EXPECTED_TEST_COUNT = predecessor.EXPECTED_TEST_COUNT + 17


_ORIGINAL_BUILD_PROTOCOL = predecessor.build_protocol
_ORIGINAL_PATCHED_CORE = predecessor._patched_core
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
_ORIGINAL_MECHANISM_PASSED = predecessor.mechanism_passed
_ORIGINAL_DIAGNOSTIC_ROUTE = predecessor.diagnostic_route
_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING = copy.deepcopy(
    predecessor._record_bound_binding()
)


def _base() -> Any:
    return predecessor._base()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.32 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _quarantine_valid() -> bool:
    value = _read(PARENT)
    authorization = value.get("authorization", {})
    population_state = value.get("population", {})
    return (
        value.get("role") == "v24531_invalid_callback_recursion_run_audit"
        and value.get("protocol_id") == quarantine.PROTOCOL_ID
        and value.get("status") == "invalid_quarantined_no_public_result"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and population_state.get("same_population_rerun_allowed") is False
        and population_state.get("next_prior_question_count")
        == PRIOR_QUESTION_COUNT
        and population_state.get("next_prior_entity_count") == PRIOR_ENTITY_COUNT
        and authorization.get("same_population_resume_retry_or_rerun") is False
        and authorization.get("fresh_disjoint_successor_protocol_design") is True
        and authorization.get("fresh_successor_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
        and _sealed(value, "audit_payload_sha256")
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


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not _quarantine_valid():
        raise RuntimeError("V2.45.32 quarantine parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_380_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "v24531_invalid_population_counted_as_consumed": True,
        "v24531_population_resume_retry_or_rerun": False,
        "population_selection_uses_visible_names_and_frozen_alias_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _record_bound_binding() -> dict[str, Any]:
    if not _quarantine_valid():
        raise RuntimeError("V2.45.32 quarantine closure drifted")
    return {
        **copy.deepcopy(_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING),
        "quarantine_path": str(PARENT),
        "quarantine_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "v24531_population_resume_retry_or_rerun": False,
        "new_population_reuses_prior_question_or_entity": False,
        "callback_recursion_regression_covered_in_configured_context": True,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return _ORIGINAL_MECHANISM_PASSED(value)


def diagnostic_route(
    mechanism: Mapping[str, Any],
    supervision: Mapping[str, Any],
    *,
    diagnostic: bool,
    reliability: bool,
    parent_validation: bool,
    latency: bool,
) -> str:
    return _ORIGINAL_DIAGNOSTIC_ROUTE(
        mechanism,
        supervision,
        diagnostic=diagnostic,
        reliability=reliability,
        parent_validation=parent_validation,
        latency=latency,
    )


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
            "TARGETED_PARENT_POLICY_ID": seeded.POLICY_ID,
            "_prior_questions": _prior_questions,
            "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
            "_parent": _parent,
            "_task_contract": _task_contract,
            "run_targeted_worker": seeded.run_alias_seeded_worker,
            "supervise_targeted_worker_with_separated_budget": seeded.supervise_alias_seeded_worker_with_separated_budget,
            "run_targeted_parent_with_separated_budget": seeded.run_alias_seeded_parent_with_separated_budget,
            "aggregate_projections": predecessor.predecessor.aggregate_alias_projections,
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
        "_previous_closed": _quarantine_valid,
        "_record_bound_binding": _record_bound_binding,
        "_patched_core": _patched_core,
        "mechanism_passed": mechanism_passed,
        "diagnostic_route": diagnostic_route,
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
    if not _quarantine_valid():
        raise RuntimeError("V2.45.32 quarantine is not closed")
    with configured_predecessor():
        value = _ORIGINAL_BUILD_PROTOCOL(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_disjoint_post_recursion_alias_seeded_entropy_credit_gate"
    value["mechanism"].update(
        {
            "callback_recursion_fix_commit": quarantine.FIX_COMMIT,
            "configured_context_callback_regression_required": True,
            "v24531_population_resume_retry_or_rerun": False,
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
    core["scope"] = "fresh_nonbenchmark_alias_seeded_entropy_credit_gate"
    mechanism = core.get("mechanism", {})
    for name in (
        "callback_recursion_fix_commit",
        "configured_context_callback_regression_required",
        "v24531_population_resume_retry_or_rerun",
    ):
        mechanism.pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    current = copied.get("mechanism", {})
    budget = copied.get("budget", {})
    provider = copied.get("provider", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_disjoint_post_recursion_alias_seeded_entropy_credit_gate"
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or current.get("callback_recursion_fix_commit") != quarantine.FIX_COMMIT
        or current.get("configured_context_callback_regression_required") is not True
        or current.get("v24531_population_resume_retry_or_rerun") is not False
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
        raise RuntimeError("V2.45.32 protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(), _outer_validators("validate_protocol"):
        value = _ORIGINAL_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_372_prior_external_questions",
        None,
    )
    checks.pop("prior_external_questions_and_entities_exactly_372_and_2976", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_380_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_380_and_3040"] = True
    checks["v24531_invalid_population_resume_retry_or_rerun"] = False
    checks["callback_recursion_regression_passed_in_configured_context"] = True
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
        raise RuntimeError("V2.45.32 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_380_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_380_and_3040",
        "v24531_invalid_population_resume_retry_or_rerun",
        "callback_recursion_regression_passed_in_configured_context",
    ):
        core_checks.pop(name, None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_372_prior_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_372_and_2976"] = True
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
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_380_consumed_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_380_and_3040")
        is not True
        or checks.get("v24531_invalid_population_resume_retry_or_rerun") is not False
        or checks.get("callback_recursion_regression_passed_in_configured_context")
        is not True
        or checks.get("focused_tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.32 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_predecessor(), _outer_validators(
        "validate_protocol", "validate_preaudit"
    ):
        return _ORIGINAL_BUILD_ACTIVATION(now=now)


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
        return _ORIGINAL_BUILD_EXECUTION_START(now=now)


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
        "role": "v24532_alias_seeded_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(_base().time.time()) if now is None else int(now),
        "status": (
            "fresh_alias_seeded_mechanism_go"
            if passed
            else "fresh_alias_seeded_mechanism_no_go"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_alias_seeded_mechanism_measured": True,
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
        "fresh_alias_seeded_mechanism_go"
        if passed
        else "fresh_alias_seeded_mechanism_no_go"
    )
    if (
        copied.get("role") != "v24532_alias_seeded_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope")
        != {
            "fresh_nonbenchmark_alias_seeded_mechanism_measured": True,
            "benchmark_quality_measured": False,
            "paired_dev64_launch_authorized": False,
            "sota_supported": False,
        }
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.32 decision drifted")
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
        "role": "v24532_alias_seeded_external_postresult_audit",
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
        != "v24532_alias_seeded_external_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status") != decision["status"]
        or copied.get("diagnostic_route") != decision["diagnostic_route"]
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != _base().protected_watcher_snapshot()
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
        raise RuntimeError("V2.45.32 postresult audit drifted")
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
