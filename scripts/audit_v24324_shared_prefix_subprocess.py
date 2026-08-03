#!/usr/bin/env python3
"""Freeze the benchmark-external V2.43.24 shared-prefix subprocess gate."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from test_v24324_shared_prefix_subprocess import (  # noqa: E402
    MODES,
    run_matrix,
)


DATE = "20260803"
ROLE = "v24324_shared_prefix_subprocess_build_audit"
OUTPUT = Path(f"results/v24324_shared_prefix_subprocess_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24323_shared_prefix_cell_entropy_build_audit_v1_{DATE}.json")
SOURCE_FILES = (
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "src/deepwide_agent/v24324_shared_prefix_runner.py",
    "tests/fixtures/v24324_shared_prefix_child.py",
    "tests/test_v24324_shared_prefix_subprocess.py",
    "scripts/audit_v24324_shared_prefix_subprocess.py",
)
RUNTIME_FILES = SOURCE_FILES[:5]
TESTS = (
    ("test_v24324_shared_prefix_subprocess.py", 5),
    ("test_v24323_shared_prefix_cell_entropy.py", 8),
    ("test_v24309_runner_exit_integration.py", 5),
    ("test_v24308_child_exit_observability.py", 9),
)
EXPECTED_TAXONOMY = {
    name: expected for name, (_, _, expected) in MODES.items()
}
EXTERNAL_ZERO = {
    "remote_network": 0,
    "model_provider": 0,
    "hosted_search": 0,
    "fetch": 0,
    "evaluator": 0,
}
PRIVILEGED = frozenset(
    {
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)
NETWORK_IMPORTS = frozenset(
    {"aiohttp", "httpx", "openai", "requests", "socket", "urllib"}
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    relative = Path(relative)
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.43.24 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.24 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _field_accesses(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    output: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in PRIVILEGED:
            output.append(f"{path.relative_to(ROOT)}:{node.lineno}:{key}")
    return output


def _network_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    output: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for name in names:
            root = name.split(".", 1)[0]
            if root in NETWORK_IMPORTS:
                output.append(f"{path.relative_to(ROOT)}:{node.lineno}:{name}")
    return output


def _run_test(filename: str) -> bool:
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
            filename,
        ],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    return completed.returncode == 0


def _parent_projection(parent: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: parent[key]
        for key in (
            "failure_taxonomy",
            "child_terminal_receipt_present",
            "child_terminal_receipt_valid",
            "result_envelope_present",
            "result_envelope_valid",
            "model_receipt_present",
            "model_receipt_valid",
            "transport_receipt_present",
            "transport_receipt_valid",
        )
    }


def build(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = _read(root, PARENT)
    if (
        parent.get("role") != "v24323_shared_prefix_cell_entropy_build_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or parent.get("authorization", {}).get("shared_prefix_runtime_design")
        is not True
        or parent.get("authorization", {}).get("runtime_or_benchmark_launch")
        is not False
        or not _sealed(parent, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.24 parent audit drifted")

    manifest = {
        relative: sha256(_ordinary(root, relative)) for relative in SOURCE_FILES
    }
    source_text = {
        relative: _ordinary(root, relative).read_text(encoding="utf-8")
        for relative in SOURCE_FILES
    }
    accesses = sorted(
        access
        for relative in RUNTIME_FILES
        for access in _field_accesses(_ordinary(root, relative))
    )
    network_imports = sorted(
        hit
        for relative in RUNTIME_FILES
        for hit in _network_imports(_ordinary(root, relative))
    )
    secret_hits = sorted(
        relative for relative, text in source_text.items() if SECRET.search(text)
    )
    test_results = [
        {"file": filename, "test_count": count, "passed": _run_test(filename)}
        for filename, count in TESTS
    ]

    raw = run_matrix()
    observed_taxonomy = {
        name: raw[name]["parent"]["failure_taxonomy"] for name in MODES
    }
    modes = {
        name: {
            "expected_taxonomy": EXPECTED_TAXONOMY[name],
            **_parent_projection(raw[name]["parent"]),
        }
        for name in MODES
    }
    pair = raw["pair"]
    baseline = raw["baseline_success"]
    candidate = raw["candidate_success"]
    unreliable = raw["candidate_unreliable"]
    watchers = protected_watcher_snapshot()
    serialized = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    findings: list[str] = []
    if observed_taxonomy != EXPECTED_TAXONOMY:
        findings.append("parent_taxonomy_mismatch")
    if not all(item["passed"] for item in test_results):
        findings.append("focused_or_dependency_regression_failed")
    if accesses:
        findings.append("privileged_field_access_in_runtime_surface")
    if network_imports:
        findings.append("network_capable_import_in_runtime_surface")
    if secret_hits:
        findings.append("credential_literal_in_source_surface")
    if watchers != parent.get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    if (
        pair.get("prefix_producer_execution_count") != 1
        or pair.get("shared_prefix_file_unchanged_across_both_branches") is not True
        or pair.get("total_repeated_upstream_effects") != 0
        or pair.get("external_effect_ledger") != EXTERNAL_ZERO
        or pair.get("v24323_pair_contract", {}).get(
            "shared_plan_query_first_wave_and_core_evidence_exact"
        )
        is not True
    ):
        findings.append("shared_prefix_or_effect_conservation_failed")
    if (
        baseline["branch"].get("context_action") != "core_only"
        or candidate["branch"].get("context_action") != "append_reserve_support"
        or candidate["branch"].get("admission_receipt", {}).get("disposition")
        != "admit_support"
        or unreliable["branch"].get("context_action") != "core_only"
        or unreliable["branch"].get("admission_receipt", {}).get("disposition")
        != "quarantine_low_reliability"
        or unreliable["branch"].get("admission_receipt", {})
        .get("anonymous_evidence", {})
        .get("evidence_chars")
        != 1_000_000
    ):
        findings.append("candidate_context_or_entropy_admission_drifted")
    if (
        OPAQUE.search(serialized)
        or "deep2wide_result_" in serialized
        or '\"question\":' in serialized
        or '\"prediction\":' in serialized
    ):
        findings.append("content_identifier_or_task_content_in_probe")
    process_present = bool(
        _matching(process_snapshot(), "tests/fixtures/v24324_shared_prefix_child.py")
        or _matching(
            process_snapshot(), "tests/test_v24324_shared_prefix_subprocess.py"
        )
    )
    if process_present:
        findings.append("subprocess_or_test_process_remained_active")

    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_audit": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "focused_and_dependency_tests": test_results,
        "test_count": sum(count for _, count in TESTS),
        "subprocess_fault_matrix": {
            "modes": modes,
            "observed_taxonomy": observed_taxonomy,
            "expected_taxonomy": EXPECTED_TAXONOMY,
            "exact_taxonomy_match": observed_taxonomy == EXPECTED_TAXONOMY,
            "authoritative_probe_local_children": len(MODES),
            "focused_test_local_children": len(MODES),
            "total_local_children_this_audit": len(MODES) * 2,
            "temporary_directories_remaining": False,
        },
        "shared_prefix_observation": {
            "prefix_bundle_payload_sha256": raw["prefix_bundle"][
                "bundle_payload_sha256"
            ],
            "prefix_file_sha256": raw["prefix_file_sha256"],
            "producer_execution_count": pair["prefix_producer_execution_count"],
            "file_unchanged_across_both_branches": pair[
                "shared_prefix_file_unchanged_across_both_branches"
            ],
            "plan_query_first_wave_core_evidence_exact": pair[
                "v24323_pair_contract"
            ]["shared_plan_query_first_wave_and_core_evidence_exact"],
            "total_repeated_upstream_effects": pair[
                "total_repeated_upstream_effects"
            ],
        },
        "context_admission_observation": {
            "baseline_context_action": baseline["branch"]["context_action"],
            "candidate_context_action": candidate["branch"]["context_action"],
            "candidate_disposition": candidate["branch"]["admission_receipt"][
                "disposition"
            ],
            "candidate_conditional_entropy_reduction_nats": candidate["branch"][
                "admission_receipt"
            ]["conditional_entropy_reduction_nats"],
            "unreliable_million_character_context_action": unreliable["branch"][
                "context_action"
            ],
            "unreliable_million_character_disposition": unreliable["branch"][
                "admission_receipt"
            ]["disposition"],
            "cross_artifact_receipt_drift_fails_closed": True,
        },
        "external_effect_ledger": dict(pair["external_effect_ledger"]),
        "privileged_field_accesses": accesses,
        "network_capable_imports": network_imports,
        "credential_literal_hits": secret_hits,
        "subprocess_or_test_process_present": process_present,
        "protected_watchers": watchers,
        "source_policy": {
            "benchmark_external": True,
            "runtime_input_question_or_opaque_id": False,
            "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "active_benchmark_or_watcher_signaled_restarted_or_modified": False,
        },
        "claim_scope": {
            "real_local_subprocess_shared_prefix_boundary": True,
            "one_prefix_file_used_unchanged_by_both_branches": True,
            "upstream_plan_search_fetch_not_repeated_by_branches": True,
            "candidate_context_action_bound_to_entropy_admission": True,
            "synthesis_randomness_shared": False,
            "reserve_effect_fully_causally_identified": False,
            "benchmark_quality_improvement": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_uncontaminated_paired_benchmark_design": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate(value)
    return value


def validate(value: Mapping[str, Any]) -> None:
    if (
        value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("subprocess_fault_matrix", {}).get("exact_taxonomy_match")
        is not True
        or value.get("test_count") != 27
        or not all(
            item.get("passed") is True
            for item in value.get("focused_and_dependency_tests", [])
        )
        or value.get("external_effect_ledger") != EXTERNAL_ZERO
        or value.get("privileged_field_accesses") != []
        or value.get("network_capable_imports") != []
        or value.get("credential_literal_hits") != []
        or value.get("subprocess_or_test_process_present") is not False
        or value.get("authorization", {}).get(
            "fresh_uncontaminated_paired_benchmark_design"
        )
        is not True
        or value.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.24 audit drifted")


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {"path": str(OUTPUT), "audit_valid": report["audit_valid"]},
            sort_keys=True,
        )
    )
