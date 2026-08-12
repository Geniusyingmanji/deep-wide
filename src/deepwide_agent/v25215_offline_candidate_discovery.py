"""Pure offline candidate discovery over four caller-supplied snapshots.

The module has no filesystem, process, environment, network, model, search,
evaluator, or credential capability.  Candidate identities are returned only
in memory.  The sealed observation contains snapshot and aggregate counts but
never an identity, item hash, record value, page, question, or prediction.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from html.parser import HTMLParser
from typing import Any


POLICY_ID = "v25215_offline_candidate_discovery_v1"
ROLE = "v25215_content_free_offline_candidate_discovery_observation"
STRATA = (
    "single_authority_exact_record",
    "single_authority_multivalue_record",
    "same_identity_multipage_record",
    "sparse_ambiguous_open_web_record",
)
MINIMUM_CANDIDATES = 64
MAXIMUM_SNAPSHOT_BYTES = 128 * 1024 * 1024
FAILURE_STAGES = (
    "snapshot_type_or_size",
    "decode",
    "json_parse",
    "schema",
    "dcf_parse",
    "html_parse",
)
_DCF_FIELD = re.compile(r"[A-Za-z][A-Za-z0-9._-]*")
_PEP503_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?$")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _snapshot(value: object) -> bytes:
    if (
        not isinstance(value, bytes)
        or not value
        or len(value) > MAXIMUM_SNAPSHOT_BYTES
    ):
        raise ValueError("snapshot_type_or_size")
    return value


def _text(value: bytes) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("decode") from exc


def _json(value: bytes) -> object:
    try:
        return json.loads(_text(value))
    except json.JSONDecodeError as exc:
        raise ValueError("json_parse") from exc


def _safe_identity(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = "-".join(value.casefold().split())
    return normalized if normalized and len(normalized) <= 100 else None


def _distinct(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _crates(value: bytes) -> tuple[list[str], int, int]:
    parsed = _json(value)
    if not isinstance(parsed, Mapping) or not isinstance(parsed.get("crates"), list):
        raise ValueError("schema")
    rows = parsed["crates"]
    selected: list[str] = []
    valid = 0
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        identity = _safe_identity(row.get("id") or row.get("name"))
        version = row.get("max_version")
        description = row.get("description")
        if (
            identity is not None
            and isinstance(version, str)
            and bool(version.strip())
            and isinstance(description, str)
            and bool(description.strip())
        ):
            valid += 1
            selected.append(identity)
    return _distinct(selected), len(rows), valid


def _dcf_records(value: bytes) -> list[dict[str, str]]:
    text = _text(value)
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    last_key: str | None = None
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw.strip():
            if current:
                records.append(current)
                current = {}
                last_key = None
            continue
        if raw[:1].isspace():
            if last_key is None:
                raise ValueError("dcf_parse")
            current[last_key] = " ".join(
                (current[last_key] + " " + raw.strip()).split()
            )
            continue
        if ":" not in raw:
            raise ValueError("dcf_parse")
        key, field_value = raw.split(":", 1)
        key = key.strip()
        if _DCF_FIELD.fullmatch(key) is None or key in current:
            raise ValueError("dcf_parse")
        current[key] = field_value.strip()
        last_key = key
    if current:
        records.append(current)
    return records


def _cran(value: bytes) -> tuple[list[str], int, int]:
    rows = _dcf_records(value)
    selected: list[str] = []
    valid = 0
    for row in rows:
        identity = _safe_identity(row.get("Package"))
        license_value = row.get("License")
        multivalue = row.get("SystemRequirements") or row.get("Suggests")
        if (
            identity is not None
            and isinstance(license_value, str)
            and bool(license_value.strip())
            and isinstance(multivalue, str)
            and bool(multivalue.strip())
        ):
            valid += 1
            selected.append(identity)
    return _distinct(selected), len(rows), valid


def _nonempty_string_or_first(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return bool(
        isinstance(value, list)
        and value
        and isinstance(value[0], str)
        and value[0].strip()
    )


def _crossref(value: bytes) -> tuple[list[str], int, int]:
    parsed = _json(value)
    if not isinstance(parsed, Mapping):
        raise ValueError("schema")
    message = parsed.get("message")
    if not isinstance(message, Mapping) or not isinstance(message.get("items"), list):
        raise ValueError("schema")
    rows = message["items"]
    selected: list[str] = []
    valid = 0
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        identity = _safe_identity(row.get("DOI"))
        if (
            identity is not None
            and _nonempty_string_or_first(row.get("title"))
            and _nonempty_string_or_first(row.get("publisher"))
            and _nonempty_string_or_first(row.get("container-title"))
        ):
            valid += 1
            selected.append(identity)
    return _distinct(selected), len(rows), valid


def _pep503(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


class _SimpleIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.casefold() != "a" or self._href is not None:
            return
        values = {name.casefold(): value for name, value in attrs}
        href = values.get("href")
        if isinstance(href, str) and href.strip():
            self._href = href.strip()
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text).strip()))
            self._href = None
            self._text = []


def _pypi(value: bytes) -> tuple[list[str], int, int]:
    parser = _SimpleIndexParser()
    try:
        parser.feed(_text(value))
        parser.close()
    except Exception as exc:
        raise ValueError("html_parse") from exc
    selected: list[str] = []
    valid = 0
    for href, anchor in parser.anchors:
        raw = anchor.strip()
        canonical = _pep503(raw)
        path = href.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        href_name = path.rsplit("/", 1)[-1]
        if (
            _PEP503_NAME.fullmatch(raw.casefold()) is not None
            and 3 <= len(canonical) <= 8
            and _pep503(href_name) == canonical
        ):
            valid += 1
            selected.append(canonical)
    return _distinct(selected), len(parser.anchors), valid


_PARSERS = {
    STRATA[0]: _crates,
    STRATA[1]: _cran,
    STRATA[2]: _crossref,
    STRATA[3]: _pypi,
}


def observation(
    *,
    stratum: str,
    snapshot_sha256: str,
    snapshot_byte_count: int,
    parsed_record_count: int,
    predicate_valid_record_count: int,
    distinct_candidate_count: int,
    failure_stage: str | None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "stratum": stratum,
        "snapshot_sha256": snapshot_sha256,
        "snapshot_byte_count": snapshot_byte_count,
        "parse_completed": failure_stage is None,
        "failure_stage": failure_stage,
        "parsed_record_count": parsed_record_count,
        "predicate_valid_record_count": predicate_valid_record_count,
        "distinct_candidate_count": distinct_candidate_count,
        "minimum_candidate_count": MINIMUM_CANDIDATES,
        "minimum_candidate_count_met": distinct_candidate_count >= MINIMUM_CANDIDATES,
        "contains_identity_item_hash_record_field_value_page_question_prediction_evidence_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect": False,
        "population_freeze_external_protocol_or_benchmark_authorized": False,
    }
    value["observation_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("observation_payload_sha256", None)
    counts = (
        "snapshot_byte_count",
        "parsed_record_count",
        "predicate_valid_record_count",
        "distinct_candidate_count",
        "minimum_candidate_count",
    )
    false_flags = (
        "contains_identity_item_hash_record_field_value_page_question_prediction_evidence_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect",
        "population_freeze_external_protocol_or_benchmark_authorized",
    )
    stage = copied.get("failure_stage")
    digest = copied.get("snapshot_sha256")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "stratum",
            "snapshot_sha256",
            "parse_completed",
            "failure_stage",
            *counts,
            "minimum_candidate_count_met",
            *false_flags,
            "observation_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("stratum") not in STRATA
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or stage not in {None, *FAILURE_STAGES}
        or copied.get("parse_completed") is not (stage is None)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied.get("minimum_candidate_count") != MINIMUM_CANDIDATES
        or copied.get("predicate_valid_record_count")
        < copied.get("distinct_candidate_count")
        or copied.get("minimum_candidate_count_met")
        is not (copied.get("distinct_candidate_count") >= MINIMUM_CANDIDATES)
        or stage is not None
        and any(copied[name] for name in counts if name != "minimum_candidate_count")
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.15 candidate discovery observation drifted")
    return copied


def discover_candidates(
    value: object, *, stratum: str
) -> tuple[list[str], dict[str, Any]]:
    if stratum not in _PARSERS:
        raise ValueError("V2.52.15 candidate stratum drifted")
    snapshot_bytes = value if isinstance(value, bytes) else b""
    digest = hashlib.sha256(snapshot_bytes).hexdigest()
    byte_count = len(snapshot_bytes)
    try:
        snapshot = _snapshot(value)
        candidates, parsed_count, valid_count = _PARSERS[stratum](snapshot)
    except ValueError as exc:
        stage = str(exc)
        if stage not in FAILURE_STAGES:
            stage = "schema"
        return [], observation(
            stratum=stratum,
            snapshot_sha256=digest,
            snapshot_byte_count=0,
            parsed_record_count=0,
            predicate_valid_record_count=0,
            distinct_candidate_count=0,
            failure_stage=stage,
        )
    return candidates, observation(
        stratum=stratum,
        snapshot_sha256=digest,
        snapshot_byte_count=byte_count,
        parsed_record_count=parsed_count,
        predicate_valid_record_count=valid_count,
        distinct_candidate_count=len(candidates),
        failure_stage=None,
    )


__all__ = [
    "FAILURE_STAGES",
    "MAXIMUM_SNAPSHOT_BYTES",
    "MINIMUM_CANDIDATES",
    "POLICY_ID",
    "ROLE",
    "STRATA",
    "discover_candidates",
    "observation",
    "validate_observation",
]
