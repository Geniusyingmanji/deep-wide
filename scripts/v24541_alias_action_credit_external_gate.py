#!/usr/bin/env python3
"""Fresh action-credit successor after the quarantined V2.45.39 wave.

The runtime surface is exactly ``opaque_id`` and ``question``.  V2.45.39's
entire population is conservatively consumed, V2.45.40 is the build parent,
and this successor owns a re-entrant lock around every nested protocol
validation patch.  No benchmark, evaluator, resume, retry, or selective
rerun is authorized here.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from scripts import v24539_alias_action_credit_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24541_fresh_post_concurrent_quarantine_alias_action_credit_external_gate_v1"
PROTOCOL = Path(f"results/v24541_alias_action_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24541_alias_action_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24541_alias_action_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24541_alias_action_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24541_alias_action_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24541_alias_action_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24541_alias_action_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(f"results/v24540_concurrent_validator_build_audit_v1_{DATE}.json")
QUARANTINE = Path(
    f"results/DO_NOT_USE_invalid_v24539_concurrent_validator_{DATE}/invalid_run_audit.json"
)
RUNNER_MARKER = "scripts/v24541_alias_action_credit_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_post_concurrent_quarantine_alias_action_credit_external_gate"
PRIOR_QUESTION_COUNT = 404
PRIOR_ENTITY_COUNT = 3232
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS

population = predecessor.population
acquisition = predecessor.acquisition
alias_projection = predecessor.alias_projection


ENTITY_GROUPS = (
    (
        "Harrisburg University of Science and Technology",
        "Lake Washington Institute of Technology",
        "Montana Technological University",
        "SUNY Polytechnic Institute",
        "Pennsylvania College of Technology",
        "Capitol Technology University",
        "Benjamin Franklin Institute of Technology",
        "Dunwoody College of Technology",
    ),
    (
        "Karlsruhe University of Applied Sciences",
        "Munich University of Applied Sciences",
        "Berlin University of Applied Sciences and Technology",
        "Bonn-Rhein-Sieg University of Applied Sciences",
        "Lucerne University of Applied Sciences and Arts",
        "Zurich University of Applied Sciences",
        "University of Applied Sciences Upper Austria",
        "Breda University of Applied Sciences",
    ),
    (
        "Atlantic Technological University",
        "Fox Valley Technical College",
        "South East Technological University",
        "Shannon Technological University",
        "Royal College of Surgeons in Ireland",
        "National College of Ireland",
        "Griffith College Dublin",
        "Institute of Art Design and Technology",
    ),
    (
        "AGH University of Science and Technology",
        "Lodz University of Technology",
        "Poznan University of Technology",
        "Silesian University of Technology",
        "Cracow University of Technology",
        "Bialystok University of Technology",
        "Opole University of Technology",
        "Military University of Technology Warsaw",
    ),
    (
        "Baku Engineering University",
        "Kazakh-British Technical University",
        "Almaty University of Power Engineering and Telecommunications",
        "New Uzbekistan University",
        "National University of Mongolia",
        "Mongolian University of Science and Technology",
        "University of Information Technology Vietnam",
        "Khon Kaen University",
    ),
    (
        "Instituto Tecnologico de Santo Domingo",
        "Universidad Iberoamericana Mexico",
        "Universidad Autonoma Metropolitana",
        "Universidad Autonoma de Guadalajara",
        "Universidad del Valle de Guatemala",
        "Universidad Rafael Landivar",
        "Universidad Francisco Marroquin",
        "Universidad Tecnologica Centroamericana",
    ),
    (
        "African Leadership University",
        "Pan-Atlantic University",
        "Afe Babalola University",
        "Landmark University Nigeria",
        "Kumasi Technical University",
        "Takoradi Technical University",
        "University of Eastern Africa Baraton",
        "Technical University of Mombasa",
    ),
    (
        "Northern Alberta Institute of Technology",
        "École de technologie supérieure",
        "Singapore Institute of Management",
        "Management Development Institute of Singapore",
        "Nanyang Academy of Fine Arts",
        "Education University of Hong Kong",
        "Hong Kong Shue Yan University",
        "University of Saint Joseph Macau",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.41 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
ALIAS_TITLE_GROUPS = tuple(
    tuple(f"{acquisition.primary_alias_surface(entity)} history" for entity in group)
    for group in ENTITY_GROUPS
)
GATES = copy.deepcopy(predecessor.GATES)
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *predecessor.SOURCE_FILES,
            "scripts/audit_v24539_invalid_concurrent_validator.py",
            "tests/test_audit_v24539_invalid_concurrent_validator.py",
            str(QUARANTINE),
            "scripts/audit_v24540_concurrent_validator_build.py",
            "tests/test_audit_v24540_concurrent_validator_build.py",
            str(PARENT),
            RUNNER_MARKER,
            "tests/test_v24541_alias_action_credit_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *predecessor.TEST_SUITES,
    ("tests/test_audit_v24539_invalid_concurrent_validator.py", 5, 120),
    ("tests/test_audit_v24540_concurrent_validator_build.py", 6, 180),
    ("tests/test_v24541_alias_action_credit_external_gate.py", 13, 420),
)
EXPECTED_TEST_COUNT = predecessor.EXPECTED_TEST_COUNT + 24


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
_FROZEN_PREDECESSOR_PROTOCOL_ID = predecessor.PROTOCOL_ID
_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING = copy.deepcopy(
    predecessor._record_bound_binding()
)
_PROTOCOL_VALIDATOR_LOCK = threading.RLock()


def _base() -> Any:
    return predecessor._base()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.41 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _quarantine_valid() -> bool:
    value = _read(QUARANTINE)
    incident = value.get("incident", {})
    population_state = value.get("population", {})
    provenance = value.get("provenance", {})
    authorization = value.get("authorization", {})
    return (
        value.get("role") == "v24539_invalid_concurrent_validator_run_audit"
        and value.get("protocol_id") == _FROZEN_PREDECESSOR_PROTOCOL_ID
        and value.get("status") == "invalid_quarantined_no_public_result"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and incident.get("shared_successor_module_patch_interleaving") is True
        and incident.get("external_effect_counts_recoverable") is False
        and incident.get("public_result_published") is False
        and population_state.get("same_population_rerun_allowed") is False
        and population_state.get("next_prior_question_count") == PRIOR_QUESTION_COUNT
        and population_state.get("next_prior_entity_count") == PRIOR_ENTITY_COUNT
        and provenance.get("fix_is_ancestor_of_head_and_target_main") is True
        and authorization.get("same_population_resume_retry_or_rerun") is False
        and authorization.get("ordinary_v24539_result_decision_or_postaudit") is False
        and authorization.get("fresh_disjoint_successor_protocol_design") is True
        and authorization.get("fresh_successor_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    closed = value.get("v24539_quarantine", {})
    repair = value.get("repair", {})
    stress = repair.get("stress", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24540_concurrent_validator_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 66
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or closed.get("valid") is not True
        or closed.get("same_population_rerun_authorized") is not False
        or closed.get("next_prior_question_count") != PRIOR_QUESTION_COUNT
        or closed.get("next_prior_entity_count") != PRIOR_ENTITY_COUNT
        or repair.get("reentrant_protocol_validator_lock_present") is not True
        or repair.get("nested_module_patch_critical_section_serialized") is not True
        or repair.get("task_execution_remains_parallel_after_protocol_validation")
        is not True
        or stress.get("passed") is not True
        or stress.get("workers") != 8
        or stress.get("validations") != 200
        or authorization.get(
            "fresh_disjoint_action_credit_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.41 build parent drifted")
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
        cells = predecessor._baseline_cells(baseline)
        for entity, raw_title in zip(entities, titles, strict=True):
            surface = acquisition.primary_alias_surface(entity)
            anchor = alias_projection.unique_alias_title_row(raw_title, cells)
            if surface is None or anchor is None or anchor.row_key != entity:
                return False
            all_surfaces.append(surface.casefold())
            matched += 1
    return matched == 64 and len(set(all_surfaces)) == 64


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_404_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_alias_title_surfaces_globally_unique_and_uniquely_match_under_frozen_rule": _alias_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "v24539_invalid_population_counted_as_consumed": True,
        "v24539_population_resume_retry_or_rerun": False,
        "population_selection_uses_visible_names_and_frozen_alias_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _record_bound_binding() -> dict[str, Any]:
    if not _quarantine_valid():
        raise RuntimeError("V2.45.41 V2.45.39 quarantine closure drifted")
    return {
        **copy.deepcopy(_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING),
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "v24539_quarantine_path": str(QUARANTINE),
        "v24539_quarantine_sha256": sha256(ROOT / QUARANTINE),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "v24539_population_resume_retry_or_rerun": False,
        "new_population_reuses_prior_question_or_entity": False,
        "concurrent_validator_build_repair_frozen": True,
        "successor_owns_reentrant_protocol_validator_lock": True,
        "required_action_aggregate_schema": predecessor.predecessor.total.POLICY_ID,
        "same_run_action_credit_used_for_routing_training_or_policy_update": False,
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
            "_prior_questions": _prior_questions,
            "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
            "_parent": _parent,
            "_task_contract": _task_contract,
            "run_targeted_worker": predecessor.predecessor.proof.run_worker,
            "supervise_targeted_worker_with_separated_budget": predecessor.predecessor.proof.supervise_worker_with_separated_budget,
            "run_targeted_parent_with_separated_budget": predecessor.predecessor.proof.run_parent_with_separated_budget,
            "aggregate_projections": predecessor.predecessor.aggregate_action_projections,
            "validate_targeted_aggregate": predecessor.predecessor.total.validate_aggregate,
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
        "QUARANTINE": QUARANTINE,
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
        "_quarantine_valid": _quarantine_valid,
        "_record_bound_binding": _record_bound_binding,
        "_patched_core": _patched_core,
        "mechanism_passed": mechanism_passed,
        "diagnostic_route": diagnostic_route,
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
        raise RuntimeError("V2.45.41 V2.45.39 quarantine is not closed")
    _parent(ROOT)
    with configured_predecessor():
        value = _ORIGINAL_BUILD_PROTOCOL(
            now=now, require_pristine=require_pristine
        )
    value = copy.deepcopy(value)
    value["scope"] = "fresh_post_concurrent_quarantine_alias_action_credit_gate"
    value["mechanism"].update(
        {
            "v24539_invalid_population_resume_retry_or_rerun": False,
            "concurrent_validator_build_audit_bound": True,
            "successor_owned_reentrant_protocol_validator_lock": True,
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
    core["scope"] = "fresh_post_quarantine_alias_action_credit_gate"
    for name in (
        "v24539_invalid_population_resume_retry_or_rerun",
        "concurrent_validator_build_audit_bound",
        "successor_owned_reentrant_protocol_validator_lock",
    ):
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PROTOCOL(value=core)
    mechanism = copied.get("mechanism", {})
    provider = copied.get("provider", {})
    budget = copied.get("budget", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_post_concurrent_quarantine_alias_action_credit_gate"
        or copied.get("parent")
        != {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("v24539_invalid_population_resume_retry_or_rerun")
        is not False
        or mechanism.get("concurrent_validator_build_audit_bound") is not True
        or mechanism.get("successor_owned_reentrant_protocol_validator_lock")
        is not True
        or provider.get("executor_count") != 8
        or provider.get("model_slot_cap") != 2
        or budget.get("effect_deadline_seconds") != 150.0
        or budget.get("worker_timeout_seconds") != 220.0
        or budget.get("parent_timeout_seconds") != 245.0
        or budget.get("maximum_batch_wall_seconds") != 255.0
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.41 protocol drifted")
    return copied


def validate_protocol(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    # This lock belongs to V2.45.41 itself.  It encloses the complete nested
    # module-patching chain; the actual eight task workers remain concurrent.
    with _PROTOCOL_VALIDATOR_LOCK:
        return _validate_protocol_unlocked(value=value)


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor(), _outer_validators("validate_protocol"):
        value = _ORIGINAL_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_396_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_396_and_3168",
        "v24537_invalid_population_resume_retry_or_rerun",
        "execution_base_action_binding_build_audit_validated",
    ):
        checks.pop(name, None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_404_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_404_and_3232"] = True
    checks["v24539_invalid_population_resume_retry_or_rerun"] = False
    checks["v24540_concurrent_validator_build_audit_validated"] = True
    checks["successor_owned_reentrant_protocol_validator_lock"] = True
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
        raise RuntimeError("V2.45.41 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_404_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_404_and_3232",
        "v24539_invalid_population_resume_retry_or_rerun",
        "v24540_concurrent_validator_build_audit_validated",
        "successor_owned_reentrant_protocol_validator_lock",
    ):
        core_checks.pop(name, None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_396_consumed_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_396_and_3168"] = True
    core_checks["v24537_invalid_population_resume_retry_or_rerun"] = False
    core_checks["execution_base_action_binding_build_audit_validated"] = True
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
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_404_consumed_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_404_and_3232")
        is not True
        or checks.get("v24539_invalid_population_resume_retry_or_rerun")
        is not False
        or checks.get("v24540_concurrent_validator_build_audit_validated")
        is not True
        or checks.get("successor_owned_reentrant_protocol_validator_lock")
        is not True
        or checks.get("focused_tests", {}).get("test_count")
        != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.41 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_predecessor(validators=True):
        return _ORIGINAL_BUILD_ACTIVATION(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_predecessor(validators=True):
        return _ORIGINAL_BUILD_EXECUTION_START(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        copied = _ORIGINAL_VALIDATE_PUBLIC_RESULT(value)
    mechanism = copied.get("mechanism_aggregate", {})
    required = (
        "acquisition_plan_tasks",
        "total_acquisition_action_count_fields",
        "total_acquisition_action_number_fields",
    )
    if not isinstance(mechanism, Mapping) or any(name not in mechanism for name in required):
        raise RuntimeError("V2.45.41 action aggregate schema is absent")
    return copied


def run_probe() -> dict[str, Any]:
    with configured_predecessor(validators=True):
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
        "role": "v24541_alias_action_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(_base().time.time()) if now is None else int(now),
        "status": (
            "fresh_post_concurrent_quarantine_alias_action_credit_go"
            if passed
            else "fresh_post_concurrent_quarantine_alias_action_credit_no_go"
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
        "fresh_post_concurrent_quarantine_alias_action_credit_go"
        if passed
        else "fresh_post_concurrent_quarantine_alias_action_credit_no_go"
    )
    if (
        copied.get("role") != "v24541_alias_action_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("authorization") != _decision_authorization(passed)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.45.41 decision drifted")
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
        "role": "v24541_alias_action_external_postresult_audit",
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
        copied.get("role") != "v24541_alias_action_external_postresult_audit"
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
        raise RuntimeError("V2.45.41 postresult audit drifted")
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
