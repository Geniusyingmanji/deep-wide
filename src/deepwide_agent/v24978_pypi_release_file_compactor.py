"""Pure identity-bound compaction of late PyPI release-file fields."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from .clients import canonicalize_url
from .v24967_requirement_aware_source_allocation import normalize_project
from .v24972_identity_bound_compact_fields import PYTHON_SPEC, VERSION, _safe_line


POLICY_ID = "v24978_pypi_release_file_compactor_v1"
ROLE = "v24978_pypi_release_file_compactor_result"
RECEIPT_ROLE = "v24978_pypi_release_file_compactor_receipt"
UNKNOWN = "Unknown"
MAX_PAGE_CHARS = 32_000_000
MAX_EVIDENCE_CHARS = 100_000
FIELD_ORDER = (
    "latest_version",
    "requires_python",
    "release_file_count",
    "first_upload_date",
    "largest_file_size_bytes",
)
FIELD_LABELS = {
    "latest_version": "Latest version",
    "requires_python": "Requires-Python",
    "release_file_count": "Current-version file count",
    "first_upload_date": "Current-version first upload date (YYYY-MM-DD)",
    "largest_file_size_bytes": "Current-version largest file size (bytes)",
}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def payload_sha256(value: object) -> str:
    from .v24972_identity_bound_compact_fields import payload_sha256 as digest

    return digest(value)


def _exact_url(project: str) -> str:
    return canonicalize_url(f"https://pypi.org/pypi/{project}/json")


def _upload_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("V2.49.78 upload time is absent")
    candidate = text[:10]
    if not DATE.fullmatch(candidate):
        raise ValueError("V2.49.78 upload date is malformed")
    datetime.strptime(candidate, "%Y-%m-%d")
    return candidate


def extract_record(page: Mapping[str, Any], *, project: str) -> dict[str, str]:
    if not isinstance(page, Mapping):
        raise ValueError("V2.49.78 page is not a mapping")
    source = canonicalize_url(str(page.get("url") or ""))
    if source != _exact_url(project):
        raise ValueError("V2.49.78 exact PyPI authority address mismatch")
    text = str(page.get("text") or page.get("raw_content") or "")
    if not text or len(text) > MAX_PAGE_CHARS or "\0" in text:
        raise ValueError("V2.49.78 PyPI page is empty or oversized")
    value = json.loads(text)
    info = value.get("info") if isinstance(value, dict) else None
    releases = value.get("releases") if isinstance(value, dict) else None
    if not isinstance(info, dict) or not isinstance(releases, dict):
        raise ValueError("V2.49.78 PyPI response schema drifted")
    if normalize_project(info.get("name")) != normalize_project(project):
        raise ValueError("V2.49.78 primary project identity mismatch")
    version = _safe_line(info.get("version"), VERSION)
    files = releases.get(version)
    if not isinstance(files, list) or not files:
        raise ValueError("V2.49.78 current-version file vector is absent")
    upload_dates: list[str] = []
    sizes: list[int] = []
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("V2.49.78 release file row is malformed")
        upload_dates.append(
            _upload_date(row.get("upload_time_iso_8601") or row.get("upload_time"))
        )
        size = row.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("V2.49.78 release file size is malformed")
        sizes.append(size)
    raw_python = " ".join(str(info.get("requires_python") or "").split())
    requires_python = (
        _safe_line(raw_python, PYTHON_SPEC) if raw_python else UNKNOWN
    )
    return {
        "latest_version": version,
        "requires_python": requires_python,
        "release_file_count": str(len(files)),
        "first_upload_date": min(upload_dates),
        "largest_file_size_bytes": str(max(sizes)),
    }


def build_compact_evidence(
    pages: Sequence[Mapping[str, Any]],
    raw_evidence: str,
    *,
    project: str,
    total_chars: int,
) -> dict[str, Any]:
    normalize_project(project)
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence) or len(pages) != 1:
        raise ValueError("V2.49.78 requires exactly one PyPI authority page")
    if (
        isinstance(total_chars, bool)
        or not isinstance(total_chars, int)
        or total_chars <= 0
        or total_chars > MAX_EVIDENCE_CHARS
        or not isinstance(raw_evidence, str)
        or len(raw_evidence) != total_chars
        or "\0" in raw_evidence
    ):
        raise ValueError("V2.49.78 raw evidence budget drifted")
    fields = extract_record(pages[0], project=project)
    source = _exact_url(project)
    lines = [
        "[IDENTITY-BOUND PYPI RELEASE-FILE RECORD]",
        f"Package: {project}",
    ]
    for field in FIELD_ORDER:
        lines.append(f"{FIELD_LABELS[field]}: {fields[field]} [source: {source}]")
    lines.extend(
        (
            "All fields bind to the exact current PyPI project and version.",
            "[/IDENTITY-BOUND PYPI RELEASE-FILE RECORD]",
        )
    )
    prefix = "\n".join(lines)
    marker = "\n\n[RAW SHARED PYPI JSON]\n"
    if len(prefix) + len(marker) >= total_chars:
        raise ValueError("V2.49.78 compact record does not fit the fixed cap")
    evidence = (prefix + marker + raw_evidence)[:total_chars]
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "input_page_count": 1,
        "exact_authority_page_count": 1,
        "identity_bound_page_count": 1,
        "unique_bound_field_count": len(FIELD_ORDER),
        "unknown_field_count": int(fields["requires_python"] == UNKNOWN),
        "conflicting_field_count": 0,
        "record_admitted": True,
        "raw_evidence_chars": len(raw_evidence),
        "compact_prefix_chars": len(prefix),
        "output_evidence_chars": len(evidence),
        "candidate_evidence_changed": evidence != raw_evidence,
        "current_version_file_vector_bound": True,
        "file_count_upload_date_and_size_derived_deterministically": True,
        "same_forward_shared_page_bytes_only": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "contains_field_value_url_page_prediction_answer_or_credential": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "evidence": evidence,
        "record": {"project": project, "fields": copy.deepcopy(fields)},
        "receipt": receipt,
    }


def validate_receipt(value: Mapping[str, Any], *, total_chars: int) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    if (
        copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("input_page_count") != 1
        or copied.get("exact_authority_page_count") != 1
        or copied.get("identity_bound_page_count") != 1
        or copied.get("unique_bound_field_count") != len(FIELD_ORDER)
        or copied.get("conflicting_field_count") != 0
        or copied.get("record_admitted") is not True
        or copied.get("raw_evidence_chars") != total_chars
        or copied.get("output_evidence_chars") != total_chars
        or copied.get("candidate_evidence_changed") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or copied.get("contains_field_value_url_page_prediction_answer_or_credential") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.78 receipt drifted")
    return copied


__all__ = [
    "FIELD_LABELS", "FIELD_ORDER", "MAX_PAGE_CHARS", "POLICY_ID", "RECEIPT_ROLE",
    "ROLE", "UNKNOWN", "build_compact_evidence", "extract_record",
    "payload_sha256", "validate_receipt",
]
