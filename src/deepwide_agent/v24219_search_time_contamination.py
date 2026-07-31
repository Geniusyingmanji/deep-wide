"""Pure, label-blind search-time-contamination diagnostics for V2.42.19.

The detector is deliberately conservative.  It can flag benchmark-metadata
leakage (BML), question-context leakage (QCL), and explicit-answer-leakage
*candidates*.  It cannot confirm EAL because neither gold answers nor evaluator
artifacts are accepted by this module.

Queries are intentionally absent from the public input type.  A query is
derived from the visible question, so query/question overlap is not evidence
that a search result contained the benchmark question.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import Any
from urllib.parse import unquote, urlsplit


PRIMARY_QCL_RATIO = 0.50
MIN_QCL_CHARS = 80
QCL_SENSITIVITY_RATIOS = (0.25, 0.50, 0.75)

_OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
_BENCHMARK_MARKERS = (
    "deepwidesearch",
    "deep-wide-search",
    "deepwidebench",
    "overall_20250916",
)
_DATASET_HOST_PATHS = (
    ("huggingface.co", "/datasets"),
    ("kaggle.com", "/datasets"),
    ("paperswithcode.com", "/dataset"),
)
_ARTIFACT_HOSTS = {
    "github.com",
    "raw.githubusercontent.com",
    "gist.github.com",
    "coursehero.com",
    "quizlet.com",
    "scribd.com",
    "chegg.com",
    "study.com",
}
_ANSWER_MARKERS = re.compile(
    r"(?:"
    r"correct\s+answer|answer\s*key|reference\s+answer|ground[ _-]?truth|"
    r"official\s+solution|solved\s+(?:answer|question)|questions?[ _-]?and[ _-]?answers?|"
    r"(?:^|[/_.-])answers?(?:[/_.-]|$)|(?:^|[/_.-])solutions?(?:[/_.-]|$)|"
    r"标准答案|参考答案|正确答案|答案[:：]"
    r")",
    re.IGNORECASE,
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _normalized(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(text.split())


@lru_cache(maxsize=512)
def _suffix_automaton(text: str) -> tuple[dict[str, Any], ...]:
    states: list[dict[str, Any]] = [{"next": {}, "link": -1, "length": 0}]
    last = 0
    for character in text:
        current = len(states)
        states.append(
            {
                "next": {},
                "link": 0,
                "length": int(states[last]["length"]) + 1,
            }
        )
        parent = last
        while parent >= 0 and character not in states[parent]["next"]:
            states[parent]["next"][character] = current
            parent = int(states[parent]["link"])
        if parent < 0:
            states[current]["link"] = 0
        else:
            target = int(states[parent]["next"][character])
            if int(states[parent]["length"]) + 1 == int(states[target]["length"]):
                states[current]["link"] = target
            else:
                clone = len(states)
                states.append(
                    {
                        "next": dict(states[target]["next"]),
                        "link": int(states[target]["link"]),
                        "length": int(states[parent]["length"]) + 1,
                    }
                )
                while parent >= 0 and states[parent]["next"].get(character) == target:
                    states[parent]["next"][character] = clone
                    parent = int(states[parent]["link"])
                states[target]["link"] = clone
                states[current]["link"] = clone
        last = current
    return tuple(states)


def longest_common_contiguous_span(question: object, content: object) -> dict[str, Any]:
    """Return length/ratio/hash only; never return question or page text."""

    normalized_question = _normalized(question)
    normalized_content = _normalized(content)
    if not normalized_question or not normalized_content:
        return {
            "normalized_question_chars": len(normalized_question),
            "longest_contiguous_chars": 0,
            "longest_contiguous_ratio": 0.0,
            "matched_span_sha256": None,
        }
    states = _suffix_automaton(normalized_question)
    state = 0
    length = 0
    best = 0
    best_end = 0
    for index, character in enumerate(normalized_content, start=1):
        while state and character not in states[state]["next"]:
            state = int(states[state]["link"])
            length = min(length, int(states[state]["length"]))
        target = states[state]["next"].get(character)
        if target is None:
            state = 0
            length = 0
        else:
            state = int(target)
            length += 1
        if length > best:
            best = length
            best_end = index
    span = normalized_content[best_end - best : best_end]
    return {
        "normalized_question_chars": len(normalized_question),
        "longest_contiguous_chars": best,
        "longest_contiguous_ratio": round(best / len(normalized_question), 6),
        "matched_span_sha256": (
            hashlib.sha256(span.encode()).hexdigest() if span else None
        ),
    }


def _url_signals(url: str) -> tuple[str, list[str]]:
    decoded = _normalized(unquote(url))
    parsed = urlsplit(url)
    host = parsed.netloc.casefold().split("@")[-1].split(":")[0]
    reasons: list[str] = []
    if host in _ARTIFACT_HOSTS:
        reasons.append("common_artifact_host")
    if any(host == expected and path in parsed.path.casefold() for expected, path in _DATASET_HOST_PATHS):
        reasons.append("dataset_host_path")
    if any(marker in decoded for marker in _BENCHMARK_MARKERS):
        reasons.append("benchmark_marker_in_url")
    return host, reasons


def scan_evidence_item(
    *,
    question: str,
    opaque_id: str,
    evidence: Mapping[str, Any],
    item_index: int,
) -> dict[str, Any]:
    """Scan one evidence projection without accepting query or evaluator data."""

    if _OPAQUE_ID.fullmatch(opaque_id) is None:
        raise RuntimeError("V2.42.19 opaque task ID is malformed")
    allowed = {
        "id",
        "kind",
        "url",
        "source_family",
        "title",
        "text",
        "fingerprint",
    }
    if not set(evidence).issubset(allowed):
        raise RuntimeError("V2.42.19 evidence projection contains an unapproved field")
    url = str(evidence.get("url") or "")
    title = str(evidence.get("title") or "")
    text = str(evidence.get("text") or "")
    kind = str(evidence.get("kind") or "")
    host, bml_reasons = _url_signals(url)
    opaque_exposed = opaque_id in unquote(url) or opaque_id in title or opaque_id in text
    if opaque_exposed:
        bml_reasons.append("opaque_task_id_exposed")
    folded_metadata = _normalized(f"{url} {title}")
    if any(marker in folded_metadata for marker in _BENCHMARK_MARKERS):
        bml_reasons.append("benchmark_marker_in_metadata")
    bml_reasons = list(dict.fromkeys(bml_reasons))

    page_content_scanned = kind == "page"
    overlap = longest_common_contiguous_span(question, text if page_content_scanned else "")
    longest = int(overlap["longest_contiguous_chars"])
    ratio = float(overlap["longest_contiguous_ratio"])
    sensitivity = {
        f"ratio_{int(threshold * 100):02d}": (
            page_content_scanned
            and longest >= MIN_QCL_CHARS
            and ratio >= threshold
        )
        for threshold in QCL_SENSITIVITY_RATIOS
    }
    qcl_candidate = bool(sensitivity[f"ratio_{int(PRIMARY_QCL_RATIO * 100):02d}"])
    answer_surface = f"{unquote(url)}\n{title}\n{text}"
    answer_artifact_candidate = bool(_ANSWER_MARKERS.search(answer_surface))
    eal_candidate = qcl_candidate and answer_artifact_candidate
    return {
        "item_index": int(item_index),
        "evidence_id": str(evidence.get("id") or ""),
        "kind": kind,
        "source_host": host,
        "url_sha256": hashlib.sha256(url.encode()).hexdigest() if url else None,
        "content_fingerprint_sha256": (
            hashlib.sha256(str(evidence.get("fingerprint") or "").encode()).hexdigest()
            if evidence.get("fingerprint")
            else None
        ),
        "bml_candidate": bool(bml_reasons),
        "bml_reasons": bml_reasons,
        "page_content_scanned_for_qcl": page_content_scanned,
        **overlap,
        "qcl_sensitivity": sensitivity,
        "qcl_primary_candidate": qcl_candidate,
        "answer_artifact_candidate": answer_artifact_candidate,
        "eal_candidate_unconfirmed": eal_candidate,
        "confirmed_eal": None,
        "question_query_page_text_or_answer_emitted": False,
    }


def scan_task(
    *, opaque_id: str, question: str, evidence: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    count = 0
    for count, item in enumerate(evidence, start=1):
        finding = scan_evidence_item(
            question=question,
            opaque_id=opaque_id,
            evidence=item,
            item_index=count,
        )
        if (
            finding["bml_candidate"]
            or any(finding["qcl_sensitivity"].values())
            or finding["answer_artifact_candidate"]
        ):
            findings.append(finding)
    flags = {
        "bml_candidate": any(row["bml_candidate"] for row in findings),
        "qcl_primary_candidate": any(
            row["qcl_primary_candidate"] for row in findings
        ),
        "eal_candidate_unconfirmed": any(
            row["eal_candidate_unconfirmed"] for row in findings
        ),
    }
    sensitivity = {
        key: any(row["qcl_sensitivity"][key] for row in findings)
        for key in (f"ratio_{int(value * 100):02d}" for value in QCL_SENSITIVITY_RATIOS)
    }
    return {
        "opaque_id_sha256": hashlib.sha256(opaque_id.encode()).hexdigest(),
        "evidence_items_scanned": count,
        "findings": findings,
        "flags": flags,
        "qcl_sensitivity": sensitivity,
        "question_query_page_text_or_answer_emitted": False,
    }


def aggregate_task_scans(tasks: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(tasks)
    threshold_keys = tuple(
        f"ratio_{int(value * 100):02d}" for value in QCL_SENSITIVITY_RATIOS
    )
    return {
        "tasks_scanned": len(rows),
        "evidence_items_scanned": sum(
            int(row.get("evidence_items_scanned", 0)) for row in rows
        ),
        "tasks_with_bml_candidate": sum(
            bool((row.get("flags") or {}).get("bml_candidate")) for row in rows
        ),
        "tasks_with_qcl_primary_candidate": sum(
            bool((row.get("flags") or {}).get("qcl_primary_candidate"))
            for row in rows
        ),
        "tasks_with_eal_candidate_unconfirmed": sum(
            bool((row.get("flags") or {}).get("eal_candidate_unconfirmed"))
            for row in rows
        ),
        "qcl_sensitivity_task_counts": {
            key: sum(bool((row.get("qcl_sensitivity") or {}).get(key)) for row in rows)
            for key in threshold_keys
        },
        "confirmed_eal": None,
        "confirmed_eal_requires_gold_and_manual_or_independent_judge": True,
        "question_query_page_text_url_or_task_id_emitted_in_aggregate": False,
    }


__all__ = [
    "MIN_QCL_CHARS",
    "PRIMARY_QCL_RATIO",
    "QCL_SENSITIVITY_RATIOS",
    "aggregate_task_scans",
    "longest_common_contiguous_span",
    "payload_sha256",
    "scan_evidence_item",
    "scan_task",
]
