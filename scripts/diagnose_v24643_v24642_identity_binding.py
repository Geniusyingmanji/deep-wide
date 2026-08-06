#!/usr/bin/env python3
"""Post-freeze diagnosis of V2.46.42's single incorrect pair admission."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24639_ror_objective_runtime import _matrix  # noqa: E402
from deepwide_agent.v24642_deterministic_pair_runtime import validate_result  # noqa: E402
from deepwide_agent.v24642_ror_external_contract import (  # noqa: E402
    DATE,
    FORWARD_AUDIT,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    sha256,
)
from deepwide_agent.v24642_ror_external_evaluator import (  # noqa: E402
    GOLD,
    gold_rows,
)


RESULT = Path(f"results/v24642_deterministic_pair_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24642_deterministic_pair_postresult_audit_v1_{DATE}.json")
PRIOR_GOLD = Path("evaluation/v24639_ror_gold_v1.csv")
OUTPUT = Path(f"results/v24643_v24642_identity_binding_diagnosis_v1_{DATE}.json")


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.43 diagnosis expected object")
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
        raise RuntimeError("V2.46.43 diagnosis parent drifted")
    current_gold = gold_rows((ROOT / GOLD).read_text(encoding="utf-8"))
    current_by_task: dict[str, list[dict[str, str]]] = {}
    for row in current_gold:
        current_by_task.setdefault(row["opaque_id"], []).append(row)
    prior_rows = list(csv.DictReader((ROOT / PRIOR_GOLD).open(encoding="utf-8")))
    prior_by_ror = {norm_ror(row["ROR ID"]): row for row in prior_rows}

    changed = correct = incorrect = historical_other_identity = 0
    unknown_before = unknown_after = 0
    changed_task_count = 0
    for index in range(1, SELECTED_COUNT + 1):
        task = validate_result(read(ROOT / TASK_ROOT / f"task_{index:04d}" / "result.json"))
        _columns, baseline = _matrix(task["predictions"]["baseline"])
        _columns, candidate = _matrix(task["predictions"]["deterministic_pair"])
        expected = current_by_task[task["opaque_id"]]
        task_changed = False
        for before, after, gold in zip(baseline, candidate, expected, strict=True):
            unknown_before += int(before[1].casefold() == "unknown")
            unknown_after += int(after[1].casefold() == "unknown")
            if before[1] == after[1]:
                continue
            task_changed = True
            changed += 1
            is_correct = norm_ror(after[1]) == norm_ror(gold["ROR ID"])
            correct += int(is_correct)
            incorrect += int(not is_correct)
            prior = prior_by_ror.get(norm_ror(after[1]))
            historical_other_identity += int(
                prior is not None
                and norm(prior["Organization"]) != norm(gold["Organization"])
            )
        changed_task_count += int(task_changed)
    if (
        changed != 1
        or changed_task_count != 1
        or correct != 0
        or incorrect != 1
        or historical_other_identity != 1
        or unknown_before - unknown_after != 1
    ):
        raise RuntimeError("V2.46.43 identity-binding aggregate drifted")
    metrics = result["metrics"]
    value = {
        "artifact_version": 1,
        "role": "v24643_v24642_identity_binding_postfreeze_diagnosis",
        "created_at_unix": int(time.time()),
        "parents": {
            "result_sha256": sha256(ROOT / RESULT),
            "postresult_audit_sha256": sha256(ROOT / POSTAUDIT),
            "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        },
        "quality": {
            "baseline_exact_table_successes": metrics["arms"]["baseline"][
                "exact_table_successes"
            ],
            "candidate_exact_table_successes": metrics["arms"]["deterministic_pair"][
                "exact_table_successes"
            ],
            "baseline_item_f1": metrics["arms"]["baseline"]["item_f1"],
            "candidate_item_f1": metrics["arms"]["deterministic_pair"]["item_f1"],
            "baseline_composite": metrics["arms"]["baseline"]["composite"],
            "candidate_composite": metrics["arms"]["deterministic_pair"]["composite"],
        },
        "admission_outcome": {
            "changed_task_count": changed_task_count,
            "changed_ror_cell_count": changed,
            "correct_admission_count": correct,
            "incorrect_admission_count": incorrect,
            "unknown_cell_reduction": unknown_before - unknown_after,
            "incorrect_candidate_is_known_prior_ror_for_different_identity_count": historical_other_identity,
        },
        "diagnosis": {
            "mechanism_naturally_triggered": True,
            "trigger_improved_task_utility": False,
            "official_ror_url_plus_body_entity_mention_establishes_page_primary_identity": False,
            "body_entity_mention_can_encode_affiliation_or_relationship": True,
            "page_primary_identity_binding_is_missing": True,
            "more_search_or_looser_pair_radius_supported": False,
        },
        "credit": {
            "pair_information_was_addressable": True,
            "verified_outer_utility_delta_positive": False,
            "admitted_step_positive_task_credit_allowed": False,
            "entropy_or_novelty_signal_can_override_wrong_identity": False,
        },
        "next_falsification": {
            "population": "fresh_and_literal_canonical_disjoint",
            "treatment": "title_or_structured_primary_identity_bound_explicit_ror_pair",
            "body_only_identity_binding_removed": True,
            "binding_type_counts_persisted_content_free": True,
            "nonunknown_ror_and_all_country_cells_immutable": True,
            "same_population_resume_retry_or_selective_rerun": False,
            "primary_gate": "strict_exact_table_gain",
            "guardrails": ["composite_nonnegative_delta", "item_f1_nonnegative_delta"],
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


if __name__ == "__main__":
    value = build()
    publish(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "diagnosis_sha256": value["diagnosis_sha256"]}, sort_keys=True))
