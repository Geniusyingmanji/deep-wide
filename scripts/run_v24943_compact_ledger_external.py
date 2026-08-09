#!/usr/bin/env python3
"""Run the fresh V2.49.43 representation-only gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24943_compact_ledger_external_contract as contract  # noqa: E402
from deepwide_agent import v24939_schema_bound_record_ledger as verbose  # noqa: E402
from deepwide_agent import v24942_compact_schema_bound_record_ledger as compact  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as population  # noqa: E402


_INHERITED_BUILD_FORWARD_AUDIT = engine.build_forward_audit


def build_forward_audit(*, now: int | None = None):
    value = _INHERITED_BUILD_FORWARD_AUDIT(now=now)
    projections = engine._read_jsonl(ROOT / contract.PROJECTIONS)
    parents = [row["projection_receipts"]["parent_30k"] for row in projections]
    candidates = [row["projection_receipts"]["target_value_30k"] for row in projections]
    parent_valid = all(
        row.get("role") == "v24943_content_free_verbose_schema_bound_receipt"
        and row.get("policy_id") == verbose.POLICY_ID
        and row.get("entropy_or_information_gain_assigns_credit") is False
        for row in parents
    )
    candidate_valid = all(
        row.get("role") == "v24943_content_free_compact_schema_bound_receipt"
        and row.get("policy_id") == compact.POLICY_ID
        and row.get("entropy_or_information_gain_assigns_credit") is False
        for row in candidates
    )
    admissible = sum(int(row["admissible_bound_observation_count"]) for row in candidates)
    retained = sum(int(row["retained_admissible_bound_observation_count"]) for row in candidates)
    discovered = sum(int(row["discovered_row_key_count"]) for row in candidates)
    value["checks"]["parent_receipts_valid"] = parent_valid
    value["checks"]["candidate_receipts_valid"] = candidate_valid
    value["checks"]["schema_bound_candidate_receipts_valid"] = candidate_valid
    protocol = engine._read(ROOT / contract.PROTOCOL)
    gate = protocol["execution"]["mechanism_gate_before_evaluator"]
    exposed = (
        admissible >= int(gate["minimum_admissible_bound_observations"])
        and retained >= int(gate["minimum_retained_admissible_bound_observations"])
        and discovered >= int(gate["minimum_discovered_row_keys"])
    )
    value["checks"]["compact_representation_mechanism_exposed"] = exposed
    value["mechanism_gate"].update(
        {
            "observed_admissible_bound_observations": admissible,
            "observed_retained_admissible_bound_observations": retained,
            "observed_discovered_row_keys": discovered,
        }
    )
    value["mechanism_gate"]["passed"] = (
        value["mechanism_gate"]["passed"] and parent_valid and candidate_valid and exposed
    )
    value["findings"] = sorted(name for name, passed in value["checks"].items() if not passed)
    value["audit_valid"] = not value["findings"]
    value["authorization"]["postfreeze_external_evaluator_protocol"] = value["audit_valid"] and value["mechanism_gate"]["passed"]
    value.pop("audit_payload_sha256", None)
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def configure() -> None:
    population.contract = contract
    engine.contract = contract
    engine.parse_target = population.parse_target
    engine.build_snapshot = population.build_snapshot
    engine.build_forward_audit = build_forward_audit


def main() -> None:
    configure()
    engine.main()


if __name__ == "__main__":
    main()
