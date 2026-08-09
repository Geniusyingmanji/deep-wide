"""Pure compact-field extraction from noisy exact authority page bytes.

V2.49.73 accidentally compared a compact record against an already projected
raw control.  This successor keeps the control as a fixed prefix of the exact
public response while deriving the candidate record from the complete shared
response.  It has no network, model, evaluator, filesystem, or process access.
"""

from __future__ import annotations

import copy
import html
import json
import re
from collections.abc import Mapping, Sequence
from urllib.parse import unquote

from . import v24972_identity_bound_compact_fields as parent
from .clients import canonicalize_url
from .v24967_requirement_aware_source_allocation import normalize_repository


POLICY_ID = "v24974_raw_authority_identity_bound_compact_fields_v1"
ROLE = "v24974_raw_authority_identity_bound_compact_fields_result"
PROJECTION_RECEIPT_ROLE = "v24974_raw_authority_projection_receipt"
MAX_RAW_PAGES = 2
MAX_RAW_PAGE_CHARS = 8_000_000
MAX_PROJECTION_CHARS = 8_000
LATEST_SECTION_CHARS = 120_000
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
RELATIVE_TIME = re.compile(
    r"<relative-time\b[^>]*\bdatetime=[\"'](\d{4}-\d{2}-\d{2})[^\"']*[\"']",
    re.IGNORECASE,
)


def _raw_text(page: Mapping[str, object]) -> str:
    value = page.get("text")
    if value is None:
        value = page.get("raw_content")
    text = str(value or "")
    if not text or len(text) > MAX_RAW_PAGE_CHARS or "\0" in text:
        raise ValueError("V2.49.74 raw authority page is empty or oversized")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _pypi_projection(text: str, project: str) -> str:
    value = json.loads(text)
    info = value.get("info") if isinstance(value, dict) else None
    if not isinstance(info, dict):
        raise ValueError("V2.49.74 PyPI info object is absent")
    # Reuse the hardened identity and field validator before projecting.
    parsed = parent._pypi_json(text, project)
    projected = {
        "info": {
            "name": info.get("name"),
            "version": parsed["pypi_latest_version"],
            "requires_python": parsed.get("requires_python"),
        }
    }
    return json.dumps(projected, ensure_ascii=False, sort_keys=True)


def _github_projection(text: str, repository: str) -> str:
    owner, repo = normalize_repository(repository)
    identity = f"{owner}/{repo}"
    title_match = TITLE.search(text)
    title = html.unescape(" ".join((title_match.group(1) if title_match else "").split()))
    if title.casefold() != f"releases · {identity} · github".casefold():
        raise ValueError("V2.49.74 GitHub HTML title identity mismatch")

    escaped = re.escape(identity)
    release = re.compile(
        rf"href=[\"']/{escaped}/releases/tag/([^\"'?#]+)[\"'][^>]*>.*?</a>"
        rf".{{0,4000}}?href=[\"']/{escaped}/releases/latest[\"']",
        re.IGNORECASE | re.DOTALL,
    )
    candidates: set[tuple[str, str]] = set()
    for matched in release.finditer(text):
        tag = unquote(html.unescape(matched.group(1)))
        section_end = text.find("</section>", matched.end())
        if section_end < 0 or section_end - matched.end() > LATEST_SECTION_CHARS:
            section_end = min(len(text), matched.end() + LATEST_SECTION_CHARS)
        date_match = RELATIVE_TIME.search(text, matched.end(), section_end)
        if date_match is None:
            continue
        safe_tag = parent._safe_line(tag, parent.TAG)
        released = parent._valid_date(date_match.group(1))
        candidates.add((safe_tag, released))
    if len(candidates) != 1:
        raise ValueError("V2.49.74 GitHub latest release is absent or ambiguous")
    tag, released = next(iter(candidates))
    return (
        f"Releases · {identity} · GitHub\n"
        f"Releases: {identity}\n"
        f"{tag} {released}\nLatest\n"
    )


def project_exact_pages(
    pages: Sequence[Mapping[str, object]], *, project: str, repository: str
) -> tuple[list[dict[str, str]], dict[str, object]]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.49.74 raw page vector is invalid")
    if len(pages) != MAX_RAW_PAGES:
        raise ValueError("V2.49.74 requires exactly two authority pages")

    projected: list[dict[str, str]] = []
    raw_chars = 0
    kinds: list[str] = []
    for page in pages:
        if not isinstance(page, Mapping):
            raise ValueError("V2.49.74 raw page is not a mapping")
        url = canonicalize_url(str(page.get("url") or ""))
        kind = parent.authority_kind(url, project=project, repository=repository)
        if kind not in {"pypi_json", "github_html"} or kind in kinds:
            raise ValueError("V2.49.74 authority kind or cardinality drifted")
        raw = _raw_text(page)
        projection = (
            _pypi_projection(raw, project)
            if kind == "pypi_json"
            else _github_projection(raw, repository)
        )
        if not projection or len(projection) > MAX_PROJECTION_CHARS:
            raise ValueError("V2.49.74 authority projection is oversized")
        projected.append({"url": url, "text": projection})
        kinds.append(kind)
        raw_chars += len(raw)
    if set(kinds) != {"pypi_json", "github_html"}:
        raise ValueError("V2.49.74 exact authority pair is incomplete")
    receipt: dict[str, object] = {
        "artifact_version": 1,
        "role": PROJECTION_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "raw_page_count": len(pages),
        "raw_page_chars": raw_chars,
        "projected_page_count": len(projected),
        "projection_chars": sum(len(page["text"]) for page in projected),
        "exact_pypi_json_count": kinds.count("pypi_json"),
        "exact_github_html_count": kinds.count("github_html"),
        "projection_derived_only_from_same_forward_shared_page_bytes": True,
        "provider_narrative_or_search_snippet_used": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "contains_field_value_url_page_prediction_answer_or_credential": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = parent.payload_sha256(receipt)
    return projected, receipt


def build_compact_evidence(
    pages: Sequence[Mapping[str, object]],
    raw_evidence: str,
    *,
    project: str,
    repository: str,
    total_chars: int,
) -> dict[str, object]:
    projected, projection_receipt = project_exact_pages(
        pages, project=project, repository=repository
    )
    result = parent.build_compact_evidence(
        projected,
        raw_evidence,
        project=project,
        repository=repository,
        total_chars=total_chars,
    )
    output = copy.deepcopy(result)
    output["artifact_version"] = 1
    output["role"] = ROLE
    output["policy_id"] = POLICY_ID
    output["projection_receipt"] = projection_receipt
    return output


def validate_receipt(value: Mapping[str, object], *, total_chars: int) -> dict[str, object]:
    """Keep the V2.49.72 count-only receipt boundary runner-compatible."""

    return parent.validate_receipt(value, total_chars=total_chars)


__all__ = [
    "MAX_PROJECTION_CHARS",
    "MAX_RAW_PAGE_CHARS",
    "MAX_RAW_PAGES",
    "POLICY_ID",
    "PROJECTION_RECEIPT_ROLE",
    "ROLE",
    "build_compact_evidence",
    "project_exact_pages",
    "validate_receipt",
]
