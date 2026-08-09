#!/usr/bin/env python3
"""Freeze and authorize the V2.49.40 external gate."""

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

from deepwide_agent import v24940_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import control_v24923_target_value_external as base  # noqa: E402


TEST_SUITES = (
    (contract.TEST, 12),
    (Path("tests/test_v24939_schema_bound_record_ledger.py"), 14),
    (Path("tests/test_v24933_contextual_record_value_projector.py"), 10),
    (Path("tests/test_v24928_unicode_total_visible_row_compactor.py"), 12),
)


def configure() -> None:
    base.contract = contract
    base.PROJECTOR_AUDIT = contract.CANDIDATE_AUDIT
    base.TEST_SUITES = TEST_SUITES


def _role_and_seal(value: dict[str, Any], role: str, field: str) -> dict[str, Any]:
    value["role"] = role
    value.pop(field, None)
    value[field] = contract.payload_sha256(value)
    return value


def main() -> None:
    configure()
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start"))
    args = parser.parse_args()
    base._clean_pushed()
    if args.command == "build-audit":
        value = _role_and_seal(
            base.build_audit(),
            "v24940_open_world_ledger_external_build_audit",
            "audit_payload_sha256",
        )
        value["checks"]["focused_tests_exact48"] = (
            value["tests"]["passed"] is True and value["tests"]["observed"] == 48
        )
        value["checks"].pop("focused_tests_exact39", None)
        value["findings"] = sorted(name for name, passed in value["checks"].items() if not passed)
        value["audit_valid"] = not value["findings"]
        value["authorization"]["protocol_publication"] = value["audit_valid"]
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        value = _role_and_seal(
            base.build_protocol(),
            "v24940_open_world_ledger_external_preregistration",
            "protocol_payload_sha256",
        )
        value["population"].update(
            {
                "rows_per_task": contract.ROWS_PER_TASK,
                "distractor_rows_per_task": contract.DISTRACTOR_ROWS_PER_TASK,
                "selected_entities": contract.SELECTED_ENTITY_COUNT,
                "selected_source_records": contract.SELECTED_RECORD_COUNT,
                "visible_row_identities_enumerated": False,
                "visible_cohort_predicate_only": True,
                "target_identities_disjoint_across_tasks": True,
                "fixed_distractor_pool_shared_across_tasks": True,
            }
        )
        value["execution"].update(
            {
                "only_treatment": "v24933_contextual_projection_to_v24939_schema_bound_open_world_ledger",
                "arm_algorithms": {
                    "parent_30k": "v24933_unicode_total_contextual_record_value_projector_v1",
                    "target_value_30k": "v24939_schema_bound_open_world_record_ledger_v1",
                },
                "model_call_order": "opaque_id_hash_counterbalanced_one_call_per_arm",
                "mechanism_gate_before_evaluator": {
                    "minimum_projection_unequal_tasks": 12,
                    "minimum_retained_target_value_pairs": 1,
                    "minimum_admissible_bound_observations": contract.SELECTED_COUNT * contract.ROWS_PER_TASK * 3,
                    "minimum_retained_admissible_bound_observations": contract.SELECTED_COUNT * contract.ROWS_PER_TASK * 3,
                    "minimum_discovered_row_keys": contract.SELECTED_COUNT * contract.PAGE_ROWS_PER_TASK,
                    "failure_as_zero_tasks": 0,
                },
            }
        )
        value["shared_prefix"]["same_frozen_public_derived_task_page_for_both_arms"] = True
        value.pop("protocol_payload_sha256")
        value["protocol_payload_sha256"] = contract.payload_sha256(value)
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = _role_and_seal(
            base.build_preaudit(),
            "v24940_open_world_ledger_external_preactivation_audit",
            "audit_payload_sha256",
        )
        value["checks"]["focused_tests_exact48"] = (
            value["tests"]["passed"] is True and value["tests"]["observed"] == 48
        )
        value["checks"].pop("focused_tests_exact39", None)
        value["findings"] = sorted(name for name, passed in value["checks"].items() if not passed)
        value["audit_valid"] = not value["findings"]
        value["authorization"]["execution_start_generation"] = value["audit_valid"]
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        path = contract.PREAUDIT
    else:
        value = _role_and_seal(
            base.build_start(),
            "v24940_open_world_ledger_external_execution_start",
            "execution_start_payload_sha256",
        )
        path = contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(f"V2.49.40 {args.command} failed: {value['findings']}")
    base._publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
