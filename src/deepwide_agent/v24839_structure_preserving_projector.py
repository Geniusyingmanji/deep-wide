"""Visible-only structure-preserving information-bottleneck projection.

The projector is a pure evidence-to-context component.  It first inspects
fetched pages as deterministic structural blocks, then selects a fixed-budget
document set that covers visible requirements and preserves table/record
boundaries.  Selected blocks are rendered in original page and block order.

Only the visible question and same-forward fetched pages are inputs.  The
component has no file, environment, process, network, model, benchmark-label,
gold, evaluator, score, reward, or historical-result capability.  Entropy and
information gain remain shadow measurements and never assign credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url


POLICY_ID = "v24839_visible_structure_preserving_information_bottleneck_v1"
ROLE = "v24839_structure_preserving_projection"
DEFAULT_TOTAL_CHARACTER_CAP = 16_000
DEFAULT_MAXIMUM_PAGE_CHARS = 5_000
DEFAULT_BLOCK_CHARACTER_CAP = 1_200
DEFAULT_MAXIMUM_VISIBLE_GROUPS = 64
DEFAULT_MAXIMUM_QUERY_TERMS = 96

_COLUMN_PATTERNS = (
    re.compile(r"(?:列名|栏名)(?:依次)?(?:为|是)\s*[：:]?\s*([^。\n]+)", re.I),
    re.compile(r"column names?[^:\n]*[：:]\s*([^\n]+)", re.I),
    re.compile(r"columns?[^:\n]*[：:]\s*([^\n]+)", re.I),
)
_TAGGED_BLOCK = re.compile(
    r"<(?P<tag>[A-Z][A-Z0-9_]{1,31})>\s*(?P<body>.*?)\s*</(?P=tag)>",
    re.DOTALL,
)
_BRACKET_CODE = re.compile(r"\[([A-Za-z][A-Za-z0-9._-]{1,39})\]")
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9._-]{1,39}|[\u4e00-\u9fff]{2,16}")
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
_HEADING_LINE = re.compile(
    r"^\s*(?:#{1,6}\s+|<h[1-6]\b|(?:section|chapter)\s+\d+\b)", re.I
)
_RECORD_LINE = re.compile(
    r"^\s*(?:[\"']?[^\n:|]{1,80}[\"']?\s*[:：=]|[-*]\s+[^\n]{1,160})"
)
_ENUMERATION = re.compile(r"^\s*(?:\d{1,3}[.)、]|[-*])\s*")
_STOPWORDS = frozenset(
    {
        "about",
        "answer",
        "column",
        "columns",
        "data",
        "exact",
        "format",
        "from",
        "markdown",
        "only",
        "output",
        "please",
        "public",
        "result",
        "return",
        "sources",
        "table",
        "these",
        "this",
        "unknown",
        "use",
        "using",
        "with",
        "一个",
        "不要",
        "使用",
        "依次",
        "公开",
        "关于",
        "列名",
        "数据",
        "未知",
        "格式",
        "来源",
        "表格",
        "输出",
        "返回",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class ProjectionPolicy:
    total_character_cap: int = DEFAULT_TOTAL_CHARACTER_CAP
    maximum_page_chars: int = DEFAULT_MAXIMUM_PAGE_CHARS
    block_character_cap: int = DEFAULT_BLOCK_CHARACTER_CAP
    maximum_visible_groups: int = DEFAULT_MAXIMUM_VISIBLE_GROUPS
    maximum_query_terms: int = DEFAULT_MAXIMUM_QUERY_TERMS

    def validate(self) -> None:
        for name in (
            "total_character_cap",
            "maximum_page_chars",
            "block_character_cap",
            "maximum_visible_groups",
            "maximum_query_terms",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"V2.48.39 {name} must be a positive integer")
        if self.block_character_cap > self.maximum_page_chars:
            raise ValueError("V2.48.39 block cap exceeds per-page cap")
        if self.maximum_page_chars > self.total_character_cap:
            raise ValueError("V2.48.39 per-page cap exceeds total cap")


def _clean(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _canonical_phrase(value: object) -> str:
    return " ".join(_clean(value).casefold().split()).strip(" |,，、.;；:：`'\"")


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").casefold()
    except ValueError:
        return ""


def _page(raw: Mapping[str, Any], ordinal: int) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    canonical = canonicalize_url(str(raw.get("url", "")))
    content = _clean(raw.get("raw_content") or raw.get("content") or "")
    if not canonical or not content:
        return None
    return {
        "ordinal": ordinal,
        "title": " ".join(str(raw.get("title", "")).split())[:500],
        "url": canonical,
        "host": _host(canonical),
        "content": content,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def _stable_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(pages, (str, bytes)):
        raise ValueError("V2.48.39 page vector is not a sequence of mappings")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(pages, 1):
        page = _page(raw, ordinal)
        if page is None or page["url"] in seen:
            continue
        seen.add(page["url"])
        output.append(page)
    return output


def _group_parts(value: object) -> list[str]:
    raw = _ENUMERATION.sub("", _clean(value)).strip().strip("|,，、.;；")
    if not raw or len(raw) > 240:
        return []
    output: list[str] = []
    without_codes = _BRACKET_CODE.sub(" ", raw)
    label = _canonical_phrase(re.sub(r"@20[0-3][0-9]\b", " ", without_codes))
    if 2 <= len(label) <= 160 and label not in _STOPWORDS:
        output.append(label)
    output.extend(
        _canonical_phrase(match.group(1)) for match in _BRACKET_CODE.finditer(raw)
    )
    return [item for item in output if len(item) >= 2 and item not in _STOPWORDS]


def visible_requirement_groups(
    question: str,
    *,
    explicit_groups: Sequence[str] | None = None,
    maximum_groups: int = DEFAULT_MAXIMUM_VISIBLE_GROUPS,
) -> list[str]:
    """Derive requirements from explicit visible syntax, never benchmark metadata."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.48.39 visible question is absent")
    values: list[str] = []
    if explicit_groups is not None:
        if isinstance(explicit_groups, (str, bytes)):
            raise ValueError("V2.48.39 explicit group vector drifted")
        for raw in explicit_groups:
            if not isinstance(raw, str):
                raise ValueError("V2.48.39 explicit group is not text")
            values.extend(_group_parts(raw))
    visible = _clean(question)
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
            values.extend(_group_parts(raw))
    for match in _TAGGED_BLOCK.finditer(visible):
        for line in match.group("body").splitlines():
            values.extend(_group_parts(line))
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            unique.append(value)
            seen.add(value)
        if len(unique) >= maximum_groups:
            break
    return unique


def _query_terms(question: str, maximum: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN.finditer(_clean(question)):
        value = _canonical_phrase(match.group(0))
        if value in _STOPWORDS or value in seen or len(value) < 2:
            continue
        seen.add(value)
        output.append(value)
        if len(output) >= maximum:
            break
    return output


def _line_kind(line: str) -> str:
    if _TABLE_LINE.match(line):
        return "table"
    if _HEADING_LINE.match(line):
        return "section"
    if _RECORD_LINE.match(line):
        return "record"
    return "text"


def _split_long_text(text: str, cap: int) -> list[str]:
    value = text.strip()
    if not value:
        return []
    if len(value) <= cap:
        return [value]
    output: list[str] = []
    current: list[str] = []
    used = 0
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        pieces = [line[index : index + cap] for index in range(0, len(line), cap)]
        for piece in pieces:
            extra = len(piece) + (1 if current else 0)
            if current and used + extra > cap:
                output.append("\n".join(current))
                current, used = [], 0
            current.append(piece)
            used += len(piece) + (1 if len(current) > 1 else 0)
    if current:
        output.append("\n".join(current))
    return output


def _blocks(page: Mapping[str, Any], cap: int) -> list[dict[str, Any]]:
    spans: list[tuple[str, str]] = []
    current: list[str] = []
    current_kind = "text"

    def flush() -> None:
        nonlocal current, current_kind
        text = "\n".join(current).strip()
        if text:
            spans.append((current_kind, text))
        current = []
        current_kind = "text"

    for raw in str(page["content"]).splitlines():
        if not raw.strip():
            flush()
            continue
        kind = _line_kind(raw)
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
    ordinal = 0
    for kind, span in spans:
        for piece in _split_long_text(span, cap):
            ordinal += 1
            output.append(
                {
                    "page_ordinal": int(page["ordinal"]),
                    "block_ordinal": ordinal,
                    "kind": kind,
                    "content": piece,
                    "content_sha256": hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                }
            )
    return output


def _contains(text: str, phrase: str) -> bool:
    haystack = _canonical_phrase(text)
    needle = _canonical_phrase(phrase)
    if not needle:
        return False
    if re.fullmatch(r"[a-z0-9._-]+", needle):
        return re.search(rf"(?<![a-z0-9._-]){re.escape(needle)}(?![a-z0-9._-])", haystack) is not None
    return needle in haystack


def _annotate(
    blocks: Sequence[Mapping[str, Any]], groups: Sequence[str], terms: Sequence[str]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for raw in blocks:
        item = dict(raw)
        content = str(item["content"])
        item["group_indexes"] = [
            index for index, group in enumerate(groups) if _contains(content, group)
        ]
        item["query_term_count"] = sum(_contains(content, term) for term in terms)
        output.append(item)
    return output


def _structure_rank(kind: str) -> int:
    return {"table": 4, "record": 3, "section": 2, "text": 1}.get(kind, 0)


def _page_header(page: Mapping[str, Any]) -> str:
    return (
        f"[E-PAGE {int(page['ordinal']):04d}] kind=fetched_page_blocks\n"
        f"title={page['title']}\n"
        f"url={page['url']}\n"
        "content="
    )


def _select(
    pages: Sequence[Mapping[str, Any]],
    blocks: Sequence[Mapping[str, Any]],
    groups: Sequence[str],
    policy: ProjectionPolicy,
) -> tuple[list[dict[str, Any]], set[int]]:
    selected: dict[tuple[int, int], dict[str, Any]] = {}
    page_used: Counter[int] = Counter()
    page_map = {int(page["ordinal"]): page for page in pages}
    rendered_used = 0

    def incremental_render_cost(block: Mapping[str, Any]) -> int:
        page = int(block["page_ordinal"])
        size = len(str(block["content"]))
        if page_used[page]:
            return 1 + size
        return len(_page_header(page_map[page])) + size + (2 if selected else 0)

    def can_add(block: Mapping[str, Any]) -> bool:
        size = len(str(block["content"]))
        page = int(block["page_ordinal"])
        return (
            (page, int(block["block_ordinal"])) not in selected
            and rendered_used + incremental_render_cost(block)
            <= policy.total_character_cap
            and page_used[page] + size <= policy.maximum_page_chars
        )

    def add(block: Mapping[str, Any]) -> None:
        nonlocal rendered_used
        copied = copy.deepcopy(dict(block))
        key = (int(copied["page_ordinal"]), int(copied["block_ordinal"]))
        if key in selected:
            return
        size = len(str(copied["content"]))
        rendered_used += incremental_render_cost(copied)
        selected[key] = copied
        page_used[key[0]] += size

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
                _structure_rank(str(block["kind"])),
                int(block["query_term_count"]),
                -len(str(block["content"])),
                -int(block["page_ordinal"]),
                -int(block["block_ordinal"]),
            ),
        )
        add(chosen)
        uncovered.difference_update(chosen["group_indexes"])

    # Preserve source diversity after visible requirement coverage.  Inspect
    # each page and retain its best bounded block, not necessarily its prefix.
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
                    _structure_rank(str(block["kind"])),
                    -int(block["block_ordinal"]),
                ),
            )
        )

    # Fill the remaining fixed budget by a stable structure/relevance order.
    remaining = sorted(
        (block for block in blocks if can_add(block)),
        key=lambda block: (
            -len(block["group_indexes"]),
            -int(block["query_term_count"]),
            -_structure_rank(str(block["kind"])),
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
                remaining.remove(chosen)
                progressed = True

    retained = {
        index
        for block in selected.values()
        for index in block["group_indexes"]
    }
    return [selected[key] for key in sorted(selected)], retained


def _host_entropy(host_counts: Mapping[str, int]) -> float:
    total = sum(host_counts.values())
    if total <= 0:
        return 0.0
    return round(
        -sum((count / total) * math.log(count / total) for count in host_counts.values()),
        12,
    )


def _render(
    pages: Sequence[Mapping[str, Any]], blocks: Sequence[Mapping[str, Any]]
) -> str:
    by_page = {int(page["ordinal"]): page for page in pages}
    grouped: dict[int, list[str]] = {}
    for block in blocks:
        grouped.setdefault(int(block["page_ordinal"]), []).append(
            str(block["content"])
        )
    output = [
        _page_header(by_page[ordinal]) + "\n".join(grouped[ordinal])
        for ordinal in sorted(grouped)
    ]
    return "\n\n".join(output) or "No usable web material was retrieved within budget."


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
    policy: ProjectionPolicy | None = None,
) -> dict[str, Any]:
    chosen = policy or ProjectionPolicy()
    chosen.validate()
    stable = _stable_pages(pages)
    groups = visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=chosen.maximum_visible_groups,
    )
    terms = _query_terms(question, chosen.maximum_query_terms)
    raw_blocks = [
        block for page in stable for block in _blocks(page, chosen.block_character_cap)
    ]
    blocks = _annotate(raw_blocks, groups, terms)
    selected, retained = _select(stable, blocks, groups, chosen)
    supported = {
        index
        for index in range(len(groups))
        if any(index in block["group_indexes"] for block in blocks)
    }
    projection = _render(stable, selected)
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
        "input_unique_host_count": len({page["host"] for page in stable if page["host"]}),
        "projected_unique_host_count": len(
            {page_map[index]["host"] for index in selected_pages if page_map[index]["host"]}
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
        "projected_host_entropy_nats": _host_entropy(host_counts),
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode("utf-8")).hexdigest(),
        "stable_first_seen_page_order_preserved": True,
        "selected_block_order_within_page_preserved": True,
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
    required_flags = {
        "stable_first_seen_page_order_preserved": True,
        "selected_block_order_within_page_preserved": True,
        "table_and_record_lines_split_only_when_single_line_exceeds_block_cap": True,
        "page_content_summarized_or_fabricated": False,
        "provider_narrative_or_search_snippet_forwarded": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
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
        or any(copied.get(name) is not expected for name, expected in required_flags.items())
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.39 structure-preserving receipt drifted")
    policy = ProjectionPolicy(**dict(raw_policy))
    policy.validate()
    stable = _stable_pages(pages)
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
        raise ValueError("V2.48.39 projection input or cap binding drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups, policy=policy
    ):
        raise ValueError("V2.48.39 projection is not reproducible")
    return copied


__all__ = [
    "POLICY_ID",
    "ProjectionPolicy",
    "build_projection",
    "payload_sha256",
    "validate_projection",
    "visible_requirement_groups",
]
