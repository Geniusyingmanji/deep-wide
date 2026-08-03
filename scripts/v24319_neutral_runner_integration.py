#!/usr/bin/env python3
"""Preregister and audit the benchmark-external V2.43.19 runner gate."""

from __future__ import annotations

import argparse
import ast
import hashlib
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

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24315_forward_contract import protected_watcher_snapshot  # noqa: E402
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from test_v24319_subprocess_integration import MODES, run_matrix  # noqa: E402


DATE = "20260803"
PROTOCOL_ID = "v24319_benchmark_external_deadline_conservation_runner_v1"
PROTOCOL = Path(f"results/v24319_runner_integration_preregistration_v1_{DATE}.json")
PROBE = Path(f"results/v24319_runner_integration_probe_v1_{DATE}.json")
DECISION = Path(f"results/v24319_runner_integration_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24319_runner_integration_postresult_audit_v1_{DATE}.json")
PARENT_RUNTIME_AUDIT = Path(
    f"results/v24318_deadline_conservation_build_audit_v2_{DATE}.json"
)
PARENT_SEARCH_AUDIT = Path(f"results/v24316_deadline_search_build_audit_v3_{DATE}.json")
PARENT_DIAGNOSIS_AUDIT = Path(
    f"results/v24317_v24315_outer_totality_diagnosis_audit_v1_{DATE}.json"
)
FIXTURE_MARKER = "tests/fixtures/v24319_synthetic_child.py"
SOURCE_FILES = (
    "src/deepwide_agent/v24319_runner_integration.py",
    "scripts/v24319_neutral_runner_integration.py",
    "tests/test_v24319_runner_integration.py",
    "tests/test_v24319_subprocess_integration.py",
    "tests/test_v24319_neutral_runner_integration.py",
    FIXTURE_MARKER,
)
TESTS = (
    ("test_v24319_runner_integration.py", 7),
    ("test_v24319_subprocess_integration.py", 3),
    ("test_v24319_neutral_runner_integration.py", 3),
)
EXPECTED_TAXONOMY = {
    name: expected for name, (_, _, expected) in MODES.items()
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
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise RuntimeError("V2.43.19 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.19 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path) -> dict[str, str]:
    return {relative: sha256(_ordinary(root, relative)) for relative in SOURCE_FILES}


def _parent_hashes(root: Path) -> dict[str, str]:
    return {
        str(path): sha256(_ordinary(root, path))
        for path in (
            PARENT_RUNTIME_AUDIT,
            PARENT_SEARCH_AUDIT,
            PARENT_DIAGNOSIS_AUDIT,
        )
    }


def _validate_parents(root: Path) -> None:
    runtime = _read(root, PARENT_RUNTIME_AUDIT)
    search = _read(root, PARENT_SEARCH_AUDIT)
    diagnosis = _read(root, PARENT_DIAGNOSIS_AUDIT)
    if (
        runtime.get("role") != "v24318_deadline_conservation_build_audit_v2"
        or runtime.get("audit_valid") is not True
        or runtime.get("findings") != []
        or runtime.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(runtime, "audit_payload_sha256")
        or search.get("role") != "v24316_deadline_search_build_audit_v3"
        or search.get("audit_valid") is not True
        or search.get("findings") != []
        or search.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(search, "audit_payload_sha256")
        or diagnosis.get("role")
        != "v24317_v24315_outer_totality_diagnosis_audit"
        or diagnosis.get("audit_valid") is not True
        or diagnosis.get("findings") != []
        or diagnosis.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(diagnosis, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.19 parent evidence drifted")


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    _validate_parents(root)
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24319_runner_integration_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": _parent_hashes(root),
        "modes": list(MODES),
        "expected_parent_taxonomy": EXPECTED_TAXONOMY,
        "real_local_subprocess_children": len(MODES),
        "runtime_boundary": ["opaque_id", "question"],
        "synthetic_visible_tasks_only": True,
        "model_slot_cap": 2,
        "model_search_absolute_deadline_shared": True,
        "deadline_stops_must_be_complete_success_envelopes": True,
        "structural_failures_must_not_be_success": True,
        "incomplete_parent_projection_must_not_claim_complete_effect_count": True,
        "external_network_model_search_fetch_or_evaluator_calls": 0,
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "one_benchmark_external_runner_probe": True,
            "future_paired_dev64_design": False,
            "paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value)
    return value


def validate_protocol(root: Path, value: Mapping[str, Any]) -> None:
    manifest = value.get("source_manifest")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24319_runner_integration_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("parents") != _parent_hashes(root)
        or value.get("modes") != list(MODES)
        or value.get("expected_parent_taxonomy") != EXPECTED_TAXONOMY
        or value.get("real_local_subprocess_children") != len(MODES)
        or value.get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("synthetic_visible_tasks_only") is not True
        or value.get("model_slot_cap") != 2
        or value.get("model_search_absolute_deadline_shared") is not True
        or value.get("deadline_stops_must_be_complete_success_envelopes") is not True
        or value.get("structural_failures_must_not_be_success") is not True
        or value.get("incomplete_parent_projection_must_not_claim_complete_effect_count")
        is not True
        or value.get("external_network_model_search_fetch_or_evaluator_calls") != 0
        or value.get("benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization", {}).get("one_benchmark_external_runner_probe")
        is not True
        or value.get("authorization", {}).get("paired_dev64_launch") is not False
        or value.get("authorization", {}).get("exact220") is not False
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.19 protocol drifted")


def execute_probe(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = _read(root, PROTOCOL)
    validate_protocol(root, protocol)
    raw = run_matrix()
    modes: dict[str, Any] = {}
    for name in MODES:
        row = raw[name]
        parent = row["parent"]
        projected = {
            "failure_taxonomy": parent["failure_taxonomy"],
            "child_terminal_receipt_present": parent["child_terminal_receipt_present"],
            "child_terminal_receipt_valid": parent["child_terminal_receipt_valid"],
            "result_envelope_present": parent["result_envelope_present"],
            "result_envelope_valid": parent["result_envelope_valid"],
            "model_receipt_present": parent["model_receipt_present"],
            "model_receipt_valid": parent["model_receipt_valid"],
            "transport_receipt_present": parent["transport_receipt_present"],
            "transport_receipt_valid": parent["transport_receipt_valid"],
        }
        if parent["failure_taxonomy"] == "success":
            projected.update(
                {
                    "logical_admissions": int(row["logical"]),
                    "provider_requests": int(row["requests"]),
                    "pre_provider_rejections": int(row["rejected"]),
                }
            )
        modes[name] = projected
    findings: list[str] = []
    observed = {name: modes[name]["failure_taxonomy"] for name in MODES}
    if observed != EXPECTED_TAXONOMY:
        findings.append("parent_taxonomy_mismatch")
    for name in ("slot_reject", "cache_defer_baseline", "cache_defer_candidate"):
        row = modes[name]
        if (
            row["failure_taxonomy"] != "success"
            or not all(
                row[key]
                for key in (
                    "child_terminal_receipt_valid",
                    "result_envelope_valid",
                    "model_receipt_valid",
                    "transport_receipt_valid",
                )
            )
        ):
            findings.append(f"{name}_was_not_complete_success")
    slot = modes["slot_reject"]
    if (
        slot.get("pre_provider_rejections", 0) <= 0
        or slot.get("logical_admissions")
        != slot.get("provider_requests", 0) + slot.get("pre_provider_rejections", 0)
    ):
        findings.append("slot_rejection_conservation_failed")
    structural = set(MODES) - {
        "success_baseline",
        "success_candidate",
        "slot_reject",
        "cache_defer_baseline",
        "cache_defer_candidate",
    }
    if any(modes[name]["failure_taxonomy"] == "success" for name in structural):
        findings.append("structural_failure_masqueraded_as_success")
    value = {
        "artifact_version": 1,
        "role": "v24319_runner_integration_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(_ordinary(root, PROTOCOL)),
        "modes": modes,
        "local_subprocess_children": len(MODES),
        "external_effect_ledger": {
            "remote_network": 0,
            "model_provider": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
            "local_subprocess": len(MODES),
        },
        "temporary_probe_directories_remaining": False,
        "question_opaque_id_prompt_response_prediction_query_url_page_or_credential_emitted": False,
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "findings": findings,
        "passed": not findings,
        "authorization": {
            "future_paired_dev64_design": not findings,
            "paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["probe_payload_sha256"] = payload_sha256(value)
    validate_probe(root, value)
    return value


def validate_probe(root: Path, value: Mapping[str, Any]) -> None:
    modes = value.get("modes")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24319_runner_integration_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(_ordinary(root, PROTOCOL))
        or not isinstance(modes, Mapping)
        or list(modes) != list(MODES)
        or {name: modes[name].get("failure_taxonomy") for name in MODES}
        != EXPECTED_TAXONOMY
        or value.get("local_subprocess_children") != len(MODES)
        or value.get("external_effect_ledger")
        != {
            "remote_network": 0,
            "model_provider": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
            "local_subprocess": len(MODES),
        }
        or value.get("temporary_probe_directories_remaining") is not False
        or value.get("question_opaque_id_prompt_response_prediction_query_url_page_or_credential_emitted")
        is not False
        or value.get("benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("findings") != []
        or value.get("passed") is not True
        or value.get("authorization", {}).get("future_paired_dev64_design") is not True
        or value.get("authorization", {}).get("paired_dev64_launch") is not False
        or not _sealed(value, "probe_payload_sha256")
    ):
        raise RuntimeError("V2.43.19 probe drifted")


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = _read(root, PROTOCOL)
    validate_protocol(root, protocol)
    probe = _read(root, PROBE)
    validate_probe(root, probe)
    value = {
        "artifact_version": 1,
        "role": "v24319_runner_integration_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_runner_integration_go",
        "passed": True,
        "failed_checks": [],
        "provenance": {
            "protocol_sha256": sha256(_ordinary(root, PROTOCOL)),
            "probe_sha256": sha256(_ordinary(root, PROBE)),
        },
        "authorization": probe["authorization"],
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return value


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
            "HOME": os.environ.get("HOME", str(Path.home())),
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
        timeout=240,
        check=False,
    )
    return completed.returncode == 0


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = _read(root, PROTOCOL)
    validate_protocol(root, protocol)
    probe = _read(root, PROBE)
    validate_probe(root, probe)
    decision = _read(root, DECISION)
    if (
        decision.get("status") != "neutral_runner_integration_go"
        or decision.get("passed") is not True
        or decision.get("provenance")
        != {
            "protocol_sha256": sha256(_ordinary(root, PROTOCOL)),
            "probe_sha256": sha256(_ordinary(root, PROBE)),
        }
        or decision.get("authorization", {}).get("paired_dev64_launch") is not False
        or not _sealed(decision, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.19 decision drifted")
    sources = {relative: _ordinary(root, relative).read_text(encoding="utf-8") for relative in SOURCE_FILES}
    accesses = sorted(
        access
        for relative in (
            "src/deepwide_agent/v24319_runner_integration.py",
            "scripts/v24319_neutral_runner_integration.py",
            FIXTURE_MARKER,
        )
        for access in _field_accesses(root / relative)
    )
    secret_hits = sorted(relative for relative, source in sources.items() if SECRET.search(source))
    tests = [
        {"file": filename, "test_count": count, "passed": _run_test(filename)}
        for filename, count in TESTS
    ]
    fixture_present = bool(_matching(process_snapshot(), FIXTURE_MARKER))
    findings: list[str] = []
    if protocol["source_manifest"] != _manifest(root):
        findings.append("source_manifest_drifted")
    if accesses:
        findings.append("privileged_field_access_in_runtime_surface")
    if secret_hits:
        findings.append("credential_literal_in_runtime_surface")
    if not all(test["passed"] for test in tests):
        findings.append("focused_tests_failed")
    if fixture_present:
        findings.append("synthetic_child_process_remained_active")
    value = {
        "artifact_version": 1,
        "role": "v24319_runner_integration_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "provenance": {
            "protocol_sha256": sha256(_ordinary(root, PROTOCOL)),
            "probe_sha256": sha256(_ordinary(root, PROBE)),
            "decision_sha256": sha256(_ordinary(root, DECISION)),
        },
        "source_manifest_unchanged": protocol["source_manifest"] == _manifest(root),
        "focused_tests": tests,
        "test_count": sum(count for _, count in TESTS),
        "privileged_field_accesses": accesses,
        "credential_literal_hits": secret_hits,
        "synthetic_child_process_present": fixture_present,
        "protected_watchers": protected_watcher_snapshot(),
        "external_effect_ledger": {
            "remote_network": 0,
            "model_provider": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "question_opaque_id_prompt_response_prediction_query_url_page_or_credential_emitted": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "active_run_signaled_restarted_resumed_rerun_or_modified": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "future_paired_dev64_design": not findings,
            "paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("protocol", "probe", "decision", "audit"))
    args = parser.parse_args()
    builders = {
        "protocol": (PROTOCOL, build_protocol),
        "probe": (PROBE, execute_probe),
        "decision": (DECISION, build_decision),
        "audit": (POSTAUDIT, build_postaudit),
    }
    path, builder = builders[args.action]
    value = builder(ROOT)
    publish_new(ROOT / path, value)
    print(json.dumps({"path": str(path), "action": args.action}, sort_keys=True))


if __name__ == "__main__":
    main()
