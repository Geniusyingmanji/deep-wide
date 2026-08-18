"""Pure post-freeze PyPI latest-stable-version truth.

An exact identity-bound PyPI JSON response establishes the canonical project
name and either the highest file-bearing PEP 440 release that is neither a
pre-release nor a development release, or valid ``Unknown`` when all
file-bearing parseable releases are pre/dev releases.  A nonempty invalid
version or equal-version alias conflict remains ambiguous and fails closed.

This evaluator-only module is pure.  It performs no file, environment,
process, network, model, search, fetch, benchmark, credential, or forward
effect.  Entropy/information gain assigns no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from packaging.version import InvalidVersion, Version


POLICY_ID = "v25580_pypi_stable_version_truth_v1"
ROLE = "v25580_pypi_stable_version_truth_record"
UNKNOWN = "Unknown"


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def normalize_project(value: object) -> str:
    text = str(value or "").strip()
    if (
        not text
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", text) is None
    ):
        raise ValueError("V2.55.80 PyPI project identity malformed")
    return re.sub(r"[-_.]+", "-", text).casefold()


def semantic_version(value: object) -> Version | None:
    text = " ".join(str(value or "").split())
    if not text or text.casefold() == UNKNOWN.casefold():
        return None
    try:
        parsed = Version(text)
    except InvalidVersion:
        return None
    if parsed.is_prerelease or parsed.is_devrelease:
        return None
    return parsed


def parse_response(raw: bytes, identity: str) -> dict[str, Any]:
    """Parse one exact PyPI response without performing any external effect."""

    expected = normalize_project(identity)
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("V2.55.80 PyPI response empty")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.55.80 PyPI JSON malformed") from exc
    info = value.get("info") if isinstance(value, dict) else None
    releases = value.get("releases") if isinstance(value, dict) else None
    if not isinstance(info, Mapping) or not isinstance(releases, Mapping):
        raise ValueError("V2.55.80 PyPI schema malformed")
    canonical_name = str(info.get("name") or "").strip()
    if normalize_project(canonical_name) != expected:
        raise ValueError("V2.55.80 PyPI identity mismatch")

    candidates: list[tuple[Version, str, Sequence[Any]]] = []
    parseable_file_versions = 0
    invalid_file_versions: list[str] = []
    for raw_version, files in releases.items():
        if not isinstance(raw_version, str):
            raise ValueError("V2.55.80 PyPI version key malformed")
        if not isinstance(files, Sequence) or isinstance(files, (str, bytes)):
            raise ValueError("V2.55.80 PyPI release vector malformed")
        if not files:
            continue
        if any(not isinstance(file_row, Mapping) for file_row in files):
            raise ValueError("V2.55.80 PyPI release file malformed")
        try:
            parsed = Version(raw_version)
        except InvalidVersion:
            invalid_file_versions.append(raw_version)
            continue
        parseable_file_versions += 1
        if not parsed.is_prerelease and not parsed.is_devrelease:
            candidates.append((parsed, raw_version, files))

    if invalid_file_versions:
        raise ValueError("V2.55.80 nonempty invalid release version is ambiguous")
    if parseable_file_versions == 0:
        raise ValueError("V2.55.80 no file-bearing parseable release exists")

    if not candidates:
        record: dict[str, Any] = {
            "artifact_version": 1,
            "role": ROLE,
            "policy_id": POLICY_ID,
            "identity": identity,
            "canonical_project_name": canonical_name,
            "availability": "no_stable_release",
            "latest_stable_version": None,
            "normalized_latest_stable_version": None,
            "release_file_count": 0,
            "canonical_value": UNKNOWN,
            "official_identity_bound_response_valid": True,
            "no_stable_release_is_valid_unknown": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
        record["record_payload_sha256"] = payload_sha256(record)
        return validate_record(record)

    latest = max(parsed for parsed, _raw, _files in candidates)
    selected = [row for row in candidates if row[0] == latest]
    if len(selected) != 1:
        raise ValueError("V2.55.80 equal latest stable version aliases conflict")
    parsed, raw_version, files = selected[0]
    record = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "identity": identity,
        "canonical_project_name": canonical_name,
        "availability": "stable_release",
        "latest_stable_version": raw_version,
        "normalized_latest_stable_version": str(parsed),
        "release_file_count": len(files),
        "canonical_value": raw_version,
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
        and normalize_project(copied.get("identity"))
        == normalize_project(copied.get("canonical_project_name"))
        and copied.get("official_identity_bound_response_valid") is True
        and copied.get("no_stable_release_is_valid_unknown") is True
        and copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read"
        )
        is False
        and copied.get("entropy_or_information_gain_assigns_signed_credit")
        is False
        and seal == payload_sha256(unsigned)
    )
    stable = (
        availability == "stable_release"
        and isinstance(copied.get("latest_stable_version"), str)
        and semantic_version(copied.get("latest_stable_version")) is not None
        and copied.get("normalized_latest_stable_version")
        == str(semantic_version(copied.get("latest_stable_version")))
        and isinstance(copied.get("release_file_count"), int)
        and not isinstance(copied.get("release_file_count"), bool)
        and copied["release_file_count"] > 0
        and copied.get("canonical_value") == copied.get("latest_stable_version")
    )
    unknown = (
        availability == "no_stable_release"
        and copied.get("latest_stable_version") is None
        and copied.get("normalized_latest_stable_version") is None
        and copied.get("release_file_count") == 0
        and copied.get("canonical_value") == UNKNOWN
    )
    if not common or not (stable or unknown):
        raise ValueError("V2.55.80 truth record drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "ROLE",
    "UNKNOWN",
    "normalize_project",
    "parse_response",
    "payload_sha256",
    "semantic_version",
    "validate_record",
]
