#!/usr/bin/env python3
"""One-shot aggregate-only freshness audit for an external population.

Identity strings are accepted only as command-line inputs.  They are used for
local Git-history scans and never written, printed, or included individually
in the output.  The artifact persists only the ordered-vector hash, counts,
and zero-hit conclusion.  No endpoint, page, model, evaluator, or credential
is accessed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROLE = "v25141_targeted_revision_population_selection_aggregate_audit"


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def build_audit(
    identities: Sequence[str],
    *,
    parent_commit: str,
    now: int | None = None,
) -> dict[str, Any]:
    normalized = ["-".join(str(value).casefold().split()) for value in identities]
    if (
        len(normalized) != 20
        or len(set(normalized)) != 20
        or any(not value or len(value) > 100 for value in normalized)
    ):
        raise RuntimeError("V2.51.41 identity vector drifted")
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", parent_commit + "^{commit}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()
    hit_counts: list[int] = []
    for identity in normalized:
        completed = subprocess.run(
            [
                "git",
                "log",
                resolved,
                "-i",
                "-S",
                identity,
                "--format=%H",
                "--",
                "src",
                "evaluation",
                "scripts",
                "tests",
                "results",
                "outputs",
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=True,
        )
        hit_counts.append(sum(bool(line.strip()) for line in completed.stdout.splitlines()))
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_commit": resolved,
        "identity_count": len(normalized),
        "unique_identity_count": len(set(normalized)),
        "ordered_identity_vector_sha256": payload_sha256(normalized),
        "identity_history_introduction_hit_total": sum(hit_counts),
        "identity_history_zero_hit_count": sum(count == 0 for count in hit_counts),
        "identity_plaintext_or_item_hash_persisted": False,
        "clue_to_identity_mapping_persisted": False,
        "network_endpoint_page_value_model_or_evaluator_access": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "findings": [] if not any(hit_counts) else ["identity_history_not_disjoint"],
        "audit_valid": not any(hit_counts),
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != ROLE
        or copied.get("identity_count") != 20
        or copied.get("unique_identity_count") != 20
        or copied.get("identity_history_introduction_hit_total") != 0
        or copied.get("identity_history_zero_hit_count") != 20
        or copied.get("identity_plaintext_or_item_hash_persisted") is not False
        or copied.get("clue_to_identity_mapping_persisted") is not False
        or copied.get("network_endpoint_page_value_model_or_evaluator_access")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.41 population selection audit drifted")
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
    command = argparse.ArgumentParser()
    command.add_argument("--parent", required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--identity", action="append", required=True)
    args = command.parse_args()
    value = build_audit(args.identity, parent_commit=args.parent)
    publish_exclusive(ROOT / args.output, value)
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
