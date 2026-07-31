"""Pure post-terminal source-dependency diagnostics for V2.42.20.

The audit estimates how much nominal page evidence remains after accounting
for exact/near content mirrors and softer source dependencies.  It accepts no
question, prediction, benchmark label, answer, evaluator, or search-query
field.  Returned values contain counts and hashes only, never page text, raw
URLs, evidence identifiers, or task identifiers.

The dependency-adjusted width is a preregistered sensitivity statistic, not an
estimate of factual correctness.  Hard mirror components count once.  Between
those components, a bounded pairwise dependence coefficient is used in the
standard effective-sample-size form n^2 / (n + 2 * sum(rho_ij)).
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


MIN_NEAR_DUPLICATE_CHARS = 80
NEAR_DUPLICATE_JACCARD = 0.78
NEAR_DUPLICATE_CONTAINMENT = 0.90
MIN_NEAR_DUPLICATE_LENGTH_RATIO = 0.50
MIN_SHARED_QUOTE_CHARS = 96
CHAR_SHINGLE_SIZE = 13
SAME_FAMILY_RHO = 0.20
SHARED_QUOTE_RHO = 0.45
SHARED_STRUCTURED_RECORD_RHO = 0.30
PATH_MIRROR_RHO = 0.25

_OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
_ALLOWED_EVIDENCE_FIELDS = frozenset(
    {"id", "kind", "url", "source_family", "title", "text", "fingerprint"}
)
_TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_src",
        "source",
        "utm_campaign",
        "utm_content",
        "utm_medium",
        "utm_source",
        "utm_term",
    }
)
_REDIRECT_QUERY_KEYS = frozenset(
    {"continue", "dest", "destination", "redirect", "redirect_url", "target", "u", "url"}
)
_MULTI_LABEL_SUFFIXES = frozenset(
    {
        "ac.jp",
        "ac.uk",
        "co.in",
        "co.jp",
        "co.kr",
        "co.nz",
        "co.uk",
        "com.au",
        "com.br",
        "com.cn",
        "com.hk",
        "com.mx",
        "com.sg",
        "edu.au",
        "edu.cn",
        "edu.hk",
        "edu.sg",
        "gov.au",
        "gov.cn",
        "gov.uk",
        "net.au",
        "net.cn",
        "org.au",
        "org.cn",
        "org.uk",
    }
)
_PATH_NOISE = frozenset(
    {
        "amp",
        "article",
        "articles",
        "en",
        "english",
        "html",
        "index",
        "news",
        "page",
        "post",
        "posts",
        "view",
        "www",
        "zh",
        "zh-cn",
    }
)
_STRUCTURED_PAIR = re.compile(
    r"(?:^|[|;,，；\t{}\[\]])\s*[^|;,，；\t:{}\[\]]{1,48}\s*[:：=]\s*[^|;,，；\t{}\[\]]{1,160}"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _fold(value: object) -> str:
    text = html.unescape(unquote(str(value or "")))
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _content_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(str(value or ""))).casefold()
    text = re.sub(r"<[^>]{1,256}>", " ", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())[:12000]


def _compact(value: str) -> str:
    return value.replace(" ", "")


def _host(url: object) -> str:
    try:
        host = urlsplit(str(url or "")).hostname or ""
    except ValueError:
        return ""
    host = host.rstrip(".").casefold()
    if host.startswith("www."):
        host = host[4:]
    return host


def canonical_domain(host: object) -> str:
    """Return a conservative registrable-domain approximation."""

    value = _fold(host).strip(".")
    if not value or ":" in value or value.replace(".", "").isdigit():
        return value
    labels = [part for part in value.split(".") if part]
    if len(labels) <= 2:
        return ".".join(labels)
    suffix = ".".join(labels[-2:])
    keep = 3 if suffix in _MULTI_LABEL_SUFFIXES else 2
    return ".".join(labels[-keep:])


def _canonical_url(url: object) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return ""
    host = _host(raw)
    if not host:
        return ""
    scheme = "https" if parsed.scheme.casefold() in {"http", "https"} else parsed.scheme.casefold()
    path = re.sub(r"/+", "/", unquote(parsed.path or "/"))
    if path != "/":
        path = path.rstrip("/")
    if path.endswith("/index.html"):
        path = path[: -len("index.html")].rstrip("/") or "/"
    pairs = [
        (key.casefold(), value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in _TRACKING_QUERY_KEYS
    ]
    pairs.sort()
    return urlunsplit((scheme, host, path, urlencode(pairs, doseq=True), ""))


def _redirect_targets(url: object) -> frozenset[str]:
    raw = str(url or "")
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return frozenset()
    targets: set[str] = set()
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        if key.casefold() not in _REDIRECT_QUERY_KEYS:
            continue
        candidate = _canonical_url(value)
        if candidate:
            targets.add(candidate)
    return frozenset(targets)


def _path_signature(url: object) -> str:
    try:
        path = unquote(urlsplit(str(url or "")).path).casefold()
    except ValueError:
        return ""
    parts = [
        token
        for token in re.findall(r"[\w-]+", path, flags=re.UNICODE)
        if token not in _PATH_NOISE and not token.isdigit()
    ]
    if len(parts) < 2 and sum(map(len, parts)) < 18:
        return ""
    return "/".join(parts[-6:])


def _source_family(url: object, value: object) -> str:
    raw = _fold(value)
    if raw and re.fullmatch(r"[a-z0-9.-]+", raw):
        raw = canonical_domain(raw)
    return raw or canonical_domain(_host(url))


def _shingles(text: str, size: int = CHAR_SHINGLE_SIZE) -> frozenset[str]:
    compact = _compact(text)
    if not compact:
        return frozenset()
    if len(compact) < size:
        return frozenset({compact})
    return frozenset(compact[index : index + size] for index in range(len(compact) - size + 1))


def _similarity(left: frozenset[str], right: frozenset[str]) -> tuple[float, float]:
    if not left or not right:
        return 0.0, 0.0
    common = len(left & right)
    union = len(left | right)
    return common / union, common / min(len(left), len(right))


def _longest_shared_span(left: str, right: str, size: int = 12) -> int:
    """Length of an exact normalized common span without emitting the span."""

    a = _compact(left)
    b = _compact(right)
    if len(a) < size or len(b) < size:
        return len(a) if a and a in b else len(b) if b and b in a else 0
    if len(a) > len(b):
        a, b = b, a
    positions: dict[str, list[int]] = defaultdict(list)
    for index in range(len(b) - size + 1):
        bucket = positions[b[index : index + size]]
        if len(bucket) < 64:
            bucket.append(index)
    previous: dict[int, int] = {}
    best = 0
    for index in range(len(a) - size + 1):
        current: dict[int, int] = {}
        for other in positions.get(a[index : index + size], ()):
            run = previous.get(other - 1, 0) + 1
            current[other] = run
            best = max(best, run)
        previous = current
    return best + size - 1 if best else 0


def _structured_fingerprints(raw_text: object) -> frozenset[str]:
    values: set[str] = set()
    for raw_line in str(raw_text or "").splitlines():
        line = _fold(raw_line)
        if not 24 <= len(line) <= 512:
            continue
        delimiter_count = sum(line.count(value) for value in ("|", "\t", ":", "：", ";", "；"))
        pair_count = len(_STRUCTURED_PAIR.findall(line))
        if delimiter_count >= 2 or pair_count >= 2:
            values.add(hashlib.sha256(line.encode()).hexdigest())
    return frozenset(values)


@dataclass(frozen=True)
class _Node:
    url: str
    redirect_targets: frozenset[str]
    path_signature: str
    family: str
    content: str
    content_sha256: str
    shingles: frozenset[str]
    structured: frozenset[str]


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        a = self.find(left)
        b = self.find(right)
        if a != b:
            self.parent[b] = a


def _node(evidence: Mapping[str, Any]) -> _Node | None:
    if not set(evidence).issubset(_ALLOWED_EVIDENCE_FIELDS):
        raise RuntimeError("V2.42.20 evidence projection contains an unapproved field")
    if _fold(evidence.get("kind")) != "page":
        return None
    url = _canonical_url(evidence.get("url"))
    content = _content_text(evidence.get("text"))
    supplied = _fold(evidence.get("fingerprint"))
    content_sha = hashlib.sha256(content.encode()).hexdigest() if content else supplied
    if not url and not content_sha:
        return None
    return _Node(
        url=url,
        redirect_targets=_redirect_targets(evidence.get("url")),
        path_signature=_path_signature(evidence.get("url")),
        family=_source_family(evidence.get("url"), evidence.get("source_family")),
        content=content,
        content_sha256=content_sha,
        shingles=_shingles(content),
        structured=_structured_fingerprints(evidence.get("text")),
    )


def _hard_and_soft(left: _Node, right: _Node) -> tuple[set[str], dict[str, float]]:
    hard: set[str] = set()
    soft: dict[str, float] = {}
    same_url = bool(left.url and left.url == right.url)
    exact_content = bool(left.content_sha256 and left.content_sha256 == right.content_sha256)
    if same_url:
        hard.add("same_canonical_url")
    if exact_content:
        hard.add("exact_content")
    if (
        left.url
        and right.url
        and (
            left.url in right.redirect_targets
            or right.url in left.redirect_targets
            or bool(left.redirect_targets & right.redirect_targets)
        )
    ):
        hard.add("redirect_equivalent")

    jaccard, containment = _similarity(left.shingles, right.shingles)
    shorter = min(len(_compact(left.content)), len(_compact(right.content)))
    longer = max(len(_compact(left.content)), len(_compact(right.content)))
    ratio = shorter / longer if longer else 0.0
    near_duplicate = (
        shorter >= MIN_NEAR_DUPLICATE_CHARS
        and ratio >= MIN_NEAR_DUPLICATE_LENGTH_RATIO
        and (jaccard >= NEAR_DUPLICATE_JACCARD or containment >= NEAR_DUPLICATE_CONTAINMENT)
    )
    if near_duplicate:
        hard.add("near_duplicate_content")

    common_structured = len(left.structured & right.structured)
    quote_chars = 0
    if (
        not exact_content
        and shorter >= MIN_SHARED_QUOTE_CHARS
        and (containment >= 0.08 or common_structured or jaccard >= 0.05)
    ):
        quote_chars = _longest_shared_span(left.content, right.content)
    if quote_chars >= MIN_SHARED_QUOTE_CHARS:
        soft["shared_quoted_span"] = SHARED_QUOTE_RHO
    if common_structured:
        soft["shared_structured_record"] = SHARED_STRUCTURED_RECORD_RHO

    same_path = bool(
        left.path_signature and left.path_signature == right.path_signature
    )
    different_family = bool(left.family and right.family and left.family != right.family)
    if same_path and different_family:
        soft["cross_family_path_mirror"] = PATH_MIRROR_RHO
        if jaccard >= 0.45 or containment >= 0.70 or quote_chars >= MIN_SHARED_QUOTE_CHARS:
            hard.add("cross_family_path_content_mirror")
    if left.family and left.family == right.family:
        soft["same_source_family"] = SAME_FAMILY_RHO
    return hard, soft


def analyze_task(
    *, opaque_id: str, evidence: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    if _OPAQUE_ID.fullmatch(opaque_id) is None:
        raise RuntimeError("V2.42.20 opaque task ID is malformed")
    raw_rows = list(evidence)
    candidates = [value for value in (_node(row) for row in raw_rows) if value is not None]

    # Repeated ledger copies of the same URL/content/family tuple do not inflate
    # nominal width.  Distinct URLs carrying the same content remain distinct
    # nominal nodes and are then joined by a hard mirror edge.
    unique: dict[tuple[str, str, str], _Node] = {}
    for value in candidates:
        unique.setdefault((value.url, value.content_sha256, value.family), value)
    nodes = list(unique.values())
    union = _UnionFind(len(nodes))
    hard_reasons: Counter[str] = Counter()
    hard_pairs = 0
    pair_soft: dict[tuple[int, int], dict[str, float]] = {}
    for left_index, left in enumerate(nodes):
        for right_index in range(left_index + 1, len(nodes)):
            hard, soft = _hard_and_soft(left, nodes[right_index])
            if hard:
                union.union(left_index, right_index)
                hard_pairs += 1
                hard_reasons.update(hard)
            if soft:
                pair_soft[(left_index, right_index)] = soft

    roots = {index: union.find(index) for index in range(len(nodes))}
    components = sorted(set(roots.values()))
    component_index = {root: index for index, root in enumerate(components)}
    soft_edges: dict[tuple[int, int], dict[str, float]] = {}
    soft_reasons: Counter[str] = Counter()
    for (left, right), reasons in pair_soft.items():
        a = component_index[roots[left]]
        b = component_index[roots[right]]
        if a == b:
            continue
        key = (min(a, b), max(a, b))
        current = soft_edges.setdefault(key, {})
        for reason, rho in reasons.items():
            current[reason] = max(current.get(reason, 0.0), rho)
    rho_sum = 0.0
    for reasons in soft_edges.values():
        soft_reasons.update(reasons.keys())
        rho_sum += max(reasons.values())

    hard_width = len(components)
    if hard_width:
        effective = hard_width * hard_width / (hard_width + 2.0 * rho_sum)
        effective = min(float(hard_width), max(1.0, effective))
    else:
        effective = 0.0

    dependency_union = _UnionFind(hard_width)
    for left, right in soft_edges:
        dependency_union.union(left, right)
    dependency_components = len(
        {dependency_union.find(index) for index in range(hard_width)}
    )
    family_count = len({node.family for node in nodes if node.family})
    return {
        "opaque_id_sha256": hashlib.sha256(opaque_id.encode()).hexdigest(),
        "raw_evidence_items": len(raw_rows),
        "eligible_page_items": len(candidates),
        "nominal_evidence_width": len(nodes),
        "hard_dependency_cluster_width": hard_width,
        "dependency_graph_components": dependency_components,
        "dependency_adjusted_effective_width": round(effective, 6),
        "nominal_to_effective_reduction": round(len(nodes) - effective, 6),
        "unique_source_families": family_count,
        "hard_dependency_edge_pairs": hard_pairs,
        "soft_dependency_edge_pairs": len(soft_edges),
        "hard_edge_reason_counts": dict(sorted(hard_reasons.items())),
        "soft_edge_reason_counts": dict(sorted(soft_reasons.items())),
        "same_family_alone_never_forms_a_hard_cluster": True,
        "question_query_prediction_mapping_gold_label_or_score_read": False,
        "page_text_raw_url_evidence_id_or_task_id_emitted": False,
    }


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = quantile * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[lower], 6)
    weight = rank - lower
    return round(ordered[lower] * (1.0 - weight) + ordered[upper] * weight, 6)


def aggregate_tasks(tasks: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(tasks)
    integer_fields = (
        "raw_evidence_items",
        "eligible_page_items",
        "nominal_evidence_width",
        "hard_dependency_cluster_width",
        "unique_source_families",
        "hard_dependency_edge_pairs",
        "soft_dependency_edge_pairs",
    )
    float_fields = (
        "dependency_adjusted_effective_width",
        "nominal_to_effective_reduction",
    )
    hard: Counter[str] = Counter()
    soft: Counter[str] = Counter()
    for row in rows:
        hard.update(row.get("hard_edge_reason_counts") or {})
        soft.update(row.get("soft_edge_reason_counts") or {})
    task_count = len(rows)
    totals: dict[str, float | int] = {
        field: sum(int(row.get(field, 0)) for row in rows) for field in integer_fields
    }
    totals.update(
        {
            field: round(sum(float(row.get(field, 0.0)) for row in rows), 6)
            for field in float_fields
        }
    )
    return {
        "tasks_scanned": task_count,
        "totals": totals,
        "means": {
            field: round(float(totals[field]) / task_count, 6) if task_count else 0.0
            for field in (*integer_fields, *float_fields)
        },
        "effective_width_percentiles": {
            f"p{int(value * 100):02d}": _percentile(
                [float(row.get("dependency_adjusted_effective_width", 0.0)) for row in rows],
                value,
            )
            for value in (0.0, 0.25, 0.50, 0.75, 1.0)
        },
        "tasks_with_hard_dependency_collapse": sum(
            int(row.get("hard_dependency_cluster_width", 0))
            < int(row.get("nominal_evidence_width", 0))
            for row in rows
        ),
        "tasks_with_soft_dependency_discount": sum(
            float(row.get("dependency_adjusted_effective_width", 0.0))
            < int(row.get("hard_dependency_cluster_width", 0))
            for row in rows
        ),
        "hard_edge_reason_counts": dict(sorted(hard.items())),
        "soft_edge_reason_counts": dict(sorted(soft.items())),
        "same_family_alone_never_forms_a_hard_cluster": True,
        "official_score_or_prediction_recomputed": False,
        "question_query_page_text_raw_url_task_id_mapping_gold_label_or_score_emitted": False,
    }


__all__ = [
    "CHAR_SHINGLE_SIZE",
    "MIN_NEAR_DUPLICATE_CHARS",
    "MIN_NEAR_DUPLICATE_LENGTH_RATIO",
    "MIN_SHARED_QUOTE_CHARS",
    "NEAR_DUPLICATE_CONTAINMENT",
    "NEAR_DUPLICATE_JACCARD",
    "PATH_MIRROR_RHO",
    "SAME_FAMILY_RHO",
    "SHARED_QUOTE_RHO",
    "SHARED_STRUCTURED_RECORD_RHO",
    "aggregate_tasks",
    "analyze_task",
    "canonical_domain",
    "payload_sha256",
]
