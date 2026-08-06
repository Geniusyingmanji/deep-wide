#!/usr/bin/env python3
"""Fresh successor that restores the V2.46.10 collector lifetime.

V2.46.20 consumed one external population after all task futures returned but
failed closed at main-process aggregation because its custom fast-validation
loop omitted the instance-local title-provenance collector context.  This
successor keeps the validated concurrent binding, fast control receipt, and
enforcing watchdog unchanged.  Its only runtime repair enters
``collector.capability_collection()`` around both task execution and aggregate
projection.  A new 8-task/64-entity population is disjoint from all 508 prior
external questions and 4,064 entities.
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
from scripts import v24620_title_provenance_watchdog_external_gate as frozen  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24622_fresh_collector_lifetime_external_gate_v1"
BUILD_AUDIT = Path(f"results/v24623_collector_lifetime_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24622_collector_lifetime_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24622_collector_lifetime_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24622_collector_lifetime_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24622_collector_lifetime_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24622_collector_lifetime_result_v1_{DATE}.json")
DECISION = Path(f"results/v24622_collector_lifetime_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24622_collector_lifetime_postresult_audit_v1_{DATE}.json")
DECISION_ROLE = "v24622_collector_lifetime_external_decision"
POSTAUDIT_ROLE = "v24622_collector_lifetime_external_postresult_audit"
PARENT = Path("results/v24621_v24620_postfailure_audit_v1_20260806.json")
PREVIOUS_FAILURE = Path(
    "results/v24621_v24620_terminal_collector_failure_v1_20260806.json"
)
RUNNER_MARKER = "scripts/v24622_collector_lifetime_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_title_provenance_collector_lifetime_gate"
PRIOR_QUESTION_COUNT = 508
PRIOR_ENTITY_COUNT = 4064
PRIOR_QUESTIONS = frozen._prior_questions() + frozen.QUESTIONS

controller = frozen.controller
runtime = frozen.runtime
base = frozen.base
population = frozen.population
query_policy = frozen.query_policy
alias_projection = frozen.alias_projection
acquisition = frozen.acquisition
proof = frozen.proof
total = frozen.total
bounded = frozen.bounded
binding = frozen.binding
watchdog = frozen.watchdog
collector = frozen.collector
STRICT_TASK_FIELD = frozen.STRICT_TASK_FIELD
_INHERITED_ORIGINAL_TASK_PROJECTION = runtime._ORIGINAL_TASK_PROJECTION
_MISSING = object()

_BASE_BUILD_PROTOCOL = frozen.build_protocol
_BASE_VALIDATE_PROTOCOL = frozen.validate_protocol
_BASE_BUILD_PREAUDIT = frozen.build_preaudit
_BASE_VALIDATE_PREAUDIT = frozen.validate_preaudit
_BASE_BUILD_ACTIVATION = frozen.build_activation
_BASE_VALIDATE_ACTIVATION = frozen.validate_activation
_BASE_BUILD_EXECUTION_START = frozen.build_execution_start
_BASE_VALIDATE_EXECUTION_START = frozen.validate_execution_start
_BASE_VALIDATE_PUBLIC_RESULT = frozen.validate_public_result
_BASE_RUN_PROBE_FAST = frozen._run_probe_fast
_BASE_RUN_PROCESS_SUBCOMMAND = frozen.run_process_subcommand


ENTITY_GROUPS = (
    (
        "California Northstate University",
        "University of the Cumberlands",
        "College of the Menominee Nation",
        "Oblate School of Theology",
        "Catholic Theological Union",
        "University of Philosophical Research",
        "Monterey College of Law",
        "Vermont Law and Graduate School",
    ),
    (
        "Massachusetts School of Law",
        "Appalachian School of Law",
        "Charleston School of Law",
        "Elon University School of Law",
        "Academy of Art University",
        "Full Sail University",
        "Indiana Institute of Technology",
        "Harris Stowe State University",
    ),
    (
        "University of Alaska Southeast",
        "University of Maine at Farmington",
        "University of Wisconsin Parkside",
        "University of North Carolina at Pembroke",
        "University of North Carolina at Asheville",
        "University of South Carolina Upstate",
        "University of South Carolina Aiken",
        "University of South Carolina Beaufort",
    ),
    (
        "University of Tennessee at Martin",
        "University of Tennessee at Chattanooga",
        "University of Texas at Tyler",
        "Texas A and M International University",
        "Texas A and M University Texarkana",
        "Texas A and M University Corpus Christi",
        "Texas A and M University Kingsville",
        "Texas A and M University San Antonio",
    ),
    (
        "Louisiana State University Shreveport",
        "Louisiana State University Alexandria",
        "Louisiana State University Eunice",
        "Southern University at Shreveport",
        "University of Arkansas for Medical Sciences",
        "University of West Alabama",
        "University of Montevallo",
        "University of North Alabama",
    ),
    (
        "University of West Georgia",
        "University of North Georgia",
        "Georgia Southwestern State University",
        "Georgia College and State University",
        "Governors State University Illinois",
        "Dalton State College",
        "Abraham Baldwin Agricultural College",
        "College of Coastal Georgia",
    ),
    (
        "Savannah State University",
        "Fort Valley State University",
        "Albany State University Georgia",
        "Kentucky State University",
        "Pratt Institute School of Architecture",
        "Maryland Institute College of Art",
        "College for Creative Studies",
        "Pacific Northwest College of Art",
    ),
    (
        "Watkins College of Art",
        "Montserrat College of Art",
        "Delaware College of Art and Design",
        "Lyme Academy College of Fine Arts",
        "New Hampshire Institute of Art",
        "Milwaukee Institute of Art and Design",
        "Ringling College of Art and Design",
        "California Institute of Integral Studies",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.46.22 entity group drifted")
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
GATES = copy.deepcopy(frozen.GATES)
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *frozen.SOURCE_FILES,
            "scripts/finalize_v24621_v24620_collector_failure.py",
            "tests/test_finalize_v24621_v24620_collector_failure.py",
            str(PREVIOUS_FAILURE),
            str(PARENT),
            RUNNER_MARKER,
            "tests/test_v24622_collector_lifetime_external_gate.py",
        )
    )
)
BUILD_AUDIT_SOURCE_FILES = (
    "scripts/finalize_v24621_v24620_collector_failure.py",
    "tests/test_finalize_v24621_v24620_collector_failure.py",
    str(PREVIOUS_FAILURE),
    str(PARENT),
    RUNNER_MARKER,
    "tests/test_v24622_collector_lifetime_external_gate.py",
    "scripts/audit_v24623_collector_lifetime_build.py",
    "tests/test_audit_v24623_collector_lifetime_build.py",
)
TEST_SUITES = (
    *frozen.TEST_SUITES,
    ("tests/test_finalize_v24621_v24620_collector_failure.py", 7, 180),
    ("tests/test_v24622_collector_lifetime_external_gate.py", 20, 600),
)
EXPECTED_TEST_COUNT = frozen.EXPECTED_TEST_COUNT + 27


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.22 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validated_build_audit() -> dict[str, Any]:
    value = _read(BUILD_AUDIT)
    manifest = value.get("source_manifest", {})
    git = value.get("git", {})
    authorization = value.get("authorization", {})
    runtime_state = value.get("runtime_state", {})
    tests = value.get("tests", {})
    repair = value.get("collector_lifetime_repair", {})
    expected = set(BUILD_AUDIT_SOURCE_FILES)
    if (
        value.get("role") != "v24623_collector_lifetime_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or authorization.get("v24622_protocol_publication") is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or tests.get("passed") is not True
        or tests.get("test_count") != 35
        or tests.get("network_model_search_fetch_or_evaluator_called") is not False
        or repair.get("policy") != collector.POLICY_ID
        or repair.get("collector_enters_before_task_futures") is not True
        or repair.get("collector_remains_active_through_main_aggregate") is not True
        or repair.get("collector_exits_after_aggregate_or_exception") is not True
        or repair.get("design_valid") is not True
        or runtime_state.get("benchmark_launched") is not False
        or runtime_state.get("external_population_launched_by_audit") is not False
        or runtime_state.get("evaluator_called") is not False
        or runtime_state.get("shared_api_lease_inactive") is not True
        or runtime_state.get("future_surface_pristine") is not True
        or git.get("head") != git.get("target_main")
        or git.get("head_equals_target_main") is not True
        or git.get("worktree_clean") is not True
        or git.get("all_sources_tracked") is not True
        or not isinstance(manifest, dict)
        or set(manifest) != expected
        or any(sha256(ROOT / path) != manifest.get(path) for path in expected)
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.23 build audit drifted")
    return value


def _build_audit_binding() -> dict[str, Any]:
    value = _validated_build_audit()
    return {
        "path": str(BUILD_AUDIT),
        "sha256": sha256(ROOT / BUILD_AUDIT),
        "role": value["role"],
        "audited_source_commit": value["git"]["head"],
        "protocol_publication_authorized": True,
        "fresh_external_activation_or_launch_authorized": False,
    }


def _previous_closed() -> bool:
    failure = _read(PREVIOUS_FAILURE)
    audited = _read(PARENT)
    failure_unsigned = dict(failure)
    failure_seal = failure_unsigned.pop("failure_payload_sha256", None)
    audit_unsigned = dict(audited)
    audit_seal = audit_unsigned.pop("audit_payload_sha256", None)
    return (
        failure_seal == payload_sha256(failure_unsigned)
        and audit_seal == payload_sha256(audit_unsigned)
        and audited.get("failure_sha256") == sha256(ROOT / PREVIOUS_FAILURE)
        and failure.get("status")
        == "terminal_posttask_collector_context_failure_no_result"
        and failure.get("external_population_consumed") is True
        and failure.get("external_wave_count") == 1
        and failure.get("result_created") is False
        and failure.get("failure_class")
        == "instance_local_title_provenance_collector_context_absent"
        and failure.get("preworker_controller_deadlock_recurred") is False
        and failure.get(
            "same_population_resume_retry_skip_selective_rerun_or_evaluation_authorized"
        )
        is False
        and audited.get("audit_valid") is True
        and audited.get("findings") == []
        and audited.get("failure_status")
        == "terminal_posttask_collector_context_failure_no_result"
        and audited.get("shared_api_lease_active") is False
        and audited.get("v24620_runner_present") is False
        and audited.get("v24620_result_decision_or_postaudit_present") is False
    )


def _parent(root: Path) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve() or not _previous_closed():
        raise RuntimeError("V2.46.22 terminal parent drifted")
    return _read(PARENT)


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
    primary_surfaces: list[str] = []
    for entities in ENTITY_GROUPS:
        baseline = (
            "```markdown\n| University | Founding year |\n| --- | --- |\n"
            + "\n".join(f"| {entity} | Unknown |" for entity in entities)
            + "\n```"
        )
        cells = controller._baseline_cells(baseline)
        for entity in entities:
            primary = acquisition.primary_alias_surface(entity)
            full, second, _mode = query_policy._surface_vector(entity)
            exact = alias_projection.title._unique_title_row(f"{full} history", cells)
            alias = alias_projection.unique_alias_title_row(f"{second} history", cells)
            queries = query_policy.validator_aligned_query_vector(entity, "Founding year")
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
            primary_surfaces.append(primary.casefold())
    return len(primary_surfaces) == 64 and len(set(primary_surfaces)) == 64


def _alias_surface_vector_valid() -> bool:
    return _title_query_surface_vector_valid()


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_508_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_primary_alias_surfaces_globally_unique": _title_query_surface_vector_valid(),
        "all_64_full_surfaces_uniquely_reachable_by_unchanged_exact_title_parent": _title_query_surface_vector_valid(),
        "all_64_second_surfaces_uniquely_reachable_by_unchanged_alias_title_validator": _title_query_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_populations_through_v24620_counted_as_consumed": True,
        "prior_population_resume_retry_rerun_or_evaluation": False,
        "population_selection_uses_visible_names_and_frozen_validator_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_collector_lifetime_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_collector_lifetime_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def _successor_binding() -> dict[str, Any]:
    if not _previous_closed() or not collector.binding_valid():
        raise RuntimeError("V2.46.22 predecessor or collector binding drifted")
    return {
        "parent_postfailure_audit_path": str(PARENT),
        "parent_postfailure_audit_sha256": sha256(ROOT / PARENT),
        "v24620_failure_path": str(PREVIOUS_FAILURE),
        "v24620_failure_sha256": sha256(ROOT / PREVIOUS_FAILURE),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "same_or_prior_population_resume_retry_rerun_or_evaluation": False,
        "new_population_reuses_prior_question_or_entity": False,
        "collector_policy": collector.POLICY_ID,
        "collector_context_enters_before_task_futures": True,
        "collector_context_remains_active_through_main_aggregate": True,
        "collector_context_exits_after_aggregate": True,
        "runtime_fast_control_validator_unchanged": True,
        "enforcing_batch_watchdog_unchanged": True,
        "concurrent_controller_binding_unchanged": True,
        "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
        "query_ranking_title_validator_or_evidence_projection_changed": False,
        "source_posterior_margin_leave_one_out_safe_change_or_decision_credit_rules_relaxed": False,
        "raw_task_query_url_title_page_prediction_or_provider_payload_emitted": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


mechanism_passed = frozen.mechanism_passed
diagnostic_route = frozen.diagnostic_route


@contextmanager
def configured_frozen(
    *, validators: bool = False, validator_names: Sequence[str] = ()
) -> Iterator[None]:
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
        "_title_query_surface_vector_valid": _title_query_surface_vector_valid,
        "_alias_surface_vector_valid": _alias_surface_vector_valid,
        "_parent": _parent,
        "_previous_closed": _previous_closed,
        "_task_contract": _task_contract,
        "_protocol_authorization": _protocol_authorization,
        "_activation_authorization": _activation_authorization,
        "_successor_binding": _successor_binding,
        "mechanism_passed": mechanism_passed,
        "diagnostic_route": diagnostic_route,
    }
    available = {
        "validate_protocol": validate_protocol,
        "validate_preaudit": validate_preaudit,
        "validate_activation": validate_activation,
        "validate_execution_start": validate_execution_start,
        "validate_public_result": validate_public_result,
        "validate_runtime_protocol": validate_runtime_protocol,
    }
    names = tuple(available) if validators else tuple(validator_names)
    if any(name not in available for name in names):
        raise ValueError("V2.46.22 unknown validator binding")
    for name in names:
        patches[name] = available[name]
    originals = {name: getattr(frozen, name, _MISSING) for name in patches}
    try:
        for name, value in patches.items():
            setattr(frozen, name, value)
        yield
    finally:
        for name, value in originals.items():
            if value is _MISSING:
                delattr(frozen, name)
            else:
                setattr(frozen, name, value)


_MECHANISM_FIELDS = (
    "collector_lifetime_repair_policy",
    "collector_context_enters_before_task_futures",
    "collector_context_remains_active_through_main_aggregate",
    "collector_context_exits_after_aggregate",
    "v24620_same_population_retry_resume_rerun_or_evaluation",
)


def build_protocol(
    *,
    now: int | None = None,
    require_pristine: bool = True,
    require_build_audit: bool = True,
) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.46.22 predecessor is not closed")
    build_audit = _build_audit_binding() if require_build_audit else None
    with configured_frozen():
        value = _BASE_BUILD_PROTOCOL(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["scope"] = "fresh_title_provenance_collector_lifetime_gate"
    if build_audit is not None:
        value["build_audit"] = build_audit
    value["mechanism"].update(
        {
            "collector_lifetime_repair_policy": collector.POLICY_ID,
            "collector_context_enters_before_task_futures": True,
            "collector_context_remains_active_through_main_aggregate": True,
            "collector_context_exits_after_aggregate": True,
            "v24620_same_population_retry_resume_rerun_or_evaluation": False,
        }
    )
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(value=value, require_build_audit=require_build_audit)


def validate_protocol(
    root: Path = ROOT,
    *,
    value: Mapping[str, Any] | None = None,
    require_build_audit: bool = True,
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.22 protocol root drifted")
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core.pop("build_audit", None)
    core["scope"] = "fresh_title_provenance_fast_validation_watchdog_gate"
    for name in _MECHANISM_FIELDS:
        core.get("mechanism", {}).pop(name, None)
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_frozen():
        _BASE_VALIDATE_PROTOCOL(value=core)
    mechanism = copied.get("mechanism", {})
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope") != "fresh_title_provenance_collector_lifetime_gate"
        or (
            copied.get("build_audit") != _build_audit_binding()
            if require_build_audit
            else "build_audit" in copied
        )
        or copied.get("parent") != {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}
        or copied.get("successor_binding") != _successor_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("collector_lifetime_repair_policy") != collector.POLICY_ID
        or mechanism.get("collector_context_enters_before_task_futures") is not True
        or mechanism.get("collector_context_remains_active_through_main_aggregate")
        is not True
        or mechanism.get("collector_context_exits_after_aggregate") is not True
        or mechanism.get("v24620_same_population_retry_resume_rerun_or_evaluation")
        is not False
        or mechanism.get("runtime_fast_control_validator") is not True
        or mechanism.get("runtime_complete_protocol_revalidation") is not False
        or mechanism.get("maximum_batch_wall_is_enforcing_watchdog") is not True
        or copied.get("authorization") != _protocol_authorization()
        or not collector.binding_valid()
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.46.22 protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_frozen(validator_names=("validate_protocol",)):
        value = _BASE_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_500_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_500_and_4000",
        "v24616_population_resume_retry_rerun_or_evaluation",
        "v24617_terminal_failure_and_postaudit_closed",
        "v24619_concurrent_binding_repair_audit_validated",
        "v24618_shared_mode_runtime_binding_validated",
    ):
        checks.pop(name, None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_508_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_508_and_4064"] = True
    checks["v24620_population_resume_retry_rerun_or_evaluation"] = False
    checks["v24621_terminal_failure_and_postaudit_closed"] = True
    checks["v24610_collector_context_covers_task_and_aggregate_lifetime"] = True
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.22 preaudit root drifted")
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks", {})
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_508_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_508_and_4064",
        "v24620_population_resume_retry_rerun_or_evaluation",
        "v24621_terminal_failure_and_postaudit_closed",
        "v24610_collector_context_covers_task_and_aggregate_lifetime",
    ):
        core_checks.pop(name, None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_500_consumed_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_500_and_4000"] = True
    core_checks["v24616_population_resume_retry_rerun_or_evaluation"] = False
    core_checks["v24617_terminal_failure_and_postaudit_closed"] = True
    core_checks["v24619_concurrent_binding_repair_audit_validated"] = True
    core_checks["v24618_shared_mode_runtime_binding_validated"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_frozen(validators=True):
        _BASE_VALIDATE_PREAUDIT(value=core)
    required_true = (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_508_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_508_and_4064",
        "v24621_terminal_failure_and_postaudit_closed",
        "v24610_collector_context_covers_task_and_aggregate_lifetime",
        "runtime_fast_control_receipt_replaces_per_task_complete_protocol_validation",
        "maximum_batch_wall_is_enforcing_descendant_process_group_watchdog",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("launch_authorized") is not True
        or any(checks.get(name) is not True for name in required_true)
        or checks.get("v24620_population_resume_retry_rerun_or_evaluation") is not False
        or checks.get("focused_tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or checks.get("focused_tests", {}).get("passed") is not True
        or copied.get("authorization") != _activation_authorization()
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.22 preaudit drifted")
    return copied


_ALL_VALIDATORS = frozen._ALL_VALIDATORS


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    validate_preaudit()
    with configured_frozen(validators=True):
        return _BASE_BUILD_ACTIVATION(now=now)


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.22 activation root drifted")
    with configured_frozen(validators=True):
        return _BASE_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_frozen(validators=True):
        return _BASE_BUILD_EXECUTION_START(now=now)


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.22 execution-start root drifted")
    with configured_frozen(validators=True):
        return _BASE_VALIDATE_EXECUTION_START()


def _control_receipt() -> dict[str, Any]:
    with configured_frozen(validators=True):
        return frozen._control_receipt()


def validate_runtime_control_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_frozen(validators=True):
        return frozen.validate_runtime_control_receipt(value)


def validate_runtime_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve() or value is not None:
        raise RuntimeError("V2.46.22 runtime protocol contract drifted")
    validate_runtime_control_receipt(_control_receipt())
    return _read(PROTOCOL)


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_frozen(validators=True):
        return _BASE_VALIDATE_PUBLIC_RESULT(value)


@contextmanager
def configured_runtime_stack() -> Iterator[None]:
    with configured_frozen(validators=True), frozen.configured_runtime_stack():
        if base.validate_protocol is not validate_runtime_protocol:
            raise RuntimeError("V2.46.22 fast runtime validator was not propagated")
        yield


def run_probe() -> dict[str, Any]:
    protocol = validate_protocol()
    validate_preaudit()
    activation = validate_activation()
    validate_execution_start()
    control = validate_runtime_control_receipt(_control_receipt())
    with configured_runtime_stack(), collector.capability_collection():
        return _BASE_RUN_PROBE_FAST(
            protocol=protocol,
            activation=activation,
            control=control,
        )


def _decision_authorization(route: str) -> dict[str, bool]:
    return frozen._decision_authorization(route)


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
        "role": DECISION_ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_collector_lifetime_observed"
            if passed
            else "fresh_collector_lifetime_incomplete"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_collector_lifetime_measured": True,
            "collector_context_covered_task_and_aggregate_lifetime": passed,
            "provider_transport_or_quality_causality_claimed": False,
            "benchmark_quality_measured": False,
            "paired_dev64_launch_authorized": False,
            "sota_supported": False,
        },
        "authorization": _decision_authorization(route),
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return validate_decision(value=value)


def validate_decision(*, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(DECISION)
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
    expected_status = (
        "fresh_collector_lifetime_observed"
        if passed
        else "fresh_collector_lifetime_incomplete"
    )
    claim = copied.get("claim_scope", {})
    if (
        copied.get("role") != DECISION_ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or claim.get("fresh_nonbenchmark_collector_lifetime_measured") is not True
        or claim.get("collector_context_covered_task_and_aggregate_lifetime")
        is not passed
        or claim.get("provider_transport_or_quality_causality_claimed") is not False
        or claim.get("benchmark_quality_measured") is not False
        or claim.get("paired_dev64_launch_authorized") is not False
        or claim.get("sota_supported") is not False
        or copied.get("authorization") != _decision_authorization(route)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.46.22 decision drifted")
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
    if not binding.invariant_valid():
        findings.append("v24618_runtime_binding_drifted")
    if not collector.binding_valid():
        findings.append("v24610_collector_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": POSTAUDIT_ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "decision_sha256": sha256(ROOT / DECISION),
        "decision_status": decision["status"],
        "diagnostic_route": decision["diagnostic_route"],
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "controller_binding_invariant_valid": binding.invariant_valid(),
        "collector_binding_valid_after_context_exit": collector.binding_valid(),
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "private_task_query_url_title_page_prediction_or_provider_payload_persisted": False,
        "opaque_capability_references_destroyed_after_aggregation": True,
        "inherited_original_task_projection_rebound": False,
        "provider_transport_or_quality_causality_claimed": False,
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
        copied.get("role") != POSTAUDIT_ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status") != decision["status"]
        or copied.get("diagnostic_route") != decision["diagnostic_route"]
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != base.protected_watcher_snapshot()
        or copied.get("controller_binding_invariant_valid") is not True
        or copied.get("collector_binding_valid_after_context_exit") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or copied.get(
            "private_task_query_url_title_page_prediction_or_provider_payload_persisted"
        )
        is not False
        or copied.get("opaque_capability_references_destroyed_after_aggregation")
        is not True
        or copied.get("inherited_original_task_projection_rebound") is not False
        or copied.get("provider_transport_or_quality_causality_claimed") is not False
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not binding.invariant_valid()
        or not collector.binding_valid()
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.22 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_runtime_stack():
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
