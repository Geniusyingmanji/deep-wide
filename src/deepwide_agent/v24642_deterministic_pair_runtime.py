"""Deterministic model-visible ROR pair discovery for V2.46.42.

The visible task receives one plan, one retrieval/fetch prefix, and one
baseline synthesis.  No provider call is used to declare revisions.  Instead,
the candidate scans exactly the fetched evidence prefix shown to the baseline
model.  An ``Unknown`` ROR cell may be filled only when at least one page
contains the exact visible organization phrase and exactly one explicit ROR
identifier.  Multiple distinct identifiers for one target fail closed.

Existing non-Unknown ROR cells and all country-code cells are immutable.  This
module has no file, process, benchmark, gold, evaluator, reward, or score
capability.  Entropy remains shadow-only and receives no task credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .clients import parse_json_object
from .v24257_score_first_runtime import (
    PLAN_SYSTEM,
    PLAN_USER,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    _lead_requests,
    _model_text,
    _validated_plan,
    validate_visible_task,
)
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24286_visible_schema_runtime import extract_robust_visible_columns
from .v24308_child_exit_observability import coarse_exception_type
from .v24325_shared_prefix_revision_runtime import _format_evidence, _page_vector
from . import v24637_objective_alignment_runtime as paired
from . import v24639_ror_objective_runtime as ror
from .v24640_evidence_constrained_runtime import (
    UNKNOWN,
    _contains_exact_phrase,
    _model_visible_pages,
    _render,
    _ror_suffix,
)


POLICY_ID = "v24642_deterministic_model_visible_ror_pair_discovery_v1"
ROLE = "v24642_deterministic_pair_ror_task_result"
RECEIPT_ROLE = "v24642_deterministic_pair_content_free_receipt"
ARMS = ("baseline", "deterministic_pair")

_ROR_URL = re.compile(
    r"(?<![0-9a-z])(?:https?://)?(?:www\.)?ror\.org/(0[0-9a-z]{8})(?![0-9a-z])",
    flags=re.IGNORECASE,
)
_ROR_LABEL = re.compile(
    r"(?<![0-9a-z])ror(?:\s+(?:id|identifier))?\s*[:=#-]?\s*"
    r"(0[0-9a-z]{8})(?![0-9a-z])",
    flags=re.IGNORECASE,
)


def explicit_ror_suffixes(page: Mapping[str, object]) -> tuple[str, ...]:
    """Extract only URL- or label-bound ROR identifiers from one visible page."""

    surface = "\n".join(
        (
            str(page.get("url", "")),
            str(page.get("title", "")),
            str(page.get("content", "")),
        )
    )
    values = {
        match.group(1).casefold()
        for pattern in (_ROR_URL, _ROR_LABEL)
        for match in pattern.finditer(surface)
        if _ror_suffix(match.group(1)) is not None
    }
    return tuple(sorted(values))


def _exact_surface_matches(surface: object, entity: str) -> list[re.Match[str]]:
    text = unicodedata.normalize("NFKC", str(surface))
    tokens = [re.escape(token) for token in unicodedata.normalize("NFKC", entity).split()]
    if not tokens:
        return []
    pattern = re.compile(r"(?<!\w)" + r"\s+".join(tokens) + r"(?!\w)", re.IGNORECASE)
    return list(pattern.finditer(text))


def entity_bound_ror_suffixes(
    page: Mapping[str, object], entity: str, *, radius: int = 500
) -> tuple[str, ...]:
    """Extract ROR IDs locally bound to one exact visible entity surface.

    A ROR URL is bound when the page title contains the exact entity.  An ID
    in page text is bound only when it appears in a bounded window around an
    exact entity occurrence.  This prevents a directory page from pairing one
    organization's name with another distant organization's identifier.
    """

    if isinstance(radius, bool) or not isinstance(radius, int) or radius < 100:
        raise ValueError("V2.46.42 pair-binding radius drifted")
    title = unicodedata.normalize("NFKC", str(page.get("title", "")))
    content = unicodedata.normalize("NFKC", str(page.get("content", "")))
    values: set[str] = set()
    if _exact_surface_matches(title, entity):
        values.update(explicit_ror_suffixes({"url": page.get("url", "")}))
        values.update(
            explicit_ror_suffixes(
                {
                    "title": title,
                    "content": content[: radius * 2],
                }
            )
        )
    for match in _exact_surface_matches(content, entity):
        start = max(0, match.start() - radius)
        end = min(len(content), match.end() + radius)
        values.update(explicit_ror_suffixes({"url": page.get("url", "")}))
        values.update(explicit_ror_suffixes({"content": content[start:end]}))
    return tuple(sorted(values))


def discover_pairs(
    baseline: str,
    *,
    entities: Sequence[str],
    pages: Sequence[Mapping[str, str]],
) -> tuple[str, dict[str, int | bool]]:
    """Fill Unknown ROR cells from unique exact target-page pairs only."""

    columns, rows = ror._matrix(baseline)
    if tuple(columns) != ror.EXPECTED_COLUMNS or len(rows) != len(entities):
        raise ValueError("V2.46.42 baseline projection drifted")
    output = [list(row) for row in rows]
    target_values: dict[str, set[str]] = defaultdict(set)
    entity_page_hits: Counter[str] = Counter()
    unique_page_pair_hits: Counter[str] = Counter()
    ambiguous_page_hits: Counter[str] = Counter()
    pages_with_any_explicit_ror = 0

    for page in pages:
        page_suffixes = explicit_ror_suffixes(page)
        pages_with_any_explicit_ror += int(bool(page_suffixes))
        entity_surface = " ".join(
            (str(page.get("title", "")), str(page.get("content", "")))
        )
        for entity in entities:
            if not _contains_exact_phrase(entity_surface, entity):
                continue
            entity_page_hits[entity] += 1
            suffixes = entity_bound_ror_suffixes(page, entity)
            if len(suffixes) == 1:
                target_values[entity].add(suffixes[0])
                unique_page_pair_hits[entity] += 1
            elif len(suffixes) > 1:
                ambiguous_page_hits[entity] += 1

    admitted = immutable = unique_targets = ambiguous_targets = no_pair_targets = 0
    for index, entity in enumerate(entities):
        if output[index][0] != entity:
            raise ValueError("V2.46.42 baseline visible order drifted")
        values = target_values.get(entity, set())
        if output[index][1].casefold() not in UNKNOWN:
            immutable += int(bool(values))
            continue
        if len(values) == 1 and ambiguous_page_hits[entity] == 0:
            output[index][1] = next(iter(values))
            admitted += 1
            unique_targets += 1
        elif len(values) > 1 or ambiguous_page_hits[entity] > 0:
            ambiguous_targets += 1
        else:
            no_pair_targets += 1

    changed_nonunknown = any(
        source[1].casefold() not in UNKNOWN and source[1] != target[1]
        for source, target in zip(rows, output, strict=True)
    )
    changed_country = any(
        source[2] != target[2] for source, target in zip(rows, output, strict=True)
    )
    unsupported = admitted > unique_targets
    if changed_nonunknown or changed_country or unsupported:
        raise RuntimeError("V2.46.42 pair discovery violated monotonicity")
    return _render(columns, output), {
        "model_visible_page_count": len(pages),
        "page_with_any_explicit_ror_count": pages_with_any_explicit_ror,
        "entity_page_hit_count": sum(entity_page_hits.values()),
        "unique_page_pair_hit_count": sum(unique_page_pair_hits.values()),
        "ambiguous_page_hit_count": sum(ambiguous_page_hits.values()),
        "unknown_target_unique_pair_count": unique_targets,
        "unknown_target_ambiguous_pair_count": ambiguous_targets,
        "unknown_target_no_pair_count": no_pair_targets,
        "admitted_replacement_count": admitted,
        "nonunknown_target_pair_count": immutable,
        "existing_nonunknown_cells_changed": changed_nonunknown,
        "country_code_cells_changed": changed_country,
        "fact_value_created_without_model_visible_unique_pair": unsupported,
    }


def _receipt(
    *,
    budget: Any,
    model_cost: Mapping[str, int],
    search_cost: Mapping[str, int],
    search_batch_count: int,
    fetched: int,
    usable: int,
    baseline_stats: Mapping[str, Any],
    candidate_stats: Mapping[str, Any],
    failures: Sequence[Mapping[str, str]],
    discovery: Mapping[str, int | bool],
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "shared_plan_search_fetch_evidence_prefix": True,
        "baseline_precedes_deterministic_pair_discovery": True,
        "provider_model_stage_vector": list(budget.model_stages),
        "admitted_search_queries": budget.search_queries,
        "admitted_fetch_targets": budget.fetch_targets,
        "search_batch_count": int(search_batch_count),
        "usable_page_count": int(usable),
        "baseline_table": dict(baseline_stats),
        "candidate_table": dict(candidate_stats),
        "model_cost": {key: int(amount) for key, amount in model_cost.items()},
        "search_cost": {key: int(amount) for key, amount in search_cost.items()},
        "recoverable_failure_count": len(failures),
        "recoverable_failure_type_counts": {
            name: sum(item.get("type") == name for item in failures)
            for name in sorted({str(item.get("type")) for item in failures})
        },
        "discovery": dict(discovery),
        "entropy_shadow": paired._shadow_entropy(fetched=fetched, usable=usable),
        "candidate_uses_provider_model_for_pair_declaration": False,
        "candidate_additional_model_query_fetch_or_token_effect": False,
        "provider_model_effect_cap_increased_from_v24640": False,
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
    discovery = copied.get("discovery", {})
    shadow = copied.get("entropy_shadow", {})
    stages = copied.get("provider_model_stage_vector")
    counts = (
        "model_visible_page_count",
        "page_with_any_explicit_ror_count",
        "entity_page_hit_count",
        "unique_page_pair_hit_count",
        "ambiguous_page_hit_count",
        "unknown_target_unique_pair_count",
        "unknown_target_ambiguous_pair_count",
        "unknown_target_no_pair_count",
        "admitted_replacement_count",
        "nonunknown_target_pair_count",
    )
    model_cost = copied.get("model_cost", {})
    if (
        copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("shared_plan_search_fetch_evidence_prefix") is not True
        or copied.get("baseline_precedes_deterministic_pair_discovery") is not True
        or stages != ["shared_plan", "baseline_synthesis"]
        or copied.get("admitted_search_queries", -1) not in range(5)
        or copied.get("admitted_fetch_targets", -1) not in range(11)
        or not isinstance(discovery, Mapping)
        or any(
            isinstance(discovery.get(name), bool)
            or not isinstance(discovery.get(name), int)
            or discovery.get(name, -1) < 0
            for name in counts
        )
        or discovery.get("admitted_replacement_count")
        != discovery.get("unknown_target_unique_pair_count")
        or discovery.get("existing_nonunknown_cells_changed") is not False
        or discovery.get("country_code_cells_changed") is not False
        or discovery.get("fact_value_created_without_model_visible_unique_pair") is not False
        or not isinstance(model_cost, Mapping)
        or model_cost.get("requests") != 2
        or shadow.get("routes_or_changes_forward_effects") is not False
        or shadow.get("positive_credit_assigned") is not False
        or shadow.get("requires_postfreeze_outer_utility_validation") is not True
        or copied.get("candidate_uses_provider_model_for_pair_declaration") is not False
        or copied.get("candidate_additional_model_query_fetch_or_token_effect") is not False
        or copied.get("provider_model_effect_cap_increased_from_v24640") is not False
        or copied.get(
            "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.42 content-free receipt drifted")
    return copied


def run_v24642_task(
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
        raise ValueError("V2.46.42 fixed effect envelope drifted")
    started = float(monotonic())
    budget = paired._Budget(limits, started, monotonic)
    model_before = _counter_snapshot(model, paired.MODEL_COUNTERS)
    search_before = _counter_snapshot(search, paired.SEARCH_COUNTERS)
    failures: list[dict[str, str]] = []

    def recovered(stage: str, error: BaseException) -> None:
        failures.append({"stage": stage, "type": coarse_exception_type(error)})

    if not budget.admit_model("shared_plan"):
        raise RuntimeError("V2.46.42 shared plan was not admitted")
    try:
        response = model.complete(
            PLAN_SYSTEM,
            PLAN_USER.format(question=visible["question"], query_limit=limits.search_queries),
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
        raise ValueError("V2.46.42 expected the visible ROR schema")

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
    leads = _lead_requests(batches, limits.fetch_targets)
    fetch_count = budget.admit_fetch(len(leads))
    try:
        pages_raw = union.fetch_urls(leads[:fetch_count]) if fetch_count else []
    except Exception as error:
        recovered("shared_fetch", error)
        pages_raw = []
    fetched_pages = _page_vector(pages_raw, prefix="E", page_chars=limits.page_chars)
    visible_pages = _model_visible_pages(fetched_pages, character_cap=limits.evidence_chars)
    evidence = _format_evidence(visible_pages, character_cap=limits.evidence_chars)

    fallback = paired._fallback(visible["question"], columns, entities)
    baseline = ror.project_visible_rows(fallback, entities)[0]
    if not budget.admit_model("baseline_synthesis"):
        raise RuntimeError("V2.46.42 baseline synthesis was not admitted")
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
        canonical = paired._canonical(_model_text(response), columns, visible["question"])
        baseline = ror.project_visible_rows(canonical or fallback, entities)[0]
    except Exception as error:
        recovered("baseline_synthesis", error)

    candidate, discovery = discover_pairs(
        baseline, entities=entities, pages=visible_pages
    )
    model_cost = _counter_delta(
        _counter_snapshot(model, paired.MODEL_COUNTERS), model_before
    )
    search_cost = _counter_delta(
        _counter_snapshot(search, paired.SEARCH_COUNTERS), search_before
    )
    predictions = {"baseline": baseline, "deterministic_pair": candidate}
    stats = {
        arm: paired._table_stats(predictions[arm], columns, entities) for arm in ARMS
    }
    receipt = _receipt(
        budget=budget,
        model_cost=model_cost,
        search_cost=search_cost,
        search_batch_count=len(batches),
        fetched=fetch_count,
        usable=len(visible_pages),
        baseline_stats=stats["baseline"],
        candidate_stats=stats["deterministic_pair"],
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
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in ARMS
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
        raise ValueError("V2.46.42 deterministic-pair result drifted")
    validate_visible_task(
        {"opaque_id": str(copied.get("opaque_id", "")), "question": "private-visible-content"}
    )
    validate_receipt(copied.get("receipt", {}))
    for arm in ARMS:
        columns, rows = ror._matrix(predictions[arm])
        if tuple(columns) != ror.EXPECTED_COLUMNS or len(rows) != 4:
            raise ValueError("V2.46.42 projected table drifted")
    _columns, baseline_rows = ror._matrix(predictions["baseline"])
    _columns, candidate_rows = ror._matrix(predictions["deterministic_pair"])
    changed = 0
    for baseline, candidate in zip(baseline_rows, candidate_rows, strict=True):
        if baseline[0] != candidate[0] or baseline[2] != candidate[2]:
            raise ValueError("V2.46.42 identity or country monotonicity drifted")
        if baseline[1].casefold() not in UNKNOWN and baseline[1] != candidate[1]:
            raise ValueError("V2.46.42 non-Unknown ROR fact changed")
        if baseline[1] != candidate[1]:
            changed += 1
            if _ror_suffix(candidate[1]) is None:
                raise ValueError("V2.46.42 changed ROR cell is malformed")
    if changed != copied["receipt"]["discovery"].get("admitted_replacement_count"):
        raise ValueError("V2.46.42 admitted replacement count drifted")
    return copied


__all__ = [
    "ARMS",
    "POLICY_ID",
    "ROLE",
    "discover_pairs",
    "entity_bound_ror_suffixes",
    "explicit_ror_suffixes",
    "run_v24642_task",
    "validate_receipt",
    "validate_result",
]
