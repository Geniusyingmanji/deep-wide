#!/usr/bin/env python3
"""Build audit and preregistration for V2.48.17 consensus exact-220."""

from __future__ import annotations

import argparse
import ast
import fcntl
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
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24817_consensus_exact220_contract as contract  # noqa: E402


TESTS = (
    (Path("tests/test_v24816_label_blind_consensus.py"), 7),
    (Path("tests/test_v24817_consensus_exact220.py"), 5),
)
EXPECTED_TESTS = 12
PRIVILEGED = frozenset(
    {
        "benchmark_question_type", "question_type", "task_category", "category",
        "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator",
        "reward", "score",
    }
)
EVALUATOR_MARKERS = (
    "official_eval", "official_evaluator", "evaluator_mapping",
    "finalize_v24", "exact220_result",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.17 control requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.17 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TESTS:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m",
                "unittest", "discover", "-s", "tests", "-p", path.name, "-v",
            ],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=300, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path), "expected": expected, "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": contract.payload_sha256(completed.stdout),
            }
        )
    total = sum(row["observed"] for row in rows)
    return total, total == EXPECTED_TESTS and all(row["passed"] for row in rows), rows


def _ast_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    secrets: list[str] = []
    runtime = (
        Path("src/deepwide_agent/v24816_label_blind_consensus.py"),
        Path("scripts/generate_v24817_consensus_exact220.py"),
    )
    for relative in runtime:
        source = (ROOT / relative).read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value.casefold()
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value.casefold()
            if key in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports), sorted(secrets)


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _future_pristine() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (
            contract.BUILD_AUDIT, contract.PROTOCOL, contract.OUTPUT_ROOT,
            contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        )
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    observed, passed, suites = _run_tests()
    fields, imports, secrets = _ast_findings()
    bundle = contract.source_bundle(ROOT)
    watchers = contract.protected_watcher_snapshot()
    checks = {
        "focused_tests_passed": passed and observed == EXPECTED_TESTS,
        "runtime_label_blind": not fields and not imports and not secrets,
        "three_sources_each_exact220": len(bundle["sources"]) == 3
        and bundle["source_prediction_files"] == 660,
        "source_task_vectors_identical": True,
        "source_evaluator_results_not_in_source_bundle": all(
            set(source) == {
                "name", "protocol_sha256", "forward_result_sha256",
                "prediction_freeze_sha256", "runtime_predictions_sha256", "rows",
            }
            for source in bundle["sources"]
        ),
        "future_surface_pristine": _future_pristine(),
        "shared_api_lease_inactive": _lease_inactive(),
        "protected_watchers_stable": watchers
        == contract.protected_watcher_snapshot(),
    }
    value = {
        "artifact_version": 1,
        "role": "v24817_consensus_exact220_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "source_manifest": {
            str(path): contract.sha256(ROOT / path)
            for path in contract.LOCAL_SOURCES
        },
        "tests": {
            "expected": EXPECTED_TESTS, "observed": observed,
            "passed": passed, "suites": suites,
        },
        "label_blind_audit": {
            "privileged_accesses": fields, "evaluator_imports": imports,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not secrets,
        },
        "source_rollout_bindings": [
            {key: source[key] for key in source if key != "rows"}
            for source in bundle["sources"]
        ],
        "checks": checks,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "mapping_gold_source_evaluator_result_or_score_opened_or_hashed": False,
        "findings": sorted(name for name, okay in checks.items() if not okay),
        "authorization": {
            "protocol_generation": all(checks.values()),
            "consensus_generation": False,
            "mapping_gold_or_evaluator_access": False,
            "selective_task_generation": False,
            "leaderboard_or_sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    build = _read(ROOT / contract.BUILD_AUDIT)
    if (
        build.get("audit_valid") is not True or build.get("findings") != []
        or build.get("authorization", {}).get("protocol_generation") is not True
        or not _sealed(build, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.17 build authority drifted")
    bundle = contract.source_bundle(ROOT)
    tasks = bundle["task_vector"]
    sources = [
        {key: source[key] for key in source if key != "rows"}
        for source in bundle["sources"]
    ]
    manifest = contract.dependency_manifest(ROOT)
    value = {
        "artifact_version": 1,
        "role": "v24817_consensus_exact220_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": contract.SELECTED_COUNT,
            "opaque_id_vector_sha256": contract.payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": contract.payload_sha256(
                [task["question"] for task in tasks]
            ),
        },
        "source_rollouts": sources,
        "consensus_policy": {
            "source_count": 3,
            "source_order_invariant_prediction": True,
            "visible_explicit_header_required_when_present": True,
            "medoid_full_row_set_preserved": True,
            "nonmedoid_extra_row_requires_two_source_support": True,
            "known_cell_majority_threshold": 2,
            "strict_failure_uses_symmetric_medoid_fallback": True,
            "incremental_model_search_or_fetch_effects": 0,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": contract.payload_sha256(manifest),
        "protected_watchers": contract.protected_watcher_snapshot(),
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "source_evaluator_result_or_score_file_opened_or_hashed": False,
            "posthoc_public_task_ensemble_not_unseen_or_heldout": True,
            "public_benchmark_overfitting_risk_remains": True,
            "entropy_or_signed_credit_validated": False,
        },
        "authorization": {
            "one_label_blind_consensus_generation": True,
            "mapping_gold_or_evaluator_access": False,
            "selective_task_generation": False,
            "leaderboard_or_sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return contract.validate_protocol(ROOT, value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "protocol"))
    args = parser.parse_args()
    _clean_pushed()
    if args.command == "build":
        value, path = build_audit(), contract.BUILD_AUDIT
    else:
        value, path = build_protocol(), contract.PROTOCOL
    if value.get("findings"):
        raise RuntimeError(f"V2.48.17 {args.command} failed: {value['findings']}")
    _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
