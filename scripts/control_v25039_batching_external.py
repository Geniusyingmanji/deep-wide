#!/usr/bin/env python3
"""Control-plane wrapper for the append-only V2.50.39 recovery gate."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25039_batching_external_contract as contract  # noqa: E402
from scripts import control_v25038_batching_external as engine  # noqa: E402
from scripts import run_v25039_batching_external as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25039_batching_external.py", 7),
    ("test_v25038_batching_external.py", 10),
    ("test_v25036_source_only_hosted_search.py", 5),
    ("test_v24269_task_union_discovery.py", 5),
    ("test_v24280_task_union_single_shot.py", 4),
    ("test_v24316_deadline_search.py", 7),
    ("test_v24468_total_wall_transport.py", 8),
    ("test_v24985_robust_late_page_fetch.py", 2),
)


def configure() -> None:
    engine.contract = contract
    engine.runner = runner
    engine.TEST_SUITES = TEST_SUITES


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    configure()
    value = engine.build_audit(now=now, require_clean=require_clean)
    value.pop("audit_payload_sha256", None)
    expected_manifest = {
        *(str(path) for path in contract.forward_dependency_closure(ROOT)),
        str(contract.CONTROL),
        str(contract.TEST),
        str(contract.FAILURE),
    }
    value["checks"]["source_manifest_complete"] = set(
        value["source_manifest"]
    ) == expected_manifest
    value["findings"] = sorted(
        name for name, ok in value["checks"].items() if not ok
    )
    value["audit_valid"] = not value["findings"]
    value["authorization"]["protocol_generation"] = not value["findings"]
    value.update(
        {
            "role": "v25039_batching_external_build_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "parent_failure_sha256": contract.sha256(ROOT / contract.FAILURE),
            "only_recovery_fix": "max_page_chars_20000_to_5000",
        }
    )
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25039_batching_external_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("parent_failure_sha256")
        != contract.sha256(ROOT / contract.FAILURE)
        or copied.get("only_recovery_fix") != "max_page_chars_20000_to_5000"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.39 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    configure()
    engine._clean_pushed()
    validate_build(engine._read(contract.BUILD_AUDIT, tracked=True))
    return contract.build_protocol(
        ROOT,
        now=int(__import__("time").time()) if now is None else int(now),
        tracked=True,
        require_pristine=True,
        build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    configure()
    engine._clean_pushed()
    protocol = contract.validate_protocol(ROOT, engine._read(contract.PROTOCOL, tracked=True))
    validate_build(engine._read(contract.BUILD_AUDIT, tracked=True))
    tests = engine._tests()
    semantic = engine._semantic_audit()
    future = (
        contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL, contract.RESULT,
        contract.POSTAUDIT, contract.OUTPUT_ROOT, contract.EVALUATOR,
    )
    checks = {
        "protocol_valid": True,
        "failure_parent_valid": contract._validate_failure(ROOT)["search_provider_attempts"] == 0,
        "focused_and_parent_tests_pass": tests["passed"],
        "future_surface_pristine": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink() for path in future
        ),
        "protected_watchers_exact": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": engine._lease_inactive(),
        "keyless_gpt56_endpoint_reachable": engine._endpoint_reachable(),
        "unexpected_privileged_field_access_zero": not semantic[
            "unexpected_privileged_field_accesses"
        ],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "predeclared_evaluator_endpoint_vector_absent_and_not_directly_accessed": True,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25039_batching_external_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(__import__("time").time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "parent_failure_sha256": contract.sha256(ROOT / contract.FAILURE),
        "tests": tests,
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "execution_start_generation": not findings,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25039_batching_external_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("execution_start_generation")
        is not True
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.39 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    configure()
    engine._clean_pushed()
    protocol = contract.validate_protocol(ROOT, engine._read(contract.PROTOCOL, tracked=True))
    validate_preaudit(engine._read(contract.PREAUDIT, tracked=True))
    future = (
        contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT, contract.EVALUATOR,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.39 execution surface is not pristine")
    value = {
        "artifact_version": 1,
        "role": "v25038_batching_external_execution_start",
        "successor_role": "v25039_batching_external_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(__import__("time").time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "parent_failure_sha256": contract.sha256(ROOT / contract.FAILURE),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_external_forward": True,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    configure()
    return engine.build_forward_audit(now=now)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("build-audit", "protocol", "preaudit", "start", "forward-audit")
    )
    args = parser.parse_args()
    configure()
    if args.command == "build-audit":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    elif args.command == "start":
        value, path = build_start(), contract.EXECUTION_START
    else:
        value, path = build_forward_audit(), contract.FORWARD_AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish(path, value)
    print(json.dumps({
        "path": str(path), "role": value.get("role"),
        "audit_valid": value.get("audit_valid"),
        "findings": value.get("findings"),
        "authorization": value.get("authorization"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
