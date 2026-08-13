#!/usr/bin/env python3
"""Build, preregister, audit, and authorize V2.53.42 exact-220."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25342_checkpoint_exact220_contract as contract  # noqa: E402
from scripts import control_v25267_production_only_exact220 as base  # noqa: E402


BUILD_ROLE = "v25342_checkpoint_exact220_build_audit"
PREAUDIT_ROLE = "v25343_checkpoint_exact220_preactivation_audit"
START_ROLE = "v25343_checkpoint_exact220_execution_start"

TEST_SUITES = (
    ("test_v25342_checkpoint_exact220.py", 10),
    ("test_v25271_validated_production_checkpoint_runtime.py", 9),
    ("test_v25267_production_only_exact220.py", 11),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_v25135_sparse_production_runtime.py", 9),
    ("test_v25110_exact_visible_schema.py", 4),
)
EXPECTED_TESTS = sum(count for _pattern, count in TEST_SUITES)


def configure() -> None:
    base.contract = contract
    base.TEST_SUITES = TEST_SUITES
    base.EXPECTED_TESTS = EXPECTED_TESTS
    base.validate_build = validate_build
    base.validate_preaudit = validate_preaudit


def _reseal(value: Mapping[str, Any], *, role: str) -> dict[str, Any]:
    copied = dict(value)
    copied.pop("audit_payload_sha256", None)
    copied["role"] = role
    return contract.seal(copied, "audit_payload_sha256")


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    configure()
    value = base.build_audit(now=now, require_clean=require_clean)
    return validate_build(_reseal(value, role=BUILD_ROLE))


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != BUILD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("semantic_audit", {}).get(
            "privileged_runtime_field_accesses"
        )
        != []
        or copied.get("semantic_audit", {}).get("evaluator_capabilities") != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits") != []
        or copied.get("direct_runtime_privileged_accesses") != []
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.53.42 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    configure()
    return base.build_protocol(now=now)


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    configure()
    value = base.build_preaudit(now=now)
    return validate_preaudit(_reseal(value, role=PREAUDIT_ROLE))


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != PREAUDIT_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("authorization") != base.PREAUDIT_AUTH
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.53.43 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    configure()
    value = base.build_start(now=now)
    copied = dict(value)
    copied.pop("execution_start_payload_sha256", None)
    copied["role"] = START_ROLE
    return contract.seal(copied, "execution_start_payload_sha256")


def main() -> None:
    configure()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("build-audit", "protocol", "preaudit", "start")
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    else:
        value, path = build_start(), contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    base._publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "audit_valid": value.get("audit_valid"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
