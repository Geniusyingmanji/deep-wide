#!/usr/bin/env python3
"""Create the build-only audit for V2.49.57 action-fair discovery."""

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
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24957_action_fair_discovery import (  # noqa: E402
    ActionFairBudgetEquivalentTaskUnionSearchClient,
    order_action_fair_leads,
)


DATE = "20260809"
ROLE = "v24957_action_fair_discovery_build_audit"
OUTPUT = Path(f"results/v24957_action_fair_discovery_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24957_action_fair_discovery.py"),
    Path("tests/test_v24957_action_fair_discovery.py"),
    Path("scripts/audit_v24957_action_fair_discovery_build.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24270_budget_equivalent_union.py"),
)
TEST_MODULES = (
    "tests.test_v24269_task_union_discovery",
    "tests.test_v24270_budget_equivalent_union",
    "tests.test_v24272_two_wave_retrieval",
    "tests.test_v24273_two_wave_task_runtime",
    "tests.test_v24280_task_union_single_shot",
    "tests.test_v24630_thin_backfill_search",
    "tests.test_v24957_action_fair_discovery",
)
EXPECTED_TESTS = 35
PRIVILEGED_KEYS = frozenset(
    {
        "answer_key",
        "benchmark_question_type",
        "category",
        "gold",
        "ground_truth",
        "mapping",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
EVALUATOR_MARKERS = ("evaluator", "official_eval", "finalize")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _ordinary(relative: Path, *, tracked: bool) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or tracked
        and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0
    ):
        raise RuntimeError(f"V2.49.57 expected ordinary tracked source: {relative}")
    return path


def _manifest(*, tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = _ordinary(relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.49.57 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _ast_audit() -> dict[str, list[str]]:
    relative = SOURCES[0]
    source = (ROOT / relative).read_text(encoding="utf-8")
    tree = ast.parse(source)
    privileged: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            key = None
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                key = node.slice.value.casefold()
            if key in PRIVILEGED_KEYS:
                privileged.append(f"{relative}:{node.lineno}:{key}")
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        else:
            names = []
        for name in names:
            if any(marker in name.casefold() for marker in EVALUATOR_MARKERS):
                imports.append(f"{relative}:{node.lineno}:{name}")
    return {"privileged_subscripts": sorted(privileged), "evaluator_imports": sorted(imports)}


def _source(label: str) -> dict[str, str]:
    return {
        "type": "url",
        "title": "",
        "url": f"https://{label}.example/record",
        "fetch_url": f"https://{label}.example/record",
    }


def _synthetic() -> dict[str, Any]:
    raw = [
        {
            "query": "discarded",
            "answer": "discarded",
            "results": [_source("local")],
            "error": None,
            "hosted_search_trace": {
                "actions": [
                    {"sources": [_source(f"a{index}") for index in range(1, 7)]},
                    {"sources": [_source("b1"), _source("b2")]},
                    {"sources": [_source("c1")]},
                    {"sources": [_source("d1")]},
                ]
            },
        }
    ]
    fair, observation, memberships = order_action_fair_leads(raw)
    stable = list(observation["stable_urls"])
    ordered = [str(item["url"]) for item in fair]
    prefix = 6
    stable_groups = {
        group for url in stable[:prefix] for group in memberships.get(url, frozenset())
    }
    fair_groups = {
        group for url in ordered[:prefix] for group in memberships.get(url, frozenset())
    }
    return {
        "source_set_equal": set(stable) == set(ordered),
        "source_count": len(ordered),
        "prefix_size": prefix,
        "stable_prefix_action_group_count": len(stable_groups),
        "fair_prefix_action_group_count": len(fair_groups),
        "action_group_coverage_gain": len(fair_groups) - len(stable_groups),
        "query_local_prefix_preserved": ordered[0] == "https://local.example/record",
        "raw_action_group_count": int(observation["raw_action_group_count"]),
        "raw_action_source_count": int(observation["raw_action_source_count"]),
        "content_values_persisted": False,
    }


def _tests() -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", *TEST_MODULES, "-v"]
    completed = subprocess.run(
        command, cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=180, check=False,
    )
    count = sum(line.rstrip().endswith(" ... ok") for line in completed.stdout.splitlines())
    return {
        "modules": list(TEST_MODULES),
        "expected": EXPECTED_TESTS,
        "observed_passes": count,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and count == EXPECTED_TESTS,
    }


def build(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.57 audit requires clean pushed HEAD")
    if require_clean and ((ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink()):
        raise RuntimeError("V2.49.57 audit surface is not pristine")
    manifest = _manifest(tracked=require_clean)
    ast_audit = _ast_audit()
    synthetic = _synthetic()
    tests = _tests()
    checks = {
        "tests_exactly_35_of_35": tests["passed"],
        "runtime_privileged_subscripts_absent": not ast_audit["privileged_subscripts"],
        "runtime_evaluator_imports_absent": not ast_audit["evaluator_imports"],
        "source_set_conserved": synthetic["source_set_equal"],
        "query_local_prefix_preserved": synthetic["query_local_prefix_preserved"],
        "action_group_prefix_coverage_strictly_improves": synthetic[
            "action_group_coverage_gain"
        ] > 0,
        "synthetic_persistent_surface_content_free": not synthetic[
            "content_values_persisted"
        ],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "tests": tests,
        "ast_audit": ast_audit,
        "synthetic": synthetic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": {
            "synthetic_data_only": True,
            "benchmark_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_value_read_hashed_persisted_or_emitted": False,
            "network_model_fetch_evaluator_or_benchmark_effect": False,
        },
        "authorization": {
            "neutral_live_transport_gate_design": not findings,
            "neutral_live_transport_gate_launch": False,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit",))
    args = parser.parse_args()
    del args
    value = build()
    publish(value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"]}, sort_keys=True))


if __name__ == "__main__":
    main()
