#!/usr/bin/env python3
"""Freeze and authorize the fresh V2.49.37 contextual-record gate."""

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

from deepwide_agent import v24937_layout_diverse_contextual_external_contract as contract  # noqa: E402
from scripts import control_v24923_target_value_external as base  # noqa: E402


TEST_SUITES = (
    (contract.TEST, 9),
    (Path("tests/test_v24933_contextual_record_value_projector.py"), 10),
    (Path("tests/test_v24928_unicode_total_visible_row_compactor.py"), 12),
    (Path("tests/test_v24936_v24934_identity_erratum.py"), 8),
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
    parser.add_argument(
        "command", choices=("build-audit", "protocol", "preaudit", "start")
    )
    args = parser.parse_args()
    base._clean_pushed()
    if args.command == "build-audit":
        corrected = base._read(ROOT / contract.ERRATUM_RESULT)
        corrected_post = base._read(ROOT / contract.ERRATUM_POSTAUDIT)
        value = _role_and_seal(
            base.build_audit(),
            "v24937_layout_diverse_contextual_external_build_audit",
            "audit_payload_sha256",
        )
        value["corrected_v24936_external_go"] = {
            "result": str(contract.ERRATUM_RESULT),
            "result_sha256": contract.sha256(ROOT / contract.ERRATUM_RESULT),
            "postaudit": str(contract.ERRATUM_POSTAUDIT),
            "postaudit_sha256": contract.sha256(ROOT / contract.ERRATUM_POSTAUDIT),
        }
        value["checks"]["corrected_v24936_external_go_valid"] = (
            corrected.get("passed") is True
            and corrected.get("status") == "corrected_external_go"
            and contract.sealed(corrected, "result_payload_sha256")
            and corrected_post.get("audit_valid") is True
            and corrected_post.get("findings") == []
            and contract.sealed(corrected_post, "audit_payload_sha256")
            and corrected_post.get("authorization", {}).get(
                "fresh_external_successor_design"
            )
            is True
            and corrected_post.get("authorization", {}).get(
                "public_exact220_candidate_design"
            )
            is False
        )
        value["findings"] = sorted(
            name for name, passed in value["checks"].items() if not passed
        )
        value["audit_valid"] = not value["findings"]
        value["authorization"]["protocol_publication"] = value["audit_valid"]
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        value = _role_and_seal(
            base.build_protocol(),
            "v24937_layout_diverse_contextual_external_preregistration",
            "protocol_payload_sha256",
        )
        execution = value["execution"]
        execution["only_treatment"] = (
            "bounded_visible_target_context_for_value_bearing_records_across_two_ordinary_text_layouts"
        )
        execution["arm_algorithms"] = {
            "parent_30k": "v24928_unicode_total_visible_row_sparse_table_compactor_v1",
            "target_value_30k": "v24933_unicode_total_contextual_record_value_projector_v1",
        }
        execution["model_call_order"] = "opaque_id_hash_counterbalanced_one_call_per_arm"
        execution["mechanism_gate_before_evaluator"] = {
            "minimum_projection_unequal_tasks": 8,
            "minimum_retained_target_value_pairs": 16,
            "minimum_retained_contextual_target_value_pairs": 16,
            "minimum_layouts_with_contextual_pairs": 2,
            "failure_as_zero_tasks": 0,
        }
        value["population"]["target_cell_disjoint_from_all_prior_target_keys"] = True
        value["population"]["layout_vector"] = [
            target["layout"] for target in contract.TARGETS
        ]
        value["shared_prefix"]["same_layout_diverse_page_bytes_for_both_arms"] = True
        value.pop("protocol_payload_sha256")
        value["protocol_payload_sha256"] = contract.payload_sha256(value)
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = _role_and_seal(
            base.build_preaudit(),
            "v24937_layout_diverse_contextual_external_preactivation_audit",
            "audit_payload_sha256",
        )
        path = contract.PREAUDIT
    else:
        value = _role_and_seal(
            base.build_start(),
            "v24937_layout_diverse_contextual_external_execution_start",
            "execution_start_payload_sha256",
        )
        path = contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(f"V2.49.37 {args.command} failed: {value['findings']}")
    base._publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
