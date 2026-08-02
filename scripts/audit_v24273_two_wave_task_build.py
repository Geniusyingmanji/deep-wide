#!/usr/bin/env python3
"""Build-only label-blind audit for the V2.42.73 task integration."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


PARENT_RESULT = Path("results/v24271_keyless_dev64_result_v1_20260802.json")
PARENT_BUILD_AUDIT = Path("results/v24272_two_wave_build_audit_v1_20260802.json")
OUTPUT = Path("results/v24273_two_wave_task_build_audit_v1_20260802.json")
SURFACES = (
    Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
    Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
    Path("src/deepwide_agent/v24273_two_wave_task_runtime.py"),
)
FORBIDDEN_IMPORTS = frozenset(
    {
        "asyncio",
        "ctypes",
        "multiprocessing",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
    }
)
FORBIDDEN_CALLS = frozenset({"__import__", "compile", "eval", "exec", "open"})
FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "answer_key",
        "category",
        "evaluator",
        "ground_truth",
        "gold",
        "mapping",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
ALLOWED_STRICT_FALSE_ATTESTATION = (
    "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
REPORT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "parent_no_go_result",
        "parent_build_audit",
        "surface_manifest",
        "static_audit",
        "integration_contract",
        "claim_scope",
        "authorization",
        "findings",
        "audit_valid",
        "audit_payload_sha256",
    }
)


def _literal_key_accesses(tree: ast.AST) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        key: str | None = None
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
        if key in FORBIDDEN_EXACT_KEYS:
            values.append({"line": int(node.lineno), "key": key})
    return values


def _imports(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            values.add((node.module or "").split(".")[0])
    return values


def _surface(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = _imports(tree)
    direct_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in {"getenv", "environ", "system", "popen", "run", "Popen"}
    }
    privileged = _literal_key_accesses(tree)
    script_imports = sorted(
        name
        for name in imports
        if name == "scripts" or name.startswith("scripts.")
    )
    attestation_count = source.count(ALLOWED_STRICT_FALSE_ATTESTATION)
    value = {
        "sha256": sha256(path),
        "forbidden_imports": sorted(imports.intersection(FORBIDDEN_IMPORTS)),
        "forbidden_direct_calls": sorted(direct_calls.intersection(FORBIDDEN_CALLS)),
        "forbidden_process_or_environment_attributes": sorted(attributes),
        "script_imports": script_imports,
        "privileged_exact_key_accesses": privileged,
        "strict_false_composite_attestation_occurrences": attestation_count,
        "credential_literal_present": SECRET.search(source) is not None,
        "concrete_opaque_id_present": OPAQUE.search(source) is not None,
        "evaluator_or_historical_control_path_literal_present": any(
            marker in source
            for marker in (
                "overall_20250916",
                "evaluator_mapping.jsonl",
                "MAPPING_PATH",
                "CONTROL_RUNTIME",
                "CONTROL_RESULT",
            )
        ),
    }
    value["passed"] = not any(
        (
            value["forbidden_imports"],
            value["forbidden_direct_calls"],
            value["forbidden_process_or_environment_attributes"],
            script_imports,
            privileged,
            value["credential_literal_present"],
            value["concrete_opaque_id_present"],
            value["evaluator_or_historical_control_path_literal_present"],
        )
    )
    return value


def validate_report(value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    parent = value.get("parent_no_go_result")
    parent_audit = value.get("parent_build_audit")
    static = value.get("static_audit")
    contract = value.get("integration_contract")
    authorization = value.get("authorization")
    if (
        set(value) != REPORT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24273_two_wave_task_build_audit"
        or value.get("label_blind") is not True
        or not isinstance(parent, dict)
        or parent.get("status") != "development_gate_no_go"
        or parent.get("decision_passed") is not False
        or not isinstance(parent_audit, dict)
        or parent_audit.get("audit_valid") is not True
        or not isinstance(static, dict)
        or static.get("all_surfaces_passed") is not True
        or not isinstance(contract, dict)
        or contract.get("runtime_boundary") != ["opaque_id", "question"]
        or contract.get("maximum_queries") != 4
        or contract.get("maximum_fetch_attempts") != 10
        or contract.get("cache_serve_network_fetches") != 0
        or contract.get("control_flow_interruptions_converted_to_predictions")
        is not False
        or contract.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or value.get("claim_scope")
        != "build_only_runtime_integration_not_benchmark_quality_reward_or_causal_credit"
        or not isinstance(authorization, dict)
        or any(authorization.values())
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.73 task build audit drifted")


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = read_object(root / PARENT_RESULT)
    parent_audit = read_object(root / PARENT_BUILD_AUDIT)
    if (
        parent.get("status") != "development_gate_no_go"
        or parent.get("decision", {}).get("passed") is not False
        or parent_audit.get("role") != "v24272_two_wave_build_audit"
        or parent_audit.get("audit_valid") is not True
        or parent_audit.get("authorization", {}).get("dev_benchmark_launch")
        is not False
    ):
        raise RuntimeError("V2.42.73 parent evidence drifted")
    surfaces = {str(relative): _surface(root, relative) for relative in SURFACES}
    findings = [name for name, result in surfaces.items() if not result["passed"]]
    value = {
        "artifact_version": 1,
        "role": "v24273_two_wave_task_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parent_no_go_result": {
            "path": str(PARENT_RESULT),
            "sha256": sha256(root / PARENT_RESULT),
            "status": parent["status"],
            "decision_passed": parent["decision"]["passed"],
        },
        "parent_build_audit": {
            "path": str(PARENT_BUILD_AUDIT),
            "sha256": sha256(root / PARENT_BUILD_AUDIT),
            "audit_valid": parent_audit["audit_valid"],
        },
        "surface_manifest": {name: result["sha256"] for name, result in surfaces.items()},
        "static_audit": {
            "surfaces": surfaces,
            "all_surfaces_passed": not findings,
            "injected_clients_are_only_effect_surface": True,
            "composite_receipt_attestation_is_not_benchmark_metadata": True,
        },
        "integration_contract": {
            "runtime_boundary": ["opaque_id", "question"],
            "maximum_queries": 4,
            "maximum_fetch_attempts": 10,
            "cache_serve_network_fetches": 0,
            "redirect_aliases_supported": True,
            "search_or_fetch_exception_returns_content_free_failed_receipt": True,
            "control_flow_interruptions_converted_to_predictions": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "claim_scope": "build_only_runtime_integration_not_benchmark_quality_reward_or_causal_credit",
        "authorization": {
            "dev_benchmark_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission": False,
            "sota_claim": False,
            "training_credit_assignment": False,
        },
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_report(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / OUTPUT, report)
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}))
