"""Visible-only deterministic reachability across ROR and World Bank.

The runtime receives exactly one visible ``{opaque_id, question}`` task plus
caller-supplied public response bytes.  It has no file, process, network,
credential, benchmark-label, gold, evaluator, reward, or score capability.
The baseline is a schema-complete Unknown table.  Candidate cells change only
after an exact request address, complete response schema, primary identity,
and target value bind successfully.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from . import v24724_fresh_indicator_transport as worldbank
from .v24644_primary_identity_pair_runtime import normalized_identity
from .v24648_unknown_target_structured_runtime import exact_lookup_url
from .v24733_dual_namespace_contract import (
    WORLD_BANK_TARGETS,
    parse_worldbank_visible_contract,
    visible_namespace,
)


POLICY_ID = "v24735_dual_namespace_deterministic_reachability_v1"
ROLE = "v24735_dual_namespace_reachability_task_result"
RECEIPT_ROLE = "v24735_dual_namespace_reachability_content_free_receipt"
ARMS = ("baseline", "candidate")
ROR_COLUMNS = ("Organization", "ROR ID", "Country code")
UNKNOWN = "Unknown"
MAX_ROR_RESPONSE_BYTES = 2_000_000
_ROR_SUFFIX = re.compile(r"0[0-9a-z]{8}")
_ISO2 = re.compile(r"[A-Z]{2}")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _render(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    if not columns or any("|" in str(value) for row in rows for value in row):
        raise ValueError("V2.47.35 render input drifted")
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def _visible_task(task: Mapping[str, Any]) -> dict[str, str]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.47.35 runtime task keys drifted")
    opaque_id = task.get("opaque_id")
    question = task.get("question")
    if (
        not isinstance(opaque_id, str)
        or re.fullmatch(r"task_[0-9a-f]{24}", opaque_id) is None
        or not isinstance(question, str)
        or not question
    ):
        raise ValueError("V2.47.35 visible task drifted")
    visible_namespace(question)
    return {"opaque_id": opaque_id, "question": question}


def ror_entities(question: str) -> list[str]:
    if visible_namespace(question) != "ror":
        raise ValueError("V2.47.35 expected visible ROR task")
    match = re.search(r"<ENTITIES>\n(.*?)\n</ENTITIES>", question, flags=re.DOTALL)
    if match is None:
        raise ValueError("V2.47.35 visible ROR envelope drifted")
    output = []
    for expected, line in enumerate(match.group(1).splitlines(), 1):
        prefix = f"{expected}. "
        if not line.startswith(prefix):
            raise ValueError("V2.47.35 visible ROR order drifted")
        output.append(line[len(prefix) :].strip())
    if len(output) != 4 or len(set(output)) != 4 or any(not item for item in output):
        raise ValueError("V2.47.35 visible ROR vector drifted")
    return output


def request_urls(task: Mapping[str, Any]) -> tuple[str, ...]:
    visible = _visible_task(task)
    namespace = visible_namespace(visible["question"])
    if namespace == "ror":
        return tuple(exact_lookup_url(entity) for entity in ror_entities(visible["question"]))
    contract = parse_worldbank_visible_contract(visible["question"])
    if contract["targets"] != list(WORLD_BANK_TARGETS):
        raise ValueError("V2.47.35 World Bank target vector drifted")
    urls = tuple(
        worldbank.endpoint_url(target, worldbank.PRIMARY_REPRESENTATION)
        for target in worldbank.TARGETS
    )
    return urls


def _decode_json(raw: bytes) -> Mapping[str, Any]:
    def reject(value: str) -> None:
        raise ValueError(f"V2.47.35 invalid constant: {value}")

    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ROR_RESPONSE_BYTES:
        raise ValueError("V2.47.35 ROR response size drifted")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=reject,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, InvalidOperation) as exc:
        raise ValueError("V2.47.35 invalid ROR response") from exc
    if not isinstance(value, Mapping):
        raise ValueError("V2.47.35 ROR response envelope drifted")
    return value


def _integer(value: object) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, Decimal))
        or Decimal(value) != Decimal(value).to_integral_value()
    ):
        return None
    return int(value)


def _record_suffix(record: Mapping[str, Any]) -> str | None:
    value = str(record.get("id", ""))
    prefix = "https://ror.org/"
    suffix = value[len(prefix) :] if value.startswith(prefix) else ""
    return suffix if _ROR_SUFFIX.fullmatch(suffix) else None


def _display_names(record: Mapping[str, Any]) -> set[str]:
    values = set()
    names = record.get("names")
    if not isinstance(names, Sequence) or isinstance(names, (str, bytes)):
        return values
    for item in names:
        if not isinstance(item, Mapping):
            continue
        types = item.get("types")
        if (
            isinstance(types, Sequence)
            and not isinstance(types, (str, bytes))
            and "ror_display" in {str(value).casefold() for value in types}
        ):
            name = normalized_identity(item.get("value"))
            if name:
                values.add(name)
    return values


def _country_codes(record: Mapping[str, Any]) -> set[str]:
    output = set()
    locations = record.get("locations")
    if not isinstance(locations, Sequence) or isinstance(locations, (str, bytes)):
        return output
    for location in locations:
        if not isinstance(location, Mapping):
            continue
        details = location.get("geonames_details")
        code = details.get("country_code") if isinstance(details, Mapping) else None
        if isinstance(code, str) and _ISO2.fullmatch(code):
            output.add(code)
    return output


def parse_ror_exact_response(raw: bytes, *, entity: str) -> dict[str, Any]:
    target = str(entity).strip()
    if exact_lookup_url(target) != exact_lookup_url(entity):
        raise ValueError("V2.47.35 ROR target drifted")
    value = _decode_json(raw)
    items = value.get("items")
    count = _integer(value.get("number_of_results"))
    if (
        count is None
        or count < 0
        or not isinstance(items, Sequence)
        or isinstance(items, (str, bytes))
        or count != len(items)
    ):
        raise ValueError("V2.47.35 ROR result completeness drifted")
    expected = normalized_identity(target)
    matches = {}
    for item in items:
        if not isinstance(item, Mapping) or item.get("status") != "active":
            continue
        suffix = _record_suffix(item)
        countries = _country_codes(item)
        if (
            suffix is not None
            and _display_names(item) == {expected}
            and len(countries) == 1
        ):
            matches[suffix] = next(iter(countries))
    if len(matches) != 1:
        raise ValueError("V2.47.35 ROR exact identity is absent or ambiguous")
    suffix, country = next(iter(matches.items()))
    return {
        "ror_id": suffix,
        "country_code": country,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "response_item_count": count,
        "primary_identity_bound": True,
        "target_value_bound": True,
    }


def _unknown_prediction(task: Mapping[str, Any]) -> str:
    visible = _visible_task(task)
    namespace = visible_namespace(visible["question"])
    if namespace == "ror":
        return _render(
            ROR_COLUMNS,
            [[entity, UNKNOWN, UNKNOWN] for entity in ror_entities(visible["question"])],
        )
    contract = parse_worldbank_visible_contract(visible["question"])
    return _render(
        contract["columns"],
        [
            [country["name"], UNKNOWN, UNKNOWN]
            for country in contract["countries"]
        ],
    )


def _ror_candidate(
    task: Mapping[str, Any], responses: Mapping[str, bytes]
) -> tuple[str, dict[str, Any]]:
    entities = ror_entities(str(task["question"]))
    expected = tuple(exact_lookup_url(entity) for entity in entities)
    if set(responses) != set(expected) or len(responses) != len(expected):
        raise ValueError("V2.47.35 ROR response address vector drifted")
    rows = []
    valid = 0
    failure_counts: dict[str, int] = {}
    for entity, url in zip(entities, expected, strict=True):
        try:
            record = parse_ror_exact_response(responses[url], entity=entity)
        except (TypeError, ValueError):
            rows.append([entity, UNKNOWN, UNKNOWN])
            failure_counts["identity_or_schema_invalid"] = (
                failure_counts.get("identity_or_schema_invalid", 0) + 1
            )
            continue
        rows.append([entity, record["ror_id"], record["country_code"]])
        valid += 1
    return _render(ROR_COLUMNS, rows), {
        "expected_request_count": len(expected),
        "response_count": len(responses),
        "schema_valid_response_count": valid,
        "primary_identity_bound_target_count": valid,
        "target_value_bound_cell_count": valid * 2,
        "admitted_cell_count": valid * 2,
        "failure_type_counts": failure_counts,
        "bulk_bundle_complete": False,
    }


def _worldbank_candidate(
    task: Mapping[str, Any], responses: Mapping[str, bytes]
) -> tuple[str, dict[str, Any]]:
    contract = parse_worldbank_visible_contract(str(task["question"]))
    expected = tuple(
        worldbank.endpoint_url(target, worldbank.PRIMARY_REPRESENTATION)
        for target in worldbank.TARGETS
    )
    if set(responses) != set(expected) or len(responses) != len(expected):
        raise ValueError("V2.47.35 World Bank response address vector drifted")
    vectors = []
    valid_responses = 0
    failure_counts: dict[str, int] = {}
    for target, url in zip(worldbank.TARGETS, expected, strict=True):
        try:
            records, _updated = worldbank.parse_records(
                responses[url],
                target=target,
                representation=worldbank.PRIMARY_REPRESENTATION,
            )
        except (TypeError, ValueError):
            failure_counts["bundle_schema_invalid"] = (
                failure_counts.get("bundle_schema_invalid", 0) + 1
            )
            vectors.append(None)
            continue
        vectors.append(records)
        valid_responses += 1
    complete = valid_responses == len(expected)
    rows = []
    identity_bound = 0
    value_bound = 0
    for country in contract["countries"]:
        values = []
        country_complete = complete
        for records in vectors:
            value = (
                records.get(country["iso3"])
                if complete and records is not None
                else None
            )
            if value is None:
                country_complete = False
                values.append(UNKNOWN)
            else:
                normalized = value.normalize()
                values.append("0" if normalized == 0 else format(normalized, "f"))
                value_bound += 1
        identity_bound += int(country_complete)
        rows.append([country["name"], *values])
    return _render(contract["columns"], rows), {
        "expected_request_count": len(expected),
        "response_count": len(responses),
        "schema_valid_response_count": valid_responses,
        "primary_identity_bound_target_count": identity_bound,
        "target_value_bound_cell_count": value_bound,
        "admitted_cell_count": value_bound,
        "failure_type_counts": failure_counts,
        "bulk_bundle_complete": complete,
    }


def _changed_cells(namespace: str, baseline: str, candidate: str) -> int:
    del namespace
    if baseline == candidate:
        return 0
    table_lines = [
        line.strip()
        for line in candidate.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(table_lines) < 3:
        raise ValueError("V2.47.35 candidate table drifted")
    return sum(
        value != UNKNOWN
        for line in table_lines[2:]
        for value in [cell.strip() for cell in line.strip("|").split("|")][1:]
    )


def run_task(
    task: Mapping[str, Any], responses: Mapping[str, bytes]
) -> dict[str, Any]:
    visible = _visible_task(task)
    namespace = visible_namespace(visible["question"])
    baseline = _unknown_prediction(visible)
    if not isinstance(responses, Mapping) or any(
        not isinstance(url, str) or not isinstance(raw, bytes)
        for url, raw in responses.items()
    ):
        raise ValueError("V2.47.35 response mapping drifted")
    if namespace == "ror":
        candidate, counts = _ror_candidate(visible, responses)
    else:
        candidate, counts = _worldbank_candidate(visible, responses)
    changed = _changed_cells(namespace, baseline, candidate)
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "namespace": namespace,
        **counts,
        "changed_cell_count": changed,
        "prediction_changed": candidate != baseline,
        "identity_and_value_gated": True,
        "response_content_persisted_in_public_aggregate": False,
        "positive_entropy_or_task_credit_assigned": False,
        "question_prediction_response_identity_value_or_credential_emitted": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "namespace": namespace,
        "predictions": {"baseline": baseline, "candidate": candidate},
        "prediction_sha256": {
            "baseline": hashlib.sha256(baseline.encode()).hexdigest(),
            "candidate": hashlib.sha256(candidate.encode()).hexdigest(),
        },
        "receipt": receipt,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "expected_request_count",
        "response_count",
        "schema_valid_response_count",
        "primary_identity_bound_target_count",
        "target_value_bound_cell_count",
        "admitted_cell_count",
        "changed_cell_count",
    )
    namespace = copied.get("namespace")
    expected = 4 if namespace == "ror" else 2
    if (
        copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or namespace not in {"ror", "worldbank"}
        or copied.get("expected_request_count") != expected
        or copied.get("response_count") != expected
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied.get(name, -1) < 0
            for name in counts
        )
        or copied.get("admitted_cell_count")
        != copied.get("target_value_bound_cell_count")
        or copied.get("changed_cell_count") > copied.get("admitted_cell_count")
        or copied.get("prediction_changed")
        is not (copied.get("changed_cell_count", 0) > 0)
        or copied.get("identity_and_value_gated") is not True
        or copied.get("response_content_persisted_in_public_aggregate") is not False
        or copied.get("positive_entropy_or_task_credit_assigned") is not False
        or copied.get(
            "question_prediction_response_identity_value_or_credential_emitted"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or not isinstance(copied.get("failure_type_counts"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.35 reachability receipt drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    receipt = validate_receipt(copied.get("receipt", {}))
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("namespace") != receipt["namespace"]
        or not isinstance(copied.get("opaque_id"), str)
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or receipt["prediction_changed"]
        is not (predictions["baseline"] != predictions["candidate"])
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.35 reachability result drifted")
    return copied


__all__ = [
    "ARMS",
    "MAX_ROR_RESPONSE_BYTES",
    "POLICY_ID",
    "ROLE",
    "parse_ror_exact_response",
    "request_urls",
    "ror_entities",
    "run_task",
    "validate_receipt",
    "validate_result",
]
