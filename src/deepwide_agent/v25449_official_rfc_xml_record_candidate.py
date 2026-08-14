"""Pure official RFC XML record candidate for visible RFC memberships.

The primitive consumes only a canonical base table, the visible question,
and same-forward fetched public pages supplied by its caller.  A page is
eligible only when its URL is the exact RFC Editor ``rfcNNNN.xml`` endpoint
for one member of the strict visible membership vector.  Its XML root,
front-matter RFC series identity, and URL must all bind to the same row.

One bounded front matter yields Title, Authors, Status, Stream, and Published.
Status follows the RFC XML schema: ``category`` is the publication class;
an RFC carrying a front-matter ``STD`` series is Internet Standard and one
carrying ``BCP`` is Best Current Practice.  No page prose, workgroup name,
draft prefix, benchmark label, evaluator, or truth surface participates.

This module performs no file, environment, process, network, model, search,
fetch, benchmark, or evaluator action.  Entropy/information gain remains
observational and assigns no signed credit.  It grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v25395_visible_membership_synthesis_runtime as membership
from . import v25432_source_authoritative_field_candidate as parent


POLICY_ID = "v25449_official_rfc_xml_record_candidate_v1"
ROLE = "v25449_official_rfc_xml_record_candidate"
RECEIPT_ROLE = "v25449_content_free_official_rfc_xml_record_candidate_receipt"
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
RFC_EDITOR_HOST = "www.rfc-editor.org"
MAXIMUM_PAGES = 4
MAXIMUM_XML_CHARACTERS = 500_000
MAXIMUM_AUTHORS = 64
MONTHS = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}
STATUS_BY_CATEGORY = {
    "std": "PROPOSED STANDARD",
    "bcp": "BEST CURRENT PRACTICE",
    "info": "INFORMATIONAL",
    "exp": "EXPERIMENTAL",
    "historic": "HISTORIC",
}
STREAMS = {
    "ietf": "IETF",
    "iab": "IAB",
    "irtf": "IRTF",
    "independent": "INDEPENDENT",
    "legacy": "LEGACY",
}
_RFC = re.compile(r"(?i)RFC\s*0*([0-9]{1,5})")
_URL_PATH = re.compile(r"/rfc/rfc([0-9]{1,5})\.xml")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _visible_numbers(question: str) -> tuple[int, ...]:
    values, _source = membership.visible_membership(str(question))
    output: list[int] = []
    for value in values:
        match = _RFC.fullmatch(_text(value))
        if match is None:
            return ()
        output.append(int(match.group(1)))
    return tuple(output) if len(output) == MAXIMUM_PAGES and len(set(output)) == len(output) else ()


def request_vector(question: str) -> list[dict[str, str]]:
    """Return four deterministic official URLs from strict visible membership."""

    numbers = _visible_numbers(question)
    if not numbers:
        return []
    return [
        {
            "url": f"https://{RFC_EDITOR_HOST}/rfc/rfc{number}.xml",
            "query": f"RFC {number}",
            "title": f"RFC {number}",
            "member_label": f"RFC {number}",
        }
        for number in numbers
    ]


def _url_number(value: object) -> int | None:
    try:
        parsed = urlsplit(str(value or ""))
        port = parsed.port
    except ValueError:
        return None
    match = _URL_PATH.fullmatch(parsed.path)
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold().strip(".") != RFC_EDITOR_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
        or match is None
    ):
        return None
    return int(match.group(1))


def _author(author: ET.Element) -> str | None:
    initials = _text(author.attrib.get("initials"))
    surname = _text(author.attrib.get("surname"))
    if not initials or not surname:
        return None
    value = f"{initials} {surname}"
    if _text(author.attrib.get("role")).casefold() == "editor":
        value += ", Ed."
    return parent._safe_cell(value)


def _status(root: ET.Element, front: ET.Element) -> str | None:
    category = _text(root.attrib.get("category")).casefold()
    series = {
        _text(node.attrib.get("name")).upper()
        for node in front.findall("seriesInfo")
        if _text(node.attrib.get("name"))
    }
    if "STD" in series:
        return "INTERNET STANDARD"
    if "BCP" in series:
        return "BEST CURRENT PRACTICE"
    return STATUS_BY_CATEGORY.get(category)


def _front_document(content: str) -> str | None:
    """Close one complete prefix-contained front element for bounded parsing."""

    if "<!DOCTYPE" in content.upper() or "<!ENTITY" in content.upper():
        return None
    root_match = re.search(r"<rfc(?:\s|>)", content)
    if root_match is None:
        return None
    front_end = content.find("</front>", root_match.start())
    if front_end < 0:
        return None
    prefix = content[root_match.start() : front_end + len("</front>")]
    if prefix.count("<front") != 1 or prefix.count("</front>") != 1:
        return None
    return prefix + "</rfc>"


def parse_page(page: Mapping[str, Any], expected_number: int) -> dict[str, str] | None:
    """Parse one exact RFC XML front matter or fail closed."""

    if not isinstance(page, Mapping) or _url_number(page.get("url")) != expected_number:
        return None
    content = page.get("content")
    if not isinstance(content, str) or not content or len(content) > MAXIMUM_XML_CHARACTERS:
        return None
    document = _front_document(content)
    if document is None:
        return None
    try:
        root = ET.fromstring(document)
    except ET.ParseError:
        return None
    if root.tag != "rfc" or set(root.attrib).isdisjoint({"number"}):
        return None
    try:
        root_number = int(_text(root.attrib.get("number")))
    except ValueError:
        return None
    front = root.find("front")
    if root_number != expected_number or front is None:
        return None
    rfc_series = [
        node
        for node in front.findall("seriesInfo")
        if _text(node.attrib.get("name")).upper() == "RFC"
    ]
    if len(rfc_series) != 1:
        return None
    try:
        series_number = int(_text(rfc_series[0].attrib.get("value")))
    except ValueError:
        return None
    stream_key = _text(
        rfc_series[0].attrib.get("stream") or root.attrib.get("submissionType")
    ).casefold()
    stream = STREAMS.get(stream_key)
    title_node = front.find("title")
    date = front.find("date")
    title = parent._safe_cell(
        "".join(title_node.itertext()) if title_node is not None else ""
    )
    authors = [_author(node) for node in front.findall("author")]
    month = _text(date.attrib.get("month")) if date is not None else ""
    if month.isdigit():
        month = f"{int(month):02d}"
    published = parent._safe_cell(
        f"{MONTHS.get(month, '')} {_text(date.attrib.get('year')) if date is not None else ''}".strip()
    )
    status = _status(root, front)
    if (
        series_number != expected_number
        or title is None
        or not authors
        or len(authors) > MAXIMUM_AUTHORS
        or any(value is None for value in authors)
        or status is None
        or stream is None
        or published is None
    ):
        return None
    author_text = parent._safe_cell("; ".join(str(value) for value in authors))
    if author_text is None:
        return None
    return {
        "RFC": f"RFC {expected_number}",
        "Title": title,
        "Authors": author_text,
        "Status": status,
        "Stream": stream,
        "Published": published,
    }


def _pages(values: Sequence[Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    output: dict[int, Mapping[str, Any]] = {}
    for page in values:
        number = _url_number(page.get("url")) if isinstance(page, Mapping) else None
        if number is None or number in output:
            continue
        output[number] = page
    return output


def build_candidate(
    base_prediction: str,
    *,
    question: str,
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    numbers = _visible_numbers(question)
    required, rows = parent._canonical_table(base_prediction, COLUMNS)
    base_keys = tuple(parent._key(row[0]) for row in rows)
    expected_keys = tuple(parent._key(f"RFC {number}") for number in numbers)
    available = _pages(pages)
    counts: Counter[str] = Counter()
    records: dict[int, dict[str, str]] = {}
    if numbers and base_keys == expected_keys and len(rows) == len(numbers):
        for number in numbers:
            page = available.get(number)
            if page is None:
                counts["missing_page_count"] += 1
                continue
            record = parse_page(page, number)
            if record is None:
                counts["invalid_page_count"] += 1
                continue
            records[number] = record
            counts["valid_record_count"] += 1
    else:
        counts["invalid_visible_or_base_binding_count"] += 1

    edited = copy.deepcopy(rows)
    applied = 0
    for index, number in enumerate(numbers if base_keys == expected_keys else ()):
        record = records.get(number)
        if record is None:
            continue
        for column_index, column in enumerate(required[1:], 1):
            value = record[column]
            if parent._key(edited[index][column_index]) == parent._key(value):
                counts["unchanged_coordinate_count"] += 1
                continue
            edited[index][column_index] = value
            counts[f"applied_{column}_count"] += 1
            applied += 1
    candidate = parent.table_parent._render_table(required, edited)
    changed = candidate != str(base_prediction)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_prediction": str(base_prediction),
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode("utf-8")
        ).hexdigest(),
        "candidate_prediction": candidate,
        "candidate_prediction_sha256": hashlib.sha256(
            candidate.encode("utf-8")
        ).hexdigest(),
        "visible_identity_count": len(numbers),
        "requested_page_count": len(request_vector(question)),
        "provided_page_count": len(pages),
        "valid_record_count": counts["valid_record_count"],
        "missing_page_count": counts["missing_page_count"],
        "invalid_page_count": counts["invalid_page_count"],
        "invalid_visible_or_base_binding_count": counts[
            "invalid_visible_or_base_binding_count"
        ],
        "applied_coordinate_count": applied,
        "unchanged_coordinate_count": counts["unchanged_coordinate_count"],
        "applied_field_counts": {
            column: counts[f"applied_{column}_count"] for column in COLUMNS[1:]
        },
        "candidate_prediction_changed": changed,
        "all_values_come_from_same_identity_official_xml_front_matter": True,
        "category_to_status_uses_fixed_rfc_xml_schema_only": True,
        "workgroup_source_or_draft_prefix_to_stream_inference": False,
        "partial_fetch_or_parse_failure_preserves_corresponding_base_row": True,
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "network_model_search_fetch_file_environment_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt = {
        key: copy.deepcopy(value[key])
        for key in (
            "visible_identity_count",
            "requested_page_count",
            "provided_page_count",
            "valid_record_count",
            "missing_page_count",
            "invalid_page_count",
            "invalid_visible_or_base_binding_count",
            "applied_coordinate_count",
            "unchanged_coordinate_count",
            "applied_field_counts",
            "candidate_prediction_changed",
            "positive_signed_credit_count",
        )
    }
    receipt.update(
        {
            "artifact_version": 1,
            "role": RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "all_values_come_from_same_identity_official_xml_front_matter": True,
            "category_to_status_uses_fixed_rfc_xml_schema_only": True,
            "workgroup_source_or_draft_prefix_to_stream_inference": False,
            "partial_fetch_or_parse_failure_preserves_corresponding_base_row": True,
            "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "network_model_search_fetch_file_environment_or_process_accessed": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
    )
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    value["content_free_receipt"] = validate_receipt(receipt)
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_candidate(value, question=question, pages=pages, replay=False)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "visible_identity_count",
        "requested_page_count",
        "provided_page_count",
        "valid_record_count",
        "missing_page_count",
        "invalid_page_count",
        "invalid_visible_or_base_binding_count",
        "applied_coordinate_count",
        "unchanged_coordinate_count",
        "positive_signed_credit_count",
    )
    false_flags = (
        "workgroup_source_or_draft_prefix_to_stream_inference",
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "network_model_search_fetch_file_environment_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["visible_identity_count"] not in {0, MAXIMUM_PAGES}
        or copied["requested_page_count"] not in {0, MAXIMUM_PAGES}
        or copied["valid_record_count"] > MAXIMUM_PAGES
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(copied.get("applied_field_counts"), Mapping)
        or set(copied["applied_field_counts"]) != set(COLUMNS[1:])
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in copied["applied_field_counts"].values()
        )
        or sum(copied["applied_field_counts"].values())
        != copied["applied_coordinate_count"]
        or copied.get("candidate_prediction_changed")
        is not (copied["applied_coordinate_count"] > 0)
        or copied.get(
            "all_values_come_from_same_identity_official_xml_front_matter"
        )
        is not True
        or copied.get("category_to_status_uses_fixed_rfc_xml_schema_only")
        is not True
        or copied.get("partial_fetch_or_parse_failure_preserves_corresponding_base_row")
        is not True
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.49 content-free receipt drifted")
    return copied


def validate_candidate(
    value: Mapping[str, Any],
    *,
    question: str,
    pages: Sequence[Mapping[str, Any]],
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    base = copied.get("base_prediction")
    candidate = copied.get("candidate_prediction")
    receipt = copied.get("content_free_receipt")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(base, str)
        or not isinstance(candidate, str)
        or copied.get("base_prediction_sha256")
        != hashlib.sha256(base.encode("utf-8")).hexdigest()
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or copied.get("candidate_prediction_changed") is not (base != candidate)
        or copied.get("positive_signed_credit_count") != 0
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.49 candidate artifact drifted")
    for name in receipt:
        if (
            name not in {"role", "receipt_payload_sha256"}
            and name in copied
            and copied[name] != receipt[name]
        ):
            raise ValueError("V2.54.49 receipt/result drifted")
    if replay and copied != build_candidate(base, question=question, pages=pages):
        raise ValueError("V2.54.49 candidate replay drifted")
    return copied


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "runtime_inputs": ["visible_question", "canonical_base_table", "same_forward_official_xml_pages"],
        "maximum_deterministic_official_xml_requests": MAXIMUM_PAGES,
        "exact_official_url_template": f"https://{RFC_EDITOR_HOST}/rfc/rfcNNNN.xml",
        "one_official_xml_front_matter_per_visible_row": True,
        "category_to_status_uses_fixed_rfc_xml_schema_only": True,
        "workgroup_source_or_draft_prefix_to_stream_inference": False,
        "network_model_search_fetch_file_environment_or_process_accessed": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "COLUMNS",
    "MAXIMUM_PAGES",
    "POLICY_ID",
    "RFC_EDITOR_HOST",
    "ROLE",
    "build_candidate",
    "integration_contract",
    "parse_page",
    "request_vector",
    "validate_candidate",
    "validate_receipt",
]
