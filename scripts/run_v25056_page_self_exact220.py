#!/usr/bin/env python3
"""Run the single V2.50.56 page-self label-blind exact-220 forward."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25029_evidence_conditioned_runtime as runtime  # noqa: E402
from deepwide_agent import v25056_page_self_exact220_contract as contract  # noqa: E402
from deepwide_agent.v25055_page_self_production_fetch import (  # noqa: E402
    PageSelfProductionSearchClient,
    validate_search_class,
)
from scripts import run_v25030_evidence_conditioned_exact220 as parent  # noqa: E402


_PARENT_AGGREGATE = parent._aggregate


START_AUTH = {
    "single_exact220_forward": True,
    "postfreeze_official_evaluator": False,
    "retry_resume_skip_or_selective_rerun": False,
    "leaderboard_or_sota": False,
}


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(
        ROOT, parent._read(ROOT / contract.PROTOCOL)
    )
    start = parent._read(ROOT / contract.EXECUTION_START)
    if (
        start.get("role") != contract.START_ROLE
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("selected") != contract.SELECTED_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("protected_watchers") != contract.protected_watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization") != START_AUTH
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.56 execution start drifted")
    return protocol, start


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    slots = ROOT / contract.MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        parent._publish_json(
            slots / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": contract.SLOT_ROLE,
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _aggregate(rows: list[dict[str, Any]], wall: float) -> dict[str, Any]:
    value = _PARENT_AGGREGATE(rows, wall)
    receipts = [
        runtime.validate_receipt(row["content_free_receipt"]) for row in rows
    ]
    fetches = [
        wave_receipt["fetch_receipt"]
        for receipt in receipts
        for wave_receipt in (
            receipt.get("first_wave_receipt"),
            receipt.get("second_wave_receipt"),
        )
        if isinstance(wave_receipt, dict)
    ]
    value["role"] = contract.SUMMARY_ROLE
    value["page_self_projection"] = {
        "projected_pages": sum(int(item["projected_page_count"]) for item in fetches),
        "mechanism_exposed_pages": sum(
            int(item["mechanism_engaged_page_count"]) for item in fetches
        ),
        "changed_evidence_pages": sum(
            int(item["candidate_evidence_changed_page_count"]) for item in fetches
        ),
        "exact_parent_prefix_handoff_pages": sum(
            int(item["exact_parent_prefix_handoff_page_count"]) for item in fetches
        ),
        "characters_beyond_5k_prefix": sum(
            int(item["input_characters_beyond_parent_prefix"]) for item in fetches
        ),
        "positive_signed_credit_count": sum(
            int(item["positive_signed_credit_count"]) for item in fetches
        ),
    }
    projection = value["page_self_projection"]
    value["page_self_mechanism_gate_passed"] = bool(
        projection["mechanism_exposed_pages"] >= 1
        and projection["changed_evidence_pages"]
        == projection["mechanism_exposed_pages"]
        and projection["projected_pages"]
        == projection["mechanism_exposed_pages"]
        + projection["exact_parent_prefix_handoff_pages"]
        and projection["positive_signed_credit_count"] == 0
        and value["all_tasks_within_resource_caps"] is True
    )
    value.pop("summary_payload_sha256", None)
    value["summary_payload_sha256"] = contract.payload_sha256(value)
    return value


def configure() -> None:
    parent.contract = contract
    parent.runtime = runtime
    parent.RobustLatePageBoundSearchClient = PageSelfProductionSearchClient
    parent.validate_search_class = validate_search_class
    parent._validate_start = _validate_start
    parent._prepare_output = _prepare_output
    parent._aggregate = _aggregate


def main() -> None:
    configure()
    parent.main()


if __name__ == "__main__":
    main()
