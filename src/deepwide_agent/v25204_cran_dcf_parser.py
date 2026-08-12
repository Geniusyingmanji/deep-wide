"""Total CRAN DCF parser with content-free staged failure observation.

The V2.52.03 evaluator used a stricter-than-DCF key grammar and collapsed every
exception into the same zero-row snapshot.  CRAN control fields commonly use
underscores (for example ``License_is_FOSS``), so a valid unrelated record
could invalidate the complete snapshot before the selected records were read.

This append-only parser accepts the field-name alphabet used by RFC-822-like R
DCF files, preserves exact visible values with continuation unfolding, rejects
duplicate keys and malformed continuations, and exposes only one finite failure
stage.  It has no filesystem, network, model, search, evaluator, or credit
capability.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25204_cran_dcf_parser_v1"
ROLE = "v25204_content_free_cran_dcf_parse_observation"
FAILURE_STAGES = (
    "decode",
    "orphan_continuation",
    "missing_separator",
    "invalid_field_name",
    "duplicate_field",
    "record_extraction",
)
FIELD_NAME = re.compile(r"[A-Za-z][A-Za-z0-9._-]*")


class DCFParseError(ValueError):
    def __init__(self, stage: str) -> None:
        if stage not in FAILURE_STAGES:
            raise ValueError("V2.52.04 unknown DCF failure stage")
        super().__init__("V2.52.04 CRAN DCF parse failed")
        self.stage = stage


def parse_records(value: bytes | str) -> list[dict[str, str]]:
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DCFParseError("decode") from exc
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError("V2.52.04 DCF input must be bytes or str")
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
                raise DCFParseError("orphan_continuation")
            current[last_key] = " ".join(
                (current[last_key] + " " + raw.strip()).split()
            )
            continue
        if ":" not in raw:
            raise DCFParseError("missing_separator")
        key, field_value = raw.split(":", 1)
        key = key.strip()
        if FIELD_NAME.fullmatch(key) is None:
            raise DCFParseError("invalid_field_name")
        if key in current:
            raise DCFParseError("duplicate_field")
        current[key] = field_value.strip()
        last_key = key
    if current:
        records.append(current)
    return records


def observation(*, stage: str | None, record_count: int) -> dict[str, Any]:
    if stage is not None and stage not in FAILURE_STAGES:
        raise ValueError("V2.52.04 observation stage drifted")
    if isinstance(record_count, bool) or not isinstance(record_count, int) or record_count < 0:
        raise ValueError("V2.52.04 observation record count drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parse_completed": stage is None,
        "failure_stage": stage,
        "record_count": record_count,
        "contains_field_name_value_package_question_prediction_url_gold_exception_message_traceback_or_credential": False,
        "mapping_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "network_model_search_fetch_evaluator_or_filesystem_effect": False,
    }
    value["observation_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("observation_payload_sha256", None)
    stage = copied.get("failure_stage")
    record_count = copied.get("record_count")
    false_flags = (
        "contains_field_name_value_package_question_prediction_url_gold_exception_message_traceback_or_credential",
        "mapping_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "network_model_search_fetch_evaluator_or_filesystem_effect",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "parse_completed",
            "failure_stage",
            "record_count",
            *false_flags,
            "observation_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or stage not in {None, *FAILURE_STAGES}
        or copied.get("parse_completed") is not (stage is None)
        or isinstance(record_count, bool)
        or not isinstance(record_count, int)
        or record_count < 0
        or stage is not None
        and record_count != 0
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.04 observation drifted")
    return copied


def parse_with_observation(value: bytes | str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    try:
        records = parse_records(value)
    except DCFParseError as exc:
        return [], observation(stage=exc.stage, record_count=0)
    return records, observation(stage=None, record_count=len(records))


__all__ = [
    "DCFParseError",
    "FAILURE_STAGES",
    "FIELD_NAME",
    "POLICY_ID",
    "ROLE",
    "observation",
    "parse_records",
    "parse_with_observation",
    "validate_observation",
]
