#!/usr/bin/env python3
"""Post-freeze fetch-failure and fallback diagnosis for V2.47.75.

The diagnostic consumes only the sealed V2.47.75 forward artifacts after the
prediction freeze plus the public V2.47.76 diagnosis.  It performs no model,
search, fetch, network, benchmark, quality, or evaluator action and never
opens the private population design.  Identities, queries, URLs, hosts, page
text, and candidate values are reduced to aggregate counts and hashes.

Three record scopes are reported separately.  The strict scope is a safe
exact-record parser; bounded-near and unique-target-page scopes are diagnostic
capacity upper bounds only.  None may authorize a writeback or a rerun of the
same population.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import canonicalize_url  # noqa: E402
from deepwide_agent.v24333_programmatic_support_catalog import CellTarget  # noqa: E402
from deepwide_agent.v24743_generic_record_binding import (  # noqa: E402
    _baseline_matrix,
    _source_key,
)
from deepwide_agent.v24770_visible_entity_fair_semantic_runtime import (  # noqa: E402
    _exact_alignment,
    _lead_source,
    validate_result as validate_runtime_result,
)
from deepwide_agent import (  # noqa: E402
    v24775_visible_entity_fair_execution_contract as contract,
)
from scripts import diagnose_v24776_v24775_record_reachability as parent  # noqa: E402


OUTPUT = Path("results/v24777_v24775_fetch_fallback_diagnosis_v1_20260807.json")
ROLE = "v24777_v24775_postfreeze_fetch_fallback_diagnosis"
STATUS = "staged_eight_plus_two_fallback_is_next_equal_budget_falsification"
INITIAL_FETCH_SLOTS = 8
RESERVE_FETCH_SLOTS = 2
SOURCE_FILES = (
    Path("scripts/diagnose_v24777_v24775_fetch_fallback.py"),
    Path("tests/test_diagnose_v24777_v24775_fetch_fallback.py"),
    Path("scripts/diagnose_v24776_v24775_record_reachability.py"),
    parent.OUTPUT,
    Path("src/deepwide_agent/v24770_visible_entity_fair_semantic_runtime.py"),
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("src/deepwide_agent/native_search.py"),
)


def _read(relative: Path) -> dict[str, Any]:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.47.77 repository path escaped")
    path = ROOT / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.77 expected ordinary object: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.77 expected JSON object")
    return value


def _bucket(value: int) -> str:
    return "0" if value == 0 else "1" if value == 1 else "2+"


def _histogram(values: Sequence[int]) -> dict[str, int]:
    counts = Counter(_bucket(value) for value in values)
    return {key: counts[key] for key in ("0", "1", "2+")}


def _source_from_evidence(page: Mapping[str, Any]) -> str:
    return _source_key(str(page["host"]))


def _strict_values(
    content: str, *, entities: Sequence[str], target: CellTarget
) -> set[str]:
    return parent.extract_target_candidates(
        content,
        entities=entities,
        entity=target.row_key,
        column=target.column,
    )


def _bounded_near_values(
    content: str, *, entities: Sequence[str], target: CellTarget
) -> set[str]:
    """Return a deliberately loose identity-near exact-field upper bound."""

    text = unicodedata.normalize("NFKC", str(content))
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    patterns = {entity: parent._entity_pattern(entity) for entity in entities}
    values: set[str] = set()
    for index, line in enumerate(lines):
        if patterns[target.row_key].search(line) is None:
            continue
        hits = {
            entity for entity, pattern in patterns.items() if pattern.search(line)
        }
        if hits != {target.row_key}:
            continue
        if target.column == "Founded":
            values.update(parent._same_line_founding_values(line, target.row_key))
        for nearby in lines[max(0, index - 4) : min(len(lines), index + 25)]:
            other_hits = {
                entity
                for entity, pattern in patterns.items()
                if pattern.search(nearby)
            }.difference({target.row_key})
            if other_hits:
                break
            values.update(parent._labelled_values(nearby, target.column))
    return values


def _unique_target_page_values(
    content: str, *, entities: Sequence[str], target: CellTarget
) -> set[str]:
    """Return an exact-field whole-page upper bound for one-target pages."""

    text = unicodedata.normalize("NFKC", str(content))
    if parent._entity_hits(text, entities) != {target.row_key}:
        return set()
    values: set[str] = set()
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        values.update(parent._labelled_values(line, target.column))
        if target.column == "Founded":
            values.update(parent._same_line_founding_values(line, target.row_key))
    return values


def _scope_counts(
    observations: Mapping[str, Mapping[str, set[str]]],
    fields: Mapping[str, str],
) -> dict[str, Any]:
    states, by_field, safe = parent.classify_record_cells(observations, fields)
    return {
        **states,
        "cell_state_count_by_field": by_field,
        "target_value_pair_count": sum(len(values) for values in observations.values()),
        "source_observation_count": sum(
            len(sources)
            for values in observations.values()
            for sources in values.values()
        ),
        "safe_two_source_same_value_pair_count": len(safe),
    }


def _record(
    observations: dict[str, dict[str, set[str]]],
    *,
    target: CellTarget,
    candidates: Sequence[str],
    source: str,
) -> None:
    for candidate in candidates:
        binding, value_hash = parent._pair_hash(target, candidate)
        observations[binding][value_hash].add(source)


def _private_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda row: tuple(str(row[key]) for key in sorted(row)),
    )
    return contract.payload_sha256(ordered)


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parent_value = parent.validate_diagnosis(_read(parent.OUTPUT))
    forward = contract.validate_forward_result(_read(contract.FORWARD_RESULT))
    summary = contract.validate_run_summary(_read(contract.RUN_SUMMARY))
    freeze = contract.validate_prediction_freeze(_read(contract.PREDICTION_FREEZE))
    audit = parent._validate_frozen_forward_audit(_read(contract.FORWARD_AUDIT))
    if (
        parent_value["status"] != parent.STATUS_ACQUISITION
        or parent_value["strict_exact_record_reachability"][
            "two_source_same_value_cell_count"
        ]
        != 0
        or parent_value["authorization"]["append_only_query_source_fetch_design"]
        is not True
        or forward["terminal_arm_predictions"] != 16
        or summary["valid_task_results"] != contract.SELECTED_COUNT
        or freeze["all_predictions_terminal_before_private_truth_or_quality_open"]
        is not True
        or freeze["private_truth_or_quality_path_opened_or_hashed"] is not False
        or audit["forward_health_go"] is not True
        or audit["mechanism_go"] is not False
    ):
        raise RuntimeError("V2.47.77 frozen parent chain drifted")

    strict: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    bounded: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    unique: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    fields: dict[str, str] = {}
    fetch_failure_per_task: Counter[int] = Counter()
    usable_by_position: Counter[int] = Counter()
    input_selected_pairs: Counter[tuple[int, int]] = Counter()
    unselected_aligned_counts: list[int] = []
    initial_coverage: list[int] = []
    all_coverage: list[int] = []
    initial_under_two_alternatives: list[int] = []
    private_manifest: list[dict[str, Any]] = []
    task_manifest: list[dict[str, Any]] = []
    private_literals: set[str] = set()
    totals: Counter[str] = Counter()
    fixed_tail_improved_entities = 0
    fixed_tail_brought_to_two = 0

    for ordinal in range(1, contract.SELECTED_COUNT + 1):
        relative = contract.TASK_ROOT / f"task_{ordinal:04d}" / contract.RESULT_NAME
        result = validate_runtime_result(_read(relative))
        task_manifest.append(
            {"ordinal": ordinal, "result_sha256": contract.sha256(ROOT / relative)}
        )
        entities = [str(value) for value in result["private_visible_entities"]]
        state = result["private_scheduler_state"]
        requests = list(state["fetch_requests"])
        evidence = result["parent_result"]["private_synthesis_evidence_pages"]
        replay = result["parent_result"]["private_replay_pages"]
        search_cost = result["parent_result"]["receipt"][
            "search_cost_before_adapter"
        ]
        if (
            len(requests) != contract.LIMITS["fetch_targets"]
            or len(evidence) != len(replay)
            or result["parent_result"]["receipt"]["search_cost_after_adapter"]
            != search_cost
        ):
            raise RuntimeError("V2.47.77 frozen fetch surface drifted")
        fetch_failures = int(search_cost["fetch_failures"])
        fetch_failure_per_task[fetch_failures] += 1
        totals["fetch_calls"] += int(search_cost["fetch_calls"])
        totals["fetch_failures"] += fetch_failures
        totals["fetch_request_count"] += len(requests)
        totals["usable_fetched_page_count"] += len(evidence)
        input_selected_pairs[(len(state["input_leads"]), len(state["selected_leads"]))] += 1

        private_literals.update(entities)
        private_literals.add(str(result["opaque_id"]))
        private_literals.add(str(result["private_visible_task"]["question"]))
        private_literals.update(str(query) for query in state["entity_queries"])
        for surface in ("input_leads", "selected_leads", "fetch_requests"):
            for lead in state[surface]:
                private_literals.update(
                    str(lead.get(name, ""))
                    for name in ("title", "url", "fetch_url")
                    if str(lead.get(name, "")).strip()
                )

        evidence_by_requested_url = {
            canonicalize_url(str(page["url"])): page for page in evidence
        }
        for position, request in enumerate(requests, 1):
            requested_url = canonicalize_url(
                str(request.get("fetch_url") or request.get("url") or "")
            )
            if requested_url in evidence_by_requested_url:
                usable_by_position[position] += 1
        if sum(
            canonicalize_url(str(request.get("fetch_url") or request.get("url") or ""))
            in evidence_by_requested_url
            for request in requests
        ) != len(evidence):
            raise RuntimeError("V2.47.77 requested-to-usable page binding drifted")

        columns, rows = _baseline_matrix(result["predictions"]["baseline"])
        if tuple(columns) != contract.EXPECTED_COLUMNS or [row[0] for row in rows] != entities:
            raise RuntimeError("V2.47.77 frozen visible surface drifted")
        targets: list[CellTarget] = []
        for row in rows:
            for column_index in range(1, len(columns)):
                target = CellTarget(row[0], columns[column_index], row[column_index])
                if target.baseline_unknown:
                    targets.append(target)
                    fields[target.binding_sha256] = target.column

        initial_sources = {entity: set() for entity in entities}
        final_sources = {entity: set() for entity in entities}
        for position, request in enumerate(requests, 1):
            requested_url = canonicalize_url(
                str(request.get("fetch_url") or request.get("url") or "")
            )
            page = evidence_by_requested_url.get(requested_url)
            if page is None:
                continue
            content = str(page["content"])
            source = _source_from_evidence(page)
            hits = parent._entity_hits(content, entities)
            for entity in hits:
                final_sources[entity].add(source)
                if position <= INITIAL_FETCH_SLOTS:
                    initial_sources[entity].add(source)
            for target in targets:
                strict_values = _strict_values(content, entities=entities, target=target)
                bounded_values = _bounded_near_values(
                    content, entities=entities, target=target
                )
                unique_values = _unique_target_page_values(
                    content, entities=entities, target=target
                )
                _record(strict, target=target, candidates=sorted(strict_values), source=source)
                _record(bounded, target=target, candidates=sorted(bounded_values), source=source)
                _record(unique, target=target, candidates=sorted(unique_values), source=source)
                for scope, candidates in (
                    ("strict", strict_values),
                    ("bounded_near", bounded_values),
                    ("unique_target_page", unique_values),
                ):
                    for candidate in candidates:
                        binding, value_hash = parent._pair_hash(target, candidate)
                        private_literals.add(candidate)
                        private_manifest.append(
                            {
                                "scope": scope,
                                "target_binding_sha256": binding,
                                "normalized_value_sha256": value_hash,
                                "source_key_sha256": hashlib.sha256(source.encode()).hexdigest(),
                            }
                        )

        initially_fetched_sources = {
            _lead_source(lead) for lead in requests[:INITIAL_FETCH_SLOTS]
        }
        for entity in entities:
            initial_count = len(initial_sources[entity])
            final_count = len(final_sources[entity])
            initial_coverage.append(initial_count)
            all_coverage.append(final_count)
            fixed_tail_improved_entities += int(final_count > initial_count)
            fixed_tail_brought_to_two += int(initial_count < 2 <= final_count)
            all_aligned_sources = {
                _lead_source(lead)
                for lead in state["input_leads"]
                if any(_exact_alignment(lead, entity))
            }
            selected_aligned_sources = {
                _lead_source(lead)
                for lead in state["selected_leads"]
                if any(_exact_alignment(lead, entity))
            }
            unselected_aligned_counts.append(
                len(all_aligned_sources.difference(selected_aligned_sources))
            )
            if initial_count < 2:
                initial_under_two_alternatives.append(
                    len(all_aligned_sources.difference(initially_fetched_sources))
                )

    strict_counts = _scope_counts(strict, fields)
    bounded_counts = _scope_counts(bounded, fields)
    unique_counts = _scope_counts(unique, fields)
    if any(
        counts["safe_two_source_same_value_pair_count"] != 0
        for counts in (strict_counts, bounded_counts, unique_counts)
    ):
        raise RuntimeError("V2.47.77 unexpected frozen two-source reachability")
    if (
        totals["fetch_calls"] != totals["fetch_request_count"]
        or totals["fetch_failures"] + totals["usable_fetched_page_count"]
        != totals["fetch_request_count"]
    ):
        raise RuntimeError("V2.47.77 fetch accounting drifted")

    under_two_with_alternative = sum(value > 0 for value in initial_under_two_alternatives)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": STATUS,
        "parents": {
            "v24776_diagnosis_sha256": contract.sha256(ROOT / parent.OUTPUT),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "task_result_manifest_sha256": contract.payload_sha256(task_manifest),
        },
        "source_manifest": {
            str(path): contract.sha256(ROOT / path) for path in SOURCE_FILES
        },
        "frozen_forward": {
            "selected_tasks": contract.SELECTED_COUNT,
            "terminal_arm_predictions": int(forward["terminal_arm_predictions"]),
            "valid_task_results": int(summary["valid_task_results"]),
            "forward_wall_seconds": summary["forward_wall_seconds"],
            "forward_health_go": True,
            "mechanism_go": False,
            "changed_cell_count": int(summary["changed_cell_count"]),
        },
        "fetch_accounting": {
            "fetch_request_count": totals["fetch_request_count"],
            "physical_fetch_call_count": totals["fetch_calls"],
            "fetch_failure_count": totals["fetch_failures"],
            "usable_fetched_page_count": totals["usable_fetched_page_count"],
            "fetch_failure_count_by_task_histogram": {
                str(key): fetch_failure_per_task[key]
                for key in sorted(fetch_failure_per_task)
            },
            "usable_page_count_by_request_position": {
                str(position): usable_by_position[position]
                for position in range(1, contract.LIMITS["fetch_targets"] + 1)
            },
            "helper_deadline_or_exception_failure_count": 0,
            "request_completed_without_usable_page_count": totals["fetch_failures"],
        },
        "lead_reserve_capacity": {
            "entity_slot_count": len(unselected_aligned_counts),
            "input_selected_lead_count_pair_histogram": {
                f"{input_count}/{selected_count}": amount
                for (input_count, selected_count), amount in sorted(input_selected_pairs.items())
            },
            "unselected_exact_aligned_source_count_histogram": _histogram(
                unselected_aligned_counts
            ),
            "entity_slots_with_any_unselected_exact_aligned_source": sum(
                value > 0 for value in unselected_aligned_counts
            ),
        },
        "fixed_first_eight_then_last_two_observation": {
            "initial_fetch_slots": INITIAL_FETCH_SLOTS,
            "fixed_tail_fetch_slots": RESERVE_FETCH_SLOTS,
            "initial_eight_usable_page_count": sum(
                usable_by_position[position]
                for position in range(1, INITIAL_FETCH_SLOTS + 1)
            ),
            "fixed_last_two_usable_page_count": sum(
                usable_by_position[position]
                for position in range(INITIAL_FETCH_SLOTS + 1, 11)
            ),
            "initial_exact_identity_source_coverage_histogram": _histogram(
                initial_coverage
            ),
            "all_ten_exact_identity_source_coverage_histogram": _histogram(
                all_coverage
            ),
            "initial_entity_slots_below_two_usable_identity_sources": sum(
                value < 2 for value in initial_coverage
            ),
            "initial_below_two_slots_with_unfetched_exact_aligned_source": under_two_with_alternative,
            "unfetched_exact_aligned_source_count_for_initial_below_two_histogram": _histogram(
                initial_under_two_alternatives
            ),
            "fixed_tail_improved_entity_slot_count": fixed_tail_improved_entities,
            "fixed_tail_brought_entity_slot_to_two_sources_count": fixed_tail_brought_to_two,
        },
        "record_scope_sensitivity": {
            "strict_exact_record": strict_counts,
            "bounded_near_record_capacity_upper_bound": bounded_counts,
            "unique_target_page_capacity_upper_bound": unique_counts,
            "private_scope_observation_manifest_sha256": _private_digest(
                private_manifest
            ),
            "bounded_near_or_unique_page_is_valid_writeback_policy": False,
            "all_scopes_reach_any_two_source_same_value_unknown_cell": False,
        },
        "diagnosis": {
            "wall_deadline_or_helper_exception_is_primary_loss": False,
            "completed_fetch_without_usable_page_is_primary_loss": True,
            "parser_only_is_sufficient_on_frozen_pages": False,
            "unused_exact_aligned_reserve_exists_for_every_entity": False,
            "unused_exact_aligned_reserve_exists_for_some_undercovered_entities": under_two_with_alternative > 0,
            "reserve_source_is_known_to_be_fetchable_or_same_value": False,
            "next_equal_budget_falsification": "eight_initial_fetches_then_two_unfetched_exact_aligned_source_fallbacks_for_lowest_successful_identity_coverage",
        },
        "next_falsification": {
            "logical_search_query_count": 4,
            "maximum_physical_fetch_count": 10,
            "initial_fetch_count": INITIAL_FETCH_SLOTS,
            "conditional_reserve_fetch_count": RESERVE_FETCH_SLOTS,
            "failed_url_retry_count": 0,
            "reserve_requires_preexisting_search_lead": True,
            "reserve_requires_unfetched_url_and_registrably_new_source": True,
            "reserve_requires_exact_visible_entity_title_or_url_alignment": True,
            "reserve_priority_uses_successful_page_identity_coverage_only": True,
            "page_field_or_candidate_value_used_for_reserve_routing": False,
            "strict_two_independent_same_value_gate_unchanged": True,
            "fresh_disjoint_external_population_required": True,
        },
        "source_policy": {
            "runtime_task_input_contract": ["opaque_id", "question"],
            "frozen_private_pages_and_receipts_opened_only_after_prediction_freeze": True,
            "private_identity_query_address_host_page_or_candidate_persisted": False,
            "privileged_runtime_metadata_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "same_forward_artifact_rewritten": False,
        },
        "claim_scope": {
            "fetch_bottleneck_diagnosed": True,
            "fallback_trigger_capacity_observed": True,
            "fallback_fetchability_or_same_value_effect_measured": False,
            "deepwidebench_quality_measured": False,
            "benchmark_improvement_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "append_only_equal_budget_staged_fetch_runtime_design": under_two_with_alternative > 0,
            "append_only_fresh_population_design": under_two_with_alternative > 0,
            "same_population_forward_retry_resume_or_rerun": False,
            "fresh_external_activation_or_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    validated = validate_diagnosis(value)
    parent._assert_public_surface(validated, private_literals=sorted(private_literals))
    return validated


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    fetch = copied.get("fetch_accounting", {})
    reserve = copied.get("lead_reserve_capacity", {})
    staged = copied.get("fixed_first_eight_then_last_two_observation", {})
    scopes = copied.get("record_scope_sensitivity", {})
    authorization = copied.get("authorization", {})
    scope_names = (
        "strict_exact_record",
        "bounded_near_record_capacity_upper_bound",
        "unique_target_page_capacity_upper_bound",
    )
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != STATUS
        or copied.get("source_manifest")
        != {str(path): contract.sha256(ROOT / path) for path in SOURCE_FILES}
        or copied.get("frozen_forward", {}).get("forward_health_go") is not True
        or copied.get("frozen_forward", {}).get("mechanism_go") is not False
        or fetch.get("fetch_request_count") != fetch.get("physical_fetch_call_count")
        or fetch.get("fetch_failure_count", -1)
        + fetch.get("usable_fetched_page_count", -1)
        != fetch.get("fetch_request_count")
        or fetch.get("request_completed_without_usable_page_count")
        != fetch.get("fetch_failure_count")
        or fetch.get("helper_deadline_or_exception_failure_count") != 0
        or reserve.get("entity_slot_count") != contract.SELECTED_COUNT * 4
        or staged.get("initial_fetch_slots") != INITIAL_FETCH_SLOTS
        or staged.get("fixed_tail_fetch_slots") != RESERVE_FETCH_SLOTS
        or staged.get("initial_eight_usable_page_count", -1)
        + staged.get("fixed_last_two_usable_page_count", -1)
        != fetch.get("usable_fetched_page_count")
        or any(
            not isinstance(scopes.get(name), Mapping)
            or scopes[name].get("safe_two_source_same_value_pair_count") != 0
            for name in scope_names
        )
        or scopes.get("bounded_near_or_unique_page_is_valid_writeback_policy")
        is not False
        or scopes.get("all_scopes_reach_any_two_source_same_value_unknown_cell")
        is not False
        or copied.get("diagnosis", {}).get(
            "reserve_source_is_known_to_be_fetchable_or_same_value"
        )
        is not False
        or copied.get("next_falsification", {}).get("maximum_physical_fetch_count")
        != contract.LIMITS["fetch_targets"]
        or copied.get("next_falsification", {}).get("failed_url_retry_count") != 0
        or authorization
        != {
            "append_only_equal_budget_staged_fetch_runtime_design": True,
            "append_only_fresh_population_design": True,
            "same_population_forward_retry_resume_or_rerun": False,
            "fresh_external_activation_or_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or copied.get("claim_scope", {}).get("fallback_fetchability_or_same_value_effect_measured")
        is not False
        or copied.get("claim_scope", {}).get("deepwidebench_quality_measured")
        is not False
        or copied.get("claim_scope", {}).get("sota_supported") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.77 diagnosis drifted")
    parent._assert_public_surface(copied)
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": diagnosis["status"],
                "fetch_failures": diagnosis["fetch_accounting"][
                    "fetch_failure_count"
                ],
                "undercovered_entities_with_reserve": diagnosis[
                    "fixed_first_eight_then_last_two_observation"
                ]["initial_below_two_slots_with_unfetched_exact_aligned_source"],
                "same_population_rerun_authorized": diagnosis["authorization"][
                    "same_population_forward_retry_resume_or_rerun"
                ],
            },
            sort_keys=True,
        )
    )
