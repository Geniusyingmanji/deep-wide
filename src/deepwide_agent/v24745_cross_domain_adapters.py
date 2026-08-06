"""Pure label-blind ROR/Crossref/OpenAlex adapters for V2.47.43 binding.

The runtime receives exactly one visible ``{opaque_id, question}`` task and an
exact URL-to-bytes response mapping supplied by its caller.  It has no file,
environment, process, network, model, search, benchmark-label, gold, evaluator,
reward, or score capability.  Parsed records are always passed through the
generic V2.47.43 binder; adapters never mutate a table directly.
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote, urlencode

from . import v24743_generic_record_binding as binder


POLICY_ID = "v24745_cross_domain_structured_adapters_v1"
ROLE = "v24745_cross_domain_adapter_task_result"
RECEIPT_ROLE = "v24745_cross_domain_adapter_content_free_receipt"
UNKNOWN = "Unknown"
ROR_HOST = "api.ror.org"
CROSSREF_HOST = "api.crossref.org"
OPENALEX_HOST = "api.openalex.org"
MAX_RESPONSE_BYTES = 2_000_000
ROR_COLUMNS = ("Organization", "ROR ID", "Country code")
DOI_COLUMNS = ("DOI", "Title", "Year")
_OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
_ROR_ID = re.compile(r"0[0-9a-z]{8}")
_ISO2 = re.compile(r"[A-Z]{2}")
_DOI = re.compile(r"10\.[0-9]{4,9}/\S{1,240}", flags=re.IGNORECASE)
_TAG = re.compile(r"<[^<>]{1,200}>")
MODES = frozenset(
    {
        "ror_official_exact",
        "crossref_official_exact",
        "crossref_openalex_ordinary",
    }
)
FAILURE_TYPES = frozenset(
    {
        "ror_identity_or_schema_invalid",
        "crossref_identity_or_schema_invalid",
        "openalex_identity_or_schema_invalid",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "mode",
        "identity_count",
        "expected_response_count",
        "validated_record_count",
        "failure_type_counts",
        "prediction_changed",
        "fully_admitted_row_count",
        "binding_receipt",
        "task_question_identity_response_or_prediction_content_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
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


def _canonical(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _safe_visible(value: object) -> str:
    text = _canonical(value)
    if (
        not text
        or len(text) > 512
        or any(character in text for character in "\r\n|\0")
    ):
        raise ValueError("V2.47.45 unsafe visible text")
    return text


def _metadata_text(value: object) -> str:
    text = _canonical(html.unescape(str(value or "")))
    if _TAG.search(text) is not None or any(character in text for character in "<>|"):
        raise ValueError("V2.47.45 metadata text is not plain structured text")
    return _safe_visible(text)


def _canonical_doi(value: object) -> str:
    text = _canonical(value)
    if text.casefold().startswith("https://doi.org/"):
        text = text[len("https://doi.org/") :]
    if (
        _DOI.fullmatch(text) is None
        or any(character in text for character in "\r\n|\0?#")
    ):
        raise ValueError("V2.47.45 DOI drifted")
    return text.casefold()


def ror_url(entity: str) -> str:
    target = _safe_visible(entity)
    if any(character in target for character in '"\\'):
        raise ValueError("V2.47.45 ROR target drifted")
    query = urlencode(
        (("query.advanced", f'names.value:"{target}"'), ("filter", "status:active"))
    )
    return f"https://{ROR_HOST}/v2/organizations?{query}"


def crossref_url(doi: str) -> str:
    target = _canonical_doi(doi)
    return f"https://{CROSSREF_HOST}/works/{quote(target, safe='')}"


def openalex_url(doi: str) -> str:
    target = _canonical_doi(doi)
    identifier = quote(f"https://doi.org/{target}", safe=":/")
    return f"https://{OPENALEX_HOST}/works/{identifier}"


def _visible_task(task: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(task, Mapping) or set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.47.45 runtime task keys drifted")
    opaque_id = task.get("opaque_id")
    question = task.get("question")
    if (
        not isinstance(opaque_id, str)
        or _OPAQUE_ID.fullmatch(opaque_id) is None
        or not isinstance(question, str)
        or not question
    ):
        raise ValueError("V2.47.45 visible task drifted")
    return {"opaque_id": opaque_id, "question": question}


def _numbered_block(question: str, tag: str) -> list[str]:
    match = re.search(
        rf"<{tag}>\n(?P<body>.*?)\n</{tag}>", question, flags=re.DOTALL
    )
    if match is None:
        raise ValueError("V2.47.45 visible identity block absent")
    values = []
    for position, line in enumerate(match.group("body").splitlines(), 1):
        prefix = f"{position}. "
        if not line.startswith(prefix):
            raise ValueError("V2.47.45 visible identity order drifted")
        values.append(_safe_visible(line[len(prefix) :]))
    if not values or len(values) > 32 or len(set(values)) != len(values):
        raise ValueError("V2.47.45 visible identity vector drifted")
    return values


def visible_contract(task: Mapping[str, Any]) -> dict[str, Any]:
    visible = _visible_task(task)
    question = visible["question"]
    if (
        "<ENTITIES>" in question
        and "The column names are: Organization, ROR ID, Country code." in question
        and "Use the 9-character ROR suffix" in question
    ):
        identities = _numbered_block(question, "ENTITIES")
        mode = "ror_official_exact"
        columns = ROR_COLUMNS
    elif (
        "<DOIS>" in question
        and "The column names are: DOI, Title, Year." in question
    ):
        identities = _numbered_block(question, "DOIS")
        if any(_canonical_doi(value) != value.casefold() for value in identities):
            raise ValueError("V2.47.45 visible DOI is not canonical")
        if "Use the exact-address Crossref registry record." in question:
            mode = "crossref_official_exact"
        elif (
            "Require the same value from the Crossref and OpenAlex structured records."
            in question
        ):
            mode = "crossref_openalex_ordinary"
        else:
            raise ValueError("V2.47.45 visible DOI evidence policy absent")
        columns = DOI_COLUMNS
    else:
        raise ValueError("V2.47.45 visible schema is unsupported")
    return {
        "opaque_id": visible["opaque_id"],
        "question": question,
        "mode": mode,
        "columns": columns,
        "identities": identities,
    }


def request_urls(task: Mapping[str, Any]) -> tuple[str, ...]:
    contract = visible_contract(task)
    identities = contract["identities"]
    if contract["mode"] == "ror_official_exact":
        return tuple(ror_url(value) for value in identities)
    if contract["mode"] == "crossref_official_exact":
        return tuple(crossref_url(value) for value in identities)
    return tuple(
        url
        for value in identities
        for url in (crossref_url(value), openalex_url(value))
    )


def _decode_json(raw: bytes) -> Mapping[str, Any]:
    def reject(value: str) -> None:
        raise ValueError(f"V2.47.45 invalid numeric constant: {value}")

    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise ValueError("V2.47.45 response size drifted")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=reject,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, InvalidOperation) as exc:
        raise ValueError("V2.47.45 response JSON drifted") from exc
    if not isinstance(value, Mapping):
        raise ValueError("V2.47.45 response envelope drifted")
    return value


def _integer(value: object) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, Decimal))
        or Decimal(value) != Decimal(value).to_integral_value()
    ):
        return None
    return int(value)


def _ror_display_names(record: Mapping[str, Any]) -> set[str]:
    names = record.get("names")
    if not isinstance(names, Sequence) or isinstance(names, (str, bytes)):
        return set()
    output = set()
    for item in names:
        if not isinstance(item, Mapping):
            continue
        types = item.get("types")
        if (
            isinstance(types, Sequence)
            and not isinstance(types, (str, bytes))
            and "ror_display" in {str(value).casefold() for value in types}
        ):
            try:
                output.add(_safe_visible(item.get("value")))
            except ValueError:
                continue
    return output


def _ror_country_codes(record: Mapping[str, Any]) -> set[str]:
    locations = record.get("locations")
    if not isinstance(locations, Sequence) or isinstance(locations, (str, bytes)):
        return set()
    output = set()
    for location in locations:
        if not isinstance(location, Mapping):
            continue
        details = location.get("geonames_details")
        code = details.get("country_code") if isinstance(details, Mapping) else None
        if isinstance(code, str) and _ISO2.fullmatch(code):
            output.add(code)
    return output


def parse_ror_record(raw: bytes, *, entity: str, record_id: str) -> dict[str, Any]:
    target = _safe_visible(entity)
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
        raise ValueError("V2.47.45 ROR result completeness drifted")
    matches: dict[str, str] = {}
    for item in items:
        if not isinstance(item, Mapping) or item.get("status") != "active":
            continue
        raw_id = str(item.get("id", ""))
        suffix = raw_id[len("https://ror.org/") :] if raw_id.startswith("https://ror.org/") else ""
        countries = _ror_country_codes(item)
        if (
            _ROR_ID.fullmatch(suffix)
            and _ror_display_names(item) == {target}
            and len(countries) == 1
        ):
            matches[suffix] = next(iter(countries))
    if len(matches) != 1:
        raise ValueError("V2.47.45 ROR identity is absent or ambiguous")
    suffix, country = next(iter(matches.items()))
    return binder.build_record(
        record_id=record_id,
        source_host=ROR_HOST,
        source_url=ror_url(target),
        authority="official_exact_record",
        exact_address_and_primary_identity_bound=True,
        primary_identity=target,
        fields=[
            {"label": "ROR ID", "value": suffix},
            {"label": "Country code", "value": country},
        ],
    )


def _crossref_year(message: Mapping[str, Any]) -> str:
    published = message.get("published")
    parts = published.get("date-parts") if isinstance(published, Mapping) else None
    if (
        not isinstance(parts, Sequence)
        or isinstance(parts, (str, bytes))
        or len(parts) != 1
        or not isinstance(parts[0], Sequence)
        or isinstance(parts[0], (str, bytes))
        or not parts[0]
    ):
        raise ValueError("V2.47.45 Crossref publication date drifted")
    year = _integer(parts[0][0])
    if year is None or not 1000 <= year <= 2100:
        raise ValueError("V2.47.45 Crossref year drifted")
    return str(year)


def parse_crossref_record(
    raw: bytes, *, doi: str, record_id: str, official: bool
) -> dict[str, Any]:
    target = _canonical_doi(doi)
    value = _decode_json(raw)
    message = value.get("message")
    if (
        value.get("status") != "ok"
        or value.get("message-type") != "work"
        or not isinstance(message, Mapping)
        or _canonical_doi(message.get("DOI")) != target
    ):
        raise ValueError("V2.47.45 Crossref identity drifted")
    titles = message.get("title")
    if (
        not isinstance(titles, Sequence)
        or isinstance(titles, (str, bytes))
        or len(titles) != 1
    ):
        raise ValueError("V2.47.45 Crossref title drifted")
    return binder.build_record(
        record_id=record_id,
        source_host=CROSSREF_HOST,
        source_url=crossref_url(target),
        authority=("official_exact_record" if official else "ordinary_structured_page"),
        exact_address_and_primary_identity_bound=official,
        primary_identity=doi,
        fields=[
            {"label": "Title", "value": _metadata_text(titles[0])},
            {"label": "Year", "value": _crossref_year(message)},
        ],
    )


def parse_openalex_record(raw: bytes, *, doi: str, record_id: str) -> dict[str, Any]:
    target = _canonical_doi(doi)
    value = _decode_json(raw)
    if _canonical_doi(value.get("doi")) != target:
        raise ValueError("V2.47.45 OpenAlex identity drifted")
    year = _integer(value.get("publication_year"))
    if year is None or not 1000 <= year <= 2100:
        raise ValueError("V2.47.45 OpenAlex year drifted")
    return binder.build_record(
        record_id=record_id,
        source_host=OPENALEX_HOST,
        source_url=openalex_url(target),
        authority="ordinary_structured_page",
        exact_address_and_primary_identity_bound=False,
        primary_identity=doi,
        fields=[
            {"label": "Title", "value": _metadata_text(value.get("title"))},
            {"label": "Year", "value": str(year)},
        ],
    )


def _render_unknown(columns: Sequence[str], identities: Sequence[str]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join(
            "| " + " | ".join((identity, UNKNOWN, UNKNOWN)) + " |"
            for identity in identities
        )
        + "\n```"
    )


def _full_rows(candidate: str) -> int:
    lines = [line.strip() for line in candidate.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        raise ValueError("V2.47.45 candidate table drifted")
    count = 0
    for line in lines[2:]:
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if len(cells) != 3:
            raise ValueError("V2.47.45 candidate row drifted")
        count += int(all(not binder._is_unknown(value) for value in cells[1:]))
    return count


def _build_task_result(
    task: Mapping[str, Any], responses: Mapping[str, bytes]
) -> dict[str, Any]:
    contract = visible_contract(task)
    expected = request_urls(task)
    if (
        not isinstance(responses, Mapping)
        or set(responses) != set(expected)
        or len(responses) != len(expected)
        or any(not isinstance(value, bytes) for value in responses.values())
    ):
        raise ValueError("V2.47.45 response address vector drifted")
    baseline = _render_unknown(contract["columns"], contract["identities"])
    records = []
    failures: Counter[str] = Counter()
    ordinal = 0
    for identity in contract["identities"]:
        if contract["mode"] == "ror_official_exact":
            ordinal += 1
            try:
                records.append(
                    parse_ror_record(
                        responses[ror_url(identity)],
                        entity=identity,
                        record_id=f"S{ordinal:04d}",
                    )
                )
            except (TypeError, ValueError):
                failures["ror_identity_or_schema_invalid"] += 1
        else:
            ordinal += 1
            try:
                records.append(
                    parse_crossref_record(
                        responses[crossref_url(identity)],
                        doi=identity,
                        record_id=f"S{ordinal:04d}",
                        official=contract["mode"] == "crossref_official_exact",
                    )
                )
            except (TypeError, ValueError):
                failures["crossref_identity_or_schema_invalid"] += 1
            if contract["mode"] == "crossref_openalex_ordinary":
                ordinal += 1
                try:
                    records.append(
                        parse_openalex_record(
                            responses[openalex_url(identity)],
                            doi=identity,
                            record_id=f"S{ordinal:04d}",
                        )
                    )
                except (TypeError, ValueError):
                    failures["openalex_identity_or_schema_invalid"] += 1

    binding = binder.bind_records(baseline, records)
    candidate = binding["candidate"]
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "mode": contract["mode"],
        "identity_count": len(contract["identities"]),
        "expected_response_count": len(expected),
        "validated_record_count": len(records),
        "failure_type_counts": dict(sorted(failures.items())),
        "prediction_changed": candidate != baseline,
        "fully_admitted_row_count": _full_rows(candidate),
        "binding_receipt": binding["receipt"],
        "task_question_identity_response_or_prediction_content_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    result = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": contract["opaque_id"],
        "mode": contract["mode"],
        "baseline": baseline,
        "candidate": candidate,
        "baseline_sha256": hashlib.sha256(baseline.encode()).hexdigest(),
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "receipt": receipt,
    }
    result["result_payload_sha256"] = payload_sha256(result)
    return validate_result(result)


def run_task(
    task: Mapping[str, Any], responses: Mapping[str, bytes]
) -> dict[str, Any]:
    result = _build_task_result(task, responses)
    return validate_result(result, task=task, responses=responses)


def validate_result(
    value: Mapping[str, Any],
    *,
    task: Mapping[str, Any] | None = None,
    responses: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    receipt = copied.get("receipt")
    baseline = copied.get("baseline")
    candidate = copied.get("candidate")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "mode",
            "baseline",
            "candidate",
            "baseline_sha256",
            "candidate_sha256",
            "receipt",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(baseline, str)
        or not isinstance(candidate, str)
        or copied.get("baseline_sha256") != hashlib.sha256(baseline.encode()).hexdigest()
        or copied.get("candidate_sha256") != hashlib.sha256(candidate.encode()).hexdigest()
        or not isinstance(receipt, Mapping)
        or set(receipt) != RECEIPT_KEYS
        or receipt.get("artifact_version") != 1
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("mode") not in MODES
        or receipt.get("mode") != copied.get("mode")
        or isinstance(receipt.get("identity_count"), bool)
        or not isinstance(receipt.get("identity_count"), int)
        or not 1 <= receipt.get("identity_count") <= 32
        or isinstance(receipt.get("expected_response_count"), bool)
        or not isinstance(receipt.get("expected_response_count"), int)
        or receipt.get("expected_response_count")
        != receipt.get("identity_count")
        * (2 if receipt.get("mode") == "crossref_openalex_ordinary" else 1)
        or isinstance(receipt.get("validated_record_count"), bool)
        or not isinstance(receipt.get("validated_record_count"), int)
        or not 0
        <= receipt.get("validated_record_count")
        <= receipt.get("expected_response_count")
        or not isinstance(receipt.get("failure_type_counts"), Mapping)
        or any(
            key not in FAILURE_TYPES
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
            for key, amount in receipt.get("failure_type_counts", {}).items()
        )
        or receipt.get("validated_record_count")
        + sum(receipt.get("failure_type_counts", {}).values())
        != receipt.get("expected_response_count")
        or not isinstance(receipt.get("prediction_changed"), bool)
        or receipt.get("prediction_changed") is not (candidate != baseline)
        or isinstance(receipt.get("fully_admitted_row_count"), bool)
        or not isinstance(receipt.get("fully_admitted_row_count"), int)
        or not 0
        <= receipt.get("fully_admitted_row_count")
        <= receipt.get("identity_count")
        or receipt.get("fully_admitted_row_count") != _full_rows(candidate)
        or receipt.get(
            "task_question_identity_response_or_prediction_content_persisted"
        )
        is not False
        or receipt.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or receipt.get(
            "file_environment_network_model_search_fetch_or_process_accessed"
        )
        is not False
        or receipt.get("benchmark_launch_or_evaluator_authorized") is not False
        or receipt.get("receipt_payload_sha256")
        != payload_sha256(
            {key: item for key, item in receipt.items() if key != "receipt_payload_sha256"}
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.45 adapter result drifted")
    binding_receipt = binder.validate_receipt(receipt.get("binding_receipt", {}))
    if (
        binding_receipt.get("record_count")
        != receipt.get("validated_record_count")
        or binding_receipt.get("table_row_count") != receipt.get("identity_count")
        or binding_receipt.get("table_value_cell_count")
        != receipt.get("identity_count") * 2
        or binding_receipt.get("changed_cell_count")
        != sum(
            before != after
            for before, after in zip(
                binder._table_matrix(baseline)[1],
                binder._table_matrix(candidate)[1],
            )
            for before, after in zip(before[1:], after[1:])
        )
    ):
        raise ValueError("V2.47.45 binding receipt/result drifted")
    if task is not None or responses is not None:
        if task is None or responses is None:
            raise ValueError("V2.47.45 replay inputs are incomplete")
        replay = _build_task_result(task, responses)
        if replay != copied:
            raise ValueError("V2.47.45 adapter replay drifted")
    return copied


__all__ = [
    "CROSSREF_HOST",
    "MAX_RESPONSE_BYTES",
    "OPENALEX_HOST",
    "POLICY_ID",
    "ROR_HOST",
    "crossref_url",
    "openalex_url",
    "parse_crossref_record",
    "parse_openalex_record",
    "parse_ror_record",
    "request_urls",
    "ror_url",
    "run_task",
    "validate_result",
    "visible_contract",
]
