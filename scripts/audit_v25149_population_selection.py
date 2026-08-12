#!/usr/bin/env python3
"""Aggregate-only history-disjointness audit for the V2.51.49 population."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v25141_population_selection as parent  # noqa: E402


ROLE = "v25149_deterministic_candidate_population_selection_aggregate_audit"
payload_sha256 = parent.payload_sha256


def build_audit(
    identities: Sequence[str],
    *,
    parent_commit: str,
    now: int | None = None,
) -> dict[str, Any]:
    value = parent.build_audit(
        identities,
        parent_commit=parent_commit,
        now=now,
    )
    value["role"] = ROLE
    value.pop("audit_payload_sha256")
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
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
        raise RuntimeError("V2.51.49 population selection audit drifted")
    return copied


def main() -> None:
    command = argparse.ArgumentParser()
    command.add_argument("--parent", required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--identity", action="append", required=True)
    args = command.parse_args()
    value = build_audit(args.identity, parent_commit=args.parent)
    parent.publish_exclusive(ROOT / args.output, value)
    print(
        json.dumps(
            {
                "path": str(args.output),
                "identity_count": value["identity_count"],
                "history_hits": value[
                    "identity_history_introduction_hit_total"
                ],
                "audit_valid": value["audit_valid"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
