#!/usr/bin/env python3
"""Two-wave benchmark-external World Bank transport reliability gate.

This script contains protocol, audit, execution, and post-result validation for
one fixed experiment.  It reads no benchmark resource and calls no model,
search system, or evaluator.  Twelve public endpoints (six indicators by two
official representations) are each requested once per wave under an OS-enforced
hard total-wall timeout.  Only content-free receipt metadata is persisted.
"""

from __future__ import annotations

import ast
import base64
import concurrent.futures
import fcntl
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24719_worldbank_transport_reliability as runtime  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24721_worldbank_dual_transport_two_wave_v1"
PROTOCOL = Path(f"results/v24721_worldbank_transport_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24721_worldbank_transport_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24721_worldbank_transport_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24721_worldbank_transport_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24721_worldbank_transport_result_v1_{DATE}.json")
DECISION = Path(f"results/v24721_worldbank_transport_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24721_worldbank_transport_postresult_audit_v1_{DATE}.json")
HELPER = Path("scripts/v24720_public_get_helper.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v24719_worldbank_transport_reliability.py")
RUNTIME_TEST = Path("tests/test_v24719_worldbank_transport_reliability.py")
HELPER_TEST = Path("tests/test_v24720_public_get_helper.py")
SCRIPT = Path("scripts/v24721_worldbank_transport_gate.py")
SCRIPT_TEST = Path("tests/test_v24721_worldbank_transport_gate.py")
PARENTS = (
    Path(f"results/v24700_v24694_worldbank_postresult_audit_v1_{DATE}.json"),
    Path(f"results/v24706_full220_visible_authority_scope_audit_v1_{DATE}.json"),
    Path(f"results/v24718_v24714_identity_full220_postresult_audit_v1_{DATE}.json"),
)
SOURCES = (RUNTIME_SOURCE, HELPER, RUNTIME_TEST, HELPER_TEST, SCRIPT, SCRIPT_TEST, *PARENTS)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24721_worldbank_transport_gate_v1"
LEASE_PURPOSE = "benchmark_external_worldbank_dual_transport_reliability"
RUNNER_MARKER = "scripts/v24721_worldbank_transport_gate.py run"
WAVES = 2
REQUESTS_PER_WAVE = len(runtime.TARGETS) * len(runtime.REPRESENTATIONS)
TOTAL_REQUESTS = WAVES * REQUESTS_PER_WAVE
WORKERS = REQUESTS_PER_WAVE
HARD_WALL_SECONDS = 20.0
SOCKET_TIMEOUT_SECONDS = 15.0
WAVE_WALL_CEILING_SECONDS = 25.0
EXPERIMENT_WALL_CEILING_SECONDS = 55.0
EXPECTED_TESTS = 15
PRIMARY_REPRESENTATION = "aggregate_json"
COMPARATOR_REPRESENTATION = "bulk_zip"
REQUIRED_CHECKS = (
    "primary_all_requests_http_200_and_schema_valid",
    "primary_semantic_stable_across_waves",
    "dual_representation_semantic_agreement_when_both_succeed",
    "all_wave_walls_within_ceiling",
    "experiment_wall_within_ceiling",
    "no_response_content_persisted",
)
TEST_SUITES = (
    (RUNTIME_TEST, 6),
    (HELPER_TEST, 3),
    (SCRIPT_TEST, 6),
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
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
        "instance_id",
        "question",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.47.21 expected repository file: {relative}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.21 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


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


def _require_clean_pushed_head() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.21 requires clean pushed HEAD")


def _watcher_snapshot() -> list[dict[str, Any]]:
    output = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        command = Path("/proc") / str(pid) / "cmdline"
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        ticks = int(suffix[19])
        cmdline = command.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if ticks != expected_ticks or marker not in cmdline:
            raise RuntimeError("V2.47.21 protected watcher drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def _lease_inactive(root: Path) -> bool:
    path = root / LEASE_PATH
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
        ["ps", "-eo", "pid=,args="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        RUNNER_MARKER in line
        and str(os.getpid()) not in line.split(maxsplit=1)[0]
        for line in completed.stdout.splitlines()
    )


def _parents_valid(root: Path) -> bool:
    external, scope, closure = (_read(root, path) for path in PARENTS)
    return bool(
        external.get("role") == "v24700_v24694_worldbank_postresult_audit"
        and external.get("audit_valid") is True
        and external.get("findings") == []
        and external.get("authorization", {}).get("exact220_launch") is False
        and scope.get("role") == "v24706_full220_visible_authority_scope_audit"
        and scope.get("audit_valid") is True
        and scope.get("coverage", {}).get("adapter_route_eligible_task_count") == 1
        and scope.get("authorization", {}).get("exact220") is False
        and closure.get("role") == "v24718_v24714_identity_full220_postresult_audit"
        and closure.get("audit_valid") is True
        and closure.get("findings") == []
        and closure.get("authorization", {}).get("additional_forward_resume_retry_or_rerun") is False
        and closure.get("authorization", {}).get("additional_evaluator_or_revaluation") is False
    )


def _manifest(root: Path) -> dict[str, str]:
    output = {}
    for relative in SOURCES:
        path = _ordinary(root, relative)
        if root.resolve() == ROOT.resolve() and not _tracked(relative):
            raise RuntimeError(f"V2.47.21 untracked source surface: {relative}")
        raw = path.read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.21 credential literal in source surface")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def ast_findings(root: Path = ROOT) -> tuple[list[str], list[str]]:
    accesses: list[str] = []
    imports: list[str] = []
    for relative in (RUNTIME_SOURCE, HELPER, SCRIPT):
        tree = ast.parse(_ordinary(root, relative).read_text(encoding="utf-8"))
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
                key = node.args[0].value
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value if isinstance(node.slice.value, str) else None
            if key is not None and key.casefold() in PRIVILEGED:
                accesses.append(f"{relative}:{node.lineno}:{key}")
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                lowered = name.casefold()
                if any(marker in lowered for marker in ("official_eval", "evaluator_mapping", "finalize_v24")):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    if not _parents_valid(root):
        raise RuntimeError("V2.47.21 parent chain drifted")
    manifest = _manifest(root)
    target_vector = [
        {
            "target_key": runtime.target_key(target),
            "indicator": target.indicator,
            "year": target.year,
            "urls": {
                representation: runtime.endpoint_url(target, representation)
                for representation in runtime.REPRESENTATIONS
            },
        }
        for target in runtime.TARGETS
    ]
    value = {
        "artifact_version": 1,
        "role": "v24721_worldbank_transport_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "benchmark_external_public_worldbank_transport_only",
        "parent_sha256": {str(path): sha256(root / path) for path in PARENTS},
        "target_selection": {
            "rule": "union_of_pre_v24719_worldbank_indicators_already_frozen_by_v24709_and_v24690",
            "selected_after_transport_outcome": False,
            "target_count": len(target_vector),
            "target_vector": target_vector,
            "target_vector_sha256": payload_sha256(target_vector),
        },
        "execution": {
            "waves": WAVES,
            "representations": list(runtime.REPRESENTATIONS),
            "primary_representation": PRIMARY_REPRESENTATION,
            "diagnostic_comparator_representation": COMPARATOR_REPRESENTATION,
            "representation_selected_before_transport_outcome": True,
            "requests_per_wave": REQUESTS_PER_WAVE,
            "total_requests": TOTAL_REQUESTS,
            "workers": WORKERS,
            "attempts_per_endpoint_per_wave": 1,
            "hard_total_wall_seconds_per_request": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "wave_wall_ceiling_seconds": WAVE_WALL_CEILING_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "cache_or_resume": False,
            "retry_or_selective_rerun": False,
        },
        "gates": {
            "required_checks": list(REQUIRED_CHECKS),
            "diagnostic_checks": [
                "bulk_comparator_all_requests_http_200_and_schema_valid"
            ],
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "protected_watchers": _watcher_snapshot(),
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "response_country_value_or_content_persisted": False,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "transport_launch": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def _expected_target_vector() -> list[dict[str, Any]]:
    return [
        {
            "target_key": runtime.target_key(target),
            "indicator": target.indicator,
            "year": target.year,
            "urls": {
                representation: runtime.endpoint_url(target, representation)
                for representation in runtime.REPRESENTATIONS
            },
        }
        for target in runtime.TARGETS
    ]


def validate_protocol(root: Path = ROOT, *, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = protocol.get("dependency_manifest")
    selection = protocol.get("target_selection", {})
    execution = protocol.get("execution", {})
    authorization = protocol.get("authorization", {})
    expected_target_vector = _expected_target_vector()
    if (
        protocol.get("role") != "v24721_worldbank_transport_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope") != "benchmark_external_public_worldbank_transport_only"
        or not _sealed(protocol, "protocol_payload_sha256")
        or protocol.get("parent_sha256") != {str(path): sha256(root / path) for path in PARENTS}
        or selection.get("selected_after_transport_outcome") is not False
        or selection.get("rule")
        != "union_of_pre_v24719_worldbank_indicators_already_frozen_by_v24709_and_v24690"
        or selection.get("target_count") != len(runtime.TARGETS)
        or selection.get("target_vector") != expected_target_vector
        or selection.get("target_vector_sha256") != payload_sha256(selection.get("target_vector"))
        or execution.get("waves") != WAVES
        or execution.get("representations") != list(runtime.REPRESENTATIONS)
        or execution.get("primary_representation") != PRIMARY_REPRESENTATION
        or execution.get("diagnostic_comparator_representation")
        != COMPARATOR_REPRESENTATION
        or execution.get("representation_selected_before_transport_outcome")
        is not True
        or execution.get("requests_per_wave") != REQUESTS_PER_WAVE
        or execution.get("total_requests") != TOTAL_REQUESTS
        or execution.get("workers") != WORKERS
        or execution.get("attempts_per_endpoint_per_wave") != 1
        or execution.get("hard_total_wall_seconds_per_request") != HARD_WALL_SECONDS
        or execution.get("socket_timeout_seconds") != SOCKET_TIMEOUT_SECONDS
        or execution.get("wave_wall_ceiling_seconds") != WAVE_WALL_CEILING_SECONDS
        or execution.get("experiment_wall_ceiling_seconds")
        != EXPERIMENT_WALL_CEILING_SECONDS
        or execution.get("cache_or_resume") is not False
        or execution.get("retry_or_selective_rerun") is not False
        or protocol.get("gates")
        != {
            "required_checks": list(REQUIRED_CHECKS),
            "diagnostic_checks": [
                "bulk_comparator_all_requests_http_200_and_schema_valid"
            ],
        }
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or protocol.get("protected_watchers") != _watcher_snapshot()
        or authorization
        != {
            "preactivation_audit_generation": True,
            "transport_launch": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or any(protocol.get("source_policy", {}).values())
    ):
        raise RuntimeError("V2.47.21 protocol drifted")
    return protocol


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
    outputs: list[str] = []
    observed_total = 0
    passed = True
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
        observed_total += observed
        passed = passed and completed.returncode == 0 and observed == expected
    output = "\n".join(outputs)
    return passed and observed_total == EXPECTED_TESTS, observed_total, output


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    protocol = validate_protocol(root)
    tests_passed, observed, output = _run_tests()
    accesses, imports = ast_findings(root)
    findings = []
    if not tests_passed:
        findings.append("directed_tests_failed")
    if accesses or imports:
        findings.append("label_blind_ast_failed")
    if not _lease_inactive(root):
        findings.append("shared_lease_active")
    if _runner_active():
        findings.append("transport_runner_already_active")
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        findings.append("repository_not_clean_pushed_head")
    if any((root / path).exists() or (root / path).is_symlink() for path in (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24721_worldbank_transport_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "tests": {"passed": tests_passed, "observed": observed, "expected": EXPECTED_TESTS, "output_sha256": hashlib.sha256(output.encode()).hexdigest()},
        "label_blind_audit": {"accesses": accesses, "evaluator_imports": imports, "passed": not accesses and not imports},
        "runtime_state": {"protected_watchers": _watcher_snapshot(), "shared_api_lease_inactive": _lease_inactive(root), "runner_active": _runner_active()},
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "activation_publication": not findings,
            "transport_launch": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if protocol.get("authorization", {}).get("preactivation_audit_generation") is not True:
        raise RuntimeError("V2.47.21 preaudit is not authorized")
    validate_preaudit(value)
    return value


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    tests = copied.get("tests")
    label_blind = copied.get("label_blind_audit")
    state = copied.get("runtime_state")
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    if (
        copied.get("role")
        != "v24721_worldbank_transport_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or not isinstance(tests, Mapping)
        or set(tests)
        != {"passed", "observed", "expected", "output_sha256"}
        or tests.get("passed") is not True
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("expected") != EXPECTED_TESTS
        or not isinstance(tests.get("output_sha256"), str)
        or len(tests["output_sha256"]) != 64
        or label_blind
        != {"accesses": [], "evaluator_imports": [], "passed": True}
        or not isinstance(state, Mapping)
        or state.get("protected_watchers") != _watcher_snapshot()
        or state.get("shared_api_lease_inactive") is not True
        or state.get("runner_active") is not False
        or not isinstance(findings, list)
        or any(not isinstance(item, str) or not item for item in findings)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "activation_publication": bool(valid),
            "transport_launch": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.21 preactivation audit drifted")
    return copied


def _validate_stage(value: Mapping[str, Any], *, role: str, seal: str) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != role
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or not _sealed(copied, seal)
    ):
        raise RuntimeError(f"V2.47.21 {role} drifted")
    return copied


def validate_activation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _validate_stage(
        value,
        role="v24721_worldbank_transport_activation",
        seal="activation_payload_sha256",
    )
    if (
        copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("protected_watchers") != _watcher_snapshot()
        or copied.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or copied.get("launch_authorized") is not True
        or copied.get("authorization")
        != {
            "one_transport_launch": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.47.21 activation drifted")
    return copied


def validate_execution_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _validate_stage(
        value,
        role="v24721_worldbank_transport_execution_start",
        seal="execution_start_payload_sha256",
    )
    if (
        copied.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or copied.get("protected_watchers") != _watcher_snapshot()
        or copied.get("single_owner_no_resume_retry_or_selective_rerun") is not True
        or copied.get("authorization")
        != {
            "execute_once": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
        }
    ):
        raise RuntimeError("V2.47.21 execution-start drifted")
    return copied


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    protocol = validate_protocol(root)
    preaudit = validate_preaudit(_read(root, PREAUDIT))
    if not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.21 activation runtime state is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24721_worldbank_transport_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "protected_watchers": _watcher_snapshot(),
        "network_model_search_fetch_evaluator_or_api_called": False,
        "launch_authorized": True,
        "authorization": {"one_transport_launch": True, "benchmark_dev64_or_exact220": False, "evaluator": False, "leaderboard_or_sota": False},
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if protocol.get("authorization", {}).get("transport_launch") is not False:
        raise RuntimeError("V2.47.21 protocol authorization drifted")
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    activation = validate_activation(_read(root, ACTIVATION))
    if activation.get("launch_authorized") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.21 execution start is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24721_worldbank_transport_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "protected_watchers": _watcher_snapshot(),
        "single_owner_no_resume_retry_or_selective_rerun": True,
        "authorization": {"execute_once": True, "benchmark_dev64_or_exact220": False, "evaluator": False},
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


HELPER_RESULT_KEYS = frozenset({"kind", "status_code", "content_type", "final_url", "body_base64"})


def _environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "DEEPWIDE_EXPECTED_PARENT_PID": str(os.getpid()),
    }


def _terminate_group(process: Any) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=0.5)


def hard_get(url: str, *, timeout_seconds: float = HARD_WALL_SECONDS, popen: Any = subprocess.Popen) -> dict[str, Any]:
    allowed = {
        runtime.endpoint_url(target, representation)
        for target in runtime.TARGETS
        for representation in runtime.REPRESENTATIONS
    }
    if url not in allowed or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("V2.47.21 hard GET input drifted")
    started = time.monotonic()
    process = popen(
        [sys.executable, "-I", "-B", str(ROOT / HELPER)],
        cwd=ROOT,
        env=_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        text=True,
    )
    request = json.dumps({"url": url, "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS}, separators=(",", ":"))
    try:
        stdout, _ = process.communicate(request, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_group(process)
        return {"kind": "hard_total_wall_timeout", "status_code": None, "content_type": "", "final_url": "", "body": b"", "elapsed_seconds": round(time.monotonic() - started, 6)}
    if process.returncode != 0 or len(stdout.encode()) > runtime.MAX_RESPONSE_BYTES * 2:
        return {"kind": "helper_invalid", "status_code": None, "content_type": "", "final_url": "", "body": b"", "elapsed_seconds": round(time.monotonic() - started, 6)}
    try:
        value = json.loads(stdout)
        if not isinstance(value, Mapping) or set(value) != HELPER_RESULT_KEYS:
            raise ValueError("helper schema")
        body = base64.b64decode(value["body_base64"], validate=True) if value["body_base64"] else b""
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"kind": "helper_invalid", "status_code": None, "content_type": "", "final_url": "", "body": b"", "elapsed_seconds": round(time.monotonic() - started, 6)}
    return {
        "kind": str(value["kind"]),
        "status_code": value["status_code"],
        "content_type": str(value["content_type"]),
        "final_url": str(value["final_url"]),
        "body": body,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }


def _request_one(wave: int, target: runtime.TransportTarget, representation: str) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    url = runtime.endpoint_url(target, representation)
    response = hard_get(url)
    raw = response.pop("body")
    success = False
    parsed: dict[str, Any] | None = None
    records: dict[str, Any] | None = None
    failure = response["kind"]
    if (
        response["kind"] == "response"
        and response["status_code"] == 200
        and response["final_url"] == url
    ):
        try:
            parsed = runtime.validate_parsed(runtime.parse_response(raw, target=target, representation=representation))
            records, _updated = runtime.parse_records(raw, target=target, representation=representation)
            success = True
            failure = None
        except ValueError:
            failure = "schema_invalid"
    receipt = {
        "wave": wave,
        "target_key": runtime.target_key(target),
        "indicator": target.indicator,
        "year": target.year,
        "representation": representation,
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "attempts": 1,
        "success": success,
        "failure_type": failure,
        "http_status": response["status_code"],
        "elapsed_seconds": response["elapsed_seconds"],
        "response_bytes": len(raw),
        "raw_sha256": parsed["raw_sha256"] if parsed else None,
        "semantic_sha256": parsed["semantic_sha256"] if parsed else None,
        "record_count": parsed["record_count"] if parsed else 0,
        "non_null_count": parsed["non_null_count"] if parsed else 0,
        "response_country_value_or_content_persisted": False,
    }
    return receipt, parsed, records


def run_experiment() -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    receipts: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    wave_walls: list[float] = []
    for wave in range(1, WAVES + 1):
        wave_started = time.monotonic()
        jobs = [
            (wave, target, representation)
            for target in runtime.TARGETS
            for representation in runtime.REPRESENTATIONS
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
            outputs = list(executor.map(lambda args: _request_one(*args), jobs))
        wave_walls.append(round(time.monotonic() - wave_started, 6))
        by_target: dict[str, dict[str, Mapping[str, Any]]] = {}
        record_vectors: dict[str, dict[str, Mapping[str, Any]]] = {}
        for receipt, _parsed, records in outputs:
            receipts.append(receipt)
            if receipt["success"]:
                by_target.setdefault(receipt["target_key"], {})[receipt["representation"]] = receipt
                if records is not None:
                    record_vectors.setdefault(receipt["target_key"], {})[receipt["representation"]] = records
        for target in runtime.TARGETS:
            key = runtime.target_key(target)
            vector = record_vectors.get(key, {})
            if set(vector) == set(runtime.REPRESENTATIONS):
                comparison = runtime.compare_record_vectors(vector["bulk_zip"], vector["aggregate_json"])
                comparisons.append({"wave": wave, "target_key": key, **comparison})
    wall = round(time.monotonic() - started, 6)
    successes = sum(item["success"] for item in receipts)
    per_target_wave = []
    for wave in range(1, WAVES + 1):
        for target in runtime.TARGETS:
            rows = [item for item in receipts if item["wave"] == wave and item["target_key"] == runtime.target_key(target)]
            per_target_wave.append(
                {
                    "wave": wave,
                    "target_key": runtime.target_key(target),
                    "successful_representations": sum(item["success"] for item in rows),
                    "primary_success": any(
                        item["representation"] == PRIMARY_REPRESENTATION
                        and item["success"]
                        for item in rows
                    ),
                    "comparator_success": any(
                        item["representation"] == COMPARATOR_REPRESENTATION
                        and item["success"]
                        for item in rows
                    ),
                }
            )
    primary_semantics: dict[str, set[str]] = {}
    for item in receipts:
        if item["representation"] == PRIMARY_REPRESENTATION and item["success"]:
            primary_semantics.setdefault(item["target_key"], set()).add(
                item["semantic_sha256"]
            )
    checks = {
        "primary_all_requests_http_200_and_schema_valid": all(
            item["primary_success"] for item in per_target_wave
        ),
        "primary_semantic_stable_across_waves": all(
            len(primary_semantics.get(runtime.target_key(target), set())) == 1
            and sum(
                item["representation"] == PRIMARY_REPRESENTATION
                and item["success"]
                and item["target_key"] == runtime.target_key(target)
                for item in receipts
            )
            == WAVES
            for target in runtime.TARGETS
        ),
        "dual_representation_semantic_agreement_when_both_succeed": all(item["symmetric_difference_count"] == 0 and item["common_value_mismatch_count"] == 0 for item in comparisons),
        "all_wave_walls_within_ceiling": all(value <= WAVE_WALL_CEILING_SECONDS for value in wave_walls),
        "experiment_wall_within_ceiling": wall <= EXPERIMENT_WALL_CEILING_SECONDS,
        "no_response_content_persisted": all(item["response_country_value_or_content_persisted"] is False for item in receipts),
        "bulk_comparator_all_requests_http_200_and_schema_valid": all(
            item["comparator_success"] for item in per_target_wave
        ),
    }
    result = {
        "artifact_version": 1,
        "role": "v24721_worldbank_transport_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "waves": WAVES,
        "requests": TOTAL_REQUESTS,
        "successes": successes,
        "failures": TOTAL_REQUESTS - successes,
        "failure_type_counts": dict(sorted(Counter(str(item["failure_type"]) for item in receipts if not item["success"]).items())),
        "wave_wall_seconds": wave_walls,
        "experiment_wall_seconds": wall,
        "receipts": receipts,
        "dual_representation_comparisons": comparisons,
        "per_target_wave_reachability": per_target_wave,
        "checks": checks,
        "passed": all(checks[name] for name in REQUIRED_CHECKS),
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "response_country_value_or_content_persisted": False,
        },
    }
    result["result_payload_sha256"] = payload_sha256(result)
    decision = {
        "artifact_version": 1,
        "role": "v24721_worldbank_transport_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "result_payload_sha256": result["result_payload_sha256"],
        "status": "transport_go" if result["passed"] else "transport_no_go",
        "authorization": {
            "generic_reachability_candidate_design": bool(result["passed"]),
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "additional_transport_retry_or_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    decision["decision_payload_sha256"] = payload_sha256(decision)
    return result, decision


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    receipts = copied.get("receipts")
    comparisons = copied.get("dual_representation_comparisons")
    reachability = copied.get("per_target_wave_reachability")
    checks = copied.get("checks")
    expected_pairs = {
        (wave, runtime.target_key(target), representation)
        for wave in range(1, WAVES + 1)
        for target in runtime.TARGETS
        for representation in runtime.REPRESENTATIONS
    }
    receipt_keys = frozenset(
        {
            "wave",
            "target_key",
            "indicator",
            "year",
            "representation",
            "url_sha256",
            "attempts",
            "success",
            "failure_type",
            "http_status",
            "elapsed_seconds",
            "response_bytes",
            "raw_sha256",
            "semantic_sha256",
            "record_count",
            "non_null_count",
            "response_country_value_or_content_persisted",
        }
    )
    comparison_keys = frozenset(
        {
            "wave",
            "target_key",
            "left_record_count",
            "right_record_count",
            "common_record_count",
            "symmetric_difference_count",
            "common_value_mismatch_count",
            "common_semantic_sha256",
            "content_persisted",
        }
    )
    reachability_keys = frozenset(
        {
            "wave",
            "target_key",
            "successful_representations",
            "primary_success",
            "comparator_success",
        }
    )
    success_pairs = {
        (item["wave"], item["target_key"], item["representation"])
        for item in receipts or []
        if isinstance(item, Mapping) and item.get("success") is True
    }
    expected_comparison_pairs = {
        (wave, runtime.target_key(target))
        for wave in range(1, WAVES + 1)
        for target in runtime.TARGETS
        if all(
            (wave, runtime.target_key(target), representation) in success_pairs
            for representation in runtime.REPRESENTATIONS
        )
    }
    expected_reachability = [
        {
            "wave": wave,
            "target_key": runtime.target_key(target),
            "successful_representations": sum(
                (wave, runtime.target_key(target), representation) in success_pairs
                for representation in runtime.REPRESENTATIONS
            ),
            "primary_success": (
                wave,
                runtime.target_key(target),
                PRIMARY_REPRESENTATION,
            )
            in success_pairs,
            "comparator_success": (
                wave,
                runtime.target_key(target),
                COMPARATOR_REPRESENTATION,
            )
            in success_pairs,
        }
        for wave in range(1, WAVES + 1)
        for target in runtime.TARGETS
    ]
    wave_walls = copied.get("wave_wall_seconds")
    primary_semantics: dict[str, set[str]] = {}
    for item in receipts or []:
        if (
            isinstance(item, Mapping)
            and item.get("representation") == PRIMARY_REPRESENTATION
            and item.get("success") is True
            and isinstance(item.get("semantic_sha256"), str)
        ):
            primary_semantics.setdefault(str(item["target_key"]), set()).add(
                str(item["semantic_sha256"])
            )
    recomputed_checks = {
        "primary_all_requests_http_200_and_schema_valid": all(
            item["primary_success"]
            for item in expected_reachability
        ),
        "primary_semantic_stable_across_waves": all(
            len(primary_semantics.get(runtime.target_key(target), set())) == 1
            and sum(
                (wave, runtime.target_key(target), PRIMARY_REPRESENTATION)
                in success_pairs
                for wave in range(1, WAVES + 1)
            )
            == WAVES
            for target in runtime.TARGETS
        ),
        "dual_representation_semantic_agreement_when_both_succeed": bool(
            isinstance(comparisons, list)
            and {
                (item.get("wave"), item.get("target_key"))
                for item in comparisons
                if isinstance(item, Mapping)
            }
            == expected_comparison_pairs
            and all(
                isinstance(item, Mapping)
                and item.get("symmetric_difference_count") == 0
                and item.get("common_value_mismatch_count") == 0
                for item in comparisons
            )
        ),
        "all_wave_walls_within_ceiling": bool(
            isinstance(wave_walls, list)
            and len(wave_walls) == WAVES
            and all(
                isinstance(number, (int, float))
                and not isinstance(number, bool)
                and math.isfinite(float(number))
                and 0 <= float(number) <= WAVE_WALL_CEILING_SECONDS
                for number in wave_walls
            )
        ),
        "experiment_wall_within_ceiling": bool(
            isinstance(copied.get("experiment_wall_seconds"), (int, float))
            and not isinstance(copied.get("experiment_wall_seconds"), bool)
            and math.isfinite(float(copied["experiment_wall_seconds"]))
            and 0
            <= float(copied["experiment_wall_seconds"])
            <= EXPERIMENT_WALL_CEILING_SECONDS
        ),
        "no_response_content_persisted": bool(
            isinstance(receipts, list)
            and all(
                isinstance(item, Mapping)
                and item.get("response_country_value_or_content_persisted")
                is False
                for item in receipts
            )
            and isinstance(comparisons, list)
            and all(
                isinstance(item, Mapping)
                and item.get("content_persisted") is False
                for item in comparisons
            )
        ),
        "bulk_comparator_all_requests_http_200_and_schema_valid": all(
            item["comparator_success"] for item in expected_reachability
        ),
    }
    if (
        copied.get("role") != "v24721_worldbank_transport_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("waves") != WAVES
        or copied.get("requests") != TOTAL_REQUESTS
        or not isinstance(receipts, list)
        or len(receipts) != TOTAL_REQUESTS
        or {
            (item.get("wave"), item.get("target_key"), item.get("representation"))
            for item in receipts
            if isinstance(item, Mapping)
        }
        != expected_pairs
        or any(
            not isinstance(item, Mapping)
            or set(item) != receipt_keys
            or item.get("attempts") != 1
            or item.get("response_country_value_or_content_persisted") is not False
            or item.get("indicator")
            != runtime.resolve_target(item.get("indicator"), item.get("year")).indicator
            or item.get("url_sha256")
            != hashlib.sha256(
                runtime.endpoint_url(
                    runtime.resolve_target(item.get("indicator"), item.get("year")),
                    str(item.get("representation")),
                ).encode()
            ).hexdigest()
            or not isinstance(item.get("success"), bool)
            or not isinstance(item.get("elapsed_seconds"), (int, float))
            or isinstance(item.get("elapsed_seconds"), bool)
            or not math.isfinite(float(item["elapsed_seconds"]))
            or not 0 <= float(item["elapsed_seconds"]) <= HARD_WALL_SECONDS + 2.0
            or isinstance(item.get("response_bytes"), bool)
            or not isinstance(item.get("response_bytes"), int)
            or not 0 <= item["response_bytes"] <= runtime.MAX_RESPONSE_BYTES
            or item.get("success")
            is not (
                item.get("failure_type") is None
                and item.get("http_status") == 200
                and isinstance(item.get("raw_sha256"), str)
                and isinstance(item.get("semantic_sha256"), str)
                and item.get("record_count", 0) >= runtime.MINIMUM_RECORD_COUNT
                and item.get("non_null_count", 0) >= 1
            )
            for item in receipts
        )
        or copied.get("successes") != sum(item["success"] for item in receipts)
        or copied.get("failures") != TOTAL_REQUESTS - copied.get("successes", -1)
        or copied.get("failure_type_counts")
        != dict(
            sorted(
                Counter(
                    str(item["failure_type"])
                    for item in receipts
                    if not item["success"]
                ).items()
            )
        )
        or not isinstance(comparisons, list)
        or any(
            not isinstance(item, Mapping)
            or set(item) != comparison_keys
            or isinstance(item.get("wave"), bool)
            or item.get("wave") not in range(1, WAVES + 1)
            or not isinstance(item.get("target_key"), str)
            or any(
                isinstance(item.get(name), bool)
                or not isinstance(item.get(name), int)
                or item[name] < 0
                for name in (
                    "left_record_count",
                    "right_record_count",
                    "common_record_count",
                    "symmetric_difference_count",
                    "common_value_mismatch_count",
                )
            )
            or item.get("common_record_count")
            > min(item.get("left_record_count", -1), item.get("right_record_count", -1))
            or not isinstance(item.get("common_semantic_sha256"), str)
            or len(item["common_semantic_sha256"]) != 64
            or item.get("content_persisted") is not False
            for item in comparisons
        )
        or not isinstance(reachability, list)
        or len(reachability) != WAVES * len(runtime.TARGETS)
        or any(
            not isinstance(item, Mapping)
            or set(item) != reachability_keys
            for item in reachability
        )
        or reachability != expected_reachability
        or not isinstance(checks, Mapping)
        or set(checks)
        != set(REQUIRED_CHECKS) | {
            "bulk_comparator_all_requests_http_200_and_schema_valid"
        }
        or dict(checks) != recomputed_checks
        or copied.get("passed")
        is not all(recomputed_checks[name] for name in REQUIRED_CHECKS)
        or copied.get("source_policy")
        != {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "response_country_value_or_content_persisted": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.21 result drifted")
    return copied


def validate_decision(
    value: Mapping[str, Any], *, result: Mapping[str, Any]
) -> dict[str, Any]:
    copied = dict(value)
    status = "transport_go" if result.get("passed") is True else "transport_no_go"
    if (
        copied.get("role") != "v24721_worldbank_transport_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_payload_sha256") != result.get("result_payload_sha256")
        or copied.get("status") != status
        or copied.get("authorization")
        != {
            "generic_reachability_candidate_design": status == "transport_go",
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "additional_transport_retry_or_rerun": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.47.21 decision drifted")
    return copied


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    result_raw = _read(root, RESULT)
    decision_raw = _read(root, DECISION)
    findings = []
    try:
        result = validate_result(result_raw)
    except (RuntimeError, TypeError, ValueError):
        result = result_raw
        findings.append("result_invalid")
    try:
        decision = validate_decision(decision_raw, result=result)
    except (RuntimeError, TypeError, ValueError):
        decision = decision_raw
        findings.append("decision_invalid")
    if not _lease_inactive(root):
        findings.append("shared_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24721_worldbank_transport_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision.get("status"),
        "protected_watchers": _watcher_snapshot(),
        "shared_api_lease_inactive": _lease_inactive(root),
        "network_model_search_benchmark_forward_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {"additional_transport_retry_or_rerun": False, "benchmark_dev64_or_exact220": False, "evaluator": False, "leaderboard_or_sota": False},
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def command_protocol() -> None:
    _require_clean_pushed_head()
    _publish(ROOT / PROTOCOL, build_protocol(ROOT))


def command_preaudit() -> None:
    _require_clean_pushed_head()
    _publish(ROOT / PREAUDIT, build_preaudit(ROOT))


def command_activate() -> None:
    _require_clean_pushed_head()
    _publish(ROOT / ACTIVATION, build_activation(ROOT))


def command_start() -> None:
    _require_clean_pushed_head()
    _publish(ROOT / EXECUTION_START, build_execution_start(ROOT))


def command_run() -> None:
    _require_clean_pushed_head()
    validate_execution_start(_read(ROOT, EXECUTION_START))
    if (ROOT / RESULT).exists() or (ROOT / DECISION).exists() or not _lease_inactive(ROOT):
        raise RuntimeError("V2.47.21 run surface is unsafe")
    with acquire_deepwide_api_lease(ROOT, owner=LEASE_OWNER, purpose=LEASE_PURPOSE):
        result, decision = run_experiment()
        validate_result(result)
        validate_decision(decision, result=result)
        _publish(ROOT / RESULT, result)
        _publish(ROOT / DECISION, decision)


def command_postaudit() -> None:
    _require_clean_pushed_head()
    _publish(ROOT / POSTAUDIT, build_postaudit(ROOT))


COMMANDS = {
    "protocol": command_protocol,
    "preaudit": command_preaudit,
    "activate": command_activate,
    "start": command_start,
    "run": command_run,
    "postaudit": command_postaudit,
}


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit("usage: v24721_worldbank_transport_gate.py {protocol|preaudit|activate|start|run|postaudit}")
    COMMANDS[sys.argv[1]]()
