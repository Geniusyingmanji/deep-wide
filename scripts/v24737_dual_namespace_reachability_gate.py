#!/usr/bin/env python3
"""Sealed one-shot dual-namespace deterministic reachability gate."""

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

from deepwide_agent import v24735_dual_namespace_reachability as runtime  # noqa: E402
from deepwide_agent import v24733_dual_namespace_contract as contract  # noqa: E402
from scripts import v24736_public_get_helper as helper  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24737_dual_namespace_reachability_v1"
PROTOCOL = Path(f"results/v24737_dual_namespace_reachability_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24737_dual_namespace_reachability_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24737_dual_namespace_reachability_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24737_dual_namespace_reachability_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24737_dual_namespace_reachability_forward_result_v1_{DATE}.json")
DECISION = Path(f"results/v24737_dual_namespace_reachability_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24737_dual_namespace_reachability_postresult_audit_v1_{DATE}.json")
SURFACE_AUDIT = Path(f"results/v24734_dual_namespace_surface_build_audit_v1_{DATE}.json")
TRANSPORT_DECISION = Path(f"results/v24726_fresh_bulk_transport_decision_v1_{DATE}.json")
TRANSPORT_AUDIT = Path(f"results/v24726_fresh_bulk_transport_postresult_audit_v1_{DATE}.json")
RUNTIME_SOURCE = Path("src/deepwide_agent/v24735_dual_namespace_reachability.py")
CONTRACT_SOURCE = Path("src/deepwide_agent/v24733_dual_namespace_contract.py")
HELPER_SOURCE = Path("scripts/v24736_public_get_helper.py")
SCRIPT = Path("scripts/v24737_dual_namespace_reachability_gate.py")
RUNTIME_TEST = Path("tests/test_v24735_dual_namespace_reachability.py")
HELPER_TEST = Path("tests/test_v24736_public_get_helper.py")
SCRIPT_TEST = Path("tests/test_v24737_dual_namespace_reachability_gate.py")
LEASE_SOURCE = Path("scripts/deepwide_api_lease.py")
SOURCES = (
    RUNTIME_SOURCE,
    CONTRACT_SOURCE,
    HELPER_SOURCE,
    SCRIPT,
    RUNTIME_TEST,
    HELPER_TEST,
    SCRIPT_TEST,
    LEASE_SOURCE,
    SURFACE_AUDIT,
    TRANSPORT_DECISION,
    TRANSPORT_AUDIT,
)
OUTPUT_ROOT = Path(f"outputs/v24737_dual_namespace_reachability_v1_{DATE}")
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
ATTEMPT_CLAIM = OUTPUT_ROOT / "attempt_claim.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_dual_namespace_deterministic_reachability"
RUNNER_MARKER = "scripts/v24737_dual_namespace_reachability_gate.py run"
TASK_COUNT = contract.TASK_COUNT
TASKS_PER_CLUSTER = contract.TASKS_PER_CLUSTER
REQUEST_COUNT = len(helper.ALLOWED_URLS)
ROR_REQUEST_COUNT = len(helper.ROR_URLS)
WORLD_BANK_REQUEST_COUNT = len(helper.WORLD_BANK_URLS)
WORKERS = 25
HARD_WALL_SECONDS = 20.0
SOCKET_TIMEOUT_SECONDS = 15.0
EXPERIMENT_WALL_CEILING_SECONDS = 55.0
EXPECTED_TESTS = 16
TEST_SUITES = (
    (RUNTIME_TEST, 7),
    (HELPER_TEST, 3),
    (SCRIPT_TEST, 6),
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
REQUIRED_CHECKS = (
    "fixed_request_attempt_vector_complete",
    "all_24_tasks_terminal",
    "ror_prediction_changing_task_reached",
    "worldbank_prediction_changing_task_reached",
    "ror_identity_and_target_value_binding_reached",
    "worldbank_identity_and_target_value_binding_reached",
    "experiment_wall_within_ceiling",
    "no_response_content_in_public_aggregate",
    "prediction_freeze_precedes_gold_or_evaluator",
)
REQUEST_RECEIPT_KEYS = frozenset(
    {
        "request_index",
        "namespace",
        "url_sha256",
        "attempts",
        "transport_success",
        "failure_type",
        "http_status",
        "elapsed_seconds",
        "response_bytes",
        "raw_sha256",
        "response_content_persisted",
    }
)
TASK_RECEIPT_KEYS = frozenset(
    {
        "position",
        "namespace",
        "runtime_valid",
        "prediction_changed",
        "changed_cell_count",
        "primary_identity_bound_target_count",
        "target_value_bound_cell_count",
        "response_or_prediction_content_persisted_in_public_aggregate",
    }
)
REQUEST_FAILURE_TYPES = frozenset(
    {
        "hard_total_wall_timeout",
        "helper_invalid",
        "helper_launch_error",
        "invalid_input",
        "response",
        "response_too_large",
        "transport_error",
    }
)
SOURCE_POLICY = {
    "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    "model_hosted_search_or_benchmark_forward_called": False,
    "credential_read_hashed_persisted_or_emitted": False,
    "response_body_identity_or_value_persisted_in_public_aggregate": False,
    "entropy_or_positive_task_credit_assigned": False,
}
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


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.47.37 expected repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.37 expected object")
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
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _require_clean_pushed_head() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.47.37 requires clean pushed HEAD")


def _watchers() -> list[dict[str, Any]]:
    output = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
        ticks = int(raw[raw.rfind(")") + 2 :].split()[19])
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if ticks != expected_ticks or marker not in command:
            raise RuntimeError("V2.47.37 protected watcher drifted")
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
        ["ps", "-eo", "pid=,comm=,args="], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, timeout=20, check=False,
    )
    return any(
        RUNNER_MARKER in line
        and len(line.split()) >= 2
        and "python" in line.split()[1].casefold()
        for line in completed.stdout.splitlines()
    )


def _manifest(root: Path) -> dict[str, str]:
    output = {}
    for relative in SOURCES:
        path = _ordinary(root, relative)
        if root.resolve() == ROOT.resolve() and not _tracked(relative):
            raise RuntimeError(f"V2.47.37 untracked source: {relative}")
        raw = path.read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.37 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def ast_findings(root: Path = ROOT) -> tuple[list[str], list[str]]:
    accesses = []
    imports = []
    for relative in (RUNTIME_SOURCE, CONTRACT_SOURCE, HELPER_SOURCE, SCRIPT):
        tree = ast.parse(_ordinary(root, relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key = None
            if (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"} and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value if isinstance(node.slice.value, str) else None
            if key is not None and key.casefold() in PRIVILEGED:
                accesses.append(f"{relative}:{node.lineno}:{key}")
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(marker in name.casefold() for marker in ("official_eval", "evaluator_mapping", "finalize_v24", "v24733_dual_namespace_evaluator")):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _parents(root: Path) -> None:
    surface = _read(root, SURFACE_AUDIT)
    transport = _read(root, TRANSPORT_DECISION)
    audit = _read(root, TRANSPORT_AUDIT)
    if (
        surface.get("role") != "v24734_dual_namespace_surface_build_audit"
        or surface.get("audit_valid") is not True
        or surface.get("findings") != []
        or surface.get("authorization")
        != {
            "one_successor_surface_publication": True,
            "reachability_protocol_design": True,
            "forward_launch": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(surface, "audit_payload_sha256")
        or transport.get("role") != "v24726_fresh_bulk_transport_decision"
        or transport.get("status") != "transport_go"
        or transport.get("authorization")
        != {
            "generic_reachability_candidate_design": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "additional_transport_retry_or_rerun": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(transport, "decision_payload_sha256")
        or audit.get("role") != "v24726_fresh_bulk_transport_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 parent chain drifted")


def _tasks() -> list[dict[str, str]]:
    tasks = contract.task_vector()
    if (
        len(tasks) != TASK_COUNT
        or any(set(task) != {"opaque_id", "question"} for task in tasks)
        or [contract.visible_namespace(task["question"]) for task in tasks]
        != ["ror"] * TASKS_PER_CLUSTER + ["worldbank"] * TASKS_PER_CLUSTER
    ):
        raise RuntimeError("V2.47.37 visible task vector drifted")
    return tasks


def _request_vector() -> list[str]:
    output = []
    seen = set()
    for task in _tasks():
        for url in runtime.request_urls(task):
            if url not in seen:
                seen.add(url); output.append(url)
    if set(output) != set(helper.ALLOWED_URLS) or len(output) != REQUEST_COUNT:
        raise RuntimeError("V2.47.37 request vector drifted")
    return output


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    _parents(root)
    manifest = _manifest(root)
    tasks = _tasks()
    requests = _request_vector()
    value = {
        "artifact_version": 1,
        "role": "v24737_dual_namespace_reachability_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "benchmark_external_dual_namespace_deterministic_reachability_only",
        "parents": {
            "surface_audit_sha256": sha256(root / SURFACE_AUDIT),
            "transport_decision_sha256": sha256(root / TRANSPORT_DECISION),
            "transport_audit_sha256": sha256(root / TRANSPORT_AUDIT),
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "task_count": TASK_COUNT,
            "tasks_per_cluster": TASKS_PER_CLUSTER,
            "cluster_order": ["ror", "worldbank"],
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        },
        "execution": {
            "unique_request_count": REQUEST_COUNT,
            "ror_request_count": ROR_REQUEST_COUNT,
            "worldbank_shared_bulk_request_count": WORLD_BANK_REQUEST_COUNT,
            "request_url_vector_sha256": payload_sha256(requests),
            "workers": WORKERS,
            "attempts_per_url": 1,
            "hard_total_wall_seconds": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "cache_resume_retry_or_selective_rerun": False,
            "worldbank_bulk_responses_shared_across_12_tasks": True,
        },
        "gates": {
            "required_checks": list(REQUIRED_CHECKS),
            "minimum_prediction_changing_tasks_per_cluster": 1,
            "minimum_identity_bound_targets_per_cluster": 1,
            "minimum_target_value_bound_cells_per_cluster": 1,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "protected_watchers": _watchers(),
        "evaluation_separation": {
            "gold_provenance_or_evaluator_in_forward_manifest": False,
            "prediction_freeze_before_gold_provenance_or_evaluator_open": True,
            "mechanism_no_go_stops_without_evaluator": True,
            "quality_not_measured_by_forward": True,
        },
        "source_policy": dict(SOURCE_POLICY),
        "authorization": {
            "preactivation_audit_generation": True,
            "forward_launch": False,
            "evaluator": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(root: Path = ROOT, *, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = copied.get("dependency_manifest")
    tasks = _tasks(); requests = _request_vector()
    if (
        copied.get("role") != "v24737_dual_namespace_reachability_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope") != "benchmark_external_dual_namespace_deterministic_reachability_only"
        or copied.get("parents") != {"surface_audit_sha256": sha256(root / SURFACE_AUDIT), "transport_decision_sha256": sha256(root / TRANSPORT_DECISION), "transport_audit_sha256": sha256(root / TRANSPORT_AUDIT)}
        or copied.get("task_contract") != {"runtime_input_keys": ["opaque_id", "question"], "task_count": TASK_COUNT, "tasks_per_cluster": TASKS_PER_CLUSTER, "cluster_order": ["ror", "worldbank"], "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]), "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks])}
        or copied.get("execution") != {"unique_request_count": REQUEST_COUNT, "ror_request_count": ROR_REQUEST_COUNT, "worldbank_shared_bulk_request_count": WORLD_BANK_REQUEST_COUNT, "request_url_vector_sha256": payload_sha256(requests), "workers": WORKERS, "attempts_per_url": 1, "hard_total_wall_seconds": HARD_WALL_SECONDS, "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS, "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS, "cache_resume_retry_or_selective_rerun": False, "worldbank_bulk_responses_shared_across_12_tasks": True}
        or copied.get("gates") != {"required_checks": list(REQUIRED_CHECKS), "minimum_prediction_changing_tasks_per_cluster": 1, "minimum_identity_bound_targets_per_cluster": 1, "minimum_target_value_bound_cells_per_cluster": 1}
        or not isinstance(manifest, Mapping) or dict(manifest) != _manifest(root)
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("evaluation_separation") != {"gold_provenance_or_evaluator_in_forward_manifest": False, "prediction_freeze_before_gold_provenance_or_evaluator_open": True, "mechanism_no_go_stops_without_evaluator": True, "quality_not_measured_by_forward": True}
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization") != {"preactivation_audit_generation": True, "forward_launch": False, "evaluator": False, "benchmark_dev64_or_exact220": False, "entropy_or_credit_experiment": False, "leaderboard_or_sota": False}
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 protocol drifted")
    return copied


def _run_tests() -> tuple[bool, int, str]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())), "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
    }
    outputs = []; total = 0; passed = True
    for suite, expected in TEST_SUITES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", suite.name],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=120, check=False,
        )
        outputs.append(completed.stdout)
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        total += observed; passed = passed and completed.returncode == 0 and observed == expected
    output = "\n".join(outputs)
    return passed and total == EXPECTED_TESTS, total, output


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    validate_protocol(root)
    tests_passed, observed, output = _run_tests()
    accesses, imports = ast_findings(root)
    findings = []
    if not tests_passed: findings.append("directed_tests_failed")
    if accesses or imports: findings.append("label_blind_ast_failed")
    if not _lease_inactive(root): findings.append("shared_lease_active")
    if _runner_active(): findings.append("runner_active")
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"): findings.append("repository_not_clean_pushed_head")
    if any((root / path).exists() or (root / path).is_symlink() for path in (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT, OUTPUT_ROOT)): findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24737_dual_namespace_reachability_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "tests": {"passed": tests_passed, "observed": observed, "expected": EXPECTED_TESTS, "output_sha256": hashlib.sha256(output.encode()).hexdigest()},
        "label_blind_audit": {"accesses": accesses, "evaluator_imports": imports, "passed": not accesses and not imports},
        "runtime_state": {"protected_watchers": _watchers(), "shared_api_lease_inactive": _lease_inactive(root), "runner_active": _runner_active()},
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {"activation_publication": not findings, "forward_launch": False, "evaluator": False, "benchmark_dev64_or_exact220": False, "leaderboard_or_sota": False},
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_preaudit(value)
    return value


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value); tests = copied.get("tests", {}); state = copied.get("runtime_state", {}); findings = copied.get("findings"); valid = copied.get("audit_valid")
    if (
        copied.get("role") != "v24737_dual_namespace_reachability_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or tests.get("passed") is not True or tests.get("observed") != EXPECTED_TESTS or tests.get("expected") != EXPECTED_TESTS
        or copied.get("label_blind_audit") != {"accesses": [], "evaluator_imports": [], "passed": True}
        or state.get("protected_watchers") != _watchers() or state.get("shared_api_lease_inactive") is not True or state.get("runner_active") is not False
        or not isinstance(findings, list) or valid is not (findings == [])
        or copied.get("authorization") != {"activation_publication": bool(valid), "forward_launch": False, "evaluator": False, "benchmark_dev64_or_exact220": False, "leaderboard_or_sota": False}
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 preaudit drifted")
    return copied


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    validate_protocol(root); preaudit = validate_preaudit(_read(root, PREAUDIT))
    if preaudit.get("audit_valid") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.37 activation is unsafe")
    value = {
        "artifact_version": 1, "role": "v24737_dual_namespace_reachability_activation", "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL), "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "protected_watchers": _watchers(), "network_model_search_evaluator_or_api_called": False,
        "launch_authorized": True,
        "authorization": {"one_forward_launch": True, "evaluator": False, "benchmark_dev64_or_exact220": False, "leaderboard_or_sota": False},
    }
    value["activation_payload_sha256"] = payload_sha256(value); validate_activation(value); return value


def validate_activation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24737_dual_namespace_reachability_activation" or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL) or copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("protected_watchers") != _watchers() or copied.get("network_model_search_evaluator_or_api_called") is not False
        or copied.get("launch_authorized") is not True
        or copied.get("authorization") != {"one_forward_launch": True, "evaluator": False, "benchmark_dev64_or_exact220": False, "leaderboard_or_sota": False}
        or not _sealed(copied, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 activation drifted")
    return copied


def build_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    activation = validate_activation(_read(root, ACTIVATION))
    if activation.get("launch_authorized") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.37 execution start is unsafe")
    value = {
        "artifact_version": 1, "role": "v24737_dual_namespace_reachability_execution_start", "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL), "activation_sha256": sha256(root / ACTIVATION),
        "protected_watchers": _watchers(), "single_owner_no_resume_retry_or_selective_rerun": True,
        "authorization": {"execute_once": True, "evaluator": False, "benchmark_dev64_or_exact220": False},
    }
    value["execution_start_payload_sha256"] = payload_sha256(value); validate_start(value); return value


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24737_dual_namespace_reachability_execution_start" or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL) or copied.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or copied.get("protected_watchers") != _watchers() or copied.get("single_owner_no_resume_retry_or_selective_rerun") is not True
        or copied.get("authorization") != {"execute_once": True, "evaluator": False, "benchmark_dev64_or_exact220": False}
        or not _sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 execution start drifted")
    return copied


def build_attempt_claim(*, now: int | None = None) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24737_dual_namespace_reachability_attempt_claim",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "unique_request_count": REQUEST_COUNT,
        "attempts_per_url": 1,
        "resume_retry_or_selective_rerun": False,
        "network_model_search_evaluator_or_api_called_before_claim": False,
    }
    value["claim_payload_sha256"] = payload_sha256(value)
    return validate_attempt_claim(value)


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "execution_start_sha256",
            "unique_request_count",
            "attempts_per_url",
            "resume_retry_or_selective_rerun",
            "network_model_search_evaluator_or_api_called_before_claim",
            "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v24737_dual_namespace_reachability_attempt_claim"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("unique_request_count") != REQUEST_COUNT
        or copied.get("attempts_per_url") != 1
        or copied.get("resume_retry_or_selective_rerun") is not False
        or copied.get("network_model_search_evaluator_or_api_called_before_claim")
        is not False
        or not _sealed(copied, "claim_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 attempt claim drifted")
    return copied


def _environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())), "USER": os.environ.get("USER", "azureuser"), "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "DEEPWIDE_EXPECTED_PARENT_PID": str(os.getpid()),
    }


def _terminate(process: Any) -> None:
    try: os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError: return
    try: process.wait(timeout=0.5); return
    except subprocess.TimeoutExpired: pass
    try: os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError: return
    process.wait(timeout=0.5)


def hard_get(url: str, *, timeout_seconds: float = HARD_WALL_SECONDS, popen: Any = subprocess.Popen) -> dict[str, Any]:
    if url not in helper.ALLOWED_URLS or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("V2.47.37 hard GET input drifted")
    started = time.monotonic()
    try:
        process = popen(
            [sys.executable, "-I", "-B", str(ROOT / HELPER_SOURCE)], cwd=ROOT, env=_environment(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            start_new_session=True, text=True,
        )
    except OSError:
        return {"kind": "helper_launch_error", "status_code": None, "final_url": "", "body": b"", "elapsed_seconds": round(time.monotonic() - started, 6)}
    request = json.dumps({"url": url, "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS}, separators=(",", ":"))
    try: stdout, _ = process.communicate(request, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate(process)
        return {"kind": "hard_total_wall_timeout", "status_code": None, "final_url": "", "body": b"", "elapsed_seconds": round(time.monotonic() - started, 6)}
    try:
        value = json.loads(stdout)
        if process.returncode != 0 or not isinstance(value, Mapping) or set(value) != helper.OUTPUT_KEYS:
            raise ValueError("V2.47.37 helper output")
        body = base64.b64decode(value["body_base64"], validate=True) if value["body_base64"] else b""
        if len(body) > helper.MAX_RESPONSE_BYTES: raise ValueError("V2.47.37 helper body")
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"kind": "helper_invalid", "status_code": None, "final_url": "", "body": b"", "elapsed_seconds": round(time.monotonic() - started, 6)}
    return {"kind": str(value["kind"]), "status_code": value["status_code"], "final_url": str(value["final_url"]), "body": body, "elapsed_seconds": round(time.monotonic() - started, 6)}


def _request_one(index_url: tuple[int, str]) -> tuple[dict[str, Any], bytes]:
    index, url = index_url
    response = hard_get(url); body = response.pop("body")
    success = response["kind"] == "response" and response["status_code"] == 200 and response["final_url"] == url and bool(body)
    receipt = {
        "request_index": index, "namespace": "ror" if url in helper.ROR_URLS else "worldbank",
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(), "attempts": 1,
        "transport_success": success, "failure_type": None if success else response["kind"],
        "http_status": response["status_code"], "elapsed_seconds": response["elapsed_seconds"],
        "response_bytes": len(body), "raw_sha256": hashlib.sha256(body).hexdigest() if success else None,
        "response_content_persisted": False,
    }
    return receipt, body if success else b""


def aggregate(
    task_rows: Sequence[Mapping[str, Any]], request_receipts: Sequence[Mapping[str, Any]],
    *, experiment_wall_seconds: float, prediction_sha256: str, freeze_sha256: str, now: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    namespaces = ("ror", "worldbank")
    summaries = {}
    for namespace in namespaces:
        rows = [row for row in task_rows if row.get("namespace") == namespace]
        summaries[namespace] = {
            "tasks": len(rows), "runtime_valid_tasks": sum(row.get("runtime_valid") is True for row in rows),
            "prediction_changing_tasks": sum(row.get("prediction_changed") is True for row in rows),
            "changed_cells": sum(int(row.get("changed_cell_count", 0)) for row in rows),
            "identity_bound_targets": sum(int(row.get("primary_identity_bound_target_count", 0)) for row in rows),
            "target_value_bound_cells": sum(int(row.get("target_value_bound_cell_count", 0)) for row in rows),
        }
    checks = {
        "fixed_request_attempt_vector_complete": len(request_receipts) == REQUEST_COUNT and {item.get("request_index") for item in request_receipts} == set(range(1, REQUEST_COUNT + 1)) and all(item.get("attempts") == 1 for item in request_receipts),
        "all_24_tasks_terminal": len(task_rows) == TASK_COUNT and {item.get("position") for item in task_rows} == set(range(1, TASK_COUNT + 1)) and all(item.get("runtime_valid") is True for item in task_rows),
        "ror_prediction_changing_task_reached": summaries["ror"]["prediction_changing_tasks"] >= 1,
        "worldbank_prediction_changing_task_reached": summaries["worldbank"]["prediction_changing_tasks"] >= 1,
        "ror_identity_and_target_value_binding_reached": summaries["ror"]["identity_bound_targets"] >= 1 and summaries["ror"]["target_value_bound_cells"] >= 1,
        "worldbank_identity_and_target_value_binding_reached": summaries["worldbank"]["identity_bound_targets"] >= 1 and summaries["worldbank"]["target_value_bound_cells"] >= 1,
        "experiment_wall_within_ceiling": isinstance(experiment_wall_seconds, (int, float)) and not isinstance(experiment_wall_seconds, bool) and math.isfinite(float(experiment_wall_seconds)) and 0 <= float(experiment_wall_seconds) <= EXPERIMENT_WALL_CEILING_SECONDS,
        "no_response_content_in_public_aggregate": all(item.get("response_content_persisted") is False and "body" not in item and "url" not in item for item in request_receipts),
        "prediction_freeze_precedes_gold_or_evaluator": True,
    }
    passed = all(checks[name] for name in REQUIRED_CHECKS)
    result = {
        "artifact_version": 1, "role": "v24737_dual_namespace_reachability_forward_result", "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "selected_tasks": TASK_COUNT, "terminal_arm_predictions": TASK_COUNT * len(runtime.ARMS),
        "unique_requests": REQUEST_COUNT, "request_successes": sum(item.get("transport_success") is True for item in request_receipts),
        "request_failure_type_counts": dict(sorted(Counter(str(item.get("failure_type")) for item in request_receipts if item.get("transport_success") is not True).items())),
        "experiment_wall_seconds": float(experiment_wall_seconds),
        "predictions_sha256": prediction_sha256, "prediction_freeze_sha256": freeze_sha256,
        "cluster_summaries": summaries, "request_receipts": [dict(item) for item in request_receipts],
        "task_receipts": [dict(item) for item in task_rows], "checks": checks, "passed": passed,
        "all_predictions_frozen_before_gold_provenance_or_evaluator_open": True,
        "gold_provenance_path_opened_or_hashed": False, "evaluator_called": False,
        "source_policy": dict(SOURCE_POLICY),
    }
    result["result_payload_sha256"] = payload_sha256(result)
    decision = {
        "artifact_version": 1, "role": "v24737_dual_namespace_reachability_decision", "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_payload_sha256": result["result_payload_sha256"],
        "status": "dual_namespace_reachability_go" if passed else "dual_namespace_reachability_no_go",
        "authorization": {"postfreeze_external_evaluator_protocol_design": passed, "evaluator_execution": False, "additional_forward_retry_or_rerun": False, "benchmark_dev64_or_exact220": False, "entropy_or_credit_experiment": False, "leaderboard_or_sota": False},
    }
    decision["decision_payload_sha256"] = payload_sha256(decision)
    return result, decision


def run_experiment() -> tuple[dict[str, Any], dict[str, Any]]:
    validate_attempt_claim(_read(ROOT, ATTEMPT_CLAIM))
    started = time.monotonic(); urls = _request_vector()
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        outputs = list(executor.map(_request_one, enumerate(urls, 1)))
    request_receipts = [item[0] for item in outputs]
    responses = {url: output[1] for url, output in zip(urls, outputs, strict=True)}
    prediction_rows = []; task_rows = []
    for position, task in enumerate(_tasks(), 1):
        namespace = contract.visible_namespace(task["question"]); subset = {url: responses[url] for url in runtime.request_urls(task)}
        valid = True
        try: value = runtime.run_task(task, subset)
        except (KeyError, TypeError, ValueError):
            valid = False; value = runtime.run_task(task, {url: b"" for url in runtime.request_urls(task)})
        predictions = value["predictions"]; receipt = value["receipt"]
        prediction_rows.append({"opaque_id": task["opaque_id"], "predictions": predictions, "prediction_sha256": value["prediction_sha256"], "runtime_result_valid": valid})
        task_rows.append({"position": position, "namespace": namespace, "runtime_valid": valid, "prediction_changed": receipt["prediction_changed"], "changed_cell_count": receipt["changed_cell_count"], "primary_identity_bound_target_count": receipt["primary_identity_bound_target_count"], "target_value_bound_cell_count": receipt["target_value_bound_cell_count"], "response_or_prediction_content_persisted_in_public_aggregate": False})
    if (ROOT / OUTPUT_ROOT).is_symlink() or not (ROOT / OUTPUT_ROOT).is_dir():
        raise RuntimeError("V2.47.37 attempt claim directory drifted")
    _publish_jsonl(ROOT / PREDICTIONS, prediction_rows)
    summary = {"artifact_version": 1, "role": "v24737_forward_run_summary", "attempt_claim_sha256": sha256(ROOT / ATTEMPT_CLAIM), "selected_tasks": TASK_COUNT, "terminal_prediction_rows": len(prediction_rows), "runtime_valid_tasks": sum(row["runtime_valid"] for row in task_rows), "experiment_wall_seconds": round(time.monotonic() - started, 6), "resume_retry_skip_or_selective_rerun": False, "gold_provenance_or_evaluator_opened": False}
    summary["summary_payload_sha256"] = payload_sha256(summary); _publish(ROOT / RUN_SUMMARY, summary)
    freeze = {"artifact_version": 1, "role": "v24737_prediction_freeze", "protocol_id": PROTOCOL_ID, "selected_tasks": TASK_COUNT, "terminal_arm_predictions": TASK_COUNT * len(runtime.ARMS), "predictions_sha256": sha256(ROOT / PREDICTIONS), "run_summary_sha256": sha256(ROOT / RUN_SUMMARY), "all_predictions_terminal_before_gold_provenance_or_evaluator_open": True, "gold_provenance_path_opened_or_hashed": False, "evaluator_called": False}
    freeze["freeze_payload_sha256"] = payload_sha256(freeze); _publish(ROOT / PREDICTION_FREEZE, freeze)
    return aggregate(task_rows, request_receipts, experiment_wall_seconds=summary["experiment_wall_seconds"], prediction_sha256=sha256(ROOT / PREDICTIONS), freeze_sha256=sha256(ROOT / PREDICTION_FREEZE))


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value); requests = copied.get("request_receipts"); tasks = copied.get("task_receipts"); checks = copied.get("checks"); summaries = copied.get("cluster_summaries")
    if not isinstance(requests, list) or not isinstance(tasks, list) or not isinstance(checks, Mapping) or not isinstance(summaries, Mapping):
        raise RuntimeError("V2.47.37 result vectors absent")
    expected_urls = _request_vector()
    request_valid = len(requests) == REQUEST_COUNT and all(
        isinstance(item, Mapping)
        and set(item) == REQUEST_RECEIPT_KEYS
        and item.get("request_index") == index
        and item.get("namespace") == ("ror" if url in helper.ROR_URLS else "worldbank")
        and item.get("url_sha256") == hashlib.sha256(url.encode()).hexdigest()
        and item.get("attempts") == 1
        and isinstance(item.get("transport_success"), bool)
        and (
            item.get("failure_type") is None
            if item.get("transport_success") is True
            else item.get("failure_type") in REQUEST_FAILURE_TYPES
        )
        and (
            item.get("http_status") is None
            or (
                isinstance(item.get("http_status"), int)
                and not isinstance(item.get("http_status"), bool)
                and 100 <= item.get("http_status") <= 599
            )
        )
        and isinstance(item.get("elapsed_seconds"), (int, float))
        and not isinstance(item.get("elapsed_seconds"), bool)
        and math.isfinite(float(item.get("elapsed_seconds")))
        and item.get("elapsed_seconds") >= 0
        and isinstance(item.get("response_bytes"), int)
        and not isinstance(item.get("response_bytes"), bool)
        and 0 <= item.get("response_bytes") <= helper.MAX_RESPONSE_BYTES
        and (
            isinstance(item.get("raw_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", item.get("raw_sha256")) is not None
            and item.get("http_status") == 200
            and item.get("response_bytes") > 0
            if item.get("transport_success") is True
            else item.get("raw_sha256") is None
        )
        and item.get("response_content_persisted") is False
        for index, (url, item) in enumerate(zip(expected_urls, requests, strict=True), 1)
    )
    task_valid = len(tasks) == TASK_COUNT and all(
        isinstance(item, Mapping)
        and set(item) == TASK_RECEIPT_KEYS
        and item.get("position") == index
        and item.get("namespace") == ("ror" if index <= TASKS_PER_CLUSTER else "worldbank")
        and isinstance(item.get("runtime_valid"), bool)
        and isinstance(item.get("prediction_changed"), bool)
        and all(
            isinstance(item.get(name), int)
            and not isinstance(item.get(name), bool)
            and item.get(name) >= 0
            for name in (
                "changed_cell_count",
                "primary_identity_bound_target_count",
                "target_value_bound_cell_count",
            )
        )
        and item.get("target_value_bound_cell_count")
        == item.get("primary_identity_bound_target_count") * 2
        and item.get("changed_cell_count") == item.get("target_value_bound_cell_count")
        and item.get("prediction_changed") is (item.get("changed_cell_count") > 0)
        and (
            item.get("runtime_valid") is True
            or item.get("changed_cell_count") == 0
        )
        and item.get("primary_identity_bound_target_count")
        <= (4 if index <= TASKS_PER_CLUSTER else 12)
        and item.get("response_or_prediction_content_persisted_in_public_aggregate")
        is False
        for index, item in enumerate(tasks, 1)
    )
    recomputed, _decision = aggregate(tasks, requests, experiment_wall_seconds=copied.get("experiment_wall_seconds"), prediction_sha256=str(copied.get("predictions_sha256")), freeze_sha256=str(copied.get("prediction_freeze_sha256")), now=int(copied.get("created_at_unix", 0)))
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "execution_start_sha256", "selected_tasks", "terminal_arm_predictions",
            "unique_requests", "request_successes", "request_failure_type_counts",
            "experiment_wall_seconds", "predictions_sha256", "prediction_freeze_sha256",
            "cluster_summaries", "request_receipts", "task_receipts", "checks", "passed",
            "all_predictions_frozen_before_gold_provenance_or_evaluator_open",
            "gold_provenance_path_opened_or_hashed", "evaluator_called", "source_policy",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24737_dual_namespace_reachability_forward_result" or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int) or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START) or copied.get("selected_tasks") != TASK_COUNT or copied.get("terminal_arm_predictions") != TASK_COUNT * len(runtime.ARMS)
        or copied.get("unique_requests") != REQUEST_COUNT or not request_valid or not task_valid
        or copied.get("request_successes") != sum(item.get("transport_success") is True for item in requests)
        or copied.get("request_failure_type_counts") != dict(sorted(Counter(str(item.get("failure_type")) for item in requests if item.get("transport_success") is not True).items()))
        or copied.get("predictions_sha256") != sha256(ROOT / PREDICTIONS) or copied.get("prediction_freeze_sha256") != sha256(ROOT / PREDICTION_FREEZE)
        or copied.get("cluster_summaries") != recomputed["cluster_summaries"] or dict(checks) != recomputed["checks"] or copied.get("passed") is not recomputed["passed"]
        or copied.get("all_predictions_frozen_before_gold_provenance_or_evaluator_open") is not True or copied.get("gold_provenance_path_opened_or_hashed") is not False or copied.get("evaluator_called") is not False
        or copied.get("source_policy") != SOURCE_POLICY or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 result drifted")
    return copied


def validate_decision(value: Mapping[str, Any], *, result: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value); passed = result.get("passed") is True
    if (
        set(copied) != {"artifact_version", "role", "protocol_id", "created_at_unix", "result_payload_sha256", "status", "authorization", "decision_payload_sha256"}
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24737_dual_namespace_reachability_decision" or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int) or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("result_payload_sha256") != result.get("result_payload_sha256") or copied.get("status") != ("dual_namespace_reachability_go" if passed else "dual_namespace_reachability_no_go")
        or copied.get("authorization") != {"postfreeze_external_evaluator_protocol_design": passed, "evaluator_execution": False, "additional_forward_retry_or_rerun": False, "benchmark_dev64_or_exact220": False, "entropy_or_credit_experiment": False, "leaderboard_or_sota": False}
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.47.37 decision drifted")
    return copied


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    findings = []
    try: result = validate_result(_read(root, RESULT))
    except (RuntimeError, TypeError, ValueError): result = _read(root, RESULT); findings.append("result_invalid")
    try: decision = validate_decision(_read(root, DECISION), result=result)
    except (RuntimeError, TypeError, ValueError): decision = _read(root, DECISION); findings.append("decision_invalid")
    if not _lease_inactive(root): findings.append("shared_lease_active")
    value = {
        "artifact_version": 1, "role": "v24737_dual_namespace_reachability_postresult_audit", "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT), "decision_sha256": sha256(root / DECISION), "decision_status": decision.get("status"),
        "protected_watchers": _watchers(), "shared_api_lease_inactive": _lease_inactive(root),
        "gold_provenance_or_evaluator_opened_by_audit": False, "network_model_search_or_api_called_by_audit": False,
        "findings": findings, "audit_valid": not findings,
        "authorization": {"additional_forward_retry_or_rerun": False, "evaluator_execution": False, "benchmark_dev64_or_exact220": False, "entropy_or_credit_experiment": False, "leaderboard_or_sota": False},
    }
    value["audit_payload_sha256"] = payload_sha256(value); return value


def command_protocol() -> None: _require_clean_pushed_head(); _publish(ROOT / PROTOCOL, build_protocol(ROOT))
def command_preaudit() -> None: _require_clean_pushed_head(); _publish(ROOT / PREAUDIT, build_preaudit(ROOT))
def command_activate() -> None: _require_clean_pushed_head(); _publish(ROOT / ACTIVATION, build_activation(ROOT))
def command_start() -> None: _require_clean_pushed_head(); _publish(ROOT / EXECUTION_START, build_start(ROOT))


def command_run() -> None:
    _require_clean_pushed_head(); validate_start(_read(ROOT, EXECUTION_START))
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (RESULT, DECISION, OUTPUT_ROOT)) or not _lease_inactive(ROOT):
        raise RuntimeError("V2.47.37 run surface is unsafe")
    with acquire_deepwide_api_lease(ROOT, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=ROOT / LEASE_PATH):
        (ROOT / OUTPUT_ROOT).mkdir(mode=0o700)
        _publish(ROOT / ATTEMPT_CLAIM, build_attempt_claim())
        result, decision = run_experiment(); validate_result(result); validate_decision(decision, result=result)
        _publish(ROOT / RESULT, result); _publish(ROOT / DECISION, decision)


def command_postaudit() -> None: _require_clean_pushed_head(); _publish(ROOT / POSTAUDIT, build_postaudit(ROOT))


COMMANDS = {"protocol": command_protocol, "preaudit": command_preaudit, "activate": command_activate, "start": command_start, "run": command_run, "postaudit": command_postaudit}


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit("usage: v24737_dual_namespace_reachability_gate.py {protocol|preaudit|activate|start|run|postaudit}")
    COMMANDS[sys.argv[1]]()
