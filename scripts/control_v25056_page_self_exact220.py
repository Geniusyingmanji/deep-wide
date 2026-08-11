#!/usr/bin/env python3
"""Build, preregister, audit, and authorize V2.50.56 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25056_page_self_exact220_contract as contract  # noqa: E402
from scripts import control_v25030_evidence_conditioned_exact220 as parent  # noqa: E402


TEST_SUITES = (
    (contract.TEST, 8),
    (Path("tests/test_v25055_page_self_production_fetch.py"), 5),
    (Path("tests/test_v25049_page_self_identified_record.py"), 10),
    (Path("tests/test_v25029_evidence_conditioned_runtime.py"), 5),
    (Path("tests/test_v25024_evidence_conditioned_queries.py"), 8),
    (Path("tests/test_v24996_shared_first_wave_paired_runtime.py"), 7),
    (Path("tests/test_v24990_query_vector_paired_runtime.py"), 7),
    (Path("tests/test_v24986_robust_paired_runtime.py"), 5),
    (Path("tests/test_v24985_robust_late_page_fetch.py"), 2),
    (Path("tests/test_v24982_paired_production_runtime.py"), 7),
)
EXPECTED_TESTS = sum(count for _path, count in TEST_SUITES)
PREAUDIT_AUTH = {
    "execution_start_generation": True,
    "single_exact220_forward": False,
    "postfreeze_official_evaluator": False,
    "retry_resume_skip_or_selective_rerun": False,
    "leaderboard_or_sota": False,
}
START_AUTH = {
    "single_exact220_forward": True,
    "postfreeze_official_evaluator": False,
    "retry_resume_skip_or_selective_rerun": False,
    "leaderboard_or_sota": False,
}


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = parent._protocol()
    if (
        copied.get("role") != "v25056_page_self_exact220_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("dependency_manifest_sha256")
        != protocol["dependency_manifest_sha256"]
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("conflicting_process_pids") != []
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("authorization") != PREAUDIT_AUTH
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.56 preactivation audit drifted")
    return copied


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25056_page_self_exact220_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != "authorized_not_started"
        or copied.get("findings") != []
        or copied.get("selected") != 220
        or copied.get("executor_concurrency") != 20
        or copied.get("model_slot_cap") != 8
        or copied.get("runtime_input_contract") != ["opaque_id", "question"]
        or copied.get("authorization") != START_AUTH
        or not contract.sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.56 execution start drifted")
    return copied


def configure() -> None:
    parent.contract = contract
    parent.TEST_SUITES = TEST_SUITES
    parent.EXPECTED_TESTS = EXPECTED_TESTS
    parent.PREAUDIT_AUTH = PREAUDIT_AUTH
    parent.START_AUTH = START_AUTH
    parent.validate_preaudit = validate_preaudit
    parent.validate_start = validate_start


def main() -> None:
    configure()
    parent.main()


if __name__ == "__main__":
    main()
