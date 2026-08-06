#!/usr/bin/env python3
"""Freeze a transport-outcome-blind population for resilience testing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24737_dual_namespace_reachability_gate as seal  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24739_fresh_resilience_population_design_v1_{DATE}.json")
PARENT = Path(f"results/v24738_v24737_failure_domain_diagnosis_v1_{DATE}.json")
PRE_OUTCOME_COMMIT = "1c798a0d9462c3bc44becd2c27bff7ae1bd8745a"
SELECTED_COUNT = 2
CANDIDATES = (
    ("Access to electricity (% of population)", "EG.ELC.ACCS.ZS", "2022"),
    ("People using at least basic drinking water services (% of population)", "SH.H2O.BASW.ZS", "2022"),
    ("People using at least basic sanitation services (% of population)", "SH.STA.BASS.ZS", "2022"),
    ("Unemployment, total (% of total labor force)", "SL.UEM.TOTL.ZS", "2023"),
)
_INDICATOR = re.compile(r"[A-Z][A-Z0-9.]{4,40}")
_YEAR = re.compile(r"20[0-3][0-9]")


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=check,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _candidate_rows(
    candidates: Sequence[tuple[str, str, str]] = CANDIDATES,
) -> list[dict[str, Any]]:
    rows = []
    for label, indicator, year in candidates:
        key = f"{indicator}@{year}"
        if (
            not isinstance(label, str)
            or not label.strip()
            or _INDICATOR.fullmatch(indicator) is None
            or _YEAR.fullmatch(year) is None
        ):
            raise ValueError("V2.47.39 candidate drifted")
        completed = _git(
            "grep",
            "--fixed-strings",
            "--name-only",
            key,
            PRE_OUTCOME_COMMIT,
            "--",
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError("V2.47.39 git absence proof failed")
        paths = [line for line in completed.stdout.decode("utf-8").splitlines() if line]
        rows.append(
            {
                "indicator": indicator,
                "year": year,
                "target_key": key,
                "label_sha256": hashlib.sha256(label.encode()).hexdigest(),
                "pre_outcome_tracked_path_occurrences": len(paths),
                "pre_outcome_tracked_paths_sha256": seal.payload_sha256(sorted(paths)),
            }
        )
    rows.sort(key=lambda item: item["target_key"])
    if len(rows) != len(CANDIDATES) or len({row["target_key"] for row in rows}) != len(rows):
        raise ValueError("V2.47.39 candidate vector drifted")
    return rows


def select_targets(
    candidates: Sequence[tuple[str, str, str]] = CANDIDATES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = _candidate_rows(candidates)
    if any(row["pre_outcome_tracked_path_occurrences"] != 0 for row in rows):
        raise ValueError("V2.47.39 candidate was already present before selection")
    return rows, [dict(row) for row in rows[:SELECTED_COUNT]]


def _parent_valid() -> dict[str, Any]:
    value = json.loads((ROOT / PARENT).read_text(encoding="utf-8"))
    if (
        not isinstance(value, Mapping)
        or value.get("role")
        != "v24738_v24737_failure_domain_postterminal_diagnosis"
        or value.get("diagnosis", {}).get("next_requirement")
        != "fresh_target_fixed_dual_representation_or_availability_with_target_granular_abstention"
        or value.get("authorization", {}).get(
            "fresh_target_dual_representation_resilience_design"
        )
        is not True
        or value.get("authorization", {}).get("same_population_forward_retry_or_rerun")
        is not False
        or not seal._sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.47.39 parent diagnosis drifted")
    return dict(value)


def build_design(*, now: int | None = None) -> dict[str, Any]:
    _parent_valid()
    candidates, selected = select_targets()
    resolved = _git("rev-parse", PRE_OUTCOME_COMMIT).stdout.decode().strip()
    if resolved != PRE_OUTCOME_COMMIT:
        raise RuntimeError("V2.47.39 pre-outcome commit drifted")
    value = {
        "artifact_version": 1,
        "role": "v24739_fresh_resilience_population_design",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_diagnosis_sha256": _sha256(PARENT),
        "selection": {
            "pre_outcome_commit": PRE_OUTCOME_COMMIT,
            "rule": "lexicographically_first_two_of_fixed_four_zero_occurrence_target_keys",
            "candidate_count": len(candidates),
            "candidate_vector": candidates,
            "candidate_vector_sha256": seal.payload_sha256(candidates),
            "selected_count": len(selected),
            "selected_targets": selected,
            "selected_targets_sha256": seal.payload_sha256(selected),
            "all_candidates_absent_from_pre_outcome_tracked_tree": True,
            "network_or_transport_outcome_used_for_selection": False,
        },
        "resilience_contract": {
            "representations": ["bulk_zip", "aggregate_json"],
            "both_requested_once_per_target": True,
            "target_admitted_when_at_least_one_representation_is_schema_valid": True,
            "both_valid_require_target_value_agreement": True,
            "one_target_failure_does_not_abstain_other_targets": True,
            "retry_resume_or_selective_rerun": False,
        },
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "prior_transport_outcome_used_for_target_selection": False,
        },
        "authorization": {
            "dual_representation_runtime_helper_and_protocol_design": True,
            "transport_launch": False,
            "same_population_retry_or_rerun": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = seal.payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    candidates, selected = select_targets()
    selection = copied.get("selection", {})
    if (
        copied.get("role") != "v24739_fresh_resilience_population_design"
        or copied.get("parent_diagnosis_sha256") != _sha256(PARENT)
        or selection
        != {
            "pre_outcome_commit": PRE_OUTCOME_COMMIT,
            "rule": "lexicographically_first_two_of_fixed_four_zero_occurrence_target_keys",
            "candidate_count": len(candidates),
            "candidate_vector": candidates,
            "candidate_vector_sha256": seal.payload_sha256(candidates),
            "selected_count": len(selected),
            "selected_targets": selected,
            "selected_targets_sha256": seal.payload_sha256(selected),
            "all_candidates_absent_from_pre_outcome_tracked_tree": True,
            "network_or_transport_outcome_used_for_selection": False,
        }
        or copied.get("resilience_contract")
        != {
            "representations": ["bulk_zip", "aggregate_json"],
            "both_requested_once_per_target": True,
            "target_admitted_when_at_least_one_representation_is_schema_valid": True,
            "both_valid_require_target_value_agreement": True,
            "one_target_failure_does_not_abstain_other_targets": True,
            "retry_resume_or_selective_rerun": False,
        }
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "dual_representation_runtime_helper_and_protocol_design": True,
            "transport_launch": False,
            "same_population_retry_or_rerun": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not seal._sealed(copied, "design_payload_sha256")
    ):
        raise RuntimeError("V2.47.39 population design drifted")
    return copied


def main() -> None:
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)
    value = build_design()
    descriptor = os.open(
        ROOT / OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    main()
