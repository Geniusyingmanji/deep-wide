#!/usr/bin/env python3
"""Build audit for the append-only V2.47.14 opaque-ID join repair."""

from __future__ import annotations

import ast
import fcntl
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

from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402
from scripts import preregister_v24714_sparse_full220 as preregister  # noqa: E402


AUDIT = contract.PACKAGE_BUILD
PREDECESSOR_AUDIT = Path("results/v24712_sparse_full220_package_build_audit_v1_20260806.json")
RUNTIME_FILES = (
    Path("src/deepwide_agent/v24709_sparse_worldbank_adapter.py"),
    Path("src/deepwide_agent/v24711_sparse_full220_contract.py"),
    Path("src/deepwide_agent/v24714_sparse_full220_order_join.py"),
    Path("scripts/run_v24711_sparse_full220.py"),
    Path("scripts/run_v24714_sparse_full220.py"),
)
SOURCES = (
    *RUNTIME_FILES,
    Path("scripts/preregister_v24714_sparse_full220.py"),
    Path("scripts/control_v24714_sparse_full220.py"),
    Path("scripts/audit_v24714_sparse_full220_forward.py"),
    Path("tests/test_v24714_sparse_full220_order_join.py"),
    Path("scripts/audit_v24715_order_join_package_build.py"),
    Path("tests/test_audit_v24715_order_join_package_build.py"),
    contract.ORDER_FAILURE,
    PREDECESSOR_AUDIT,
)
TESTS = (
    ("test_v24709_sparse_worldbank_adapter.py", 11),
    ("test_v24711_sparse_full220_package.py", 8),
    ("test_v24714_sparse_full220_order_join.py", 7),
    ("test_audit_v24715_order_join_package_build.py", 5),
)
EXPECTED_TEST_COUNT = 31
PRIVILEGED = frozenset(
    {"answer", "answer_key", "category", "evaluation", "evaluator",
     "evaluator_mapping", "gold", "ground_truth", "instance_id",
     "question_type", "reward", "score", "split", "task_category", "topic"}
)
EVALUATOR_IMPORT_MARKERS = (
    "official_eval", "official_evaluator", "finalize_fullset", "evaluator_mapping",
)
FORBIDDEN_DEPENDENCY_MARKERS = (
    "data/deepwidesearch/overall_20250916.jsonl",
    "external/Marco-Search-Agent", "evaluator_mapping.jsonl",
    "overall_20250916_tables", "official_eval_results", "v24267_exact220_result",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.15 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def ast_findings() -> tuple[list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    for relative in RUNTIME_FILES:
        tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"} and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value
            if key is not None and key.casefold() in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports)


def _run_tests() -> tuple[int, bool]:
    total = 0
    passed = True
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
    }
    for pattern, expected in TESTS:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
             "discover", "-s", "tests", "-p", pattern],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=90, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        count = int(match.group(1)) if match else 0
        total += count
        passed = passed and completed.returncode == 0 and count == expected
    return total, passed and total == EXPECTED_TEST_COUNT


def _parents_valid() -> bool:
    failure = contract.read_object(ROOT / contract.ORDER_FAILURE)
    predecessor = contract.read_object(ROOT / PREDECESSOR_AUDIT)
    return bool(
        failure.get("role") == "v24713_v24711_protocol_order_failure"
        and failure.get("authorization", {}).get("append_only_order_join_repair_build") is True
        and failure.get("authorization", {}).get("activation_or_forward_launch") is False
        and failure.get("observed", {}).get("same_id_set") is True
        and failure.get("observed", {}).get("same_order") is False
        and predecessor.get("role") == "v24712_sparse_full220_package_build_audit"
        and predecessor.get("audit_valid") is True
        and predecessor.get("findings") == []
        and predecessor.get("authorization", {}).get("protocol_publication") is True
        and predecessor.get("authorization", {}).get("activation_or_forward_launch") is False
        and contract.sealed(predecessor, "audit_payload_sha256")
    )


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )


def _join_evidence() -> dict[str, Any]:
    visible = contract.validate_visible_rows(ROOT)
    control = contract.validate_control_rows(ROOT)
    visible_ids = [row["opaque_id"] for row in visible]
    control_ids = [row["opaque_id"] for row in control]
    ordered = contract.ordered_visible_rows(ROOT)
    ordered_ids = [row["opaque_id"] for row in ordered]
    return {
        "visible_count": len(visible_ids),
        "control_count": len(control_ids),
        "visible_unique_count": len(set(visible_ids)),
        "control_unique_count": len(set(control_ids)),
        "same_id_set": set(visible_ids) == set(control_ids),
        "raw_file_order_equal": visible_ids == control_ids,
        "same_position_count": sum(
            visible_id == control_id
            for visible_id, control_id in zip(visible_ids, control_ids, strict=True)
        ),
        "ordered_join_matches_control_order": ordered_ids == control_ids,
    }
    return any(
        contract.RUNNER_MARKER in line for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "audit_v24715_order_join_package_build.py" not in line
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    fields, imports = ast_findings()
    secrets = [str(path) for path in SOURCES if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))]
    dependency_hits = [d for d in preregister.DEPENDENCIES if any(m in d for m in FORBIDDEN_DEPENDENCY_MARKERS)]
    test_count, tests_passed = _run_tests()
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    parents = _parents_valid()
    watchers = contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    active = _active()
    join = _join_evidence()
    findings: list[str] = []
    if head != remote:
        findings.append("source_commit_not_pushed")
    if not clean:
        findings.append("source_worktree_not_clean")
    if not tracked:
        findings.append("source_not_tracked")
    if not parents:
        findings.append("v24712_or_v24713_parent_drifted")
    if not tests_passed or test_count != EXPECTED_TEST_COUNT:
        findings.append("order_join_regression_failed")
    if fields:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if secrets:
        findings.append("credential_literal_in_package")
    if dependency_hits:
        findings.append("evaluator_score_or_raw_benchmark_dependency_present")
    if not lease:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("forward_runner_active")
    if join != {
        "visible_count": 220,
        "control_count": 220,
        "visible_unique_count": 220,
        "control_unique_count": 220,
        "same_id_set": True,
        "raw_file_order_equal": False,
        "same_position_count": 3,
        "ordered_join_matches_control_order": True,
    }:
        findings.append("actual_opaque_id_join_evidence_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24715_order_join_package_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "order_failure_path": str(contract.ORDER_FAILURE),
            "order_failure_sha256": contract.sha256(ROOT / contract.ORDER_FAILURE),
            "predecessor_package_audit_path": str(PREDECESSOR_AUDIT),
            "predecessor_package_audit_sha256": contract.sha256(ROOT / PREDECESSOR_AUDIT),
            "valid": parents,
        },
        "repair": {
            "only_semantic_change": "unique opaque-ID join and control-order reindexing",
            "predecessor_source_files_immutable": True,
            "actual_join_evidence": join,
            "actual_visible_and_control_id_sets_equal": join["same_id_set"],
            "actual_raw_file_orders_different": not join["raw_file_order_equal"],
            "ordered_join_matches_control_order": join[
                "ordered_join_matches_control_order"
            ],
        },
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "git": {"head": head, "target_main": remote, "head_equals_target_main": head == remote,
                "worktree_clean": clean, "all_sources_tracked": tracked},
        "tests": {"expected": EXPECTED_TEST_COUNT, "observed": test_count,
                  "passed": tests_passed, "synthetic_or_contract_only": True},
        "label_blind_audit": {
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_runtime_field_accesses": fields,
            "evaluator_imports": imports,
            "credential_literal_hits": secrets,
            "forbidden_dependency_hits": dependency_hits,
            "passed": not fields and not imports and not secrets and not dependency_hits,
        },
        "runtime_state": {"protected_watchers": watchers,
                          "shared_api_lease_inactive": lease,
                          "forward_runner_active": active},
        "source_policy": {
            "visible_manifest_and_control_prediction_rows_opened_for_id_order_validation": True,
            "question_and_prediction_bytes_validated_but_not_used_for_routing_or_persisted_by_audit": True,
            "actual_candidate_prediction_generated_by_audit": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_forward_or_evaluator_called": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {"protocol_publication": not findings,
                          "activation_or_forward_launch": False,
                          "evaluator": False, "leaderboard_or_sota": False},
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != "v24715_order_join_package_build_audit"
        or value.get("audit_valid") is not True or value.get("findings") != []
        or value.get("parents", {}).get("valid") is not True
        or value.get("repair", {}).get("ordered_join_matches_control_order") is not True
        or value.get("tests", {}).get("passed") is not True
        or value.get("tests", {}).get("observed") != EXPECTED_TEST_COUNT
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or value.get("runtime_state", {}).get("forward_runner_active") is not False
        or value.get("authorization") != {
            "protocol_publication": True, "activation_or_forward_launch": False,
            "evaluator": False, "leaderboard_or_sota": False,
        }
        or not contract.sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.15 build audit drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    validate_audit(value)
    publish(ROOT / AUDIT, value)
    print(json.dumps({"path": str(AUDIT), "audit_valid": value["audit_valid"],
                      "findings": value["findings"], "test_count": value["tests"]["observed"]}, sort_keys=True))
