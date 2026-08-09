"""Identity-bound compact field evidence over shared authoritative pages.

This module is a pure, label-blind representation primitive.  A visible task
provides one PyPI project and one GitHub ``owner/repository`` identity.  The
caller supplies page bytes fetched during the same forward pass.  Only exact
PyPI/GitHub public addresses and exact response identities may contribute.

The primitive never searches, fetches, calls a model, opens benchmark data, or
reads evaluator feedback.  Missing fields become ``Unknown``.  Any conflicting
value for one field invalidates the whole compact record and returns the raw
shared evidence byte-for-byte.  A content-free receipt exposes counts only;
field values, URLs, page text, predictions, and their hashes are absent.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any
from urllib.parse import unquote, urlsplit

from .clients import canonicalize_url
from .v24967_requirement_aware_source_allocation import (
    normalize_project,
    normalize_repository,
)


POLICY_ID = "v24972_identity_bound_compact_field_evidence_v1"
ROLE = "v24972_identity_bound_compact_field_result"
RECEIPT_ROLE = "v24972_identity_bound_compact_field_receipt"
UNKNOWN = "Unknown"
MAX_PAGES = 16
MAX_PAGE_CHARS = 250_000
MAX_RAW_EVIDENCE_CHARS = 100_000
FIELD_ORDER = (
    "pypi_latest_version",
    "requires_python",
    "github_latest_release_tag",
    "github_latest_release_date",
)
FIELD_LABELS = {
    "pypi_latest_version": "PyPI latest version",
    "requires_python": "Requires-Python",
    "github_latest_release_tag": "GitHub latest release tag",
    "github_latest_release_date": "GitHub latest release date (YYYY-MM-DD)",
}
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.!+_-]{0,127}")
TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/+~-]{0,127}")
PYTHON_SPEC = re.compile(r"[A-Za-z0-9.*<>=!~^,+_() -]{1,128}")
TAG_DATE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._/+~-]{0,127})\s+"
    r"(\d{4}-\d{2}-\d{2})$"
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "input_page_count",
        "exact_authority_page_count",
        "identity_bound_page_count",
        "identity_mismatch_page_count",
        "malformed_page_count",
        "pypi_html_page_count",
        "pypi_json_page_count",
        "github_html_page_count",
        "github_json_page_count",
        "field_observation_count",
        "unique_bound_field_count",
        "unknown_field_count",
        "conflicting_field_count",
        "record_admitted",
        "raw_evidence_chars",
        "compact_prefix_chars",
        "output_evidence_chars",
        "candidate_evidence_changed",
        "field_level_provenance_bound",
        "missing_field_is_unknown",
        "any_field_conflict_invalidates_record",
        "visible_project_and_repository_identity_only",
        "same_forward_shared_page_bytes_only",
        "provider_narrative_or_snippet_used",
        "entropy_or_information_gain_assigns_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "contains_field_value_url_page_prediction_answer_or_credential",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _safe_line(value: object, pattern: re.Pattern[str]) -> str:
    text = " ".join(str(value or "").split())
    if not pattern.fullmatch(text) or any(character in text for character in "|\0"):
        raise ValueError("V2.49.72 unsafe compact field value")
    return text


def _valid_date(value: object) -> str:
    text = str(value or "").strip()[:10]
    try:
        observed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("V2.49.72 invalid release date") from exc
    return observed.isoformat()


def _segments(canonical: str) -> tuple[str, list[str], str]:
    parsed = urlsplit(canonical)
    host = (parsed.hostname or "").casefold().rstrip(".")
    segments = [unquote(part) for part in parsed.path.split("/") if part]
    return host, segments, parsed.query


def authority_kind(
    value: object,
    *,
    project: str,
    repository: str,
) -> str | None:
    """Return one exact authority surface; subpaths and query strings fail."""

    canonical = canonicalize_url(str(value or ""))
    if not canonical:
        return None
    host, segments, query = _segments(canonical)
    if query:
        return None
    expected_project = normalize_project(project)
    owner, repo = normalize_repository(repository)
    folded = [part.casefold() for part in segments]
    if (
        host == "pypi.org"
        and len(folded) == 2
        and folded[0] == "project"
        and normalize_project(folded[1]) == expected_project
    ):
        return "pypi_html"
    if (
        host == "pypi.org"
        and len(folded) == 3
        and folded[0] == "pypi"
        and normalize_project(folded[1]) == expected_project
        and folded[2] == "json"
    ):
        return "pypi_json"
    if (
        host == "github.com"
        and folded == [owner, repo, "releases"]
    ):
        return "github_html"
    if (
        host == "api.github.com"
        and folded == ["repos", owner, repo, "releases", "latest"]
    ):
        return "github_json"
    return None


def _page_text(page: Mapping[str, Any]) -> str:
    value = page.get("text")
    if value is None:
        value = page.get("raw_content")
    if value is None:
        value = page.get("content")
    text = str(value or "")
    if not text or len(text) > MAX_PAGE_CHARS or "\0" in text:
        raise ValueError("V2.49.72 page text is empty or oversized")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _pypi_html(text: str, project: str) -> dict[str, str]:
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    expected = normalize_project(project)
    versions: set[str] = set()
    for line in lines[:128]:
        if " " not in line:
            continue
        identity, candidate = line.rsplit(" ", 1)
        try:
            matches = normalize_project(identity) == expected
        except ValueError:
            matches = False
        if matches and VERSION.fullmatch(candidate):
            versions.add(_safe_line(candidate, VERSION))
    title_identity = any(
        line.casefold() == f"{project} · pypi".casefold() for line in lines[:16]
    )
    if not title_identity or len(versions) != 1:
        raise ValueError("V2.49.72 PyPI HTML identity/version is not unique")
    return {"pypi_latest_version": next(iter(versions))}


def _pypi_json(text: str, project: str) -> dict[str, str]:
    value = json.loads(text)
    info = value.get("info") if isinstance(value, dict) else None
    if not isinstance(info, dict):
        raise ValueError("V2.49.72 PyPI JSON info is absent")
    if normalize_project(info.get("name")) != normalize_project(project):
        raise ValueError("V2.49.72 PyPI JSON primary identity mismatch")
    version = _safe_line(info.get("version"), VERSION)
    raw_python = " ".join(str(info.get("requires_python") or "").split())
    output = {"pypi_latest_version": version}
    if raw_python:
        output["requires_python"] = _safe_line(raw_python, PYTHON_SPEC)
    return output


def _github_html(text: str, repository: str) -> dict[str, str]:
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    owner, repo = normalize_repository(repository)
    identity = f"{owner}/{repo}"
    anchors = {
        f"releases: {identity}",
        f"releases · {identity} · github",
    }
    if not any(line.casefold() in anchors for line in lines[:400]):
        raise ValueError("V2.49.72 GitHub HTML primary identity mismatch")
    candidates: set[tuple[str, str]] = set()
    for index, line in enumerate(lines):
        matched = TAG_DATE.fullmatch(line)
        if matched is None:
            continue
        following = [item.casefold() for item in lines[index + 1 : index + 7]]
        if "latest" not in following:
            continue
        candidates.add(
            (_safe_line(matched.group(1), TAG), _valid_date(matched.group(2)))
        )
    if len(candidates) != 1:
        raise ValueError("V2.49.72 GitHub HTML latest release is not unique")
    tag, released = next(iter(candidates))
    return {
        "github_latest_release_tag": tag,
        "github_latest_release_date": released,
    }


def _github_json(text: str, repository: str) -> dict[str, str]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("V2.49.72 GitHub JSON object is absent")
    if value.get("draft") is True or value.get("prerelease") is True:
        raise ValueError("V2.49.72 GitHub latest response is draft or prerelease")
    owner, repo = normalize_repository(repository)
    html_url = canonicalize_url(str(value.get("html_url") or ""))
    host, segments, query = _segments(html_url) if html_url else ("", [], "")
    folded = [part.casefold() for part in segments]
    tag = _safe_line(value.get("tag_name"), TAG)
    if (
        query
        or host != "github.com"
        or len(folded) != 5
        or folded[:4] != [owner, repo, "releases", "tag"]
        or unquote(segments[4]) != tag
    ):
        raise ValueError("V2.49.72 GitHub JSON primary identity/tag mismatch")
    released = _valid_date(value.get("published_at"))
    return {
        "github_latest_release_tag": tag,
        "github_latest_release_date": released,
    }


PARSERS = {
    "pypi_html": _pypi_html,
    "pypi_json": _pypi_json,
    "github_html": _github_html,
    "github_json": _github_json,
}


def _render_record(
    *,
    project: str,
    repository: str,
    fields: Mapping[str, Mapping[str, Any]],
) -> str:
    lines = [
        "[IDENTITY-BOUND COMPACT FIELD RECORD]",
        f"Package: {project}",
        f"GitHub repository: {repository}",
    ]
    for field in FIELD_ORDER:
        observed = fields[field]
        value = str(observed["value"])
        sources = list(observed["sources"])
        provenance = ", ".join(sources) if sources else "no bound source"
        lines.append(f"{FIELD_LABELS[field]}: {value} [source: {provenance}]")
    lines.extend(
        (
            "Missing fields are Unknown; any field conflict invalidates this record.",
            "[/IDENTITY-BOUND COMPACT FIELD RECORD]",
        )
    )
    return "\n".join(lines)


def build_compact_evidence(
    pages: Sequence[Mapping[str, Any]],
    raw_evidence: str,
    *,
    project: str,
    repository: str,
    total_chars: int,
) -> dict[str, Any]:
    """Prefix raw shared evidence with a bound record under the same char cap."""

    normalize_project(project)
    normalize_repository(repository)
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.49.72 page vector is invalid")
    if len(pages) > MAX_PAGES:
        raise ValueError("V2.49.72 page vector exceeds the hard cap")
    if (
        isinstance(total_chars, bool)
        or not isinstance(total_chars, int)
        or total_chars <= 0
        or total_chars > MAX_RAW_EVIDENCE_CHARS
        or not isinstance(raw_evidence, str)
        or len(raw_evidence) != total_chars
        or "\0" in raw_evidence
    ):
        raise ValueError("V2.49.72 raw evidence budget drifted")

    counts = {
        "exact_authority_page_count": 0,
        "identity_bound_page_count": 0,
        "identity_mismatch_page_count": 0,
        "malformed_page_count": 0,
        "pypi_html_page_count": 0,
        "pypi_json_page_count": 0,
        "github_html_page_count": 0,
        "github_json_page_count": 0,
    }
    observations: dict[str, list[tuple[str, str]]] = {
        field: [] for field in FIELD_ORDER
    }
    for page in pages:
        if not isinstance(page, Mapping):
            counts["malformed_page_count"] += 1
            continue
        source = canonicalize_url(str(page.get("url") or ""))
        kind = authority_kind(source, project=project, repository=repository)
        if kind is None:
            continue
        counts["exact_authority_page_count"] += 1
        counts[f"{kind}_page_count"] += 1
        try:
            text = _page_text(page)
            identity = project if kind.startswith("pypi") else repository
            parsed = PARSERS[kind](text, identity)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            counts["identity_mismatch_page_count"] += 1
            continue
        counts["identity_bound_page_count"] += 1
        for field, value in parsed.items():
            observations[field].append((value, source))

    fields: dict[str, dict[str, Any]] = {}
    conflicting = 0
    observation_count = 0
    unique = 0
    for field in FIELD_ORDER:
        rows = observations[field]
        observation_count += len(rows)
        values = {value for value, _source in rows}
        if len(values) > 1:
            conflicting += 1
            fields[field] = {"value": UNKNOWN, "sources": []}
        elif len(values) == 1:
            value = next(iter(values))
            fields[field] = {
                "value": value,
                "sources": sorted({source for observed, source in rows if observed == value}),
            }
            unique += 1
        else:
            fields[field] = {"value": UNKNOWN, "sources": []}

    record_admitted = conflicting == 0 and unique > 0
    if not record_admitted:
        fields = {
            field: {"value": UNKNOWN, "sources": []} for field in FIELD_ORDER
        }
    prefix = (
        _render_record(project=project, repository=repository, fields=fields)
        if record_admitted
        else ""
    )
    if prefix and len(prefix) + len("\n\n[RAW SHARED EVIDENCE]\n") >= total_chars:
        record_admitted = False
        fields = {
            field: {"value": UNKNOWN, "sources": []} for field in FIELD_ORDER
        }
        prefix = ""
        unique = 0
    candidate = (
        (prefix + "\n\n[RAW SHARED EVIDENCE]\n" + raw_evidence)[:total_chars]
        if record_admitted
        else raw_evidence
    )
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "input_page_count": len(pages),
        **counts,
        "field_observation_count": observation_count,
        "unique_bound_field_count": unique if record_admitted else 0,
        "unknown_field_count": len(FIELD_ORDER) - (unique if record_admitted else 0),
        "conflicting_field_count": conflicting,
        "record_admitted": record_admitted,
        "raw_evidence_chars": len(raw_evidence),
        "compact_prefix_chars": len(prefix),
        "output_evidence_chars": len(candidate),
        "candidate_evidence_changed": candidate != raw_evidence,
        "field_level_provenance_bound": record_admitted,
        "missing_field_is_unknown": True,
        "any_field_conflict_invalidates_record": True,
        "visible_project_and_repository_identity_only": True,
        "same_forward_shared_page_bytes_only": True,
        "provider_narrative_or_snippet_used": False,
        "entropy_or_information_gain_assigns_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "contains_field_value_url_page_prediction_answer_or_credential": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    validate_receipt(receipt, total_chars=total_chars)
    result = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "evidence": candidate,
        "record": {
            "project": project,
            "repository": repository,
            "fields": copy.deepcopy(fields),
        },
        "receipt": receipt,
    }
    return result


def validate_receipt(value: Mapping[str, Any], *, total_chars: int) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = (
        "input_page_count",
        "exact_authority_page_count",
        "identity_bound_page_count",
        "identity_mismatch_page_count",
        "malformed_page_count",
        "pypi_html_page_count",
        "pypi_json_page_count",
        "github_html_page_count",
        "github_json_page_count",
        "field_observation_count",
        "unique_bound_field_count",
        "unknown_field_count",
        "conflicting_field_count",
        "raw_evidence_chars",
        "compact_prefix_chars",
        "output_evidence_chars",
    )
    admitted = copied.get("record_admitted") is True
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or copied["input_page_count"] > MAX_PAGES
        or copied["exact_authority_page_count"]
        != sum(
            copied[name]
            for name in (
                "pypi_html_page_count",
                "pypi_json_page_count",
                "github_html_page_count",
                "github_json_page_count",
            )
        )
        or copied["identity_bound_page_count"]
        + copied["identity_mismatch_page_count"]
        != copied["exact_authority_page_count"]
        or copied["unique_bound_field_count"] + copied["unknown_field_count"]
        != len(FIELD_ORDER)
        or copied["unique_bound_field_count"] > len(FIELD_ORDER)
        or copied["conflicting_field_count"] > len(FIELD_ORDER)
        or copied["raw_evidence_chars"] != total_chars
        or copied["output_evidence_chars"] != total_chars
        or admitted is not (copied["unique_bound_field_count"] > 0)
        or copied.get("candidate_evidence_changed") is not admitted
        or copied.get("field_level_provenance_bound") is not admitted
        or (not admitted and copied["compact_prefix_chars"] != 0)
        or (admitted and copied["compact_prefix_chars"] <= 0)
        or (copied["conflicting_field_count"] > 0 and admitted)
        or copied.get("missing_field_is_unknown") is not True
        or copied.get("any_field_conflict_invalidates_record") is not True
        or copied.get("visible_project_and_repository_identity_only") is not True
        or copied.get("same_forward_shared_page_bytes_only") is not True
        or copied.get("provider_narrative_or_snippet_used") is not False
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or copied.get("contains_field_value_url_page_prediction_answer_or_credential")
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.72 compact field receipt drifted")
    return copied


__all__ = [
    "FIELD_LABELS",
    "FIELD_ORDER",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "UNKNOWN",
    "authority_kind",
    "build_compact_evidence",
    "payload_sha256",
    "validate_receipt",
]
