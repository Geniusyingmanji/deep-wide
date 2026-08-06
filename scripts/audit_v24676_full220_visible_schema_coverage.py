#!/usr/bin/env python3
"""Label-blind full-220 visible-schema coverage audit.

This audit reads only the frozen DeepWideBench ``{opaque_id, question}``
manifest through the validated V2.46.35 visible-only contract.  It never opens
mapping, category, split, gold, predictions, scores, rewards, evaluator files,
or prior per-task outcomes.  Its output contains aggregate counts only: no
question, column name, or opaque task identifier is persisted.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    FORWARD_CONTRACT,
    SOURCE_MANIFEST,
    selected_tasks,
    sha256,
    validate_forward_contract,
)
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from deepwide_agent.v24675_expanded_visible_schema import (  # noqa: E402
    extract_expanded_visible_columns,
)


DATE = "20260806"
OUTPUT = Path(f"results/v24676_full220_visible_schema_coverage_audit_v1_{DATE}.json")
PARENT_DIAGNOSIS = Path(
    f"results/v24674_v24671_information_gain_no_go_diagnosis_v1_{DATE}.json"
)
EXPECTED_OLD_WIDTHS = {
    "0": 26,
    "1": 3,
    "3": 43,
    "4": 45,
    "5": 38,
    "6": 27,
    "7": 16,
    "8": 5,
    "9": 7,
    "10": 3,
    "11": 1,
    "12": 2,
    "14": 2,
    "20": 2,
}
EXPECTED_NEW_WIDTHS = {
    "0": 5,
    "1": 3,
    "3": 47,
    "4": 48,
    "5": 43,
    "6": 31,
    "7": 17,
    "8": 6,
    "9": 10,
    "10": 3,
    "11": 1,
    "12": 2,
    "14": 2,
    "20": 2,
}
EXPECTED_ADDED_WIDTHS = {"3": 4, "4": 3, "5": 5, "6": 4, "7": 1, "8": 1, "9": 3}
ROR_VISIBLE_PATTERN = re.compile(
    r"\bROR\b|Research Organization Registry|9-character ROR", re.IGNORECASE
)


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.76 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.76 expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _histogram(values: Counter[int]) -> dict[str, int]:
    return {str(key): values[key] for key in sorted(values)}


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    contract = validate_forward_contract(ROOT, FORWARD_CONTRACT)
    tasks = selected_tasks(ROOT, contract)
    parent = read(ROOT / PARENT_DIAGNOSIS)
    if (
        parent.get("role") != "v24674_v24671_information_gain_no_go_diagnosis"
        or not sealed(parent, "diagnosis_payload_sha256")
        or parent.get("authorization", {}).get(
            "label_blind_full_visible_question_coverage_audit"
        )
        is not True
        or parent.get("authorization", {}).get("dev64") is not False
        or parent.get("authorization", {}).get("exact220") is not False
    ):
        raise RuntimeError("V2.46.76 parent diagnosis drifted")

    old_widths: Counter[int] = Counter()
    new_widths: Counter[int] = Counter()
    added_widths: Counter[int] = Counter()
    old_covered = new_covered = newly_covered = changed_existing = ror_visible = 0
    for task in tasks:
        if set(task) != {"opaque_id", "question"}:
            raise RuntimeError("V2.46.76 visible boundary drifted")
        question = task["question"]
        old = extract_robust_visible_columns(question)
        new = extract_expanded_visible_columns(question)
        old_widths[len(old)] += 1
        new_widths[len(new)] += 1
        old_covered += int(bool(old))
        new_covered += int(bool(new))
        if not old and new:
            newly_covered += 1
            added_widths[len(new)] += 1
        changed_existing += int(bool(old) and old != new)
        ror_visible += int(bool(ROR_VISIBLE_PATTERN.search(question)))

    old_histogram = _histogram(old_widths)
    new_histogram = _histogram(new_widths)
    added_histogram = _histogram(added_widths)
    findings: list[str] = []
    if len(tasks) != 220:
        findings.append("visible_task_denominator_drifted")
    if old_histogram != EXPECTED_OLD_WIDTHS:
        findings.append("frozen_parser_width_histogram_drifted")
    if new_histogram != EXPECTED_NEW_WIDTHS:
        findings.append("expanded_parser_width_histogram_drifted")
    if added_histogram != EXPECTED_ADDED_WIDTHS:
        findings.append("new_coverage_width_histogram_drifted")
    if (old_covered, new_covered, newly_covered, changed_existing) != (194, 215, 21, 0):
        findings.append("coverage_totals_drifted")
    if ror_visible != 0:
        findings.append("ror_visible_schema_coverage_drifted")

    value = {
        "artifact_version": 1,
        "role": "v24676_full220_visible_schema_coverage_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "v24674_diagnosis_sha256": sha256(ROOT / PARENT_DIAGNOSIS),
            "v24635_visible_forward_contract_sha256": sha256(ROOT / FORWARD_CONTRACT),
            "visible_manifest_sha256": sha256(ROOT / SOURCE_MANIFEST),
        },
        "coverage": {
            "fixed_visible_task_denominator": len(tasks),
            "frozen_parser_covered_task_count": old_covered,
            "expanded_parser_covered_task_count": new_covered,
            "newly_covered_task_count": newly_covered,
            "already_covered_task_changed_count": changed_existing,
            "remaining_no_unambiguous_explicit_schema_task_count": len(tasks)
            - new_covered,
            "frozen_parser_width_histogram": old_histogram,
            "expanded_parser_width_histogram": new_histogram,
            "newly_covered_width_histogram": added_histogram,
            "explicit_ror_namespace_task_count": ror_visible,
        },
        "interpretation": {
            "ror_structured_adapter_has_natural_visible_schema_coverage_on_full220": False,
            "expanded_visible_schema_has_nonzero_full220_reachability": True,
            "expanded_visible_schema_coverage_fraction": round(newly_covered / 220, 12),
            "expanded_parser_preserves_every_frozen_nonempty_parse": True,
            "coverage_is_quality_or_score_evidence": False,
            "coverage_authorizes_runtime_implementation_only": not findings,
            "fresh_dev64_or_exact220_authorized_by_coverage": False,
        },
        "source_policy": {
            "runtime_input_keys": ["opaque_id", "question"],
            "only_visible_manifest_read": True,
            "question_column_name_or_opaque_id_persisted_or_emitted": False,
            "mapping_category_split_gold_prediction_score_reward_or_evaluator_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "concurrency_safe_runtime_integration_implementation": not findings,
            "fresh_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v24676_full220_visible_schema_coverage_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("coverage", {}).get("newly_covered_task_count") != 21
        or copied.get("coverage", {}).get("already_covered_task_changed_count") != 0
        or copied.get("coverage", {}).get("explicit_ror_namespace_task_count") != 0
        or copied.get("authorization")
        != {
            "concurrency_safe_runtime_integration_implementation": True,
            "fresh_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.76 audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = validate_audit(build_audit())
    publish_new(ROOT / OUTPUT, audit)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": audit["audit_valid"],
                "old_covered": audit["coverage"]["frozen_parser_covered_task_count"],
                "new_covered": audit["coverage"]["expanded_parser_covered_task_count"],
                "newly_covered": audit["coverage"]["newly_covered_task_count"],
            },
            sort_keys=True,
        )
    )
