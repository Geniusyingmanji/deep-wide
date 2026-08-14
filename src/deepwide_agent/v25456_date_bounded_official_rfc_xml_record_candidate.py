"""Date-bounded official RFC XML record candidate.

This successor preserves every V2.54.49 identity, URL, XML-root, RFC-series,
row, and field binding.  It changes only bounded front-matter extraction: if
the fetched prefix contains a complete ``date`` element but ends before the
literal ``</front>``, the parser closes a temporary front immediately after
that date.  XML parsing must then prove that the root, front, author sequence,
and date are all structurally complete.  Complete fronts remain accepted.

DOCTYPE and ENTITY inputs still fail closed.  The module performs no I/O or
provider action and grants no launch, truth access, evaluator access, or
signed credit.
"""

from __future__ import annotations

import re
import types
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from collections.abc import Callable
from typing import Any

from . import v25449_official_rfc_xml_record_candidate as parent


POLICY_ID = "v25456_date_bounded_official_rfc_xml_record_candidate_v1"
ROLE = "v25456_date_bounded_official_rfc_xml_record_candidate"
RECEIPT_ROLE = (
    "v25456_content_free_date_bounded_official_rfc_xml_record_candidate_receipt"
)
COLUMNS = parent.COLUMNS
RFC_EDITOR_HOST = parent.RFC_EDITOR_HOST
MAXIMUM_PAGES = parent.MAXIMUM_PAGES
MAXIMUM_XML_CHARACTERS = parent.MAXIMUM_XML_CHARACTERS
MAXIMUM_AUTHORS = parent.MAXIMUM_AUTHORS
payload_sha256 = parent.payload_sha256
request_vector_for_identities = parent.request_vector_for_identities
request_vector = parent.request_vector

_DATE = re.compile(r"<date\b[^>]*(?:/>|>.*?</date>)", re.DOTALL)


def _front_document(content: str) -> str | None:
    """Return a complete front or a structurally safe date-bounded closure."""

    upper = content.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        return None
    complete = parent._front_document(content)
    if complete is not None:
        return complete
    root = re.search(r"<rfc(?:\s|>)", content)
    if root is None:
        return None
    front = re.search(r"<front(?:\s|>)", content[root.start() :])
    if front is None:
        return None
    front_start = root.start() + front.start()
    date = _DATE.search(content, front_start)
    if date is None:
        return None
    prefix = content[root.start() : date.end()]
    if prefix.count("<front") != 1 or "</front>" in prefix:
        return None
    document = prefix + "</front></rfc>"
    try:
        parsed = ET.fromstring(document)
    except ET.ParseError:
        return None
    parsed_front = parsed.find("front")
    if (
        parsed.tag != "rfc"
        or parsed_front is None
        or parsed_front.find("date") is None
    ):
        return None
    return document


def _xml_cell(value: object) -> str | None:
    """Normalize XML typography, then apply the unchanged safe-cell gate."""

    normalized = " ".join(
        unicodedata.normalize("NFKC", str(value or "")).split()
    )
    return parent.parent._safe_cell(normalized)


def _author(author: ET.Element) -> str | None:
    """Use explicit RFC XML author attributes without prose inference."""

    initials = parent._text(author.attrib.get("initials"))
    surname = parent._text(author.attrib.get("surname"))
    if initials and surname:
        value = f"{initials} {surname}"
    else:
        value = parent._text(
            author.attrib.get("asciiFullname") or author.attrib.get("fullname")
        )
    if not value:
        return None
    if parent._text(author.attrib.get("role")).casefold() == "editor":
        value += ", Ed."
    return _xml_cell(value)


def parse_page(
    page: Mapping[str, Any], expected_number: int
) -> dict[str, str] | None:
    """Parse one bound RFC XML front, including a safe date-bounded prefix."""

    if (
        not isinstance(page, Mapping)
        or parent._url_number(page.get("url")) != expected_number
    ):
        return None
    content = page.get("content")
    if (
        not isinstance(content, str)
        or not content
        or len(content) > MAXIMUM_XML_CHARACTERS
    ):
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
        root_number = int(parent._text(root.attrib.get("number")))
    except ValueError:
        return None
    front = root.find("front")
    if root_number != expected_number or front is None:
        return None
    rfc_series = [
        node
        for node in front.findall("seriesInfo")
        if parent._text(node.attrib.get("name")).upper() == "RFC"
    ]
    if len(rfc_series) != 1:
        return None
    try:
        series_number = int(
            parent._text(rfc_series[0].attrib.get("value"))
        )
    except ValueError:
        return None
    stream_key = parent._text(
        rfc_series[0].attrib.get("stream") or root.attrib.get("submissionType")
    ).casefold()
    stream = parent.STREAMS.get(stream_key)
    title_node = front.find("title")
    date = front.find("date")
    title = _xml_cell(
        "".join(title_node.itertext()) if title_node is not None else ""
    )
    authors = [_author(node) for node in front.findall("author")]
    month = parent._text(date.attrib.get("month")) if date is not None else ""
    if month.isdigit():
        month = f"{int(month):02d}"
    published = _xml_cell(
        f"{parent.MONTHS.get(month, '')} "
        f"{parent._text(date.attrib.get('year')) if date is not None else ''}"
        .strip()
    )
    status = parent._status(root, front)
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
    author_text = _xml_cell("; ".join(str(value) for value in authors))
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


def _clone(function: Callable[..., Any], namespace: dict[str, Any]) -> Callable[..., Any]:
    cloned = types.FunctionType(
        function.__code__,
        namespace,
        name=function.__name__.replace("v25449", "v25456"),
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    cloned.__kwdefaults__ = dict(function.__kwdefaults__ or {})
    cloned.__annotations__ = dict(function.__annotations__)
    cloned.__doc__ = function.__doc__
    return cloned


_NAMESPACE = dict(parent.__dict__)
_NAMESPACE.update(
    {
        "POLICY_ID": POLICY_ID,
        "ROLE": ROLE,
        "RECEIPT_ROLE": RECEIPT_ROLE,
        "COLUMNS": COLUMNS,
        "RFC_EDITOR_HOST": RFC_EDITOR_HOST,
        "MAXIMUM_PAGES": MAXIMUM_PAGES,
        "MAXIMUM_XML_CHARACTERS": MAXIMUM_XML_CHARACTERS,
        "MAXIMUM_AUTHORS": MAXIMUM_AUTHORS,
        "_front_document": _front_document,
        "_author": _author,
        "parse_page": parse_page,
        "payload_sha256": payload_sha256,
    }
)

for _name in (
    "validate_receipt",
    "validate_candidate",
    "build_candidate_for_identities",
    "build_candidate",
):
    _NAMESPACE[_name] = _clone(getattr(parent, _name), _NAMESPACE)

validate_receipt = _NAMESPACE["validate_receipt"]
validate_candidate = _NAMESPACE["validate_candidate"]
build_candidate_for_identities = _NAMESPACE["build_candidate_for_identities"]
build_candidate = _NAMESPACE["build_candidate"]


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "exact_official_url_template": (
            f"https://{RFC_EDITOR_HOST}/rfc/rfcNNNN.xml"
        ),
        "one_official_xml_front_matter_per_visible_row": True,
        "complete_front_supported": True,
        "date_bounded_temporary_front_closure_supported": True,
        "date_must_be_complete_before_temporary_closure": True,
        "temporary_closure_must_parse_as_rfc_front_with_date": True,
        "url_xml_root_series_and_base_row_identity_all_bound": True,
        "category_to_status_uses_fixed_rfc_xml_schema_only": True,
        "workgroup_source_or_draft_prefix_to_stream_inference": False,
        "network_model_search_fetch_file_environment_or_process_accessed": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "COLUMNS",
    "MAXIMUM_AUTHORS",
    "MAXIMUM_PAGES",
    "MAXIMUM_XML_CHARACTERS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "RFC_EDITOR_HOST",
    "ROLE",
    "build_candidate",
    "build_candidate_for_identities",
    "integration_contract",
    "parse_page",
    "payload_sha256",
    "request_vector",
    "request_vector_for_identities",
    "validate_candidate",
    "validate_receipt",
]
