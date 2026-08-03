"""Programmatic evidence-support catalog for entropy-gated cell revision.

V2.43.30 showed that model-declared citations were the activation bottleneck:
all proposed changes were rejected for fetch-integrity or source-independence,
not for the entropy threshold.  This pure, benchmark-external successor builds
eligible support sets *before* revision.  A model may select a sealed support
set, but cannot manufacture its evidence membership, target binding, value, or
source independence.

The catalog is runtime-private because it contains visible candidate values and
evidence IDs.  Public receipts returned by ``resolve_support_selection`` contain
only hashes, counts, a disposition, and entropy credit.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .v24323_shared_prefix_cell_entropy import (
    AnonymousCellBelief,
    ReserveEvidenceSignal,
    admit_reserve_evidence,
    payload_sha256,
    validate_admission_receipt,
)


POLICY_ID = "v24333_programmatic_multihost_support_catalog_v1"
CATALOG_ROLE = "v24333_programmatic_support_catalog"
RESOLUTION_ROLE = "v24333_support_selection_receipt"
UNKNOWN = frozenset(
    {"", "-", "—", "?", "n/a", "na", "none", "null", "unknown", "未知", "不详", "无法确认"}
)
DISPOSITIONS = frozenset(
    {
        "admit_programmatic_support",
        "admit_programmatic_override",
        "quarantine_unknown_support_set",
        "quarantine_target_binding",
        "quarantine_value_binding",
        "quarantine_evidence_binding",
    }
)
COMMON_SECOND_LEVEL_SUFFIXES = frozenset(
    {
        "ac.uk", "co.uk", "gov.uk", "org.uk", "com.au", "edu.au", "gov.au",
        "com.cn", "edu.cn", "gov.cn", "org.cn", "co.jp", "ac.jp", "go.jp",
        "co.kr", "ac.kr", "go.kr", "com.br", "com.mx", "co.nz", "co.in",
    }
)
STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
        "has", "have", "in", "is", "it", "of", "on", "or", "that", "the", "this",
        "to", "was", "were", "with", "official", "record", "records", "source",
        "page", "result", "results", "unknown", "name", "value", "值", "名称", "结果",
    }
)
STRUCTURED_PATTERNS = (
    re.compile(r"(?<!\d)(?:1[0-9]{3}|20[0-9]{2}|21[0-9]{2})(?!\d)"),
    re.compile(r"(?<!\d)\d{4}[-/]\d{1,2}[-/]\d{1,2}(?!\d)"),
    re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)*(?:%|％)?(?![\w.])"),
    re.compile(r"[\"“‘「『]([^\"”’」』\n]{2,80})[\"”’」』]"),
)
TOKEN_PATTERN = re.compile(
    r"\d{1,4}(?:[.,]\d+)*(?:%|％)?|[A-Za-z][A-Za-z0-9&'’./-]{1,30}|[\u4e00-\u9fff]{2,24}"
)
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "target_count",
        "page_count",
        "intact_page_count",
        "independent_source_count",
        "minimum_unknown_sources",
        "minimum_override_sources",
        "candidate_groups_considered",
        "eligible_support_set_count",
        "quarantined_candidate_groups",
        "support_sets",
        "catalog_payload_sha256",
    }
)
SUPPORT_SET_KEYS = frozenset(
    {
        "support_set_id",
        "target_binding_sha256",
        "row_key",
        "column",
        "old_value",
        "baseline_cell_unknown",
        "candidate_value",
        "candidate_value_sha256",
        "evidence_ids",
        "evidence_source_bindings",
        "evidence_membership_sha256",
        "independent_source_count",
        "corroborating_source_count",
        "conflicting_source_count",
        "required_source_count",
        "admission_receipt",
    }
)
RESOLUTION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "catalog_payload_sha256",
        "support_set_id_sha256",
        "selection_binding_sha256",
        "target_binding_matches",
        "value_binding_matches",
        "evidence_binding_matches",
        "independent_source_count",
        "required_source_count",
        "disposition",
        "admitted",
        "conditional_entropy_reduction_nats",
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(text.split())


def _support_normalize(value: object) -> str:
    return "".join(
        character
        for character in _normalize(value)
        if character.isalnum() or "\u4e00" <= character <= "\u9fff"
    )


def _is_unknown(value: object) -> bool:
    return _normalize(value) in UNKNOWN


def _source_key(host: str) -> str:
    value = _normalize(host).strip(".")
    if not value or re.fullmatch(r"[a-z0-9.-]+", value) is None:
        raise ValueError("V2.43.33 host is invalid")
    labels = [item for item in value.split(".") if item]
    if len(labels) < 2:
        raise ValueError("V2.43.33 host is not independently attributable")
    last_two = ".".join(labels[-2:])
    if last_two in COMMON_SECOND_LEVEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return last_two


@dataclass(frozen=True)
class CellTarget:
    row_key: str
    column: str
    old_value: str | None

    def validate(self) -> None:
        if not _normalize(self.row_key) or not _normalize(self.column):
            raise ValueError("V2.43.33 target binding is empty")
        if self.old_value is not None and not isinstance(self.old_value, str):
            raise ValueError("V2.43.33 old value is not text")

    @property
    def baseline_unknown(self) -> bool:
        return self.old_value is None or _is_unknown(self.old_value)

    @property
    def binding_sha256(self) -> str:
        self.validate()
        return payload_sha256(
            {
                "row_key": _normalize(self.row_key),
                "column": _normalize(self.column),
                "old_value": None if self.old_value is None else _normalize(self.old_value),
            }
        )


@dataclass(frozen=True)
class SupportPage:
    evidence_id: str
    host: str
    content: str
    fetch_integrity: bool

    def validate(self) -> None:
        if re.fullmatch(r"R\d{4}", self.evidence_id) is None:
            raise ValueError("V2.43.33 evidence ID is invalid")
        _source_key(self.host)
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("V2.43.33 support page content is empty")
        if not isinstance(self.fetch_integrity, bool):
            raise ValueError("V2.43.33 fetch integrity is not boolean")


def _coerce_target(value: CellTarget | Mapping[str, Any]) -> CellTarget:
    if isinstance(value, CellTarget):
        target = value
    elif isinstance(value, Mapping) and set(value) == {"row_key", "column", "old_value"}:
        target = CellTarget(
            row_key=str(value["row_key"]),
            column=str(value["column"]),
            old_value=None if value["old_value"] is None else str(value["old_value"]),
        )
    else:
        raise ValueError("V2.43.33 target schema drifted")
    target.validate()
    return target


def _coerce_page(value: SupportPage | Mapping[str, Any]) -> SupportPage:
    if isinstance(value, SupportPage):
        page = value
    elif isinstance(value, Mapping) and {"evidence_id", "host", "content", "fetch_integrity"}.issubset(value):
        page = SupportPage(
            evidence_id=str(value["evidence_id"]),
            host=str(value["host"]),
            content=str(value["content"]),
            fetch_integrity=value["fetch_integrity"],
        )
    else:
        raise ValueError("V2.43.33 support page schema drifted")
    page.validate()
    return page


def _entity_windows(content: str, entity: str, *, radius: int = 600) -> list[str]:
    text = unicodedata.normalize("NFKC", content)
    needle = unicodedata.normalize("NFKC", entity).strip()
    if len(needle) < 2:
        return []
    output: list[str] = []
    for match in re.finditer(re.escape(needle), text, flags=re.IGNORECASE):
        start = max(0, match.start() - radius)
        end = min(len(text), match.end() + radius)
        output.append(text[start:end])
    return output


def _column_tokens(column: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", column).casefold()
    values = [
        match.group(0)
        for match in re.finditer(r"[a-z0-9]{3,}|[\u4e00-\u9fff]{2,}", normalized)
        if match.group(0) not in STOPWORDS
    ]
    exact = _normalize(column)
    if exact and exact not in values:
        values.append(exact)
    return tuple(dict.fromkeys(values))


def _column_neighborhoods(window: str, column: str, *, radius: int = 180) -> list[str]:
    text = unicodedata.normalize("NFKC", window)
    output: list[str] = []
    for token in _column_tokens(column):
        for match in re.finditer(re.escape(token), text, flags=re.IGNORECASE):
            output.append(
                text[max(0, match.start() - radius) : min(len(text), match.end() + radius)]
            )
    return output


def _candidate_values(window: str, target: CellTarget) -> set[str]:
    values: set[str] = set()
    neighborhoods = _column_neighborhoods(window, target.column)
    for neighborhood in neighborhoods:
        for pattern in STRUCTURED_PATTERNS:
            for match in pattern.finditer(neighborhood):
                value = match.group(1) if match.lastindex else match.group(0)
                values.add(" ".join(value.strip().split()))
        for token in _column_tokens(target.column):
            relation = re.compile(
                re.escape(token)
                + r"\s*(?::|=|is|are|was|were|为|是|：|－|-)\s*"
                + r"([^\n|.;。；]{1,80})",
                flags=re.IGNORECASE,
            )
            for match in relation.finditer(neighborhood):
                values.add(" ".join(match.group(1).strip().split()))
    excluded = {
        _support_normalize(target.row_key),
        _support_normalize(target.column),
        _support_normalize(target.old_value),
    }
    row_normalized = _support_normalize(target.row_key)
    column_normalized = _support_normalize(target.column)
    output: set[str] = set()
    for value in values:
        normalized = _support_normalize(value)
        words = _normalize(value).split()
        if (
            not 2 <= len(value) <= 80
            or not normalized
            or normalized in excluded
            or (row_normalized and row_normalized in normalized)
            or (column_normalized and column_normalized in normalized)
            or _normalize(value) in UNKNOWN
            or (len(words) == 1 and words[0] in STOPWORDS)
            or value.casefold().startswith(("http://", "https://"))
            or all(character.isdigit() for character in normalized) and len(normalized) > 10
        ):
            continue
        output.add(value)
    return output


def _candidate_priority(value: str) -> tuple[int, int, int, str]:
    normalized = _normalize(value)
    structured = int(
        any(pattern.fullmatch(value) for pattern in STRUCTURED_PATTERNS[:3])
    )
    token_count = len(TOKEN_PATTERN.findall(value))
    return (-structured, token_count, len(value), normalized)


def _aggregate_reliability(source_count: int) -> float:
    if source_count < 1:
        return 0.0
    return round(min(0.95, 0.75 + 0.05 * (source_count - 1)), 12)


def _candidate_support(
    target: CellTarget,
    pages: Sequence[SupportPage],
) -> tuple[dict[str, dict[str, tuple[str, int]]], set[str]]:
    groups: dict[str, dict[str, tuple[str, int]]] = defaultdict(dict)
    originals: dict[str, list[str]] = defaultdict(list)
    old_sources: set[str] = set()
    old_normalized = _support_normalize(target.old_value)
    for page in pages:
        if not page.fetch_integrity:
            continue
        source = _source_key(page.host)
        windows = _entity_windows(page.content, target.row_key)
        if old_normalized and any(old_normalized in _support_normalize(window) for window in windows):
            old_sources.add(source)
        for window in windows:
            for candidate in _candidate_values(window, target):
                normalized = _support_normalize(candidate)
                if not normalized:
                    continue
                originals[normalized].append(candidate)
                current = groups[normalized].get(source)
                choice = (page.evidence_id, len(window))
                if current is None or choice < current:
                    groups[normalized][source] = choice
    canonicalized: dict[str, dict[str, tuple[str, int]]] = {}
    for normalized, sources in groups.items():
        canonical = sorted(set(originals[normalized]), key=_candidate_priority)[0]
        canonicalized[canonical] = sources
    return canonicalized, old_sources


def _support_set(
    target: CellTarget,
    candidate: str,
    sources: Mapping[str, tuple[str, int]],
    old_sources: set[str],
    *,
    required_sources: int,
) -> dict[str, Any]:
    selected_sources = sorted(sources)
    evidence_ids = [sources[source][0] for source in selected_sources]
    reliability = _aggregate_reliability(len(selected_sources))
    conflicting = len(old_sources.difference(selected_sources))
    if target.baseline_unknown:
        belief = AnonymousCellBelief((0.55, 0.45), 0)
        likelihoods = (8.0, 1.0)
    else:
        belief = AnonymousCellBelief((0.70, 0.30), 0)
        likelihoods = (0.5, 8.0)
    admission = admit_reserve_evidence(
        belief,
        ReserveEvidenceSignal(
            likelihood_ratios=likelihoods,
            source_reliability=reliability,
            source_independence=1.0,
            fetch_integrity=True,
            independent_sources=len(selected_sources),
            corroborating_sources=len(selected_sources),
            conflicting_sources=conflicting,
            evidence_chars=sum(sources[source][1] for source in selected_sources),
        ),
    )
    validate_admission_receipt(admission)
    membership = [
        {"source_key_sha256": _sha256_text(source), "evidence_id": sources[source][0]}
        for source in selected_sources
    ]
    identity = {
        "target_binding_sha256": target.binding_sha256,
        "candidate_value_sha256": _sha256_text(_normalize(candidate)),
        "evidence_membership_sha256": payload_sha256(membership),
        "required_source_count": required_sources,
    }
    support_id = payload_sha256(identity)
    return {
        "support_set_id": support_id,
        "target_binding_sha256": target.binding_sha256,
        "row_key": target.row_key,
        "column": target.column,
        "old_value": target.old_value,
        "baseline_cell_unknown": target.baseline_unknown,
        "candidate_value": candidate,
        "candidate_value_sha256": identity["candidate_value_sha256"],
        "evidence_ids": evidence_ids,
        "evidence_source_bindings": membership,
        "evidence_membership_sha256": identity["evidence_membership_sha256"],
        "independent_source_count": len(selected_sources),
        "corroborating_source_count": len(selected_sources),
        "conflicting_source_count": conflicting,
        "required_source_count": required_sources,
        "admission_receipt": admission,
    }


def build_support_catalog(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    pages: Sequence[SupportPage | Mapping[str, Any]],
    *,
    minimum_unknown_sources: int = 2,
    minimum_override_sources: int = 3,
    maximum_support_sets_per_target: int = 32,
) -> dict[str, Any]:
    if isinstance(targets, (str, bytes)) or isinstance(pages, (str, bytes)):
        raise ValueError("V2.43.33 catalog input is not a sequence")
    if (
        isinstance(minimum_unknown_sources, bool)
        or not isinstance(minimum_unknown_sources, int)
        or minimum_unknown_sources < 2
        or isinstance(minimum_override_sources, bool)
        or not isinstance(minimum_override_sources, int)
        or minimum_override_sources < 3
        or minimum_override_sources < minimum_unknown_sources
        or isinstance(maximum_support_sets_per_target, bool)
        or not isinstance(maximum_support_sets_per_target, int)
        or maximum_support_sets_per_target < 1
    ):
        raise ValueError("V2.43.33 catalog threshold drifted")
    cells = [_coerce_target(value) for value in targets]
    evidence = [_coerce_page(value) for value in pages]
    if len({target.binding_sha256 for target in cells}) != len(cells):
        raise ValueError("V2.43.33 duplicate target binding")
    if len({page.evidence_id for page in evidence}) != len(evidence):
        raise ValueError("V2.43.33 duplicate evidence ID")
    support_sets: list[dict[str, Any]] = []
    quarantine: Counter[str] = Counter()
    considered = 0
    for target in sorted(cells, key=lambda value: value.binding_sha256):
        groups, old_sources = _candidate_support(target, evidence)
        required = minimum_unknown_sources if target.baseline_unknown else minimum_override_sources
        ranked = sorted(
            groups.items(),
            key=lambda item: (-len(item[1]), _candidate_priority(item[0])),
        )
        eligible_for_target: list[dict[str, Any]] = []
        for candidate, sources in ranked:
            considered += 1
            if len(sources) < required:
                quarantine["quarantine_insufficient_independence"] += 1
                continue
            item = _support_set(
                target,
                candidate,
                sources,
                old_sources,
                required_sources=required,
            )
            disposition = item["admission_receipt"]["disposition"]
            if item["admission_receipt"]["context_action"] == "core_only":
                quarantine[str(disposition)] += 1
                continue
            eligible_for_target.append(item)
        support_sets.extend(eligible_for_target[:maximum_support_sets_per_target])
        if len(eligible_for_target) > maximum_support_sets_per_target:
            quarantine["quarantine_catalog_capacity"] += (
                len(eligible_for_target) - maximum_support_sets_per_target
            )
    support_sets.sort(key=lambda item: item["support_set_id"])
    value = {
        "artifact_version": 1,
        "role": CATALOG_ROLE,
        "policy_id": POLICY_ID,
        "target_count": len(cells),
        "page_count": len(evidence),
        "intact_page_count": sum(page.fetch_integrity for page in evidence),
        "independent_source_count": len({_source_key(page.host) for page in evidence if page.fetch_integrity}),
        "minimum_unknown_sources": minimum_unknown_sources,
        "minimum_override_sources": minimum_override_sources,
        "candidate_groups_considered": considered,
        "eligible_support_set_count": len(support_sets),
        "quarantined_candidate_groups": dict(sorted(quarantine.items())),
        "support_sets": support_sets,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    validate_catalog_identity(value)
    return value


def validate_catalog_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    support_sets = value.get("support_sets")
    quarantine = value.get("quarantined_candidate_groups")
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != CATALOG_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(support_sets, list)
        or value.get("eligible_support_set_count") != len(support_sets)
        or not isinstance(quarantine, Mapping)
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in quarantine.values())
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.33 catalog identity drifted")
    seen: set[str] = set()
    for item in support_sets:
        if not isinstance(item, Mapping) or set(item) != SUPPORT_SET_KEYS:
            raise ValueError("V2.43.33 support-set schema drifted")
        admission = item.get("admission_receipt")
        validate_admission_receipt(admission)
        bindings = item.get("evidence_source_bindings")
        if not isinstance(bindings, list) or any(
            not isinstance(binding, Mapping)
            or set(binding) != {"source_key_sha256", "evidence_id"}
            or re.fullmatch(r"[0-9a-f]{64}", str(binding["source_key_sha256"]))
            is None
            or re.fullmatch(r"R\d{4}", str(binding["evidence_id"])) is None
            for binding in bindings
        ):
            raise ValueError("V2.43.33 evidence-source binding drifted")
        expected_target_binding = CellTarget(
            row_key=str(item.get("row_key")),
            column=str(item.get("column")),
            old_value=(
                None
                if item.get("old_value") is None
                else str(item.get("old_value"))
            ),
        ).binding_sha256
        expected_membership_sha256 = payload_sha256(bindings)
        expected_support_set_id = payload_sha256(
            {
                "target_binding_sha256": item.get("target_binding_sha256"),
                "candidate_value_sha256": item.get("candidate_value_sha256"),
                "evidence_membership_sha256": item.get(
                    "evidence_membership_sha256"
                ),
                "required_source_count": item.get("required_source_count"),
            }
        )
        if (
            not isinstance(item.get("support_set_id"), str)
            or re.fullmatch(r"[0-9a-f]{64}", item["support_set_id"]) is None
            or item["support_set_id"] in seen
            or item["support_set_id"] != expected_support_set_id
            or not isinstance(item.get("target_binding_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", item["target_binding_sha256"]) is None
            or item["target_binding_sha256"] != expected_target_binding
            or item.get("baseline_cell_unknown")
            is not (
                item.get("old_value") is None or _is_unknown(item.get("old_value"))
            )
            or item.get("candidate_value_sha256") != _sha256_text(_normalize(item.get("candidate_value")))
            or not isinstance(item.get("evidence_ids"), list)
            or len(item["evidence_ids"]) != len(set(item["evidence_ids"]))
            or item["evidence_ids"]
            != [str(binding["evidence_id"]) for binding in bindings]
            or item.get("evidence_membership_sha256")
            != expected_membership_sha256
            or item.get("independent_source_count")
            != len({str(binding["source_key_sha256"]) for binding in bindings})
            or item.get("corroborating_source_count") != len(bindings)
            or item["admission_receipt"]["anonymous_evidence"][
                "independent_sources"
            ]
            != item.get("independent_source_count")
            or item["admission_receipt"]["anonymous_evidence"][
                "corroborating_sources"
            ]
            != item.get("corroborating_source_count")
            or item.get("independent_source_count", 0) < item.get("required_source_count", 1)
            or admission["context_action"] == "core_only"
        ):
            raise ValueError("V2.43.33 support-set identity drifted")
        seen.add(item["support_set_id"])
    return dict(value)


def validate_support_catalog(
    value: Mapping[str, Any],
    targets: Sequence[CellTarget | Mapping[str, Any]],
    pages: Sequence[SupportPage | Mapping[str, Any]],
    *,
    maximum_support_sets_per_target: int = 32,
) -> dict[str, Any]:
    expected = build_support_catalog(
        targets,
        pages,
        minimum_unknown_sources=int(value.get("minimum_unknown_sources", -1)),
        minimum_override_sources=int(value.get("minimum_override_sources", -1)),
        maximum_support_sets_per_target=maximum_support_sets_per_target,
    )
    if dict(value) != expected:
        raise ValueError("V2.43.33 catalog replay drifted")
    return validate_catalog_identity(value)


def resolve_support_selection(
    catalog: Mapping[str, Any],
    *,
    row_key: str,
    column: str,
    new_value: str,
    support_set_id: str,
    declared_evidence_ids: Sequence[str],
) -> dict[str, Any]:
    validate_catalog_identity(catalog)
    by_id = {item["support_set_id"]: item for item in catalog["support_sets"]}
    item = by_id.get(support_set_id)
    target_matches = False
    value_matches = False
    evidence_matches = False
    independent = 0
    required = 0
    credit = 0.0
    if item is None:
        disposition = "quarantine_unknown_support_set"
    else:
        target_matches = (
            _normalize(row_key) == _normalize(item["row_key"])
            and _normalize(column) == _normalize(item["column"])
        )
        value_matches = _support_normalize(new_value) == _support_normalize(
            item["candidate_value"]
        )
        evidence_matches = (
            isinstance(declared_evidence_ids, Sequence)
            and not isinstance(declared_evidence_ids, (str, bytes))
            and list(declared_evidence_ids) == item["evidence_ids"]
        )
        independent = int(item["independent_source_count"])
        required = int(item["required_source_count"])
        if not target_matches:
            disposition = "quarantine_target_binding"
        elif not value_matches:
            disposition = "quarantine_value_binding"
        elif not evidence_matches:
            disposition = "quarantine_evidence_binding"
        elif item["baseline_cell_unknown"]:
            disposition = "admit_programmatic_support"
            credit = float(
                item["admission_receipt"]["conditional_entropy_reduction_nats"]
            )
        else:
            disposition = "admit_programmatic_override"
            credit = float(
                item["admission_receipt"]["conditional_entropy_reduction_nats"]
            )
    admitted = disposition.startswith("admit_")
    value = {
        "artifact_version": 1,
        "role": RESOLUTION_ROLE,
        "policy_id": POLICY_ID,
        "catalog_payload_sha256": catalog["catalog_payload_sha256"],
        "support_set_id_sha256": _sha256_text(str(support_set_id)),
        "selection_binding_sha256": payload_sha256(
            {
                "row_key": _normalize(row_key),
                "column": _normalize(column),
                "new_value": _normalize(new_value),
                "support_set_id": str(support_set_id),
                "declared_evidence_ids": list(declared_evidence_ids)
                if isinstance(declared_evidence_ids, Sequence)
                and not isinstance(declared_evidence_ids, (str, bytes))
                else None,
            }
        ),
        "target_binding_matches": target_matches,
        "value_binding_matches": value_matches,
        "evidence_binding_matches": evidence_matches,
        "independent_source_count": independent,
        "required_source_count": required,
        "disposition": disposition,
        "admitted": admitted,
        "conditional_entropy_reduction_nats": round(credit, 12),
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_resolution_receipt(value)
    return value


def validate_resolution_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    disposition = value.get("disposition")
    admitted = value.get("admitted")
    credit = value.get("conditional_entropy_reduction_nats")
    if (
        set(value) != RESOLUTION_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RESOLUTION_ROLE
        or value.get("policy_id") != POLICY_ID
        or disposition not in DISPOSITIONS
        or admitted is not str(disposition).startswith("admit_")
        or isinstance(credit, bool)
        or not isinstance(credit, (int, float))
        or not math.isfinite(float(credit))
        or float(credit) < 0
        or (admitted and float(credit) <= 0)
        or (not admitted and float(credit) != 0)
        or value.get("question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.33 resolution receipt drifted")
    return dict(value)


__all__ = [
    "CATALOG_ROLE",
    "CellTarget",
    "POLICY_ID",
    "RESOLUTION_ROLE",
    "SupportPage",
    "build_support_catalog",
    "resolve_support_selection",
    "validate_catalog_identity",
    "validate_resolution_receipt",
    "validate_support_catalog",
]
