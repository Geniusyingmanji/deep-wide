#!/usr/bin/env python3
"""Post-freeze aggregate diagnosis of V2.46.40's zero-trigger result."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24639_ror_objective_runtime import _matrix  # noqa: E402
from deepwide_agent.v24640_evidence_constrained_runtime import (  # noqa: E402
    UNKNOWN,
    validate_result,
)
from deepwide_agent.v24640_ror_external_contract import (  # noqa: E402
    DATE,
    FORWARD_AUDIT,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    sha256,
)
from deepwide_agent.v24640_ror_external_evaluator import (  # noqa: E402
    GOLD,
    gold_rows,
)

RESULT = Path(f"results/v24640_evidence_constrained_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24640_evidence_constrained_postresult_audit_v1_{DATE}.json"
)
OUTPUT = Path(f"results/v24641_v24640_zero_trigger_diagnosis_v1_{DATE}.json")


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.41 diagnosis expected object")
    return value


def sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def norm_ror(value: object) -> str:
    raw = str(value).strip().casefold().rstrip("/")
    if raw.startswith("https://ror.org/"):
        raw = raw.rsplit("/", 1)[-1]
    return norm(raw)


def fact_state(value: str, expected: str, *, ror: bool) -> str:
    if value.strip().casefold() in UNKNOWN:
        return "unknown"
    normalizer = norm_ror if ror else norm
    return "correct" if normalizer(value) == normalizer(expected) else "incorrect"


def build() -> dict:
    result = read(ROOT / RESULT)
    post = read(ROOT / POSTAUDIT)
    forward_audit = read(ROOT / FORWARD_AUDIT)
    if (
        not sealed(result, "result_sha256")
        or not sealed(post, "audit_sha256")
        or not sealed(forward_audit, "audit_sha256")
        or result.get("passed") is not False
        or post.get("audit_valid") is not True
        or forward_audit.get("audit_valid") is not True
    ):
        raise RuntimeError("V2.46.41 diagnosis parent drifted")
    gold = gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    gold_by_task: dict[str, list[dict[str, str]]] = {}
    for row in gold:
        gold_by_task.setdefault(row["opaque_id"], []).append(row)

    totals = Counter()
    ror_states = Counter()
    country_states = Counter()
    exact_recoverable_under_unknown_only = 0
    for index in range(1, SELECTED_COUNT + 1):
        task_result = validate_result(read(ROOT / TASK_ROOT / f"task_{index:04d}" / "result.json"))
        receipt = task_result["receipt"]
        revision = receipt["revision"]
        for key in (
            "admitted_search_queries",
            "admitted_fetch_targets",
            "search_batch_count",
            "usable_page_count",
            "recoverable_failure_count",
        ):
            totals[key] += int(receipt[key])
        for key in (
            "raw_declaration_count",
            "well_formed_declaration_count",
            "supported_declaration_count",
            "admitted_replacement_count",
            "conflicting_target_count",
            "nonunknown_target_proposal_count",
        ):
            totals[key] += int(revision[key])
        columns, predicted_rows = _matrix(task_result["predictions"]["baseline"])
        if len(columns) != 3 or len(predicted_rows) != 4:
            raise RuntimeError("V2.46.41 baseline matrix drifted")
        expected_rows = gold_by_task[task_result["opaque_id"]]
        task_ror_states = []
        task_country_states = []
        for predicted, expected in zip(predicted_rows, expected_rows, strict=True):
            if norm(predicted[0]) != norm(expected["Organization"]):
                raise RuntimeError("V2.46.41 identity alignment drifted")
            ror_state = fact_state(predicted[1], expected["ROR ID"], ror=True)
            country_state = fact_state(
                predicted[2], expected["Country code"], ror=False
            )
            ror_states[ror_state] += 1
            country_states[country_state] += 1
            task_ror_states.append(ror_state)
            task_country_states.append(country_state)
        exact_recoverable_under_unknown_only += int(
            "incorrect" not in task_ror_states
            and "incorrect" not in task_country_states
            and "unknown" not in task_country_states
        )

    expected_totals = {
        "admitted_search_queries": 48,
        "admitted_fetch_targets": 120,
        "search_batch_count": 12,
        "usable_page_count": 113,
        "recoverable_failure_count": 0,
        "raw_declaration_count": 0,
        "well_formed_declaration_count": 0,
        "supported_declaration_count": 0,
        "admitted_replacement_count": 0,
        "conflicting_target_count": 0,
        "nonunknown_target_proposal_count": 0,
    }
    if dict(totals) != expected_totals:
        raise RuntimeError("V2.46.41 aggregate mechanism count drifted")
    if ror_states != {"correct": 11, "incorrect": 16, "unknown": 21}:
        raise RuntimeError("V2.46.41 ROR state count drifted")
    if country_states != {"correct": 44, "incorrect": 4}:
        raise RuntimeError("V2.46.41 country state count drifted")
    if exact_recoverable_under_unknown_only != 3:
        raise RuntimeError("V2.46.41 recoverable-task count drifted")

    value = {
        "artifact_version": 1,
        "role": "v24641_v24640_zero_trigger_postfreeze_diagnosis",
        "created_at_unix": int(time.time()),
        "parents": {
            "result_sha256": sha256(ROOT / RESULT),
            "postresult_audit_sha256": sha256(ROOT / POSTAUDIT),
            "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        },
        "quality": {
            "baseline_exact_table_successes": 1,
            "candidate_exact_table_successes": 1,
            "baseline_item_f1": 0.5729166666666666,
            "candidate_item_f1": 0.5729166666666666,
            "baseline_composite": 0.8932291666666666,
            "candidate_composite": 0.8932291666666666,
            "candidate_minus_baseline_exact_table_successes": 0,
            "candidate_minus_baseline_composite": 0.0,
        },
        "mechanism": dict(totals),
        "baseline_fact_state_counts": {
            "ror": dict(ror_states),
            "country": dict(country_states),
            "tasks_without_incorrect_nonunknown_fact_and_with_only_ror_unknowns": exact_recoverable_under_unknown_only,
        },
        "diagnosis": {
            "network_or_slot_failure_explains_zero_trigger": False,
            "dependent_revision_emitted_zero_raw_declarations": True,
            "deterministic_gate_observed_a_supported_declaration": False,
            "deterministic_gate_rejected_a_supported_declaration": False,
            "usable_page_count_proves_exact_entity_ror_pair_support": False,
            "exact_pair_support_presence_identifiable_from_content_free_artifacts": False,
            "zero_trigger_identifies_model_abstention_vs_support_absence": False,
            "unknown_only_monotonicity_cannot_repair_16_incorrect_nonunknown_ror_cells": True,
        },
        "next_falsification": {
            "population": "fresh_and_literal_canonical_disjoint",
            "treatment": "deterministic_model_visible_exact_pair_discovery_before_model_declaration",
            "persist_content_free_exact_pair_available_ambiguous_and_admitted_counts": True,
            "nonunknown_ror_and_all_country_cells_remain_immutable": True,
            "same_total_model_query_fetch_budget": True,
            "same_population_resume_retry_or_selective_rerun": False,
            "primary_gate": "strict_exact_table_gain",
            "guardrails": ["composite_nonnegative_delta", "item_f1_nonnegative_delta"],
            "unknown_count_diagnostic_only": True,
        },
        "privacy": {
            "question_query_url_page_entity_value_prediction_or_credential_emitted": False,
            "aggregate_counts_only": True,
            "gold_opened_only_after_prediction_freeze": True,
        },
        "claim_scope": {
            "mechanism_failure_localized": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "fresh_external_successor_design": True,
            "fresh_external_successor_launch": False,
            "dev64": False,
            "exact220": False,
        },
    }
    value["diagnosis_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_relative_to(Path("results")) or output != OUTPUT:
        raise ValueError("V2.46.41 diagnosis output drifted")
    value = build()
    publish(ROOT / output, value)
    print(json.dumps({"path": str(output), "diagnosis_sha256": value["diagnosis_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
