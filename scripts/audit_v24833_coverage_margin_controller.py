#!/usr/bin/env python3
"""Build audit for the pure V2.48.33 coverage-margin controller."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24272_two_wave_entropy_voc import FirstWaveObservation  # noqa: E402
from deepwide_agent.v24833_coverage_margin_controller import (  # noqa: E402
    POLICY_VALUES,
    build_synthetic_gate,
    decide_coverage_margin,
    payload_sha256,
    validate_synthetic_gate,
)


OUTPUT = Path(
    "results/v24833_coverage_margin_controller_build_audit_v1_20260807.json"
)
SOURCE = Path("src/deepwide_agent/v24833_coverage_margin_controller.py")
TEST = Path("tests/test_v24833_coverage_margin_controller.py")
SCRIPT = Path("scripts/audit_v24833_coverage_margin_controller.py")
DIAGNOSIS = Path(
    "results/v24832_v24800_v24831_stop_gate_diagnosis_v1_20260807.json"
)
PARENT_AUDIT = Path(
    "results/v24831_keyless_exact220_postresult_audit_v1_20260807.json"
)
FROZEN_TASK_ROOT = Path("outputs/v24831_keyless_exact220_v1_20260807/tasks")
SOURCES = (
    SOURCE,
    TEST,
    SCRIPT,
    Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
    Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
    Path("tests/test_v24272_two_wave_entropy_voc.py"),
    Path("tests/test_v24272_two_wave_retrieval.py"),
    Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
    Path("tests/test_v24799_fixed_full_budget_control.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24833_coverage_margin_controller.py"), 7),
    (Path("tests/test_v24272_two_wave_entropy_voc.py"), 7),
    (Path("tests/test_v24272_two_wave_retrieval.py"), 6),
    (Path("tests/test_v24799_fixed_full_budget_control.py"), 5),
)
EXPECTED_TESTS = 25
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
FORBIDDEN_RUNTIME_FIELDS = {
    "category",
    "question_type",
    "task_category",
    "ground_truth",
    "answer_key",
    "gold",
    "score",
    "reward",
    "split",
}


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.33 build audit requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.48.33 audit expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.33 audit expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _ast_findings() -> tuple[list[str], list[str], list[str]]:
    source = (ROOT / SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    dangerous_imports = sorted(
        imports & {"os", "pathlib", "subprocess", "requests", "socket", "urllib"}
    )
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    dangerous_calls = sorted(
        calls & {"open", "eval", "exec", "compile", "__import__"}
    )
    field_hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in FORBIDDEN_RUNTIME_FIELDS:
                field_hits.add(node.value)
    return dangerous_imports, dangerous_calls, sorted(field_hits)


def _run_tests() -> tuple[int, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TEST_SUITES:
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
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=360,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": payload_sha256(completed.stdout),
            }
        )
    return sum(row["observed"] for row in rows), rows


def _replay_frozen_content_free_receipts() -> dict[str, Any]:
    decisions: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    margins: Counter[str] = Counter()
    for position in range(1, 221):
        path = ROOT / FROZEN_TASK_ROOT / f"task_{position:04d}" / "result.json"
        envelope = _read(path)
        result = envelope.get("result") or {}
        receipt = (result.get("two_wave_retrieval") or {}).get("receipt") or {}
        first = receipt.get("wave1") or {}
        if (
            result.get("mapping_gold_evaluator_or_score_read") is not False
            or not isinstance(first, Mapping)
        ):
            raise RuntimeError("V2.48.33 frozen content-free receipt drifted")
        observation = FirstWaveObservation(
            queries_executed=int(first["queries_executed"]),
            sources_discovered=int(first["sources_discovered"]),
            fetches_attempted=int(first["fetches_attempted"]),
            usable_pages=int(first["usable_pages"]),
            novel_pages=int(first["novel_pages"]),
            unique_hosts=int(first["new_unique_hosts"]),
            content_chars=int(first["content_chars"]),
            required_column_count=int(receipt["required_column_count"]),
            explicit_row_target=int(receipt["explicit_row_target"]),
            search_seconds=float(first["search_seconds"]),
            fetch_seconds=float(first["fetch_seconds"]),
            unrecoverable_search_failures=int(
                first["unrecoverable_search_failures"]
            ),
        )
        decision = decide_coverage_margin(observation)
        decisions[str(decision["decision"])] += 1
        reasons[str(decision["reason"])] += 1
        for name, value in decision["coverage_margin"].items():
            margins[f"{name}_{str(value).lower()}"] += 1
    if sum(decisions.values()) != 220:
        raise RuntimeError("V2.48.33 frozen replay denominator drifted")
    return {
        "selected": 220,
        "decision_counts": dict(sorted(decisions.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "margin_counts": dict(sorted(margins.items())),
        "prediction_mapping_gold_evaluator_metric_or_score_opened": False,
        "task_identifier_question_query_url_page_or_prediction_emitted": False,
        "replay_used_only_content_free_first_wave_receipts": True,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    diagnosis = _read(ROOT / DIAGNOSIS)
    parent = _read(ROOT / PARENT_AUDIT)
    if (
        diagnosis.get("diagnosis_valid") is not True
        or diagnosis.get("findings") != []
        or not _sealed(diagnosis, "diagnosis_payload_sha256")
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or not _sealed(parent, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.33 parent evidence drifted")
    observed, suites = _run_tests()
    synthetic = validate_synthetic_gate(build_synthetic_gate())
    replay = _replay_frozen_content_free_receipts()
    imports, calls, fields = _ast_findings()
    secrets = [
        str(path)
        for path in SOURCES
        if SECRET.search((ROOT / path).read_text(encoding="utf-8"))
    ]
    source_manifest = {str(path): sha256(ROOT / path) for path in SOURCES}
    checks = {
        "focused_tests_exact25": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "synthetic_grid_nonempty": synthetic["counts"]["observations"] > 1_000,
        "synthetic_unsafe_early_stop_zero": synthetic["counts"][
            "unsafe_early_stops"
        ]
        == 0,
        "synthetic_in_budget_incomplete_stop_zero": synthetic["counts"][
            "in_budget_incomplete_stops"
        ]
        == 0,
        "synthetic_entropy_nonzero_zero": synthetic["counts"]["entropy_nonzero"]
        == 0,
        "frozen_replay_exact220": replay["selected"] == 220,
        "frozen_replay_early_stop_reachable": replay["reason_counts"].get(
            "first_wave_sufficient", 0
        )
        > 0,
        "frozen_replay_expand_reachable": replay["decision_counts"].get(
            "expand", 0
        )
        > 0,
        "frozen_replay_not_full_budget": replay["decision_counts"].get("stop", 0)
        > 0,
        "runtime_ast_no_io_or_dynamic_execution": imports == [] and calls == [],
        "runtime_ast_no_privileged_field_access": fields == [],
        "source_secret_literal_zero": secrets == [],
        "policy_entropy_weight_zero": POLICY_VALUES["information_gain_weight"]
        == 0.0,
    }
    value = {
        "artifact_version": 1,
        "role": "v24833_coverage_margin_controller_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "target_main": _git("rev-parse", "target/main"),
            "head_equals_target_main": True,
            "worktree_clean": True,
        },
        "parents": {
            "v24832_diagnosis_sha256": sha256(ROOT / DIAGNOSIS),
            "v24831_postresult_audit_sha256": sha256(ROOT / PARENT_AUDIT),
        },
        "policy": dict(POLICY_VALUES),
        "source_manifest": source_manifest,
        "source_manifest_sha256": payload_sha256(source_manifest),
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "suites": suites,
        },
        "synthetic_gate": synthetic,
        "frozen_content_free_replay": replay,
        "ast_audit": {
            "dangerous_imports": imports,
            "dangerous_calls": calls,
            "privileged_runtime_field_accesses": fields,
            "credential_literal_hits": secrets,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "source_policy": {
            "historical_benchmark_prediction_mapping_gold_evaluator_metric_or_score_opened_by_replay": False,
            "historical_benchmark_metric_or_stratum_is_runtime_input": False,
            "future_runtime_uses_only_same_pass_content_free_observation": True,
            "entropy_or_information_gain_assigns_credit": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "authorization": {
            "fresh_benchmark_external_gate_design": all(checks.values()),
            "external_forward": False,
            "public_dev64": False,
            "public_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = payload_sha256(value)
    if value["findings"]:
        raise RuntimeError(f"V2.48.33 build audit failed: {value['findings']}")
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": artifact["audit_valid"],
                "tests": artifact["tests"]["observed"],
                "replay": artifact["frozen_content_free_replay"][
                    "decision_counts"
                ],
                "authorization": artifact["authorization"],
            },
            sort_keys=True,
        )
    )
