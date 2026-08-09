#!/usr/bin/env python3
"""Build-only audit for V2.49.59 registrable-source-fair discovery."""

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

from deepwide_agent.v24959_source_fair_discovery import (  # noqa: E402
    compare_prefixes,
    order_source_fair_leads,
)


DATE = "20260809"
OUTPUT = Path(f"results/v24959_source_fair_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24959_source_fair_discovery.py"),
    Path("tests/test_v24959_source_fair_discovery.py"),
    Path("scripts/audit_v24959_source_fair_build.py"),
    Path("src/deepwide_agent/v24957_action_fair_discovery.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
)
TEST_MODULES = (
    "tests.test_v24358_two_batch_discovery",
    "tests.test_v24770_visible_entity_fair_semantic_runtime",
    "tests.test_v24957_action_fair_discovery",
    "tests.test_v24958_action_fair_live_gate",
    "tests.test_v24959_source_fair_discovery",
)
EXPECTED_TESTS = 36
PRIVILEGED = frozenset(
    {
        "answer_key", "benchmark_question_type", "category", "gold",
        "ground_truth", "mapping", "question_type", "reward", "score",
        "split", "task_category",
    }
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
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


def _manifest(*, tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = ROOT / relative
        tracked_ok = not tracked or subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode == 0
        if (
            relative.is_absolute() or ".." in relative.parts or path.is_symlink()
            or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
            or not tracked_ok
        ):
            raise RuntimeError(f"V2.49.59 source identity drifted: {relative}")
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.49.59 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _ast_audit() -> dict[str, list[str]]:
    relative = SOURCES[0]
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    privileged: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            key = node.slice.value.casefold() if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str) else None
            if key in PRIVILEGED:
                privileged.append(f"{relative}:{node.lineno}:{key}")
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        else:
            names = []
        for name in names:
            if any(marker in name.casefold() for marker in ("evaluator", "official_eval", "finalize")):
                imports.append(f"{relative}:{node.lineno}:{name}")
    return {"privileged_subscripts": sorted(privileged), "evaluator_imports": sorted(imports)}


def _source(host: str, suffix: str) -> dict[str, str]:
    return {
        "type": "url", "title": "",
        "url": f"https://{host}/{suffix}",
        "fetch_url": f"https://{host}/{suffix}",
    }


def _synthetic() -> dict[str, Any]:
    raw = [{
        "query": "discarded", "answer": "discarded",
        "results": [_source("news.alpha.example", "local")], "error": None,
        "hosted_search_trace": {"actions": [
            {"sources": [_source("docs.alpha.example", f"a{i}") for i in range(1, 7)]},
            {"sources": [_source("beta.example", "b1")]},
            {"sources": [_source("gamma.example", "c1")]},
            {"sources": [_source("delta.example", "d1")]},
        ]},
    }]
    ordered, observation, private = order_source_fair_leads(raw)
    stable = list(observation["stable_urls"])
    candidate = [item["url"] for item in ordered]
    source_by_url = private["source_by_url"]
    prefix_checks: list[bool] = []
    gains: list[int] = []
    for cap in range(1, len(stable) + 1):
        stable_sources = {source_by_url[url] for url in stable[:cap] if source_by_url[url]}
        candidate_sources = {source_by_url[url] for url in candidate[:cap] if source_by_url[url]}
        prefix_checks.append(len(candidate_sources) >= len(stable_sources))
        gains.append(len(candidate_sources) - len(stable_sources))
    prefix = compare_prefixes(raw, cap=6)["receipt"]
    return {
        "source_set_equal": set(stable) == set(candidate),
        "all_prefix_source_coverage_non_decreasing": all(prefix_checks),
        "maximum_prefix_source_coverage_gain": max(gains, default=0),
        "cap6_stable_sources": prefix["stable_prefix_registrable_source_count"],
        "cap6_candidate_sources": prefix["candidate_prefix_registrable_source_count"],
        "cap6_matched_cost": prefix["matched_prefix_cost"],
        "content_values_persisted": False,
    }


def _tests() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", *TEST_MODULES, "-v"],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=180, check=False,
    )
    observed = sum(line.rstrip().endswith(" ... ok") for line in completed.stdout.splitlines())
    return {
        "modules": list(TEST_MODULES), "expected": EXPECTED_TESTS,
        "observed_passes": observed, "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == EXPECTED_TESTS,
    }


def build(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.59 audit requires clean pushed HEAD")
    if require_clean and ((ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink()):
        raise RuntimeError("V2.49.59 audit surface is not pristine")
    manifest = _manifest(tracked=require_clean)
    ast_audit = _ast_audit()
    synthetic = _synthetic()
    tests = _tests()
    checks = {
        "tests_exactly_36_of_36": tests["passed"],
        "runtime_privileged_subscripts_absent": not ast_audit["privileged_subscripts"],
        "runtime_evaluator_imports_absent": not ast_audit["evaluator_imports"],
        "source_set_conserved": synthetic["source_set_equal"],
        "every_prefix_source_coverage_non_decreasing": synthetic[
            "all_prefix_source_coverage_non_decreasing"
        ],
        "synthetic_prefix_gain_is_strict": synthetic[
            "maximum_prefix_source_coverage_gain"
        ] > 0,
        "matched_prefix_cost": synthetic["cap6_matched_cost"],
        "persistent_surface_content_free": not synthetic["content_values_persisted"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24959_source_fair_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "tests": tests, "ast_audit": ast_audit, "synthetic": synthetic,
        "checks": checks, "findings": findings, "audit_valid": not findings,
        "source_policy": {
            "synthetic_data_only": True,
            "benchmark_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_value_read_hashed_persisted_or_emitted": False,
            "network_model_fetch_evaluator_or_benchmark_effect": False,
        },
        "authorization": {
            "neutral_source_fair_live_gate_design": not findings,
            "neutral_source_fair_live_gate_launch": False,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False, "leaderboard_or_sota": False,
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
    parser.parse_args()
    value = build()
    publish(value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"]}, sort_keys=True))


if __name__ == "__main__":
    main()
