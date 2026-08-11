"""Pure identity-bound current-release representation for PyPI JSON bytes.

The caller supplies one public PyPI JSON response fetched during the same
forward pass and a project identity visible in the user question.  The
primitive binds ``info.name``, ``info.version``, ``info.requires_python``, and
the earliest upload date under ``releases[info.version]`` into one coherent
current-release record.  It never searches, fetches, calls a model, reads a
benchmark, or accesses evaluator feedback.

The returned candidate evidence has the same exact character budget as the
raw-prefix control.  A content-free receipt contains counts and booleans only;
it excludes project names, field values, raw bytes, URLs, and content hashes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import date
from typing import Any

POLICY_ID = "v25047_identity_bound_pypi_current_release_record_v1"
ROLE = "v25047_pypi_current_release_representation_result"
RECEIPT_ROLE = "v25047_content_free_pypi_current_release_receipt"
MAX_RAW_BYTES = 64 * 1024 * 1024
MAX_EVIDENCE_CHARS = 100_000
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.!+_-]{0,127}")
PYTHON_SPEC = re.compile(r"[A-Za-z0-9.*<>=!~^,+_() ;:-]{1,256}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}")
UPLOAD_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PROJECT_NORMALIZER = re.compile(r"[-_.]+")


def normalize_project(value: object) -> str:
    """Normalize one visible PyPI identity without importing search policy."""

    text = PROJECT_NORMALIZER.sub("-", str(value).strip().casefold()).strip("-")
    if not text or len(text) > 128 or re.fullmatch(r"[a-z0-9-]+", text) is None:
        raise ValueError("V2.50.47 invalid visible PyPI project identity")
    return text


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _safe_line(value: object, pattern: re.Pattern[str], *, field: str) -> str:
    text = " ".join(str(value or "").split())
    if (
        not text
        or not pattern.fullmatch(text)
        or any(character in text for character in "|\r\n\x00")
    ):
        raise ValueError(f"V2.50.47 invalid {field}")
    return text


def _release_dates(files: object) -> list[str]:
    if not isinstance(files, list) or not files:
        raise ValueError("V2.50.47 current release files absent")
    values: set[str] = set()
    invalid = 0
    for item in files:
        if not isinstance(item, Mapping):
            invalid += 1
            continue
        raw = str(
            item.get("upload_time_iso_8601")
            or item.get("upload_time")
            or ""
        )[:10]
        if not UPLOAD_DATE.fullmatch(raw):
            invalid += 1
            continue
        try:
            values.add(date.fromisoformat(raw).isoformat())
        except ValueError:
            invalid += 1
    if not values:
        raise ValueError("V2.50.47 current release upload date absent")
    return sorted(values)


def parse_current_record(raw_json: str, *, visible_project: str) -> dict[str, str]:
    """Parse one exact identity-bound current-release record."""

    expected = normalize_project(visible_project)
    if (
        not isinstance(raw_json, str)
        or not raw_json
        or len(raw_json.encode("utf-8")) > MAX_RAW_BYTES
        or "\x00" in raw_json
    ):
        raise ValueError("V2.50.47 raw JSON contract drifted")
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError("V2.50.47 malformed JSON") from exc
    info = value.get("info") if isinstance(value, Mapping) else None
    releases = value.get("releases") if isinstance(value, Mapping) else None
    if not isinstance(info, Mapping) or not isinstance(releases, Mapping):
        raise ValueError("V2.50.47 PyPI schema absent")
    name = _safe_line(info.get("name"), SAFE_NAME, field="project name")
    if normalize_project(name) != expected:
        raise ValueError("V2.50.47 primary project identity mismatch")
    version = _safe_line(info.get("version"), VERSION, field="latest version")
    files = releases.get(version)
    dates = _release_dates(files)
    requires_raw = " ".join(str(info.get("requires_python") or "").split())
    requires_python = (
        _safe_line(requires_raw, PYTHON_SPEC, field="Requires-Python")
        if requires_raw
        else "Unknown"
    )
    return {
        "Package": name,
        "Latest version": version,
        "Latest release date (YYYY-MM-DD)": dates[0],
        "Requires-Python": requires_python,
    }


def render_record(record: Mapping[str, str]) -> str:
    expected = (
        "Package",
        "Latest version",
        "Latest release date (YYYY-MM-DD)",
        "Requires-Python",
    )
    if tuple(record) != expected:
        raise ValueError("V2.50.47 record field order drifted")
    values = [str(record[field]) for field in expected]
    if any(not value or any(character in value for character in "|\r\n\x00") for value in values):
        raise ValueError("V2.50.47 unsafe rendered record")
    return (
        "[IDENTITY-BOUND PYPI CURRENT-RELEASE RECORD]\n"
        f"Package: {values[0]}\n"
        f"Latest version: {values[1]}\n"
        f"Latest release date (YYYY-MM-DD): {values[2]}\n"
        f"Requires-Python: {values[3]}\n"
        "All four fields belong to the same exact PyPI project identity; the "
        "date is the earliest upload date under releases[info.version].\n"
        "[/IDENTITY-BOUND PYPI CURRENT-RELEASE RECORD]"
    )


def fixed_raw_prefix(raw_json: str, *, total_chars: int) -> str:
    if (
        isinstance(total_chars, bool)
        or not isinstance(total_chars, int)
        or not 1 <= total_chars <= MAX_EVIDENCE_CHARS
        or not isinstance(raw_json, str)
        or not raw_json
        or "\x00" in raw_json
    ):
        raise ValueError("V2.50.47 raw prefix contract drifted")
    return raw_json[:total_chars].ljust(total_chars)


def build_representations(
    raw_json: str,
    *,
    visible_project: str,
    total_chars: int,
) -> dict[str, Any]:
    """Return matched raw and compact-prefix evidence under one char cap."""

    control = fixed_raw_prefix(raw_json, total_chars=total_chars)
    record = parse_current_record(raw_json, visible_project=visible_project)
    compact = render_record(record)
    marker = "\n\n[RAW PYPI RESPONSE PREFIX]\n"
    if len(compact) + len(marker) > total_chars:
        raise ValueError("V2.50.47 compact record exceeds evidence budget")
    remaining = total_chars - len(compact) - len(marker)
    candidate = (compact + marker + raw_json[:remaining]).ljust(total_chars)
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "raw_response_characters": len(raw_json),
        "control_evidence_characters": len(control),
        "candidate_evidence_characters": len(candidate),
        "compact_record_characters": len(compact),
        "current_release_file_count": len(
            json.loads(raw_json)["releases"][record["Latest version"]]
        ),
        "bound_field_count": len(record),
        "unknown_bound_field_count": sum(value == "Unknown" for value in record.values()),
        "record_admitted": True,
        "primary_identity_bound_to_visible_project": True,
        "version_bound_to_info_version": True,
        "date_bound_to_releases_info_version": True,
        "requires_python_bound_to_same_info_record": True,
        "same_forward_raw_response_bytes_only": True,
        "control_and_candidate_character_budgets_equal": True,
        "candidate_contains_compact_record_then_same_raw_prefix": True,
        "provider_narrative_search_snippet_or_general_knowledge_used": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "contains_project_field_value_raw_page_url_prediction_answer_hash_or_credential": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "control_evidence": control,
        "candidate_evidence": candidate,
        "content_free_receipt": validate_receipt(receipt),
    }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "raw_response_characters",
        "control_evidence_characters",
        "candidate_evidence_characters",
        "compact_record_characters",
        "current_release_file_count",
        "bound_field_count",
        "unknown_bound_field_count",
    )
    true_flags = (
        "record_admitted",
        "primary_identity_bound_to_visible_project",
        "version_bound_to_info_version",
        "date_bound_to_releases_info_version",
        "requires_python_bound_to_same_info_record",
        "same_forward_raw_response_bytes_only",
        "control_and_candidate_character_budgets_equal",
        "candidate_contains_compact_record_then_same_raw_prefix",
    )
    false_flags = (
        "provider_narrative_search_snippet_or_general_knowledge_used",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "entropy_or_information_gain_assigns_credit_or_routes",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "contains_project_field_value_raw_page_url_prediction_answer_hash_or_credential",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version", "role", "policy_id", *counts, *true_flags,
        *false_flags, "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["raw_response_characters"] <= 0
        or copied["control_evidence_characters"]
        != copied["candidate_evidence_characters"]
        or not 1 <= copied["bound_field_count"] <= 4
        or copied["unknown_bound_field_count"] > copied["bound_field_count"]
        or copied["current_release_file_count"] <= 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.47 representation receipt drifted")
    return copied


__all__ = [
    "MAX_EVIDENCE_CHARS", "MAX_RAW_BYTES", "POLICY_ID", "ROLE",
    "build_representations", "fixed_raw_prefix", "parse_current_record",
    "normalize_project", "payload_sha256", "render_record", "validate_receipt",
]
