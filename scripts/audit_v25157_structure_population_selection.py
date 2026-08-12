#!/usr/bin/env python3
"""Freeze a history-disjoint CRAN population for the V2.51.57 structure gate.

Selection uses repository history only. No endpoint, page, model, search,
evaluator, credential, or benchmark content is opened. The published artifact
contains only an ordered-vector hash and aggregate zero-hit counts; package
identities and per-item hashes are intentionally absent.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATE = "20260812"
PARENT_COMMIT = "aa971a16"
ROLE = "v25157_structure_population_selection_aggregate_audit"
OUTPUT = Path(
    f"results/v25157_structure_population_selection_audit_v1_{DATE}.json"
)
PACKAGES = (
    "chatlas",
    "finetune",
    "chores",
    "querychat",
    "tidyllm",
    "vitals",
    "fiery",
    "routr",
    "brochure",
    "ambiorix",
    "rhino",
    "leprechaun",
    "charpente",
    "shiny.fluent",
    "shiny.react",
    "reactR",
    "ggh4x",
    "ggdist",
    "sfnetworks",
    "pointblank",
)
SCOPES = ("src", "evaluation", "scripts", "tests", "results", "outputs")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def build_audit(*, now: int | None = None) -> dict[str, object]:
    parent = subprocess.run(
        ["git", "rev-parse", "--verify", PARENT_COMMIT + "^{commit}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()
    if len(PACKAGES) != 20 or len(set(PACKAGES)) != 20:
        raise RuntimeError("V2.51.57 population vector drifted")
    history_hits = 0
    for package in PACKAGES:
        completed = subprocess.run(
            [
                "git",
                "log",
                "--format=%H",
                "-S",
                package,
                parent,
                "--",
                *SCOPES,
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=True,
        )
        history_hits += len(
            [line for line in completed.stdout.splitlines() if line.strip()]
        )
    value: dict[str, object] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_commit": parent,
        "identity_count": len(PACKAGES),
        "unique_identity_count": len(set(PACKAGES)),
        "identity_history_total_hit_count": history_hits,
        "identity_history_zero_hit_count": len(PACKAGES)
        if history_hits == 0
        else 0,
        "ordered_identity_vector_sha256": payload_sha256(PACKAGES),
        "identity_plaintext_per_item_hash_or_clue_mapping_emitted": False,
        "endpoint_page_value_model_search_evaluator_credential_or_benchmark_opened": False,
        "mapping_gold_category_question_type_split_score_reward_or_historical_result_read": False,
        "selection_uses_repository_history_only": True,
        "population_frozen_for_single_future_zero_model_structure_gate": True,
        "audit_valid": history_hits == 0,
        "findings": [] if history_hits == 0 else ["historical_identity_overlap"],
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: dict[str, object]) -> dict[str, object]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("identity_count") != 20
        or copied.get("unique_identity_count") != 20
        or copied.get("identity_history_total_hit_count") != 0
        or copied.get("identity_history_zero_hit_count") != 20
        or copied.get("ordered_identity_vector_sha256")
        != payload_sha256(PACKAGES)
        or copied.get("identity_plaintext_per_item_hash_or_clue_mapping_emitted")
        is not False
        or copied.get(
            "endpoint_page_value_model_search_evaluator_credential_or_benchmark_opened"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("selection_uses_repository_history_only") is not True
        or copied.get("population_frozen_for_single_future_zero_model_structure_gate")
        is not True
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.57 population selection audit drifted")
    return copied


def publish(path: Path, value: dict[str, object]) -> None:
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
    value = build_audit()
    publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {"path": str(OUTPUT), "audit_valid": value["audit_valid"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
