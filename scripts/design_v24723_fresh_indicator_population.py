#!/usr/bin/env python3
"""Select a fresh World Bank indicator population from pre-outcome code."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.v24721_worldbank_transport_gate import payload_sha256  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24723_fresh_indicator_population_design_v1_{DATE}.json")
PRE_OUTCOME_COMMIT = "d2b7deacc9f66cf8ac8c4904b588c8c889d68c26"
SOURCE_PATH = Path("tests/test_v24686_worldbank_target_value_runtime.py")
PRIOR_KEYS = frozenset(
    {
        "AG.SRF.TOTL.K2@2022",
        "EN.POP.DNST@2022",
        "SP.POP.TOTL@2023",
        "TG.VAL.TOTL.GD.ZS@2023",
        "NY.GDP.PCAP.CD@2023",
        "SP.URB.TOTL.IN.ZS@2023",
    }
)
_INDICATOR = re.compile(r"[A-Z][A-Z0-9.]{4,40}")
_YEAR = re.compile(r"20[0-3][0-9]")


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=True,
    ).stdout


def source_at_pre_outcome_commit() -> bytes:
    return _git("show", f"{PRE_OUTCOME_COMMIT}:{SOURCE_PATH}")


def select_targets(source: bytes) -> list[dict[str, str]]:
    try:
        text = source.decode("utf-8")
        tree = ast.parse(text)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError("V2.47.23 frozen source is invalid") from exc
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "TARGETS"
            for target in node.targets
        )
    ]
    if len(assignments) != 1:
        raise ValueError("V2.47.23 TARGETS assignment drifted")
    try:
        raw = ast.literal_eval(assignments[0].value)
    except (TypeError, ValueError) as exc:
        raise ValueError("V2.47.23 TARGETS is not literal") from exc
    selected: list[dict[str, str]] = []
    for item in raw:
        if (
            not isinstance(item, tuple)
            or len(item) != 3
            or not all(isinstance(value, str) for value in item)
        ):
            raise ValueError("V2.47.23 target tuple drifted")
        label, indicator, year = item
        key = f"{indicator}@{year}"
        if (
            not label.strip()
            or _INDICATOR.fullmatch(indicator) is None
            or _YEAR.fullmatch(year) is None
            or key in PRIOR_KEYS
        ):
            raise ValueError("V2.47.23 target is invalid or already consumed")
        selected.append(
            {
                "label_sha256": hashlib.sha256(label.encode()).hexdigest(),
                "indicator": indicator,
                "year": year,
                "target_key": key,
            }
        )
    selected.sort(key=lambda item: item["target_key"])
    if len(selected) != 2 or len({item["target_key"] for item in selected}) != 2:
        raise ValueError("V2.47.23 fresh target count drifted")
    return selected


def build_design(*, now: int | None = None) -> dict[str, Any]:
    source = source_at_pre_outcome_commit()
    targets = select_targets(source)
    value = {
        "artifact_version": 1,
        "role": "v24723_fresh_indicator_population_design",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selection": {
            "pre_outcome_commit": PRE_OUTCOME_COMMIT,
            "pre_outcome_source_path": str(SOURCE_PATH),
            "pre_outcome_source_sha256": hashlib.sha256(source).hexdigest(),
            "rule": "all_literal_TARGETS_entries_from_frozen_source_excluding_v24721_consumed_keys",
            "network_or_transport_outcome_used_for_selection": False,
            "prior_target_key_count": len(PRIOR_KEYS),
            "prior_target_keys_sha256": payload_sha256(sorted(PRIOR_KEYS)),
            "selected_count": len(targets),
            "selected_targets": targets,
            "selected_targets_sha256": payload_sha256(targets),
        },
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "fresh_bulk_primary_transport_protocol_design": True,
            "transport_launch": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = payload_sha256(value)
    validate_design(value)
    return value


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    selection = copied.get("selection", {})
    source = source_at_pre_outcome_commit()
    targets = select_targets(source)
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    if (
        copied.get("role") != "v24723_fresh_indicator_population_design"
        or selection.get("pre_outcome_commit") != PRE_OUTCOME_COMMIT
        or selection.get("pre_outcome_source_path") != str(SOURCE_PATH)
        or selection.get("pre_outcome_source_sha256")
        != hashlib.sha256(source).hexdigest()
        or selection.get("rule")
        != "all_literal_TARGETS_entries_from_frozen_source_excluding_v24721_consumed_keys"
        or selection.get("network_or_transport_outcome_used_for_selection")
        is not False
        or selection.get("prior_target_key_count") != len(PRIOR_KEYS)
        or selection.get("prior_target_keys_sha256")
        != payload_sha256(sorted(PRIOR_KEYS))
        or selection.get("selected_count") != len(targets)
        or selection.get("selected_targets") != targets
        or selection.get("selected_targets_sha256") != payload_sha256(targets)
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "fresh_bulk_primary_transport_protocol_design": True,
            "transport_launch": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.23 population design drifted")
    return copied


def main() -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(OUTPUT)
    value = build_design()
    descriptor = os.open(
        path,
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
