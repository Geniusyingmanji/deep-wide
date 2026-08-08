"""Visible-only target--value coverage projector at a fixed 30k budget.

The parent V2.48.42 projector covers visible phrases independently.  For wide
table tasks, however, a block that contains only a row entity or only a target
column does not bind the requested value.  This successor ranks structural
blocks by *joint* visible row/target coverage before the inherited relevance,
structure, source-diversity, and atomic table-header closure terms.

Only the visible question and same-forward fetched pages are inputs.  The
component has no file, environment, process, network, model, benchmark label,
gold, evaluator, score, reward, or historical-result capability.  Entropy and
information gain are shadow observations and never assign signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24842_atomic_table_header_closure as parent


POLICY_ID = "v24921_visible_target_value_coverage_projector_v1"
ROLE = "v24921_target_value_coverage_projection"
RECEIPT_ROLE = "v24921_content_free_target_value_coverage_receipt"
TOTAL_CHARACTER_CAP = 30_000
MAXIMUM_PAGE_CHARS = 5_000
BLOCK_CHARACTER_CAP = 1_200
MAXIMUM_VISIBLE_GROUPS = 64
MAXIMUM_QUERY_TERMS = 96
ProjectionPolicy = parent.ProjectionPolicy
payload_sha256 = parent.payload_sha256

_TAGGED_BLOCK = re.compile(
    r"<(?P<tag>[A-Z][A-Z0-9_]{1,31})>\s*(?P<body>.*?)\s*</(?P=tag)>",
    re.DOTALL,
)
_ROW_TAGS = frozenset({"COUNTRIES", "ENTITIES", "ROWS", "ITEMS", "MEMBERS"})
_COLUMN_PATTERNS = structure._COLUMN_PATTERNS


def profile_policy() -> ProjectionPolicy:
    return ProjectionPolicy(
        total_character_cap=TOTAL_CHARACTER_CAP,
        maximum_page_chars=MAXIMUM_PAGE_CHARS,
        block_character_cap=BLOCK_CHARACTER_CAP,
        maximum_visible_groups=MAXIMUM_VISIBLE_GROUPS,
        maximum_query_terms=MAXIMUM_QUERY_TERMS,
    )


def _unique(values: Sequence[str], maximum: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = structure._canonical_phrase(raw)
        if len(value) < 2 or value in structure._STOPWORDS or value in seen:
            continue
        output.append(value)
        seen.add(value)
        if len(output) >= maximum:
            break
    return output


def visible_row_targets(question: str, *, maximum: int = 64) -> list[str]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.21 visible question is absent")
    values: list[str] = []
    for match in _TAGGED_BLOCK.finditer(structure._clean(question)):
        if match.group("tag") not in _ROW_TAGS:
            continue
        for raw in match.group("body").splitlines():
            line = structure._ENUMERATION.sub("", raw).strip()
            line = re.sub(r"\[[A-Za-z][A-Za-z0-9._-]{1,39}\]\s*$", "", line)
            if 2 <= len(line) <= 160:
                values.append(line)
    # Small visible prompts often name a row without a tag.  This deliberately
    # narrow fallback never consults benchmark metadata or inferred labels.
    for pattern in (
        r"(?:return|include|find)\s+(?:the\s+)?row\s+for\s+([^.;\n]+)",
        r"(?:返回|包括|查找)(?:关于|对应)?\s*([^。；\n]{2,160})(?:的)?(?:行|记录)",
    ):
        match = re.search(pattern, question, re.I)
        if match is not None:
            values.append(match.group(1))
    return _unique(values, maximum)


def visible_target_columns(question: str, *, maximum: int = 64) -> list[str]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.21 visible question is absent")
    values: list[str] = []
    visible = structure._clean(question)
    for pattern in _COLUMN_PATTERNS:
        match = pattern.search(visible)
        if match is None:
            continue
        clause = re.split(
            r"(?:不要问|don't ask|do not ask|输出格式|output format)",
            match.group(1),
            maxsplit=1,
            flags=re.I,
        )[0]
        for raw in re.split(r"\s*[|,，、]\s*", clause):
            values.extend(structure._group_parts(raw))
    columns = _unique(values, maximum + 1)
    # The first visible column is normally the entity/row key.  Joint binding
    # must pair rows with value targets, not reward the identity column twice.
    return columns[1:maximum + 1] if len(columns) > 1 else []


def _annotate_target_value(
    blocks: Sequence[Mapping[str, Any]],
    rows: Sequence[str],
    targets: Sequence[str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for raw in blocks:
        block = copy.deepcopy(dict(raw))
        content = str(block["content"])
        row_indexes = [
            index for index, value in enumerate(rows) if structure._contains(content, value)
        ]
        target_indexes = [
            index for index, value in enumerate(targets) if structure._contains(content, value)
        ]
        block["visible_row_indexes"] = row_indexes
        block["visible_target_indexes"] = target_indexes
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
            if header is None or header.get("kind") != "table":
                raise ValueError("V2.49.21 target-value header binding drifted")
            effective_targets.update(
                int(value) for value in header["visible_target_indexes"]
            )
        block["target_value_pair_indexes"] = [
            [int(row), target]
            for row in block["visible_row_indexes"]
            for target in sorted(effective_targets)
        ]
    return output


def _select(
    pages: Sequence[Mapping[str, Any]],
    blocks: Sequence[Mapping[str, Any]],
    groups: Sequence[str],
    rows: Sequence[str],
    targets: Sequence[str],
    policy: ProjectionPolicy,
) -> tuple[list[dict[str, Any]], set[int], dict[str, int], set[tuple[int, int]]]:
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
        values: list[Mapping[str, Any]] = []
        required = block.get("required_table_header_block_ordinal")
        if isinstance(required, int):
            dependency = block_map.get((page, required))
            if dependency is None or dependency.get("kind") != "table":
                raise ValueError("V2.49.21 table-header dependency drifted")
            values.append(dependency)
        values.append(block)
        unique = {
            (int(value["page_ordinal"]), int(value["block_ordinal"])): value
            for value in values
            if (int(value["page_ordinal"]), int(value["block_ordinal"])) not in selected
        }
        return [unique[key] for key in sorted(unique)]

    def incremental_render_cost(values: Sequence[Mapping[str, Any]]) -> int:
        if not values:
            return 0
        page_indexes = {int(value["page_ordinal"]) for value in values}
        if len(page_indexes) != 1:
            raise ValueError("V2.49.21 structural bundle crossed page boundary")
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
            rendered_used + incremental_render_cost(values) <= policy.total_character_cap
            and page_used[page] + content <= policy.maximum_page_chars
        )

    def add(block: Mapping[str, Any]) -> None:
        nonlocal rendered_used, dependency_additions
        values = bundle(block)
        if not values:
            return
        rendered_used += incremental_render_cost(values)
        requested = (int(block["page_ordinal"]), int(block["block_ordinal"]))
        for value in values:
            copied = copy.deepcopy(dict(value))
            key = (int(copied["page_ordinal"]), int(copied["block_ordinal"]))
            if key in selected:
                continue
            dependency_additions += int(key != requested)
            selected[key] = copied
            page_used[key[0]] += len(str(copied["content"]))

    supported_pairs = {
        (int(pair[0]), int(pair[1]))
        for block in blocks
        for pair in block["target_value_pair_indexes"]
    }
    uncovered_pairs = set(supported_pairs)
    while uncovered_pairs:
        candidates = [
            block
            for block in blocks
            if can_add(block)
            and uncovered_pairs.intersection(
                (int(pair[0]), int(pair[1]))
                for pair in block["target_value_pair_indexes"]
            )
        ]
        if not candidates:
            break
        chosen = max(
            candidates,
            key=lambda block: (
                len(
                    uncovered_pairs.intersection(
                        (int(pair[0]), int(pair[1]))
                        for pair in block["target_value_pair_indexes"]
                    )
                ),
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
            (int(pair[0]), int(pair[1]))
            for value in selected.values()
            for pair in value["target_value_pair_indexes"]
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
                len(block["target_value_pair_indexes"]),
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

    # Keep the inherited source-diversity safety: at least one bounded block
    # per page when space remains.
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
                        len(block["target_value_pair_indexes"]),
                        len(block["group_indexes"]),
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
            if (int(block["page_ordinal"]), int(block["block_ordinal"])) not in selected
        ),
        key=lambda block: (
            -len(block["target_value_pair_indexes"]),
            -len(block["visible_row_indexes"]),
            -len(block["visible_target_indexes"]),
            -len(block["group_indexes"]),
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

    retained = {
        index for block in selected.values() for index in block["group_indexes"]
    }
    retained_pairs = {
        (int(pair[0]), int(pair[1]))
        for block in selected.values()
        for pair in block["target_value_pair_indexes"]
    }
    selected_tail = 0
    orphan = 0
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
    }, retained_pairs


def _content_free_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_projector_policy_id": parent.POLICY_ID,
        "policy": copy.deepcopy(dict(value["policy"])),
        "input_page_count": int(value["input_page_count"]),
        "projected_page_count": int(value["projected_page_count"]),
        "input_block_count": int(value["input_block_count"]),
        "projected_block_count": int(value["projected_block_count"]),
        "visible_row_target_count": int(value["visible_row_target_count"]),
        "visible_value_target_count": int(value["visible_value_target_count"]),
        "supported_target_value_pair_count": int(
            value["supported_target_value_pair_count"]
        ),
        "retained_target_value_pair_count": int(
            value["retained_target_value_pair_count"]
        ),
        "missed_target_value_pair_count": int(value["missed_target_value_pair_count"]),
        "retained_supported_visible_requirement_group_count": int(
            value["retained_supported_visible_requirement_group_count"]
        ),
        "projected_rendered_characters": int(value["projected_rendered_characters"]),
        "selected_table_continuation_block_count": int(
            value["selected_table_continuation_block_count"]
        ),
        "table_header_dependency_addition_count": int(
            value["table_header_dependency_addition_count"]
        ),
        "orphan_selected_table_continuation_block_count": int(
            value["orphan_selected_table_continuation_block_count"]
        ),
        "joint_target_value_coverage_prioritized_before_independent_phrase_coverage": True,
        "source_diversity_and_stable_output_order_preserved": True,
        "atomic_table_header_closure_enforced": True,
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
    counts = (
        "input_page_count",
        "projected_page_count",
        "input_block_count",
        "projected_block_count",
        "visible_row_target_count",
        "visible_value_target_count",
        "supported_target_value_pair_count",
        "retained_target_value_pair_count",
        "missed_target_value_pair_count",
        "retained_supported_visible_requirement_group_count",
        "projected_rendered_characters",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
    )
    policy = copied.get("policy")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_projector_policy_id") != parent.POLICY_ID
        or policy
        != {
            "total_character_cap": TOTAL_CHARACTER_CAP,
            "maximum_page_chars": MAXIMUM_PAGE_CHARS,
            "block_character_cap": BLOCK_CHARACTER_CAP,
            "maximum_visible_groups": MAXIMUM_VISIBLE_GROUPS,
            "maximum_query_terms": MAXIMUM_QUERY_TERMS,
        }
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["retained_target_value_pair_count"]
        > copied["supported_target_value_pair_count"]
        or copied["missed_target_value_pair_count"]
        != copied["supported_target_value_pair_count"]
        - copied["retained_target_value_pair_count"]
        or copied["projected_rendered_characters"] > TOTAL_CHARACTER_CAP
        or copied["orphan_selected_table_continuation_block_count"] != 0
        or copied[
            "joint_target_value_coverage_prioritized_before_independent_phrase_coverage"
        ]
        is not True
        or copied["source_diversity_and_stable_output_order_preserved"] is not True
        or copied["atomic_table_header_closure_enforced"] is not True
        or copied["same_forward_page_bytes_only"] is not True
        or copied[
            "additional_search_fetch_model_call_token_context_or_wall_cap"
        ]
        is not False
        or copied["entropy_information_gain_shadow_only"] is not True
        or copied["entropy_or_information_gain_assigns_credit"] is not False
        or copied[
            "contains_question_query_url_host_page_projection_content_hash_opaque_id_or_credential"
        ]
        is not False
        or copied[
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.21 target-value coverage receipt drifted")
    return copied


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    policy = profile_policy()
    stable = structure._stable_pages(pages)
    groups = structure.visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=policy.maximum_visible_groups,
    )
    rows = visible_row_targets(question, maximum=policy.maximum_visible_groups)
    targets = visible_target_columns(
        question, maximum=policy.maximum_visible_groups
    )
    terms = structure._query_terms(question, policy.maximum_query_terms)
    raw_blocks = [
        block for page in stable for block in parent._blocks(page, policy.block_character_cap)
    ]
    blocks = structure._annotate(raw_blocks, groups, terms)
    blocks = _annotate_target_value(blocks, rows, targets)
    selected, retained, closure, retained_pairs = _select(
        stable, blocks, groups, rows, targets, policy
    )
    supported = {
        index
        for index in range(len(groups))
        if any(index in block["group_indexes"] for block in blocks)
    }
    supported_pairs = {
        (int(pair[0]), int(pair[1]))
        for block in blocks
        for pair in block["target_value_pair_indexes"]
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
        "parent_projector_policy_id": parent.POLICY_ID,
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
        "visible_value_target_vector_sha256": payload_sha256(targets),
        "visible_requirement_group_count": len(groups),
        "supported_visible_requirement_group_count": len(supported),
        "retained_supported_visible_requirement_group_count": len(
            supported.intersection(retained)
        ),
        "missed_supported_visible_requirement_group_count": len(supported - retained),
        "visible_row_target_count": len(rows),
        "visible_value_target_count": len(targets),
        "supported_target_value_pair_count": len(supported_pairs),
        "retained_target_value_pair_count": len(supported_pairs & retained_pairs),
        "missed_target_value_pair_count": len(supported_pairs - retained_pairs),
        "input_page_count": len(stable),
        "projected_page_count": len(selected_pages),
        "input_block_count": len(blocks),
        "projected_block_count": len(selected),
        "input_unique_host_count": len({page["host"] for page in stable if page["host"]}),
        "projected_unique_host_count": len(
            {page_map[index]["host"] for index in selected_pages if page_map[index]["host"]}
        ),
        "input_content_characters": sum(len(str(page["content"])) for page in stable),
        "allocated_content_characters": sum(per_page),
        "projected_rendered_characters": len(projection),
        "per_page_allocated_characters": per_page,
        "projected_host_entropy_nats": structure._host_entropy(host_counts),
        **closure,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode()).hexdigest(),
        "content_free_receipt": {},
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
    receipt = copied.get("content_free_receipt")
    projection = copied.get("projection")
    policy = copied.get("policy")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_projector_policy_id") != parent.POLICY_ID
        or policy
        != {
            "total_character_cap": TOTAL_CHARACTER_CAP,
            "maximum_page_chars": MAXIMUM_PAGE_CHARS,
            "block_character_cap": BLOCK_CHARACTER_CAP,
            "maximum_visible_groups": MAXIMUM_VISIBLE_GROUPS,
            "maximum_query_terms": MAXIMUM_QUERY_TERMS,
        }
        or copied.get("visible_question_sha256")
        != hashlib.sha256(question.encode()).hexdigest()
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode()).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or copied.get("projected_rendered_characters") > TOTAL_CHARACTER_CAP
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != receipt
        or receipt["projected_rendered_characters"] != len(projection)
        or copied.get("missed_target_value_pair_count")
        != copied.get("supported_target_value_pair_count")
        - copied.get("retained_target_value_pair_count")
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
        raise ValueError("V2.49.21 target-value projection drifted")
    stable = structure._stable_pages(pages)
    groups = structure.visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=MAXIMUM_VISIBLE_GROUPS,
    )
    rows = visible_row_targets(question, maximum=MAXIMUM_VISIBLE_GROUPS)
    targets = visible_target_columns(question, maximum=MAXIMUM_VISIBLE_GROUPS)
    allocations = copied.get("per_page_allocated_characters")
    if (
        copied.get("visible_requirement_vector_sha256") != payload_sha256(groups)
        or copied.get("visible_row_target_vector_sha256") != payload_sha256(rows)
        or copied.get("visible_value_target_vector_sha256") != payload_sha256(targets)
        or copied.get("input_page_count") != len(stable)
        or not isinstance(allocations, list)
        or len(allocations) != len(stable)
        or any(
            isinstance(number, bool)
            or not isinstance(number, int)
            or not 0 <= number <= MAXIMUM_PAGE_CHARS
            for number in allocations
        )
        or sum(allocations) != copied.get("allocated_content_characters")
    ):
        raise ValueError("V2.49.21 visible input or cap binding drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups
    ):
        raise ValueError("V2.49.21 projection is not reproducible")
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
    "visible_row_targets",
    "visible_target_columns",
]
