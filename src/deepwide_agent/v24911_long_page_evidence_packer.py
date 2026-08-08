"""Visible-only long-page evidence packing with a prefix-safe fallback.

The production baseline fetches and forwards at most the first 5,000
characters of each page.  This pure component accepts a longer, same-forward
page prefix (at most 12,000 characters), but still exposes at most 5,000
characters per page to synthesis.  Short pages are byte-for-byte identity;
long pages use visible-question terms and structural blocks to retain useful
late material.  If visible requirement coverage would regress relative to the
5,000-character prefix, the whole projection falls back to that prefix.

No file, environment, process, network, model, benchmark label, gold,
evaluator, score, reward, or historical-result capability is present.
Entropy is a shadow statistic and never assigns signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url
from . import v24839_structure_preserving_projector as structure
from . import v24842_atomic_table_header_closure as atomic


POLICY_ID = "v24911_visible_long_page_prefix_safe_evidence_packer_v1"
ROLE = "v24911_long_page_evidence_packing_receipt"
DEFAULT_INPUT_PAGE_CHARACTER_CAP = 12_000
DEFAULT_OUTPUT_PAGE_CHARACTER_CAP = 5_000
DEFAULT_BLOCK_CHARACTER_CAP = 1_200
DEFAULT_TOTAL_RENDERED_CHARACTER_CAP = 120_000
DEFAULT_MAXIMUM_PAGES = 10
DEFAULT_MAXIMUM_VISIBLE_GROUPS = 64
DEFAULT_MAXIMUM_QUERY_TERMS = 96


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class PackingPolicy:
    input_page_character_cap: int = DEFAULT_INPUT_PAGE_CHARACTER_CAP
    output_page_character_cap: int = DEFAULT_OUTPUT_PAGE_CHARACTER_CAP
    block_character_cap: int = DEFAULT_BLOCK_CHARACTER_CAP
    total_rendered_character_cap: int = DEFAULT_TOTAL_RENDERED_CHARACTER_CAP
    maximum_pages: int = DEFAULT_MAXIMUM_PAGES
    maximum_visible_groups: int = DEFAULT_MAXIMUM_VISIBLE_GROUPS
    maximum_query_terms: int = DEFAULT_MAXIMUM_QUERY_TERMS

    def validate(self) -> None:
        for name in (
            "input_page_character_cap",
            "output_page_character_cap",
            "block_character_cap",
            "total_rendered_character_cap",
            "maximum_pages",
            "maximum_visible_groups",
            "maximum_query_terms",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"V2.49.11 {name} must be a positive integer")
        if self.output_page_character_cap >= self.input_page_character_cap:
            raise ValueError("V2.49.11 input cap must strictly exceed output cap")
        if self.block_character_cap > self.output_page_character_cap:
            raise ValueError("V2.49.11 block cap exceeds active per-page cap")
        minimum_total = self.maximum_pages * (
            self.output_page_character_cap + 1_000
        )
        if self.total_rendered_character_cap < minimum_total:
            raise ValueError("V2.49.11 total cap cannot hold bounded page headers")


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").casefold()
    except ValueError:
        return ""


def _page(
    raw: Mapping[str, Any], ordinal: int, policy: PackingPolicy
) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    canonical = canonicalize_url(str(raw.get("url", "")))
    full = structure._clean(raw.get("raw_content") or raw.get("content") or "")
    if not canonical or not full:
        return None
    effective = full[: policy.input_page_character_cap]
    return {
        "ordinal": ordinal,
        "title": " ".join(str(raw.get("title", "")).split())[:500],
        "url": canonical,
        "host": _host(canonical),
        "full_content_sha256": hashlib.sha256(full.encode("utf-8")).hexdigest(),
        "effective_content_sha256": hashlib.sha256(
            effective.encode("utf-8")
        ).hexdigest(),
        "full_content_characters": len(full),
        "effective_content": effective,
        "effective_content_characters": len(effective),
    }


def _stable_pages(
    pages: Sequence[Mapping[str, Any]], policy: PackingPolicy
) -> list[dict[str, Any]]:
    if isinstance(pages, (str, bytes)):
        raise ValueError("V2.49.11 page vector is not a mapping sequence")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(pages, 1):
        page = _page(raw, ordinal, policy)
        if page is None or page["url"] in seen:
            continue
        seen.add(str(page["url"]))
        output.append(page)
    if len(output) > policy.maximum_pages:
        raise ValueError("V2.49.11 usable page count exceeds frozen fetch cap")
    return output


def _as_structural_page(page: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ordinal": int(page["ordinal"]),
        "title": str(page["title"]),
        "url": str(page["url"]),
        "host": str(page["host"]),
        "content": str(page["effective_content"]),
        "content_sha256": str(page["effective_content_sha256"]),
    }


def _contains(text: str, phrase: str) -> bool:
    return structure._contains(text, phrase)


def _supported_groups(texts: Sequence[str], groups: Sequence[str]) -> set[int]:
    return {
        index
        for index, group in enumerate(groups)
        if any(_contains(text, group) for text in texts)
    }


def _group_entropy(selected: set[int], groups: Sequence[str]) -> float:
    if not selected:
        return 0.0
    lengths = [max(1, len(groups[index])) for index in sorted(selected)]
    total = sum(lengths)
    return round(
        -sum((value / total) * math.log(value / total) for value in lengths),
        12,
    )


def _pack_long_page(
    page: Mapping[str, Any],
    groups: Sequence[str],
    terms: Sequence[str],
    policy: PackingPolicy,
) -> tuple[str, dict[str, int], list[str]]:
    structural = _as_structural_page(page)
    raw_blocks = atomic._blocks(structural, policy.block_character_cap)
    blocks = structure._annotate(raw_blocks, groups, terms)
    parent_policy = structure.ProjectionPolicy(
        total_character_cap=policy.total_rendered_character_cap,
        maximum_page_chars=policy.output_page_character_cap,
        block_character_cap=policy.block_character_cap,
        maximum_visible_groups=policy.maximum_visible_groups,
        maximum_query_terms=policy.maximum_query_terms,
    )
    selected, _retained, closure = atomic._select(
        [structural], blocks, groups, parent_policy
    )
    excerpt = "\n".join(str(block["content"]) for block in selected)
    if not excerpt:
        excerpt = str(page["effective_content"])[
            : policy.output_page_character_cap
        ]
    if len(excerpt) > policy.output_page_character_cap:
        raise RuntimeError("V2.49.11 structural selection exceeded per-page cap")
    return excerpt, closure, [str(block["content_sha256"]) for block in selected]


def _render(pages: Sequence[Mapping[str, Any]], excerpts: Sequence[str]) -> str:
    blocks: list[str] = []
    for ordinal, (page, excerpt) in enumerate(zip(pages, excerpts, strict=True), 1):
        if not excerpt:
            continue
        blocks.append(
            f"[E{ordinal:04d}] kind=fetched_page\n"
            f"title={page['title']}\n"
            f"url={page['url']}\n"
            f"content={excerpt}"
        )
    return "\n\n".join(blocks) or "No usable web material was retrieved within budget."


def build_packing(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
    policy: PackingPolicy | None = None,
) -> dict[str, Any]:
    chosen = policy or PackingPolicy()
    chosen.validate()
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.11 visible question is absent")
    stable = _stable_pages(pages, chosen)
    groups = structure.visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=chosen.maximum_visible_groups,
    )
    terms = structure._query_terms(question, chosen.maximum_query_terms)
    prefix_excerpts = [
        str(page["effective_content"])[: chosen.output_page_character_cap]
        for page in stable
    ]
    candidate_excerpts: list[str] = []
    selected_hashes: list[list[str]] = []
    short_identity = 0
    long_packed = 0
    continuation_count = 0
    dependency_additions = 0
    orphan_count = 0
    for page, prefix in zip(stable, prefix_excerpts, strict=True):
        if int(page["effective_content_characters"]) <= chosen.output_page_character_cap:
            candidate_excerpts.append(prefix)
            selected_hashes.append(
                [hashlib.sha256(prefix.encode("utf-8")).hexdigest()]
            )
            short_identity += 1
            continue
        excerpt, closure, hashes = _pack_long_page(
            page, groups, terms, chosen
        )
        candidate_excerpts.append(excerpt)
        selected_hashes.append(hashes)
        long_packed += 1
        continuation_count += closure[
            "selected_table_continuation_block_count"
        ]
        dependency_additions += closure[
            "table_header_dependency_addition_count"
        ]
        orphan_count += closure[
            "orphan_selected_table_continuation_block_count"
        ]

    supported = _supported_groups(
        [str(page["effective_content"]) for page in stable], groups
    )
    prefix_retained = _supported_groups(prefix_excerpts, groups)
    candidate_retained = _supported_groups(candidate_excerpts, groups)
    fallback = not prefix_retained.issubset(candidate_retained)
    if fallback:
        candidate_excerpts = list(prefix_excerpts)
        selected_hashes = [
            [hashlib.sha256(value.encode("utf-8")).hexdigest()]
            for value in candidate_excerpts
        ]
        candidate_retained = set(prefix_retained)
        continuation_count = dependency_additions = orphan_count = 0

    projection = _render(stable, candidate_excerpts)
    if len(projection) > chosen.total_rendered_character_cap:
        raise RuntimeError("V2.49.11 rendered projection exceeded total cap")
    input_characters = sum(
        int(page["effective_content_characters"]) for page in stable
    )
    output_characters = sum(len(value) for value in candidate_excerpts)
    host_counts = Counter(
        str(page["host"]) or "unknown-host"
        for page, excerpt in zip(stable, candidate_excerpts, strict=True)
        if excerpt
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "policy": {
            "input_page_character_cap": chosen.input_page_character_cap,
            "output_page_character_cap": chosen.output_page_character_cap,
            "block_character_cap": chosen.block_character_cap,
            "total_rendered_character_cap": chosen.total_rendered_character_cap,
            "maximum_pages": chosen.maximum_pages,
            "maximum_visible_groups": chosen.maximum_visible_groups,
            "maximum_query_terms": chosen.maximum_query_terms,
        },
        "visible_question_sha256": hashlib.sha256(
            question.encode("utf-8")
        ).hexdigest(),
        "visible_requirement_vector_sha256": payload_sha256(groups),
        "visible_requirement_group_count": len(groups),
        "supported_visible_requirement_group_count": len(supported),
        "prefix_retained_supported_visible_requirement_group_count": len(
            supported.intersection(prefix_retained)
        ),
        "candidate_retained_supported_visible_requirement_group_count": len(
            supported.intersection(candidate_retained)
        ),
        "candidate_visible_requirement_gain_count": len(
            supported.intersection(candidate_retained - prefix_retained)
        ),
        "visible_query_term_count": len(terms),
        "input_page_count": len(stable),
        "short_page_identity_count": short_identity,
        "long_page_packed_count": long_packed,
        "input_effective_content_characters": input_characters,
        "output_active_content_characters": output_characters,
        "projected_rendered_characters": len(projection),
        "per_page_effective_content_characters": [
            int(page["effective_content_characters"]) for page in stable
        ],
        "per_page_output_content_characters": [
            len(value) for value in candidate_excerpts
        ],
        "per_page_full_content_sha256": [
            str(page["full_content_sha256"]) for page in stable
        ],
        "per_page_effective_content_sha256": [
            str(page["effective_content_sha256"]) for page in stable
        ],
        "per_page_selected_block_content_sha256": selected_hashes,
        "selected_table_continuation_block_count": continuation_count,
        "table_header_dependency_addition_count": dependency_additions,
        "orphan_selected_table_continuation_block_count": orphan_count,
        "projected_unique_host_count": len(
            {page["host"] for page in stable if page["host"]}
        ),
        "projected_host_entropy_nats": structure._host_entropy(host_counts),
        "selected_requirement_entropy_nats": _group_entropy(
            supported.intersection(candidate_retained), groups
        ),
        "prefix_safe_fallback_applied": fallback,
        "candidate_requirement_coverage_not_less_than_prefix_baseline": (
            prefix_retained.issubset(candidate_retained)
        ),
        "short_page_content_byte_identity_preserved": all(
            candidate_excerpts[index] == str(page["effective_content"])
            for index, page in enumerate(stable)
            if int(page["effective_content_characters"])
            <= chosen.output_page_character_cap
        ),
        "stable_first_seen_page_and_selected_block_order_preserved": True,
        "active_per_page_and_total_character_caps_enforced": True,
        "atomic_table_header_closure_enforced_for_packed_pages": not fallback,
        "same_forward_page_bytes_only": True,
        "search_provider_narrative_or_snippet_forwarded": False,
        "page_content_summarized_or_fabricated": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode("utf-8")).hexdigest(),
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_packing(
        value,
        question=question,
        pages=pages,
        explicit_groups=explicit_groups,
        replay=False,
    )


def validate_packing(
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
    projection = copied.get("projection")
    expected_policy = {
        "input_page_character_cap",
        "output_page_character_cap",
        "block_character_cap",
        "total_rendered_character_cap",
        "maximum_pages",
        "maximum_visible_groups",
        "maximum_query_terms",
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(raw_policy, Mapping)
        or set(raw_policy) != expected_policy
        or copied.get("visible_question_sha256")
        != hashlib.sha256(question.encode("utf-8")).hexdigest()
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or copied.get("candidate_requirement_coverage_not_less_than_prefix_baseline")
        is not True
        or copied.get("short_page_content_byte_identity_preserved") is not True
        or copied.get("stable_first_seen_page_and_selected_block_order_preserved")
        is not True
        or copied.get("active_per_page_and_total_character_caps_enforced")
        is not True
        or copied.get("same_forward_page_bytes_only") is not True
        or copied.get("search_provider_narrative_or_snippet_forwarded") is not False
        or copied.get("page_content_summarized_or_fabricated") is not False
        or copied.get("entropy_information_gain_shadow_only") is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        ) is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.11 evidence packing receipt drifted")
    policy = PackingPolicy(**dict(raw_policy))
    policy.validate()
    stable = _stable_pages(pages, policy)
    groups = structure.visible_requirement_groups(
        question,
        explicit_groups=explicit_groups,
        maximum_groups=policy.maximum_visible_groups,
    )
    per_effective = copied.get("per_page_effective_content_characters")
    per_output = copied.get("per_page_output_content_characters")
    selected_hashes = copied.get("per_page_selected_block_content_sha256")
    if (
        copied.get("visible_requirement_vector_sha256") != payload_sha256(groups)
        or copied.get("visible_requirement_group_count") != len(groups)
        or copied.get("input_page_count") != len(stable)
        or copied.get("short_page_identity_count")
        + copied.get("long_page_packed_count")
        != len(stable)
        or not isinstance(per_effective, list)
        or not isinstance(per_output, list)
        or not isinstance(selected_hashes, list)
        or len(per_effective) != len(stable)
        or len(per_output) != len(stable)
        or len(selected_hashes) != len(stable)
        or per_effective
        != [int(page["effective_content_characters"]) for page in stable]
        or any(
            isinstance(number, bool)
            or not isinstance(number, int)
            or not 0 <= number <= policy.output_page_character_cap
            for number in per_output
        )
        or copied.get("output_active_content_characters") != sum(per_output)
        or copied.get("projected_rendered_characters")
        > policy.total_rendered_character_cap
        or copied.get("per_page_full_content_sha256")
        != [page["full_content_sha256"] for page in stable]
        or copied.get("per_page_effective_content_sha256")
        != [page["effective_content_sha256"] for page in stable]
        or copied.get("orphan_selected_table_continuation_block_count") != 0
        or copied.get(
            "candidate_retained_supported_visible_requirement_group_count"
        )
        < copied.get(
            "prefix_retained_supported_visible_requirement_group_count"
        )
    ):
        raise ValueError("V2.49.11 evidence packing input or cap binding drifted")
    if replay and copied != build_packing(
        question,
        pages,
        explicit_groups=explicit_groups,
        policy=policy,
    ):
        raise ValueError("V2.49.11 evidence packing is not reproducible")
    return copied


__all__ = [
    "POLICY_ID",
    "PackingPolicy",
    "build_packing",
    "payload_sha256",
    "validate_packing",
]
