#!/usr/bin/env python3
"""Aggregate-only history-disjointness selector for the V2.52.13 population.

The caller supplies exactly sixteen identities for each frozen external risk
stratum.  Identities are used only as local Git pickaxe inputs and are never
printed or persisted individually.  The artifact contains one ordered-vector
hash plus aggregate per-stratum counts.  It does not attest how candidates
were discovered and grants no population freeze, runtime, or external effect.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v25141_population_selection as base  # noqa: E402
from scripts import design_v25211_receipt_reliability_gate as design  # noqa: E402


ROLE = "v25213_receipt_reliability_population_selection_aggregate_audit"
RISK_STRATA = design.RISK_STRATA
TASKS_PER_STRATUM = design.TASKS_PER_STRATUM
TASK_COUNT = design.TASK_COUNT
HISTORY_PATHS = (
    "src",
    "evaluation",
    "scripts",
    "tests",
    "results",
    "outputs",
)
payload_sha256 = base.payload_sha256


def _normalize(value: object) -> str:
    return "-".join(str(value).casefold().split())


def _validate_candidates(
    candidates: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    if not isinstance(candidates, Mapping) or set(candidates) != set(RISK_STRATA):
        raise RuntimeError("V2.52.13 risk-stratum set drifted")
    normalized: dict[str, tuple[str, ...]] = {}
    all_identities: list[str] = []
    for stratum in RISK_STRATA:
        values = candidates.get(stratum)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise RuntimeError("V2.52.13 stratum identity vector drifted")
        rows = tuple(_normalize(value) for value in values)
        if (
            len(rows) != TASKS_PER_STRATUM
            or len(set(rows)) != TASKS_PER_STRATUM
            or any(not value or len(value) > 100 for value in rows)
        ):
            raise RuntimeError("V2.52.13 stratum identity vector drifted")
        normalized[stratum] = rows
        all_identities.extend(rows)
    if len(all_identities) != TASK_COUNT or len(set(all_identities)) != TASK_COUNT:
        raise RuntimeError("V2.52.13 global identity vector drifted")
    return normalized


def _resolve_parent(parent_commit: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--verify", parent_commit + "^{commit}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _history_hits(identity: str, *, parent_commit: str) -> int:
    completed = subprocess.run(
        [
            "git",
            "log",
            parent_commit,
            "-i",
            "-S",
            identity,
            "--format=%H",
            "--",
            *HISTORY_PATHS,
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    )
    return sum(bool(line.strip()) for line in completed.stdout.splitlines())


def build_audit(
    candidates: Mapping[str, Sequence[str]],
    *,
    parent_commit: str,
    now: int | None = None,
) -> dict[str, Any]:
    normalized = _validate_candidates(candidates)
    resolved = _resolve_parent(parent_commit)
    ordered = [
        identity
        for stratum in RISK_STRATA
        for identity in normalized[stratum]
    ]
    hits: dict[str, list[int]] = {
        stratum: [
            _history_hits(identity, parent_commit=resolved)
            for identity in normalized[stratum]
        ]
        for stratum in RISK_STRATA
    }
    total_hits = sum(sum(rows) for rows in hits.values())
    zero_counts = {
        stratum: sum(count == 0 for count in hits[stratum])
        for stratum in RISK_STRATA
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_commit": resolved,
        "risk_strata": list(RISK_STRATA),
        "tasks_per_stratum": TASKS_PER_STRATUM,
        "identity_count": len(ordered),
        "unique_identity_count": len(set(ordered)),
        "stratum_identity_counts": {
            stratum: len(normalized[stratum]) for stratum in RISK_STRATA
        },
        "ordered_identity_vector_sha256": payload_sha256(ordered),
        "identity_history_introduction_hit_total": total_hits,
        "identity_history_zero_hit_count": sum(zero_counts.values()),
        "stratum_identity_history_zero_hit_counts": zero_counts,
        "selection_uses_local_repository_history_only": True,
        "candidate_preselection_provenance_attested_by_selector": False,
        "identity_plaintext_item_hash_or_stratum_identity_mapping_persisted": False,
        "endpoint_page_value_question_prediction_or_evidence_persisted": False,
        "risk_stratum_passed_as_hidden_runtime_input_or_router_signal": False,
        "identity_is_future_visible_task_input_not_hidden_mapping": True,
        "selection_script_network_model_search_fetch_or_evaluator_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "prior_external_or_deepwidebench_population_reuse": False,
        "population_frozen_or_external_protocol_authorized": False,
        "retry_resume_replacement_selective_rerun_or_revaluation_authorized": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "findings": [] if total_hits == 0 else ["identity_history_not_disjoint"],
        "audit_valid": total_hits == 0,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    expected_counts = {stratum: TASKS_PER_STRATUM for stratum in RISK_STRATA}
    true_flags = (
        "selection_uses_local_repository_history_only",
        "identity_is_future_visible_task_input_not_hidden_mapping",
    )
    false_flags = (
        "candidate_preselection_provenance_attested_by_selector",
        "identity_plaintext_item_hash_or_stratum_identity_mapping_persisted",
        "endpoint_page_value_question_prediction_or_evidence_persisted",
        "risk_stratum_passed_as_hidden_runtime_input_or_router_signal",
        "selection_script_network_model_search_fetch_or_evaluator_called",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "prior_external_or_deepwidebench_population_reuse",
        "population_frozen_or_external_protocol_authorized",
        "retry_resume_replacement_selective_rerun_or_revaluation_authorized",
        "entropy_or_information_gain_assigns_signed_credit",
    )
    vector_hash = copied.get("ordered_identity_vector_sha256")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("risk_strata") != list(RISK_STRATA)
        or copied.get("tasks_per_stratum") != TASKS_PER_STRATUM
        or copied.get("identity_count") != TASK_COUNT
        or copied.get("unique_identity_count") != TASK_COUNT
        or copied.get("stratum_identity_counts") != expected_counts
        or not isinstance(vector_hash, str)
        or len(vector_hash) != 64
        or copied.get("identity_history_introduction_hit_total") != 0
        or copied.get("identity_history_zero_hit_count") != TASK_COUNT
        or copied.get("stratum_identity_history_zero_hit_counts")
        != expected_counts
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.52.13 population selection audit drifted")
    return copied


def _parse_candidates(values: Sequence[str]) -> dict[str, list[str]]:
    output = {stratum: [] for stratum in RISK_STRATA}
    for raw in values:
        stratum, separator, identity = str(raw).partition("=")
        if not separator or stratum not in output or not identity:
            raise RuntimeError("V2.52.13 candidate argument drifted")
        output[stratum].append(identity)
    return output


def main() -> None:
    command = argparse.ArgumentParser()
    command.add_argument("--parent", required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--candidate", action="append", required=True)
    args = command.parse_args()
    value = build_audit(
        _parse_candidates(args.candidate),
        parent_commit=args.parent,
    )
    base.publish_exclusive(ROOT / args.output, value)
    print(
        json.dumps(
            {
                "path": str(args.output),
                "identity_count": value["identity_count"],
                "history_hits": value["identity_history_introduction_hit_total"],
                "audit_valid": value["audit_valid"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
