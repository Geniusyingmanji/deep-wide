#!/usr/bin/env python3
"""Clean-build audit for V2.47.56 zero-effect structured integration."""

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
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24757_zero_effect_integration_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24755_generic_structured_adapter_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("src/deepwide_agent/v24754_generic_structured_page_adapter.py"),
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("tests/test_v24743_generic_record_binding.py"),
    Path("tests/test_v24754_generic_structured_page_adapter.py"),
    Path("tests/test_v24756_zero_effect_structured_integration.py"),
    Path("scripts/audit_v24757_zero_effect_integration_build.py"),
    Path("tests/test_audit_v24757_zero_effect_integration_build.py"),
    PARENT,
)
TEST_SUITES = (
    (Path("tests/test_v24743_generic_record_binding.py"), 12),
    (Path("tests/test_v24754_generic_structured_page_adapter.py"), 9),
    (Path("tests/test_v24756_zero_effect_structured_integration.py"), 6),
    (Path("tests/test_audit_v24757_zero_effect_integration_build.py"), 2),
)
EXPECTED_TESTS = 29
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
RUNNER_MARKERS = (
    "scripts/v24752_host_local_gate.py run",
    "scripts/run_v24756",
    "scripts/run_v24758",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
PRIVILEGED = frozenset(
    {
        "answer",
        "answer_key",
        "category",
        "evaluator",
        "gold",
        "ground_truth",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
EVALUATOR_IMPORT_MARKERS = (
    "official_eval",
    "evaluator_mapping",
    "external_evaluator",
    "finalize_v24",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.57 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.57 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


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


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not _tracked(relative)
    ):
        raise RuntimeError(f"V2.47.57 expected tracked file: {relative}")
    return path


def _manifest() -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        raw = _ordinary(relative).read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.57 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def _parent_valid() -> bool:
    parent = _read(ROOT / PARENT)
    return bool(
        parent.get("role") == "v24755_generic_structured_adapter_build_audit"
        and parent.get("audit_valid") is True
        and parent.get("findings") == []
        and parent.get("tests", {}).get("observed") == 23
        and parent.get("authorization", {}).get(
            "fresh_external_population_and_protocol_design"
        )
        is True
        and parent.get("authorization", {}).get("external_launch") is False
        and parent.get("authorization", {}).get("exact220") is False
        and _sealed(parent, "audit_payload_sha256")
    )


def ast_findings() -> tuple[list[str], list[str]]:
    accesses: list[str] = []
    imports: list[str] = []
    for relative in SOURCES[:3]:
        tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value.casefold()
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = (
                    node.slice.value.casefold()
                    if isinstance(node.slice.value, str)
                    else None
                )
            if key in PRIVILEGED:
                accesses.append(f"{relative}:{node.lineno}:{key}")
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _run_tests() -> tuple[bool, int, str]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    total = 0
    passed = True
    outputs: list[str] = []
    for suite, expected in TEST_SUITES:
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
                suite.name,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            check=False,
        )
        outputs.append(completed.stdout)
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        total += observed
        passed = passed and completed.returncode == 0 and observed == expected
    return passed and total == EXPECTED_TESTS, total, "\n".join(outputs)


def _watchers() -> list[dict[str, Any]]:
    output = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        proc = Path("/proc") / str(pid)
        raw = (proc / "stat").read_text(encoding="utf-8")
        ticks = int(raw[raw.rfind(")") + 2 :].split()[19])
        command = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(
            errors="replace"
        )
        if ticks != expected_ticks or marker not in command:
            raise RuntimeError("V2.47.57 protected watcher drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def _lease_inactive() -> bool:
    path = ROOT / LEASE_PATH
    if path.is_symlink():
        return False
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _runner_active() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        marker in line
        and len(line.split()) >= 2
        and "python" in line.split()[1].casefold()
        for marker in RUNNER_MARKERS
        for line in completed.stdout.splitlines()
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = _manifest()
    tests_passed, observed, test_output = _run_tests()
    accesses, imports = ast_findings()
    watchers = _watchers()
    lease_inactive = _lease_inactive()
    runner_active = _runner_active()
    repository_clean = not _git("status", "--porcelain")
    head_pushed = _git("rev-parse", "HEAD") == _git("rev-parse", "target/main")
    findings: list[str] = []
    if not _parent_valid():
        findings.append("adapter_build_parent_invalid")
    if not tests_passed:
        findings.append("directed_tests_failed")
    if accesses or imports:
        findings.append("label_blind_ast_failed")
    if not lease_inactive:
        findings.append("shared_lease_active")
    if runner_active:
        findings.append("runner_active")
    if not repository_clean or not head_pushed:
        findings.append("repository_not_clean_pushed_head")
    value = {
        "artifact_version": 1,
        "role": "v24757_zero_effect_integration_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_adapter_build_audit_sha256": sha256(ROOT / PARENT),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "tests": {
            "passed": tests_passed,
            "observed": observed,
            "expected": EXPECTED_TESTS,
            "output_sha256": hashlib.sha256(test_output.encode()).hexdigest(),
        },
        "label_blind_audit": {
            "privileged_accesses": accesses,
            "evaluator_imports": imports,
            "passed": not accesses and not imports,
        },
        "integration_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "baseline_precedes_adapter": True,
            "adapter_pages_content_multiset_subset_of_synthesis_evidence": True,
            "redirect_resolved_final_url_required": True,
            "unfetched_snippet_or_search_narrative_replayed": False,
            "adapter_model_query_search_fetch_or_token_delta": 0,
            "ordinary_records_require_two_registrably_independent_sources": True,
            "nonunknown_cells_mutable": False,
            "entropy_or_prediction_change_positive_credit": False,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": lease_inactive,
            "runner_active": runner_active,
        },
        "git": {
            "repository_clean": repository_clean,
            "head_equals_target_main": head_pushed,
        },
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_external_population_and_protocol_design": not findings,
            "external_launch": False,
            "paired_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    tests = copied.get("tests", {})
    label = copied.get("label_blind_audit")
    state = copied.get("runtime_state", {})
    git = copied.get("git")
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    if (
        copied.get("role") != "v24757_zero_effect_integration_build_audit"
        or copied.get("parent_adapter_build_audit_sha256") != sha256(ROOT / PARENT)
        or copied.get("dependency_manifest") != _manifest()
        or copied.get("dependency_manifest_sha256")
        != payload_sha256(copied.get("dependency_manifest"))
        or tests.get("passed") is not True
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("expected") != EXPECTED_TESTS
        or label
        != {
            "privileged_accesses": [],
            "evaluator_imports": [],
            "passed": True,
        }
        or copied.get("integration_contract")
        != {
            "runtime_input_keys": ["opaque_id", "question"],
            "baseline_precedes_adapter": True,
            "adapter_pages_content_multiset_subset_of_synthesis_evidence": True,
            "redirect_resolved_final_url_required": True,
            "unfetched_snippet_or_search_narrative_replayed": False,
            "adapter_model_query_search_fetch_or_token_delta": 0,
            "ordinary_records_require_two_registrably_independent_sources": True,
            "nonunknown_cells_mutable": False,
            "entropy_or_prediction_change_positive_credit": False,
        }
        or state.get("protected_watchers") != _watchers()
        or state.get("shared_api_lease_inactive") is not True
        or state.get("runner_active") is not False
        or git != {"repository_clean": True, "head_equals_target_main": True}
        or copied.get("source_policy")
        != {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
            "credential_read_hashed_persisted_or_emitted": False,
        }
        or not isinstance(findings, list)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "fresh_external_population_and_protocol_design": bool(valid),
            "external_launch": False,
            "paired_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.57 integration build audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    audit = build_audit()
    _publish(ROOT / OUTPUT, audit)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": audit["audit_valid"],
                "tests": audit["tests"]["observed"],
                "findings": audit["findings"],
            },
            sort_keys=True,
        )
    )
