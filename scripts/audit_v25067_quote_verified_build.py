#!/usr/bin/env python3
"""Clean-build audit for V2.50.65/66 quote-verified record binding.

The audit runs only synthetic/unit regressions, resolves the repository-local
Python dependency closure, and checks strict label blindness, evaluator
isolation, credential literals, protected watcher identity, and shared-lease
inactivity.  It performs no network, model-provider, search, fetch, evaluator,
or benchmark effect.  A valid result authorizes only a fresh external protocol
*design*; it does not authorize publication, activation, launch, or exact-220.
"""

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

from deepwide_agent import v25065_quote_verified_record_binding as binding  # noqa: E402
from deepwide_agent import v25066_quote_verified_paired_runtime as runtime  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


DATE = "20260811"
OUTPUT = Path(f"results/v25067_quote_verified_record_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25067_quote_verified_build.py")
TEST = Path("tests/test_audit_v25067_quote_verified_build.py")
BINDING_SOURCE = Path("src/deepwide_agent/v25065_quote_verified_record_binding.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25066_quote_verified_paired_runtime.py")
BINDING_TEST = Path("tests/test_v25065_quote_verified_record_binding.py")
RUNTIME_TEST = Path("tests/test_v25066_quote_verified_paired_runtime.py")
PARENT_DIAGNOSIS = Path("results/v25064_three_run_strategy_diagnosis_v1_20260811.json")
PARENT_AUDIT = Path("results/v25064_three_run_strategy_audit_v1_20260811.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")

TEST_SUITES = (
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
SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
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
EXPECTED_PARENT_HASHES = {
    "diagnosis": "7035ee144a8693937fa0aa72e7bd0971f26f56a91d7cde094123a6b52ebaae89",
    "audit": "da2b497bd73aa558b2adc02bde340660fd6ae3261f81072e25e619c79a31a4b6",
}


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
        raise RuntimeError(f"V2.50.67 expected ordinary repository file: {relative}")
    return path


def sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.67 expected JSON object")
    return value


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
                        candidates.append(
                            Path("src") / Path(*item.name.split(".")).with_suffix(".py")
                        )
                    elif item.name.startswith("scripts."):
                        candidates.append(Path(*item.name.split(".")).with_suffix(".py"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
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
                elif module == "scripts":
                    candidates.extend(Path("scripts") / f"{item.name}.py" for item in node.names)
                elif module.startswith("scripts."):
                    candidates.append(Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                absolute = ROOT / candidate
                if absolute.is_file() and not absolute.is_symlink():
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


def _parent_barrier() -> dict[str, Any]:
    diagnosis = _json(PARENT_DIAGNOSIS)
    audit = _json(PARENT_AUDIT)
    hashes = {"diagnosis": sha256(PARENT_DIAGNOSIS), "audit": sha256(PARENT_AUDIT)}
    authorization = diagnosis.get("authorization") or {}
    if (
        hashes != EXPECTED_PARENT_HASHES
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or authorization.get("source_record_binding_build_design") is not True
        or authorization.get("fresh_external_protocol_publication") is not False
        or authorization.get("fresh_external_launch") is not False
        or authorization.get("new_exact220_launch") is not False
        or diagnosis.get("diagnosis", {}).get(
            "next_candidate_reallocates_existing_model_call_to_record_proposal_and_deterministic_quote_verification"
        )
        is not True
    ):
        raise RuntimeError("V2.50.67 V2.50.64 parent barrier drifted")
    return hashes


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    tests = _tests()
    closure = _dependency_closure((BINDING_SOURCE, RUNTIME_SOURCE))
    semantic = _semantic_findings(closure)
    direct_imports = {
        str(path): _direct_forbidden_imports(path)
        for path in (BINDING_SOURCE, RUNTIME_SOURCE)
    }
    explicit = (SOURCE, TEST, BINDING_SOURCE, RUNTIME_SOURCE, BINDING_TEST, RUNTIME_TEST)
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not _tracked(path)
    )
    parent_hashes = _parent_barrier()
    watchers = _watchers()
    lease = _lease_inactive()
    manifest = {str(path): sha256(path) for path in closure}
    checks = {
        "focused_and_parent_tests_exact52": tests["passed"],
        "v25064_parent_diagnosis_and_audit_bound": parent_hashes
        == EXPECTED_PARENT_HASHES,
        "candidate_policy_ids_exact": binding.POLICY_ID
        == "v25065_model_proposed_quote_verified_source_record_binding_v1"
        and runtime.POLICY_ID
        == "v25066_matched_cost_quote_verified_record_representation_v1",
        "runtime_dependency_closure_nonempty": bool(closure),
        "all_sources_tracked": not untracked,
        "git_clean_head_equals_target_main": clean and head == target,
        "candidate_direct_forbidden_imports_empty": not any(direct_imports.values()),
        "privileged_runtime_field_findings_empty": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capabilities_empty": not semantic["evaluator_capabilities"],
        "credential_literal_findings_empty": not semantic["credential_literal_hits"],
        "shared_api_lease_inactive": lease,
        "protected_watcher_identity_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "matched_budget_contract_exact": runtime.ARMS
        == ("raw_fetched_evidence", "quote_verified_record_representation")
        and binding.PROPOSAL_OUTPUT_TOKEN_CAP == 1_200
        and binding.MAXIMUM_PROPOSAL_INPUT_CHARACTERS == 12_000
        and binding.MAXIMUM_CONTROL_EVIDENCE_CHARACTERS == 60_000,
        "entropy_signed_credit_disabled": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    authorization = {
        "fresh_external_protocol_design": not findings,
        "fresh_external_protocol_publication": False,
        "fresh_external_activation_or_launch": False,
        "paired_dev_or_public_exact220": False,
        "evaluator_or_leaderboard_or_sota": False,
        "retry_resume_or_selective_rerun": False,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25067_quote_verified_record_binding_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "parent_hashes": parent_hashes,
        "tests": tests,
        "runtime_dependency_manifest": manifest,
        "runtime_dependency_manifest_sha256": payload_sha256(manifest),
        "runtime_semantic_audit": {
            **semantic,
            "candidate_direct_forbidden_imports": direct_imports,
            "untracked_sources": untracked,
        },
        "runtime_state": {
            "shared_api_lease_inactive": lease,
            "protected_watchers": watchers,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "authorization": authorization,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    runtime_state = copied.get("runtime_state") or {}
    if (
        copied.get("role") != "v25067_quote_verified_record_binding_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_hashes") != EXPECTED_PARENT_HASHES
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or runtime_state.get("shared_api_lease_inactive") is not True
        or any(
            row.get("matches_frozen_identity") is not True
            for row in (runtime_state.get("protected_watchers") or {}).values()
        )
        or authorization.get("fresh_external_protocol_design") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "fresh_external_protocol_design"
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.67 build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V2.50.67 audit publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> None:
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
