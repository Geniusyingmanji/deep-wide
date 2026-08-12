#!/usr/bin/env python3
"""Aggregate-only freshness audit for the V2.51.60 population.

The caller supplies exactly twenty identities.  They are used only for local
Git-history scans and are never written, printed, or persisted individually.
The output contains an ordered-vector hash and aggregate counts.  This audit
does not authorize a protocol, external activation, evaluator, or benchmark.
"""

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


ROLE = "v25160_vertical_key_value_population_selection_aggregate_audit"
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
    value.update(
        {
            "selection_uses_repository_history_only": True,
            "v25141_v25145_v25149_v25153_v25157_population_reuse": False,
            "population_frozen_for_single_future_vertical_key_value_gate": True,
            "external_protocol_activation_evaluator_or_deepwidebench_authorized": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
    )
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
        or copied.get("selection_uses_repository_history_only") is not True
        or copied.get(
            "v25141_v25145_v25149_v25153_v25157_population_reuse"
        )
        is not False
        or copied.get(
            "population_frozen_for_single_future_vertical_key_value_gate"
        )
        is not True
        or copied.get(
            "external_protocol_activation_evaluator_or_deepwidebench_authorized"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.60 population selection audit drifted")
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
