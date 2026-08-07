"""Label-blind information-bottleneck projection for fetched web pages.

V2.48.35 found that a wider retrieval policy increased exact-table successes
but also increased synthesis input and regressed every continuous quality
metric.  This pure component addresses only the evidence-to-context boundary.
It does not search, fetch, synthesize, score, or route benchmark tasks.

The projector preserves a small prefix from every usable page, then allocates
the remaining character budget round-robin across pages.  This prevents an
early long page from monopolizing context while keeping stable page order,
source provenance, table-row boundaries, and deterministic replay.  Entropy
and information gain are measurements only and assign no credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url


POLICY_ID = "v24836_label_blind_source_balanced_information_bottleneck_v1"
ROLE = "v24836_information_bottleneck_projection"
DEFAULT_TOTAL_CHARACTER_CAP = 16_000
DEFAULT_MINIMUM_PAGE_PREFIX_CHARS = 800
DEFAULT_ROUND_ROBIN_CHUNK_CHARS = 800
DEFAULT_MAXIMUM_PAGE_CHARS = 5_000
UNKNOWN_MARKERS = frozenset(
    {"", "unknown", "未知", "n/a", "na", "not available", "not found", "—", "-"}
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
    minimum_page_prefix_chars: int = DEFAULT_MINIMUM_PAGE_PREFIX_CHARS
    round_robin_chunk_chars: int = DEFAULT_ROUND_ROBIN_CHUNK_CHARS
    maximum_page_chars: int = DEFAULT_MAXIMUM_PAGE_CHARS

    def validate(self) -> None:
        for name in (
            "total_character_cap",
            "minimum_page_prefix_chars",
            "round_robin_chunk_chars",
            "maximum_page_chars",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"V2.48.36 {name} must be a positive integer")
        if self.minimum_page_prefix_chars > self.maximum_page_chars:
            raise ValueError("V2.48.36 minimum prefix exceeds per-page cap")
        if self.round_robin_chunk_chars > self.maximum_page_chars:
            raise ValueError("V2.48.36 round-robin chunk exceeds per-page cap")


def _clean_text(value: object) -> str:
    text = str(value or "").replace("\x00", "").replace("\r\n", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").casefold()
    except ValueError:
        return ""


def _page(raw: Mapping[str, Any], ordinal: int) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    canonical = canonicalize_url(str(raw.get("url", "")))
    content = _clean_text(raw.get("raw_content") or raw.get("content") or "")
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
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ordinal, raw in enumerate(pages, start=1):
        page = _page(raw, ordinal)
        if page is None or page["url"] in seen:
            continue
        seen.add(page["url"])
        output.append(page)
    return output


def _allocate(pages: Sequence[Mapping[str, Any]], policy: ProjectionPolicy) -> list[int]:
    """Allocate a strict total budget without reading task or evaluator state."""

    policy.validate()
    caps = [min(len(str(page["content"])), policy.maximum_page_chars) for page in pages]
    allocations = [0 for _ in caps]
    remaining = policy.total_character_cap

    # One small prefix per page first.  If the total cap is smaller than one
    # complete prefix per page, distribute it in input order with no overflow.
    for index, cap in enumerate(caps):
        amount = min(cap, policy.minimum_page_prefix_chars, remaining)
        allocations[index] += amount
        remaining -= amount
        if remaining <= 0:
            return allocations

    # Allocate later content in equal chunks.  Pages already at their cap are
    # skipped; termination is bounded by the total cap and positive chunk size.
    while remaining > 0:
        progressed = False
        for index, cap in enumerate(caps):
            available = cap - allocations[index]
            if available <= 0:
                continue
            amount = min(available, policy.round_robin_chunk_chars, remaining)
            allocations[index] += amount
            remaining -= amount
            progressed = True
            if remaining <= 0:
                break
        if not progressed:
            break
    return allocations


def _host_entropy(host_counts: Mapping[str, int]) -> float:
    total = sum(host_counts.values())
    if total <= 0:
        return 0.0
    return round(
        -sum((count / total) * math.log(count / total) for count in host_counts.values()),
        12,
    )


def _render(pages: Sequence[Mapping[str, Any]], allocations: Sequence[int]) -> str:
    blocks: list[str] = []
    evidence_ordinal = 0
    for page, amount in zip(pages, allocations, strict=True):
        if amount <= 0:
            continue
        evidence_ordinal += 1
        blocks.append(
            f"[E{evidence_ordinal:04d}] kind=fetched_page\n"
            f"title={page['title']}\n"
            f"url={page['url']}\n"
            f"content={str(page['content'])[:amount]}"
        )
    return "\n\n".join(blocks) or "No usable web material was retrieved within budget."


def build_projection(
    pages: Sequence[Mapping[str, Any]], *, policy: ProjectionPolicy | None = None
) -> dict[str, Any]:
    chosen = policy or ProjectionPolicy()
    chosen.validate()
    stable = _stable_pages(pages)
    allocations = _allocate(stable, chosen)
    projected = _render(stable, allocations)
    host_counts = Counter(
        str(page["host"]) or "unknown-host"
        for page, amount in zip(stable, allocations, strict=True)
        if amount > 0
    )
    input_characters = sum(len(str(page["content"])) for page in stable)
    allocated_characters = sum(allocations)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "policy": {
            "total_character_cap": chosen.total_character_cap,
            "minimum_page_prefix_chars": chosen.minimum_page_prefix_chars,
            "round_robin_chunk_chars": chosen.round_robin_chunk_chars,
            "maximum_page_chars": chosen.maximum_page_chars,
        },
        "input_page_count": len(stable),
        "projected_page_count": sum(amount > 0 for amount in allocations),
        "input_unique_host_count": len({page["host"] for page in stable if page["host"]}),
        "projected_unique_host_count": len({
            page["host"]
            for page, amount in zip(stable, allocations, strict=True)
            if amount > 0 and page["host"]
        }),
        "input_content_characters": input_characters,
        "allocated_content_characters": allocated_characters,
        "projected_rendered_characters": len(projected),
        "truncated_content_characters": max(0, input_characters - allocated_characters),
        "per_page_allocated_characters": allocations,
        "per_page_content_sha256": [str(page["content_sha256"]) for page in stable],
        "projected_host_entropy_nats": _host_entropy(host_counts),
        "projection": projected,
        "projection_sha256": hashlib.sha256(projected.encode("utf-8")).hexdigest(),
        "stable_first_seen_page_order_preserved": True,
        "each_usable_page_receives_prefix_before_any_page_receives_tail": True,
        "total_and_per_page_character_caps_enforced": True,
        "page_content_reordered_or_summarized": False,
        "query_or_provider_narrative_forwarded": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "question_benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_projection(value, pages=pages, replay=False)


def validate_projection(
    value: Mapping[str, Any], *, pages: Sequence[Mapping[str, Any]], replay: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    raw_policy = copied.get("policy")
    allocations = copied.get("per_page_allocated_characters")
    digests = copied.get("per_page_content_sha256")
    projection = copied.get("projection")
    expected = {
        "artifact_version", "role", "policy_id", "policy", "input_page_count",
        "projected_page_count", "input_unique_host_count", "projected_unique_host_count",
        "input_content_characters", "allocated_content_characters",
        "projected_rendered_characters", "truncated_content_characters",
        "per_page_allocated_characters", "per_page_content_sha256",
        "projected_host_entropy_nats", "projection", "projection_sha256",
        "stable_first_seen_page_order_preserved",
        "each_usable_page_receives_prefix_before_any_page_receives_tail",
        "total_and_per_page_character_caps_enforced",
        "page_content_reordered_or_summarized", "query_or_provider_narrative_forwarded",
        "entropy_information_gain_shadow_only",
        "entropy_or_information_gain_assigns_credit",
        "question_benchmark_label_mapping_gold_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "receipt_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(raw_policy, Mapping)
        or set(raw_policy) != {
            "total_character_cap", "minimum_page_prefix_chars",
            "round_robin_chunk_chars", "maximum_page_chars",
        }
        or not isinstance(allocations, list)
        or not isinstance(digests, list)
        or len(allocations) != len(digests)
        or len(allocations) != copied.get("input_page_count")
        or any(isinstance(number, bool) or not isinstance(number, int) or number < 0
               for number in allocations)
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or copied.get("allocated_content_characters") != sum(allocations)
        or copied.get("stable_first_seen_page_order_preserved") is not True
        or copied.get("each_usable_page_receives_prefix_before_any_page_receives_tail") is not True
        or copied.get("total_and_per_page_character_caps_enforced") is not True
        or copied.get("page_content_reordered_or_summarized") is not False
        or copied.get("query_or_provider_narrative_forwarded") is not False
        or copied.get("entropy_information_gain_shadow_only") is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get("question_benchmark_label_mapping_gold_evaluator_score_or_reward_read") is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.36 information-bottleneck receipt drifted")
    policy = ProjectionPolicy(**dict(raw_policy))
    policy.validate()
    if (
        sum(allocations) > policy.total_character_cap
        or any(number > policy.maximum_page_chars for number in allocations)
    ):
        raise ValueError("V2.48.36 projection exceeded a character cap")
    stable = _stable_pages(pages)
    if digests != [page["content_sha256"] for page in stable]:
        raise ValueError("V2.48.36 input page binding drifted")
    if replay and copied != build_projection(pages, policy=policy):
        raise ValueError("V2.48.36 projection is not reproducible")
    return copied


__all__ = [
    "POLICY_ID", "ProjectionPolicy", "build_projection", "payload_sha256",
    "validate_projection",
]
