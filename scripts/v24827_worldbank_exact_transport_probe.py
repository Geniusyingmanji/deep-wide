#!/usr/bin/env python3
"""Frozen, content-free probe for the V2.48.26 exact World Bank transport.

The probe uses one fixed benchmark-external ``WLD`` endpoint twice.  Protocol,
preactivation audit, activation, and execution-start artifacts must each be
published from a clean pushed commit before ``run`` can create a network
effect.  The helper response is validated in memory and immediately discarded;
the result persists only status/count/latency metadata.
"""

from __future__ import annotations

import ast
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
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24826_worldbank_exact_api_transport import (  # noqa: E402
    EXACT_TARGET_TOTAL_WALL_SECONDS,
    exact_target_key,
    payload_sha256,
    validate_helper_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260807"
PROTOCOL_ID = "v24827_fixed_wld_exact_transport_probe_v1"
PROTOCOL = Path(
    f"results/v24827_worldbank_exact_transport_probe_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24827_worldbank_exact_transport_probe_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24827_worldbank_exact_transport_probe_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24827_worldbank_exact_transport_probe_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24827_worldbank_exact_transport_probe_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24827_worldbank_exact_transport_probe_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24826_worldbank_exact_api_transport_build_audit_v1_{DATE}.json"
)
RUNTIME = Path("src/deepwide_agent/v24826_worldbank_exact_api_transport.py")
HELPER = Path("scripts/run_v24826_worldbank_exact_fetch_helper.py")
SCRIPT = Path("scripts/v24827_worldbank_exact_transport_probe.py")
TEST = Path("tests/test_v24827_worldbank_exact_transport_probe.py")
SOURCES = (PARENT, RUNTIME, HELPER, SCRIPT, TEST)

# WLD is an aggregate entity and is deliberately outside the country rows used
# by the external table populations.  The literal is frozen before any probe
# outcome and is not selected from benchmark feedback.
PROBE_URL = (
    "https://api.worldbank.org/v2/country/WLD/indicator/"
    "SP.POP.TOTL?date=2023&format=json&per_page=100"
)
PROBE_TARGET_KEY = "WLD|SP.POP.TOTL|2023"
WAVES = 2
REQUESTS = WAVES
PER_WAVE_WALL_CEILING_SECONDS = 51.0
EXPERIMENT_WALL_CEILING_SECONDS = 103.0
EXPECTED_TESTS = 7
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24827_worldbank_exact_transport_probe_v1"
LEASE_PURPOSE = "benchmark_external_content_free_exact_transport_probe"

PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
PRIVILEGED = frozenset(
    {
        "answer_key",
        "benchmark_question_type",
        "category",
        "evaluator",
        "gold",
        "ground_truth",
        "mapping",
        "question",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
EVALUATOR_MARKERS = (
    "official_eval",
    "official_evaluator",
    "external_evaluator",
    "evaluator_mapping",
    "finalize_v24",
)
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


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.48.27 expected repository file: {relative}")
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
        raise RuntimeError("V2.48.27 expected JSON object")
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
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
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
        raise RuntimeError("V2.48.27 requires clean pushed HEAD")


def _require_absent(paths: Sequence[Path]) -> None:
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in paths):
        raise RuntimeError("V2.48.27 future artifact surface is not pristine")


def _watchers() -> list[dict[str, Any]]:
    output = []
    for pid, expected_ticks, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.27 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(
            errors="replace"
        )
        if len(suffix) <= 19 or int(suffix[19]) != expected_ticks or marker not in command:
            raise RuntimeError("V2.48.27 protected watcher drifted")
        output.append(
            {"pid": pid, "start_ticks": expected_ticks, "marker": marker}
        )
    return output


def _lease_inactive(root: Path = ROOT) -> bool:
    path = root / LEASE_PATH
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


def _runner_active() -> bool:
    expected = (ROOT / SCRIPT).resolve()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            tokens = [
                item.decode(errors="replace")
                for item in (entry / "cmdline").read_bytes().split(b"\0")
                if item
            ]
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if not tokens or tokens[-1] != "run":
            continue
        for token in tokens:
            try:
                if Path(token).resolve() == expected:
                    return True
            except (OSError, ValueError):
                continue
    return False


def _parent_valid(root: Path = ROOT) -> bool:
    value = _read(root, PARENT)
    return bool(
        value.get("role")
        == "v24826_worldbank_exact_api_transport_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "non_evaluation_transport_probe_design"
        )
        is True
        and value.get("authorization", {}).get("public_exact220") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _manifest(root: Path = ROOT) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = _ordinary(root, relative)
        if root.resolve() == ROOT.resolve() and not _tracked(relative):
            raise RuntimeError(f"V2.48.27 untracked source: {relative}")
        raw = path.read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.48.27 credential literal in source surface")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def ast_findings(root: Path = ROOT) -> tuple[list[str], list[str]]:
    accesses: list[str] = []
    imports: list[str] = []
    for relative in (RUNTIME, HELPER, SCRIPT):
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
                key = node.args[0].value.casefold()
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value.casefold()
            if key in PRIVILEGED:
                accesses.append(f"{relative}:{node.lineno}:{key}")
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or "", *(alias.name for alias in node.names)]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    if not _parent_valid(root) or exact_target_key(PROBE_URL) != PROBE_TARGET_KEY:
        raise RuntimeError("V2.48.27 parent or fixed target drifted")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24827_worldbank_exact_transport_probe_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "benchmark_external_fixed_wld_transport_only",
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "target": {
            "selection_rule": "fixed_wld_population_total_2023_before_any_probe_outcome",
            "selected_after_transport_outcome": False,
            "benchmark_task_or_country_row": False,
            "url": PROBE_URL,
            "target_key": PROBE_TARGET_KEY,
        },
        "execution": {
            "waves": WAVES,
            "requests": REQUESTS,
            "sequential": True,
            "helper_attempt_cap": 3,
            "helper_hard_total_wall_seconds": EXACT_TARGET_TOTAL_WALL_SECONDS,
            "per_wave_wall_ceiling_seconds": PER_WAVE_WALL_CEILING_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "cache_resume_retry_skip_or_selective_rerun": False,
            "helper_bounded_retry_inside_each_frozen_request": True,
        },
        "gates": {
            "required": [
                "exact_request_count",
                "all_waves_terminal_success",
                "every_wave_has_http_200",
                "every_wave_has_positive_response_bytes",
                "all_wave_walls_within_ceiling",
                "experiment_wall_within_ceiling",
                "content_free_persistent_receipts",
            ]
        },
        "persistent_result_policy": {
            "status_count_latency_only": True,
            "response_body_content_value_or_hash_persisted": False,
            "question_query_prediction_answer_or_credential_persisted": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "protected_watchers": _watchers(),
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "response_body_content_value_or_hash_persisted": False,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "probe_launch": False,
            "external_population_or_public_exact220": False,
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
    execution = copied.get("execution", {})
    target = copied.get("target", {})
    manifest = copied.get("dependency_manifest")
    if (
        copied.get("role")
        != "v24827_worldbank_exact_transport_probe_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("scope") != "benchmark_external_fixed_wld_transport_only"
        or copied.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or target
        != {
            "selection_rule": "fixed_wld_population_total_2023_before_any_probe_outcome",
            "selected_after_transport_outcome": False,
            "benchmark_task_or_country_row": False,
            "url": PROBE_URL,
            "target_key": PROBE_TARGET_KEY,
        }
        or exact_target_key(target.get("url", "")) != PROBE_TARGET_KEY
        or execution
        != {
            "waves": WAVES,
            "requests": REQUESTS,
            "sequential": True,
            "helper_attempt_cap": 3,
            "helper_hard_total_wall_seconds": EXACT_TARGET_TOTAL_WALL_SECONDS,
            "per_wave_wall_ceiling_seconds": PER_WAVE_WALL_CEILING_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "cache_resume_retry_skip_or_selective_rerun": False,
            "helper_bounded_retry_inside_each_frozen_request": True,
        }
        or copied.get("gates", {}).get("required")
        != [
            "exact_request_count",
            "all_waves_terminal_success",
            "every_wave_has_http_200",
            "every_wave_has_positive_response_bytes",
            "all_wave_walls_within_ceiling",
            "experiment_wall_within_ceiling",
            "content_free_persistent_receipts",
        ]
        or copied.get("persistent_result_policy")
        != {
            "status_count_latency_only": True,
            "response_body_content_value_or_hash_persisted": False,
            "question_query_prediction_answer_or_credential_persisted": False,
        }
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("protected_watchers") != _watchers()
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "probe_launch": False,
            "external_population_or_public_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.27 protocol drifted")
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
            TEST.name,
            "-v",
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return (
        completed.returncode == 0 and observed == EXPECTED_TESTS,
        observed,
        completed.stdout,
    )


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    validate_protocol(root)
    passed, observed, output = _run_tests()
    accesses, imports = ast_findings(root)
    findings = []
    if not passed:
        findings.append("directed_tests_failed")
    if accesses or imports:
        findings.append("label_blind_ast_failed")
    if not _lease_inactive(root):
        findings.append("shared_api_lease_active")
    if _runner_active():
        findings.append("probe_runner_active")
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        findings.append("repository_not_clean_pushed_head")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (ACTIVATION, EXECUTION_START, RESULT, POSTAUDIT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24827_worldbank_exact_transport_probe_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "tests": {
            "passed": passed,
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
            "probe_launch": False,
            "external_population_or_public_exact220": False,
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
        != "v24827_worldbank_exact_transport_probe_preactivation_audit"
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
            "probe_launch": False,
            "external_population_or_public_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.27 preactivation audit drifted")
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
        raise RuntimeError(f"V2.48.27 {role} drifted")
    return copied


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    validate_protocol(root)
    preaudit = validate_preaudit(_read(root, PREAUDIT))
    if (
        preaudit.get("audit_valid") is not True
        or not _lease_inactive(root)
        or _runner_active()
    ):
        raise RuntimeError("V2.48.27 activation state is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24827_worldbank_exact_transport_probe_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "protected_watchers": _watchers(),
        "network_model_search_fetch_evaluator_or_api_called": False,
        "launch_authorized": True,
        "authorization": {
            "one_probe_launch": True,
            "external_population_or_public_exact220": False,
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
        role="v24827_worldbank_exact_transport_probe_activation",
        seal="activation_payload_sha256",
    )
    if (
        copied.get("preactivation_audit_sha256") != sha256(ROOT / PREAUDIT)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("network_model_search_fetch_evaluator_or_api_called")
        is not False
        or copied.get("launch_authorized") is not True
        or copied.get("authorization")
        != {
            "one_probe_launch": True,
            "external_population_or_public_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.48.27 activation drifted")
    return copied


def build_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    activation = validate_activation(_read(root, ACTIVATION))
    if (
        activation.get("launch_authorized") is not True
        or not _lease_inactive(root)
        or _runner_active()
    ):
        raise RuntimeError("V2.48.27 execution-start state is unsafe")
    value = {
        "artifact_version": 1,
        "role": "v24827_worldbank_exact_transport_probe_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "protected_watchers": _watchers(),
        "single_owner_no_resume_retry_skip_or_selective_rerun": True,
        "authorization": {
            "execute_once": True,
            "external_population_or_public_exact220": False,
            "evaluator": False,
        },
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    validate_start(value)
    return value


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _stage(
        value,
        role="v24827_worldbank_exact_transport_probe_execution_start",
        seal="execution_start_payload_sha256",
    )
    if (
        copied.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or copied.get("protected_watchers") != _watchers()
        or copied.get("single_owner_no_resume_retry_skip_or_selective_rerun")
        is not True
        or copied.get("authorization")
        != {
            "execute_once": True,
            "external_population_or_public_exact220": False,
            "evaluator": False,
        }
    ):
        raise RuntimeError("V2.48.27 execution start drifted")
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
    }


def _terminate(process: Any) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=1)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=1)


def _empty_receipt(wave: int, status: str, elapsed: float) -> dict[str, Any]:
    return {
        "wave": wave,
        "helper_status": status,
        "terminal_success": False,
        "attempt_count": 0,
        "provider_retry_count": 0,
        "elapsed_seconds": round(max(0.0, elapsed), 6),
        "response_bytes": 0,
        "http_status_counts": {},
        "failure_class_counts": {status: 1},
        "response_content_value_or_hash_persisted": False,
    }


def run_probe_once(
    wave: int,
    *,
    popen: Any = subprocess.Popen,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if not 1 <= wave <= WAVES or exact_target_key(PROBE_URL) != PROBE_TARGET_KEY:
        raise ValueError("V2.48.27 probe input drifted")
    started = float(monotonic())
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
    try:
        stdout, _ = process.communicate(
            json.dumps({"url": PROBE_URL}, separators=(",", ":")),
            timeout=EXACT_TARGET_TOTAL_WALL_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _terminate(process)
        return _empty_receipt(
            wave, "hard_total_wall_timeout", float(monotonic()) - started
        )
    elapsed = float(monotonic()) - started
    if process.returncode != 0 or len(stdout.encode()) > 2_200_000:
        return _empty_receipt(wave, "helper_nonzero_or_oversized", elapsed)
    try:
        helper = validate_helper_result(json.loads(stdout))
    except (json.JSONDecodeError, TypeError, ValueError):
        return _empty_receipt(wave, "helper_invalid_result", elapsed)
    if helper["url"] != PROBE_URL or exact_target_key(helper["url"]) != PROBE_TARGET_KEY:
        return _empty_receipt(wave, "helper_binding_drift", elapsed)
    # Deliberately retain no raw_content, response hash, URL, indicator, value,
    # or semantic digest after this point.
    status_counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    for attempt in helper["attempts"]:
        if attempt["http_status"] is not None:
            status_counts[str(attempt["http_status"])] += 1
        if attempt["outcome"] == "failure":
            failures[str(attempt["error_type"] or "unknown_failure")] += 1
    return {
        "wave": wave,
        "helper_status": str(helper["status"]),
        "terminal_success": helper["status"] == "ok",
        "attempt_count": int(helper["attempt_count"]),
        "provider_retry_count": int(helper["attempt_count"] - 1),
        "elapsed_seconds": round(max(0.0, elapsed), 6),
        "response_bytes": int(helper["response_bytes"]),
        "http_status_counts": dict(sorted(status_counts.items())),
        "failure_class_counts": dict(sorted(failures.items())),
        "response_content_value_or_hash_persisted": False,
    }


RECEIPT_KEYS = frozenset(
    {
        "wave",
        "helper_status",
        "terminal_success",
        "attempt_count",
        "provider_retry_count",
        "elapsed_seconds",
        "response_bytes",
        "http_status_counts",
        "failure_class_counts",
        "response_content_value_or_hash_persisted",
    }
)


def _validate_receipt(receipt: Mapping[str, Any], wave: int) -> dict[str, Any]:
    copied = dict(receipt)
    status_counts = copied.get("http_status_counts")
    failures = copied.get("failure_class_counts")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("wave") != wave
        or copied.get("helper_status")
        not in {
            "ok",
            "exhausted",
            "hard_total_wall_timeout",
            "helper_nonzero_or_oversized",
            "helper_invalid_result",
            "helper_binding_drift",
        }
        or not isinstance(copied.get("terminal_success"), bool)
        or isinstance(copied.get("attempt_count"), bool)
        or not isinstance(copied.get("attempt_count"), int)
        or not 0 <= copied["attempt_count"] <= 3
        or copied.get("provider_retry_count")
        != max(0, copied["attempt_count"] - 1)
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or copied["elapsed_seconds"] < 0
        or isinstance(copied.get("response_bytes"), bool)
        or not isinstance(copied.get("response_bytes"), int)
        or copied["response_bytes"] < 0
        or not isinstance(status_counts, Mapping)
        or any(
            re.fullmatch(r"[1-5][0-9]{2}", str(name)) is None
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for name, count in status_counts.items()
        )
        or not isinstance(failures, Mapping)
        or any(
            not isinstance(name, str)
            or not name
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for name, count in failures.items()
        )
        or copied.get("response_content_value_or_hash_persisted") is not False
    ):
        raise RuntimeError("V2.48.27 content-free receipt drifted")
    success = copied["helper_status"] == "ok"
    pre_provider_failure = copied["helper_status"] in {
        "hard_total_wall_timeout",
        "helper_nonzero_or_oversized",
        "helper_invalid_result",
        "helper_binding_drift",
    }
    expected_failure_classes = (
        1
        if pre_provider_failure
        else copied["attempt_count"] - int(success)
    )
    if (
        copied["terminal_success"] is not success
        or (success and (copied["attempt_count"] < 1 or copied["response_bytes"] <= 0))
        or (not success and copied["response_bytes"] != 0)
        or (pre_provider_failure and copied["attempt_count"] != 0)
        or sum(status_counts.values()) > copied["attempt_count"]
        or sum(failures.values()) != expected_failure_classes
    ):
        raise RuntimeError("V2.48.27 receipt conservation drifted")
    return copied


def _summarize(receipts: Sequence[Mapping[str, Any]], wall: float) -> dict[str, Any]:
    validated = [_validate_receipt(item, index) for index, item in enumerate(receipts, 1)]
    status_counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    for item in validated:
        status_counts.update(item["http_status_counts"])
        failures.update(item["failure_class_counts"])
    checks = {
        "exact_request_count": len(validated) == REQUESTS,
        "all_waves_terminal_success": all(
            item["terminal_success"] for item in validated
        ),
        "every_wave_has_http_200": all(
            item["http_status_counts"].get("200", 0) == 1 for item in validated
        ),
        "every_wave_has_positive_response_bytes": all(
            item["response_bytes"] > 0 for item in validated
        ),
        "all_wave_walls_within_ceiling": all(
            item["elapsed_seconds"] <= PER_WAVE_WALL_CEILING_SECONDS
            for item in validated
        ),
        "experiment_wall_within_ceiling": wall <= EXPERIMENT_WALL_CEILING_SECONDS,
        "content_free_persistent_receipts": all(
            item["response_content_value_or_hash_persisted"] is False
            and set(item) == RECEIPT_KEYS
            for item in validated
        ),
    }
    return {
        "request_count": len(validated),
        "terminal_success_count": sum(item["terminal_success"] for item in validated),
        "provider_attempt_count": sum(item["attempt_count"] for item in validated),
        "provider_retry_count": sum(item["provider_retry_count"] for item in validated),
        "response_byte_count": sum(item["response_bytes"] for item in validated),
        "http_status_counts": dict(sorted(status_counts.items())),
        "failure_class_counts": dict(sorted(failures.items())),
        "wave_elapsed_seconds": [item["elapsed_seconds"] for item in validated],
        "experiment_elapsed_seconds": round(max(0.0, wall), 6),
        "checks": checks,
        "passed": all(checks.values()),
    }


def build_result(
    receipts: Sequence[Mapping[str, Any]],
    wall: float,
    *,
    execution_start_sha256: str,
    now: int | None = None,
) -> dict[str, Any]:
    summary = _summarize(receipts, wall)
    value = {
        "artifact_version": 1,
        "role": "v24827_worldbank_exact_transport_probe_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "execution_start_sha256": execution_start_sha256,
        "status": "transport_probe_go" if summary["passed"] else "transport_probe_no_go",
        "receipts": [dict(item) for item in receipts],
        **summary,
        "persistent_result_policy": {
            "status_count_latency_only": True,
            "response_body_content_value_or_hash_persisted": False,
        },
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "response_body_content_value_or_hash_persisted": False,
        },
        "authorization": {
            "accounting_successor_design": bool(summary["passed"]),
            "external_population_or_public_exact220": False,
            "same_probe_retry_resume_or_rerun": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(value, expected_start_sha256=execution_start_sha256)
    return value


def validate_result(
    value: Mapping[str, Any], *, expected_start_sha256: str | None = None
) -> dict[str, Any]:
    copied = dict(value)
    receipts = copied.get("receipts")
    expected_start = expected_start_sha256 or sha256(ROOT / EXECUTION_START)
    if not isinstance(receipts, list) or len(receipts) != REQUESTS:
        raise RuntimeError("V2.48.27 result receipt vector drifted")
    summary = _summarize(receipts, float(copied.get("experiment_elapsed_seconds", -1)))
    expected_summary = {
        "request_count": copied.get("request_count"),
        "terminal_success_count": copied.get("terminal_success_count"),
        "provider_attempt_count": copied.get("provider_attempt_count"),
        "provider_retry_count": copied.get("provider_retry_count"),
        "response_byte_count": copied.get("response_byte_count"),
        "http_status_counts": copied.get("http_status_counts"),
        "failure_class_counts": copied.get("failure_class_counts"),
        "wave_elapsed_seconds": copied.get("wave_elapsed_seconds"),
        "experiment_elapsed_seconds": copied.get("experiment_elapsed_seconds"),
        "checks": copied.get("checks"),
        "passed": copied.get("passed"),
    }
    if (
        copied.get("role") != "v24827_worldbank_exact_transport_probe_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("execution_start_sha256") != expected_start
        or expected_summary != summary
        or copied.get("status")
        != ("transport_probe_go" if summary["passed"] else "transport_probe_no_go")
        or copied.get("persistent_result_policy")
        != {
            "status_count_latency_only": True,
            "response_body_content_value_or_hash_persisted": False,
        }
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "accounting_successor_design": bool(summary["passed"]),
            "external_population_or_public_exact220": False,
            "same_probe_retry_resume_or_rerun": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.48.27 result drifted")
    forbidden = {
        "raw_content",
        "response_sha256",
        "url",
        "indicator",
        "country",
        "value",
        "question",
        "prediction",
        "answer",
        "credential",
    }
    if forbidden.intersection(copied):
        raise RuntimeError("V2.48.27 forbidden persistent result field")
    return copied


def run_experiment(
    *, probe: Callable[[int], dict[str, Any]] = run_probe_once
) -> dict[str, Any]:
    started = time.monotonic()
    receipts = [probe(wave) for wave in range(1, WAVES + 1)]
    wall = time.monotonic() - started
    return build_result(
        receipts,
        wall,
        execution_start_sha256=sha256(ROOT / EXECUTION_START),
    )


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    protocol = validate_protocol(root)
    validate_preaudit(_read(root, PREAUDIT))
    validate_activation(_read(root, ACTIVATION))
    validate_start(_read(root, EXECUTION_START))
    result = validate_result(_read(root, RESULT))
    accesses, imports = ast_findings(root)
    findings = []
    if accesses or imports:
        findings.append("label_blind_ast_failed")
    if _runner_active():
        findings.append("probe_runner_still_active")
    if not _lease_inactive(root):
        findings.append("shared_api_lease_active")
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        findings.append("repository_not_clean_pushed_head")
    if protocol.get("dependency_manifest") != _manifest(root):
        findings.append("dependency_manifest_drifted")
    if (root / POSTAUDIT).exists() or (root / POSTAUDIT).is_symlink():
        findings.append("postaudit_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24827_worldbank_exact_transport_probe_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "result_sha256": sha256(root / RESULT),
        "result_status": result["status"],
        "protected_watchers": _watchers(),
        "label_blind_audit": {
            "accesses": accesses,
            "evaluator_imports": imports,
            "passed": not accesses and not imports,
        },
        "shared_api_lease_inactive": _lease_inactive(root),
        "network_model_search_benchmark_forward_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "accounting_successor_design": not findings
            and result["status"] == "transport_probe_go",
            "external_population_or_public_exact220": False,
            "same_probe_retry_resume_or_rerun": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postaudit(value)
    return value


def validate_postaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    result = validate_result(_read(ROOT, RESULT))
    if (
        copied.get("role")
        != "v24827_worldbank_exact_transport_probe_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("result_sha256") != sha256(ROOT / RESULT)
        or copied.get("result_status") != result["status"]
        or copied.get("protected_watchers") != _watchers()
        or copied.get("label_blind_audit")
        != {"accesses": [], "evaluator_imports": [], "passed": True}
        or copied.get("shared_api_lease_inactive") is not True
        or copied.get(
            "network_model_search_benchmark_forward_or_evaluator_called_by_audit"
        )
        is not False
        or not isinstance(findings, list)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "accounting_successor_design": bool(valid)
            and result["status"] == "transport_probe_go",
            "external_population_or_public_exact220": False,
            "same_probe_retry_resume_or_rerun": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.27 postresult audit drifted")
    return copied


def command_protocol() -> None:
    _require_clean_pushed_head()
    _require_absent((PROTOCOL, PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, POSTAUDIT))
    _publish(ROOT / PROTOCOL, build_protocol(ROOT))


def command_preaudit() -> None:
    _require_clean_pushed_head()
    _require_absent((PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, POSTAUDIT))
    _publish(ROOT / PREAUDIT, build_preaudit(ROOT))


def command_activation() -> None:
    _require_clean_pushed_head()
    _require_absent((ACTIVATION, EXECUTION_START, RESULT, POSTAUDIT))
    _publish(ROOT / ACTIVATION, build_activation(ROOT))


def command_start() -> None:
    _require_clean_pushed_head()
    _require_absent((EXECUTION_START, RESULT, POSTAUDIT))
    _publish(ROOT / EXECUTION_START, build_start(ROOT))


def command_run() -> None:
    _require_clean_pushed_head()
    validate_protocol(ROOT)
    validate_preaudit(_read(ROOT, PREAUDIT))
    validate_activation(_read(ROOT, ACTIVATION))
    validate_start(_read(ROOT, EXECUTION_START))
    _require_absent((RESULT, POSTAUDIT))
    if not _lease_inactive(ROOT) or _runner_active():
        raise RuntimeError("V2.48.27 run state is unsafe")
    with acquire_deepwide_api_lease(
        ROOT,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=ROOT / LEASE_PATH,
    ):
        _publish(ROOT / RESULT, run_experiment())


def command_postaudit() -> None:
    _require_clean_pushed_head()
    _require_absent((POSTAUDIT,))
    _publish(ROOT / POSTAUDIT, build_postaudit(ROOT))


COMMANDS = {
    "protocol": command_protocol,
    "preaudit": command_preaudit,
    "activation": command_activation,
    "start": command_start,
    "run": command_run,
    "postaudit": command_postaudit,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} {{{'|'.join(COMMANDS)}}}")
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
