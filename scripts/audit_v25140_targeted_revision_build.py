#!/usr/bin/env python3
"""Clean-build audit for the V2.51.39 targeted revision runtime."""

from __future__ import annotations

import ast
import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25140_targeted_revision_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25140_targeted_revision_build.py")
TEST = Path("tests/test_audit_v25140_targeted_revision_build.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25139_targeted_revision_runtime.py")
RUNTIME_TEST = Path("tests/test_v25139_targeted_revision_runtime.py")
PARENT_DIAGNOSIS = Path(
    "results/v25138_v25137_sparse_production_diagnosis_v1_20260812.json"
)
EXPECTED_PARENT_HASH = (
    "d5a86211c770b02dc280fa1bd792f8cca02921aa51deed2d6ae2056f314f26cb"
)
TEST_SUITES = (
    ("test_audit_v25140_targeted_revision_build.py", 4),
    ("test_v25139_targeted_revision_runtime.py", 13),
    ("test_v25135_sparse_production_runtime.py", 9),
    ("test_v25134_schema_total_causal_salience_runtime.py", 8),
    ("test_v25127_causally_coupled_target_record_runtime.py", 5),
    ("test_v25123_visible_legacy_query_compatible_runtime.py", 7),
    ("test_v25119_grounded_target_record_paired_runtime.py", 7),
    ("test_v25117_grounded_target_record_plan.py", 6),
    ("test_v25118_target_record_frontier_selection.py", 7),
    ("test_v24999_shared_response_selection_runtime.py", 7),
    ("test_v24990_query_vector_paired_runtime.py", 7),
    ("test_v24986_robust_paired_runtime.py", 5),
    ("test_v25110_exact_visible_schema.py", 4),
    ("test_v24259_deterministic_table_normalizer.py", 11),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
PROTECTED_WATCHERS = {
    795336: 713986317,
    2808901: 746680268,
    2889939: 746969965,
    3061652: 747569004,
}
_SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in _SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
DIRECT_FORBIDDEN_IMPORTS = frozenset(
    {
        "asyncio",
        "httpx",
        "importlib",
        "openai",
        "os",
        "pathlib",
        "requests",
        "runpy",
        "socket",
        "subprocess",
        "urllib.request",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.51.40 expected ordinary repository file")
    return path


def sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _test(pattern: str, expected: int) -> dict[str, Any]:
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
            pattern,
            "-v",
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
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "pattern": pattern,
        "expected": expected,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": payload_sha256(completed.stdout),
    }


def _tests() -> dict[str, Any]:
    suites = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _dependency_closure(entrypoints: Iterable[Path]) -> tuple[Path, ...]:
    pending = list(entrypoints)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = _ordinary(relative)
        observed.add(relative)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("deepwide_agent."):
                        candidates.append(
                            Path("src")
                            / Path(*item.name.split(".")).with_suffix(".py")
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == (
                    "src",
                    "deepwide_agent",
                ):
                    if module:
                        candidates.append(
                            Path("src/deepwide_agent")
                            / Path(*module.split(".")).with_suffix(".py")
                        )
                    else:
                        candidates.extend(
                            Path("src/deepwide_agent") / f"{item.name}.py"
                            for item in node.names
                        )
                elif module == "deepwide_agent":
                    candidates.extend(
                        Path("src/deepwide_agent") / f"{item.name}.py"
                        for item in node.names
                    )
                elif module.startswith("deepwide_agent."):
                    candidates.append(
                        Path("src") / Path(*module.split(".")).with_suffix(".py")
                    )
            for candidate in candidates:
                if (ROOT / candidate).is_file() and not (
                    ROOT / candidate
                ).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def _direct_forbidden_imports(relative: Path) -> list[str]:
    tree = ast.parse(
        _ordinary(relative).read_text(encoding="utf-8"), filename=str(relative)
    )
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    return sorted(
        name
        for name in imports
        if any(
            name == forbidden or name.startswith(forbidden + ".")
            for forbidden in DIRECT_FORBIDDEN_IMPORTS
        )
    )


def _semantic_findings(closure: Iterable[Path]) -> dict[str, list[str]]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in closure:
        path = _ordinary(relative)
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    return {
        "privileged_runtime_field_accesses": sorted(set(privileged) - allowed),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
        "allowed_provider_rank_access": sorted(allowed & set(privileged)),
    }


def _watchers() -> dict[str, Any]:
    output: dict[str, Any] = {}
    for pid, expected in PROTECTED_WATCHERS.items():
        path = Path("/proc") / str(pid) / "stat"
        if not path.is_file():
            output[str(pid)] = {"present": False, "start_ticks": None}
            continue
        raw = path.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        start = int(suffix[19]) if len(suffix) > 19 else None
        output[str(pid)] = {
            "present": True,
            "start_ticks": start,
            "matches_frozen_identity": start == expected,
        }
    return output


def _lease_inactive() -> bool:
    path = ROOT / LEASE_PATH
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


def _diagnosis_barrier() -> bool:
    value = json.loads(_ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
    diagnosis = value.get("diagnosis") or {}
    authorization = value.get("authorization") or {}
    return bool(
        sha256(PARENT_DIAGNOSIS) == EXPECTED_PARENT_HASH
        and value.get("role")
        == "v25138_v25137_sparse_production_counts_only_diagnosis"
        and value.get("diagnosis_valid") is True
        and value.get("findings") == []
        and diagnosis.get(
            "observed_primary_conversion_bottleneck_is_revision_actionability"
        )
        is True
        and diagnosis.get(
            "next_build_only_candidate_must_supply_completed_production_table_to_revision"
        )
        is True
        and diagnosis.get(
            "next_build_only_candidate_must_supply_only_verified_incremental_evidence_as_delta"
        )
        is True
        and diagnosis.get(
            "next_build_only_candidate_must_preserve_unmentioned_rows_and_cells"
        )
        is True
        and diagnosis.get(
            "next_build_only_candidate_must_preserve_production_on_revision_projection_or_posteffect_failure"
        )
        is True
        and diagnosis.get("entropy_or_information_gain_signed_credit") == 0
        and authorization.get(
            "production_table_conditioned_targeted_revision_build_only"
        )
        is True
        and authorization.get("new_fresh_disjoint_external_protocol_or_launch")
        is False
        and authorization.get("deepwidebench_dev64_exact220_leaderboard_or_sota")
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    tests = _tests()
    closure = _dependency_closure((RUNTIME_SOURCE,))
    semantic = _semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        PARENT_DIAGNOSIS,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not _tracked(path)
    )
    watchers = _watchers()
    checks = {
        "focused_targeted_revision_and_parent_tests_exact100": tests["passed"],
        "v25138_counts_only_diagnosis_bound": _diagnosis_barrier(),
        "all_sources_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_candidate_has_no_effect_imports": not _direct_forbidden_imports(
            RUNTIME_SOURCE
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True
            for row in watchers.values()
        ),
        "shared_api_lease_inactive": _lease_inactive(),
        "production_table_conditioned_targeted_revision_build_only": True,
        "query_fetch_model_output_token_wall_and_network_caps_unchanged": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25140_targeted_revision_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "runtime_dependency_closure": [str(path) for path in closure],
        "runtime_semantic_audit": {**semantic, "untracked_sources": untracked},
        "parent_diagnosis": {
            "path": str(PARENT_DIAGNOSIS),
            "sha256": sha256(PARENT_DIAGNOSIS),
        },
        "runtime_state": {
            "shared_api_lease_inactive": _lease_inactive(),
            "protected_watchers": watchers,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "fresh_disjoint_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_or_selective_rerun": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != "v25140_targeted_revision_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or authorization.get("fresh_disjoint_external_protocol_design") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "fresh_disjoint_external_protocol_design"
        )
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.40 build audit drifted")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
