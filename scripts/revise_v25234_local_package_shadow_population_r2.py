#!/usr/bin/env python3
"""Freeze the V2.52.34 R2 aggregate-capacity correction."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25234_local_package_shadow_population as parent  # noqa: E402


DATE = "20260812"
ROLE = "v25234_local_package_shadow_population_design_r2"
OUTPUT = Path(
    f"results/v25234_local_package_shadow_population_design_r2_{DATE}.json"
)
SOURCE = Path("scripts/revise_v25234_local_package_shadow_population_r2.py")
TEST = Path("tests/test_revise_v25234_local_package_shadow_population_r2.py")
PARENT = parent.OUTPUT
PARENT_SHA256 = "a9c0081dd1a9b05816fd206ef00acd2faefb3e490fba72ad14947b35600e764b"
OLD_COUNTS = copy.deepcopy(parent.CAPACITY_PROBE)
CORRECTED_COUNTS = {
    "installed_unique": 2045,
    "compact_alpha": 116,
    "single_hyphen_alpha": 351,
    "multi_hyphen_alpha": 370,
    "digit_bearing": 1122,
    "excluded_other": 86,
}


def build_revision(*, now: int | None = None) -> dict[str, Any]:
    if parent.base.sha256(PARENT) != PARENT_SHA256:
        raise RuntimeError("V2.52.34 R2 parent hash drifted")
    raw = json.loads(parent.base._ordinary(PARENT).read_text(encoding="utf-8"))
    checked = parent.validate_design(raw)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_design": {"path": str(PARENT), "sha256": PARENT_SHA256},
        "correction": {
            "field": "pre_design_capacity_probe.counts",
            "old_counts": OLD_COUNTS,
            "corrected_counts": CORRECTED_COUNTS,
            "reason": "the initial aggregate probe allowed plus_or_dot in the no_digit hyphen branch while the frozen morphology text requires lowercase_letters_and_hyphens_only",
            "misclassified_single_hyphen_package_count": 2,
            "identity_plaintext_or_item_hash_opened_emitted_or_persisted": False,
            "formal_ranking_history_scan_selection_or_task_freeze_performed": False,
            "all_four_corrected_morphology_capacities_at_least_64": True,
        },
        "unchanged_contracts": {
            "source_contract": copy.deepcopy(checked["source_contract"]),
            "morphology_contract": copy.deepcopy(checked["morphology_contract"]),
            "selection_contract": copy.deepcopy(checked["selection_contract"]),
            "task_contract": copy.deepcopy(checked["task_contract"]),
            "future_shadow_gate": copy.deepcopy(checked["future_shadow_gate"]),
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": copy.deepcopy(checked["authorization"]),
    }
    value["design_payload_sha256"] = parent.base.payload_sha256(value)
    return validate_revision(value)


def validate_revision(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    correction = copied.get("correction") or {}
    unchanged = copied.get("unchanged_contracts") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "parent_design",
            "correction",
            "unchanged_contracts",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "design_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("parent_design")
        != {"path": str(PARENT), "sha256": PARENT_SHA256}
        or correction.get("field") != "pre_design_capacity_probe.counts"
        or correction.get("old_counts") != OLD_COUNTS
        or correction.get("corrected_counts") != CORRECTED_COUNTS
        or correction.get("misclassified_single_hyphen_package_count") != 2
        or correction.get("identity_plaintext_or_item_hash_opened_emitted_or_persisted")
        is not False
        or correction.get("formal_ranking_history_scan_selection_or_task_freeze_performed")
        is not False
        or correction.get("all_four_corrected_morphology_capacities_at_least_64")
        is not True
        or unchanged
        != {
            "source_contract": parent.build_design(now=0)["source_contract"],
            "morphology_contract": parent.build_design(now=0)["morphology_contract"],
            "selection_contract": parent.build_design(now=0)["selection_contract"],
            "task_contract": parent.build_design(now=0)["task_contract"],
            "future_shadow_gate": parent.build_design(now=0)["future_shadow_gate"],
        }
        or copied.get("authorization")
        != parent.build_design(now=0)["authorization"]
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or seal != parent.base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.34 R2 population design correction drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_revision()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "single_hyphen_alpha": value["correction"]["corrected_counts"][
                    "single_hyphen_alpha"
                ],
                "formal_selection": value["authorization"][
                    "formal_dpkg_query_history_scan_or_population_freeze"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
