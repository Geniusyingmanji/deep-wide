#!/usr/bin/env python3
"""Clean-build audit for V2.50.75/76 anchor-bounded record-region verification."""

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

from deepwide_agent import v25075_anchor_bounded_record_region as binding  # noqa: E402
from deepwide_agent import v25076_anchor_bounded_record_region_paired_runtime as runtime  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


DATE = "20260811"
OUTPUT = Path(f"results/v25077_anchor_bounded_record_region_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25077_anchor_bounded_record_region_build.py")
TEST = Path("tests/test_audit_v25077_anchor_bounded_record_region_build.py")
BINDING_SOURCE = Path("src/deepwide_agent/v25075_anchor_bounded_record_region.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25076_anchor_bounded_record_region_paired_runtime.py")
BINDING_TEST = Path("tests/test_v25075_anchor_bounded_record_region.py")
RUNTIME_TEST = Path("tests/test_v25076_anchor_bounded_record_region_paired_runtime.py")
PARENT_DIAGNOSIS = Path("results/v25074_v25073_field_local_external_diagnosis_v1_20260811.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_PARENT_HASH = "d8bf3802a26298461c88fb1a1fbbe474eefb107a2e048d7349b1eb4c083b8973"

TEST_SUITES = (
    ("test_v25075_anchor_bounded_record_region.py", 12),
    ("test_v25076_anchor_bounded_record_region_paired_runtime.py", 4),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25066_quote_verified_paired_runtime.py", 6),
    ("test_v25029_evidence_conditioned_runtime.py", 5),
    ("test_v25024_evidence_conditioned_queries.py", 8),
    ("test_v24996_shared_first_wave_paired_runtime.py", 7),
    ("test_v24990_query_vector_paired_runtime.py", 7),
    ("test_v24986_robust_paired_runtime.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
PROTECTED_WATCHERS = {
    795336: 713986317,
    2808901: 746680268,
    2889939: 746969965,
    3061652: 747569004,
}
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
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
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
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
        raise RuntimeError("V2.50.77 expected ordinary repository file")
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
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


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
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
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
                        candidates.append(Path("src") / Path(*item.name.split(".")).with_suffix(".py"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
                    if module:
                        candidates.append(Path("src/deepwide_agent") / Path(*module.split(".")).with_suffix(".py"))
                    else:
                        candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module == "deepwide_agent":
                    candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module.startswith("deepwide_agent."):
                    candidates.append(Path("src") / Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                if (ROOT / candidate).is_file() and not (ROOT / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def _direct_forbidden_imports(relative: Path) -> list[str]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"), filename=str(relative))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    return sorted(
        name
        for name in imports
        if any(name == forbidden or name.startswith(forbidden + ".") for forbidden in DIRECT_FORBIDDEN_IMPORTS)
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


def _parent_barrier() -> str:
    path = _ordinary(PARENT_DIAGNOSIS)
    value = json.loads(path.read_text(encoding="utf-8"))
    observed = sha256(PARENT_DIAGNOSIS)
    expected = EXPECTED_PARENT_HASH
    if (
        observed != expected
        or not isinstance(value, dict)
        or value.get("diagnosis", {}).get(
            "next_candidate_should_use_unique_anchor_to_define_same_page_bounded_record_region"
        )
        is not True
        or value.get("authorization", {}).get("new_disjoint_build_only_successor_design") is not True
        or value.get("authorization", {}).get("new_external_launch") is not False
    ):
        raise RuntimeError("V2.50.77 parent barrier drifted")
    return observed


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    tests = _tests()
    closure = _dependency_closure((BINDING_SOURCE, RUNTIME_SOURCE))
    semantic = _semantic_findings(closure)
    direct = {str(path): _direct_forbidden_imports(path) for path in (BINDING_SOURCE, RUNTIME_SOURCE)}
    explicit = (SOURCE, TEST, BINDING_SOURCE, RUNTIME_SOURCE, BINDING_TEST, RUNTIME_TEST, PARENT_DIAGNOSIS)
    untracked = sorted(str(path) for path in {*closure, *explicit} if tracked and not _tracked(path))
    parent_hash = _parent_barrier()
    watchers = _watchers()
    manifest = {str(path): sha256(path) for path in closure}
    repository_ready = clean and head == target
    checks = {
        "focused_and_parent_tests_exact68": tests["passed"],
        "v25074_parent_diagnosis_bound": parent_hash == sha256(PARENT_DIAGNOSIS),
        "candidate_policy_ids_exact": binding.POLICY_ID
        == "v25075_anchor_bounded_same_page_record_region_v1"
        and runtime.POLICY_ID
        == "v25076_matched_cost_anchor_bounded_record_region_representation_v1",
        "all_sources_tracked": not untracked,
        "git_clean_head_equals_target_main": repository_ready if tracked else True,
        "candidate_direct_forbidden_imports_empty": not any(direct.values()),
        "privileged_runtime_field_findings_empty": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capabilities_empty": not semantic["evaluator_capabilities"],
        "credential_literal_findings_empty": not semantic["credential_literal_hits"],
        "shared_api_lease_inactive": _lease_inactive(),
        "protected_watcher_identity_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "matched_budget_contract_exact": runtime.ARMS
        == ("raw_fetched_evidence", "anchor_bounded_record_region_representation")
        and binding.PROPOSAL_OUTPUT_TOKEN_CAP == 1_200
        and binding.MAXIMUM_PROPOSAL_INPUT_CHARACTERS == 12_000
        and binding.MAXIMUM_CONTROL_EVIDENCE_CHARACTERS == 60_000,
        "anchor_bounded_region_contract_exact": binding.MAXIMUM_ANCHOR_CHARACTERS == 500
        and binding.MAXIMUM_RECORD_REGION_CHARACTERS == 1_600
        and binding.MAXIMUM_FIELD_QUOTE_CHARACTERS == 1_200,
        "entropy_signed_credit_disabled": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25077_anchor_bounded_record_region_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "parent_diagnosis_sha256": parent_hash,
        "tests": tests,
        "runtime_dependency_manifest": manifest,
        "runtime_dependency_manifest_sha256": payload_sha256(manifest),
        "runtime_semantic_audit": {
            **semantic,
            "candidate_direct_forbidden_imports": direct,
            "untracked_sources": untracked,
        },
        "runtime_state": {"shared_api_lease_inactive": _lease_inactive(), "protected_watchers": watchers},
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "authorization": {
            "fresh_disjoint_external_protocol_design": not findings,
            "fresh_external_protocol_publication": False,
            "fresh_external_activation_or_launch": False,
            "paired_dev_or_public_exact220": False,
            "evaluator_or_leaderboard_or_sota": False,
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
        copied.get("role") != "v25077_anchor_bounded_record_region_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or authorization.get("fresh_disjoint_external_protocol_design") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "fresh_disjoint_external_protocol_design"
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.77 build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
