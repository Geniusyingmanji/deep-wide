#!/usr/bin/env python3
"""Fresh-population bulk-primary World Bank transport gate."""

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
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as runtime  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts import design_v24723_fresh_indicator_population as design  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24726_fresh_indicator_bulk_primary_transport_v1"
PROTOCOL = Path(f"results/v24726_fresh_bulk_transport_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24726_fresh_bulk_transport_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24726_fresh_bulk_transport_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24726_fresh_bulk_transport_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24726_fresh_bulk_transport_result_v1_{DATE}.json")
DECISION = Path(f"results/v24726_fresh_bulk_transport_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24726_fresh_bulk_transport_postresult_audit_v1_{DATE}.json")
DESIGN = design.OUTPUT
DIAGNOSIS = Path(f"results/v24722_v24721_transport_diagnosis_v1_{DATE}.json")
HELPER = Path("scripts/v24725_public_get_helper.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v24724_fresh_indicator_transport.py")
RUNTIME_TEST = Path("tests/test_v24724_fresh_indicator_transport.py")
HELPER_TEST = Path("tests/test_v24725_public_get_helper.py")
DESIGN_TEST = Path("tests/test_design_v24723_fresh_indicator_population.py")
SCRIPT = Path("scripts/v24726_fresh_bulk_transport_gate.py")
SCRIPT_TEST = Path("tests/test_v24726_fresh_bulk_transport_gate.py")
LEASE_SOURCE = Path("scripts/deepwide_api_lease.py")
SOURCES = (
    RUNTIME_SOURCE,
    HELPER,
    RUNTIME_TEST,
    HELPER_TEST,
    SCRIPT,
    SCRIPT_TEST,
    LEASE_SOURCE,
    DESIGN,
    DIAGNOSIS,
)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24726_fresh_bulk_transport_gate_v1"
LEASE_PURPOSE = "benchmark_external_fresh_indicator_bulk_primary_transport"
RUNNER_MARKER = "scripts/v24726_fresh_bulk_transport_gate.py run"
WAVES = 2
REQUESTS_PER_WAVE = len(runtime.TARGETS) * len(runtime.REPRESENTATIONS)
TOTAL_REQUESTS = WAVES * REQUESTS_PER_WAVE
PRIMARY_REQUESTS = WAVES * len(runtime.TARGETS)
WORKERS = REQUESTS_PER_WAVE
HARD_WALL_SECONDS = 20.0
SOCKET_TIMEOUT_SECONDS = 15.0
WAVE_WALL_CEILING_SECONDS = 25.0
EXPERIMENT_WALL_CEILING_SECONDS = 55.0
EXPECTED_TESTS = 15
TEST_SUITES = (
    (RUNTIME_TEST, 4),
    (HELPER_TEST, 2),
    (DESIGN_TEST, 3),
    (SCRIPT_TEST, 6),
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
REQUIRED_CHECKS = (
    "primary_all_requests_http_200_and_schema_valid",
    "primary_semantic_stable_across_waves",
    "primary_record_count_at_least_260",
    "common_domain_values_agree_when_comparator_succeeds",
    "domain_projection_is_content_free",
    "all_wave_walls_within_ceiling",
    "experiment_wall_within_ceiling",
    "no_response_content_persisted",
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
        raise RuntimeError(f"V2.47.26 expected repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.26 expected object")
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
        raise RuntimeError("V2.47.26 requires clean pushed HEAD")


def _watchers() -> list[dict[str, Any]]:
    output = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
        ticks = int(raw[raw.rfind(")") + 2 :].split()[19])
        cmdline = (
            (Path("/proc") / str(pid) / "cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode(errors="replace")
        )
        if ticks != expected_ticks or marker not in cmdline:
            raise RuntimeError("V2.47.26 protected watcher drifted")
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
    return any(RUNNER_MARKER in line for line in completed.stdout.splitlines())


def _manifest(root: Path) -> dict[str, str]:
    output = {}
    for relative in SOURCES:
        path = _ordinary(root, relative)
        if root.resolve() == ROOT.resolve() and not _tracked(relative):
            raise RuntimeError(f"V2.47.26 untracked source: {relative}")
        raw = path.read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.26 credential literal found")
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
                if any(
                    marker in name.casefold()
                    for marker in ("official_eval", "evaluator_mapping", "finalize_v24")
                ):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _parents(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    design_value = design.validate_design(_read(root, DESIGN))
    diagnosis = _read(root, DIAGNOSIS)
    if (
        design_value.get("authorization", {}).get(
            "fresh_bulk_primary_transport_protocol_design"
        )
        is not True
        or design_value.get("authorization", {}).get("transport_launch") is not False
        or diagnosis.get("role")
        != "v24722_v24721_transport_postterminal_diagnosis"
        or diagnosis.get("authorization", {}).get("fresh_indicator_population_design")
        is not True
        or diagnosis.get("authorization", {}).get(
            "same_population_transport_retry_or_rerun"
        )
        is not False
        or not _sealed(diagnosis, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.47.26 parent chain drifted")
    selected = [
        item["target_key"]
        for item in design_value["selection"]["selected_targets"]
    ]
    if selected != [runtime.target_key(item) for item in runtime.TARGETS]:
        raise RuntimeError("V2.47.26 runtime/design target mismatch")
    return design_value, diagnosis


def _target_vector() -> list[dict[str, Any]]:
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


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    _parents(root)
    manifest = _manifest(root)
    vector = _target_vector()
    value = {
        "artifact_version": 1,
        "role": "v24726_fresh_bulk_transport_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "benchmark_external_fresh_indicator_transport_only",
        "parents": {
            "design_sha256": sha256(root / DESIGN),
            "diagnosis_sha256": sha256(root / DIAGNOSIS),
        },
        "target_selection": {
            "selected_before_any_v24726_transport_outcome": True,
            "target_count": len(vector),
            "target_vector": vector,
            "target_vector_sha256": payload_sha256(vector),
        },
        "execution": {
            "waves": WAVES,
            "representations": list(runtime.REPRESENTATIONS),
            "primary_representation": runtime.PRIMARY_REPRESENTATION,
            "diagnostic_comparator_representation": runtime.COMPARATOR_REPRESENTATION,
            "requests_per_wave": REQUESTS_PER_WAVE,
            "total_requests": TOTAL_REQUESTS,
            "primary_requests": PRIMARY_REQUESTS,
            "workers": WORKERS,
            "attempts_per_endpoint_per_wave": 1,
            "hard_total_wall_seconds": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "wave_wall_ceiling_seconds": WAVE_WALL_CEILING_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "cache_resume_retry_or_selective_rerun": False,
        },
        "gates": {
            "required_checks": list(REQUIRED_CHECKS),
            "diagnostic_checks": [
                "comparator_all_requests_http_200_and_schema_valid"
            ],
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "protected_watchers": _watchers(),
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


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = copied.get("dependency_manifest")
    selection = copied.get("target_selection", {})
    execution = copied.get("execution", {})
    if (
        copied.get("role") != "v24726_fresh_bulk_transport_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope") != "benchmark_external_fresh_indicator_transport_only"
        or copied.get("parents")
        != {
            "design_sha256": sha256(root / DESIGN),
            "diagnosis_sha256": sha256(root / DIAGNOSIS),
        }
        or selection.get("selected_before_any_v24726_transport_outcome") is not True
        or selection.get("target_count") != len(runtime.TARGETS)
        or selection.get("target_vector") != _target_vector()
        or selection.get("target_vector_sha256") != payload_sha256(_target_vector())
        or execution
        != {
            "waves": WAVES,
            "representations": list(runtime.REPRESENTATIONS),
            "primary_representation": runtime.PRIMARY_REPRESENTATION,
            "diagnostic_comparator_representation": runtime.COMPARATOR_REPRESENTATION,
            "requests_per_wave": REQUESTS_PER_WAVE,
            "total_requests": TOTAL_REQUESTS,
            "primary_requests": PRIMARY_REQUESTS,
            "workers": WORKERS,
            "attempts_per_endpoint_per_wave": 1,
            "hard_total_wall_seconds": HARD_WALL_SECONDS,
            "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
            "wave_wall_ceiling_seconds": WAVE_WALL_CEILING_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "cache_resume_retry_or_selective_rerun": False,
        }
        or copied.get("gates")
        != {
            "required_checks": list(REQUIRED_CHECKS),
            "diagnostic_checks": [
                "comparator_all_requests_http_200_and_schema_valid"
            ],
        }
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("protected_watchers") != _watchers()
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "transport_launch": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.26 protocol drifted")
    return copied


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
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        findings.append("repository_not_clean_pushed_head")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24726_fresh_bulk_transport_preactivation_audit",
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
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
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
        copied.get("role")
        != "v24726_fresh_bulk_transport_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or tests.get("passed") is not True
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("expected") != EXPECTED_TESTS
        or not isinstance(tests.get("output_sha256"), str)
        or len(tests["output_sha256"]) != 64
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
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.26 preaudit drifted")
    return copied


def _stage(
    value: Mapping[str, Any], *, role: str, seal: str
) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != role
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or not _sealed(copied, seal)
    ):
        raise RuntimeError(f"V2.47.26 {role} drifted")
    return copied


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    validate_protocol(root)
    preaudit = validate_preaudit(_read(root, PREAUDIT))
    if preaudit.get("audit_valid") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.26 activation is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24726_fresh_bulk_transport_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "protected_watchers": _watchers(),
        "network_model_search_fetch_evaluator_or_api_called": False,
        "launch_authorized": True,
        "authorization": {
            "one_transport_launch": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    validate_activation(value)
    return value


def validate_activation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _stage(
        value,
        role="v24726_fresh_bulk_transport_activation",
        seal="activation_payload_sha256",
    )
    if (
        copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("protected_watchers") != _watchers()
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
        raise RuntimeError("V2.47.26 activation drifted")
    return copied


def build_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    activation = validate_activation(_read(root, ACTIVATION))
    if activation.get("launch_authorized") is not True or not _lease_inactive(root) or _runner_active():
        raise RuntimeError("V2.47.26 execution start is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24726_fresh_bulk_transport_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "protected_watchers": _watchers(),
        "single_owner_no_resume_retry_or_selective_rerun": True,
        "authorization": {
            "execute_once": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    validate_start(value)
    return value


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _stage(
        value,
        role="v24726_fresh_bulk_transport_execution_start",
        seal="execution_start_payload_sha256",
    )
    if (
        copied.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("single_owner_no_resume_retry_or_selective_rerun") is not True
        or copied.get("authorization")
        != {
            "execute_once": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
        }
    ):
        raise RuntimeError("V2.47.26 execution-start drifted")
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
    allowed = {
        runtime.endpoint_url(target, representation)
        for target in runtime.TARGETS
        for representation in runtime.REPRESENTATIONS
    }
    if url not in allowed or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("V2.47.26 hard GET input drifted")
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
        if (
            process.returncode != 0
            or not isinstance(value, Mapping)
            or set(value)
            != {"kind", "status_code", "content_type", "final_url", "body_base64"}
        ):
            raise ValueError("helper output")
        body = (
            base64.b64decode(value["body_base64"], validate=True)
            if value["body_base64"]
            else b""
        )
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
    wave: int, target: runtime.FreshTarget, representation: str
) -> tuple[dict[str, Any], Mapping[str, Any] | None]:
    url = runtime.endpoint_url(target, representation)
    response = hard_get(url)
    raw = response.pop("body")
    records: Mapping[str, Any] | None = None
    meta: dict[str, Any] | None = None
    failure = response["kind"]
    if (
        response["kind"] == "response"
        and response["status_code"] == 200
        and response["final_url"] == url
    ):
        try:
            meta = runtime.parse_response(
                raw, target=target, representation=representation
            )
            records, _updated = runtime.parse_records(
                raw, target=target, representation=representation
            )
            failure = None
        except ValueError:
            failure = "schema_invalid"
    success = meta is not None and records is not None
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
        "raw_sha256": meta["raw_sha256"] if meta else None,
        "semantic_sha256": meta["semantic_sha256"] if meta else None,
        "record_count": meta["record_count"] if meta else 0,
        "non_null_count": meta["non_null_count"] if meta else 0,
        "response_country_value_or_content_persisted": False,
    }
    return receipt, records


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
        records_by_target: dict[str, dict[str, Mapping[str, Any]]] = {}
        for receipt, records in outputs:
            receipts.append(receipt)
            if receipt["success"] and records is not None:
                records_by_target.setdefault(receipt["target_key"], {})[
                    receipt["representation"]
                ] = records
        for target in runtime.TARGETS:
            key = runtime.target_key(target)
            vector = records_by_target.get(key, {})
            if set(vector) == set(runtime.REPRESENTATIONS):
                comparisons.append(
                    {
                        "wave": wave,
                        "target_key": key,
                        **runtime.compare_domains(
                            vector[runtime.PRIMARY_REPRESENTATION],
                            vector[runtime.COMPARATOR_REPRESENTATION],
                        ),
                    }
                )
    wall = round(time.monotonic() - started, 6)
    primary = [
        item
        for item in receipts
        if item["representation"] == runtime.PRIMARY_REPRESENTATION
    ]
    comparator = [
        item
        for item in receipts
        if item["representation"] == runtime.COMPARATOR_REPRESENTATION
    ]
    semantics: dict[str, set[str]] = {}
    for item in primary:
        if item["success"]:
            semantics.setdefault(item["target_key"], set()).add(
                item["semantic_sha256"]
            )
    checks = {
        "primary_all_requests_http_200_and_schema_valid": all(
            item["success"] for item in primary
        )
        and len(primary) == PRIMARY_REQUESTS,
        "primary_semantic_stable_across_waves": all(
            len(semantics.get(runtime.target_key(target), set())) == 1
            and sum(
                item["success"]
                and item["target_key"] == runtime.target_key(target)
                for item in primary
            )
            == WAVES
            for target in runtime.TARGETS
        ),
        "primary_record_count_at_least_260": all(
            item["success"]
            and item["record_count"] >= runtime.MINIMUM_PRIMARY_RECORD_COUNT
            for item in primary
        )
        and len(primary) == PRIMARY_REQUESTS,
        "common_domain_values_agree_when_comparator_succeeds": all(
            item["common_value_mismatch_count"] == 0 for item in comparisons
        ),
        "domain_projection_is_content_free": all(
            item["content_persisted"] is False for item in comparisons
        ),
        "all_wave_walls_within_ceiling": all(
            value <= WAVE_WALL_CEILING_SECONDS for value in wave_walls
        ),
        "experiment_wall_within_ceiling": wall
        <= EXPERIMENT_WALL_CEILING_SECONDS,
        "no_response_content_persisted": all(
            item["response_country_value_or_content_persisted"] is False
            for item in receipts
        ),
        "comparator_all_requests_http_200_and_schema_valid": all(
            item["success"] for item in comparator
        )
        and len(comparator) == PRIMARY_REQUESTS,
    }
    passed = all(checks[name] for name in REQUIRED_CHECKS)
    result = {
        "artifact_version": 1,
        "role": "v24726_fresh_bulk_transport_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "waves": WAVES,
        "requests": TOTAL_REQUESTS,
        "primary_requests": len(primary),
        "primary_successes": sum(item["success"] for item in primary),
        "comparator_requests": len(comparator),
        "comparator_successes": sum(item["success"] for item in comparator),
        "failure_type_counts": dict(
            sorted(
                Counter(
                    str(item["failure_type"])
                    for item in receipts
                    if not item["success"]
                ).items()
            )
        ),
        "wave_wall_seconds": wave_walls,
        "experiment_wall_seconds": wall,
        "receipts": receipts,
        "domain_comparisons": comparisons,
        "checks": checks,
        "passed": passed,
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
        "role": "v24726_fresh_bulk_transport_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "result_payload_sha256": result["result_payload_sha256"],
        "status": "transport_go" if passed else "transport_no_go",
        "authorization": {
            "generic_reachability_candidate_design": passed,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "additional_transport_retry_or_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    decision["decision_payload_sha256"] = payload_sha256(decision)
    return result, decision


def _expected_receipt_pairs() -> set[tuple[int, str, str]]:
    return {
        (wave, runtime.target_key(target), representation)
        for wave in range(1, WAVES + 1)
        for target in runtime.TARGETS
        for representation in runtime.REPRESENTATIONS
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    receipts = copied.get("receipts")
    comparisons = copied.get("domain_comparisons")
    checks = copied.get("checks")
    if not isinstance(receipts, list) or not isinstance(comparisons, list):
        raise RuntimeError("V2.47.26 result vectors absent")
    pairs = {
        (item.get("wave"), item.get("target_key"), item.get("representation"))
        for item in receipts
        if isinstance(item, Mapping)
    }
    primary = [
        item
        for item in receipts
        if isinstance(item, Mapping)
        and item.get("representation") == runtime.PRIMARY_REPRESENTATION
    ]
    comparator = [
        item
        for item in receipts
        if isinstance(item, Mapping)
        and item.get("representation") == runtime.COMPARATOR_REPRESENTATION
    ]
    semantics: dict[str, set[str]] = {}
    for item in primary:
        if item.get("success") is True and isinstance(item.get("semantic_sha256"), str):
            semantics.setdefault(str(item["target_key"]), set()).add(
                str(item["semantic_sha256"])
            )
    expected_comparison_pairs = {
        (wave, runtime.target_key(target))
        for wave in range(1, WAVES + 1)
        for target in runtime.TARGETS
        if all(
            any(
                item.get("wave") == wave
                and item.get("target_key") == runtime.target_key(target)
                and item.get("representation") == representation
                and item.get("success") is True
                for item in receipts
            )
            for representation in runtime.REPRESENTATIONS
        )
    }
    wave_walls = copied.get("wave_wall_seconds")
    recomputed = {
        "primary_all_requests_http_200_and_schema_valid": len(primary)
        == PRIMARY_REQUESTS
        and all(item.get("success") is True for item in primary),
        "primary_semantic_stable_across_waves": all(
            len(semantics.get(runtime.target_key(target), set())) == 1
            and sum(
                item.get("success") is True
                and item.get("target_key") == runtime.target_key(target)
                for item in primary
            )
            == WAVES
            for target in runtime.TARGETS
        ),
        "primary_record_count_at_least_260": len(primary) == PRIMARY_REQUESTS
        and all(
            item.get("success") is True
            and item.get("record_count", 0)
            >= runtime.MINIMUM_PRIMARY_RECORD_COUNT
            for item in primary
        ),
        "common_domain_values_agree_when_comparator_succeeds": {
            (item.get("wave"), item.get("target_key"))
            for item in comparisons
            if isinstance(item, Mapping)
        }
        == expected_comparison_pairs
        and all(
            item.get("common_value_mismatch_count") == 0
            for item in comparisons
        ),
        "domain_projection_is_content_free": all(
            item.get("content_persisted") is False for item in comparisons
        ),
        "all_wave_walls_within_ceiling": isinstance(wave_walls, list)
        and len(wave_walls) == WAVES
        and all(
            isinstance(number, (int, float))
            and not isinstance(number, bool)
            and math.isfinite(float(number))
            and 0 <= float(number) <= WAVE_WALL_CEILING_SECONDS
            for number in wave_walls
        ),
        "experiment_wall_within_ceiling": isinstance(
            copied.get("experiment_wall_seconds"), (int, float)
        )
        and not isinstance(copied.get("experiment_wall_seconds"), bool)
        and 0
        <= float(copied["experiment_wall_seconds"])
        <= EXPERIMENT_WALL_CEILING_SECONDS,
        "no_response_content_persisted": all(
            item.get("response_country_value_or_content_persisted") is False
            for item in receipts
        ),
        "comparator_all_requests_http_200_and_schema_valid": len(comparator)
        == PRIMARY_REQUESTS
        and all(item.get("success") is True for item in comparator),
    }
    if (
        copied.get("role") != "v24726_fresh_bulk_transport_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
        or copied.get("waves") != WAVES
        or copied.get("requests") != TOTAL_REQUESTS
        or len(receipts) != TOTAL_REQUESTS
        or pairs != _expected_receipt_pairs()
        or any(
            not isinstance(item, Mapping)
            or item.get("attempts") != 1
            or not isinstance(item.get("success"), bool)
            or item.get("response_country_value_or_content_persisted") is not False
            or item.get("url_sha256")
            != hashlib.sha256(
                runtime.endpoint_url(
                    runtime.resolve_target(item.get("indicator"), item.get("year")),
                    str(item.get("representation")),
                ).encode()
            ).hexdigest()
            or item.get("success")
            is not (
                item.get("failure_type") is None
                and item.get("http_status") == 200
                and isinstance(item.get("raw_sha256"), str)
                and isinstance(item.get("semantic_sha256"), str)
                and item.get("record_count", 0)
                >= (
                    runtime.MINIMUM_PRIMARY_RECORD_COUNT
                    if item.get("representation")
                    == runtime.PRIMARY_REPRESENTATION
                    else runtime.MINIMUM_COMPARATOR_RECORD_COUNT
                )
            )
            for item in receipts
        )
        or copied.get("primary_requests") != len(primary)
        or copied.get("primary_successes")
        != sum(item["success"] for item in primary)
        or copied.get("comparator_requests") != len(comparator)
        or copied.get("comparator_successes")
        != sum(item["success"] for item in comparator)
        or not isinstance(checks, Mapping)
        or dict(checks) != recomputed
        or copied.get("passed")
        is not all(recomputed[name] for name in REQUIRED_CHECKS)
        or any(copied.get("source_policy", {}).values())
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.26 result drifted")
    return copied


def validate_decision(
    value: Mapping[str, Any], *, result: Mapping[str, Any]
) -> dict[str, Any]:
    copied = dict(value)
    passed = result.get("passed") is True
    if (
        copied.get("role") != "v24726_fresh_bulk_transport_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("result_payload_sha256") != result.get("result_payload_sha256")
        or copied.get("status")
        != ("transport_go" if passed else "transport_no_go")
        or copied.get("authorization")
        != {
            "generic_reachability_candidate_design": passed,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "additional_transport_retry_or_rerun": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.47.26 decision drifted")
    return copied


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    findings = []
    try:
        result = validate_result(_read(root, RESULT))
    except (RuntimeError, TypeError, ValueError):
        result = _read(root, RESULT)
        findings.append("result_invalid")
    try:
        decision_value = validate_decision(_read(root, DECISION), result=result)
    except (RuntimeError, TypeError, ValueError):
        decision_value = _read(root, DECISION)
        findings.append("decision_invalid")
    if not _lease_inactive(root):
        findings.append("shared_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24726_fresh_bulk_transport_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision_value.get("status"),
        "protected_watchers": _watchers(),
        "shared_api_lease_inactive": _lease_inactive(root),
        "network_model_search_benchmark_forward_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "additional_transport_retry_or_rerun": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
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
    if (ROOT / RESULT).exists() or (ROOT / DECISION).exists() or not _lease_inactive(ROOT):
        raise RuntimeError("V2.47.26 run surface is unsafe")
    with acquire_deepwide_api_lease(
        ROOT, owner=LEASE_OWNER, purpose=LEASE_PURPOSE
    ):
        result, decision_value = run_experiment()
        validate_result(result)
        validate_decision(decision_value, result=result)
        _publish(ROOT / RESULT, result)
        _publish(ROOT / DECISION, decision_value)


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
            "usage: v24726_fresh_bulk_transport_gate.py "
            "{protocol|preaudit|activate|start|run|postaudit}"
        )
    COMMANDS[sys.argv[1]]()
