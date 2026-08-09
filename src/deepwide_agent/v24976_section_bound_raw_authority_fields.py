"""Section-bound successor to the raw-authority compact-field seam.

The V2.49.74 GitHub matcher allowed a tag link outside the current release
section to fall within a bounded character window before ``/releases/latest``.
On short pages that can create false ambiguity.  This pure successor binds the
tag href, latest marker, and release date to the same exact ``<section>``.
"""

from __future__ import annotations

import copy
import html
import re
from collections.abc import Mapping, Sequence
from urllib.parse import unquote

from . import v24972_identity_bound_compact_fields as fields
from . import v24974_raw_authority_compact_fields as parent
from .clients import canonicalize_url
from .v24967_requirement_aware_source_allocation import normalize_repository


POLICY_ID = "v24976_section_bound_raw_authority_fields_v1"
ROLE = "v24976_section_bound_raw_authority_fields_result"
PROJECTION_RECEIPT_ROLE = "v24976_section_bound_projection_receipt"
SECTION_CHARS = 250_000
LATEST_HREF = "releases/latest"


def _github_projection(text: str, repository: str) -> str:
    owner, repo = normalize_repository(repository)
    identity = f"{owner}/{repo}"
    title_match = parent.TITLE.search(text)
    title = html.unescape(
        " ".join((title_match.group(1) if title_match else "").split())
    )
    if title.casefold() != f"releases · {identity} · github".casefold():
        raise ValueError("V2.49.76 GitHub HTML title identity mismatch")

    escaped = re.escape(identity)
    latest = re.compile(
        rf"href=[\"']/{escaped}/releases/latest[\"']",
        re.IGNORECASE,
    )
    tag_href = re.compile(
        rf"href=[\"']/{escaped}/releases/tag/([^\"'?#]+)[\"']",
        re.IGNORECASE,
    )
    lowered = text.casefold()
    candidates: set[tuple[str, str]] = set()
    for marker in latest.finditer(text):
        section_start = lowered.rfind("<section", 0, marker.start())
        section_end = lowered.find("</section>", marker.end())
        if (
            section_start < 0
            or section_end < 0
            or section_end - section_start > SECTION_CHARS
        ):
            continue
        before_latest = text[section_start : marker.start()]
        tags = {
            fields._safe_line(unquote(html.unescape(matched.group(1))), fields.TAG)
            for matched in tag_href.finditer(before_latest)
        }
        if len(tags) != 1:
            continue
        date_match = parent.RELATIVE_TIME.search(text, marker.end(), section_end)
        if date_match is None:
            continue
        candidates.add((next(iter(tags)), fields._valid_date(date_match.group(1))))
    if len(candidates) != 1:
        raise ValueError("V2.49.76 section-bound latest release is absent or ambiguous")
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
        raise ValueError("V2.49.76 raw page vector is invalid")
    if len(pages) != parent.MAX_RAW_PAGES:
        raise ValueError("V2.49.76 requires exactly two authority pages")
    projected: list[dict[str, str]] = []
    kinds: list[str] = []
    raw_chars = 0
    for page in pages:
        if not isinstance(page, Mapping):
            raise ValueError("V2.49.76 raw page is not a mapping")
        url = canonicalize_url(str(page.get("url") or ""))
        kind = fields.authority_kind(
            url, project=project, repository=repository
        )
        if kind not in {"pypi_json", "github_html"} or kind in kinds:
            raise ValueError("V2.49.76 authority kind or cardinality drifted")
        raw = parent._raw_text(page)
        projection = (
            parent._pypi_projection(raw, project)
            if kind == "pypi_json"
            else _github_projection(raw, repository)
        )
        if not projection or len(projection) > parent.MAX_PROJECTION_CHARS:
            raise ValueError("V2.49.76 authority projection is oversized")
        projected.append({"url": url, "text": projection})
        kinds.append(kind)
        raw_chars += len(raw)
    if set(kinds) != {"pypi_json", "github_html"}:
        raise ValueError("V2.49.76 exact authority pair is incomplete")
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
        "tag_latest_and_date_bound_to_same_release_section": True,
        "projection_derived_only_from_same_forward_shared_page_bytes": True,
        "provider_narrative_or_search_snippet_used": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "contains_field_value_url_page_prediction_answer_or_credential": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = fields.payload_sha256(receipt)
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
    result = fields.build_compact_evidence(
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


validate_receipt = fields.validate_receipt


__all__ = [
    "POLICY_ID",
    "PROJECTION_RECEIPT_ROLE",
    "ROLE",
    "SECTION_CHARS",
    "build_compact_evidence",
    "project_exact_pages",
    "validate_receipt",
]
