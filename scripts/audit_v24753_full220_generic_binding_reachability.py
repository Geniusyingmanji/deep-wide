#!/usr/bin/env python3
"""Label-blind exact-220 reachability audit for generic record binding.

The audit opens only the frozen ``{opaque_id, question}`` manifest through the
validated V2.46.35 visible-only contract.  It distinguishes code that can run
today from a conditional integration upper bound: V2.47.45 accepts only its
special ROR/DOI contracts, while earlier deterministic projectors recognize a
small subset of visible value-column kinds after a baseline table exists.

Only aggregate counts are published.  Questions, columns, opaque identifiers,
predictions, pages, and per-task decisions are never persisted or emitted.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24365_entity_segment_projection import (  # noqa: E402
    _column_kind,
)
from deepwide_agent.v24405_structured_label_projection import (  # noqa: E402
    YEAR_KINDS,
)
from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    FORWARD_CONTRACT,
    SOURCE_MANIFEST,
    selected_tasks,
    sha256,
    validate_forward_contract,
)
from deepwide_agent.v24675_expanded_visible_schema import (  # noqa: E402
    extract_expanded_visible_columns,
)
from deepwide_agent.v24745_cross_domain_adapters import (  # noqa: E402
    visible_contract,
)


DATE = "20260806"
OUTPUT = Path(
    f"results/v24753_full220_generic_binding_reachability_audit_v1_{DATE}.json"
)
PARENT_POSTAUDIT = Path(
    f"results/v24752_host_local_postresult_audit_v1_{DATE}.json"
)
SCHEMA_PARENT = Path(
    f"results/v24676_full220_visible_schema_coverage_audit_v1_{DATE}.json"
)
CURRENT_ADAPTER_SOURCE = Path(
    "src/deepwide_agent/v24745_cross_domain_adapters.py"
)
BINDER_SOURCE = Path("src/deepwide_agent/v24743_generic_record_binding.py")
YEAR_PROJECTOR_SOURCE = Path(
    "src/deepwide_agent/v24405_structured_label_projection.py"
)

EXPECTED_SCHEMA_WIDTHS = {
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
EXPECTED_KNOWN_VALUE_KIND_TASKS = {
    "city": 11,
    "country": 15,
    "elevation": 1,
    "founding_year": 5,
    "headquarters_city": 1,
    "launch_year": 2,
    "year": 23,
}
EXPECTED_KNOWN_VALUE_KIND_COLUMNS = {
    "city": 11,
    "country": 15,
    "elevation": 1,
    "founding_year": 5,
    "headquarters_city": 1,
    "launch_year": 2,
    "year": 29,
}
EXPECTED_KNOWN_COLUMN_HISTOGRAM = {"0": 168, "1": 43, "2": 7, "3": 1, "4": 1}
EXPECTED_YEAR_KIND_TASKS = {"founding_year": 5, "launch_year": 2, "year": 23}
EXPECTED_YEAR_KIND_COLUMNS = {"founding_year": 5, "launch_year": 2, "year": 29}
EXPECTED_YEAR_COLUMN_HISTOGRAM = {"0": 190, "1": 26, "2": 2, "3": 2}


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.53 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.53 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _histogram(values: Counter[int]) -> dict[str, int]:
    return {str(key): values[key] for key in sorted(values)}


def _kind_counts(values: Counter[str]) -> dict[str, int]:
    return {key: values[key] for key in sorted(values)}


def _forbidden_ast_accesses(path: Path) -> list[str]:
    """Reject evaluator-only mapping access without scanning data files."""

    privileged = {
        "answer",
        "answer_key",
        "category",
        "evaluator",
        "gold",
        "ground_truth",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        key: str | None = None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value.casefold()
        if key in privileged:
            findings.append(f"{path.name}:{node.lineno}:{key}")
    return sorted(findings)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    contract = validate_forward_contract(ROOT, FORWARD_CONTRACT)
    tasks = selected_tasks(ROOT, contract)
    parent = _read(ROOT / PARENT_POSTAUDIT)
    schema_parent = _read(ROOT / SCHEMA_PARENT)
    if (
        parent.get("role") != "v24747_cross_domain_postresult_audit"
        or parent.get("decision_status") != "cross_domain_mechanism_go"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or not _sealed(parent, "audit_payload_sha256")
        or parent.get("authorization", {}).get("paired_dev64_launch") is not False
        or parent.get("authorization", {}).get("exact220") is not False
    ):
        raise RuntimeError("V2.47.53 mechanism parent drifted")
    if (
        schema_parent.get("role")
        != "v24676_full220_visible_schema_coverage_audit"
        or schema_parent.get("audit_valid") is not True
        or schema_parent.get("findings") != []
        or not _sealed(schema_parent, "audit_payload_sha256")
        or schema_parent.get("coverage", {}).get(
            "expanded_parser_covered_task_count"
        )
        != 215
    ):
        raise RuntimeError("V2.47.53 visible-schema parent drifted")

    schema_widths: Counter[int] = Counter()
    known_column_histogram: Counter[int] = Counter()
    year_column_histogram: Counter[int] = Counter()
    known_kind_tasks: Counter[str] = Counter()
    known_kind_columns: Counter[str] = Counter()
    year_kind_tasks: Counter[str] = Counter()
    year_kind_columns: Counter[str] = Counter()
    current_modes: Counter[str] = Counter()
    schema_tasks = known_tasks = year_tasks = 0

    for task in tasks:
        if set(task) != {"opaque_id", "question"}:
            raise RuntimeError("V2.47.53 visible boundary drifted")
        try:
            current = visible_contract(task)
        except (KeyError, TypeError, ValueError):
            current = None
        if current is not None:
            current_modes[str(current["mode"])] += 1

        columns = extract_expanded_visible_columns(task["question"])
        schema_widths[len(columns)] += 1
        schema_tasks += int(bool(columns))
        kinds = [_column_kind(column) for column in columns[1:]]
        known = [str(kind) for kind in kinds if kind is not None]
        year = [kind for kind in known if kind in YEAR_KINDS]
        known_column_histogram[len(known)] += 1
        year_column_histogram[len(year)] += 1
        known_tasks += int(bool(known))
        year_tasks += int(bool(year))
        known_kind_columns.update(known)
        year_kind_columns.update(year)
        known_kind_tasks.update(set(known))
        year_kind_tasks.update(set(year))

    current_adapter_tasks = sum(current_modes.values())
    known_columns = sum(known_kind_columns.values())
    year_columns = sum(year_kind_columns.values())
    findings: list[str] = []
    if len(tasks) != 220:
        findings.append("visible_task_denominator_drifted")
    if _histogram(schema_widths) != EXPECTED_SCHEMA_WIDTHS or schema_tasks != 215:
        findings.append("expanded_visible_schema_coverage_drifted")
    if (
        _kind_counts(known_kind_tasks) != EXPECTED_KNOWN_VALUE_KIND_TASKS
        or _kind_counts(known_kind_columns) != EXPECTED_KNOWN_VALUE_KIND_COLUMNS
        or _histogram(known_column_histogram) != EXPECTED_KNOWN_COLUMN_HISTOGRAM
        or (known_tasks, known_columns) != (52, 64)
    ):
        findings.append("conditional_known_value_kind_coverage_drifted")
    if (
        _kind_counts(year_kind_tasks) != EXPECTED_YEAR_KIND_TASKS
        or _kind_counts(year_kind_columns) != EXPECTED_YEAR_KIND_COLUMNS
        or _histogram(year_column_histogram) != EXPECTED_YEAR_COLUMN_HISTOGRAM
        or (year_tasks, year_columns) != (30, 36)
    ):
        findings.append("conditional_year_record_coverage_drifted")
    if current_adapter_tasks != 0 or current_modes:
        findings.append("current_adapter_executable_coverage_drifted")
    accesses = _forbidden_ast_accesses(Path(__file__))
    if accesses:
        findings.append("label_blind_ast_failed")

    value = {
        "artifact_version": 1,
        "role": "v24753_full220_generic_binding_reachability_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "v24752_postresult_audit_sha256": sha256(ROOT / PARENT_POSTAUDIT),
            "v24676_schema_coverage_audit_sha256": sha256(ROOT / SCHEMA_PARENT),
            "v24635_visible_forward_contract_sha256": sha256(
                ROOT / FORWARD_CONTRACT
            ),
            "visible_manifest_sha256": sha256(ROOT / SOURCE_MANIFEST),
        },
        "implementation_bindings": {
            "generic_binder_sha256": sha256(ROOT / BINDER_SOURCE),
            "current_cross_domain_adapter_sha256": sha256(
                ROOT / CURRENT_ADAPTER_SOURCE
            ),
            "conditional_year_projector_sha256": sha256(
                ROOT / YEAR_PROJECTOR_SOURCE
            ),
        },
        "coverage": {
            "fixed_visible_task_denominator": len(tasks),
            "expanded_visible_schema_task_count": schema_tasks,
            "expanded_visible_schema_width_histogram": _histogram(schema_widths),
            "current_v24745_executable_task_count": current_adapter_tasks,
            "current_v24745_mode_counts": _kind_counts(current_modes),
            "conditional_known_value_kind_task_count": known_tasks,
            "conditional_known_value_kind_column_count": known_columns,
            "conditional_known_value_kind_task_counts": _kind_counts(
                known_kind_tasks
            ),
            "conditional_known_value_kind_column_counts": _kind_counts(
                known_kind_columns
            ),
            "conditional_known_column_count_histogram": _histogram(
                known_column_histogram
            ),
            "conditional_exact_year_record_task_count": year_tasks,
            "conditional_exact_year_record_column_count": year_columns,
            "conditional_exact_year_record_task_counts": _kind_counts(
                year_kind_tasks
            ),
            "conditional_exact_year_record_column_counts": _kind_counts(
                year_kind_columns
            ),
            "conditional_exact_year_column_count_histogram": _histogram(
                year_column_histogram
            ),
        },
        "decision": {
            "current_adapter_has_nonzero_exact220_executable_coverage": False,
            "current_adapter_can_enter_dev64_or_exact220": False,
            "conditional_counts_are_trigger_quality_or_score_evidence": False,
            "conditional_counts_assume_baseline_rows_and_fetched_pages_are_available": True,
            "conditional_counts_prove_structured_records_will_be_found": False,
            "zero_additional_model_search_or_fetch_effect_integration_is_required": True,
            "ordinary_records_still_require_two_registrably_independent_sources": True,
            "next_external_gate_must_show_nonzero_exact_record_binding": True,
            "status": "generic_binding_transfer_no_go_before_integration",
        },
        "source_policy": {
            "runtime_input_keys": ["opaque_id", "question"],
            "only_visible_manifest_and_sealed_aggregate_parents_read": True,
            "aggregate_counts_only": True,
            "question_column_opaque_id_or_per_task_decision_persisted_or_emitted": False,
            "mapping_category_split_gold_prediction_page_score_reward_or_evaluator_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "label_blind_ast_accesses": accesses,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "zero_additional_effect_integration_design": not findings,
            "fresh_external_protocol_or_launch": False,
            "paired_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    coverage = copied.get("coverage", {})
    decision = copied.get("decision", {})
    if (
        copied.get("role")
        != "v24753_full220_generic_binding_reachability_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or coverage.get("fixed_visible_task_denominator") != 220
        or coverage.get("expanded_visible_schema_task_count") != 215
        or coverage.get("current_v24745_executable_task_count") != 0
        or coverage.get("current_v24745_mode_counts") != {}
        or coverage.get("conditional_known_value_kind_task_count") != 52
        or coverage.get("conditional_known_value_kind_column_count") != 64
        or coverage.get("conditional_exact_year_record_task_count") != 30
        or coverage.get("conditional_exact_year_record_column_count") != 36
        or decision.get("status")
        != "generic_binding_transfer_no_go_before_integration"
        or decision.get("current_adapter_can_enter_dev64_or_exact220") is not False
        or decision.get("conditional_counts_are_trigger_quality_or_score_evidence")
        is not False
        or copied.get("source_policy", {}).get("label_blind_ast_accesses") != []
        or copied.get("authorization")
        != {
            "zero_additional_effect_integration_design": True,
            "fresh_external_protocol_or_launch": False,
            "paired_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.53 reachability audit drifted")
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
                "current_executable": audit["coverage"][
                    "current_v24745_executable_task_count"
                ],
                "conditional_year_tasks": audit["coverage"][
                    "conditional_exact_year_record_task_count"
                ],
                "status": audit["decision"]["status"],
            },
            sort_keys=True,
        )
    )
