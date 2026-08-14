#!/usr/bin/env python3
"""Offline diagnosis of the frozen V2.54.54 official-XML prefixes."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25449_official_rfc_xml_record_candidate as primitive  # noqa: E402
from deepwide_agent import v25454_official_rfc_xml_shared_effect_external_contract as contract  # noqa: E402
from scripts import run_v25454_official_rfc_xml_shared_effect_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25455_v25454_official_xml_prefix_diagnosis"
SOURCE = Path("scripts/diagnose_v25455_v25454_official_xml_prefix.py")
TEST = Path("tests/test_diagnose_v25455_v25454_official_xml_prefix.py")
FORWARD_RESULT = contract.FORWARD_RESULT
FORWARD_AUDIT = contract.FORWARD_AUDIT
TASK_ROWS = contract.TASK_ROWS
PREDICTION_FREEZE = contract.PREDICTION_FREEZE
OUTPUT = Path(
    f"results/v25455_v25454_official_xml_prefix_diagnosis_v1_{DATE}.json"
)
FIXED_HASHES = {
    FORWARD_RESULT: "43a65a3088d0a105bf90cd5c0f938dfe4e67e3a9dc1d5299a7a082ce6fdd61e5",
    FORWARD_AUDIT: "a748519f2aa755aed6cba4e29f3647d96958016a2f281c838364522233840ba2",
    TASK_ROWS: "54dd1065e05c926337d7b1ea56a1950bffc1b868849d76c6eafddd5c23fa30dc",
    PREDICTION_FREEZE: "47849f964638e7d3f56320007c32a1de36354ba73a313ae1e43ac83467c123fd",
}
EXPECTED_STATS = {
    "task_count": 20,
    "exact_nonredirected_page_count": 78,
    "fixed_5000_character_prefix_count": 78,
    "xml_declaration_count": 78,
    "rfc_root_open_count": 78,
    "front_open_count": 78,
    "complete_date_count": 78,
    "front_close_count": 0,
    "current_parser_valid_record_count": 0,
    "date_bounded_parseable_record_count": 78,
    "prediction_changed_task_count": 0,
    "minimum_date_end_offset": 956,
    "maximum_date_end_offset": 3266,
}
EXPECTED_AUTHOR_HISTOGRAM = {
    "1": 21,
    "2": 15,
    "3": 14,
    "4": 14,
    "5": 13,
    "6": 1,
}
_DATE = re.compile(r"<date\b[^>]*(?:/>|>.*?</date>)", re.DOTALL)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.54.55 expected ordinary repository file")
    return path


def _tracked(relative: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        ).returncode
        == 0
    )


def _date_bounded_document(content: str) -> str | None:
    """Return a safe temporary RFC/front closure ending at complete date."""

    upper = content.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        return None
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
    if parsed.tag != "rfc" or parsed_front is None or parsed_front.find("date") is None:
        return None
    return document


def _rows() -> list[dict[str, Any]]:
    values = [
        json.loads(line)
        for line in _ordinary(TASK_ROWS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [runner.validate_task_row(value) for value in values]


def _bound_forward() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = json.loads(_ordinary(FORWARD_RESULT).read_text(encoding="utf-8"))
    audit = json.loads(_ordinary(FORWARD_AUDIT).read_text(encoding="utf-8"))
    runner.validate_forward_result(forward)
    if (
        any(contract.sha256(ROOT / path) != digest for path, digest in FIXED_HASHES.items())
        or audit.get("role")
        != "v25454_official_rfc_xml_shared_effect_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("mechanism_decision", {}).get("mechanism_gate_passed")
        is not False
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
    ):
        raise RuntimeError("V2.54.55 frozen forward barrier drifted")
    return forward, audit


def _stats(rows: list[Mapping[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    pages: list[Mapping[str, Any]] = []
    current_valid = 0
    changed = 0
    for row in rows:
        result = row["runtime_result"]
        pages.extend(result["private_same_forward_official_rfc_xml_pages"])
        application = result["private_official_rfc_xml_application"]
        current_valid += int(application["valid_record_count"])
        changed += int(row["candidate_prediction_changed"])
    date_offsets: list[int] = []
    author_histogram: Counter[str] = Counter()
    date_parseable = 0
    for page in pages:
        content = str(page["content"])
        date = _DATE.search(content)
        if date is not None:
            date_offsets.append(date.end())
        document = _date_bounded_document(content)
        if document is not None:
            date_parseable += 1
            root = ET.fromstring(document)
            front = root.find("front")
            author_histogram[str(len(front.findall("author")))] += 1
    stats = {
        "task_count": len(rows),
        "exact_nonredirected_page_count": len(pages),
        "fixed_5000_character_prefix_count": sum(
            len(str(page["content"])) == 5000 for page in pages
        ),
        "xml_declaration_count": sum(
            str(page["content"]).lstrip().startswith("<?xml") for page in pages
        ),
        "rfc_root_open_count": sum(
            re.search(r"<rfc(?:\s|>)", str(page["content"])) is not None
            for page in pages
        ),
        "front_open_count": sum("<front" in str(page["content"]) for page in pages),
        "complete_date_count": len(date_offsets),
        "front_close_count": sum("</front>" in str(page["content"]) for page in pages),
        "current_parser_valid_record_count": current_valid,
        "date_bounded_parseable_record_count": date_parseable,
        "prediction_changed_task_count": changed,
        "minimum_date_end_offset": min(date_offsets) if date_offsets else -1,
        "maximum_date_end_offset": max(date_offsets) if date_offsets else -1,
    }
    return stats, dict(sorted(author_histogram.items()))


def build_diagnosis(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    forward, audit = _bound_forward()
    rows = _rows()
    stats, authors = _stats(rows)
    if require_clean:
        head = _git("rev-parse", "HEAD")
        target = _git("rev-parse", "target/main")
        clean = not _git("status", "--porcelain")
        tracked = _tracked(SOURCE) and _tracked(TEST)
    else:
        head = target = "build-only"
        clean = tracked = True
    findings = []
    if stats != EXPECTED_STATS:
        findings.append("frozen_prefix_statistics_drifted")
    if authors != EXPECTED_AUTHOR_HISTOGRAM:
        findings.append("complete_author_histogram_drifted")
    if not (clean and head == target and tracked):
        findings.append("repository_not_clean_pushed_and_tracked")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "bound_artifact_sha256": {str(path): digest for path, digest in FIXED_HASHES.items()},
        "forward_status": {
            "terminal_tasks": forward["aggregate"]["terminal_tasks"],
            "mechanism_gate_passed": audit["mechanism_decision"]["mechanism_gate_passed"],
            "postfreeze_quality_protocol_authorized": audit["authorization"]["postfreeze_quality_protocol"],
        },
        "aggregate_prefix_statistics": stats,
        "complete_author_count_histogram": authors,
        "diagnosis": {
            "network_or_exact_url_binding_failure": False,
            "all_exact_pages_are_fixed_5000_character_prefixes": True,
            "current_parser_requires_complete_front_close": True,
            "all_frozen_prefixes_lack_complete_front_close": True,
            "all_frozen_prefixes_contain_complete_author_sequence_and_date": True,
            "date_bounded_temporary_front_closure_parseable_for_all_exact_pages": True,
            "safe_successor_requires_no_new_fetch_model_search_or_truth": True,
        },
        "candidate_page_field_values_or_identifiers_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "date_bounded_official_xml_parser_successor_build": not findings,
            "new_external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    valid = copied.get("diagnosis_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("aggregate_prefix_statistics") != EXPECTED_STATS
        or copied.get("complete_author_count_histogram") != EXPECTED_AUTHOR_HISTOGRAM
        or copied.get("findings") != []
        or valid is not True
        or copied.get("candidate_page_field_values_or_identifiers_emitted") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "date_bounded_official_xml_parser_successor_build": True,
            "new_external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.55 prefix diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "diagnosis_valid": value["diagnosis_valid"], "findings": value["findings"], "stats": value["aggregate_prefix_statistics"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
