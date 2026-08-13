#!/usr/bin/env python3
"""Build, preregister, audit, and authorize V2.53.76 exact-220."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25375_schema_total_changed_safe_runtime as runtime  # noqa: E402
from deepwide_agent import v25376_changed_safe_exact220_contract as contract  # noqa: E402
from scripts import control_v25267_production_only_exact220 as base  # noqa: E402
from scripts import audit_v25136_sparse_production_build as semantic  # noqa: E402


BUILD_ROLE = "v25376_changed_safe_exact220_build_audit"
PREAUDIT_ROLE = "v25377_changed_safe_exact220_preactivation_audit"
START_ROLE = "v25377_changed_safe_exact220_execution_start"
TEST_SUITES = (
    ("test_v25376_changed_safe_exact220.py", 10),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25369_changed_safe_verified_coordinate_edit.py", 8),
    ("test_v25360_quote_coordinate_partial_field_record.py", 8),
    ("test_v25354_pre_effect_query_compatible_grounded_fact_runtime.py", 6),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(count for _pattern, count in TEST_SUITES)


def configure() -> None:
    base.contract = contract
    base.visible_schema = runtime.exact_schema
    base.TEST_SUITES = TEST_SUITES
    base.EXPECTED_TESTS = EXPECTED_TESTS
    base.validate_build = validate_build
    base.validate_preaudit = validate_preaudit


def _schema_counts() -> dict[str, int]:
    counts = {name: 0 for name in sorted(runtime.SCHEMA_SOURCES)}
    limits = runtime.score.ScoreFirstLimits(**contract.LIMITS)
    for task in contract.task_vector(ROOT):
        _plan, _observation, source = runtime.projected_plan(
            {}, task["question"], limits
        )
        counts[source] += 1
    return counts


def _direct_privileged_accesses() -> list[dict[str, str]]:
    fields = {
        "category",
        "question_type",
        "task_category",
        "ground_truth",
        "answer_key",
        "split",
        "score",
        "reward",
    }
    output: list[dict[str, str]] = []
    for relative in (contract.CONTRACT, contract.RUNNER, contract.RUNTIME):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key: object | None = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            if isinstance(key, str) and key in fields:
                output.append({"path": str(relative), "field": key})
    return output


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    configure()
    value = base.build_audit(now=now, require_clean=require_clean)
    copied = dict(value)
    copied.pop("audit_payload_sha256", None)
    counts = _schema_counts()
    parent = contract.parent_receipts(ROOT, tracked=require_clean)
    closure = contract.forward_dependency_closure(ROOT)
    findings = semantic._semantic_findings(closure)
    checks = dict(copied["checks"])
    checks.update(
        {
            "changed_safe_mechanism_parent_bound": bool(parent),
            "schema_total_projected_plan_reachable_220_of_220": sum(counts.values()) == 220,
            "schema_sources_exact194_expanded21_generic5": counts
            == {
                "exact_visible": 194,
                "expanded_visible": 21,
                "generic_result": 5,
                "provider_plan": 0,
            },
            "candidate_is_only_scored_prediction": contract.source_policy()[
                "scored_prediction_is_changed_safe_candidate"
            ],
            "candidate_has_zero_independent_model_effect": contract.source_policy()[
                "candidate_has_no_independent_model_or_sampling_effect"
            ],
            "truthful_query4_fetch14_model3_caps": contract.PHYSICAL_CAPS
            == {
                "queries_per_task": 4,
                "fetches_per_task": 14,
                "model_forwards_per_task": 3,
            },
            "direct_runtime_privileged_access_zero": not _direct_privileged_accesses(),
            "semantic_privileged_evaluator_credential_findings_zero": (
                findings["privileged_runtime_field_accesses"] == []
                and findings["evaluator_capabilities"] == []
                and findings["credential_literal_hits"] == []
            ),
        }
    )
    # The inherited check describes its old production-only treatment and old
    # four-model cap.  Replace those two names with exact successor assertions.
    checks.pop("production_only_no_candidate_treatment", None)
    checks.pop("truthful_physical_caps_fixed", None)
    failed = sorted(name for name, passed in checks.items() if not passed)
    copied.update(
        {
            "role": BUILD_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "schema_source_counts": counts,
            "changed_safe_parent_receipts": parent,
            "semantic_audit": findings,
            "direct_runtime_privileged_accesses": _direct_privileged_accesses(),
            "checks": checks,
            "findings": failed,
            "audit_valid": not failed,
            "source_policy": contract.source_policy(),
            "authorization": {
                "protocol_generation_after_build_commit_push": not failed,
                "external_forward": False,
                "postfreeze_official_evaluator": False,
                "leaderboard_or_sota": False,
            },
        }
    )
    return validate_build(contract.seal(copied, "audit_payload_sha256"))


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != BUILD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("schema_source_counts")
        != {
            "exact_visible": 194,
            "expanded_visible": 21,
            "generic_result": 5,
            "provider_plan": 0,
        }
        or copied.get("semantic_audit", {}).get("privileged_runtime_field_accesses") != []
        or copied.get("semantic_audit", {}).get("evaluator_capabilities") != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits") != []
        or copied.get("direct_runtime_privileged_accesses") != []
        or copied.get("source_policy") != contract.source_policy()
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.53.76 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    configure()
    return base.build_protocol(now=now)


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    configure()
    value = base.build_preaudit(now=now)
    copied = dict(value)
    copied.pop("audit_payload_sha256", None)
    copied["role"] = PREAUDIT_ROLE
    return validate_preaudit(contract.seal(copied, "audit_payload_sha256"))


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
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
        raise RuntimeError("V2.53.77 preactivation audit drifted")
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
    parser.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start"))
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
