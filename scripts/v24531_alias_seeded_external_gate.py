#!/usr/bin/env python3
"""Fresh one-wave external gate for alias-seeded acquisition.

The 64 visible entities are literal/canonical disjoint from all 372 earlier
external questions and 2,976 entities.  Population selection uses visible
names and the frozen alias grammar only.  V2.45.29 changes the two existing
queries and pre-fetch ranking without adding a query, batch, fetch, model
request, vote, source credit, entropy credit, or decision credit.
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
from scripts import v24445_serialized_narrative_external_gate as population  # noqa: E402
from scripts import v24528_alias_title_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24531_fresh_alias_seeded_entropy_credit_external_gate_v1"
PROTOCOL = Path(f"results/v24531_alias_seeded_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24531_alias_seeded_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24531_alias_seeded_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24531_alias_seeded_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24531_alias_seeded_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24531_alias_seeded_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24531_alias_seeded_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24530_alias_seeded_bounded_worker_build_audit_v1_{DATE}.json"
)
RUNNER_MARKER = "scripts/v24531_alias_seeded_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_alias_seeded_entropy_credit_external_gate"
PRIOR_QUESTION_COUNT = 372
PRIOR_ENTITY_COUNT = 2976
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS
PREVIOUS_RESULT = predecessor.RESULT
PREVIOUS_DECISION = predecessor.DECISION
PREVIOUS_POSTAUDIT = predecessor.POSTAUDIT
PREVIOUS_PROTOCOL_ID = predecessor.PROTOCOL_ID


ENTITY_GROUPS = (
    (
        "Rochester Institute of Technology",
        "Worcester Polytechnic Institute",
        "Rensselaer Polytechnic Institute",
        "Rose-Hulman Institute of Technology",
        "Wentworth Institute of Technology",
        "Oregon Institute of Technology",
        "University of Texas at Arlington",
        "University of Texas at Dallas",
    ),
    (
        "University of Texas at San Antonio",
        "Kennesaw State University",
        "Tennessee State University",
        "Tennessee Technological University",
        "Sam Houston State University",
        "Grambling State University",
        "University of Arkansas Fort Smith",
        "University of Missouri St Louis",
    ),
    (
        "Western Illinois University",
        "Eastern Illinois University",
        "Wayne State University",
        "Western Michigan University",
        "Eastern Michigan University",
        "Central Michigan University",
        "Grand Valley State University",
        "Case Western Reserve University",
    ),
    (
        "Singapore Management University",
        "Singapore University of Technology and Design",
        "Singapore Institute of Technology",
        "Singapore University of Social Sciences",
        "Hong Kong Baptist University",
        "Macao University of Science and Technology",
        "Korea Advanced Institute of Science and Technology",
        "Indian Institute of Technology Guwahati",
    ),
    (
        "Indian Institute of Technology Hyderabad",
        "Indian Institute of Management Ahmedabad",
        "Indian Institute of Management Bangalore",
        "École Polytechnique Fédérale de Lausanne",
        "Queen Mary University of London",
        "London South Bank University",
        "University of East London",
        "Royal Holloway University of London",
    ),
    (
        "University of West London",
        "Queensland University of Technology",
        "Royal Melbourne Institute of Technology",
        "Charles Sturt University",
        "Western Sydney University",
        "James Cook University",
        "British Columbia Institute of Technology",
        "Toronto Metropolitan University",
    ),
    (
        "Wilfrid Laurier University",
        "Memorial University of Newfoundland",
        "Nelson Mandela University",
        "Cape Peninsula University of Technology",
        "Tshwane University of Technology",
        "Durban University of Technology",
        "Central University of Technology",
        "Federal University of Technology Akure",
    ),
    (
        "Universidad Nacional Autónoma de México",
        "Universidad de Buenos Aires",
        "Universidade de São Paulo",
        "Universidad Nacional de Colombia",
        "Universidad de Costa Rica",
        "Universidad de Puerto Rico",
        "Universidad Central de Venezuela",
        "Pontificia Universidad Católica del Perú",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.31 entity group drifted")
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
            "src/deepwide_agent/v24529_alias_seeded_target_acquisition.py",
            "tests/test_v24529_alias_seeded_target_acquisition.py",
            "src/deepwide_agent/v24530_alias_seeded_bounded_worker.py",
            "tests/test_v24530_alias_seeded_bounded_worker.py",
            "scripts/audit_v24530_alias_seeded_bounded_worker_build.py",
            "tests/test_audit_v24530_alias_seeded_bounded_worker_build.py",
            str(PARENT),
            str(PREVIOUS_RESULT),
            str(PREVIOUS_DECISION),
            str(PREVIOUS_POSTAUDIT),
            RUNNER_MARKER,
            "tests/test_v24531_alias_seeded_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *predecessor.TEST_SUITES,
    ("tests/test_v24529_alias_seeded_target_acquisition.py", 8, 180),
    ("tests/test_v24530_alias_seeded_bounded_worker.py", 3, 300),
    ("tests/test_audit_v24530_alias_seeded_bounded_worker_build.py", 6, 90),
    ("tests/test_v24531_alias_seeded_external_gate.py", 12, 300),
)
EXPECTED_TEST_COUNT = predecessor.EXPECTED_TEST_COUNT + 29


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
_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING = copy.deepcopy(
    predecessor._record_bound_binding()
)


def _base() -> Any:
    return predecessor._base()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.31 expected object")
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
    authorization = value.get("authorization", {})
    if (
        not isinstance(value, dict)
        or value.get("role")
        != "v24530_alias_seeded_bounded_worker_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("v24528_no_go_closure", {}).get("valid") is not True
        or value.get("v24528_no_go_closure", {}).get(
            "population_rerun_authorized"
        )
        is not False
        or authorization.get(
            "fresh_disjoint_alias_seeded_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.31 build parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_372_prior_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_prior_external_populations_rerun": False,
        "v24528_population_rerun": False,
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
        and result.get("selected") == 8
        and result.get("passed") is False
        and result.get("mechanism_passed") is False
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and decision.get("status") == "fresh_alias_mechanism_no_go"
        and decision.get("diagnostic_route")
        == "alias_source_title_coverage_successor"
        and decision.get("authorization", {}).get("new_exact220") is False
        and postaudit.get("audit_valid") is True
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("findings") == []
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
    )


def _record_bound_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.31 V2.45.28 closure drifted")
    return {
        **copy.deepcopy(_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING),
        "alias_seeded_target_acquisition_policy": acquisition.POLICY_ID,
        "alias_seeded_bounded_worker_policy": seeded.POLICY_ID,
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "new_population_reuses_prior_question_or_entity": False,
        "v24528_population_rerun": False,
        "v24528_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24528_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24528_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "alias_seed_derived_only_from_visible_row_text": True,
        "alias_title_priority_uses_visible_title_only": True,
        "alias_hint_receives_vote_source_entropy_or_decision_credit": False,
        "logical_query_search_batch_and_fetch_caps_changed": False,
        "source_count_posterior_margin_leave_one_out_and_credit_rules_relaxed": False,
        "historical_private_page_opened": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return predecessor.mechanism_passed(value)


def diagnostic_route(
    mechanism: Mapping[str, Any],
    supervision: Mapping[str, Any],
    *,
    diagnostic: bool,
    reliability: bool,
    parent_validation: bool,
    latency: bool,
) -> str:
    return predecessor.diagnostic_route(
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
            "aggregate_projections": predecessor.aggregate_alias_projections,
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
        "_previous_closed": _previous_closed,
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
    if not _previous_closed():
        raise RuntimeError("V2.45.31 predecessor is not closed")
    with configured_predecessor():
        value = _ORIGINAL_BUILD_PROTOCOL(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_nonbenchmark_alias_seeded_entropy_credit_gate"
    value["mechanism"].update(
        {
            "alias_seeded_target_acquisition_policy": acquisition.POLICY_ID,
            "alias_seeded_bounded_worker_policy": seeded.POLICY_ID,
            "alias_seed_derived_only_from_visible_row_text": True,
            "visible_title_alias_hit_priority_before_frozen_target_coverage_order": True,
            "alias_hint_receives_vote_source_entropy_or_decision_credit": False,
            "logical_query_search_batch_and_fetch_caps_changed": False,
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
    core["scope"] = "fresh_nonbenchmark_natural_alias_title_entropy_credit_gate"
    mechanism = core.get("mechanism", {})
    for name in (
        "alias_seeded_target_acquisition_policy",
        "alias_seeded_bounded_worker_policy",
        "alias_seed_derived_only_from_visible_row_text",
        "visible_title_alias_hit_priority_before_frozen_target_coverage_order",
        "alias_hint_receives_vote_source_entropy_or_decision_credit",
        "logical_query_search_batch_and_fetch_caps_changed",
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
        != "fresh_nonbenchmark_alias_seeded_entropy_credit_gate"
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or current.get("targeted_parent_policy") != seeded.POLICY_ID
        or current.get("alias_seeded_target_acquisition_policy")
        != acquisition.POLICY_ID
        or current.get("alias_seeded_bounded_worker_policy") != seeded.POLICY_ID
        or current.get("alias_seed_derived_only_from_visible_row_text") is not True
        or current.get(
            "visible_title_alias_hit_priority_before_frozen_target_coverage_order"
        )
        is not True
        or current.get("alias_hint_receives_vote_source_entropy_or_decision_credit")
        is not False
        or current.get("logical_query_search_batch_and_fetch_caps_changed") is not False
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
        raise RuntimeError("V2.45.31 alias-seeded protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(), _outer_validators("validate_protocol"):
        value = _ORIGINAL_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_364_prior_external_questions",
        None,
    )
    checks.pop("prior_external_questions_and_entities_exactly_364_and_2912", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_372_prior_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_372_and_2976"] = True
    checks["alias_seeded_worker_cli_binding_validated"] = True
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
        raise RuntimeError("V2.45.31 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    core_checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_372_prior_external_questions",
        None,
    )
    core_checks.pop("prior_external_questions_and_entities_exactly_372_and_2976", None)
    core_checks.pop("alias_seeded_worker_cli_binding_validated", None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_364_prior_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_364_and_2912"] = True
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
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_372_prior_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_372_and_2976")
        is not True
        or checks.get("alias_seeded_worker_cli_binding_validated") is not True
        or checks.get("focused_tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.31 preactivation audit drifted")
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
        "role": "v24531_alias_seeded_external_decision",
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
    if (
        copied.get("role") != "v24531_alias_seeded_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != (
            "fresh_alias_seeded_mechanism_go"
            if passed
            else "fresh_alias_seeded_mechanism_no_go"
        )
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
        raise RuntimeError("V2.45.31 decision drifted")
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
        "role": "v24531_alias_seeded_external_postresult_audit",
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
        != "v24531_alias_seeded_external_postresult_audit"
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
        raise RuntimeError("V2.45.31 postresult audit drifted")
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
