#!/usr/bin/env python3
"""Clean-build audit for the V2.46.86 World Bank target-value runtime.

This audit reads only repository sources, git/process/lease state, and
synthetic tests.  It opens no benchmark manifest, question, prediction, gold,
mapping, category, split, score, reward, evaluator output, or credential.  It
performs no model, search, fetch, World Bank, benchmark, or evaluator effect.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24686_worldbank_target_value_runtime as runtime  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402


DATE = "20260806"
AUDIT = Path(f"results/v24687_worldbank_target_value_build_audit_v1_{DATE}.json")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v24686_worldbank_target_value_runtime.py"
)
SOURCES = (
    RUNTIME_SOURCE,
    Path("tests/test_v24686_worldbank_target_value_runtime.py"),
    Path("scripts/audit_v24687_worldbank_target_value_build.py"),
    Path("tests/test_audit_v24687_worldbank_target_value_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24675_expanded_visible_schema.py"), 8, 120),
    (Path("tests/test_v24677_expanded_visible_schema_runtime.py"), 8, 180),
    (Path("tests/test_v24686_worldbank_target_value_runtime.py"), 10, 120),
    (Path("tests/test_audit_v24687_worldbank_target_value_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 32


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _run_test(path: Path, timeout: int) -> tuple[bool, int]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            path.name,
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode == 0, int(match.group(1)) if match else 0


def _implementation_valid() -> bool:
    question = (
        "Use public web sources to return one Markdown table about these countries:\n"
        "<COUNTRIES>\n"
        "1. Alpha [AAA]\n2. Bravo [BBB]\n3. Charlie [CCC]\n4. Delta [DDD]\n"
        "</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        "Country | Metric A [SP.DYN.LE00.IN] @2022 | "
        "Metric B [IT.NET.USER.ZS] @2022\n"
        "Use the World Bank API values. Preserve the decimal representation returned "
        "by the official API. Use Unknown when unavailable. Return one table only."
    )
    contract = runtime._visible_contract(question)
    requests = runtime.target_lookup_requests(contract)
    return (
        runtime.GENERIC_FETCH_CAP == 2
        and runtime.TARGETED_LOOKUP_CAP == 8
        and contract["frozen_parser_columns"] == []
        and contract["expanded_parser_columns"] == contract["columns"]
        and len(requests) == 8
        and len({item["member_label"] for item in requests}) == 8
        and all("api.worldbank.org" in item["url"] for item in requests)
    )


def _active() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = ("v24686", "v24687", "worldbank_target_value")
    return any(
        any(marker in line for marker in markers)
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line
        and "audit_v24687_worldbank_target_value_build.py" not in line
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    accesses, imports = common.ast_findings(RUNTIME_SOURCE)
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    suites: list[dict[str, Any]] = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed = _run_test(path, timeout)
        suites.append(
            {
                "path": str(path),
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": passed and observed == expected,
            }
        )
    test_count = sum(item["observed_test_count"] for item in suites)
    head = common._git("rev-parse", "HEAD")
    remote = common._git("rev-parse", "target/main")
    clean = common._git("status", "--porcelain") == ""
    tracked = all(common._tracked(path) for path in SOURCES)
    watchers = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": common._watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in common.EXPECTED_WATCHERS
    ]
    lease_inactive = common._lease_inactive()
    implementation_valid = _implementation_valid()
    active = _active()
    findings: list[str] = []
    if head != remote:
        findings.append("v24687_source_commit_not_pushed")
    if not clean:
        findings.append("v24687_source_worktree_not_clean")
    if not tracked:
        findings.append("v24687_source_not_tracked")
    if not implementation_valid:
        findings.append("v24686_target_value_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24675_v24677_v24686_v24687_regression_failed")
    if accesses:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24686_or_v24687_process_active")
    value = {
        "artifact_version": 1,
        "role": "v24687_worldbank_target_value_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "mechanism": {
            "runtime_policy": runtime.POLICY_ID,
            "three_arm_design": list(runtime.ARMS),
            "shared_plan_search_generic_fetch_evidence_prefix": True,
            "generic_fetch_cap": runtime.GENERIC_FETCH_CAP,
            "exact_target_lookup_cap": runtime.TARGETED_LOOKUP_CAP,
            "exact_address_tuple": ["ISO3", "indicator", "year"],
            "official_decimal_lexeme_preserved": True,
            "nonempty_incorrect_value_may_be_corrected": True,
            "unsupported_value_projects_to_unknown": True,
            "completion_rechecked_after_admission": True,
            "entropy_routes_or_assigns_credit": False,
            "implementation_valid": implementation_valid,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": suites,
            "test_count": test_count,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_worldbank_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "passed": not accesses and not imports and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "v24686_or_v24687_process_active": active,
            "external_population_or_benchmark_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "source_policy": {
            "mapping_gold_category_split_question_type_score_reward_or_evaluator_read": False,
            "benchmark_manifest_question_prediction_or_private_result_opened_by_audit": False,
            "remote_network_model_search_fetch_worldbank_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_worldbank_population_and_protocol_design": not findings,
            "population_gold_or_provenance_publication": False,
            "preactivation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24687_worldbank_target_value_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("mechanism", {}).get("implementation_valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("protected_watchers_unchanged")
        is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive")
        is not True
        or copied.get("runtime_state", {}).get("v24686_or_v24687_process_active")
        is not False
        or copied.get("authorization")
        != {
            "fresh_disjoint_worldbank_population_and_protocol_design": True,
            "population_gold_or_provenance_publication": False,
            "preactivation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.87 build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    result = build_audit()
    validate_audit(result)
    publish_new(ROOT / AUDIT, result)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": result["audit_valid"],
                "findings": result["findings"],
                "test_count": result["tests"]["test_count"],
            },
            sort_keys=True,
        )
    )
