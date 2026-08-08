"""Visible-only atomic table-header closure for fixed-budget projection.

This successor preserves V2.48.39 relevance, document-set coverage, stable
page order, and the rendered-character budget. Its only selection change is a
structural dependency: every selected continuation block from a long table
atomically requires the first block of that same table span. If the bundle
does not fit, the continuation is not selected. Entropy and information gain
remain shadow measurements and never assign credit.

Only the visible question and same-forward fetched pages are accepted. The
component has no file, environment, process, network, model, benchmark-label,
gold, evaluator, score, reward, or historical-result capability.
"""

from __future__ import annotations

import copy
import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as parent


POLICY_ID = "v24842_visible_atomic_table_header_closure_v1"
ROLE = "v24842_atomic_table_header_closure_projection"
ProjectionPolicy = parent.ProjectionPolicy
DEFAULT_TOTAL_CHARACTER_CAP = parent.DEFAULT_TOTAL_CHARACTER_CAP
DEFAULT_MAXIMUM_PAGE_CHARS = parent.DEFAULT_MAXIMUM_PAGE_CHARS
DEFAULT_BLOCK_CHARACTER_CAP = parent.DEFAULT_BLOCK_CHARACTER_CAP
DEFAULT_MAXIMUM_VISIBLE_GROUPS = parent.DEFAULT_MAXIMUM_VISIBLE_GROUPS
DEFAULT_MAXIMUM_QUERY_TERMS = parent.DEFAULT_MAXIMUM_QUERY_TERMS
payload_sha256 = parent.payload_sha256
visible_requirement_groups = parent.visible_requirement_groups


def _blocks(page: Mapping[str, Any], cap: int) -> list[dict[str, Any]]:
    """Split structural spans and bind long-table continuations to their header."""

    spans: list[tuple[str, str, int]] = []
    current: list[str] = []
    current_kind = "text"
    span_ordinal = 0

    def flush() -> None:
        nonlocal current, current_kind, span_ordinal
        text = "\n".join(current).strip()
        if text:
            span_ordinal += 1
            spans.append((current_kind, text, span_ordinal))
        current = []
        current_kind = "text"

    for raw in str(page["content"]).splitlines():
        if not raw.strip():
            flush()
            continue
        kind = parent._line_kind(raw)
        if current and (
            (kind == "table") != (current_kind == "table")
            or (kind == "record") != (current_kind == "record")
        ):
            flush()
        if not current:
            current_kind = kind
        elif current_kind == "section" and kind == "text":
            current_kind = "section"
        current.append(raw.rstrip())
    flush()

    output: list[dict[str, Any]] = []
    block_ordinal = 0
    for kind, span, structure_group_ordinal in spans:
        pieces = parent._split_long_text(span, cap)
        header_block_ordinal = block_ordinal + 1 if kind == "table" and pieces else None
        for piece_ordinal, piece in enumerate(pieces, 1):
            block_ordinal += 1
            output.append(
                {
                    "page_ordinal": int(page["ordinal"]),
                    "block_ordinal": block_ordinal,
                    "kind": kind,
                    "content": piece,
                    "content_sha256": hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                    "structure_group_ordinal": structure_group_ordinal,
                    "table_piece_ordinal": piece_ordinal if kind == "table" else 0,
                    "required_table_header_block_ordinal": (
                        header_block_ordinal
                        if kind == "table" and piece_ordinal > 1
                        else None
                    ),
                }
            )
    return output


def _select(
    pages: Sequence[Mapping[str, Any]],
    blocks: Sequence[Mapping[str, Any]],
    groups: Sequence[str],
    policy: ProjectionPolicy,
) -> tuple[list[dict[str, Any]], set[int], dict[str, int]]:
    selected: dict[tuple[int, int], dict[str, Any]] = {}
    page_used: Counter[int] = Counter()
    page_map = {int(page["ordinal"]): page for page in pages}
    block_map = {
        (int(block["page_ordinal"]), int(block["block_ordinal"])): block
        for block in blocks
    }
    rendered_used = 0
    dependency_additions = 0

    def bundle(block: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        page = int(block["page_ordinal"])
        required = block.get("required_table_header_block_ordinal")
        values: list[Mapping[str, Any]] = []
        if isinstance(required, int):
            dependency = block_map.get((page, required))
            if dependency is None or dependency.get("kind") != "table":
                raise ValueError("V2.48.42 table-header dependency drifted")
            values.append(dependency)
        values.append(block)
        unique = {
            (int(value["page_ordinal"]), int(value["block_ordinal"])): value
            for value in values
            if (
                int(value["page_ordinal"]), int(value["block_ordinal"])
            )
            not in selected
        }
        return [unique[key] for key in sorted(unique)]

    def incremental_render_cost(values: Sequence[Mapping[str, Any]]) -> int:
        if not values:
            return 0
        pages_in_bundle = {int(value["page_ordinal"]) for value in values}
        if len(pages_in_bundle) != 1:
            raise ValueError("V2.48.42 structural bundle crossed page boundary")
        page = next(iter(pages_in_bundle))
        size = sum(len(str(value["content"])) for value in values)
        count = len(values)
        if page_used[page]:
            return size + count
        return (
            len(parent._page_header(page_map[page]))
            + size
            + max(0, count - 1)
            + (2 if selected else 0)
        )

    def can_add(block: Mapping[str, Any]) -> bool:
        values = bundle(block)
        if not values:
            return False
        page = int(block["page_ordinal"])
        content = sum(len(str(value["content"])) for value in values)
        return (
            rendered_used + incremental_render_cost(values)
            <= policy.total_character_cap
            and page_used[page] + content <= policy.maximum_page_chars
        )

    def add(block: Mapping[str, Any]) -> None:
        nonlocal rendered_used, dependency_additions
        values = bundle(block)
        if not values:
            return
        rendered_used += incremental_render_cost(values)
        requested_key = (
            int(block["page_ordinal"]),
            int(block["block_ordinal"]),
        )
        for value in values:
            copied = copy.deepcopy(dict(value))
            key = (
                int(copied["page_ordinal"]),
                int(copied["block_ordinal"]),
            )
            if key in selected:
                continue
            if key != requested_key:
                dependency_additions += 1
            selected[key] = copied
            page_used[key[0]] += len(str(copied["content"]))

    supported = {
        index
        for index in range(len(groups))
        if any(index in block["group_indexes"] for block in blocks)
    }
    uncovered = set(supported)
    while uncovered:
        candidates = [
            block
            for block in blocks
            if can_add(block) and uncovered.intersection(block["group_indexes"])
        ]
        if not candidates:
            break
        chosen = max(
            candidates,
            key=lambda block: (
                len(uncovered.intersection(block["group_indexes"])),
                parent._structure_rank(str(block["kind"])),
                int(block["query_term_count"]),
                -len(str(block["content"])),
                -int(block["page_ordinal"]),
                -int(block["block_ordinal"]),
            ),
        )
        add(chosen)
        uncovered.difference_update(
            index
            for value in selected.values()
            for index in value["group_indexes"]
        )

    for page in pages:
        ordinal = int(page["ordinal"])
        if any(key[0] == ordinal for key in selected):
            continue
        candidates = [
            block
            for block in blocks
            if int(block["page_ordinal"]) == ordinal and can_add(block)
        ]
        if not candidates:
            continue
        add(
            max(
                candidates,
                key=lambda block: (
                    len(block["group_indexes"]),
                    int(block["query_term_count"]),
                    parent._structure_rank(str(block["kind"])),
                    -int(block["block_ordinal"]),
                ),
            )
        )

    remaining = sorted(
        (
            block
            for block in blocks
            if (
                int(block["page_ordinal"]), int(block["block_ordinal"])
            )
            not in selected
        ),
        key=lambda block: (
            -len(block["group_indexes"]),
            -int(block["query_term_count"]),
            -parent._structure_rank(str(block["kind"])),
            int(block["page_ordinal"]),
            int(block["block_ordinal"]),
        ),
    )
    progressed = True
    while progressed:
        progressed = False
        for page in pages:
            ordinal = int(page["ordinal"])
            chosen = next(
                (
                    block
                    for block in remaining
                    if int(block["page_ordinal"]) == ordinal and can_add(block)
                ),
                None,
            )
            if chosen is not None:
                add(chosen)
                remaining = [
                    value
                    for value in remaining
                    if (
                        int(value["page_ordinal"]), int(value["block_ordinal"])
                    )
                    not in selected
                ]
                progressed = True

    retained = {
        index for block in selected.values() for index in block["group_indexes"]
    }
    orphan = 0
    selected_tail = 0
    for block in selected.values():
        required = block.get("required_table_header_block_ordinal")
        if isinstance(required, int):
            selected_tail += 1
            if (int(block["page_ordinal"]), required) not in selected:
                orphan += 1
    return [selected[key] for key in sorted(selected)], retained, {
        "selected_table_continuation_block_count": selected_tail,
        "table_header_dependency_addition_count": dependency_additions,
        "orphan_selected_table_continuation_block_count": orphan,
    }


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
    policy: ProjectionPolicy | None = None,
) -> dict[str, Any]:
    chosen = policy or ProjectionPolicy()
    chosen.validate()
    stable = parent._stable_pages(pages)
    groups = visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=chosen.maximum_visible_groups,
    )
    terms = parent._query_terms(question, chosen.maximum_query_terms)
    raw_blocks = [
        block for page in stable for block in _blocks(page, chosen.block_character_cap)
    ]
    blocks = parent._annotate(raw_blocks, groups, terms)
    selected, retained, closure = _select(stable, blocks, groups, chosen)
    supported = {
        index
        for index in range(len(groups))
        if any(index in block["group_indexes"] for block in blocks)
    }
    projection = parent._render(stable, selected)
    selected_pages = {int(block["page_ordinal"]) for block in selected}
    page_map = {int(page["ordinal"]): page for page in stable}
    host_counts = Counter(
        str(page_map[ordinal]["host"]) or "unknown-host" for ordinal in selected_pages
    )
    input_characters = sum(len(str(page["content"])) for page in stable)
    allocated = sum(len(str(block["content"])) for block in selected)
    per_page = [
        sum(
            len(str(block["content"]))
            for block in selected
            if int(block["page_ordinal"]) == int(page["ordinal"])
        )
        for page in stable
    ]
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "policy": {
            "total_character_cap": chosen.total_character_cap,
            "maximum_page_chars": chosen.maximum_page_chars,
            "block_character_cap": chosen.block_character_cap,
            "maximum_visible_groups": chosen.maximum_visible_groups,
            "maximum_query_terms": chosen.maximum_query_terms,
        },
        "visible_question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "visible_requirement_vector_sha256": payload_sha256(groups),
        "visible_requirement_group_count": len(groups),
        "supported_visible_requirement_group_count": len(supported),
        "retained_supported_visible_requirement_group_count": len(
            supported.intersection(retained)
        ),
        "missed_supported_visible_requirement_group_count": len(supported - retained),
        "visible_query_term_count": len(terms),
        "input_page_count": len(stable),
        "projected_page_count": len(selected_pages),
        "input_block_count": len(blocks),
        "projected_block_count": len(selected),
        "projected_block_kind_counts": dict(
            sorted(Counter(str(block["kind"]) for block in selected).items())
        ),
        "input_unique_host_count": len(
            {page["host"] for page in stable if page["host"]}
        ),
        "projected_unique_host_count": len(
            {
                page_map[index]["host"]
                for index in selected_pages
                if page_map[index]["host"]
            }
        ),
        "input_content_characters": input_characters,
        "allocated_content_characters": allocated,
        "projected_rendered_characters": len(projection),
        "truncated_content_characters": max(0, input_characters - allocated),
        "per_page_allocated_characters": per_page,
        "per_page_content_sha256": [str(page["content_sha256"]) for page in stable],
        "selected_block_content_sha256": [
            str(block["content_sha256"]) for block in selected
        ],
        "projected_host_entropy_nats": parent._host_entropy(host_counts),
        **closure,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode("utf-8")).hexdigest(),
        "stable_first_seen_page_order_preserved": True,
        "selected_block_order_within_page_preserved": True,
        "atomic_table_header_closure_enforced": True,
        "insufficient_bundle_budget_drops_dependent_table_continuation": True,
        "table_and_record_lines_split_only_when_single_line_exceeds_block_cap": True,
        "page_content_summarized_or_fabricated": False,
        "provider_narrative_or_search_snippet_forwarded": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_projection(
        value,
        question=question,
        pages=pages,
        explicit_groups=explicit_groups,
        replay=False,
    )


def validate_projection(
    value: Mapping[str, Any],
    *,
    question: str,
    pages: Sequence[Mapping[str, Any]],
    explicit_groups: Sequence[str] | None = None,
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    raw_policy = copied.get("policy")
    allocations = copied.get("per_page_allocated_characters")
    projection = copied.get("projection")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(raw_policy, Mapping)
        or set(raw_policy)
        != {
            "total_character_cap",
            "maximum_page_chars",
            "block_character_cap",
            "maximum_visible_groups",
            "maximum_query_terms",
        }
        or copied.get("visible_question_sha256")
        != hashlib.sha256(question.encode("utf-8")).hexdigest()
        or not isinstance(allocations, list)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in allocations
        )
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or copied.get("projected_rendered_characters")
        > int(raw_policy.get("total_character_cap", -1))
        or copied.get("allocated_content_characters") != sum(allocations)
        or copied.get("missed_supported_visible_requirement_group_count")
        != copied.get("supported_visible_requirement_group_count")
        - copied.get("retained_supported_visible_requirement_group_count")
        or copied.get("orphan_selected_table_continuation_block_count") != 0
        or copied.get("atomic_table_header_closure_enforced") is not True
        or copied.get(
            "insufficient_bundle_budget_drops_dependent_table_continuation"
        )
        is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.42 atomic table-header receipt drifted")
    policy = ProjectionPolicy(**dict(raw_policy))
    policy.validate()
    stable = parent._stable_pages(pages)
    groups = visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=policy.maximum_visible_groups,
    )
    if (
        copied.get("visible_requirement_vector_sha256") != payload_sha256(groups)
        or copied.get("visible_requirement_group_count") != len(groups)
        or len(allocations) != len(stable)
        or copied.get("input_page_count") != len(stable)
        or copied.get("per_page_content_sha256")
        != [page["content_sha256"] for page in stable]
        or sum(allocations) > policy.total_character_cap
        or any(number > policy.maximum_page_chars for number in allocations)
    ):
        raise ValueError("V2.48.42 projection input or cap binding drifted")
    if replay and copied != build_projection(
        question,
        pages,
        explicit_groups=explicit_groups,
        policy=policy,
    ):
        raise ValueError("V2.48.42 projection is not reproducible")
    return copied


__all__ = [
    "POLICY_ID",
    "ProjectionPolicy",
    "build_projection",
    "payload_sha256",
    "validate_projection",
    "visible_requirement_groups",
]
