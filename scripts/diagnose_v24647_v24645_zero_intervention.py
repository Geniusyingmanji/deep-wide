#!/usr/bin/env python3
"""Post-freeze aggregate diagnosis of V2.46.45's zero intervention."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24639_ror_objective_runtime import _matrix  # noqa: E402
from deepwide_agent.v24640_evidence_constrained_runtime import UNKNOWN  # noqa: E402
from deepwide_agent.v24644_primary_identity_pair_runtime import (  # noqa: E402
    validate_result,
)
from deepwide_agent.v24645_ror_external_contract import (  # noqa: E402
    DATE,
    FORWARD_AUDIT,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    sha256,
)
from deepwide_agent.v24645_ror_external_evaluator import (  # noqa: E402
    GOLD,
    gold_rows,
)


RESULT = Path(f"results/v24645_primary_identity_pair_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24645_primary_identity_pair_postresult_audit_v1_{DATE}.json"
)
OUTPUT = Path(
    f"results/v24647_v24645_zero_intervention_diagnosis_v1_{DATE}.json"
)


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.47 diagnosis expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.47 diagnosis expected object")
    return value


def sealed(value: dict[str, Any], field: str) -> bool:
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


def clean() -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=20,
        ).stdout.strip()

    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.47 diagnosis requires clean HEAD == target/main")


def build(*, now: int | None = None) -> dict[str, Any]:
    result = read(ROOT / RESULT)
    post = read(ROOT / POSTAUDIT)
    forward_audit = read(ROOT / FORWARD_AUDIT)
    if (
        not sealed(result, "result_sha256")
        or not sealed(post, "audit_sha256")
        or not sealed(forward_audit, "audit_sha256")
        or result.get("passed") is not False
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or forward_audit.get("audit_valid") is not True
        or forward_audit.get("findings") != []
    ):
        raise RuntimeError("V2.46.47 diagnosis parent drifted")

    metrics = result.get("metrics", {})
    arms = metrics.get("arms", {}) if isinstance(metrics, dict) else {}
    expected_arm = {
        "tasks": 12,
        "exact_table_successes": 0,
        "entity_recall": 1.0,
        "row_f1": 1.0,
        "item_f1": 0.625,
        "column_f1": 1.0,
        "composite": 0.90625,
        "unknown_value_cells": 35,
    }
    if (
        arms != {
            "baseline": expected_arm,
            "deterministic_pair": expected_arm,
        }
        or metrics.get("gate_passed") is not False
        or any(
            float(value) != 0.0
            for value in metrics.get("candidate_minus_baseline", {}).values()
        )
    ):
        raise RuntimeError("V2.46.47 quality aggregate drifted")

    gold = gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    gold_by_task: dict[str, list[dict[str, str]]] = {}
    for row in gold:
        gold_by_task.setdefault(row["opaque_id"], []).append(row)

    ror_states: Counter[str] = Counter()
    country_states: Counter[str] = Counter()
    discovery: Counter[str] = Counter()
    identical_prediction_tasks = 0
    exact_recoverable_under_unknown_only = 0
    tasks_blocked_by_incorrect_nonempty_ror = 0
    discovery_fields = (
        "model_visible_page_count",
        "page_with_any_explicit_ror_count",
        "official_api_page_count",
        "entity_page_hit_count",
        "unique_page_pair_hit_count",
        "ambiguous_page_hit_count",
        "unknown_target_unique_pair_count",
        "unknown_target_ambiguous_pair_count",
        "unknown_target_no_pair_count",
        "admitted_replacement_count",
        "nonunknown_target_pair_count",
        "exact_title_identity_pair_count",
        "structured_primary_identity_pair_count",
        "body_only_identity_rejected_pair_count",
    )

    for index in range(1, SELECTED_COUNT + 1):
        task = validate_result(
            read(ROOT / TASK_ROOT / f"task_{index:04d}" / "result.json")
        )
        predictions = task["predictions"]
        identical_prediction_tasks += int(
            predictions["baseline"] == predictions["deterministic_pair"]
        )
        columns, predicted_rows = _matrix(predictions["baseline"])
        expected_rows = gold_by_task.get(task["opaque_id"], [])
        if (
            tuple(columns) != ("Organization", "ROR ID", "Country code")
            or len(predicted_rows) != 4
            or len(expected_rows) != 4
        ):
            raise RuntimeError("V2.46.47 task denominator drifted")
        task_ror_states = []
        task_country_states = []
        for predicted, expected in zip(predicted_rows, expected_rows, strict=True):
            if norm(predicted[0]) != norm(expected["Organization"]):
                raise RuntimeError("V2.46.47 identity alignment drifted")
            ror_state = fact_state(predicted[1], expected["ROR ID"], ror=True)
            country_state = fact_state(
                predicted[2], expected["Country code"], ror=False
            )
            ror_states[ror_state] += 1
            country_states[country_state] += 1
            task_ror_states.append(ror_state)
            task_country_states.append(country_state)
        exact_recoverable_under_unknown_only += int(
            "unknown" in task_ror_states
            and "incorrect" not in task_ror_states
            and set(task_country_states) == {"correct"}
        )
        tasks_blocked_by_incorrect_nonempty_ror += int(
            "incorrect" in task_ror_states
        )
        receipt = task["receipt"]
        for field in discovery_fields:
            discovery[field] += int(receipt["discovery"][field])

    expected_discovery = {
        "model_visible_page_count": 108,
        "page_with_any_explicit_ror_count": 45,
        "official_api_page_count": 37,
        "entity_page_hit_count": 41,
        "unique_page_pair_hit_count": 3,
        "ambiguous_page_hit_count": 0,
        "unknown_target_unique_pair_count": 0,
        "unknown_target_ambiguous_pair_count": 0,
        "unknown_target_no_pair_count": 35,
        "admitted_replacement_count": 0,
        "nonunknown_target_pair_count": 3,
        "exact_title_identity_pair_count": 0,
        "structured_primary_identity_pair_count": 3,
        "body_only_identity_rejected_pair_count": 12,
    }
    if (
        identical_prediction_tasks != SELECTED_COUNT
        or ror_states != {"correct": 12, "incorrect": 1, "unknown": 35}
        or country_states != {"correct": 48}
        or dict(discovery) != expected_discovery
        or exact_recoverable_under_unknown_only != 11
        or tasks_blocked_by_incorrect_nonempty_ror != 1
        or forward_audit.get("checks", {})
        != {
            **expected_discovery,
            "terminal_tasks": 12,
            "terminal_arm_predictions": 24,
            "model_slot_acquisitions": 24,
            "model_slot_timeouts": 0,
            "predictions_frozen_before_gold_open": True,
            "gold_or_provenance_opened_or_hashed_by_audit": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        }
    ):
        raise RuntimeError("V2.46.47 aggregate mechanism drifted")

    value = {
        "artifact_version": 1,
        "role": "v24647_v24645_zero_intervention_postfreeze_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result_sha256": sha256(ROOT / RESULT),
            "postresult_audit_sha256": sha256(ROOT / POSTAUDIT),
            "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        },
        "quality": {
            "tasks_per_arm": 12,
            "baseline_exact_table_successes": 0,
            "candidate_exact_table_successes": 0,
            "baseline_item_f1": 0.625,
            "candidate_item_f1": 0.625,
            "baseline_composite": 0.90625,
            "candidate_composite": 0.90625,
            "candidate_minus_baseline_exact_table_successes": 0,
            "candidate_minus_baseline_item_f1": 0.0,
            "candidate_minus_baseline_composite": 0.0,
        },
        "mechanism": dict(discovery),
        "baseline_fact_state_counts": {
            "ror": dict(ror_states),
            "country": dict(country_states),
            "tasks_recoverable_if_all_ror_unknowns_were_safely_filled": exact_recoverable_under_unknown_only,
            "tasks_also_requiring_nonempty_ror_correction": tasks_blocked_by_incorrect_nonempty_ror,
        },
        "diagnosis": {
            "strict_identity_gate_naturally_found_structured_pairs": True,
            "structured_pairs_targeted_baseline_unknown_cells": False,
            "all_structured_pairs_targeted_baseline_nonunknown_cells": True,
            "candidate_changed_any_prediction": False,
            "candidate_received_an_effective_treatment": False,
            "body_only_pairs_were_rejected": True,
            "zero_delta_estimates_identity_gate_safety": False,
            "zero_delta_estimates_quality_of_correct_unknown_fills": False,
            "current_bottleneck_is_unknown_target_structured_pair_acquisition": True,
            "more_unconditional_pages_supported": False,
        },
        "credit": {
            "candidate_incremental_outer_utility": 0.0,
            "candidate_positive_task_credit_allowed": False,
            "identity_binding_is_required_before_information_gain": True,
            "identity_binding_without_unknown_target_intervention_earns_task_credit": False,
            "entropy_or_credit_assignment_validated": False,
        },
        "next_falsification": {
            "population": "fresh_and_literal_canonical_disjoint",
            "treatment": "unknown_target_directed_structured_primary_identity_acquisition",
            "strong_baseline": "deterministic_official_registry_name_lookup_when_available",
            "same_total_model_query_fetch_budget": True,
            "unconditional_page_volume_increase": False,
            "nonunknown_ror_and_all_country_cells_remain_immutable": True,
            "separate_nonempty_correction_experiment_required": True,
            "same_population_resume_retry_or_selective_rerun": False,
            "mechanism_gate": "at_least_one_identity_bound_unknown_target_intervention",
            "primary_quality_gate": "strict_exact_table_gain",
            "guardrails": [
                "composite_nonnegative_delta",
                "item_f1_nonnegative_delta",
            ],
            "unknown_count_diagnostic_only": True,
        },
        "privacy": {
            "question_query_url_page_entity_value_prediction_or_credential_emitted": False,
            "aggregate_counts_only": True,
            "gold_opened_only_after_prediction_freeze": True,
            "diagnosis_feeds_back_into_v24645_forward": False,
        },
        "claim_scope": {
            "zero_intervention_localized": True,
            "identity_gate_precision_measured": False,
            "unknown_fill_quality_measured": False,
            "deepwidebench_quality_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "fresh_external_successor_design": True,
            "fresh_external_successor_launch": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_relative_to(Path("results")) or output != OUTPUT:
        raise ValueError("V2.46.47 diagnosis output drifted")
    clean()
    value = build()
    publish(ROOT / output, value)
    print(
        json.dumps(
            {
                "path": str(output),
                "diagnosis_sha256": value["diagnosis_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
