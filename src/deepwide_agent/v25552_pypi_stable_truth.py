"""Pure post-freeze PyPI stable-release truth totality.

An exact, identity-bound PyPI JSON response can validly establish either one
latest stable release date or that the project currently has no stable
release.  The latter is a real ``Unknown`` answer, not evaluator failure.

This module is evaluator-only and pure.  It performs no file, environment,
process, network, model, search, fetch, benchmark, or credential access.  It
must never enter a forward dependency closure.  Entropy/information gain
assigns no signed credit and this build authorizes no execution.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from packaging.version import InvalidVersion, Version


POLICY_ID = "v25552_pypi_stable_truth_totality_v1"
ROLE = "v25552_pypi_stable_truth_record"
UNKNOWN = "Unknown"


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def normalize_project(value: object) -> str:
    text = str(value or "").strip()
    if not text or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", text) is None:
        raise ValueError("V2.55.52 PyPI project identity malformed")
    return re.sub(r"[-_.]+", "-", text).casefold()


def _utc_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("V2.55.52 upload timestamp missing")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("V2.55.52 upload timestamp malformed") from exc
    if parsed.tzinfo is None:
        raise ValueError("V2.55.52 upload timestamp timezone missing")
    return parsed.astimezone(timezone.utc).date().isoformat()


def render_date(value: str) -> str:
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("V2.55.52 release date malformed") from exc
    return f"{parsed.year}年{parsed.month}月{parsed.day}日"


def parse_response(raw: bytes, identity: str) -> dict[str, Any]:
    """Parse an exact PyPI response into a stable date or valid Unknown."""

    expected = normalize_project(identity)
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("V2.55.52 PyPI response empty")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.55.52 PyPI JSON malformed") from exc
    info = value.get("info") if isinstance(value, dict) else None
    releases = value.get("releases") if isinstance(value, dict) else None
    if not isinstance(info, Mapping) or not isinstance(releases, Mapping):
        raise ValueError("V2.55.52 PyPI schema malformed")
    if normalize_project(info.get("name")) != expected:
        raise ValueError("V2.55.52 PyPI identity mismatch")

    candidates: list[tuple[Version, str, Sequence[Any]]] = []
    parseable_file_versions = 0
    invalid_file_versions: list[str] = []
    for raw_version, files in releases.items():
        if not isinstance(raw_version, str):
            raise ValueError("V2.55.52 PyPI version key malformed")
        if not isinstance(files, Sequence) or isinstance(files, (str, bytes)):
            raise ValueError("V2.55.52 PyPI release vector malformed")
        if not files:
            continue
        try:
            version = Version(raw_version)
        except InvalidVersion:
            invalid_file_versions.append(raw_version)
            continue
        parseable_file_versions += 1
        if not version.is_prerelease and not version.is_devrelease:
            candidates.append((version, raw_version, files))

    if invalid_file_versions:
        raise ValueError("V2.55.52 nonempty invalid release version is ambiguous")
    if parseable_file_versions == 0:
        raise ValueError("V2.55.52 no file-bearing parseable release exists")

    if not candidates:
        record: dict[str, Any] = {
            "artifact_version": 1,
            "role": ROLE,
            "policy_id": POLICY_ID,
            "identity": identity,
            "availability": "no_stable_release",
            "latest_stable_version": None,
            "release_file_count": 0,
            "release_date_iso": None,
            "canonical_value": UNKNOWN,
            "sort_key": None,
            "official_identity_bound_response_valid": True,
            "no_stable_release_is_valid_unknown": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
        record["record_payload_sha256"] = payload_sha256(record)
        return validate_record(record)

    latest = max(version for version, _raw, _files in candidates)
    selected = [row for row in candidates if row[0] == latest]
    if len(selected) != 1:
        raise ValueError("V2.55.52 equal latest stable version aliases conflict")
    _version, raw_version, files = selected[0]
    dates: list[str] = []
    for file_row in files:
        if not isinstance(file_row, Mapping):
            raise ValueError("V2.55.52 release file malformed")
        dates.append(
            _utc_date(
                file_row.get("upload_time_iso_8601")
                or file_row.get("upload_time")
            )
        )
    if not dates:
        raise ValueError("V2.55.52 latest stable file vector empty")
    release_date = min(dates)
    record = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "identity": identity,
        "availability": "stable_release",
        "latest_stable_version": raw_version,
        "release_file_count": len(files),
        "release_date_iso": release_date,
        "canonical_value": render_date(release_date),
        "sort_key": release_date,
        "official_identity_bound_response_valid": True,
        "no_stable_release_is_valid_unknown": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    record["record_payload_sha256"] = payload_sha256(record)
    return validate_record(record)


def validate_record(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("record_payload_sha256", None)
    availability = copied.get("availability")
    common = (
        copied.get("artifact_version") == 1
        and copied.get("role") == ROLE
        and copied.get("policy_id") == POLICY_ID
        and isinstance(copied.get("identity"), str)
        and bool(normalize_project(copied.get("identity")))
        and copied.get("official_identity_bound_response_valid") is True
        and copied.get("no_stable_release_is_valid_unknown") is True
        and copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read"
        )
        is False
        and copied.get("entropy_or_information_gain_assigns_signed_credit") is False
        and seal == payload_sha256(unsigned)
    )
    stable = (
        availability == "stable_release"
        and isinstance(copied.get("latest_stable_version"), str)
        and isinstance(copied.get("release_file_count"), int)
        and not isinstance(copied.get("release_file_count"), bool)
        and copied["release_file_count"] > 0
        and isinstance(copied.get("release_date_iso"), str)
        and copied.get("sort_key") == copied.get("release_date_iso")
        and copied.get("canonical_value") == render_date(copied["release_date_iso"])
    )
    unknown = (
        availability == "no_stable_release"
        and copied.get("latest_stable_version") is None
        and copied.get("release_file_count") == 0
        and copied.get("release_date_iso") is None
        and copied.get("canonical_value") == UNKNOWN
        and copied.get("sort_key") is None
    )
    if not common or not (stable or unknown):
        raise ValueError("V2.55.52 truth record drifted")
    return copied


def ordered_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Known dates descend; Unknown rows stay after them in supplied order."""

    if isinstance(records, (str, bytes)):
        raise ValueError("V2.55.52 record vector malformed")
    checked = [validate_record(record) for record in records]
    if len({record["identity"] for record in checked}) != len(checked):
        raise ValueError("V2.55.52 duplicate truth identity")
    indexed = list(enumerate(checked))
    known = sorted(
        [item for item in indexed if item[1]["availability"] == "stable_release"],
        key=lambda item: item[1]["sort_key"],
        reverse=True,
    )
    unknown = [
        item for item in indexed if item[1]["availability"] == "no_stable_release"
    ]
    ordered = known + unknown
    return [copy.deepcopy(record) for _index, record in ordered]


__all__ = [
    "POLICY_ID",
    "ROLE",
    "UNKNOWN",
    "normalize_project",
    "ordered_records",
    "parse_response",
    "payload_sha256",
    "render_date",
    "validate_record",
]
