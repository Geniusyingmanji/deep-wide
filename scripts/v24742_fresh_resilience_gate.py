#!/usr/bin/env python3
"""Sealed one-shot fresh-target dual-representation resilience gate."""

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

from deepwide_agent import v24740_dual_representation_resilience as runtime  # noqa: E402
from scripts import design_v24739_fresh_resilience_population as design  # noqa: E402
from scripts import v24741_public_get_helper as helper  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24742_fresh_dual_representation_resilience_v1"
PROTOCOL = Path(f"results/v24742_fresh_resilience_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24742_fresh_resilience_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24742_fresh_resilience_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24742_fresh_resilience_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24742_fresh_resilience_result_v1_{DATE}.json")
DECISION = Path(f"results/v24742_fresh_resilience_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24742_fresh_resilience_postresult_audit_v1_{DATE}.json")
DESIGN = design.OUTPUT
DIAGNOSIS = Path(f"results/v24738_v24737_failure_domain_diagnosis_v1_{DATE}.json")
RUNTIME_SOURCE = Path("src/deepwide_agent/v24740_dual_representation_resilience.py")
RUNTIME_TEST = Path("tests/test_v24740_dual_representation_resilience.py")
HELPER_SOURCE = Path("scripts/v24741_public_get_helper.py")
HELPER_TEST = Path("tests/test_v24741_public_get_helper.py")
DESIGN_SOURCE = Path("scripts/design_v24739_fresh_resilience_population.py")
DESIGN_TEST = Path("tests/test_design_v24739_fresh_resilience_population.py")
SCRIPT = Path("scripts/v24742_fresh_resilience_gate.py")
SCRIPT_TEST = Path("tests/test_v24742_fresh_resilience_gate.py")
LEASE_SOURCE = Path("scripts/deepwide_api_lease.py")
SOURCES = (
    RUNTIME_SOURCE,
    RUNTIME_TEST,
    HELPER_SOURCE,
    HELPER_TEST,
    DESIGN_SOURCE,
    DESIGN_TEST,
    SCRIPT,
    SCRIPT_TEST,
    LEASE_SOURCE,
    DESIGN,
    DIAGNOSIS,
)
OUTPUT_ROOT = Path(f"outputs/v24742_fresh_resilience_v1_{DATE}")
ATTEMPT_CLAIM = OUTPUT_ROOT / "attempt_claim.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_fresh_target_dual_representation_resilience"
RUNNER_MARKER = "scripts/v24742_fresh_resilience_gate.py run"
REQUEST_COUNT = len(helper.ALLOWED_URLS)
TARGET_COUNT = len(runtime.TARGETS)
WORKERS = REQUEST_COUNT
HARD_WALL_SECONDS = 20.0
SOCKET_TIMEOUT_SECONDS = 15.0
EXPERIMENT_WALL_CEILING_SECONDS = 25.0
EXPECTED_TESTS = 21
TEST_SUITES = (
    (RUNTIME_TEST, 8),
    (HELPER_TEST, 4),
    (DESIGN_TEST, 3),
    (SCRIPT_TEST, 6),
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
REQUIRED_CHECKS = (
    "fixed_four_request_attempt_vector_complete",
    "schema_valid_representations_have_successful_transport",
    "both_targets_admitted_by_at_least_one_schema_valid_representation",
    "all_dual_valid_targets_have_common_value_agreement",
    "every_schema_valid_representation_admits_as_singleton",
    "target_failure_isolation_contract_valid",
    "experiment_wall_within_ceiling",
    "no_response_country_value_or_content_persisted",
    "retry_resume_or_selective_rerun_absent",
)
REQUEST_RECEIPT_KEYS = frozenset(
    {
        "request_index",
        "target_key",
        "representation",
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
SINGLETON_RECEIPT_KEYS = frozenset(
    {
        "target_key",
        "available_representation",
        "target_admitted",
        "selected_representation",
        "admitted_record_count",
        "response_country_value_or_content_persisted",
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
    "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    "model_search_benchmark_forward_or_evaluator_called": False,
    "credential_read_hashed_persisted_or_emitted": False,
    "response_country_value_or_content_persisted": False,
    "same_population_retry_resume_or_selective_rerun": False,
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
        raise RuntimeError(f"V2.47.42 expected repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.42 expected object")
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
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _require_clean_pushed_head() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.42 requires clean pushed HEAD")


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
            raise RuntimeError("V2.47.42 protected watcher drifted")
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
    for relative in SOURCES:
        path = _ordinary(root, relative)
        if root.resolve() == ROOT.resolve() and not _tracked(relative):
            raise RuntimeError(f"V2.47.42 untracked source: {relative}")
        raw = path.read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.42 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def ast_findings(root: Path = ROOT) -> tuple[list[str], list[str]]:
    accesses = []
    imports = []
    for relative in (RUNTIME_SOURCE, HELPER_SOURCE, DESIGN_SOURCE, SCRIPT):
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
                        "v24733_dual_namespace_evaluator",
                    )
                ):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _parents(root: Path) -> None:
    population = _read(root, DESIGN)
    diagnosis = _read(root, DIAGNOSIS)
    design.validate_design(population)
    if (
        population.get("role") != "v24739_fresh_resilience_population_design"
        or [
            item.get("target_key")
            for item in population.get("selection", {}).get("selected_targets", [])
            if isinstance(item, Mapping)
        ]
        != [runtime.target_key(target) for target in runtime.TARGETS]
        or population.get("authorization", {}).get(
            "dual_representation_runtime_helper_and_protocol_design"
        )
        is not True
        or population.get("authorization", {}).get("transport_launch") is not False
        or not _sealed(population, "design_payload_sha256")
        or diagnosis.get("role")
        != "v24738_v24737_failure_domain_postterminal_diagnosis"
        or diagnosis.get("diagnosis", {}).get("next_requirement")
        != "fresh_target_fixed_dual_representation_or_availability_with_target_granular_abstention"
        or diagnosis.get("authorization", {}).get(
            "fresh_target_dual_representation_resilience_design"
        )
        is not True
        or diagnosis.get("authorization", {}).get("same_population_forward_retry_or_rerun")
        is not False
        or not _sealed(diagnosis, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 parent chain drifted")


def _request_vector() -> list[tuple[runtime.FreshTarget, str, str]]:
    output = [
        (target, representation, runtime.endpoint_url(target, representation))
        for target in runtime.TARGETS
        for representation in runtime.REPRESENTATIONS
    ]
    if len(output) != REQUEST_COUNT or {row[2] for row in output} != set(helper.ALLOWED_URLS):
        raise RuntimeError("V2.47.42 request vector drifted")
    return output


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    _parents(root)
    manifest = _manifest(root)
    requests = _request_vector()
    value = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "benchmark_external_fresh_target_dual_representation_resilience_only",
        "parents": {
            "population_design_sha256": sha256(root / DESIGN),
            "failure_domain_diagnosis_sha256": sha256(root / DIAGNOSIS),
        },
        "target_contract": {
            "target_count": TARGET_COUNT,
            "target_key_vector": [runtime.target_key(target) for target in runtime.TARGETS],
            "target_key_vector_sha256": payload_sha256(
                [runtime.target_key(target) for target in runtime.TARGETS]
            ),
            "representations": list(runtime.REPRESENTATIONS),
        },
        "execution": {
            "unique_request_count": REQUEST_COUNT,
            "request_url_vector_sha256": payload_sha256([row[2] for row in requests]),
            "workers": WORKERS,
            "attempts_per_url": 1,
            "hard_total_wall_seconds": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "retry_resume_or_selective_rerun": False,
            "attempt_claim_precedes_first_network_call": True,
        },
        "admission": {
            "target_requires_at_least_one_schema_valid_representation": True,
            "dual_valid_requires_common_domain_at_least": runtime.MINIMUM_AGGREGATE_RECORD_COUNT,
            "dual_valid_requires_zero_common_value_mismatch": True,
            "failure_isolated_per_target": True,
            "every_observed_schema_valid_representation_singleton_checked": True,
        },
        "gates": {"required_checks": list(REQUIRED_CHECKS)},
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "protected_watchers": _watchers(),
        "source_policy": dict(SOURCE_POLICY),
        "authorization": {
            "preactivation_audit_generation": True,
            "transport_launch": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value=value)


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = copied.get("dependency_manifest")
    _parents(root)
    requests = _request_vector()
    expected = build_protocol_shape(root, manifest=manifest, requests=requests)
    for key in ("created_at_unix", "protocol_payload_sha256"):
        expected.pop(key, None)
    observed = dict(copied)
    observed.pop("created_at_unix", None)
    observed.pop("protocol_payload_sha256", None)
    if (
        observed != expected
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 protocol drifted")
    return copied


def build_protocol_shape(
    root: Path, *, manifest: object, requests: Sequence[tuple[runtime.FreshTarget, str, str]]
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_preregistration",
        "protocol_id": PROTOCOL_ID,
        "scope": "benchmark_external_fresh_target_dual_representation_resilience_only",
        "parents": {
            "population_design_sha256": sha256(root / DESIGN),
            "failure_domain_diagnosis_sha256": sha256(root / DIAGNOSIS),
        },
        "target_contract": {
            "target_count": TARGET_COUNT,
            "target_key_vector": [runtime.target_key(target) for target in runtime.TARGETS],
            "target_key_vector_sha256": payload_sha256(
                [runtime.target_key(target) for target in runtime.TARGETS]
            ),
            "representations": list(runtime.REPRESENTATIONS),
        },
        "execution": {
            "unique_request_count": REQUEST_COUNT,
            "request_url_vector_sha256": payload_sha256([row[2] for row in requests]),
            "workers": WORKERS,
            "attempts_per_url": 1,
            "hard_total_wall_seconds": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "retry_resume_or_selective_rerun": False,
            "attempt_claim_precedes_first_network_call": True,
        },
        "admission": {
            "target_requires_at_least_one_schema_valid_representation": True,
            "dual_valid_requires_common_domain_at_least": runtime.MINIMUM_AGGREGATE_RECORD_COUNT,
            "dual_valid_requires_zero_common_value_mismatch": True,
            "failure_isolated_per_target": True,
            "every_observed_schema_valid_representation_singleton_checked": True,
        },
        "gates": {"required_checks": list(REQUIRED_CHECKS)},
        "dependency_manifest": dict(manifest) if isinstance(manifest, Mapping) else manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "protected_watchers": _watchers(),
        "source_policy": dict(SOURCE_POLICY),
        "authorization": {
            "preactivation_audit_generation": True,
            "transport_launch": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }


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
    outputs = []
    total = 0
    passed = True
    for suite, expected in TEST_SUITES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", suite.name],
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
    output = "\n".join(outputs)
    return passed and total == EXPECTED_TESTS, total, output


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
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        findings.append("repository_not_clean_pushed_head")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT, OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_preactivation_audit",
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
            "evaluator_imports": imports,
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
            "transport_launch": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_preaudit(value)


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    tests = copied.get("tests", {})
    state = copied.get("runtime_state", {})
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "protocol_sha256",
            "tests",
            "label_blind_audit",
            "runtime_state",
            "findings",
            "audit_valid",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("role") != "v24742_fresh_resilience_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or tests.get("passed") is not True
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("expected") != EXPECTED_TESTS
        or copied.get("label_blind_audit")
        != {"accesses": [], "evaluator_imports": [], "passed": True}
        or state.get("protected_watchers") != _watchers()
        or state.get("shared_api_lease_inactive") is not True
        or state.get("runner_active") is not False
        or not isinstance(findings, list)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "activation_publication": bool(valid),
            "transport_launch": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 preaudit drifted")
    return copied


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    validate_protocol(root)
    preaudit = validate_preaudit(_read(root, PREAUDIT))
    if preaudit.get("audit_valid") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.42 activation is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "protected_watchers": _watchers(),
        "network_model_search_benchmark_forward_or_evaluator_called": False,
        "launch_authorized": True,
        "authorization": {
            "one_transport_launch": True,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return validate_activation(value)


def validate_activation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "protocol_sha256",
            "preactivation_audit_sha256",
            "protected_watchers",
            "network_model_search_benchmark_forward_or_evaluator_called",
            "launch_authorized",
            "authorization",
            "activation_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("role") != "v24742_fresh_resilience_activation"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("network_model_search_benchmark_forward_or_evaluator_called") is not False
        or copied.get("launch_authorized") is not True
        or copied.get("authorization")
        != {
            "one_transport_launch": True,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 activation drifted")
    return copied


def build_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    activation = validate_activation(_read(root, ACTIVATION))
    if activation.get("launch_authorized") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.42 execution start is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "protected_watchers": _watchers(),
        "single_owner_no_retry_resume_or_selective_rerun": True,
        "authorization": {
            "execute_once": True,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
        },
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return validate_start(value)


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "protocol_sha256",
            "activation_sha256",
            "protected_watchers",
            "single_owner_no_retry_resume_or_selective_rerun",
            "authorization",
            "execution_start_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("role") != "v24742_fresh_resilience_execution_start"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("single_owner_no_retry_resume_or_selective_rerun") is not True
        or copied.get("authorization")
        != {
            "execute_once": True,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
        }
        or not _sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 execution start drifted")
    return copied


def build_attempt_claim(*, now: int | None = None) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_attempt_claim",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "unique_request_count": REQUEST_COUNT,
        "attempts_per_url": 1,
        "retry_resume_or_selective_rerun": False,
        "network_model_search_benchmark_forward_or_evaluator_called_before_claim": False,
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
            "retry_resume_or_selective_rerun",
            "network_model_search_benchmark_forward_or_evaluator_called_before_claim",
            "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("role") != "v24742_fresh_resilience_attempt_claim"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("unique_request_count") != REQUEST_COUNT
        or copied.get("attempts_per_url") != 1
        or copied.get("retry_resume_or_selective_rerun") is not False
        or copied.get("network_model_search_benchmark_forward_or_evaluator_called_before_claim") is not False
        or not _sealed(copied, "claim_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 attempt claim drifted")
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
    if url not in helper.ALLOWED_URLS or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("V2.47.42 hard GET input drifted")
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
        stdout, _ = process.communicate(request, timeout=timeout_seconds)
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
        if process.returncode != 0 or not isinstance(value, Mapping) or set(value) != helper.OUTPUT_KEYS:
            raise ValueError("V2.47.42 helper output")
        body = base64.b64decode(value["body_base64"], validate=True) if value["body_base64"] else b""
        if len(body) > runtime.MAX_RESPONSE_BYTES:
            raise ValueError("V2.47.42 helper body")
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


def _request_one(
    indexed: tuple[int, tuple[runtime.FreshTarget, str, str]]
) -> tuple[dict[str, Any], bytes]:
    index, (target, representation, url) = indexed
    response = hard_get(url)
    body = response.pop("body")
    success = (
        response["kind"] == "response"
        and response["status_code"] == 200
        and response["final_url"] == url
        and bool(body)
    )
    receipt = {
        "request_index": index,
        "target_key": runtime.target_key(target),
        "representation": representation,
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "attempts": 1,
        "transport_success": success,
        "failure_type": None if success else response["kind"],
        "http_status": response["status_code"],
        "elapsed_seconds": response["elapsed_seconds"],
        "response_bytes": len(body),
        "raw_sha256": hashlib.sha256(body).hexdigest() if success else None,
        "response_content_persisted": False,
    }
    return receipt, body if success else b""


def _singleton_rows(
    responses: Mapping[str, bytes], target_receipts: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    for target, receipt in zip(runtime.TARGETS, target_receipts, strict=True):
        representation_rows = receipt["representation_receipts"]
        for row in representation_rows:
            if row["schema_valid"] is not True:
                continue
            available = str(row["representation"])
            singleton = {
                runtime.endpoint_url(target, representation): (
                    responses[runtime.endpoint_url(target, representation)]
                    if representation == available
                    else b""
                )
                for representation in runtime.REPRESENTATIONS
            }
            resolved = runtime.reconcile_target(target, singleton)
            singleton_receipt = resolved["receipt"]
            output.append(
                {
                    "target_key": runtime.target_key(target),
                    "available_representation": available,
                    "target_admitted": singleton_receipt["target_admitted"],
                    "selected_representation": singleton_receipt["selected_representation"],
                    "admitted_record_count": singleton_receipt["admitted_record_count"],
                    "response_country_value_or_content_persisted": False,
                }
            )
    return output


def aggregate(
    request_receipts: Sequence[Mapping[str, Any]],
    target_receipts: Sequence[Mapping[str, Any]],
    bundle_receipt: Mapping[str, Any],
    singleton_receipts: Sequence[Mapping[str, Any]],
    *,
    experiment_wall_seconds: float,
    attempt_claim_sha256: str,
    run_summary_sha256: str,
    now: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validated_targets = [runtime.validate_receipt(row) for row in target_receipts]
    validated_bundle = runtime.validate_bundle_receipt(
        bundle_receipt, target_receipts=validated_targets
    )
    valid_representation_count = sum(
        row["schema_valid_representation_count"] for row in validated_targets
    )
    transport_by_pair = {
        (item.get("target_key"), item.get("representation")): item.get(
            "transport_success"
        )
        is True
        for item in request_receipts
    }
    checks = {
        "fixed_four_request_attempt_vector_complete": (
            len(request_receipts) == REQUEST_COUNT
            and {item.get("request_index") for item in request_receipts}
            == set(range(1, REQUEST_COUNT + 1))
            and all(item.get("attempts") == 1 for item in request_receipts)
        ),
        "schema_valid_representations_have_successful_transport": all(
            row["schema_valid"] is not True
            or transport_by_pair.get(
                (target_receipt["target_key"], row["representation"])
            )
            is True
            for target_receipt in validated_targets
            for row in target_receipt["representation_receipts"]
        ),
        "both_targets_admitted_by_at_least_one_schema_valid_representation": (
            validated_bundle["admitted_target_count"] == TARGET_COUNT
            and all(row["schema_valid_representation_count"] >= 1 for row in validated_targets)
        ),
        "all_dual_valid_targets_have_common_value_agreement": all(
            row["schema_valid_representation_count"] != len(runtime.REPRESENTATIONS)
            or (
                row["dual_valid_common_value_agreement"] is True
                and row["dual_valid_consistency_failed"] is False
                and row["comparison"]["common_domain_count"]
                >= runtime.MINIMUM_AGGREGATE_RECORD_COUNT
                and row["comparison"]["common_value_mismatch_count"] == 0
            )
            for row in validated_targets
        ),
        "every_schema_valid_representation_admits_as_singleton": (
            len(singleton_receipts) == valid_representation_count
            and all(
                item.get("target_admitted") is True
                and item.get("selected_representation")
                == item.get("available_representation")
                and item.get("admitted_record_count", 0)
                >= runtime.MINIMUM_AGGREGATE_RECORD_COUNT
                for item in singleton_receipts
            )
        ),
        "target_failure_isolation_contract_valid": (
            validated_bundle["all_target_failures_isolated"] is True
            and all(row["target_failure_isolated"] is True for row in validated_targets)
        ),
        "experiment_wall_within_ceiling": (
            isinstance(experiment_wall_seconds, (int, float))
            and not isinstance(experiment_wall_seconds, bool)
            and math.isfinite(float(experiment_wall_seconds))
            and 0 <= float(experiment_wall_seconds) <= EXPERIMENT_WALL_CEILING_SECONDS
        ),
        "no_response_country_value_or_content_persisted": (
            all(
                item.get("response_content_persisted") is False
                and "body" not in item
                and "url" not in item
                for item in request_receipts
            )
            and all(
                item.get("response_country_value_or_content_persisted") is False
                for item in singleton_receipts
            )
            and validated_bundle["response_country_value_or_content_persisted"] is False
        ),
        "retry_resume_or_selective_rerun_absent": True,
    }
    passed = all(checks[name] for name in REQUIRED_CHECKS)
    result = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "attempt_claim_sha256": attempt_claim_sha256,
        "run_summary_sha256": run_summary_sha256,
        "targets": TARGET_COUNT,
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
        "schema_valid_representations": valid_representation_count,
        "admitted_targets": validated_bundle["admitted_target_count"],
        "experiment_wall_seconds": float(experiment_wall_seconds),
        "request_receipts": [dict(item) for item in request_receipts],
        "target_receipts": validated_targets,
        "bundle_receipt": validated_bundle,
        "singleton_receipts": [dict(item) for item in singleton_receipts],
        "checks": checks,
        "passed": passed,
        "source_policy": dict(SOURCE_POLICY),
    }
    result["result_payload_sha256"] = payload_sha256(result)
    decision = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_payload_sha256": result["result_payload_sha256"],
        "status": "fresh_resilience_go" if passed else "fresh_resilience_no_go",
        "authorization": {
            "fresh_visible_reachability_protocol_design": passed,
            "additional_transport_retry_or_rerun": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    decision["decision_payload_sha256"] = payload_sha256(decision)
    return result, decision


def run_experiment() -> tuple[dict[str, Any], dict[str, Any]]:
    validate_attempt_claim(_read(ROOT, ATTEMPT_CLAIM))
    started = time.monotonic()
    vector = _request_vector()
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        outputs = list(executor.map(_request_one, enumerate(vector, 1)))
    request_receipts = [item[0] for item in outputs]
    responses = {
        row[2]: output[1]
        for row, output in zip(vector, outputs, strict=True)
    }
    resolved = runtime.reconcile_bundle(responses)
    target_receipts = resolved["target_receipts"]
    singleton_receipts = _singleton_rows(responses, target_receipts)
    wall = round(time.monotonic() - started, 6)
    summary = {
        "artifact_version": 1,
        "role": "v24742_fresh_resilience_run_summary",
        "protocol_id": PROTOCOL_ID,
        "attempt_claim_sha256": sha256(ROOT / ATTEMPT_CLAIM),
        "requests": REQUEST_COUNT,
        "request_successes": sum(row["transport_success"] for row in request_receipts),
        "targets": TARGET_COUNT,
        "admitted_targets": resolved["receipt"]["admitted_target_count"],
        "schema_valid_representations": sum(
            row["schema_valid_representation_count"] for row in target_receipts
        ),
        "experiment_wall_seconds": wall,
        "retry_resume_or_selective_rerun": False,
        "response_country_value_or_content_persisted": False,
        "benchmark_forward_or_evaluator_called": False,
    }
    summary["summary_payload_sha256"] = payload_sha256(summary)
    validate_run_summary(
        summary,
        request_receipts=request_receipts,
        target_receipts=target_receipts,
        bundle_receipt=resolved["receipt"],
    )
    _publish(ROOT / RUN_SUMMARY, summary)
    return aggregate(
        request_receipts,
        target_receipts,
        resolved["receipt"],
        singleton_receipts,
        experiment_wall_seconds=wall,
        attempt_claim_sha256=sha256(ROOT / ATTEMPT_CLAIM),
        run_summary_sha256=sha256(ROOT / RUN_SUMMARY),
    )


def _validate_request_receipts(requests: object) -> bool:
    if not isinstance(requests, list) or len(requests) != REQUEST_COUNT:
        return False
    vector = _request_vector()
    return all(
        isinstance(item, Mapping)
        and set(item) == REQUEST_RECEIPT_KEYS
        and item.get("request_index") == index
        and item.get("target_key") == runtime.target_key(target)
        and item.get("representation") == representation
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
            and item.get("response_bytes") == 0
        )
        and item.get("response_content_persisted") is False
        for index, ((target, representation, url), item) in enumerate(
            zip(vector, requests, strict=True), 1
        )
    )


def _validate_singletons(
    singletons: object, targets: Sequence[Mapping[str, Any]]
) -> bool:
    if not isinstance(singletons, list):
        return False
    expected = []
    for target_receipt in targets:
        for row in target_receipt["representation_receipts"]:
            if row["schema_valid"] is True:
                expected.append(
                    {
                        "target_key": target_receipt["target_key"],
                        "available_representation": row["representation"],
                        "target_admitted": True,
                        "selected_representation": row["representation"],
                        "admitted_record_count": row["record_count"],
                        "response_country_value_or_content_persisted": False,
                    }
                )
    return len(singletons) == len(expected) and all(
        isinstance(item, Mapping)
        and set(item) == SINGLETON_RECEIPT_KEYS
        and dict(item) == row
        for item, row in zip(singletons, expected, strict=True)
    )


def validate_run_summary(
    value: Mapping[str, Any],
    *,
    request_receipts: Sequence[Mapping[str, Any]],
    target_receipts: Sequence[Mapping[str, Any]],
    bundle_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    copied = dict(value)
    validated_targets = [runtime.validate_receipt(item) for item in target_receipts]
    validated_bundle = runtime.validate_bundle_receipt(
        bundle_receipt, target_receipts=validated_targets
    )
    wall = copied.get("experiment_wall_seconds")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "attempt_claim_sha256",
            "requests",
            "request_successes",
            "targets",
            "admitted_targets",
            "schema_valid_representations",
            "experiment_wall_seconds",
            "retry_resume_or_selective_rerun",
            "response_country_value_or_content_persisted",
            "benchmark_forward_or_evaluator_called",
            "summary_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24742_fresh_resilience_run_summary"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("attempt_claim_sha256") != sha256(ROOT / ATTEMPT_CLAIM)
        or copied.get("requests") != REQUEST_COUNT
        or copied.get("request_successes")
        != sum(item.get("transport_success") is True for item in request_receipts)
        or copied.get("targets") != TARGET_COUNT
        or copied.get("admitted_targets")
        != validated_bundle["admitted_target_count"]
        or copied.get("schema_valid_representations")
        != sum(
            item["schema_valid_representation_count"] for item in validated_targets
        )
        or not isinstance(wall, (int, float))
        or isinstance(wall, bool)
        or not math.isfinite(float(wall))
        or float(wall) < 0
        or copied.get("retry_resume_or_selective_rerun") is not False
        or copied.get("response_country_value_or_content_persisted") is not False
        or copied.get("benchmark_forward_or_evaluator_called") is not False
        or not _sealed(copied, "summary_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 run summary drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    requests = copied.get("request_receipts")
    targets = copied.get("target_receipts")
    bundle = copied.get("bundle_receipt")
    singletons = copied.get("singleton_receipts")
    checks = copied.get("checks")
    if not isinstance(targets, list) or len(targets) != TARGET_COUNT:
        raise RuntimeError("V2.47.42 target receipts absent")
    validated_targets = [runtime.validate_receipt(item) for item in targets]
    validated_bundle = runtime.validate_bundle_receipt(
        bundle if isinstance(bundle, Mapping) else {}, target_receipts=validated_targets
    )
    if not _validate_request_receipts(requests) or not _validate_singletons(singletons, validated_targets):
        raise RuntimeError("V2.47.42 content-free receipt vector drifted")
    validate_attempt_claim(_read(ROOT, ATTEMPT_CLAIM))
    summary = validate_run_summary(
        _read(ROOT, RUN_SUMMARY),
        request_receipts=requests,
        target_receipts=validated_targets,
        bundle_receipt=validated_bundle,
    )
    recomputed, _decision = aggregate(
        requests,
        validated_targets,
        validated_bundle,
        singletons,
        experiment_wall_seconds=copied.get("experiment_wall_seconds"),
        attempt_claim_sha256=str(copied.get("attempt_claim_sha256")),
        run_summary_sha256=str(copied.get("run_summary_sha256")),
        now=int(copied.get("created_at_unix", 0)),
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "execution_start_sha256",
            "attempt_claim_sha256",
            "run_summary_sha256",
            "targets",
            "unique_requests",
            "request_successes",
            "request_failure_type_counts",
            "schema_valid_representations",
            "admitted_targets",
            "experiment_wall_seconds",
            "request_receipts",
            "target_receipts",
            "bundle_receipt",
            "singleton_receipts",
            "checks",
            "passed",
            "source_policy",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("role") != "v24742_fresh_resilience_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("attempt_claim_sha256") != sha256(ROOT / ATTEMPT_CLAIM)
        or copied.get("run_summary_sha256") != sha256(ROOT / RUN_SUMMARY)
        or copied.get("experiment_wall_seconds")
        != summary.get("experiment_wall_seconds")
        or copied.get("targets") != TARGET_COUNT
        or copied.get("unique_requests") != REQUEST_COUNT
        or copied.get("request_successes")
        != sum(item.get("transport_success") is True for item in requests)
        or copied.get("request_failure_type_counts")
        != dict(
            sorted(
                Counter(
                    str(item.get("failure_type"))
                    for item in requests
                    if item.get("transport_success") is not True
                ).items()
            )
        )
        or copied.get("schema_valid_representations")
        != sum(item["schema_valid_representation_count"] for item in validated_targets)
        or copied.get("admitted_targets") != validated_bundle["admitted_target_count"]
        or dict(checks) != recomputed["checks"]
        or copied.get("passed") is not recomputed["passed"]
        or copied.get("source_policy") != SOURCE_POLICY
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 result drifted")
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
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("role") != "v24742_fresh_resilience_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_payload_sha256") != result.get("result_payload_sha256")
        or copied.get("status")
        != ("fresh_resilience_go" if passed else "fresh_resilience_no_go")
        or copied.get("authorization")
        != {
            "fresh_visible_reachability_protocol_design": passed,
            "additional_transport_retry_or_rerun": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 decision drifted")
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
        "role": "v24742_fresh_resilience_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision.get("status"),
        "protected_watchers": _watchers(),
        "shared_api_lease_inactive": _lease_inactive(root),
        "response_body_country_value_or_content_opened_by_audit": False,
        "benchmark_manifest_mapping_gold_or_evaluator_opened_by_audit": False,
        "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "additional_transport_retry_or_rerun": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_postaudit(value)


def validate_postaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "result_sha256",
            "decision_sha256",
            "decision_status",
            "protected_watchers",
            "shared_api_lease_inactive",
            "response_body_country_value_or_content_opened_by_audit",
            "benchmark_manifest_mapping_gold_or_evaluator_opened_by_audit",
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit",
            "findings",
            "audit_valid",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24742_fresh_resilience_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("decision_sha256") != sha256(ROOT / DECISION)
        or copied.get("decision_status")
        not in {"fresh_resilience_go", "fresh_resilience_no_go"}
        or copied.get("protected_watchers") != _watchers()
        or copied.get("shared_api_lease_inactive") is not True
        or copied.get("response_body_country_value_or_content_opened_by_audit")
        is not False
        or copied.get("benchmark_manifest_mapping_gold_or_evaluator_opened_by_audit")
        is not False
        or copied.get(
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit"
        )
        is not False
        or not isinstance(findings, list)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "additional_transport_retry_or_rerun": False,
            "benchmark_forward": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.42 postresult audit drifted")
    return copied


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
        raise RuntimeError("V2.47.42 run surface is unsafe")
    with acquire_deepwide_api_lease(
        ROOT, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=ROOT / LEASE_PATH
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
            "usage: v24742_fresh_resilience_gate.py "
            "{protocol|preaudit|activate|start|run|postaudit}"
        )
    COMMANDS[sys.argv[1]]()
