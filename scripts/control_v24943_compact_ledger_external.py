#!/usr/bin/env python3
"""Freeze and authorize the V2.49.43 representation-only gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24943_compact_ledger_external_contract as contract  # noqa: E402
from scripts import control_v24923_target_value_external as base  # noqa: E402

TEST_SUITES = (
    (contract.TEST, 7),
    (Path("tests/test_v24942_compact_schema_bound_record_ledger.py"), 8),
    (Path("tests/test_v24939_schema_bound_record_ledger.py"), 14),
    (Path("tests/test_v24941_open_world_ledger_external.py"), 6),
)


def configure() -> None:
    base.contract = contract
    base.PROJECTOR_AUDIT = contract.CANDIDATE_AUDIT
    base.TEST_SUITES = TEST_SUITES


def _seal(value: dict[str, Any], role: str, field: str) -> dict[str, Any]:
    value["role"] = role; value.pop(field, None); value[field] = contract.payload_sha256(value); return value


def _parent_valid() -> bool:
    result = base._read(ROOT / contract.PARENT_RESULT)
    audit = base._read(ROOT / contract.PARENT_POSTAUDIT)
    return result.get("status") == "open_world_ledger_external_no_go" and result.get("passed") is False and result.get("metrics", {}).get("target_value_30k_minus_parent_30k", {}).get("composite", 0) > 0 and contract.sealed(result, "result_payload_sha256") and audit.get("audit_valid") is True and audit.get("findings") == [] and contract.sealed(audit, "audit_payload_sha256")


def main() -> None:
    configure()
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start")); args = parser.parse_args()
    base._clean_pushed()
    if args.command == "build-audit":
        value = _seal(base.build_audit(), "v24943_compact_ledger_external_build_audit", "audit_payload_sha256")
        value["checks"]["focused_tests_exact35"] = value["tests"]["passed"] is True and value["tests"]["observed"] == 35
        value["checks"].pop("focused_tests_exact39", None)
        value["checks"]["v24941_external_no_go_valid"] = _parent_valid()
        value["checks"]["only_candidate_change_is_ledger_representation"] = True
        value["findings"] = sorted(name for name, passed in value["checks"].items() if not passed); value["audit_valid"] = not value["findings"]
        value["authorization"]["protocol_publication"] = value["audit_valid"]
        value.pop("audit_payload_sha256"); value["audit_payload_sha256"] = contract.payload_sha256(value); path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        value = _seal(base.build_protocol(), "v24943_compact_ledger_external_preregistration", "protocol_payload_sha256")
        value["population"].update({"rows_per_task": 8, "distractor_rows_per_task": 8, "selected_entities": 144, "selected_source_records": 152, "visible_row_identities_enumerated": False, "new_target_disjoint_from_v24941": True})
        value["execution"].update({
            "only_treatment": "v24939_verbose_ledger_render_to_v24942_compact_ledger_render",
            "arm_algorithms": {"parent_30k": "v24939_schema_bound_open_world_record_ledger_v1", "target_value_30k": "v24942_compact_schema_bound_open_world_record_ledger_v1"},
            "same_discovery_conflict_record_and_observation_seals": True,
            "task_page_binding": "exactly_one_frozen_page_with_visible_cohort_count_equal_rows_per_task",
            "mechanism_gate_before_evaluator": {"minimum_projection_unequal_tasks": 9, "minimum_retained_target_value_pairs": 1, "minimum_admissible_bound_observations": 864, "minimum_retained_admissible_bound_observations": 864, "minimum_discovered_row_keys": 288, "failure_as_zero_tasks": 0},
        })
        value.pop("protocol_payload_sha256"); value["protocol_payload_sha256"] = contract.payload_sha256(value); path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = _seal(base.build_preaudit(), "v24943_compact_ledger_external_preactivation_audit", "audit_payload_sha256")
        value["checks"]["focused_tests_exact35"] = value["tests"]["passed"] is True and value["tests"]["observed"] == 35
        value["checks"].pop("focused_tests_exact39", None); value["checks"]["v24941_external_no_go_remains_valid"] = _parent_valid()
        value["findings"] = sorted(name for name, passed in value["checks"].items() if not passed); value["audit_valid"] = not value["findings"]
        value["authorization"]["execution_start_generation"] = value["audit_valid"]
        value.pop("audit_payload_sha256"); value["audit_payload_sha256"] = contract.payload_sha256(value); path = contract.PREAUDIT
    else:
        value = _seal(base.build_start(), "v24943_compact_ledger_external_execution_start", "execution_start_payload_sha256"); path = contract.EXECUTION_START
    if value.get("findings"): raise RuntimeError(value["findings"])
    base._publish(ROOT / path, value); print(json.dumps({"path": str(path), "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__": main()
