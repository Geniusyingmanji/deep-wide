#!/usr/bin/env python3
"""Fresh title-provenance probe with fast validation and a hard watchdog.

V2.46.16 consumed its unique population while eight task threads deadlocked
before parent launch.  V2.46.18 repairs the shared controller binding.  This
successor uses a new literal/canonical-disjoint 8-task population after 500
questions / 4,000 entities, validates the complete protocol once before the
wave, and gives each task only a frozen control-chain receipt.

The inherited 255-second batch ceiling is enforced by a content-free
descendant-process-group watchdog.  Runtime input remains exactly
``opaque_id`` and ``question``.  No query/search/fetch/model budget, title
validator, evidence, entropy, credit, evaluator, or benchmark rule changes.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import math
import sys
import tempfile
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent import v24607_proof_carrying_title_provenance as proof  # noqa: E402
from deepwide_agent import v24608_total_title_provenance_projection as total  # noqa: E402
from deepwide_agent import v24609_bounded_title_provenance_parent as bounded  # noqa: E402
from deepwide_agent import v24618_concurrent_controller_binding as binding  # noqa: E402
from deepwide_agent import v24620_enforcing_batch_watchdog as watchdog  # noqa: E402
from scripts import v24610_title_provenance_collector as collector  # noqa: E402
from scripts import v24616_repaired_title_provenance_external_gate as frozen  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24620_fresh_title_provenance_watchdog_external_gate_v1"
PROTOCOL = Path(
    f"results/v24620_title_provenance_watchdog_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24620_title_provenance_watchdog_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24620_title_provenance_watchdog_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24620_title_provenance_watchdog_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24620_title_provenance_watchdog_external_result_v1_{DATE}.json"
)
DECISION = Path(
    f"results/v24620_title_provenance_watchdog_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24620_title_provenance_watchdog_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path("results/v24619_concurrent_binding_repair_audit_v1_20260805.json")
RUNNER_MARKER = "scripts/v24620_title_provenance_watchdog_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_title_provenance_watchdog_external_gate"
PRIOR_QUESTION_COUNT = 500
PRIOR_ENTITY_COUNT = 4000
PRIOR_QUESTIONS = frozen._prior_questions() + frozen.QUESTIONS
SELECTED = 8
EXECUTOR_COUNT = 8
MODEL_SLOT_CAP = 2
BATCH_WALL_CEILING_SECONDS = 255.0

controller = frozen.controller
runtime = frozen.runtime
base = frozen.base
population = frozen.population
query_policy = frozen.query_policy
alias_projection = frozen.alias_projection
acquisition = frozen.acquisition
STRICT_TASK_FIELD = frozen.STRICT_TASK_FIELD
_INHERITED_ORIGINAL_TASK_PROJECTION = runtime._ORIGINAL_TASK_PROJECTION
_MISSING = object()

_BASE_BUILD_PROTOCOL = frozen._BASE_BUILD_PROTOCOL
_BASE_VALIDATE_PROTOCOL = frozen._BASE_VALIDATE_PROTOCOL
_BASE_BUILD_PREAUDIT = frozen._BASE_BUILD_PREAUDIT
_BASE_VALIDATE_PREAUDIT = frozen._BASE_VALIDATE_PREAUDIT
_BASE_BUILD_ACTIVATION = frozen._BASE_BUILD_ACTIVATION
_BASE_VALIDATE_ACTIVATION = frozen._BASE_VALIDATE_ACTIVATION
_BASE_BUILD_EXECUTION_START = frozen._BASE_BUILD_EXECUTION_START
_BASE_VALIDATE_EXECUTION_START = frozen._BASE_VALIDATE_EXECUTION_START
_BASE_VALIDATE_PUBLIC_RESULT = frozen._BASE_VALIDATE_PUBLIC_RESULT
_BASE_RUN_PROBE = frozen._BASE_RUN_PROBE
_BASE_RUN_PROCESS_SUBCOMMAND = frozen._BASE_RUN_PROCESS_SUBCOMMAND


ENTITY_GROUPS = (
    (
        "Franklin W Olin College of Engineering",
        "Cooper Union for the Advancement of Science and Art",
        "Pennsylvania Academy of the Fine Arts",
        "Cleveland Institute of Art",
        "Columbus College of Art and Design",
        "Kansas City Art Institute",
        "Rocky Mountain College of Art and Design",
        "Laguna College of Art and Design",
    ),
    (
        "Southern California College of Optometry",
        "Illinois College of Optometry",
        "Pennsylvania College of Optometry",
        "Palmer College of Chiropractic",
        "Logan University College of Chiropractic",
        "National University of Health Sciences",
        "University of Western States",
        "Lake Erie College of Osteopathic Medicine",
    ),
    (
        "Edward Via College of Osteopathic Medicine",
        "Philadelphia College of Osteopathic Medicine",
        "Kansas City University of Medicine and Biosciences",
        "A T Still University of Health Sciences",
        "Rocky Vista University",
        "Ponce Health Sciences University",
        "Massachusetts College of Pharmacy and Health Sciences",
        "New York College of Podiatric Medicine",
    ),
    (
        "College of the Muscogee Nation",
        "Institute of American Indian Arts",
        "Salish Kootenai College",
        "Sitting Bull College",
        "Stone Child College",
        "Turtle Mountain Community College",
        "Little Big Horn College",
        "Blackfeet Community College",
    ),
    (
        "Aaniiih Nakoda College",
        "Nueta Hidatsa Sahnish College",
        "Saginaw Chippewa Tribal College",
        "Keweenaw Bay Ojibwa Community College",
        "Tohono Oodham Community College",
        "Northwest Indian College",
        "Haskell Indian Nations University",
        "United Tribes Technical College",
    ),
    (
        "Southwestern Indian Polytechnic Institute",
        "Pontifical College Josephinum",
        "Byzantine Catholic Seminary of Saints Cyril and Methodius",
        "Saint Meinrad Seminary and School of Theology",
        "Conception Seminary College",
        "Kenrick Glennon Seminary",
        "Mount Angel Seminary",
        "Notre Dame Seminary Graduate School of Theology",
    ),
    (
        "Jewish Theological Seminary of America",
        "Reconstructionist Rabbinical College",
        "Hebrew Union College Jewish Institute of Religion",
        "Buddhist Tzu Chi University",
        "Maharishi International University",
        "Soka University of America",
        "International Institute for Restorative Practices",
        "Middlebury Institute of International Studies at Monterey",
    ),
    (
        "Art Center College of Design",
        "Fashion Institute of Design and Merchandising",
        "New York School of Interior Design",
        "Boston Architectural College",
        "Southern California Institute of Architecture",
        "New School of Architecture and Design",
        "University of Science and Arts of Oklahoma",
        "Missouri University of Science and Technology",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.46.20 entity group drifted")
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
            "results/v24617_v24616_terminal_deadlock_failure_v1_20260805.json",
            "results/v24617_v24616_postfailure_audit_v1_20260805.json",
            "src/deepwide_agent/v24618_concurrent_controller_binding.py",
            "tests/test_v24618_concurrent_controller_binding.py",
            "scripts/audit_v24619_concurrent_binding_repair.py",
            "tests/test_audit_v24619_concurrent_binding_repair.py",
            str(PARENT),
            "src/deepwide_agent/v24620_enforcing_batch_watchdog.py",
            "tests/test_v24620_enforcing_batch_watchdog.py",
            RUNNER_MARKER,
            "tests/test_v24620_title_provenance_watchdog_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *frozen.TEST_SUITES,
    ("tests/test_v24618_concurrent_controller_binding.py", 8, 180),
    ("tests/test_audit_v24619_concurrent_binding_repair.py", 9, 180),
    ("tests/test_v24620_enforcing_batch_watchdog.py", 9, 180),
    ("tests/test_v24620_title_provenance_watchdog_external_gate.py", 20, 600),
)
EXPECTED_TEST_COUNT = frozen.EXPECTED_TEST_COUNT + 46


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.20 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    baseline = value.get("freshness_baseline", {})
    repair = value.get("binding_repair", {})
    deadline = value.get("batch_deadline_diagnosis", {})
    if (
        value.get("role") != "v24619_concurrent_binding_repair_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 44
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or baseline.get("prior_external_question_count") != PRIOR_QUESTION_COUNT
        or baseline.get("prior_external_entity_count") != PRIOR_ENTITY_COUNT
        or baseline.get("v24616_population_resume_retry_rerun_or_evaluation_authorized")
        is not False
        or repair.get("policy_id") != binding.POLICY_ID
        or repair.get("binding_idle_after_tests") is not True
        or repair.get("eight_runtime_holders_overlap") is not True
        or repair.get("real_proof_total_bounded_modules_mutated") is not False
        or deadline.get("declared_batch_wall_is_enforcing_watchdog") is not False
        or authorization.get(
            "fresh_disjoint_content_free_title_provenance_successor_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or authorization.get("evaluator_access_authorized") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.20 parent audit drifted")
    return value


def _previous_closed() -> bool:
    value = _parent(ROOT)
    closed = value.get("closed_parent", {})
    return (
        closed.get("valid") is True
        and closed.get("v24616_population_consumed") is True
        and closed.get("v24616_population_resume_retry_rerun_or_evaluation_authorized")
        is False
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
        "selected": SELECTED,
        "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_500_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_primary_alias_surfaces_globally_unique": _title_query_surface_vector_valid(),
        "all_64_full_surfaces_uniquely_reachable_by_unchanged_exact_title_parent": _title_query_surface_vector_valid(),
        "all_64_second_surfaces_uniquely_reachable_by_unchanged_alias_title_validator": _title_query_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_populations_through_v24616_counted_as_consumed": True,
        "prior_population_resume_retry_rerun_or_evaluation": False,
        "population_selection_uses_visible_names_and_frozen_validator_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_title_provenance_watchdog_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_title_provenance_watchdog_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def _successor_binding() -> dict[str, Any]:
    if not _previous_closed() or not binding.invariant_valid():
        raise RuntimeError("V2.46.20 predecessor or binding drifted")
    return {
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "same_or_prior_population_resume_retry_rerun_or_evaluation": False,
        "new_population_reuses_prior_question_or_entity": False,
        "controller_binding_policy": binding.POLICY_ID,
        "protocol_view_proof_policy": binding.frozen.protocol_proof.POLICY_ID,
        "runtime_view_proof_policy": proof.POLICY_ID,
        "runtime_view_total_policy": total.POLICY_ID,
        "runtime_view_bounded_policy": bounded.POLICY_ID,
        "runtime_view_collector_policy": collector.POLICY_ID,
        "protocol_view_rebinds_controller_only": True,
        "runtime_view_rebinds_controller_only": True,
        "same_mode_concurrent_holders_share_binding": True,
        "runtime_task_uses_frozen_control_chain_receipt_only": True,
        "runtime_task_performs_complete_protocol_validation": False,
        "batch_watchdog_policy": watchdog.POLICY_ID,
        "batch_wall_ceiling_is_enforcing_watchdog": True,
        "v24607_parent_proof_module_mutated": False,
        "v24607_parent_validator_mutated": False,
        "v24609_frozen_proof_or_total_binding_mutated": False,
        "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
        "query_ranking_title_validator_or_evidence_projection_changed": False,
        "source_posterior_margin_leave_one_out_safe_change_or_decision_credit_rules_relaxed": False,
        "raw_task_query_url_title_page_prediction_or_provider_payload_emitted": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


mechanism_passed = frozen.mechanism_passed
diagnostic_route = frozen.diagnostic_route


@contextmanager
def configured_controller(
    *,
    protocol_compatibility: bool,
    validator_names: Sequence[str] = (),
    runtime_fast_protocol: bool = False,
) -> Iterator[None]:
    if runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION:
        raise RuntimeError("V2.46.20 inherited original projector drifted")
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
        "_quarantine_valid": _previous_closed,
        "_task_contract": _task_contract,
        "_protocol_authorization": _protocol_authorization,
        "_activation_authorization": _activation_authorization,
        "_successor_binding": _successor_binding,
        "mechanism_passed": mechanism_passed,
        "diagnostic_route": diagnostic_route,
    }
    validators = {
        "validate_protocol": (
            validate_runtime_protocol if runtime_fast_protocol else validate_protocol
        ),
        "validate_preaudit": validate_preaudit,
        "validate_activation": validate_activation,
        "validate_execution_start": validate_execution_start,
        "validate_public_result": validate_public_result,
    }
    for name in validator_names:
        patches[name] = validators[name]
    originals = {name: getattr(controller, name, _MISSING) for name in patches}
    runtime_patches: dict[str, Any] = {}
    if not protocol_compatibility:
        runtime_patches = {
            "proof": proof,
            "total": total,
            "bounded": bounded,
            "capability_collection": collector.capability_collection,
            "aggregate_strict_projections": collector.aggregate_projections,
            "mechanism_passed": mechanism_passed,
            "diagnostic_route": diagnostic_route,
        }
    runtime_originals = {
        name: getattr(runtime, name, _MISSING) for name in runtime_patches
    }
    task_field_original = getattr(total, "TASK_FIELD", _MISSING)
    try:
        for name, value in patches.items():
            setattr(controller, name, value)
        for name, value in runtime_patches.items():
            setattr(runtime, name, value)
        if not protocol_compatibility:
            total.TASK_FIELD = STRICT_TASK_FIELD
        with binding.controller_bindings(
            controller, protocol_compatibility=protocol_compatibility
        ):
            yield
    finally:
        if not protocol_compatibility:
            if task_field_original is _MISSING:
                delattr(total, "TASK_FIELD")
            else:
                total.TASK_FIELD = task_field_original
        for name, value in runtime_originals.items():
            if value is _MISSING:
                delattr(runtime, name)
            else:
                setattr(runtime, name, value)
        for name, value in originals.items():
            if value is _MISSING:
                delattr(controller, name)
            else:
                setattr(controller, name, value)
        if not binding.invariant_valid():
            raise RuntimeError("V2.46.20 controller exit contaminated runtime proof")


_PROVENANCE_MECHANISM_FIELDS = frozen._PROVENANCE_MECHANISM_FIELDS
_V24620_MECHANISM_FIELDS = (
    "concurrent_controller_binding_policy",
    "same_mode_concurrent_holders_share_binding",
    "runtime_fast_control_validator",
    "runtime_complete_protocol_revalidation",
    "enforcing_batch_watchdog_policy",
    "maximum_batch_wall_is_enforcing_watchdog",
)


def build_protocol(
    *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.46.20 predecessor is not closed")
    _parent(ROOT)
    with configured_controller(protocol_compatibility=True):
        value = _BASE_BUILD_PROTOCOL(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["scope"] = "fresh_title_provenance_fast_validation_watchdog_gate"
    value["mechanism"].update(
        {
            "targeted_proof_policy": proof.POLICY_ID,
            "targeted_parent_policy": bounded.POLICY_ID,
            "content_free_title_provenance_observer_policy": proof.provenance_policy.POLICY_ID,
            "proof_carrying_content_free_title_provenance_policy": proof.POLICY_ID,
            "total_content_free_title_provenance_projection_policy": total.POLICY_ID,
            "bounded_content_free_title_provenance_parent_policy": bounded.POLICY_ID,
            "immutable_title_provenance_collector_policy": collector.POLICY_ID,
            "collector_projector_is_module_load_unbound_v24608_function": True,
            "controller_binding_policy": binding.POLICY_ID,
            "concurrent_controller_binding_policy": binding.POLICY_ID,
            "protocol_view_rebinds_controller_only": True,
            "runtime_view_rebinds_controller_only": True,
            "same_mode_concurrent_holders_share_binding": True,
            "runtime_fast_control_validator": True,
            "runtime_complete_protocol_revalidation": False,
            "enforcing_batch_watchdog_policy": watchdog.POLICY_ID,
            "maximum_batch_wall_is_enforcing_watchdog": True,
            "v24607_parent_proof_module_mutated": False,
            "v24607_parent_validator_mutated": False,
            "v24609_frozen_proof_or_total_binding_mutated": False,
            "action_source_title_count_observed": True,
            "query_local_citation_title_count_observed": True,
            "effective_fetch_request_title_count_observed": True,
            "fetched_result_title_count_observed": True,
            "same_url_action_citation_alignment_in_memory_only": True,
            "title_provenance_claims_provider_transport_or_quality_causality": False,
            "raw_task_query_url_title_page_prediction_or_provider_payload_emitted": False,
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
        raise RuntimeError("V2.46.20 protocol root drifted")
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_content_free_title_funnel_external_gate"
    for name in (*_PROVENANCE_MECHANISM_FIELDS, *_V24620_MECHANISM_FIELDS):
        core.get("mechanism", {}).pop(name, None)
    core["mechanism"]["targeted_proof_policy"] = binding.frozen.protocol_proof.POLICY_ID
    core["mechanism"]["targeted_parent_policy"] = binding.frozen.protocol_bounded.POLICY_ID
    core["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "protocol_payload_sha256"}
    )
    with configured_controller(protocol_compatibility=True):
        _BASE_VALIDATE_PROTOCOL(value=core)
    mechanism = copied.get("mechanism", {})
    budget = copied.get("budget", {})
    provider = copied.get("provider", {})
    required_true = (
        "collector_projector_is_module_load_unbound_v24608_function",
        "protocol_view_rebinds_controller_only",
        "runtime_view_rebinds_controller_only",
        "same_mode_concurrent_holders_share_binding",
        "runtime_fast_control_validator",
        "maximum_batch_wall_is_enforcing_watchdog",
        "action_source_title_count_observed",
        "query_local_citation_title_count_observed",
        "effective_fetch_request_title_count_observed",
        "fetched_result_title_count_observed",
        "same_url_action_citation_alignment_in_memory_only",
    )
    required_false = (
        "runtime_complete_protocol_revalidation",
        "v24607_parent_proof_module_mutated",
        "v24607_parent_validator_mutated",
        "v24609_frozen_proof_or_total_binding_mutated",
        "title_provenance_claims_provider_transport_or_quality_causality",
        "raw_task_query_url_title_page_prediction_or_provider_payload_emitted",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_title_provenance_fast_validation_watchdog_gate"
        or copied.get("parent") != {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}
        or copied.get("successor_binding") != _successor_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or mechanism.get("targeted_proof_policy") != proof.POLICY_ID
        or mechanism.get("targeted_parent_policy") != bounded.POLICY_ID
        or mechanism.get("content_free_title_provenance_observer_policy")
        != proof.provenance_policy.POLICY_ID
        or mechanism.get("proof_carrying_content_free_title_provenance_policy")
        != proof.POLICY_ID
        or mechanism.get("total_content_free_title_provenance_projection_policy")
        != total.POLICY_ID
        or mechanism.get("bounded_content_free_title_provenance_parent_policy")
        != bounded.POLICY_ID
        or mechanism.get("immutable_title_provenance_collector_policy")
        != collector.POLICY_ID
        or mechanism.get("controller_binding_policy") != binding.POLICY_ID
        or mechanism.get("concurrent_controller_binding_policy") != binding.POLICY_ID
        or mechanism.get("enforcing_batch_watchdog_policy") != watchdog.POLICY_ID
        or any(mechanism.get(name) is not True for name in required_true)
        or any(mechanism.get(name) is not False for name in required_false)
        or provider.get("executor_count") != EXECUTOR_COUNT
        or provider.get("model_slot_cap") != MODEL_SLOT_CAP
        or budget.get("effect_deadline_seconds") != 150.0
        or budget.get("worker_timeout_seconds") != 220.0
        or budget.get("parent_timeout_seconds") != 245.0
        or budget.get("maximum_batch_wall_seconds") != BATCH_WALL_CEILING_SECONDS
        or budget.get("maximum_targeted_search_batches_per_task") != 1
        or budget.get("maximum_targeted_logical_queries_per_task") != 2
        or budget.get("maximum_targeted_fetches_per_task") != 3
        or copied.get("authorization") != _protocol_authorization()
        or not binding.invariant_valid()
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.46.20 protocol drifted")
    return copied


def _control_receipt() -> dict[str, Any]:
    protocol = _read(PROTOCOL)
    preaudit = _read(PREAUDIT)
    activation = _read(ACTIVATION)
    start = _read(EXECUTION_START)
    return {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "surface_manifest_sha256": protocol.get("surface_manifest_sha256"),
        "preactivation_audit_sha256": sha256(ROOT / PREAUDIT),
        "activation_sha256": sha256(ROOT / ACTIVATION),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "selected": start.get("selected"),
        "executor_count": start.get("executor_count"),
        "model_slot_cap": start.get("model_slot_cap"),
        "runtime_input_keys": ["opaque_id", "question"],
        "activation_launch_authorized": activation.get("launch_authorized"),
        "execution_authorized": start.get("execution_authorized"),
        "benchmark_or_evaluator_authorized": start.get(
            "benchmark_or_evaluator_authorized"
        ),
    }


def validate_runtime_control_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = _read(PROTOCOL)
    preaudit = _read(PREAUDIT)
    activation = _read(ACTIVATION)
    start = _read(EXECUTION_START)
    if (
        copied != _control_receipt()
        or copied.get("protocol_id") != PROTOCOL_ID
        or protocol.get("protocol_id") != PROTOCOL_ID
        or activation.get("protocol_id") != PROTOCOL_ID
        or start.get("protocol_id") != PROTOCOL_ID
        or not _sealed(protocol, "protocol_payload_sha256")
        or not _sealed(preaudit, "audit_payload_sha256")
        or not _sealed(activation, "activation_payload_sha256")
        or not _sealed(start, "execution_start_payload_sha256")
        or activation.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or activation.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or start.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or start.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or copied.get("surface_manifest_sha256")
        != protocol.get("surface_manifest_sha256")
        or copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or activation.get("surface_manifest_sha256")
        != protocol.get("surface_manifest_sha256")
        or copied.get("selected") != SELECTED
        or copied.get("executor_count") != EXECUTOR_COUNT
        or copied.get("model_slot_cap") != MODEL_SLOT_CAP
        or copied.get("runtime_input_keys") != ["opaque_id", "question"]
        or copied.get("activation_launch_authorized") is not True
        or copied.get("execution_authorized") is not True
        or copied.get("benchmark_or_evaluator_authorized") is not False
    ):
        raise RuntimeError("V2.46.20 runtime control receipt drifted")
    return copied


def validate_runtime_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Validate the frozen control chain without source or protocol replay."""

    if root.resolve() != ROOT.resolve() or value is not None:
        raise RuntimeError("V2.46.20 runtime protocol validator contract drifted")
    validate_runtime_control_receipt(_control_receipt())
    return _read(PROTOCOL)


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_controller(
        protocol_compatibility=True, validator_names=("validate_protocol",)
    ):
        value = _BASE_BUILD_PREAUDIT(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_476_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_476_and_3808",
        "v24596_population_resume_retry_rerun_or_evaluation",
        "v24596_result_decision_and_postaudit_closed",
        "v24603_title_funnel_build_audit_validated",
        "v24602_instance_local_immutable_collector_bound",
        "title_funnel_claims_retrieval_effect_quality_or_causality",
        "raw_title_query_url_or_page_text_emitted",
    ):
        checks.pop(name, None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_500_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_500_and_4000"] = True
    checks["v24616_population_resume_retry_rerun_or_evaluation"] = False
    checks["v24617_terminal_failure_and_postaudit_closed"] = True
    checks["v24619_concurrent_binding_repair_audit_validated"] = True
    checks["v24618_shared_mode_runtime_binding_validated"] = True
    checks["v24610_instance_local_immutable_collector_bound"] = True
    checks["four_title_provenance_boundaries_observed_counts_only"] = True
    checks["title_provenance_claims_provider_transport_or_quality_causality"] = False
    checks["raw_task_query_url_title_page_prediction_or_provider_payload_emitted"] = False
    checks["runtime_fast_control_receipt_replaces_per_task_complete_protocol_validation"] = True
    checks["maximum_batch_wall_is_enforcing_descendant_process_group_watchdog"] = True
    checks["watchdog_emits_process_identifier_or_command_line"] = False
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.20 preaudit root drifted")
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.46.20 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_500_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_500_and_4000",
        "v24616_population_resume_retry_rerun_or_evaluation",
        "v24617_terminal_failure_and_postaudit_closed",
        "v24619_concurrent_binding_repair_audit_validated",
        "v24618_shared_mode_runtime_binding_validated",
        "v24610_instance_local_immutable_collector_bound",
        "four_title_provenance_boundaries_observed_counts_only",
        "title_provenance_claims_provider_transport_or_quality_causality",
        "raw_task_query_url_title_page_prediction_or_provider_payload_emitted",
        "runtime_fast_control_receipt_replaces_per_task_complete_protocol_validation",
        "maximum_batch_wall_is_enforcing_descendant_process_group_watchdog",
        "watchdog_emits_process_identifier_or_command_line",
    ):
        core_checks.pop(name, None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_476_consumed_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_476_and_3808"] = True
    core_checks["v24596_population_resume_retry_rerun_or_evaluation"] = False
    core_checks["v24596_result_decision_and_postaudit_closed"] = True
    core_checks["v24603_title_funnel_build_audit_validated"] = True
    core_checks["v24602_instance_local_immutable_collector_bound"] = True
    core_checks["title_funnel_claims_retrieval_effect_quality_or_causality"] = False
    core_checks["raw_title_query_url_or_page_text_emitted"] = False
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_controller(
        protocol_compatibility=True, validator_names=("validate_protocol",)
    ):
        _BASE_VALIDATE_PREAUDIT(value=core)
    required_true = (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_500_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_500_and_4000",
        "v24617_terminal_failure_and_postaudit_closed",
        "v24619_concurrent_binding_repair_audit_validated",
        "v24618_shared_mode_runtime_binding_validated",
        "all_64_full_and_second_query_surfaces_validator_reachable",
        "v24610_instance_local_immutable_collector_bound",
        "four_title_provenance_boundaries_observed_counts_only",
        "runtime_fast_control_receipt_replaces_per_task_complete_protocol_validation",
        "maximum_batch_wall_is_enforcing_descendant_process_group_watchdog",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("launch_authorized") is not True
        or any(checks.get(name) is not True for name in required_true)
        or checks.get("v24616_population_resume_retry_rerun_or_evaluation") is not False
        or checks.get("watchdog_emits_process_identifier_or_command_line") is not False
        or checks.get("controller_rebinds_inherited_original_task_projection") is not False
        or checks.get("title_provenance_claims_provider_transport_or_quality_causality")
        is not False
        or checks.get("raw_task_query_url_title_page_prediction_or_provider_payload_emitted")
        is not False
        or checks.get("focused_tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or checks.get("focused_tests", {}).get("passed") is not True
        or copied.get("authorization") != _activation_authorization()
        or not binding.invariant_valid()
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.20 preactivation audit drifted")
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
    with configured_controller(
        protocol_compatibility=True, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_BUILD_ACTIVATION(now=now)


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.20 activation root drifted")
    with configured_controller(
        protocol_compatibility=True, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_controller(
        protocol_compatibility=True, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_BUILD_EXECUTION_START(now=now)


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.20 execution-start root drifted")
    with configured_controller(
        protocol_compatibility=True, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    mechanism = value.get("mechanism_aggregate")
    required = (
        "content_free_title_provenance_provider_activity_tasks",
        "content_free_title_provenance_action_nonempty_title_tasks",
        "content_free_title_provenance_citation_nonempty_title_tasks",
        "content_free_title_provenance_action_empty_citation_nonempty_tasks",
        "content_free_title_provenance_fetch_request_nonempty_title_tasks",
        "content_free_title_provenance_fetched_result_nonempty_title_tasks",
        "content_free_title_provenance_empty_request_page_title_recovery_tasks",
        "total_content_free_title_provenance_count_fields",
        "all_content_free_title_provenance_success_rows_consumed_validated_capabilities",
    )
    receipt = value.get("batch_watchdog_receipt")
    if not isinstance(mechanism, Mapping) or any(name not in mechanism for name in required):
        raise RuntimeError("V2.46.20 title-provenance aggregate schema is absent")
    if (
        not isinstance(receipt, Mapping)
        or receipt.get("policy_id") != watchdog.POLICY_ID
        or receipt.get("timeout_seconds") != BATCH_WALL_CEILING_SECONDS
        or receipt.get("started") is not True
        or receipt.get("closed") is not True
        or receipt.get("triggered") is not False
        or receipt.get("signal_failure_count") != 0
        or receipt.get("process_identifier_or_command_line_emitted") is not False
        or receipt.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("runtime_fast_control_validation_passed") is not True
        or value.get("runtime_complete_protocol_revalidation_per_task") is not False
    ):
        raise RuntimeError("V2.46.20 watchdog or fast-validator receipt drifted")
    total.validate_aggregate(mechanism)
    core = dict(value)
    core.pop("batch_watchdog_receipt", None)
    core.pop("runtime_fast_control_validation_passed", None)
    core.pop("runtime_complete_protocol_revalidation_per_task", None)
    core["result_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "result_payload_sha256"}
    )
    with configured_controller(
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
    ):
        _BASE_VALIDATE_PUBLIC_RESULT(core)
    if not _sealed(dict(value), "result_payload_sha256"):
        raise RuntimeError("V2.46.20 result seal drifted")
    return dict(value)


def _fast_run_one(
    root: Path,
    output_root: Path,
    slots: Path,
    directory: Path,
    checkpoint: Path,
    ordinal: int,
    control_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    control = validate_runtime_control_receipt(control_receipt)
    outcome = base.run_targeted_parent_with_separated_budget(
        ordinal=ordinal,
        cwd=root,
        output_root=output_root,
        directory=directory,
        checkpoint_directory=checkpoint,
        supervisor_command=[
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / RUNNER_MARKER),
            "supervisor",
            "--ordinal",
            str(ordinal),
            "--output-root",
            str(output_root),
            "--directory",
            str(directory),
            "--checkpoint-directory",
            str(checkpoint),
            "--slots",
            str(slots),
        ],
        expected_model_cap=MODEL_SLOT_CAP,
        expected_validator_manifest_sha256=str(control["surface_manifest_sha256"]),
    )
    return {
        "mechanism": outcome.proof.adaptive_projection,
        "observation": outcome.proof.observation,
        "timing": outcome.proof.timing_receipt,
        "supervision": outcome.supervision_receipt,
    }


def _run_probe_fast(
    *,
    protocol: Mapping[str, Any],
    activation: Mapping[str, Any],
    control: Mapping[str, Any],
) -> dict[str, Any]:
    root = ROOT.resolve()
    protocol = dict(protocol)
    activation = dict(activation)
    control = validate_runtime_control_receipt(control)
    if not base._future(root, (RESULT, DECISION, POSTAUDIT)) or not base._git_ready(root):
        raise RuntimeError("V2.46.20 result/git surface is not ready")
    with base.acquire_deepwide_api_lease(
        root,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=root / base.LEASE_PATH,
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            work = []
            for ordinal in range(1, SELECTED + 1):
                directory = output_root / f"task_{ordinal:02d}"
                checkpoint = output_root / f"checkpoint_{ordinal:02d}"
                directory.mkdir()
                checkpoint.mkdir()
                work.append((ordinal, directory, checkpoint))
            started = time.monotonic()
            guard = watchdog.EnforcingBatchWatchdog(
                runner_marker=RUNNER_MARKER,
                timeout_seconds=BATCH_WALL_CEILING_SECONDS,
            ).start()
            try:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=EXECUTOR_COUNT
                ) as pool:
                    futures = [
                        pool.submit(
                            _fast_run_one,
                            root,
                            output_root,
                            slots,
                            directory,
                            checkpoint,
                            ordinal,
                            control,
                        )
                        for ordinal, directory, checkpoint in work
                    ]
                    outcomes = [future.result() for future in futures]
            finally:
                guard.close()
            batch_wall = max(0.0, time.monotonic() - started)
            guard_receipt = guard.content_free_receipt()
            mechanism = base.aggregate_projections(
                [item["mechanism"] for item in outcomes], selected=SELECTED
            )
            observation = base.aggregate_observations(
                [item["observation"] for item in outcomes], selected=SELECTED
            )
            timing = base.aggregate_stage_timings(
                [item["timing"] for item in outcomes], selected=SELECTED
            )
            supervision = base.aggregate_supervision_receipts(
                [item["supervision"] for item in outcomes], selected=SELECTED
            )
        mechanism_go = base._mechanism_passed(mechanism)
        reliability = base._reliability_passed(observation, supervision)
        parent_validation = (
            timing["parent_success_tasks"] == SELECTED
            and timing["certificate_validation_invocations"] == SELECTED
            and timing["recursive_historical_semantic_replay_tasks"] == 0
            and timing["parent_certificate_validation_wall_p95_seconds"] <= 1.0
        )
        latency = (
            batch_wall <= BATCH_WALL_CEILING_SECONDS
            and supervision["worker_wall_max_seconds"] <= base.WORKER_TIMEOUT_SECONDS + 1
            and guard_receipt["triggered"] is False
        )
        value = {
            "artifact_version": 1,
            "role": "v24492_targeted_external_result",
            "protocol_id": PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": SELECTED,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
            "one_wave": True,
            "batch_wall_seconds": round(batch_wall, 6),
            "mechanism_aggregate": mechanism,
            "observation_aggregate": observation,
            "stage_timing_aggregate": timing,
            "supervision_aggregate": supervision,
            "mechanism_passed": mechanism_go,
            "reliability_passed": reliability,
            "parent_validation_passed": parent_validation,
            "latency_passed": latency,
            "passed": mechanism_go and reliability and parent_validation and latency,
            "temporary_execution_directory_remaining": False,
            "private_task_or_web_content_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "runtime_fast_control_validation_passed": True,
            "runtime_complete_protocol_revalidation_per_task": False,
            "batch_watchdog_receipt": guard_receipt,
            "provenance": {
                "protocol_sha256": sha256(root / PROTOCOL),
                "preactivation_audit_sha256": sha256(root / PREAUDIT),
                "activation_sha256": sha256(root / ACTIVATION),
                "execution_start_sha256": sha256(root / EXECUTION_START),
                "surface_manifest_sha256": protocol["surface_manifest_sha256"],
            },
        }
        value["result_payload_sha256"] = payload_sha256(value)
        validate_public_result(value)
        base.publish(root / RESULT, value)
    if base.protected_watcher_snapshot() != activation["protected_watchers"]:
        raise RuntimeError("V2.46.20 protected watcher identity drifted")
    return value


@contextmanager
def configured_runtime_stack() -> Iterator[None]:
    """Install the inherited runtime chain with only the fast validator."""

    with ExitStack() as stack:
        stack.enter_context(
            configured_controller(
                protocol_compatibility=False,
                validator_names=_ALL_VALIDATORS,
                runtime_fast_protocol=True,
            )
        )
        # V2.46.04 calls V2.45.71 directly; V2.45.96 is population history,
        # not an execution layer.  Mirror that exact call chain here.
        stack.enter_context(
            controller.configured_previous(validator_names=controller._ALL_VALIDATORS)
        )
        stack.enter_context(controller.previous.configured_predecessor(validators=True))
        stack.enter_context(runtime.configured_base(validators=True))
        if base.validate_protocol is not validate_runtime_protocol:
            raise RuntimeError("V2.46.20 fast runtime validator was not propagated")
        yield


def run_probe() -> dict[str, Any]:
    # The complete, source-manifest-aware validation is deliberately outside
    # the runtime binding.  No task thread may switch back to protocol mode.
    protocol = validate_protocol()
    validate_preaudit()
    activation = validate_activation()
    validate_execution_start()
    control = validate_runtime_control_receipt(_control_receipt())
    with configured_runtime_stack():
        return _run_probe_fast(
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
        "role": "v24620_title_provenance_watchdog_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_title_provenance_watchdog_observed"
            if passed
            else "fresh_title_provenance_watchdog_incomplete"
        ),
        "passed": passed,
        "result_sha256": sha256(ROOT / RESULT),
        "diagnostic_route": route,
        "claim_scope": {
            "fresh_nonbenchmark_title_provenance_measured": True,
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
    status = (
        "fresh_title_provenance_watchdog_observed"
        if passed
        else "fresh_title_provenance_watchdog_incomplete"
    )
    if (
        copied.get("role") != "v24620_title_provenance_watchdog_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope", {}).get(
            "provider_transport_or_quality_causality_claimed"
        )
        is not False
        or copied.get("authorization") != _decision_authorization(route)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.46.20 decision drifted")
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
    value = {
        "artifact_version": 1,
        "role": "v24620_title_provenance_watchdog_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "decision_sha256": sha256(ROOT / DECISION),
        "decision_status": decision["status"],
        "diagnostic_route": decision["diagnostic_route"],
        "shared_api_lease_active": lease_active,
        "protected_watchers": watchers,
        "controller_binding_invariant_valid": binding.invariant_valid(),
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
        copied.get("role")
        != "v24620_title_provenance_watchdog_external_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status") != decision["status"]
        or copied.get("diagnostic_route") != decision["diagnostic_route"]
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != base.protected_watcher_snapshot()
        or copied.get("controller_binding_invariant_valid") is not True
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
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.20 postresult audit drifted")
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
