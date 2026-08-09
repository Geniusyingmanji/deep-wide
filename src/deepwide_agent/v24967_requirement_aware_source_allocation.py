"""URL-only requirement-aware source selection and evidence allocation.

The policy is deliberately narrow: a visible task supplies one PyPI project
identity and one GitHub repository identity.  Only exact public authority/path
matches satisfy either requirement.  Page text, provider summaries, benchmark
labels, predictions, evaluator data, and scores never affect selection.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import unquote, urlsplit

from .clients import canonicalize_url
from .v24959_source_fair_discovery import order_source_fair_leads


POLICY_ID = "v24967_requirement_aware_authority_allocation_v1"
REQUIREMENTS = ("pypi_project", "github_release")
PROJECT_NORMALIZER = re.compile(r"[-_.]+")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def normalize_project(value: object) -> str:
    text = PROJECT_NORMALIZER.sub("-", str(value).strip().casefold()).strip("-")
    if not text or len(text) > 128 or not re.fullmatch(r"[a-z0-9-]+", text):
        raise ValueError("V2.49.67 invalid visible PyPI project identity")
    return text


def normalize_repository(value: object) -> tuple[str, str]:
    text = str(value).strip()
    if not REPOSITORY.fullmatch(text):
        raise ValueError("V2.49.67 invalid visible GitHub repository identity")
    owner, repository = text.split("/", 1)
    return owner.casefold(), repository.casefold()


def authority_requirement(
    lead_or_url: Mapping[str, Any] | str,
    *,
    project: str,
    repository: str,
) -> str | None:
    """Classify only exact PyPI-project or GitHub-release URL identities."""

    expected_project = normalize_project(project)
    expected_owner, expected_repository = normalize_repository(repository)
    if isinstance(lead_or_url, Mapping):
        raw = str(lead_or_url.get("fetch_url") or lead_or_url.get("url") or "")
    else:
        raw = str(lead_or_url)
    canonical = canonicalize_url(raw)
    parsed = urlsplit(canonical)
    host = (parsed.hostname or "").casefold().rstrip(".")
    segments = [unquote(part).casefold() for part in parsed.path.split("/") if part]
    if (
        host == "pypi.org"
        and len(segments) >= 2
        and segments[0] == "project"
        and normalize_project(segments[1]) == expected_project
    ):
        return "pypi_project"
    if (
        host == "github.com"
        and len(segments) >= 3
        and segments[0] == expected_owner
        and segments[1] == expected_repository
        and segments[2] == "releases"
    ):
        return "github_release"
    return None


def select_requirement_aware(
    raw: object,
    *,
    cap: int,
    project: str,
    repository: str,
    prior_urls: Sequence[str] | set[str] | frozenset[str] = (),
    prior_sources: Sequence[str] | set[str] | frozenset[str] = (),
    prior_requirements: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    """Select uncovered exact requirements, then fill source-fairly."""

    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.49.67 invalid prefix cap")
    vectors = (prior_urls, prior_sources, prior_requirements)
    if any(isinstance(value, (str, bytes)) for value in vectors):
        raise ValueError("V2.49.67 invalid prior vector")
    previous_urls = {
        canonicalize_url(str(value))
        for value in prior_urls
        if canonicalize_url(str(value))
    }
    previous_sources = {
        str(value).strip().casefold() for value in prior_sources if str(value).strip()
    }
    previous_requirements = {str(value) for value in prior_requirements}
    if not previous_requirements.issubset(REQUIREMENTS):
        raise ValueError("V2.49.67 prior requirement vector drifted")

    ordered, observation, private = order_source_fair_leads(
        raw, prior_sources=previous_sources
    )
    by_url = {
        canonicalize_url(str(lead.get("url", ""))): copy.deepcopy(dict(lead))
        for lead in ordered
        if canonicalize_url(str(lead.get("url", "")))
    }
    order = [canonicalize_url(str(value)) for value in observation["source_fair_urls"]]
    if len(order) != len(set(order)) or set(order) != set(by_url):
        raise RuntimeError("V2.49.67 parent URL set drifted")

    available = [url for url in order if url not in previous_urls]
    chosen: list[str] = []
    newly_covered: set[str] = set()
    for requirement in REQUIREMENTS:
        if requirement in previous_requirements:
            continue
        match = next(
            (
                url
                for url in available
                if url not in chosen
                and authority_requirement(
                    by_url[url], project=project, repository=repository
                )
                == requirement
            ),
            None,
        )
        if match is not None:
            chosen.append(match)
            newly_covered.add(requirement)
    for url in available:
        if url not in chosen:
            chosen.append(url)
        if len(chosen) >= cap:
            break
    chosen = chosen[:cap]
    selected_requirements = {
        requirement
        for url in chosen
        if (
            requirement := authority_requirement(
                by_url[url], project=project, repository=repository
            )
        )
        is not None
    }
    cumulative_requirements = previous_requirements | selected_requirements
    source_by_url = private["source_by_url"]
    current_sources = {
        source_by_url[url]
        for url in chosen
        if source_by_url.get(url) is not None
    }
    cumulative_sources = previous_sources | current_sources
    receipt = {
        "artifact_version": 1,
        "role": "v24967_requirement_aware_selection_receipt",
        "policy_id": POLICY_ID,
        "prefix_cap": cap,
        "selected_url_count": len(chosen),
        "prior_url_count": len(previous_urls),
        "prior_source_count": len(previous_sources),
        "current_source_count": len(current_sources),
        "cumulative_source_count": len(cumulative_sources),
        "prior_requirement_count": len(previous_requirements),
        "selected_requirement_count": len(selected_requirements),
        "new_requirement_count": len(cumulative_requirements - previous_requirements),
        "cumulative_requirement_count": len(cumulative_requirements),
        "exact_pypi_project_selected": "pypi_project" in selected_requirements,
        "exact_github_release_selected": "github_release" in selected_requirements,
        "same_parent_url_set_before_cap": True,
        "visible_project_and_repository_identity_only": True,
        "provider_narrative_snippet_page_content_prediction_or_score_used": False,
        "benchmark_label_mapping_gold_evaluator_reward_read": False,
        "contains_query_url_host_title_page_prediction_answer_or_credential": False,
    }
    validate_selection_receipt(receipt)
    return {
        "selected": [copy.deepcopy(by_url[url]) for url in chosen],
        "cumulative_sources": frozenset(cumulative_sources),
        "cumulative_requirements": frozenset(cumulative_requirements),
        "receipt": receipt,
    }


def _page_vector(
    leads: Sequence[Mapping[str, Any]],
    fetched: Mapping[str, Mapping[str, Any]],
    *,
    project: str,
    repository: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for lead in leads:
        canonical = canonicalize_url(
            str(lead.get("fetch_url") or lead.get("url") or "")
        )
        page = fetched.get(canonical) or {}
        text = str(page.get("raw_content") or page.get("content") or "").strip()
        if not text:
            continue
        title = " ".join(str(page.get("title") or "Fetched page").split())
        rendered = f"TITLE: {title}\nCONTENT:\n{text}\n\n"
        output.append(
            {
                "rendered": rendered,
                "requirement": authority_requirement(
                    lead, project=project, repository=repository
                ),
            }
        )
    return output


def compose_evidence(
    leads: Sequence[Mapping[str, Any]],
    fetched: Mapping[str, Mapping[str, Any]],
    *,
    project: str,
    repository: str,
    total_chars: int,
    requirement_quota_chars: int,
    requirement_aware: bool,
) -> tuple[str, dict[str, Any]]:
    """Render an exact-size evidence budget and content-free allocation receipt."""

    integers = (total_chars, requirement_quota_chars)
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for value in integers)
        or total_chars <= 0
        or requirement_quota_chars <= 0
        or requirement_quota_chars * len(REQUIREMENTS) > total_chars
    ):
        raise ValueError("V2.49.67 invalid evidence budget")
    pages = _page_vector(
        leads, fetched, project=project, repository=repository
    )
    if not pages:
        raise RuntimeError("V2.49.67 no usable pages")

    fragments: list[tuple[str | None, str]] = []
    consumed = [0] * len(pages)
    if requirement_aware:
        for requirement in REQUIREMENTS:
            index = next(
                (
                    position
                    for position, page in enumerate(pages)
                    if page["requirement"] == requirement
                ),
                None,
            )
            if index is None:
                continue
            rendered = str(pages[index]["rendered"])
            amount = min(requirement_quota_chars, len(rendered))
            fragments.append((requirement, rendered[:amount]))
            consumed[index] = amount
    for index, page in enumerate(pages):
        rendered = str(page["rendered"])
        if consumed[index] < len(rendered):
            fragments.append((page["requirement"], rendered[consumed[index] :]))

    pieces: list[str] = []
    requirement_chars = {name: 0 for name in REQUIREMENTS}
    remaining = total_chars
    for requirement, fragment in fragments:
        if remaining <= 0:
            break
        piece = fragment[:remaining]
        pieces.append(piece)
        if requirement in requirement_chars:
            requirement_chars[requirement] += len(piece)
        remaining -= len(piece)
    evidence = "".join(pieces)
    if len(evidence) != total_chars:
        raise RuntimeError("V2.49.67 fixed evidence budget unavailable")
    usable_requirements = {
        str(page["requirement"])
        for page in pages
        if page["requirement"] in REQUIREMENTS
    }
    receipt = {
        "artifact_version": 1,
        "role": "v24967_requirement_aware_evidence_receipt",
        "policy_id": POLICY_ID,
        "requirement_aware": bool(requirement_aware),
        "selected_lead_count": len(leads),
        "usable_page_count": len(pages),
        "usable_requirement_count": len(usable_requirements),
        "evidence_chars": len(evidence),
        "pypi_project_evidence_chars": requirement_chars["pypi_project"],
        "github_release_evidence_chars": requirement_chars["github_release"],
        "total_requirement_evidence_chars": sum(requirement_chars.values()),
        "fixed_total_budget": True,
        "visible_project_and_repository_identity_only": True,
        "provider_narrative_or_snippet_used": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_read": False,
        "contains_query_url_host_title_page_prediction_answer_or_credential": False,
    }
    validate_evidence_receipt(receipt, total_chars=total_chars)
    return evidence, receipt


def validate_selection_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    integer_fields = (
        "prefix_cap",
        "selected_url_count",
        "prior_url_count",
        "prior_source_count",
        "current_source_count",
        "cumulative_source_count",
        "prior_requirement_count",
        "selected_requirement_count",
        "new_requirement_count",
        "cumulative_requirement_count",
    )
    if (
        copied.get("role") != "v24967_requirement_aware_selection_receipt"
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or copied["selected_url_count"] > copied["prefix_cap"]
        or copied["cumulative_source_count"] < copied["prior_source_count"]
        or copied["cumulative_requirement_count"] < copied["prior_requirement_count"]
        or copied["cumulative_requirement_count"] > len(REQUIREMENTS)
        or copied.get("same_parent_url_set_before_cap") is not True
        or copied.get("visible_project_and_repository_identity_only") is not True
        or copied.get("provider_narrative_snippet_page_content_prediction_or_score_used")
        is not False
        or copied.get("benchmark_label_mapping_gold_evaluator_reward_read") is not False
        or copied.get("contains_query_url_host_title_page_prediction_answer_or_credential")
        is not False
    ):
        raise ValueError("V2.49.67 selection receipt drifted")
    return copied


def validate_evidence_receipt(
    value: Mapping[str, Any], *, total_chars: int
) -> dict[str, Any]:
    copied = dict(value)
    integer_fields = (
        "selected_lead_count",
        "usable_page_count",
        "usable_requirement_count",
        "evidence_chars",
        "pypi_project_evidence_chars",
        "github_release_evidence_chars",
        "total_requirement_evidence_chars",
    )
    if (
        copied.get("role") != "v24967_requirement_aware_evidence_receipt"
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("requirement_aware"), bool)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or copied["evidence_chars"] != total_chars
        or copied["usable_requirement_count"] > len(REQUIREMENTS)
        or copied["total_requirement_evidence_chars"]
        != copied["pypi_project_evidence_chars"]
        + copied["github_release_evidence_chars"]
        or copied["total_requirement_evidence_chars"] > copied["evidence_chars"]
        or copied.get("fixed_total_budget") is not True
        or copied.get("visible_project_and_repository_identity_only") is not True
        or copied.get("provider_narrative_or_snippet_used") is not False
        or copied.get("benchmark_label_mapping_gold_evaluator_score_reward_read")
        is not False
        or copied.get("contains_query_url_host_title_page_prediction_answer_or_credential")
        is not False
    ):
        raise ValueError("V2.49.67 evidence receipt drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "REQUIREMENTS",
    "authority_requirement",
    "compose_evidence",
    "normalize_project",
    "normalize_repository",
    "select_requirement_aware",
    "validate_evidence_receipt",
    "validate_selection_receipt",
]
