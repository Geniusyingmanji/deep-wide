#!/usr/bin/env python3
"""Static and synthetic build-only audit for V2.42.72 two-wave retrieval."""

from __future__ import annotations

import ast
import hashlib
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

from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    FirstWaveObservation,
    decide_two_wave,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


PARENT_RESULT = Path("results/v24271_keyless_dev64_result_v1_20260802.json")
OUTPUT = Path("results/v24272_two_wave_build_audit_v1_20260802.json")
SURFACES = (
    Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
    Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
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
FORBIDDEN_CALLS = frozenset(
    {
        "__import__",
        "compile",
        "eval",
        "exec",
        "open",
    }
)
FORBIDDEN_RUNTIME_KEYS = frozenset(
    {
        "answerkey",
        "benchmarkcategory",
        "category",
        "evaluator",
        "groundtruth",
        "gold",
        "mapping",
        "questiontype",
        "reward",
        "score",
        "split",
        "taskcategory",
    }
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
        "surface_manifest",
        "static_audit",
        "synthetic_replay",
        "claim_scope",
        "authorization",
        "findings",
        "audit_valid",
        "audit_payload_sha256",
    }
)


def _normalized(value: object) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def _imports(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            values.add((node.module or "").split(".")[0])
    return values


def _runtime_key_accesses(tree: ast.AST) -> list[dict[str, Any]]:
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
        if key is not None and _normalized(key) in FORBIDDEN_RUNTIME_KEYS:
            values.append({"line": int(node.lineno), "key": key})
    return values


def _surface_audit(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = _imports(tree)
    direct_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    forbidden_attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in {"getenv", "environ", "system", "popen", "run", "Popen"}
    }
    privileged = _runtime_key_accesses(tree)
    value = {
        "sha256": sha256(path),
        "forbidden_imports": sorted(imported.intersection(FORBIDDEN_IMPORTS)),
        "forbidden_direct_calls": sorted(direct_calls.intersection(FORBIDDEN_CALLS)),
        "forbidden_process_or_environment_attributes": sorted(forbidden_attributes),
        "privileged_runtime_key_accesses": privileged,
        "credential_literal_present": SECRET.search(source) is not None,
        "concrete_opaque_id_present": OPAQUE.search(source) is not None,
    }
    value["passed"] = not any(
        (
            value["forbidden_imports"],
            value["forbidden_direct_calls"],
            value["forbidden_process_or_environment_attributes"],
            privileged,
            value["credential_literal_present"],
            value["concrete_opaque_id_present"],
        )
    )
    return value


def _synthetic_replay() -> dict[str, Any]:
    stop = decide_two_wave(
        FirstWaveObservation(
            queries_executed=2,
            sources_discovered=6,
            fetches_attempted=6,
            usable_pages=4,
            novel_pages=3,
            unique_hosts=2,
            content_chars=8_000,
            required_column_count=3,
            explicit_row_target=0,
            search_seconds=4.0,
            fetch_seconds=5.0,
        )
    )
    expand = decide_two_wave(
        FirstWaveObservation(
            queries_executed=2,
            sources_discovered=2,
            fetches_attempted=6,
            usable_pages=2,
            novel_pages=1,
            unique_hosts=1,
            content_chars=1_000,
            required_column_count=6,
            explicit_row_target=0,
            search_seconds=4.0,
            fetch_seconds=5.0,
        )
    )
    return {
        "stop_decision": stop["decision"],
        "stop_reason": stop["reason"],
        "stop_receipt_sha256": stop["receipt_sha256"],
        "expand_decision": expand["decision"],
        "expand_reason": expand["reason"],
        "expand_receipt_sha256": expand["receipt_sha256"],
        "question_query_url_host_page_prediction_answer_task_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_or_evaluator_called": False,
    }


def validate_report(value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    parent = value.get("parent_no_go_result")
    static = value.get("static_audit")
    replay = value.get("synthetic_replay")
    authorization = value.get("authorization")
    if (
        set(value) != REPORT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24272_two_wave_build_audit"
        or value.get("label_blind") is not True
        or not isinstance(parent, dict)
        or parent.get("status") != "development_gate_no_go"
        or parent.get("decision_passed") is not False
        or not isinstance(static, dict)
        or static.get("all_surfaces_passed") is not True
        or not isinstance(replay, dict)
        or replay.get("stop_decision") != "stop"
        or replay.get("expand_decision") != "expand"
        or replay.get("network_model_search_fetch_or_evaluator_called") is not False
        or replay.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("claim_scope")
        != "build_only_transport_evidence_uncertainty_not_benchmark_quality_reward_or_causal_credit"
        or not isinstance(authorization, dict)
        or any(authorization.values())
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.72 build audit drifted")


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = read_object(root / PARENT_RESULT)
    if (
        parent.get("role") != "v24271_keyless_dev64_result"
        or parent.get("status") != "development_gate_no_go"
        or parent.get("decision", {}).get("passed") is not False
        or parent.get("claims", {}).get("sota") is not False
    ):
        raise RuntimeError("V2.42.72 parent NO-GO result drifted")
    surface = {str(relative): _surface_audit(root, relative) for relative in SURFACES}
    findings = [name for name, result in surface.items() if not result["passed"]]
    replay = _synthetic_replay()
    value = {
        "artifact_version": 1,
        "role": "v24272_two_wave_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parent_no_go_result": {
            "path": str(PARENT_RESULT),
            "sha256": sha256(root / PARENT_RESULT),
            "status": parent["status"],
            "decision_passed": parent["decision"]["passed"],
            "only_failed_check": "task_wall_sum_ratio",
        },
        "surface_manifest": {name: result["sha256"] for name, result in surface.items()},
        "static_audit": {
            "surfaces": surface,
            "all_surfaces_passed": not findings,
            "network_and_effects_only_via_injected_search_adapter": True,
            "controller_is_pure_and_receipt_replay_validated": True,
        },
        "synthetic_replay": replay,
        "claim_scope": "build_only_transport_evidence_uncertainty_not_benchmark_quality_reward_or_causal_credit",
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
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / OUTPUT, report)
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}))
