#!/usr/bin/env python3
"""Freeze the zero-runtime-effect V2.51.13 preactivation failure."""

from __future__ import annotations

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

from deepwide_agent import v25113_schema_recovered_external_contract as parent  # noqa: E402


OUTPUT = Path("results/v25114_v25113_failed_preactivation_audit_v1_20260811.json")
EXPECTED_BUILD_SHA256 = "9b3b5207c5d3a7b66948dd7ea86a4001b6ae98a8371127749df4b139d8d0d398"
EXPECTED_PROTOCOL_SHA256 = "088ffc59d2c08467a4e59ba5eac2f2eb73adba7647a7b1e1f5ae2f5d263b7717"
EXPECTED_HEAD = "9200dc80ee5b95a5298c752121a16db3407d0bdc"
PROTECTED_WATCHERS = {
    795336: 713986317,
    2808901: 746680268,
    2889939: 746969965,
    3061652: 747569004,
}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha256(relative: Path) -> str:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.51.14 expected ordinary repository file")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
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


def _test_reproduction() -> dict[str, Any]:
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
            "test_v25113_schema_recovered_external.py",
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
    ran = re.search(r"Ran (\d+) tests?", completed.stdout)
    failed = re.search(r"FAILED \(errors=(\d+)\)", completed.stdout)
    return {
        "pattern": "test_v25113_schema_recovered_external.py",
        "observed_tests": int(ran.group(1)) if ran else 0,
        "observed_errors": int(failed.group(1)) if failed else 0,
        "returncode": completed.returncode,
        "build_audit_phase_test_named": (
            "test_build_audit_authorizes_protocol_only" in completed.stdout
        ),
        "protocol_pristine_phase_test_named": (
            "test_protocol_freezes_population_and_twenty_by_four_scheduling"
            in completed.stdout
        ),
        "output_sha256": payload_sha256(completed.stdout),
        "question_prediction_page_query_url_gold_score_or_credential_emitted": False,
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
    path = ROOT / parent.LEASE_PATH
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


def _absent_surfaces() -> dict[str, bool]:
    paths = (
        parent.PREAUDIT,
        parent.EXECUTION_START,
        parent.FORWARD_RESULT,
        parent.FORWARD_AUDIT,
        parent.EVALUATOR,
        parent.EVALUATOR_TEST,
        parent.EVALUATOR_PROTOCOL,
        parent.RESULT,
        parent.POSTAUDIT,
        parent.OUTPUT_ROOT,
    )
    return {
        str(path): not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    }


def _active_target_processes() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (
        str(parent.RUNNER),
        str(parent.EVALUATOR),
    )
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    reproduction = _test_reproduction()
    surfaces = _absent_surfaces()
    watchers = _watchers()
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25114_v25113_failed_preactivation_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "build_audit_sha256": _sha256(parent.BUILD_AUDIT),
            "protocol_sha256": _sha256(parent.PROTOCOL),
            "git_head": head,
            "target_main": target,
        },
        "failure": {
            "stage": "preactivation_before_publication",
            "finding": "focused_and_parent_tests_exact126",
            "test_reproduction": reproduction,
            "root_cause": "two_build_phase_tests_were_not_protocol_phase_stable",
            "build_audit_test_observed_existing_protocol_and_failed_future_pristine_check": True,
            "protocol_test_required_protocol_path_absence_after_protocol_was_frozen": True,
            "runtime_parser_budget_or_stage_accounting_failure_observed": False,
        },
        "effects": {
            "preactivation_artifact_published": False,
            "execution_start_published": False,
            "output_root_or_model_slots_created": False,
            "model_search_fetch_evaluator_or_benchmark_api_called": False,
            "local_keyless_socket_reachability_preflight_attempted": True,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        },
        "absent_surfaces": surfaces,
        "runtime_state": {
            "shared_api_lease_inactive": _lease_inactive(),
            "active_target_processes": _active_target_processes(),
            "protected_watchers": watchers,
        },
        "content_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "question_prediction_page_query_url_answer_or_credential_persisted_or_emitted": False,
        },
        "authorization": {
            "append_only_phase_stable_test_fix": True,
            "fresh_recovery_namespace_reusing_zero_effect_population": True,
            "v25113_protocol_overwrite_activation_or_forward": False,
            "evaluator_deepwidebench_exact220_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    parents = copied.get("parents") or {}
    failure = copied.get("failure") or {}
    reproduction = failure.get("test_reproduction") or {}
    effects = copied.get("effects") or {}
    state = copied.get("runtime_state") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != "v25114_v25113_failed_preactivation_audit"
        or parents.get("build_audit_sha256") != EXPECTED_BUILD_SHA256
        or parents.get("protocol_sha256") != EXPECTED_PROTOCOL_SHA256
        or parents.get("git_head") != EXPECTED_HEAD
        or parents.get("target_main") != EXPECTED_HEAD
        or failure.get("stage") != "preactivation_before_publication"
        or failure.get("finding") != "focused_and_parent_tests_exact126"
        or reproduction.get("observed_tests") != 12
        or reproduction.get("observed_errors") != 2
        or reproduction.get("returncode") == 0
        or reproduction.get("build_audit_phase_test_named") is not True
        or reproduction.get("protocol_pristine_phase_test_named") is not True
        or failure.get(
            "build_audit_test_observed_existing_protocol_and_failed_future_pristine_check"
        )
        is not True
        or failure.get(
            "protocol_test_required_protocol_path_absence_after_protocol_was_frozen"
        )
        is not True
        or failure.get("runtime_parser_budget_or_stage_accounting_failure_observed")
        is not False
        or any(copied.get("absent_surfaces", {}).values()) is not True
        or not all(copied.get("absent_surfaces", {}).values())
        or effects.get("local_keyless_socket_reachability_preflight_attempted") is not True
        or any(
            effects.get(name) is not False
            for name in (
                "preactivation_artifact_published",
                "execution_start_published",
                "output_root_or_model_slots_created",
                "model_search_fetch_evaluator_or_benchmark_api_called",
                "retry_resume_skip_population_replacement_or_selective_rerun",
            )
        )
        or state.get("shared_api_lease_inactive") is not True
        or state.get("active_target_processes") != []
        or any(
            row.get("matches_frozen_identity") is not True
            for row in (state.get("protected_watchers") or {}).values()
        )
        or authorization.get("append_only_phase_stable_test_fix") is not True
        or authorization.get("fresh_recovery_namespace_reusing_zero_effect_population")
        is not True
        or authorization.get("v25113_protocol_overwrite_activation_or_forward") is not False
        or authorization.get("evaluator_deepwidebench_exact220_leaderboard_or_sota")
        is not False
        or copied.get("content_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.14 failed preactivation audit drifted")
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
    print(json.dumps({"path": str(OUTPUT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
