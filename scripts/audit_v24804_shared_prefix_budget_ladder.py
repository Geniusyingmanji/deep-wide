#!/usr/bin/env python3
"""Build-only audit for the V2.48.04 external shared-prefix budget ladder."""

from __future__ import annotations

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

from deepwide_agent.v24804_shared_prefix_budget_ladder import (  # noqa: E402
    ARMS,
    POLICY_ID,
    AdaptivePolicy,
    decide_adaptive,
)


DATE = "20260807"
OUTPUT = Path(f"results/v24804_shared_prefix_budget_ladder_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24803_v24800_aggregate_failure_surface_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24804_shared_prefix_budget_ladder.py"),
    Path("tests/test_v24804_shared_prefix_budget_ladder.py"),
    Path("scripts/audit_v24804_shared_prefix_budget_ladder.py"),
)
RUNTIME = SOURCES[0]
TEST = SOURCES[1]
EXPECTED_TESTS = 6
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)
PRIVILEGED = frozenset(
    {
        "benchmark_question_type", "question_type", "task_category", "category",
        "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator",
        "score", "reward",
    }
)
EVALUATOR_IMPORT_MARKERS = (
    "official_eval", "official_evaluator", "finalize_v24", "evaluator_mapping",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
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
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.04 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.04 audit expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def ast_findings(relative: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
    accesses: list[str] = []
    imports: list[str] = []
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
            accesses.append(f"{relative}:{node.lineno}:{key}")
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        for name in names:
            if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _watchers() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.04 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.48.04 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def _lease_inactive() -> bool:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-c",
            "from pathlib import Path; import fcntl, os; "
            "p=Path('outputs/deepwide_benchmark_api.lease.lock'); "
            "p.parent.mkdir(parents=True,exist_ok=True); "
            "fd=os.open(p,os.O_RDWR|os.O_CREAT,0o600); "
            "fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); "
            "fcntl.flock(fd,fcntl.LOCK_UN); os.close(fd)",
        ],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=10, check=False,
    )
    return completed.returncode == 0


def _parent_valid() -> bool:
    value = _read(PARENT)
    return (
        value.get("role") == "v24803_v24800_aggregate_failure_surface"
        and value.get("diagnosis_valid") is True and value.get("findings") == []
        and value.get("authorization", {}).get(
            "benchmark_external_shared_prefix_implementation"
        ) is True
        and value.get("authorization", {}).get("new_public_exact220") is False
        and _sealed(value, "diagnosis_payload_sha256")
    )


def _synthetic_decision_gate() -> dict[str, Any]:
    statistics = {
        "requested_target_count": 8,
        "returned_result_count": 0,
        "valid_exact_record_count": 0,
        "null_value_record_count": 0,
        "invalid_exact_response_count": 0,
        "unmatched_or_duplicate_result_count": 0,
        "missing_response_count": 8,
    }
    reference = hashlib.sha256(b"v24804-calibration").hexdigest()
    expand = decide_adaptive(
        first_records=[], first_stats=statistics,
        policy=AdaptivePolicy(
            calibration_ref_sha256=reference, per_lookup_cost=0.0
        ),
    )
    stop = decide_adaptive(
        first_records=[], first_stats=statistics,
        policy=AdaptivePolicy(
            calibration_ref_sha256=reference, per_lookup_cost=1.0
        ),
    )
    fail_closed = decide_adaptive(
        first_records=[], first_stats=statistics,
        policy=AdaptivePolicy(
            calibration_ref_sha256=reference,
            calibration_complete=False,
            per_lookup_cost=0.0,
        ),
    )
    return {
        "arms": list(ARMS),
        "policy_id": POLICY_ID,
        "expand_decision": expand["decision"],
        "stop_decision": stop["decision"],
        "calibration_incomplete_decision": fail_closed["decision"],
        "calibration_incomplete_reason": fail_closed["reason"],
        "entropy_feature_value_zero": all(
            row["information_gain_feature_value"] == 0
            for row in (expand, stop, fail_closed)
        ),
        "entropy_assigns_signed_credit_false": all(
            row["entropy_assigns_signed_credit"] is False
            for row in (expand, stop, fail_closed)
        ),
        "wave_two_response_read_false": all(
            row["wave_two_response_or_value_read"] is False
            for row in (expand, stop, fail_closed)
        ),
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    before = _watchers()
    accesses, imports = ast_findings(RUNTIME)
    test = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / TEST), "-v"],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=60, check=False,
    )
    after = _watchers()
    source_text = "\n".join(
        _ordinary(relative).read_text(encoding="utf-8") for relative in SOURCES
    )
    test_count = test.stdout.count(" ... ok")
    decision = _synthetic_decision_gate()
    checks = {
        "parent_authority_valid": _parent_valid(),
        "focused_tests_passed": test.returncode == 0
        and test_count == EXPECTED_TESTS,
        "runtime_privileged_access_absent": accesses == [],
        "runtime_evaluator_import_absent": imports == [],
        "credential_literal_absent": SECRET.search(source_text) is None,
        "three_arms_exact": decision["arms"] == list(ARMS),
        "expand_and_stop_paths_both_reachable": decision["expand_decision"]
        == "expand" and decision["stop_decision"] == "stop",
        "missing_calibration_fails_closed": decision[
            "calibration_incomplete_decision"
        ] == "stop" and decision["calibration_incomplete_reason"]
        == "calibration_incomplete_fail_closed",
        "entropy_is_zero_weight_and_not_credit": decision[
            "entropy_feature_value_zero"
        ] and decision["entropy_assigns_signed_credit_false"],
        "adaptive_decision_is_suffix_blind": decision[
            "wave_two_response_read_false"
        ],
        "protected_watchers_unchanged": before == after,
        "shared_api_lease_inactive": _lease_inactive(),
    }
    value = {
        "artifact_version": 1,
        "role": "v24804_shared_prefix_budget_ladder_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": _git("rev-parse", "HEAD"),
        "parent_sha256": _sha256(PARENT),
        "source_manifest": {str(path): _sha256(path) for path in SOURCES},
        "focused_test_count": test_count,
        "runtime_privileged_accesses": accesses,
        "runtime_evaluator_imports": imports,
        "synthetic_decision_gate": decision,
        "protected_watchers_before": before,
        "protected_watchers_after": after,
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "effect_boundary": {
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "benchmark_task_or_private_evaluator_resource_opened": False,
            "external_population_consumed": False,
            "public_benchmark_forward_authorized": False,
        },
        "authorization": {
            "fresh_benchmark_external_population_and_protocol_design": all(
                checks.values()
            ),
            "external_launch": False,
            "public_dev64": False,
            "public_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v24804_shared_prefix_budget_ladder_build_audit"
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization") != {
            "fresh_benchmark_external_population_and_protocol_design": True,
            "external_launch": False, "public_dev64": False,
            "public_exact220": False, "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.04 build audit drifted")
    return copied


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
    audit = build_audit()
    publish(ROOT / OUTPUT, audit)
    print(json.dumps({
        "output": str(OUTPUT), "audit_valid": audit["audit_valid"],
        "focused_test_count": audit["focused_test_count"],
        "authorization": audit["authorization"],
    }, sort_keys=True))
