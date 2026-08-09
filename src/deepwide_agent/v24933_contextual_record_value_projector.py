"""Unicode-total contextual record/value evidence projection.

V2.49.21 can bind a visible row to a visible target when both phrases occur
inside the same block (or when a long Markdown-table continuation carries an
explicit table-header dependency).  Ordinary web pages commonly put the
target in a short section heading and the row/value in following narrative or
record blocks.  Those blocks therefore had no target-value pair even though
the relationship was visible in the page structure.

This pure successor carries a visible-target context from a bounded heading
to following value-bearing row blocks in the same page section.  Selection
first covers the resulting row-target pairs, then preserves the inherited
visible-requirement, source-diversity, stable-order, 30k total and 5k/page
rules.  A selected context-dependent block atomically includes its heading.

Inputs remain limited to the visible question and same-forward fetched pages.
There is no file, environment, process, network, model, benchmark-label,
gold, evaluator, score, reward, or historical-result capability.  Entropy and
information gain remain shadow-only and never assign signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24842_atomic_table_header_closure as atomic
from . import v24921_target_value_coverage_projector as target_value
from . import v24928_unicode_total_visible_row_compactor as unicode_total


POLICY_ID = "v24933_unicode_total_contextual_record_value_projector_v1"
ROLE = "v24933_contextual_record_value_projection"
RECEIPT_ROLE = "v24933_content_free_contextual_record_value_receipt"
TOTAL_CHARACTER_CAP = target_value.TOTAL_CHARACTER_CAP
MAXIMUM_PAGE_CHARS = target_value.MAXIMUM_PAGE_CHARS
BLOCK_CHARACTER_CAP = target_value.BLOCK_CHARACTER_CAP
MAXIMUM_VISIBLE_GROUPS = target_value.MAXIMUM_VISIBLE_GROUPS
MAXIMUM_QUERY_TERMS = target_value.MAXIMUM_QUERY_TERMS
ProjectionPolicy = target_value.ProjectionPolicy
payload_sha256 = target_value.payload_sha256

_VALUE = re.compile(
    r"(?<![A-Za-z0-9])[-+]?(?:\d{1,3}(?:[ ,]\d{3})+|\d+)"
    r"(?:\.\d+)?(?:\s*(?:%|‰|million|billion|trillion))?(?![A-Za-z0-9])",
    re.I,
)
_MAXIMUM_CONTEXT_CHARACTERS = 800


def profile_policy() -> ProjectionPolicy:
    return target_value.profile_policy()


def _value_like_count(content: str) -> int:
    return len(_VALUE.findall(content))


def _visible_target_alias_groups(
    question: str, *, maximum: int = MAXIMUM_VISIBLE_GROUPS
) -> list[tuple[str, ...]]:
    """Return one alias set per visible value column, excluding the row key."""

    visible = structure._clean(question)
    groups: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for pattern in structure._COLUMN_PATTERNS:
        match = pattern.search(visible)
        if match is None:
            continue
        clause = re.split(
            r"(?:不要问|don't ask|do not ask|输出格式|output format)",
            match.group(1),
            maxsplit=1,
            flags=re.I,
        )[0]
        raw_columns = re.split(r"\s*[|,，、]\s*", clause)
        for raw in raw_columns[1:]:
            aliases: list[str] = []
            alias_seen: set[str] = set()
            for part in structure._group_parts(raw):
                value = structure._canonical_phrase(part)
                if (
                    len(value) >= 2
                    and value not in structure._STOPWORDS
                    and value not in alias_seen
                ):
                    aliases.append(value)
                    alias_seen.add(value)
            group = tuple(aliases)
            if group and group not in seen:
                groups.append(group)
                seen.add(group)
            if len(groups) >= maximum:
                return groups
    return groups


def _annotate_rows_and_targets(
    blocks: Sequence[Mapping[str, Any]],
    rows: Sequence[str],
    target_alias_groups: Sequence[Sequence[str]],
) -> list[dict[str, Any]]:
    """Bind rows to semantic value columns instead of double-counting aliases."""

    output: list[dict[str, Any]] = []
    for raw in blocks:
        block = copy.deepcopy(dict(raw))
        content = str(block["content"])
        block["visible_row_indexes"] = [
            index
            for index, row in enumerate(rows)
            if structure._contains(content, row)
        ]
        block["visible_target_indexes"] = [
            index
            for index, aliases in enumerate(target_alias_groups)
            if any(structure._contains(content, alias) for alias in aliases)
        ]
        output.append(block)
    by_key = {
        (int(block["page_ordinal"]), int(block["block_ordinal"])): block
        for block in output
    }
    for block in output:
        effective_targets = set(int(value) for value in block["visible_target_indexes"])
        required = block.get("required_table_header_block_ordinal")
        if isinstance(required, int):
            header = by_key.get((int(block["page_ordinal"]), required))
            if header is None or str(header.get("kind")) != "table":
                raise ValueError("V2.49.33 table target context drifted")
            effective_targets.update(
                int(value) for value in header["visible_target_indexes"]
            )
        block["target_value_pair_indexes"] = [
            [int(row), target]
            for row in block["visible_row_indexes"]
            for target in sorted(effective_targets)
        ]
    return output


def _annotate_context(
    blocks: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach same-section target context to value-bearing visible rows."""

    output = [copy.deepcopy(dict(block)) for block in blocks]
    by_page: dict[int, list[dict[str, Any]]] = {}
    for block in output:
        by_page.setdefault(int(block["page_ordinal"]), []).append(block)

    for page_blocks in by_page.values():
        context_targets: set[int] = set()
        context_ordinal: int | None = None
        for block in sorted(page_blocks, key=lambda value: int(value["block_ordinal"])):
            kind = str(block["kind"])
            local_targets = {
                int(value) for value in block.get("visible_target_indexes", [])
            }
            local_rows = {
                int(value) for value in block.get("visible_row_indexes", [])
            }
            content = str(block["content"])

            # Any explicit section heading starts a new semantic section.  A
            # short target-only block also acts as a context label, covering
            # common pages whose headings were flattened to plain text.
            if kind == "section":
                context_targets = set(local_targets)
                context_ordinal = (
                    int(block["block_ordinal"]) if context_targets else None
                )
            elif (
                local_targets
                and not local_rows
                and len(content) <= _MAXIMUM_CONTEXT_CHARACTERS
                and kind in {"record", "text"}
            ):
                context_targets = set(local_targets)
                context_ordinal = int(block["block_ordinal"])

            existing_pairs = {
                (int(pair[0]), int(pair[1]))
                for pair in block.get("target_value_pair_indexes", [])
            }
            values = _value_like_count(content)
            context_pairs: set[tuple[int, int]] = set()
            if local_rows and values > 0 and context_targets:
                context_pairs = {
                    (row, target)
                    for row in local_rows
                    for target in context_targets
                }
            # A row-target co-occurrence is only a value-bearing observation
            # when the same block also exposes a value-like token.
            local_value_pairs = existing_pairs if values > 0 else set()
            all_pairs = local_value_pairs | context_pairs
            contributed = context_pairs - local_value_pairs
            block["value_like_token_count"] = values
            block["bound_target_value_pair_indexes"] = [
                [row, target] for row, target in sorted(all_pairs)
            ]
            block["contextual_target_value_pair_indexes"] = [
                [row, target] for row, target in sorted(contributed)
            ]
            block["required_context_block_ordinal"] = (
                context_ordinal if contributed else None
            )
    return output


def _select(
    pages: Sequence[Mapping[str, Any]],
    blocks: Sequence[Mapping[str, Any]],
    groups: Sequence[str],
    policy: ProjectionPolicy,
) -> tuple[
    list[dict[str, Any]],
    set[int],
    set[tuple[int, int]],
    set[tuple[int, int]],
    dict[str, int],
]:
    selected: dict[tuple[int, int], dict[str, Any]] = {}
    page_used: Counter[int] = Counter()
    page_map = {int(page["ordinal"]): page for page in pages}
    block_map = {
        (int(block["page_ordinal"]), int(block["block_ordinal"])): block
        for block in blocks
    }
    rendered_used = 0
    context_dependency_additions = 0
    table_dependency_additions = 0

    def bundle(block: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        page = int(block["page_ordinal"])
        values: list[Mapping[str, Any]] = []
        for field, expected_kind in (
            ("required_table_header_block_ordinal", "table"),
            ("required_context_block_ordinal", None),
        ):
            required = block.get(field)
            if not isinstance(required, int):
                continue
            dependency = block_map.get((page, required))
            if dependency is None or (
                expected_kind is not None
                and str(dependency.get("kind")) != expected_kind
            ):
                raise ValueError("V2.49.33 contextual dependency drifted")
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
        page_indexes = {int(value["page_ordinal"]) for value in values}
        if len(page_indexes) != 1:
            raise ValueError("V2.49.33 dependency crossed a page boundary")
        page = next(iter(page_indexes))
        size = sum(len(str(value["content"])) for value in values)
        if page_used[page]:
            return size + len(values)
        return (
            len(structure._page_header(page_map[page]))
            + size
            + max(0, len(values) - 1)
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
        nonlocal rendered_used, context_dependency_additions, table_dependency_additions
        values = bundle(block)
        if not values:
            return
        rendered_used += incremental_render_cost(values)
        requested = (int(block["page_ordinal"]), int(block["block_ordinal"]))
        table_required = block.get("required_table_header_block_ordinal")
        context_required = block.get("required_context_block_ordinal")
        for value in values:
            copied = copy.deepcopy(dict(value))
            key = (int(copied["page_ordinal"]), int(copied["block_ordinal"]))
            if key in selected:
                continue
            if key != requested and key[1] == table_required:
                table_dependency_additions += 1
            if key != requested and key[1] == context_required:
                context_dependency_additions += 1
            selected[key] = copied
            page_used[key[0]] += len(str(copied["content"]))

    def pairs(block: Mapping[str, Any], field: str) -> set[tuple[int, int]]:
        return {
            (int(pair[0]), int(pair[1])) for pair in block.get(field, [])
        }

    supported_pairs = set().union(
        *(pairs(block, "bound_target_value_pair_indexes") for block in blocks)
    ) if blocks else set()
    uncovered_pairs = set(supported_pairs)
    while uncovered_pairs:
        candidates = [
            block
            for block in blocks
            if can_add(block)
            and uncovered_pairs.intersection(
                pairs(block, "bound_target_value_pair_indexes")
            )
        ]
        if not candidates:
            break
        chosen = max(
            candidates,
            key=lambda block: (
                len(
                    uncovered_pairs.intersection(
                        pairs(block, "bound_target_value_pair_indexes")
                    )
                ),
                len(pairs(block, "contextual_target_value_pair_indexes")),
                int(block["value_like_token_count"]),
                len(block["visible_row_indexes"]),
                len(block["visible_target_indexes"]),
                structure._structure_rank(str(block["kind"])),
                int(block["query_term_count"]),
                -len(str(block["content"])),
                -int(block["page_ordinal"]),
                -int(block["block_ordinal"]),
            ),
        )
        add(chosen)
        uncovered_pairs.difference_update(
            set().union(
                *(
                    pairs(value, "bound_target_value_pair_indexes")
                    for value in selected.values()
                )
            )
            if selected
            else set()
        )

    supported_groups = {
        index
        for index in range(len(groups))
        if any(index in block["group_indexes"] for block in blocks)
    }
    retained_groups = {
        index for block in selected.values() for index in block["group_indexes"]
    }
    uncovered_groups = supported_groups - retained_groups
    while uncovered_groups:
        candidates = [
            block
            for block in blocks
            if can_add(block) and uncovered_groups.intersection(block["group_indexes"])
        ]
        if not candidates:
            break
        chosen = max(
            candidates,
            key=lambda block: (
                len(uncovered_groups.intersection(block["group_indexes"])),
                len(pairs(block, "bound_target_value_pair_indexes")),
                int(block["value_like_token_count"]),
                structure._structure_rank(str(block["kind"])),
                int(block["query_term_count"]),
                -len(str(block["content"])),
                -int(block["page_ordinal"]),
                -int(block["block_ordinal"]),
            ),
        )
        add(chosen)
        uncovered_groups.difference_update(
            index for value in selected.values() for index in value["group_indexes"]
        )

    # Retain one bounded block from each source before filling the remaining
    # budget, preserving the inherited source-diversity safety.
    for page in pages:
        ordinal = int(page["ordinal"])
        if any(key[0] == ordinal for key in selected):
            continue
        candidates = [
            block
            for block in blocks
            if int(block["page_ordinal"]) == ordinal and can_add(block)
        ]
        if candidates:
            add(
                max(
                    candidates,
                    key=lambda block: (
                        len(pairs(block, "bound_target_value_pair_indexes")),
                        len(block["group_indexes"]),
                        int(block["value_like_token_count"]),
                        int(block["query_term_count"]),
                        structure._structure_rank(str(block["kind"])),
                        -int(block["block_ordinal"]),
                    ),
                )
            )

    remaining = sorted(
        (
            block
            for block in blocks
            if (int(block["page_ordinal"]), int(block["block_ordinal"]))
            not in selected
        ),
        key=lambda block: (
            -len(pairs(block, "bound_target_value_pair_indexes")),
            -len(pairs(block, "contextual_target_value_pair_indexes")),
            -len(block["group_indexes"]),
            -int(block["value_like_token_count"]),
            -int(block["query_term_count"]),
            -structure._structure_rank(str(block["kind"])),
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
                    if (int(value["page_ordinal"]), int(value["block_ordinal"]))
                    not in selected
                ]
                progressed = True

    retained_groups = {
        index for block in selected.values() for index in block["group_indexes"]
    }
    retained_pairs = set().union(
        *(
            pairs(block, "bound_target_value_pair_indexes")
            for block in selected.values()
        )
    ) if selected else set()
    retained_contextual_pairs = set().union(
        *(
            pairs(block, "contextual_target_value_pair_indexes")
            for block in selected.values()
        )
    ) if selected else set()
    selected_context_blocks = sum(
        isinstance(block.get("required_context_block_ordinal"), int)
        for block in selected.values()
    )
    selected_table_tails = sum(
        isinstance(block.get("required_table_header_block_ordinal"), int)
        for block in selected.values()
    )
    orphan_context = sum(
        isinstance(block.get("required_context_block_ordinal"), int)
        and (
            int(block["page_ordinal"]),
            int(block["required_context_block_ordinal"]),
        )
        not in selected
        for block in selected.values()
    )
    orphan_table = sum(
        isinstance(block.get("required_table_header_block_ordinal"), int)
        and (
            int(block["page_ordinal"]),
            int(block["required_table_header_block_ordinal"]),
        )
        not in selected
        for block in selected.values()
    )
    return (
        [selected[key] for key in sorted(selected)],
        retained_groups,
        retained_pairs,
        retained_contextual_pairs,
        {
            "selected_context_dependent_block_count": selected_context_blocks,
            "context_dependency_addition_count": context_dependency_additions,
            "orphan_selected_context_dependent_block_count": orphan_context,
            "selected_table_continuation_block_count": selected_table_tails,
            "table_header_dependency_addition_count": table_dependency_additions,
            "orphan_selected_table_continuation_block_count": orphan_table,
        },
    )


def _content_free_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    names = (
        "input_page_count",
        "projected_page_count",
        "input_block_count",
        "projected_block_count",
        "visible_row_target_count",
        "visible_value_target_count",
        "value_bearing_row_block_count",
        "context_dependent_value_block_count",
        "supported_bound_target_value_pair_count",
        "retained_bound_target_value_pair_count",
        "missed_bound_target_value_pair_count",
        "supported_contextual_target_value_pair_count",
        "retained_contextual_target_value_pair_count",
        "missed_contextual_target_value_pair_count",
        "retained_supported_visible_requirement_group_count",
        "projected_rendered_characters",
        "selected_context_dependent_block_count",
        "context_dependency_addition_count",
        "orphan_selected_context_dependent_block_count",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
    )
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_projector_policy_id": unicode_total.POLICY_ID,
        "policy": copy.deepcopy(dict(value["policy"])),
        **{name: int(value[name]) for name in names},
        "bounded_visible_target_context_only": True,
        "value_bearing_row_target_pairs_prioritized_before_independent_phrase_coverage": True,
        "context_and_table_dependencies_atomic": True,
        "source_diversity_and_stable_output_order_preserved": True,
        "same_forward_page_bytes_only": True,
        "additional_search_fetch_model_call_token_context_or_wall_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_projection_content_hash_opaque_id_or_credential": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return validate_receipt(receipt)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    count_names = (
        "input_page_count",
        "projected_page_count",
        "input_block_count",
        "projected_block_count",
        "visible_row_target_count",
        "visible_value_target_count",
        "value_bearing_row_block_count",
        "context_dependent_value_block_count",
        "supported_bound_target_value_pair_count",
        "retained_bound_target_value_pair_count",
        "missed_bound_target_value_pair_count",
        "supported_contextual_target_value_pair_count",
        "retained_contextual_target_value_pair_count",
        "missed_contextual_target_value_pair_count",
        "retained_supported_visible_requirement_group_count",
        "projected_rendered_characters",
        "selected_context_dependent_block_count",
        "context_dependency_addition_count",
        "orphan_selected_context_dependent_block_count",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
    )
    expected_policy = {
        "total_character_cap": TOTAL_CHARACTER_CAP,
        "maximum_page_chars": MAXIMUM_PAGE_CHARS,
        "block_character_cap": BLOCK_CHARACTER_CAP,
        "maximum_visible_groups": MAXIMUM_VISIBLE_GROUPS,
        "maximum_query_terms": MAXIMUM_QUERY_TERMS,
    }
    flags = {
        "bounded_visible_target_context_only": True,
        "value_bearing_row_target_pairs_prioritized_before_independent_phrase_coverage": True,
        "context_and_table_dependencies_atomic": True,
        "source_diversity_and_stable_output_order_preserved": True,
        "same_forward_page_bytes_only": True,
        "additional_search_fetch_model_call_token_context_or_wall_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_projection_content_hash_opaque_id_or_credential": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_projector_policy_id") != unicode_total.POLICY_ID
        or copied.get("policy") != expected_policy
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_names
        )
        or copied["retained_bound_target_value_pair_count"]
        > copied["supported_bound_target_value_pair_count"]
        or copied["missed_bound_target_value_pair_count"]
        != copied["supported_bound_target_value_pair_count"]
        - copied["retained_bound_target_value_pair_count"]
        or copied["retained_contextual_target_value_pair_count"]
        > copied["supported_contextual_target_value_pair_count"]
        or copied["missed_contextual_target_value_pair_count"]
        != copied["supported_contextual_target_value_pair_count"]
        - copied["retained_contextual_target_value_pair_count"]
        or copied["projected_rendered_characters"] > TOTAL_CHARACTER_CAP
        or copied["orphan_selected_context_dependent_block_count"] != 0
        or copied["orphan_selected_table_continuation_block_count"] != 0
        or any(copied.get(name) is not expected for name, expected in flags.items())
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.33 contextual record/value receipt drifted")
    return copied


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    compacted_pages, compaction_receipt = unicode_total.compact_pages(question, pages)
    policy = profile_policy()
    stable = structure._stable_pages(compacted_pages)
    groups = structure.visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=policy.maximum_visible_groups,
    )
    rows = target_value.visible_row_targets(
        question, maximum=policy.maximum_visible_groups
    )
    target_alias_groups = _visible_target_alias_groups(
        question, maximum=policy.maximum_visible_groups
    )
    terms = structure._query_terms(question, policy.maximum_query_terms)
    raw_blocks = [
        block
        for page in stable
        for block in atomic._blocks(page, policy.block_character_cap)
    ]
    blocks = structure._annotate(raw_blocks, groups, terms)
    blocks = _annotate_rows_and_targets(blocks, rows, target_alias_groups)
    blocks = _annotate_context(blocks)
    selected, retained_groups, retained_pairs, retained_contextual, closure = _select(
        stable, blocks, groups, policy
    )
    supported_groups = {
        index
        for index in range(len(groups))
        if any(index in block["group_indexes"] for block in blocks)
    }
    supported_pairs = {
        (int(pair[0]), int(pair[1]))
        for block in blocks
        for pair in block["bound_target_value_pair_indexes"]
    }
    supported_contextual = {
        (int(pair[0]), int(pair[1]))
        for block in blocks
        for pair in block["contextual_target_value_pair_indexes"]
    }
    projection = structure._render(stable, selected)
    selected_pages = {int(block["page_ordinal"]) for block in selected}
    page_map = {int(page["ordinal"]): page for page in stable}
    per_page = [
        sum(
            len(str(block["content"]))
            for block in selected
            if int(block["page_ordinal"]) == int(page["ordinal"])
        )
        for page in stable
    ]
    host_counts = Counter(
        str(page_map[index]["host"]) or "unknown-host" for index in selected_pages
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_projector_policy_id": unicode_total.POLICY_ID,
        "policy": {
            "total_character_cap": policy.total_character_cap,
            "maximum_page_chars": policy.maximum_page_chars,
            "block_character_cap": policy.block_character_cap,
            "maximum_visible_groups": policy.maximum_visible_groups,
            "maximum_query_terms": policy.maximum_query_terms,
        },
        "visible_question_sha256": hashlib.sha256(question.encode()).hexdigest(),
        "visible_requirement_vector_sha256": payload_sha256(groups),
        "visible_row_target_vector_sha256": payload_sha256(rows),
        "visible_value_target_vector_sha256": payload_sha256(target_alias_groups),
        "visible_requirement_group_count": len(groups),
        "supported_visible_requirement_group_count": len(supported_groups),
        "retained_supported_visible_requirement_group_count": len(
            supported_groups.intersection(retained_groups)
        ),
        "visible_row_target_count": len(rows),
        "visible_value_target_count": len(target_alias_groups),
        "value_bearing_row_block_count": sum(
            bool(block["visible_row_indexes"])
            and int(block["value_like_token_count"]) > 0
            for block in blocks
        ),
        "context_dependent_value_block_count": sum(
            bool(block["contextual_target_value_pair_indexes"])
            for block in blocks
        ),
        "supported_bound_target_value_pair_count": len(supported_pairs),
        "retained_bound_target_value_pair_count": len(
            supported_pairs.intersection(retained_pairs)
        ),
        "missed_bound_target_value_pair_count": len(supported_pairs - retained_pairs),
        "supported_contextual_target_value_pair_count": len(supported_contextual),
        "retained_contextual_target_value_pair_count": len(
            supported_contextual.intersection(retained_contextual)
        ),
        "missed_contextual_target_value_pair_count": len(
            supported_contextual - retained_contextual
        ),
        "input_page_count": len(stable),
        "projected_page_count": len(selected_pages),
        "input_block_count": len(blocks),
        "projected_block_count": len(selected),
        "input_content_characters": sum(
            len(str(page["content"])) for page in stable
        ),
        "allocated_content_characters": sum(per_page),
        "projected_rendered_characters": len(projection),
        "per_page_allocated_characters": per_page,
        "projected_host_entropy_nats": structure._host_entropy(host_counts),
        **closure,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode()).hexdigest(),
        "content_free_receipt": {},
        "unicode_total_compaction_receipt": compaction_receipt,
        "stable_page_and_block_output_order_preserved": True,
        "same_forward_page_bytes_only": True,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["content_free_receipt"] = _content_free_receipt(value)
    value["artifact_payload_sha256"] = payload_sha256(value)
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
    seal = unsigned.pop("artifact_payload_sha256", None)
    projection = copied.get("projection")
    receipt = copied.get("content_free_receipt")
    allocations = copied.get("per_page_allocated_characters")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_projector_policy_id") != unicode_total.POLICY_ID
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode()).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or copied.get("projected_rendered_characters") > TOTAL_CHARACTER_CAP
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != receipt
        or receipt["projected_rendered_characters"] != len(projection)
        or unicode_total.validate_receipt(
            copied.get("unicode_total_compaction_receipt", {})
        )
        != copied.get("unicode_total_compaction_receipt")
        or not isinstance(allocations, list)
        or sum(allocations) != copied.get("allocated_content_characters")
        or any(
            isinstance(number, bool)
            or not isinstance(number, int)
            or not 0 <= number <= MAXIMUM_PAGE_CHARS
            for number in allocations
        )
        or copied.get("orphan_selected_context_dependent_block_count") != 0
        or copied.get("orphan_selected_table_continuation_block_count") != 0
        or copied.get("stable_page_and_block_output_order_preserved") is not True
        or copied.get("same_forward_page_bytes_only") is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.33 contextual record/value projection drifted")
    compacted_pages, _compaction = unicode_total.compact_pages(question, pages)
    stable = structure._stable_pages(compacted_pages)
    groups = structure.visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=MAXIMUM_VISIBLE_GROUPS,
    )
    rows = target_value.visible_row_targets(question, maximum=MAXIMUM_VISIBLE_GROUPS)
    target_alias_groups = _visible_target_alias_groups(
        question, maximum=MAXIMUM_VISIBLE_GROUPS
    )
    if (
        copied.get("visible_requirement_vector_sha256") != payload_sha256(groups)
        or copied.get("visible_row_target_vector_sha256") != payload_sha256(rows)
        or copied.get("visible_value_target_vector_sha256")
        != payload_sha256(target_alias_groups)
        or copied.get("input_page_count") != len(stable)
        or len(allocations) != len(stable)
    ):
        raise ValueError("V2.49.33 visible input binding drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups
    ):
        raise ValueError("V2.49.33 projection is not reproducible")
    return copied


__all__ = [
    "BLOCK_CHARACTER_CAP",
    "MAXIMUM_PAGE_CHARS",
    "MAXIMUM_QUERY_TERMS",
    "MAXIMUM_VISIBLE_GROUPS",
    "POLICY_ID",
    "ROLE",
    "TOTAL_CHARACTER_CAP",
    "build_projection",
    "payload_sha256",
    "profile_policy",
    "validate_projection",
    "validate_receipt",
]
