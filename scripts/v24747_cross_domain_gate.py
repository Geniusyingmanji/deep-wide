#!/usr/bin/env python3
"""Sealed one-shot ROR/Crossref/OpenAlex generic-binding gate."""

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
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24744_cross_domain_contract as contract  # noqa: E402
from deepwide_agent import v24745_cross_domain_adapters as runtime  # noqa: E402
from scripts import v24746_public_get_helper as helper  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24747_cross_domain_generic_binding_gate_v1"
PROTOCOL = Path(f"results/v24747_cross_domain_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24747_cross_domain_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24747_cross_domain_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24747_cross_domain_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24747_cross_domain_result_v1_{DATE}.json")
DECISION = Path(f"results/v24747_cross_domain_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24747_cross_domain_postresult_audit_v1_{DATE}.json")
POPULATION = Path(f"results/v24744_cross_domain_population_design_v1_{DATE}.json")

RUNTIME_SOURCE = Path("src/deepwide_agent/v24745_cross_domain_adapters.py")
BINDER_SOURCE = Path("src/deepwide_agent/v24743_generic_record_binding.py")
CONTRACT_SOURCE = Path("src/deepwide_agent/v24744_cross_domain_contract.py")
HELPER_SOURCE = Path("scripts/v24746_public_get_helper.py")
SCRIPT = Path("scripts/v24747_cross_domain_gate.py")
LEASE_SOURCE = Path("scripts/deepwide_api_lease.py")
RUNTIME_TEST = Path("tests/test_v24745_cross_domain_adapters.py")
BINDER_TEST = Path("tests/test_v24743_generic_record_binding.py")
DESIGN_TEST = Path("tests/test_design_v24744_cross_domain_population.py")
HELPER_TEST = Path("tests/test_v24746_public_get_helper.py")
SCRIPT_TEST = Path("tests/test_v24747_cross_domain_gate.py")
CONTROL_SURFACE = (
    RUNTIME_SOURCE,
    BINDER_SOURCE,
    CONTRACT_SOURCE,
    HELPER_SOURCE,
    SCRIPT,
    LEASE_SOURCE,
    RUNTIME_TEST,
    BINDER_TEST,
    DESIGN_TEST,
    HELPER_TEST,
    SCRIPT_TEST,
    POPULATION,
)
FORWARD_AST_SURFACE = (
    RUNTIME_SOURCE,
    BINDER_SOURCE,
    CONTRACT_SOURCE,
    HELPER_SOURCE,
    SCRIPT,
)

OUTPUT_ROOT = Path(f"outputs/v24747_cross_domain_gate_v1_{DATE}")
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
ATTEMPT_CLAIM = OUTPUT_ROOT / "attempt_claim.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_cross_domain_generic_binding_gate"
RUNNER_MARKER = "scripts/v24747_cross_domain_gate.py run"

TASK_COUNT = 6
TASKS_PER_CLUSTER = 2
REQUEST_COUNT = 32
WORKERS = 32
HARD_WALL_SECONDS = 20.0
SOCKET_TIMEOUT_SECONDS = 15.0
EXPERIMENT_WALL_CEILING_SECONDS = 40.0
MODES = (
    "ror_official_exact",
    "crossref_official_exact",
    "crossref_openalex_ordinary",
)
EXPECTED_TESTS = 32
TEST_SUITES = (
    (BINDER_TEST, 12),
    (DESIGN_TEST, 4),
    (RUNTIME_TEST, 6),
    (HELPER_TEST, 3),
    (SCRIPT_TEST, 7),
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
REQUIRED_CHECKS = (
    "fixed_32_request_attempt_vector_complete",
    "all_6_tasks_terminal_and_runtime_valid",
    "at_least_one_transport_success_per_host",
    "ror_official_exact_full_row_reached",
    "crossref_official_exact_full_row_reached",
    "ordinary_crossref_openalex_full_row_reached",
    "ordinary_two_registrable_source_corroboration_reached",
    "experiment_wall_within_ceiling",
    "public_aggregate_is_content_free",
    "prediction_freeze_precedes_evaluator_or_quality_read",
)
REQUEST_RECEIPT_KEYS = frozenset(
    {
        "request_index",
        "source_host",
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
        "mode",
        "runtime_valid",
        "prediction_changed",
        "changed_cell_count",
        "fully_admitted_row_count",
        "official_admitted_cell_count",
        "corroborated_admitted_cell_count",
        "conflicting_cell_count",
        "validated_record_count",
        "adapter_failure_count",
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
        "http_or_content_invalid",
    }
)
SOURCE_POLICY = {
    "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    "model_hosted_search_or_benchmark_forward_called": False,
    "credential_read_hashed_persisted_or_emitted": False,
    "private_population_or_provenance_opened_or_hashed": False,
    "response_body_identity_value_or_prediction_persisted_in_public_aggregate": False,
    "entropy_or_positive_task_credit_assigned": False,
    "resume_retry_or_selective_rerun": False,
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


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
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
        raise RuntimeError(f"V2.47.47 expected repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.47 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
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
        raise RuntimeError("V2.47.47 requires clean pushed HEAD")


def _watchers() -> list[dict[str, Any]]:
    output = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
        ticks = int(raw[raw.rfind(")") + 2 :].split()[19])
        command = (
            (Path("/proc") / str(pid) / "cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode(errors="replace")
        )
        if ticks != expected_ticks or marker not in command:
            raise RuntimeError("V2.47.47 protected watcher drifted")
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
        RUNNER_MARKER in line
        and len(line.split()) >= 2
        and "python" in line.split()[1].casefold()
        for line in completed.stdout.splitlines()
    )


def _manifest(root: Path) -> dict[str, str]:
    output = {}
    for relative in CONTROL_SURFACE:
        path = _ordinary(root, relative)
        if root.resolve() == ROOT.resolve() and not _tracked(relative):
            raise RuntimeError(f"V2.47.47 untracked control file: {relative}")
        raw = path.read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.47 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def ast_findings(root: Path = ROOT) -> tuple[list[str], list[str]]:
    accesses = []
    imports = []
    for relative in FORWARD_AST_SURFACE:
        tree = ast.parse(_ordinary(root, relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key = None
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
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(
                    marker in name.casefold()
                    for marker in (
                        "official_eval",
                        "evaluator_mapping",
                        "finalize_v24",
                        "v24744_cross_domain_population_private",
                    )
                ):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _population(root: Path) -> dict[str, Any]:
    value = _read(root, POPULATION)
    if (
        value.get("role") != "v24744_cross_domain_population_design"
        or value.get("task_shape")
        != {
            "ror_tasks": 2,
            "official_crossref_tasks": 2,
            "ordinary_dual_source_tasks": 2,
            "total_tasks": 6,
            "total_rows": 24,
        }
        or value.get("selection_timing")
        != {
            "doi_vector_and_ror_seed_frozen_before_endpoint_outcome": True,
            "crossref_openalex_or_ror_api_called": False,
            "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        }
        or value.get("visible_contract_sha256") != sha256(root / CONTRACT_SOURCE)
        or value.get("authorization")
        != {
            "cross_domain_adapter_and_gate_build": True,
            "external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "design_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 population design drifted")
    return value


def _tasks() -> list[dict[str, str]]:
    tasks = contract.task_vector()
    modes = [runtime.visible_contract(task)["mode"] for task in tasks]
    if (
        len(tasks) != TASK_COUNT
        or any(set(task) != {"opaque_id", "question"} for task in tasks)
        or modes
        != [
            "ror_official_exact",
            "ror_official_exact",
            "crossref_official_exact",
            "crossref_official_exact",
            "crossref_openalex_ordinary",
            "crossref_openalex_ordinary",
        ]
    ):
        raise RuntimeError("V2.47.47 visible task vector drifted")
    return tasks


def _request_vector() -> list[str]:
    values = [url for task in _tasks() for url in runtime.request_urls(task)]
    if (
        len(values) != REQUEST_COUNT
        or len(set(values)) != REQUEST_COUNT
        or set(values) != helper.ALLOWED_URLS
    ):
        raise RuntimeError("V2.47.47 request vector drifted")
    return values


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    _population(root)
    manifest = _manifest(root)
    tasks = _tasks()
    requests = _request_vector()
    value = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "benchmark_external_cross_domain_generic_binding_only",
        "parent_population_sha256": sha256(root / POPULATION),
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "task_count": TASK_COUNT,
            "tasks_per_cluster": TASKS_PER_CLUSTER,
            "cluster_order": list(MODES),
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        },
        "execution": {
            "unique_request_count": REQUEST_COUNT,
            "request_url_vector_sha256": payload_sha256(requests),
            "source_host_counts": {
                runtime.ROR_HOST: 8,
                runtime.CROSSREF_HOST: 16,
                runtime.OPENALEX_HOST: 8,
            },
            "workers": WORKERS,
            "attempts_per_url": 1,
            "hard_total_wall_seconds": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "single_wave": True,
            "cache_resume_retry_or_selective_rerun": False,
        },
        "gates": {"required_checks": list(REQUIRED_CHECKS)},
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "protected_watchers": _watchers(),
        "evaluation_separation": {
            "private_population_gold_provenance_or_evaluator_in_forward_manifest": False,
            "prediction_freeze_before_evaluator_or_quality_read": True,
            "mechanism_no_go_stops_without_evaluator": True,
            "quality_not_measured_by_forward": True,
        },
        "source_policy": dict(SOURCE_POLICY),
        "authorization": {
            "preactivation_audit_generation": True,
            "external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(root, PROTOCOL)
    tasks = _tasks()
    requests = _request_vector()
    manifest = copied.get("dependency_manifest")
    if (
        copied.get("role") != "v24747_cross_domain_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope")
        != "benchmark_external_cross_domain_generic_binding_only"
        or copied.get("parent_population_sha256") != sha256(root / POPULATION)
        or copied.get("task_contract")
        != {
            "runtime_input_keys": ["opaque_id", "question"],
            "task_count": TASK_COUNT,
            "tasks_per_cluster": TASKS_PER_CLUSTER,
            "cluster_order": list(MODES),
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
        or copied.get("execution")
        != {
            "unique_request_count": REQUEST_COUNT,
            "request_url_vector_sha256": payload_sha256(requests),
            "source_host_counts": {
                runtime.ROR_HOST: 8,
                runtime.CROSSREF_HOST: 16,
                runtime.OPENALEX_HOST: 8,
            },
            "workers": WORKERS,
            "attempts_per_url": 1,
            "hard_total_wall_seconds": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "single_wave": True,
            "cache_resume_retry_or_selective_rerun": False,
        }
        or copied.get("gates") != {"required_checks": list(REQUIRED_CHECKS)}
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("evaluation_separation")
        != {
            "private_population_gold_provenance_or_evaluator_in_forward_manifest": False,
            "prediction_freeze_before_evaluator_or_quality_read": True,
            "mechanism_no_go_stops_without_evaluator": True,
            "quality_not_measured_by_forward": True,
        }
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 protocol drifted")
    return copied


def _run_tests() -> tuple[bool, int, str]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    outputs = []
    observed_total = 0
    passed = True
    python = ROOT / ".venv-eval/bin/python"
    for suite, expected in TEST_SUITES:
        module = str(suite.with_suffix("")).replace("/", ".")
        completed = subprocess.run(
            [str(python), "-I", "-B", "-m", "unittest", module, "-v"],
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
    validate_protocol(root)
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
        findings.append("runner_active")
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        findings.append("repository_not_clean_pushed_head")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT, OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "tests": {
            "passed": tests_passed,
            "observed": observed,
            "expected": EXPECTED_TESTS,
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        },
        "label_blind_audit": {
            "accesses": accesses,
            "evaluator_or_private_imports": imports,
            "passed": not accesses and not imports,
        },
        "runtime_state": {
            "protected_watchers": _watchers(),
            "shared_api_lease_inactive": _lease_inactive(root),
            "runner_active": _runner_active(),
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "activation_publication": not findings,
            "external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_preaudit(value)
    return value


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    tests = copied.get("tests", {})
    state = copied.get("runtime_state", {})
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    if (
        copied.get("role") != "v24747_cross_domain_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or tests.get("passed") is not True
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("expected") != EXPECTED_TESTS
        or copied.get("label_blind_audit")
        != {
            "accesses": [],
            "evaluator_or_private_imports": [],
            "passed": True,
        }
        or state.get("protected_watchers") != _watchers()
        or state.get("shared_api_lease_inactive") is not True
        or state.get("runner_active") is not False
        or not isinstance(findings, list)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "activation_publication": bool(valid),
            "external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 preaudit drifted")
    return copied


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    validate_protocol(root)
    preaudit = validate_preaudit(_read(root, PREAUDIT))
    if preaudit.get("audit_valid") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.47 activation is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "protected_watchers": _watchers(),
        "network_model_search_evaluator_or_api_called": False,
        "launch_authorized": True,
        "authorization": {
            "one_external_launch": True,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    validate_activation(value)
    return value


def validate_activation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24747_cross_domain_activation"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("network_model_search_evaluator_or_api_called") is not False
        or copied.get("launch_authorized") is not True
        or copied.get("authorization")
        != {
            "one_external_launch": True,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 activation drifted")
    return copied


def build_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    activation = validate_activation(_read(root, ACTIVATION))
    if activation.get("launch_authorized") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.47 execution start is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "protected_watchers": _watchers(),
        "single_owner_no_resume_retry_or_selective_rerun": True,
        "authorization": {
            "execute_once": True,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        },
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    validate_start(value)
    return value


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24747_cross_domain_execution_start"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("single_owner_no_resume_retry_or_selective_rerun") is not True
        or copied.get("authorization")
        != {
            "execute_once": True,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        }
        or not _sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 execution start drifted")
    return copied


def build_attempt_claim(*, now: int | None = None) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_attempt_claim",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "unique_request_count": REQUEST_COUNT,
        "attempts_per_url": 1,
        "single_wave": True,
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
            "single_wave",
            "resume_retry_or_selective_rerun",
            "network_model_search_evaluator_or_api_called_before_claim",
            "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24747_cross_domain_attempt_claim"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("unique_request_count") != REQUEST_COUNT
        or copied.get("attempts_per_url") != 1
        or copied.get("single_wave") is not True
        or copied.get("resume_retry_or_selective_rerun") is not False
        or copied.get("network_model_search_evaluator_or_api_called_before_claim")
        is not False
        or not _sealed(copied, "claim_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 attempt claim drifted")
    return copied


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


def _terminate(process: Any) -> None:
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


def hard_get(
    url: str,
    *,
    timeout_seconds: float = HARD_WALL_SECONDS,
    popen: Any = subprocess.Popen,
) -> dict[str, Any]:
    if (
        url not in helper.ALLOWED_URLS
        or isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(float(timeout_seconds))
        or timeout_seconds <= 0
    ):
        raise ValueError("V2.47.47 hard GET input drifted")
    started = time.monotonic()
    try:
        process = popen(
            [sys.executable, "-I", "-B", str(ROOT / HELPER_SOURCE)],
            cwd=ROOT,
            env=_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )
    except OSError:
        return {
            "kind": "helper_launch_error",
            "status_code": None,
            "final_url": "",
            "body": b"",
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }
    request = json.dumps(
        {"url": url, "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS},
        separators=(",", ":"),
    )
    try:
        stdout, _stderr = process.communicate(request, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate(process)
        return {
            "kind": "hard_total_wall_timeout",
            "status_code": None,
            "final_url": "",
            "body": b"",
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }
    try:
        value = json.loads(stdout)
        if (
            process.returncode != 0
            or not isinstance(value, Mapping)
            or set(value) != helper.OUTPUT_KEYS
        ):
            raise ValueError("V2.47.47 helper output drifted")
        body = (
            base64.b64decode(value["body_base64"], validate=True)
            if value["body_base64"]
            else b""
        )
        if len(body) > runtime.MAX_RESPONSE_BYTES:
            raise ValueError("V2.47.47 helper body drifted")
    except (ValueError, TypeError, json.JSONDecodeError):
        return {
            "kind": "helper_invalid",
            "status_code": None,
            "final_url": "",
            "body": b"",
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }
    return {
        "kind": str(value["kind"]),
        "status_code": value["status_code"],
        "final_url": str(value["final_url"]),
        "body": body,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }


def _request_one(index_url: tuple[int, str]) -> tuple[dict[str, Any], bytes]:
    index, url = index_url
    response = hard_get(url)
    body = response.pop("body")
    success = (
        response["kind"] == "response"
        and response["status_code"] == 200
        and response["final_url"] == url
        and bool(body)
    )
    failure_type = None
    if not success:
        failure_type = (
            "http_or_content_invalid"
            if response["kind"] == "response"
            else response["kind"]
        )
    receipt = {
        "request_index": index,
        "source_host": urlsplit(url).hostname,
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "attempts": 1,
        "transport_success": success,
        "failure_type": failure_type,
        "http_status": response["status_code"],
        "elapsed_seconds": response["elapsed_seconds"],
        "response_bytes": len(body),
        "raw_sha256": hashlib.sha256(body).hexdigest() if success else None,
        "response_content_persisted": False,
    }
    return receipt, body if success else b""


def aggregate(
    task_rows: Sequence[Mapping[str, Any]],
    request_receipts: Sequence[Mapping[str, Any]],
    *,
    experiment_wall_seconds: float,
    predictions_sha256: str,
    freeze_sha256: str,
    now: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    summaries = {}
    for mode in MODES:
        rows = [row for row in task_rows if row.get("mode") == mode]
        summaries[mode] = {
            "tasks": len(rows),
            "runtime_valid_tasks": sum(row.get("runtime_valid") is True for row in rows),
            "prediction_changing_tasks": sum(
                row.get("prediction_changed") is True for row in rows
            ),
            "changed_cells": sum(int(row.get("changed_cell_count", 0)) for row in rows),
            "fully_admitted_rows": sum(
                int(row.get("fully_admitted_row_count", 0)) for row in rows
            ),
            "official_admitted_cells": sum(
                int(row.get("official_admitted_cell_count", 0)) for row in rows
            ),
            "corroborated_admitted_cells": sum(
                int(row.get("corroborated_admitted_cell_count", 0)) for row in rows
            ),
            "conflicting_cells": sum(
                int(row.get("conflicting_cell_count", 0)) for row in rows
            ),
            "validated_records": sum(
                int(row.get("validated_record_count", 0)) for row in rows
            ),
            "adapter_failures": sum(
                int(row.get("adapter_failure_count", 0)) for row in rows
            ),
        }
    hosts = {
        host: sum(
            row.get("transport_success") is True
            for row in request_receipts
            if row.get("source_host") == host
        )
        for host in (runtime.ROR_HOST, runtime.CROSSREF_HOST, runtime.OPENALEX_HOST)
    }
    checks = {
        "fixed_32_request_attempt_vector_complete": (
            len(request_receipts) == REQUEST_COUNT
            and {item.get("request_index") for item in request_receipts}
            == set(range(1, REQUEST_COUNT + 1))
            and all(item.get("attempts") == 1 for item in request_receipts)
        ),
        "all_6_tasks_terminal_and_runtime_valid": (
            len(task_rows) == TASK_COUNT
            and {item.get("position") for item in task_rows}
            == set(range(1, TASK_COUNT + 1))
            and all(item.get("runtime_valid") is True for item in task_rows)
        ),
        "at_least_one_transport_success_per_host": all(value >= 1 for value in hosts.values()),
        "ror_official_exact_full_row_reached": summaries[
            "ror_official_exact"
        ]["fully_admitted_rows"]
        >= 1,
        "crossref_official_exact_full_row_reached": summaries[
            "crossref_official_exact"
        ]["fully_admitted_rows"]
        >= 1,
        "ordinary_crossref_openalex_full_row_reached": summaries[
            "crossref_openalex_ordinary"
        ]["fully_admitted_rows"]
        >= 1,
        "ordinary_two_registrable_source_corroboration_reached": summaries[
            "crossref_openalex_ordinary"
        ]["corroborated_admitted_cells"]
        >= 2,
        "experiment_wall_within_ceiling": (
            isinstance(experiment_wall_seconds, (int, float))
            and not isinstance(experiment_wall_seconds, bool)
            and math.isfinite(float(experiment_wall_seconds))
            and 0 <= float(experiment_wall_seconds) <= EXPERIMENT_WALL_CEILING_SECONDS
        ),
        "public_aggregate_is_content_free": (
            all(
                item.get("response_content_persisted") is False
                and "body" not in item
                and "url" not in item
                for item in request_receipts
            )
            and all(
                item.get(
                    "response_or_prediction_content_persisted_in_public_aggregate"
                )
                is False
                for item in task_rows
            )
        ),
        "prediction_freeze_precedes_evaluator_or_quality_read": True,
    }
    passed = all(checks[name] for name in REQUIRED_CHECKS)
    result = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "selected_tasks": TASK_COUNT,
        "terminal_arm_predictions": TASK_COUNT * 2,
        "unique_requests": REQUEST_COUNT,
        "request_successes": sum(
            item.get("transport_success") is True for item in request_receipts
        ),
        "request_failure_type_counts": dict(
            sorted(
                Counter(
                    str(item.get("failure_type"))
                    for item in request_receipts
                    if item.get("transport_success") is not True
                ).items()
            )
        ),
        "transport_successes_by_host": hosts,
        "experiment_wall_seconds": float(experiment_wall_seconds),
        "predictions_sha256": predictions_sha256,
        "prediction_freeze_sha256": freeze_sha256,
        "cluster_summaries": summaries,
        "request_receipts": [dict(item) for item in request_receipts],
        "task_receipts": [dict(item) for item in task_rows],
        "checks": checks,
        "passed": passed,
        "all_predictions_frozen_before_private_population_evaluator_or_quality_read": True,
        "private_population_provenance_or_evaluator_path_opened_or_hashed": False,
        "evaluator_called": False,
        "source_policy": dict(SOURCE_POLICY),
    }
    result["result_payload_sha256"] = payload_sha256(result)
    decision = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_payload_sha256": result["result_payload_sha256"],
        "status": "cross_domain_mechanism_go" if passed else "cross_domain_mechanism_no_go",
        "authorization": {
            "task_cluster_disjoint_paired_dev64_protocol_design": passed,
            "paired_dev64_launch": False,
            "additional_external_retry_or_rerun": False,
            "evaluator_execution": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    decision["decision_payload_sha256"] = payload_sha256(decision)
    return result, decision


def _failure_projection(task: Mapping[str, Any]) -> dict[str, Any]:
    visible = runtime.visible_contract(task)
    baseline = runtime._render_unknown(visible["columns"], visible["identities"])
    expected = len(runtime.request_urls(task))
    return {
        "baseline": baseline,
        "candidate": baseline,
        "result_payload_sha256": None,
        "receipt": {
            "prediction_changed": False,
            "fully_admitted_row_count": 0,
            "validated_record_count": 0,
            "failure_type_counts": {"runtime_failure_projection": expected},
            "binding_receipt": {
                "changed_cell_count": 0,
                "official_admitted_cell_count": 0,
                "corroborated_admitted_cell_count": 0,
                "conflicting_cell_count": 0,
            },
        },
    }


def run_experiment() -> tuple[dict[str, Any], dict[str, Any]]:
    validate_attempt_claim(_read(ROOT, ATTEMPT_CLAIM))
    started = time.monotonic()
    urls = _request_vector()
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        outputs = list(executor.map(_request_one, enumerate(urls, 1)))
    request_receipts = [item[0] for item in outputs]
    responses = {
        url: output[1]
        for url, output in zip(urls, outputs, strict=True)
    }
    prediction_rows = []
    task_rows = []
    for position, task in enumerate(_tasks(), 1):
        mode = runtime.visible_contract(task)["mode"]
        task_urls = runtime.request_urls(task)
        subset = {url: responses[url] for url in task_urls}
        runtime_valid = True
        try:
            value = runtime.run_task(task, subset)
        except (KeyError, TypeError, ValueError):
            runtime_valid = False
            value = _failure_projection(task)
        receipt = value["receipt"]
        binding = receipt["binding_receipt"]
        failures = receipt.get("failure_type_counts", {})
        prediction_rows.append(
            {
                "opaque_id": task["opaque_id"],
                "predictions": {
                    "baseline": value["baseline"],
                    "candidate": value["candidate"],
                },
                "runtime_result_sha256": value.get("result_payload_sha256"),
                "runtime_result_valid": runtime_valid,
            }
        )
        task_rows.append(
            {
                "position": position,
                "mode": mode,
                "runtime_valid": runtime_valid,
                "prediction_changed": bool(receipt["prediction_changed"]),
                "changed_cell_count": int(binding["changed_cell_count"]),
                "fully_admitted_row_count": int(receipt["fully_admitted_row_count"]),
                "official_admitted_cell_count": int(
                    binding["official_admitted_cell_count"]
                ),
                "corroborated_admitted_cell_count": int(
                    binding["corroborated_admitted_cell_count"]
                ),
                "conflicting_cell_count": int(binding["conflicting_cell_count"]),
                "validated_record_count": int(receipt["validated_record_count"]),
                "adapter_failure_count": sum(int(amount) for amount in failures.values()),
                "response_or_prediction_content_persisted_in_public_aggregate": False,
            }
        )
    if (ROOT / OUTPUT_ROOT).is_symlink() or not (ROOT / OUTPUT_ROOT).is_dir():
        raise RuntimeError("V2.47.47 attempt claim directory drifted")
    _publish_jsonl(ROOT / PREDICTIONS, prediction_rows)
    summary = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_run_summary",
        "attempt_claim_sha256": sha256(ROOT / ATTEMPT_CLAIM),
        "selected_tasks": TASK_COUNT,
        "terminal_prediction_rows": len(prediction_rows),
        "terminal_arm_predictions": len(prediction_rows) * 2,
        "request_attempts": len(request_receipts),
        "runtime_valid_tasks": sum(row["runtime_valid"] for row in task_rows),
        "experiment_wall_seconds": round(time.monotonic() - started, 6),
        "resume_retry_skip_or_selective_rerun": False,
        "private_population_provenance_evaluator_or_quality_opened": False,
    }
    summary["summary_payload_sha256"] = payload_sha256(summary)
    _publish(ROOT / RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "selected_tasks": TASK_COUNT,
        "terminal_arm_predictions": TASK_COUNT * 2,
        "predictions_sha256": sha256(ROOT / PREDICTIONS),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "all_predictions_terminal_before_private_population_evaluator_or_quality_read": True,
        "private_population_provenance_path_opened_or_hashed": False,
        "evaluator_called": False,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze)
    _publish(ROOT / PREDICTION_FREEZE, freeze)
    return aggregate(
        task_rows,
        request_receipts,
        experiment_wall_seconds=summary["experiment_wall_seconds"],
        predictions_sha256=sha256(ROOT / PREDICTIONS),
        freeze_sha256=sha256(ROOT / PREDICTION_FREEZE),
    )


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    requests = copied.get("request_receipts")
    tasks = copied.get("task_receipts")
    checks = copied.get("checks")
    summaries = copied.get("cluster_summaries")
    if (
        not isinstance(requests, list)
        or not isinstance(tasks, list)
        or not isinstance(checks, Mapping)
        or not isinstance(summaries, Mapping)
    ):
        raise RuntimeError("V2.47.47 result vectors absent")
    expected_urls = _request_vector()
    request_valid = len(requests) == REQUEST_COUNT and all(
        isinstance(item, Mapping)
        and set(item) == REQUEST_RECEIPT_KEYS
        and item.get("request_index") == index
        and item.get("source_host") == urlsplit(url).hostname
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
        and 0 <= item.get("response_bytes") <= runtime.MAX_RESPONSE_BYTES
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
    expected_modes = [
        "ror_official_exact",
        "ror_official_exact",
        "crossref_official_exact",
        "crossref_official_exact",
        "crossref_openalex_ordinary",
        "crossref_openalex_ordinary",
    ]
    task_valid = len(tasks) == TASK_COUNT and all(
        isinstance(item, Mapping)
        and set(item) == TASK_RECEIPT_KEYS
        and item.get("position") == index
        and item.get("mode") == expected_mode
        and isinstance(item.get("runtime_valid"), bool)
        and isinstance(item.get("prediction_changed"), bool)
        and all(
            isinstance(item.get(name), int)
            and not isinstance(item.get(name), bool)
            and item.get(name) >= 0
            for name in (
                "changed_cell_count",
                "fully_admitted_row_count",
                "official_admitted_cell_count",
                "corroborated_admitted_cell_count",
                "conflicting_cell_count",
                "validated_record_count",
                "adapter_failure_count",
            )
        )
        and item.get("changed_cell_count")
        == item.get("official_admitted_cell_count")
        + item.get("corroborated_admitted_cell_count")
        and item.get("prediction_changed") is (item.get("changed_cell_count") > 0)
        and item.get("fully_admitted_row_count") <= 4
        and item.get("changed_cell_count") <= 8
        and item.get("conflicting_cell_count") <= 8
        and item.get("validated_record_count") + item.get("adapter_failure_count")
        == (8 if expected_mode == "crossref_openalex_ordinary" else 4)
        and (
            item.get("official_admitted_cell_count") == 0
            if expected_mode == "crossref_openalex_ordinary"
            else item.get("corroborated_admitted_cell_count") == 0
        )
        and (
            item.get("runtime_valid") is True
            or (
                item.get("changed_cell_count") == 0
                and item.get("validated_record_count") == 0
            )
        )
        and item.get(
            "response_or_prediction_content_persisted_in_public_aggregate"
        )
        is False
        for index, (item, expected_mode) in enumerate(
            zip(tasks, expected_modes, strict=True), 1
        )
    )
    try:
        created_at = int(copied.get("created_at_unix"))
    except (TypeError, ValueError):
        created_at = -1
    recomputed, _decision = aggregate(
        tasks,
        requests,
        experiment_wall_seconds=copied.get("experiment_wall_seconds"),
        predictions_sha256=str(copied.get("predictions_sha256")),
        freeze_sha256=str(copied.get("prediction_freeze_sha256")),
        now=created_at,
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "execution_start_sha256",
            "selected_tasks",
            "terminal_arm_predictions",
            "unique_requests",
            "request_successes",
            "request_failure_type_counts",
            "transport_successes_by_host",
            "experiment_wall_seconds",
            "predictions_sha256",
            "prediction_freeze_sha256",
            "cluster_summaries",
            "request_receipts",
            "task_receipts",
            "checks",
            "passed",
            "all_predictions_frozen_before_private_population_evaluator_or_quality_read",
            "private_population_provenance_or_evaluator_path_opened_or_hashed",
            "evaluator_called",
            "source_policy",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24747_cross_domain_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("selected_tasks") != TASK_COUNT
        or copied.get("terminal_arm_predictions") != TASK_COUNT * 2
        or copied.get("unique_requests") != REQUEST_COUNT
        or not request_valid
        or not task_valid
        or copied.get("request_successes")
        != sum(item.get("transport_success") is True for item in requests)
        or copied.get("request_failure_type_counts")
        != recomputed.get("request_failure_type_counts")
        or copied.get("transport_successes_by_host")
        != recomputed.get("transport_successes_by_host")
        or copied.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or copied.get("prediction_freeze_sha256")
        != sha256(ROOT / PREDICTION_FREEZE)
        or copied.get("cluster_summaries") != recomputed.get("cluster_summaries")
        or dict(checks) != recomputed.get("checks")
        or copied.get("passed") is not recomputed.get("passed")
        or copied.get(
            "all_predictions_frozen_before_private_population_evaluator_or_quality_read"
        )
        is not True
        or copied.get(
            "private_population_provenance_or_evaluator_path_opened_or_hashed"
        )
        is not False
        or copied.get("evaluator_called") is not False
        or copied.get("source_policy") != SOURCE_POLICY
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 result drifted")
    return copied


def validate_decision(
    value: Mapping[str, Any], *, result: Mapping[str, Any]
) -> dict[str, Any]:
    copied = dict(value)
    passed = result.get("passed") is True
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "result_payload_sha256",
            "status",
            "authorization",
            "decision_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24747_cross_domain_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("result_payload_sha256")
        != result.get("result_payload_sha256")
        or copied.get("status")
        != (
            "cross_domain_mechanism_go"
            if passed
            else "cross_domain_mechanism_no_go"
        )
        or copied.get("authorization")
        != {
            "task_cluster_disjoint_paired_dev64_protocol_design": passed,
            "paired_dev64_launch": False,
            "additional_external_retry_or_rerun": False,
            "evaluator_execution": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.47.47 decision drifted")
    return copied


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    findings = []
    try:
        result = validate_result(_read(root, RESULT))
    except (RuntimeError, TypeError, ValueError):
        result = _read(root, RESULT)
        findings.append("result_invalid")
    try:
        decision = validate_decision(_read(root, DECISION), result=result)
    except (RuntimeError, TypeError, ValueError):
        decision = _read(root, DECISION)
        findings.append("decision_invalid")
    if not _lease_inactive(root):
        findings.append("shared_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24747_cross_domain_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision.get("status"),
        "protected_watchers": _watchers(),
        "shared_api_lease_inactive": _lease_inactive(root),
        "private_population_provenance_evaluator_or_quality_opened_by_audit": False,
        "network_model_search_or_api_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "additional_external_retry_or_rerun": False,
            "evaluator_execution": False,
            "paired_dev64_launch": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
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
    _publish(ROOT / EXECUTION_START, build_start(ROOT))


def command_run() -> None:
    _require_clean_pushed_head()
    validate_start(_read(ROOT, EXECUTION_START))
    if (
        any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (RESULT, DECISION, OUTPUT_ROOT)
        )
        or not _lease_inactive(ROOT)
    ):
        raise RuntimeError("V2.47.47 run surface is unsafe")
    with acquire_deepwide_api_lease(
        ROOT,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=ROOT / LEASE_PATH,
    ):
        (ROOT / OUTPUT_ROOT).mkdir(mode=0o700)
        _publish(ROOT / ATTEMPT_CLAIM, build_attempt_claim())
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
        raise SystemExit(
            "usage: v24747_cross_domain_gate.py "
            "{protocol|preaudit|activate|start|run|postaudit}"
        )
    COMMANDS[sys.argv[1]]()
