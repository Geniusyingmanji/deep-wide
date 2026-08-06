"""Unknown-targeted official structured lookup for the V2.46.48 gate.

The visible task first receives one plan, four hosted-search queries, at most
six generic fetches, and one baseline synthesis.  Only baseline ``Unknown``
ROR cells may then spend the remaining fetch budget, up to four public ROR v2
advanced-name lookups.  A lookup is projected into a candidate fact only when
exactly one active record has one normalized ``ror_display`` name equal to the
visible target.  Existing non-Unknown ROR cells and all country cells remain
immutable.

The complete task envelope remains two provider-model effects, four hosted
queries, and at most ten fetch targets.  The candidate can spend more fetches
than the baseline, so this is a quality-cost Pareto comparison rather than an
equal-effect causal ablation.  This module has no file, process, benchmark,
gold, evaluator, reward, or score capability.  Entropy is shadow-only.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit

from . import v24637_objective_alignment_runtime as paired
from . import v24639_ror_objective_runtime as ror
from . import v24644_primary_identity_pair_runtime as identity
from .clients import parse_json_object
from .v24257_score_first_runtime import (
    PLAN_SYSTEM,
    PLAN_USER,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    _model_text,
    _validated_plan,
    validate_visible_task,
)
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24286_visible_schema_runtime import extract_robust_visible_columns
from .v24308_child_exit_observability import coarse_exception_type
from .v24325_shared_prefix_revision_runtime import _format_evidence
from .v24640_evidence_constrained_runtime import UNKNOWN


POLICY_ID = "v24648_unknown_target_official_structured_lookup_v1"
ROLE = "v24648_unknown_target_structured_ror_task_result"
RECEIPT_ROLE = "v24648_unknown_target_structured_content_free_receipt"
ARMS = ("baseline", "unknown_target_structured")
GENERIC_FETCH_CAP = 6
TARGETED_LOOKUP_CAP = 4


def exact_lookup_url(entity: str) -> str:
    """Build one bounded official ROR v2 exact-name lookup URL."""

    target = str(entity).strip()
    if not target or any(character in target for character in "\r\n\0\"\\"):
        raise ValueError("V2.46.48 lookup target drifted")
    query = urlencode(
        (
            ("query.advanced", f'names.value:"{target}"'),
            ("filter", "status:active"),
        )
    )
    return f"https://api.ror.org/v2/organizations?{query}"


def unknown_target_lookup_requests(
    baseline: str, entities: Sequence[str], *, limit: int = TARGETED_LOOKUP_CAP
) -> list[dict[str, str]]:
    """Select only baseline-Unknown ROR cells in visible row order."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 4:
        raise ValueError("V2.46.48 lookup limit drifted")
    columns, rows = ror._matrix(baseline)
    if tuple(columns) != ror.EXPECTED_COLUMNS or len(rows) != len(entities):
        raise ValueError("V2.46.48 baseline projection drifted")
    requests: list[dict[str, str]] = []
    for row, entity in zip(rows, entities, strict=True):
        if row[0] != entity:
            raise ValueError("V2.46.48 visible identity order drifted")
        if row[1].casefold() not in UNKNOWN:
            continue
        requests.append(
            {
                "url": exact_lookup_url(entity),
                "title": "",
                "query": "unknown-target official structured lookup",
                "member_label": entity,
            }
        )
        if len(requests) == limit:
            break
    return requests


def _lookup_target(url: object, expected: Mapping[str, str]) -> str | None:
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold() != "api.ror.org"
        or parsed.path.rstrip("/") != "/v2/organizations"
        or parsed.fragment
    ):
        return None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if len(pairs) != 2 or dict(pairs).get("filter") != "status:active":
        return None
    advanced = dict(pairs).get("query.advanced", "")
    match = re.fullmatch(r'names\.value:"(.+)"', advanced, flags=re.DOTALL)
    if match is None:
        return None
    target = match.group(1)
    return target if exact_lookup_url(target) == expected.get(target) else None


def _display_names(record: Mapping[str, Any]) -> set[str]:
    names = record.get("names")
    if not isinstance(names, Sequence) or isinstance(names, (str, bytes)):
        return set()
    values = set()
    for raw in names:
        if not isinstance(raw, Mapping):
            continue
        types = raw.get("types")
        if (
            isinstance(types, Sequence)
            and not isinstance(types, (str, bytes))
            and "ror_display" in {str(value).casefold() for value in types}
        ):
            value = identity.normalized_identity(raw.get("value"))
            if value:
                values.add(value)
    return values


def project_exact_lookup_pages(
    batches: object, requested_entities: Sequence[str]
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Project exact active search hits into minimal official record pages."""

    expected = {entity: exact_lookup_url(entity) for entity in requested_entities}
    pages: list[dict[str, str]] = []
    stats: Counter[str] = Counter(
        {
            "requested_target_count": len(expected),
            "returned_result_count": 0,
            "parseable_response_count": 0,
            "unique_exact_response_count": 0,
            "ambiguous_exact_response_count": 0,
            "no_exact_response_count": 0,
            "malformed_response_count": 0,
            "projected_record_count": 0,
        }
    )
    seen_targets: set[str] = set()
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        stats["malformed_response_count"] += len(expected)
        return pages, dict(stats)
    for raw_batch in batches:
        if not isinstance(raw_batch, Mapping):
            continue
        results = raw_batch.get("results")
        if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
            continue
        for raw_result in results:
            if not isinstance(raw_result, Mapping):
                continue
            stats["returned_result_count"] += 1
            target = _lookup_target(raw_result.get("url"), expected)
            if target is None or target in seen_targets:
                stats["malformed_response_count"] += 1
                continue
            seen_targets.add(target)
            raw_content = str(
                raw_result.get("raw_content") or raw_result.get("content") or ""
            )
            try:
                response = json.loads(raw_content)
            except (json.JSONDecodeError, TypeError, ValueError):
                stats["malformed_response_count"] += 1
                continue
            items = response.get("items") if isinstance(response, Mapping) else None
            number = (
                response.get("number_of_results")
                if isinstance(response, Mapping)
                else None
            )
            if (
                isinstance(number, bool)
                or not isinstance(number, int)
                or number < 0
                or not isinstance(items, Sequence)
                or isinstance(items, (str, bytes))
                or number != len(items)
            ):
                stats["malformed_response_count"] += 1
                continue
            stats["parseable_response_count"] += 1
            matches: dict[str, Mapping[str, Any]] = {}
            target_identity = identity.normalized_identity(target)
            for raw_item in items:
                if not isinstance(raw_item, Mapping) or raw_item.get("status") != "active":
                    continue
                suffix = identity.frozen._ror_suffix(raw_item.get("id"))
                displays = _display_names(raw_item)
                if suffix is not None and displays == {target_identity}:
                    matches[suffix] = raw_item
            if len(matches) == 1:
                stats["unique_exact_response_count"] += 1
            elif len(matches) > 1:
                stats["ambiguous_exact_response_count"] += 1
            else:
                stats["no_exact_response_count"] += 1
            for suffix, record in sorted(matches.items()):
                displays = [
                    {"value": target, "types": ["ror_display"]}
                ]
                pages.append(
                    {
                        "evidence_id": f"L{len(pages) + 1:04d}",
                        "url": f"https://api.ror.org/v2/organizations/{suffix}",
                        "title": "ROR API response",
                        "content": json.dumps(
                            {
                                "id": record.get("id"),
                                "names": displays,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    }
                )
                stats["projected_record_count"] += 1
    stats["malformed_response_count"] += len(set(expected) - seen_targets)
    return pages, dict(stats)


def _receipt(
    *,
    budget: paired._Budget,
    model_cost: Mapping[str, int],
    search_cost: Mapping[str, int],
    search_batch_count: int,
    generic_fetch_targets: int,
    generic_pages: int,
    lookup_fetch_targets: int,
    lookup_stats: Mapping[str, int],
    baseline_stats: Mapping[str, Any],
    candidate_stats: Mapping[str, Any],
    failures: Sequence[Mapping[str, str]],
    discovery: Mapping[str, int | bool],
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "shared_plan_search_generic_fetch_baseline_prefix": True,
        "baseline_precedes_unknown_target_lookup": True,
        "provider_model_stage_vector": list(budget.model_stages),
        "admitted_hosted_search_queries": budget.search_queries,
        "admitted_total_fetch_targets": budget.fetch_targets,
        "generic_fetch_cap": GENERIC_FETCH_CAP,
        "unknown_target_lookup_cap": TARGETED_LOOKUP_CAP,
        "generic_fetch_targets": int(generic_fetch_targets),
        "generic_model_visible_page_count": int(generic_pages),
        "unknown_target_lookup_fetch_targets": int(lookup_fetch_targets),
        "search_batch_count": int(search_batch_count),
        "lookup": dict(lookup_stats),
        "discovery": dict(discovery),
        "baseline_table": dict(baseline_stats),
        "candidate_table": dict(candidate_stats),
        "model_cost": {key: int(amount) for key, amount in model_cost.items()},
        "search_cost": {key: int(amount) for key, amount in search_cost.items()},
        "recoverable_failure_count": len(failures),
        "recoverable_failure_type_counts": {
            name: sum(item.get("type") == name for item in failures)
            for name in sorted({str(item.get("type")) for item in failures})
        },
        "entropy_shadow": paired._shadow_entropy(
            fetched=budget.fetch_targets,
            usable=generic_pages + int(lookup_stats.get("parseable_response_count", 0)),
        ),
        "candidate_is_deterministic_exact_name_registry_baseline": True,
        "candidate_additional_provider_model_effect": False,
        "candidate_additional_hosted_search_query": False,
        "candidate_additional_native_fetch_effect": lookup_fetch_targets > 0,
        "same_total_task_model_query_fetch_caps_as_parent": True,
        "quality_cost_pareto_not_equal_effect_causal_ablation": True,
        "nonunknown_ror_and_all_country_cells_immutable": True,
        "identity_binding_precedes_entropy_or_task_credit": True,
        "positive_task_credit_assigned": False,
        "question_prompt_query_url_page_prediction_answer_entity_or_opaque_id_emitted": False,
        "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = paired.payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    lookup = copied.get("lookup", {})
    discovery = copied.get("discovery", {})
    model_cost = copied.get("model_cost", {})
    count_fields = (
        "requested_target_count",
        "returned_result_count",
        "parseable_response_count",
        "unique_exact_response_count",
        "ambiguous_exact_response_count",
        "no_exact_response_count",
        "malformed_response_count",
        "projected_record_count",
    )
    discovery_counts = (
        "candidate_evidence_page_count",
        "page_with_any_explicit_ror_count",
        "official_api_page_count",
        "entity_page_hit_count",
        "unique_page_pair_hit_count",
        "ambiguous_page_hit_count",
        "unknown_target_unique_pair_count",
        "unknown_target_ambiguous_pair_count",
        "unknown_target_no_pair_count",
        "admitted_replacement_count",
        "nonunknown_target_pair_count",
        "exact_title_identity_pair_count",
        "structured_primary_identity_pair_count",
        "body_only_identity_rejected_pair_count",
    )
    if (
        copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("shared_plan_search_generic_fetch_baseline_prefix") is not True
        or copied.get("baseline_precedes_unknown_target_lookup") is not True
        or copied.get("provider_model_stage_vector")
        != ["shared_plan", "baseline_synthesis"]
        or copied.get("admitted_hosted_search_queries", -1) not in range(5)
        or copied.get("admitted_total_fetch_targets", -1) not in range(11)
        or copied.get("generic_fetch_cap") != 6
        or copied.get("unknown_target_lookup_cap") != 4
        or copied.get("generic_fetch_targets", -1) not in range(7)
        or copied.get("unknown_target_lookup_fetch_targets", -1) not in range(5)
        or copied.get("generic_fetch_targets", 0)
        + copied.get("unknown_target_lookup_fetch_targets", 0)
        != copied.get("admitted_total_fetch_targets")
        or not isinstance(lookup, Mapping)
        or any(
            isinstance(lookup.get(name), bool)
            or not isinstance(lookup.get(name), int)
            or lookup.get(name, -1) < 0
            for name in count_fields
        )
        or lookup.get("requested_target_count")
        != copied.get("unknown_target_lookup_fetch_targets")
        or lookup.get("unique_exact_response_count", 0)
        + lookup.get("ambiguous_exact_response_count", 0)
        + lookup.get("no_exact_response_count", 0)
        != lookup.get("parseable_response_count")
        or not isinstance(discovery, Mapping)
        or any(
            isinstance(discovery.get(name), bool)
            or not isinstance(discovery.get(name), int)
            or discovery.get(name, -1) < 0
            for name in discovery_counts
        )
        or discovery.get("admitted_replacement_count")
        != discovery.get("unknown_target_unique_pair_count")
        or discovery.get("existing_nonunknown_cells_changed") is not False
        or discovery.get("country_code_cells_changed") is not False
        or discovery.get("fact_value_created_without_model_visible_unique_pair")
        is not False
        or not isinstance(model_cost, Mapping)
        or model_cost.get("requests") != 2
        or copied.get("candidate_is_deterministic_exact_name_registry_baseline")
        is not True
        or copied.get("candidate_additional_provider_model_effect") is not False
        or copied.get("candidate_additional_hosted_search_query") is not False
        or copied.get("same_total_task_model_query_fetch_caps_as_parent") is not True
        or copied.get("quality_cost_pareto_not_equal_effect_causal_ablation")
        is not True
        or copied.get("nonunknown_ror_and_all_country_cells_immutable") is not True
        or copied.get("identity_binding_precedes_entropy_or_task_credit") is not True
        or copied.get("positive_task_credit_assigned") is not False
        or copied.get(
            "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or copied.get("entropy_shadow", {}).get("routes_or_changes_forward_effects")
        is not False
        or seal != paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.48 content-free receipt drifted")
    return copied


def run_v24648_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    entities = ror.extract_visible_entities(visible["question"])
    limits.validate()
    if limits.model_calls != 3 or limits.search_queries != 4 or limits.fetch_targets != 10:
        raise ValueError("V2.46.48 fixed effect envelope drifted")
    started = float(monotonic())
    budget = paired._Budget(limits, started, monotonic)
    model_before = _counter_snapshot(model, paired.MODEL_COUNTERS)
    search_before = _counter_snapshot(search, paired.SEARCH_COUNTERS)
    failures: list[dict[str, str]] = []

    def recovered(stage: str, error: BaseException) -> None:
        failures.append({"stage": stage, "type": coarse_exception_type(error)})

    if not budget.admit_model("shared_plan"):
        raise RuntimeError("V2.46.48 shared plan was not admitted")
    try:
        response = model.complete(
            PLAN_SYSTEM,
            PLAN_USER.format(
                question=visible["question"], query_limit=limits.search_queries
            ),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        plan = _validated_plan(
            parse_json_object(_model_text(response)), visible["question"], limits
        )
    except Exception as error:
        recovered("shared_plan", error)
        plan = _validated_plan({}, visible["question"], limits)
    columns = extract_robust_visible_columns(visible["question"]) or list(plan["columns"])
    if tuple(columns) != ror.EXPECTED_COLUMNS:
        raise ValueError("V2.46.48 expected the visible ROR schema")

    queries = ror.visible_query_vector(visible["question"], limits.search_queries)
    query_count = budget.admit_search(len(queries))
    union = TaskUnionDiscoverySearchClient(search)
    try:
        batches = (
            union.search_many(
                queries[:query_count],
                max_results=limits.search_results_per_query,
                search_depth="advanced",
                include_raw_content=False,
            )
            if query_count
            else []
        )
    except Exception as error:
        recovered("shared_search", error)
        batches = []
    leads = identity._page_title_only_lead_requests(batches, GENERIC_FETCH_CAP)
    generic_fetch_count = budget.admit_fetch(len(leads))
    try:
        generic_raw = (
            union.fetch_urls(leads[:generic_fetch_count])
            if generic_fetch_count
            else []
        )
    except Exception as error:
        recovered("generic_fetch", error)
        generic_raw = []
    generic_pages = identity._final_url_page_vector(
        generic_raw, prefix="E", page_chars=limits.page_chars
    )
    generic_visible = identity.frozen._model_visible_pages(
        generic_pages, character_cap=limits.evidence_chars
    )
    evidence = _format_evidence(
        generic_visible, character_cap=limits.evidence_chars
    )

    fallback = paired._fallback(visible["question"], columns, entities)
    baseline = ror.project_visible_rows(fallback, entities)[0]
    if not budget.admit_model("baseline_synthesis"):
        raise RuntimeError("V2.46.48 baseline synthesis was not admitted")
    try:
        response = model.complete(
            SYNTHESIS_SYSTEM,
            SYNTHESIS_USER.format(
                question=visible["question"],
                columns=json.dumps(columns, ensure_ascii=False),
                evidence=evidence,
            ),
            max_output_tokens=limits.synthesis_output_tokens,
            json_mode=False,
        )
        canonical = paired._canonical(
            _model_text(response), columns, visible["question"]
        )
        baseline = ror.project_visible_rows(canonical or fallback, entities)[0]
    except Exception as error:
        recovered("baseline_synthesis", error)

    lookup_requests = unknown_target_lookup_requests(
        baseline, entities, limit=TARGETED_LOOKUP_CAP
    )
    lookup_fetch_count = budget.admit_fetch(len(lookup_requests))
    try:
        lookup_raw = (
            union.fetch_urls(lookup_requests[:lookup_fetch_count])
            if lookup_fetch_count
            else []
        )
    except Exception as error:
        recovered("unknown_target_lookup", error)
        lookup_raw = []
    lookup_entities = [
        request["member_label"] for request in lookup_requests[:lookup_fetch_count]
    ]
    lookup_pages, lookup_stats = project_exact_lookup_pages(
        lookup_raw, lookup_entities
    )
    candidate, raw_discovery = identity.discover_pairs(
        baseline,
        entities=entities,
        pages=[*generic_visible, *lookup_pages],
    )
    discovery = dict(raw_discovery)
    discovery["candidate_evidence_page_count"] = discovery.pop(
        "model_visible_page_count"
    )
    discovery["generic_model_visible_page_count"] = len(generic_visible)
    discovery["targeted_structured_page_count"] = len(lookup_pages)

    model_cost = _counter_delta(
        _counter_snapshot(model, paired.MODEL_COUNTERS), model_before
    )
    search_cost = _counter_delta(
        _counter_snapshot(search, paired.SEARCH_COUNTERS), search_before
    )
    predictions = {"baseline": baseline, "unknown_target_structured": candidate}
    stats = {
        arm: paired._table_stats(predictions[arm], columns, entities) for arm in ARMS
    }
    receipt = _receipt(
        budget=budget,
        model_cost=model_cost,
        search_cost=search_cost,
        search_batch_count=len(batches),
        generic_fetch_targets=generic_fetch_count,
        generic_pages=len(generic_visible),
        lookup_fetch_targets=lookup_fetch_count,
        lookup_stats=lookup_stats,
        baseline_stats=stats["baseline"],
        candidate_stats=stats["unknown_target_structured"],
        failures=failures,
        discovery=discovery,
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "columns": list(columns),
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "receipt": receipt,
        "elapsed_seconds": round(max(0.0, float(monotonic()) - started), 6),
        "private_visible_task_content_present": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["result_sha256"] = paired.payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    predictions = copied.get("predictions", {})
    hashes = copied.get("prediction_sha256", {})
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or set(predictions) != set(ARMS)
        or set(hashes) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("private_visible_task_content_present") is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.48 task result drifted")
    validate_receipt(copied.get("receipt", {}))
    for arm in ARMS:
        columns, rows = ror._matrix(predictions[arm])
        if tuple(columns) != ror.EXPECTED_COLUMNS or len(rows) != 4:
            raise ValueError("V2.46.48 projected table drifted")
    _columns, baseline = ror._matrix(predictions["baseline"])
    _columns, candidate = ror._matrix(predictions["unknown_target_structured"])
    changed = 0
    for source, target in zip(baseline, candidate, strict=True):
        if source[0] != target[0] or source[2] != target[2]:
            raise ValueError("V2.46.48 identity or country mutation")
        if source[1].casefold() not in UNKNOWN and source[1] != target[1]:
            raise ValueError("V2.46.48 nonunknown ROR mutation")
        changed += int(source[1] != target[1])
    if changed != copied["receipt"]["discovery"]["admitted_replacement_count"]:
        raise ValueError("V2.46.48 admitted replacement count drifted")
    return copied


__all__ = [
    "ARMS",
    "GENERIC_FETCH_CAP",
    "POLICY_ID",
    "ROLE",
    "TARGETED_LOOKUP_CAP",
    "exact_lookup_url",
    "project_exact_lookup_pages",
    "run_v24648_task",
    "unknown_target_lookup_requests",
    "validate_receipt",
    "validate_result",
]
