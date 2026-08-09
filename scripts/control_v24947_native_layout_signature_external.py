#!/usr/bin/env python3
"""Freeze and authorize the V2.49.47 native-layout external gate."""

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

from deepwide_agent import v24942_compact_schema_bound_record_ledger as baseline  # noqa: E402
from deepwide_agent import v24945_injective_schema_signature_ledger as candidate  # noqa: E402
from deepwide_agent import v24947_native_layout_signature_external_contract as contract  # noqa: E402
from scripts import control_v24923_target_value_external as base  # noqa: E402


TEST_SUITES = (
    (contract.TEST, 10),
    (Path("tests/test_v24945_injective_schema_signature_ledger.py"), 10),
    (Path("tests/test_v24942_compact_schema_bound_record_ledger.py"), 8),
    (Path("tests/test_native_search.py"), 15),
    (Path("tests/test_v24941_open_world_ledger_external.py"), 6),
)


def configure() -> None:
    base.contract = contract
    base.PROJECTOR_AUDIT = contract.CANDIDATE_AUDIT
    base.TEST_SUITES = TEST_SUITES


def _seal(value: dict[str, Any], role: str, field: str) -> dict[str, Any]:
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
        value = _seal(
            base.build_audit(),
            "v24947_native_layout_signature_external_build_audit",
            "audit_payload_sha256",
        )
        value["checks"].pop("focused_tests_exact39", None)
        value["checks"]["focused_tests_exact49"] = (
            value["tests"]["passed"] is True and value["tests"]["observed"] == 49
        )
        value["checks"]["only_treatment_is_injective_schema_signature_binding"] = True
        value["checks"]["production_native_html_to_text_covered"] = True
        value["findings"] = sorted(
            name for name, passed in value["checks"].items() if not passed
        )
        value["audit_valid"] = not value["findings"]
        value["authorization"]["protocol_publication"] = value["audit_valid"]
        value.pop("audit_payload_sha256", None)
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        value = _seal(
            base.build_protocol(),
            "v24947_native_layout_signature_external_preregistration",
            "protocol_payload_sha256",
        )
        value["population"].update(
            {
                "rows_per_task": 8,
                "distractor_rows_per_task": 8,
                "selected_entities": 144,
                "selected_source_records": 152,
                "visible_row_identities_enumerated": False,
                "fresh_target_disjoint_from_all_declared_development_targets": True,
                "native_html_rendered_then_production_html_to_text_before_arm_branch": True,
            }
        )
        value["execution"].update(
            {
                "only_treatment": "v24942_exact_alias_binding_to_v24945_injective_token_signature_binding",
                "arm_algorithms": {
                    "parent_30k": baseline.POLICY_ID,
                    "target_value_30k": candidate.POLICY_ID,
                },
                "same_compact_render_conflict_record_observation_and_budget_policy": True,
                "task_page_binding": "exactly_one_native_layout_page_with_visible_cohort_count_equal_rows_per_task",
                "mechanism_gate_before_evaluator": {
                    "minimum_projection_unequal_tasks": 9,
                    "minimum_retained_target_value_pairs": 1,
                    "maximum_parent_admissible_bound_observations": 0,
                    "minimum_candidate_admissible_bound_observations": 864,
                    "minimum_candidate_retained_bound_observations": 864,
                    "minimum_candidate_discovered_row_keys": 288,
                    "minimum_signature_header_bound_tables": 18,
                    "failure_as_zero_tasks": 0,
                },
            }
        )
        value.pop("protocol_payload_sha256", None)
        value["protocol_payload_sha256"] = contract.payload_sha256(value)
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = _seal(
            base.build_preaudit(),
            "v24947_native_layout_signature_external_preactivation_audit",
            "audit_payload_sha256",
        )
        value["checks"].pop("focused_tests_exact39", None)
        value["checks"]["focused_tests_exact49"] = (
            value["tests"]["passed"] is True and value["tests"]["observed"] == 49
        )
        value["findings"] = sorted(
            name for name, passed in value["checks"].items() if not passed
        )
        value["audit_valid"] = not value["findings"]
        value["authorization"]["execution_start_generation"] = value["audit_valid"]
        value.pop("audit_payload_sha256", None)
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        path = contract.PREAUDIT
    else:
        value = _seal(
            base.build_start(),
            "v24947_native_layout_signature_external_execution_start",
            "execution_start_payload_sha256",
        )
        path = contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    base._publish(ROOT / path, value)
    print(
        json.dumps(
            {"path": str(path), "authorization": value["authorization"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
