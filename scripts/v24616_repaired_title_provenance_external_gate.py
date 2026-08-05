#!/usr/bin/env python3
"""Fresh title-provenance gate with non-contaminating controller views.

V2.46.12 consumed its one external population but terminated before producing
a result because its protocol-compatibility shim mutated the real V2.46.07
proof module.  V2.46.14 repairs that controller boundary.  This successor uses
a new literal/canonical-disjoint 8-task population after 492 questions / 3,936
entities, and explicitly selects the native V2.45.99 title-funnel view only for
protocol construction/validation while selecting V2.46.07--10 only for real
runtime and result validation.

Runtime input remains exactly ``opaque_id`` and ``question``.  The observer
emits only fixed-vocabulary counts for provider action titles, query-local
citations, fetch-request titles, and fetched-result titles.  It changes no
query/search/fetch/model budget, ranking, validator, evidence, posterior,
entropy, credit, or evaluator rule.  The wave is single-use and cannot be
retried, resumed, selectively rerun, or evaluated.
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
from deepwide_agent import v24607_proof_carrying_title_provenance as proof  # noqa: E402
from deepwide_agent import v24608_total_title_provenance_projection as total  # noqa: E402
from deepwide_agent import v24609_bounded_title_provenance_parent as bounded  # noqa: E402
from deepwide_agent import v24614_title_provenance_controller_binding as binding  # noqa: E402
from scripts import audit_v24615_controller_binding_repair as build_gate  # noqa: E402
from scripts import v24604_content_free_title_funnel_external_gate as controller  # noqa: E402
from scripts import v24610_title_provenance_collector as collector  # noqa: E402
from scripts import v24612_title_provenance_external_gate as consumed_run  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24616_fresh_repaired_title_provenance_external_gate_v1"
PROTOCOL = Path(
    f"results/v24616_repaired_title_provenance_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24616_repaired_title_provenance_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24616_repaired_title_provenance_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24616_repaired_title_provenance_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24616_repaired_title_provenance_external_result_v1_{DATE}.json"
)
DECISION = Path(
    f"results/v24616_repaired_title_provenance_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24616_repaired_title_provenance_external_postresult_audit_v1_{DATE}.json"
)
PARENT = build_gate.AUDIT
PREVIOUS_FAILURE = Path("results/v24613_v24612_terminal_failure_v1_20260805.json")
PREVIOUS_POSTAUDIT = Path("results/v24613_v24612_postfailure_audit_v1_20260805.json")
RUNNER_MARKER = "scripts/v24616_repaired_title_provenance_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_repaired_content_free_title_provenance_external_gate"
PRIOR_QUESTION_COUNT = 492
PRIOR_ENTITY_COUNT = 3936
PRIOR_QUESTIONS = consumed_run._prior_questions() + consumed_run.QUESTIONS

previous_run = controller.previous_run
previous = controller.previous
runtime = controller.runtime
base = controller.base
population = controller.population
query_policy = controller.query_policy
alias_projection = controller.alias_projection
acquisition = controller.acquisition
STRICT_TASK_FIELD = controller.STRICT_TASK_FIELD
_INHERITED_ORIGINAL_TASK_PROJECTION = runtime._ORIGINAL_TASK_PROJECTION
_MISSING = object()

_BASE_BUILD_PROTOCOL = controller.build_protocol
_BASE_VALIDATE_PROTOCOL = controller.validate_protocol
_BASE_BUILD_PREAUDIT = controller.build_preaudit
_BASE_VALIDATE_PREAUDIT = controller.validate_preaudit
_BASE_BUILD_ACTIVATION = controller.build_activation
_BASE_VALIDATE_ACTIVATION = controller.validate_activation
_BASE_BUILD_EXECUTION_START = controller.build_execution_start
_BASE_VALIDATE_EXECUTION_START = controller.validate_execution_start
_BASE_VALIDATE_PUBLIC_RESULT = controller.validate_public_result
_BASE_RUN_PROBE = controller.run_probe
_BASE_RUN_PROCESS_SUBCOMMAND = controller.run_process_subcommand


ENTITY_GROUPS = (
    (
        "National University of Jose C Paz",
        "National University of Moreno",
        "National University of Rafaela",
        "National University of Rio Negro",
        "National University of Tierra del Fuego",
        "National University of Villa Mercedes",
        "Provincial University of Ezeiza",
        "Federal University of Roraima",
    ),
    (
        "Federal University of Tocantins",
        "Federal University of Southern Bahia",
        "Federal University of Western Bahia",
        "Federal University of Cariri",
        "Federal University of Pampa",
        "Federal University of Fronteira Sul",
        "Federal University of Latin American Integration",
        "Federal University of Reconcavo da Bahia",
    ),
    (
        "Federal University of the Jequitinhonha and Mucuri Valleys",
        "Amazonian University of Pando",
        "Autonomous University of Beni Jose Ballivian",
        "National University Siglo XX",
        "Bolivian Indigenous Aymara University Tupak Katari",
        "Bolivian Indigenous Quechua University Casimiro Huanca",
        "National University of Tumbes",
        "National University of Jaen Peru",
    ),
    (
        "National University of Frontera Peru",
        "National University of Barranca",
        "National Intercultural University of Quillabamba",
        "National Intercultural University of the Amazon",
        "State University of Milagro",
        "State University of Bolivar Ecuador",
        "Amazon State University Ecuador",
        "Technical University of Cotopaxi",
    ),
    (
        "Technical University of Babahoyo",
        "Technical University of Manabi",
        "Technical University of the North Ecuador",
        "University of the Armed Forces ESPE",
        "University of the Amazon Colombia",
        "University of Sucre Colombia",
        "University of Cordoba Colombia",
        "University of Pamplona Colombia",
    ),
    (
        "University of Cundinamarca",
        "University of Prizren Ukshin Hoti",
        "University of Curacao Dr Moises da Costa Gomez",
        "Agricultural University of Iceland",
        "University of Applied Sciences of the Grisons",
        "University of Applied Sciences and Arts Western Switzerland",
        "University of Nova Gorica",
        "University for Information Science and Technology Saint Paul the Apostle",
    ),
    (
        "University of Mitrovica Isa Boletini",
        "University of Gjilan Kadri Zeka",
        "University of Gjakova Fehmi Agani",
        "University of Peja Haxhi Zeka",
        "Papua New Guinea University of Natural Resources and Environment",
        "Pacific Theological College",
        "Fulton Adventist University College",
        "Oceania University of Medicine",
    ),
    (
        "Vanuatu National University",
        "Tonga National University",
        "Mediterranean University of Albania",
        "University of Vlora Ismail Qemali",
        "University of Gjirokaster Eqrem Cabej",
        "University of Shkoder Luigj Gurakuqi",
        "University of Korca Fan Noli",
        "University of Elbasan Aleksander Xhuvani",
    ),
)


def _question(group: Sequence[str]) -> str:
    if len(group) != 8:
        raise ValueError("V2.46.16 entity group drifted")
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
GATES = {
    **copy.deepcopy(controller.GATES),
    "minimum_content_free_title_provenance_provider_activity_tasks": 1,
}
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *controller.SOURCE_FILES,
            str(PREVIOUS_FAILURE),
            str(PREVIOUS_POSTAUDIT),
            "scripts/finalize_v24613_v24612_title_provenance_failure.py",
            "src/deepwide_agent/v24614_title_provenance_controller_binding.py",
            "tests/test_v24614_title_provenance_controller_binding.py",
            "scripts/audit_v24615_controller_binding_repair.py",
            "tests/test_audit_v24615_controller_binding_repair.py",
            str(PARENT),
            RUNNER_MARKER,
            "tests/test_v24616_repaired_title_provenance_external_gate.py",
        )
    )
)
TEST_SUITES = (
    *controller.TEST_SUITES,
    ("tests/test_v24614_title_provenance_controller_binding.py", 7, 300),
    ("tests/test_audit_v24615_controller_binding_repair.py", 8, 180),
    ("tests/test_v24616_repaired_title_provenance_external_gate.py", 20, 600),
)
EXPECTED_TEST_COUNT = controller.EXPECTED_TEST_COUNT + 35


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.16 expected object")
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
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24615_controller_binding_repair_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("test_count") != 57
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or baseline.get("prior_external_question_count") != PRIOR_QUESTION_COUNT
        or baseline.get("prior_external_entity_count") != PRIOR_ENTITY_COUNT
        or baseline.get("v24612_population_resume_retry_rerun_or_evaluation_authorized")
        is not False
        or repair.get("binding_valid") is not True
        or repair.get("v24607_parent_proof_module_mutated") is not False
        or repair.get("v24607_parent_validator_mutated") is not False
        or repair.get("v24609_frozen_proof_or_total_binding_mutated") is not False
        or authorization.get(
            "fresh_disjoint_content_free_title_provenance_successor_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or authorization.get("evaluator_access_authorized") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.16 build parent drifted")
    return value


def _previous_closed() -> bool:
    failed = _read(PREVIOUS_FAILURE)
    audited = _read(PREVIOUS_POSTAUDIT)
    failure_unsigned = dict(failed)
    failure_seal = failure_unsigned.pop("failure_payload_sha256", None)
    audit_unsigned = dict(audited)
    audit_seal = audit_unsigned.pop("audit_payload_sha256", None)
    return (
        failure_seal == payload_sha256(failure_unsigned)
        and audit_seal == payload_sha256(audit_unsigned)
        and audited.get("failure_sha256") == sha256(ROOT / PREVIOUS_FAILURE)
        and failed.get("status") == "terminal_controller_binding_failure_no_result"
        and failed.get("external_wave_count") == 1
        and failed.get("external_population_consumed") is True
        and failed.get("result_created") is False
        and failed.get("official_evaluator_called") is False
        and failed.get(
            "same_population_resume_retry_skip_selective_rerun_or_evaluation_authorized"
        )
        is False
        and audited.get("audit_valid") is True
        and audited.get("findings") == []
        and _parent(ROOT).get("audit_valid") is True
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
    all_primary: list[str] = []
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
            all_primary.append(primary.casefold())
    return len(all_primary) == 64 and len(set(all_primary)) == 64


def _alias_surface_vector_valid() -> bool:
    return _title_query_surface_vector_valid()


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_492_consumed_external_questions": _fresh_entity_vector_valid(),
        "all_64_preregistered_primary_alias_surfaces_globally_unique": _title_query_surface_vector_valid(),
        "all_64_full_surfaces_uniquely_reachable_by_unchanged_exact_title_parent": _title_query_surface_vector_valid(),
        "all_64_second_surfaces_uniquely_reachable_by_unchanged_alias_title_validator": _title_query_surface_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_populations_through_v24612_counted_as_consumed": True,
        "prior_population_resume_retry_rerun_or_evaluation": False,
        "population_selection_uses_visible_names_and_frozen_validator_grammar_only": True,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _protocol_authorization() -> dict[str, bool]:
    return {
        "one_fresh_repaired_title_provenance_probe_design": True,
        "external_probe_launch": False,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def _activation_authorization() -> dict[str, bool]:
    return {
        "one_fresh_repaired_title_provenance_probe_launch": True,
        "benchmark_launch": False,
        "paired_dev64_or_exact220": False,
        "evaluator": False,
    }


def _successor_binding() -> dict[str, Any]:
    if not _previous_closed() or not binding.invariant_valid():
        raise RuntimeError("V2.46.16 predecessor or binding drifted")
    return {
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "v24613_failure_sha256": sha256(ROOT / PREVIOUS_FAILURE),
        "v24613_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "same_or_prior_population_resume_retry_rerun_or_evaluation": False,
        "new_population_reuses_prior_question_or_entity": False,
        "controller_binding_policy": binding.POLICY_ID,
        "protocol_view_proof_policy": binding.protocol_proof.POLICY_ID,
        "runtime_view_proof_policy": binding.runtime_proof.POLICY_ID,
        "runtime_view_total_policy": binding.runtime_total.POLICY_ID,
        "runtime_view_bounded_policy": binding.runtime_bounded.POLICY_ID,
        "runtime_view_collector_policy": collector.POLICY_ID,
        "protocol_view_rebinds_controller_only": True,
        "runtime_view_rebinds_controller_only": True,
        "v24607_parent_proof_module_mutated": False,
        "v24607_parent_validator_mutated": False,
        "v24609_frozen_proof_or_total_binding_mutated": False,
        "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
        "query_ranking_title_validator_or_evidence_projection_changed": False,
        "source_posterior_margin_leave_one_out_safe_change_or_decision_credit_rules_relaxed": False,
        "raw_task_query_url_title_page_prediction_or_provider_payload_emitted": False,
        "paired_dev64_or_exact220_directly_authorized": False,
    }


def mechanism_passed(value: Mapping[str, Any]) -> bool:
    return (
        controller.mechanism_passed(value)
        and value.get("content_free_title_provenance_provider_activity_tasks", 0)
        >= GATES["minimum_content_free_title_provenance_provider_activity_tasks"]
        and value.get(
            "all_content_free_title_provenance_success_rows_consumed_validated_capabilities"
        )
        is True
        and value.get(
            "all_content_free_title_provenance_failure_rows_are_content_free_zero_projections"
        )
        is True
        and value.get(
            "content_free_title_provenance_failure_rows_claim_zero_private_effects"
        )
        is False
        and value.get("content_free_title_provenance_private_content_emitted") is False
        and value.get("content_free_title_provenance_privileged_evaluator_content_read")
        is False
        and value.get(
            "content_free_title_provenance_projection_claims_provider_or_transport_causality"
        )
        is False
        and value.get("content_free_title_provenance_changes_effect_or_credit_surface")
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
    if not reliability:
        return "title_provenance_reliability_successor"
    if not parent_validation:
        return "title_provenance_parent_validation_successor"
    if not latency:
        return "title_provenance_latency_successor"
    if int(mechanism.get("content_free_title_provenance_provider_activity_tasks", 0)) == 0:
        return "title_provenance_runtime_successor"
    counts = mechanism.get("total_content_free_title_provenance_count_fields", {})
    if int(counts.get("action_source_nonempty_title_count", 0)) > 0:
        return "title_transport_projection_bug_successor"
    if int(counts.get("same_url_action_empty_citation_nonempty_count", 0)) > 0:
        return "same_response_citation_title_backfill_successor"
    if (
        int(counts.get("action_source_nonempty_title_count", 0)) == 0
        and int(counts.get("query_local_citation_nonempty_title_count", 0)) == 0
        and int(counts.get("fetched_result_nonempty_title_count", 0)) > 0
    ):
        return "post_fetch_title_integration_successor"
    if (
        int(counts.get("action_source_nonempty_title_count", 0)) == 0
        and int(counts.get("query_local_citation_nonempty_title_count", 0)) == 0
        and int(counts.get("fetched_result_nonempty_title_count", 0)) == 0
    ):
        return "provider_title_acquisition_successor"
    if int(counts.get("query_local_citation_nonempty_title_count", 0)) > 0:
        return "citation_title_alignment_diagnosis"
    if int(counts.get("fetch_request_nonempty_title_count", 0)) > 0:
        return "fetch_request_title_transport_diagnosis"
    return "title_provenance_unresolved_successor"


@contextmanager
def configured_controller(
    *, protocol_compatibility: bool, validator_names: Sequence[str] = ()
) -> Iterator[None]:
    if runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION:
        raise RuntimeError("V2.46.16 inherited original projector drifted")
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
        "validate_protocol": validate_protocol,
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
            raise RuntimeError("V2.46.16 controller exit contaminated runtime proof")


_PROVENANCE_MECHANISM_FIELDS = (
    "content_free_title_provenance_observer_policy",
    "proof_carrying_content_free_title_provenance_policy",
    "total_content_free_title_provenance_projection_policy",
    "bounded_content_free_title_provenance_parent_policy",
    "immutable_title_provenance_collector_policy",
    "collector_projector_is_module_load_unbound_v24608_function",
    "controller_binding_policy",
    "protocol_view_rebinds_controller_only",
    "runtime_view_rebinds_controller_only",
    "v24607_parent_proof_module_mutated",
    "v24607_parent_validator_mutated",
    "v24609_frozen_proof_or_total_binding_mutated",
    "action_source_title_count_observed",
    "query_local_citation_title_count_observed",
    "effective_fetch_request_title_count_observed",
    "fetched_result_title_count_observed",
    "same_url_action_citation_alignment_in_memory_only",
    "title_provenance_claims_provider_transport_or_quality_causality",
    "raw_task_query_url_title_page_prediction_or_provider_payload_emitted",
)


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.46.16 predecessor is not closed")
    _parent(ROOT)
    with configured_controller(protocol_compatibility=True):
        value = _BASE_BUILD_PROTOCOL(now=now, require_pristine=require_pristine)
    value = copy.deepcopy(value)
    value["scope"] = "fresh_repaired_content_free_title_provenance_external_gate"
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
            "protocol_view_rebinds_controller_only": True,
            "runtime_view_rebinds_controller_only": True,
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
        raise RuntimeError("V2.46.16 protocol root drifted")
    copied = dict(value) if value is not None else _read(PROTOCOL)
    core = copy.deepcopy(copied)
    core["scope"] = "fresh_content_free_title_funnel_external_gate"
    for name in _PROVENANCE_MECHANISM_FIELDS:
        core.get("mechanism", {}).pop(name, None)
    core["mechanism"]["targeted_proof_policy"] = binding.protocol_proof.POLICY_ID
    core["mechanism"]["targeted_parent_policy"] = binding.protocol_bounded.POLICY_ID
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
        "action_source_title_count_observed",
        "query_local_citation_title_count_observed",
        "effective_fetch_request_title_count_observed",
        "fetched_result_title_count_observed",
        "same_url_action_citation_alignment_in_memory_only",
    )
    required_false = (
        "v24607_parent_proof_module_mutated",
        "v24607_parent_validator_mutated",
        "v24609_frozen_proof_or_total_binding_mutated",
        "title_provenance_claims_provider_transport_or_quality_causality",
        "raw_task_query_url_title_page_prediction_or_provider_payload_emitted",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "fresh_repaired_content_free_title_provenance_external_gate"
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
        or any(mechanism.get(name) is not True for name in required_true)
        or any(mechanism.get(name) is not False for name in required_false)
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
        or not binding.invariant_valid()
        or runtime._ORIGINAL_TASK_PROJECTION is not _INHERITED_ORIGINAL_TASK_PROJECTION
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.46.16 protocol drifted")
    return copied


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
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_492_consumed_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_492_and_3936"] = True
    checks["v24612_population_resume_retry_rerun_or_evaluation"] = False
    checks["v24613_terminal_failure_and_postaudit_closed"] = True
    checks["v24615_controller_binding_repair_audit_validated"] = True
    checks["v24614_protocol_and_runtime_views_isolated"] = True
    checks["v24610_instance_local_immutable_collector_bound"] = True
    checks["four_title_provenance_boundaries_observed_counts_only"] = True
    checks["title_provenance_claims_provider_transport_or_quality_causality"] = False
    checks["raw_task_query_url_title_page_prediction_or_provider_payload_emitted"] = False
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.16 preaudit root drifted")
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.46.16 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    for name in (
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_492_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_492_and_3936",
        "v24612_population_resume_retry_rerun_or_evaluation",
        "v24613_terminal_failure_and_postaudit_closed",
        "v24615_controller_binding_repair_audit_validated",
        "v24614_protocol_and_runtime_views_isolated",
        "v24610_instance_local_immutable_collector_bound",
        "four_title_provenance_boundaries_observed_counts_only",
        "title_provenance_claims_provider_transport_or_quality_causality",
        "raw_task_query_url_title_page_prediction_or_provider_payload_emitted",
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
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_492_consumed_external_questions",
        "prior_external_questions_and_entities_exactly_492_and_3936",
        "v24613_terminal_failure_and_postaudit_closed",
        "v24615_controller_binding_repair_audit_validated",
        "v24614_protocol_and_runtime_views_isolated",
        "all_64_full_and_second_query_surfaces_validator_reachable",
        "v24610_instance_local_immutable_collector_bound",
        "four_title_provenance_boundaries_observed_counts_only",
        "complete_nested_protocol_validation_critical_section_serialized",
        "task_execution_remains_parallel_after_protocol_validation",
    )
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("launch_authorized") is not True
        or any(checks.get(name) is not True for name in required_true)
        or checks.get("v24612_population_resume_retry_rerun_or_evaluation") is not False
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
        raise RuntimeError("V2.46.16 preactivation audit drifted")
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
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_BUILD_ACTIVATION(now=now)


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.16 activation root drifted")
    with configured_controller(
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_controller(
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_BUILD_EXECUTION_START(now=now)


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    if root.resolve() != ROOT.resolve():
        raise RuntimeError("V2.46.16 execution-start root drifted")
    with configured_controller(
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
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
    if not isinstance(mechanism, Mapping) or any(name not in mechanism for name in required):
        raise RuntimeError("V2.46.16 title-provenance aggregate schema is absent")
    total.validate_aggregate(mechanism)
    with configured_controller(
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_VALIDATE_PUBLIC_RESULT(value)


def run_probe() -> dict[str, Any]:
    with configured_controller(
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
    ):
        return _BASE_RUN_PROBE()


def _decision_authorization(route: str) -> dict[str, bool]:
    primary = {
        "title_transport_projection_bug_successor",
        "same_response_citation_title_backfill_successor",
        "post_fetch_title_integration_successor",
        "provider_title_acquisition_successor",
    }
    return {
        "title_transport_projection_bug_successor_design": route
        == "title_transport_projection_bug_successor",
        "same_response_citation_title_backfill_successor_design": route
        == "same_response_citation_title_backfill_successor",
        "post_fetch_title_integration_successor_design": route
        == "post_fetch_title_integration_successor",
        "provider_title_acquisition_successor_design": route
        == "provider_title_acquisition_successor",
        "title_provenance_followup_diagnosis_design": route not in primary,
        "fresh_paired_dev64_design": False,
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
        "role": "v24616_repaired_title_provenance_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "fresh_repaired_title_provenance_observed"
            if passed
            else "fresh_repaired_title_provenance_incomplete"
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
    expected_status = (
        "fresh_repaired_title_provenance_observed"
        if passed
        else "fresh_repaired_title_provenance_incomplete"
    )
    if (
        copied.get("role") != "v24616_repaired_title_provenance_external_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status") != expected_status
        or copied.get("passed") is not passed
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("diagnostic_route") != route
        or copied.get("claim_scope", {}).get("provider_transport_or_quality_causality_claimed")
        is not False
        or copied.get("authorization") != _decision_authorization(route)
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.46.16 decision drifted")
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
        findings.append("v24614_runtime_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24616_repaired_title_provenance_external_postresult_audit",
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
        != "v24616_repaired_title_provenance_external_postresult_audit"
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
        raise RuntimeError("V2.46.16 postresult audit drifted")
    return copied


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_controller(
        protocol_compatibility=False, validator_names=_ALL_VALIDATORS
    ):
        _BASE_RUN_PROCESS_SUBCOMMAND(args)


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
