#!/usr/bin/env python3
"""Offline label-blind build audit for V2.42.89/90 low-coverage rescue."""

from __future__ import annotations

import ast
import copy
import json
import os
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24290_low_coverage_task_runtime import (  # noqa: E402
    run_v24290_task,
    validate_v24290_result,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402


OUTPUT = Path("results/v24290_low_coverage_task_build_audit_v1_20260803.json")
DIAGNOSIS = Path("results/v24288_v24287_exact220_diagnosis_v1_20260803.json")
SOURCES = (
    "src/deepwide_agent/v24289_low_coverage_rescue.py",
    "src/deepwide_agent/v24290_low_coverage_task_runtime.py",
)
TESTS = (
    "tests/test_v24289_low_coverage_rescue.py",
    "tests/test_v24290_low_coverage_task_runtime.py",
)
FORBIDDEN_IMPORTS = frozenset(
    {"ctypes", "multiprocessing", "os", "pathlib", "requests", "socket", "subprocess"}
)
FORBIDDEN_KEYS = frozenset(
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
FORBIDDEN_PATH_MARKERS = (
    "evaluator_mapping",
    "official_eval_results",
    "conservative_summary",
    "runtime_manifest_v1_repro",
    "v24287_exact220_v1_20260803",
    "v24288_v24287_exact220_diagnosis",
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


class _Model:
    def __init__(self, values: list[str]) -> None:
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system: str, user: str, *, max_output_tokens: int, json_mode: bool = False) -> Any:
        del system, user, max_output_tokens, json_mode
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return SimpleNamespace(text=self.values.pop(0))


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if raw.is_absolute() or ".." in raw.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.90 expected ordinary file: {relative}")
    return path


def _imports(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            values.add((node.module or "").split(".")[0])
    return values


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
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value
        if key in FORBIDDEN_KEYS:
            values.append({"line": int(node.lineno), "key": key})
    return values


def _static_audit(root: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for relative in SOURCES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = sorted(_imports(tree).intersection(FORBIDDEN_IMPORTS))
        accesses = _literal_key_accesses(tree)
        markers = sorted(marker for marker in FORBIDDEN_PATH_MARKERS if marker in source)
        files[relative] = {
            "sha256": sha256(path),
            "forbidden_imports": imports,
            "privileged_exact_key_accesses": accesses,
            "benchmark_evaluator_or_diagnosis_path_literals": markers,
            "credential_literal_present": SECRET.search(source) is not None,
            "concrete_opaque_id_present": OPAQUE.search(source) is not None,
            "passed": not imports and not accesses and not markers and SECRET.search(source) is None and OPAQUE.search(source) is None,
        }
    runtime_source = (root / SOURCES[1]).read_text(encoding="utf-8")
    boundary_before_effect_adapter = runtime_source.find("validate_visible_task(task)") < runtime_source.find("LowCoverageCachingSearchClient(")
    return {
        "files": files,
        "runtime_visible_boundary_validation_precedes_effect_adapter": boundary_before_effect_adapter,
        "passed": all(value["passed"] for value in files.values()) and boundary_before_effect_adapter,
    }


def _limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


def _synthetic_replay() -> dict[str, Any]:
    task = {
        "opaque_id": "task_" + "a" * 24,
        "question": "Return one table. The column names are: Name, Version, and Date.",
    }
    plan = json.dumps(
        {
            "columns": ["wrong"],
            "queries": ["visible one", "visible two", "visible three", "visible four"],
        }
    )
    table = "| Name | Version | Date |\n| --- | --- | --- |\n| A | 1 | 2026 |"
    stop_search = TailSearch(sparse=False)
    stop = run_v24290_task(
        task,
        model=_Model([plan, table]),
        search=stop_search,
        limits=_limits(),
        monotonic=Clock(),
    )
    rescue_search = TailSearch(sparse=True, failed_fetches=3, empty_first=True)
    rescued = run_v24290_task(
        task,
        model=_Model([plan, table]),
        search=rescue_search,
        limits=_limits(),
        monotonic=Clock(),
    )
    validate_v24290_result(stop)
    validate_v24290_result(rescued)
    stop_receipt = stop["two_wave_retrieval"]["receipt"]
    rescue_receipt = rescued["two_wave_retrieval"]["receipt"]
    value = {
        "selected": 2,
        "terminal": 2,
        "stop": {
            "controller_decision": stop_receipt["controller"]["decision"],
            "rescue_triggered": stop_receipt["rescue"]["triggered"],
            "provider_search_calls_added_by_rescue": stop_receipt["hosted_search_requests_added_by_rescue"],
            "fetches_attempted": stop_receipt["total"]["fetches_attempted"],
        },
        "low_coverage": {
            "controller_decision": rescue_receipt["controller"]["decision"],
            "rescue_triggered": rescue_receipt["rescue"]["triggered"],
            "provider_search_calls_added_by_rescue": rescue_receipt["hosted_search_requests_added_by_rescue"],
            "usable_pages_before": rescue_receipt["total_before_rescue"]["usable_pages"],
            "usable_pages_after": rescue_receipt["total"]["usable_pages"],
            "rescue_fetches": rescue_receipt["rescue"]["fetches_attempted"],
            "total_fetches": rescue_receipt["total"]["fetches_attempted"],
        },
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_persisted": False,
        "network_model_search_fetch_or_evaluator_called": False,
    }
    encoded = json.dumps(value, sort_keys=True)
    if OPAQUE.search(encoded) or "visible one" in encoded or "| A |" in encoded:
        raise RuntimeError("V2.42.90 synthetic replay leaked content")
    return value


def validate_report(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    static = value.get("static_audit")
    replay = value.get("synthetic_replay")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24290_low_coverage_task_build_audit"
        or value.get("label_blind") is not True
        or not isinstance(static, Mapping)
        or static.get("passed") is not True
        or not isinstance(replay, Mapping)
        or replay.get("selected") != 2
        or replay.get("terminal") != 2
        or replay.get("stop", {}).get("controller_decision") != "stop"
        or replay.get("stop", {}).get("rescue_triggered") is not False
        or replay.get("low_coverage", {}).get("controller_decision") != "expand"
        or replay.get("low_coverage", {}).get("rescue_triggered") is not True
        or replay.get("low_coverage", {}).get("provider_search_calls_added_by_rescue") != 0
        or replay.get("low_coverage", {}).get("usable_pages_after", 0)
        <= replay.get("low_coverage", {}).get("usable_pages_before", 0)
        or replay.get("low_coverage", {}).get("total_fetches", 11) > 10
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.90 build audit drifted")


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    diagnosis_path = _ordinary(root, DIAGNOSIS)
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    if (
        diagnosis.get("role") != "v24288_v24287_exact220_postterminal_diagnosis"
        or diagnosis.get("mechanism_conclusions", {}).get("quality_regressed") is not True
        or diagnosis.get("mechanism_conclusions", {}).get("single_component_causal_attribution_supported") is not False
        or diagnosis.get("controller", {}).get("stop", {}).get("selected") != 175
        or diagnosis.get("controller", {}).get("expand_low_coverage", {}).get("selected") != 23
        or any(diagnosis.get("authorization", {}).values())
    ):
        raise RuntimeError("V2.42.90 diagnosis parent drifted")
    static = _static_audit(root)
    replay = _synthetic_replay()
    findings = [] if static["passed"] else ["static_active_surface_failed"]
    value = {
        "artifact_version": 1,
        "role": "v24290_low_coverage_task_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parent_diagnosis": {
            "path": str(DIAGNOSIS),
            "sha256": sha256(diagnosis_path),
            "stop_tasks": 175,
            "expand_tasks": 43,
            "expand_low_coverage_tasks": 23,
            "causal_claim_available": False,
        },
        "surface_manifest": {
            relative: sha256(_ordinary(root, relative))
            for relative in (*SOURCES, *TESTS)
        },
        "static_audit": static,
        "synthetic_replay": replay,
        "candidate_scope": {
            "same_response_deterministic_tail_only": True,
            "maximum_total_queries": 4,
            "maximum_total_fetch_attempts": 10,
            "maximum_rescue_fetch_attempts": 4,
            "maximum_pre_rescue_retrieval_seconds": 60,
            "normal_stop_path_has_zero_rescue_effects": True,
            "runtime_boundary": ["opaque_id", "question"],
            "benchmark_calibrated_or_quality_proven": False,
        },
        "authorization": {
            "one_neutral_public_documentation_probe": False,
            "dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_report(value)
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


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / OUTPUT, report)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": report["audit_valid"]}, sort_keys=True))
