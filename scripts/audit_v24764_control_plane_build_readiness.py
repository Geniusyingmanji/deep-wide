#!/usr/bin/env python3
"""Clean-head readiness audit for building the V2.47.65 control plane.

This audit does not build, activate, or run an experiment.  It binds the
corrected inert V2.47.63 scientific contract to already-audited reliability
components and an exact append-only source work order.  A strict GO authorizes
only source implementation, local synthetic tests, and a later clean-build
package audit.  It grants no preactivation, launch, evaluator, dev64, or 220
authority.
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24269_task_union_discovery import (  # noqa: E402
    TaskUnionDiscoverySearchClient,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallNativeSearchClient,
    HardTotalWallResponsesClient,
)


DATE = "20260807"
OUTPUT = Path(f"results/v24764_control_plane_build_readiness_v1_{DATE}.json")
PARENT = Path(
    "results/v24763_corrected_zero_effect_external_preregistration_v1_20260806.json"
)
CORRECTION = Path(
    "results/v24762_v24759_source_provenance_correction_v1_20260806.json"
)
READINESS_SOURCE = Path("scripts/audit_v24764_control_plane_build_readiness.py")
READINESS_TEST = Path("tests/test_audit_v24764_control_plane_build_readiness.py")
EXISTING_SOURCES = (
    Path("src/deepwide_agent/v24263_global_model_limiter.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24309_runner_exit_integration.py"),
    Path("src/deepwide_agent/v24312_deadline_reliability.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("src/deepwide_agent/v24760_zero_effect_external_contract.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24263_global_model_limiter.py"), 6),
    (Path("tests/test_v24269_task_union_discovery.py"), 5),
    (Path("tests/test_v24309_runner_exit_integration.py"), 5),
    (Path("tests/test_v24312_deadline_reliability.py"), 7),
    (Path("tests/test_v24316_deadline_search.py"), 7),
    (Path("tests/test_v24468_total_wall_transport.py"), 8),
    (Path("tests/test_v24756_zero_effect_structured_integration.py"), 6),
    (READINESS_TEST, 5),
)
EXPECTED_TESTS = 49
SOURCES = (
    *EXISTING_SOURCES,
    *(path for path, _count in TEST_SUITES[:-1]),
    READINESS_SOURCE,
    READINESS_TEST,
    PARENT,
    CORRECTION,
)
PLANNED_SOURCES = (
    Path("src/deepwide_agent/v24765_zero_effect_execution_contract.py"),
    Path("scripts/run_v24765_zero_effect_task.py"),
    Path("scripts/run_v24765_zero_effect_external.py"),
    Path("scripts/audit_v24765_zero_effect_forward.py"),
    Path("scripts/control_v24765_zero_effect_external.py"),
    Path("scripts/audit_v24766_zero_effect_package_build.py"),
    Path("tests/test_v24765_zero_effect_package.py"),
    Path("tests/test_v24765_zero_effect_control.py"),
    Path("tests/test_audit_v24766_zero_effect_package_build.py"),
)
PLANNED_RUNTIME_SOURCES = PLANNED_SOURCES[:5]
PLANNED_AUDIT_SOURCES = PLANNED_SOURCES[5:]
PLANNED_RUNTIME_KEYS = (
    "task_runtime_input_exactly_opaque_id_question",
    "hard_total_wall_model_inner",
    "deadline_aware_global_model_slot_cap8",
    "hard_total_wall_native_search_inner",
    "runtime_owned_single_task_union_wrapper",
    "thin_title_backfill_forbidden",
    "two_model_four_query_ten_fetch_caps",
    "process_group_parent_timeout195",
    "eight_task_executors",
    "failure_as_zero_fixed_denominator8",
    "prediction_freeze_before_private_truth",
    "content_free_forward_aggregate",
    "adapter_zero_additional_effect",
)
FUTURE_RESULTS = (
    Path(f"results/v24765_zero_effect_forward_audit_v1_{DATE}.json"),
    Path(f"results/v24765_zero_effect_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24765_zero_effect_activation_v1_{DATE}.json"),
    Path(f"results/v24765_zero_effect_execution_start_v1_{DATE}.json"),
    Path(f"results/v24765_zero_effect_forward_result_v1_{DATE}.json"),
    Path(f"results/v24765_zero_effect_quality_preregistration_v1_{DATE}.json"),
    Path(f"results/v24765_zero_effect_quality_result_v1_{DATE}.json"),
    Path(f"results/v24765_zero_effect_postresult_audit_v1_{DATE}.json"),
    Path(f"results/v24766_zero_effect_package_build_audit_v1_{DATE}.json"),
    Path(f"outputs/v24765_zero_effect_external_v1_{DATE}"),
)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
RUNNER_MARKERS = (
    "scripts/run_v24765_zero_effect_external.py",
    "scripts/run_v24765_zero_effect_task.py",
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
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise RuntimeError(f"V2.47.64 expected tracked ordinary file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.64 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    protocol = _read(PARENT)
    correction = _read(CORRECTION)
    return bool(
        protocol.get("role")
        == "v24763_corrected_zero_effect_external_preregistration"
        and protocol.get("task_contract", {}).get("runtime_input_keys")
        == ["opaque_id", "question"]
        and protocol.get("task_contract", {}).get("task_count") == 8
        and protocol.get("runtime", {}).get("task_executors") == 8
        and protocol.get("runtime", {}).get("global_model_slot_cap") == 8
        and protocol.get("runtime", {}).get("limits", {}).get("model_calls") == 2
        and protocol.get("runtime", {}).get("limits", {}).get("search_queries")
        == 4
        and protocol.get("runtime", {}).get("limits", {}).get("fetch_targets")
        == 10
        and protocol.get("runtime", {}).get(
            "adapter_additional_model_query_search_fetch_or_token_effect"
        )
        == 0
        and protocol.get("authorization", {}).get("runner_or_control_plane_build")
        is False
        and protocol.get("authorization", {}).get("one_external_forward_launch")
        is False
        and protocol.get("authorization", {}).get("quality_surface_open") is False
        and _sealed(protocol, "protocol_payload_sha256")
        and correction.get("role")
        == "v24762_v24759_source_provenance_correction"
        and correction.get("recertification", {}).get(
            "v24760_population_recertified_under_corrected_provenance"
        )
        is True
        and correction.get("supersession", {}).get(
            "v24761_protocol_authorizes_successor_use"
        )
        is False
        and correction.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is False
        and _sealed(correction, "correction_payload_sha256")
    )


def _manifest() -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        raw = _ordinary(relative).read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.64 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def _run_tests() -> tuple[bool, int, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows: list[dict[str, Any]] = []
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
        row = {
            "path": str(suite),
            "expected": expected,
            "observed": observed,
            "return_code": completed.returncode,
            "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "passed": completed.returncode == 0 and observed == expected,
        }
        rows.append(row)
        total += observed
        passed = passed and row["passed"]
    return passed and total == EXPECTED_TESTS, total, rows


def compatibility_contract() -> dict[str, Any]:
    runtime_path = _ordinary(
        Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py")
    )
    source = runtime_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    union_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "TaskUnionDiscoverySearchClient"
    ]
    forbidden = [
        marker
        for marker in (
            "ThinSameResponseCitationTitleBackfillSearchClient",
            "run_v24630_task",
            "citation_title_backfill",
        )
        if marker in source
    ]
    return {
        "runtime_owned_task_union_wrapper_call_count": len(union_calls),
        "planned_search_inner_class": HardTotalWallNativeSearchClient.__name__,
        "planned_model_inner_class": HardTotalWallResponsesClient.__name__,
        "planned_model_slot_wrapper_class": DeadlineAwareGlobalModelSlotLimiter.__name__,
        "task_union_wrapper_class": TaskUnionDiscoverySearchClient.__name__,
        "hard_total_wall_search_is_deadline_aware": issubclass(
            HardTotalWallNativeSearchClient, DeadlineAwareNativeSearchClient
        ),
        "thin_title_backfill_or_second_runtime_import_markers": forbidden,
        "double_task_union_wrapper_allowed": False,
        "compatible": len(union_calls) == 1
        and not forbidden
        and issubclass(
            HardTotalWallNativeSearchClient, DeadlineAwareNativeSearchClient
        ),
    }


def ast_findings() -> tuple[list[str], list[str]]:
    accesses: list[str] = []
    imports: list[str] = []
    for relative in (
        Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
        Path("src/deepwide_agent/v24760_zero_effect_external_contract.py"),
    ):
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
                if "evaluator" in name.casefold() or "gold" in name.casefold():
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


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
            raise RuntimeError("V2.47.64 protected watcher drifted")
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
    tests_passed, observed, suites = _run_tests()
    compatibility = compatibility_contract()
    accesses, imports = ast_findings()
    watchers = _watchers()
    lease_inactive = _lease_inactive()
    runner_active = _runner_active()
    parent_valid = _parent_valid()
    planned_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in PLANNED_SOURCES
    )
    future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in FUTURE_RESULTS
    )
    clean = _git("status", "--porcelain") == ""
    pushed = _git("rev-parse", "HEAD") == _git("rev-parse", "target/main")
    findings: list[str] = []
    if not parent_valid:
        findings.append("corrected_inert_parent_invalid")
    if not tests_passed:
        findings.append("reliability_or_readiness_tests_failed")
    if not compatibility.get("compatible"):
        findings.append("runtime_transport_composition_incompatible")
    if accesses or imports:
        findings.append("label_blind_ast_failed")
    if not planned_pristine or not future_pristine:
        findings.append("planned_or_future_surface_not_pristine")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if runner_active:
        findings.append("v24765_runner_active")
    if not clean or not pushed:
        findings.append("repository_not_clean_pushed_head")
    value = {
        "artifact_version": 1,
        "role": "v24764_control_plane_build_readiness",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_protocol_sha256": sha256(ROOT / PARENT),
        "correction_sha256": sha256(ROOT / CORRECTION),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "inherited_scientific_contract": {
            "runtime_sha256": payload_sha256(_read(PARENT)["runtime"]),
            "forward_health_gate_sha256": payload_sha256(
                _read(PARENT)["forward_health_gate"]
            ),
            "mechanism_gate_sha256": payload_sha256(
                _read(PARENT)["mechanism_gate_before_private_truth"]
            ),
            "quality_gate_sha256": payload_sha256(
                _read(PARENT)["quality_gate_after_prediction_freeze"]
            ),
            "entropy_credit_scope_sha256": payload_sha256(
                _read(PARENT)["entropy_credit_scope"]
            ),
            "task_runtime_input_keys": ["opaque_id", "question"],
            "task_count": 8,
            "science_contract_mutable_by_source_build": False,
        },
        "transport_compatibility": compatibility,
        "work_order": {
            "planned_runtime_sources": [str(path) for path in PLANNED_RUNTIME_SOURCES],
            "planned_audit_and_test_sources": [
                str(path) for path in PLANNED_AUDIT_SOURCES
            ],
            "required_runtime_contracts": list(PLANNED_RUNTIME_KEYS),
            "planned_sources_pristine": planned_pristine,
            "future_result_and_output_surfaces_pristine": future_pristine,
            "append_only_implementation": True,
            "private_population_or_truth_not_in_forward_manifest": True,
            "source_build_may_open_private_population": False,
            "package_audit_may_open_private_population": False,
        },
        "tests": {
            "passed": tests_passed,
            "observed": observed,
            "expected": EXPECTED_TESTS,
            "suites": suites,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "privileged_accesses": accesses,
            "evaluator_or_gold_imports": imports,
            "passed": not accesses and not imports,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": lease_inactive,
            "v24765_runner_active": runner_active,
        },
        "git": {
            "repository_clean": clean,
            "head_equals_target_main": pushed,
        },
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "v24765_control_plane_source_implementation_and_local_tests": not findings,
            "v24766_package_audit_source_implementation": not findings,
            "source_commit_and_push": not findings,
            "package_audit_artifact_generation": False,
            "preactivation_audit": False,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
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
    compatibility = copied.get("transport_compatibility")
    inherited = copied.get("inherited_scientific_contract", {})
    work = copied.get("work_order", {})
    tests = copied.get("tests", {})
    label = copied.get("label_blind_audit")
    state = copied.get("runtime_state", {})
    git = copied.get("git")
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    if (
        copied.get("role") != "v24764_control_plane_build_readiness"
        or copied.get("parent_protocol_sha256") != sha256(ROOT / PARENT)
        or copied.get("correction_sha256") != sha256(ROOT / CORRECTION)
        or copied.get("dependency_manifest") != _manifest()
        or copied.get("dependency_manifest_sha256")
        != payload_sha256(copied.get("dependency_manifest"))
        or inherited
        != {
            "runtime_sha256": payload_sha256(_read(PARENT)["runtime"]),
            "forward_health_gate_sha256": payload_sha256(
                _read(PARENT)["forward_health_gate"]
            ),
            "mechanism_gate_sha256": payload_sha256(
                _read(PARENT)["mechanism_gate_before_private_truth"]
            ),
            "quality_gate_sha256": payload_sha256(
                _read(PARENT)["quality_gate_after_prediction_freeze"]
            ),
            "entropy_credit_scope_sha256": payload_sha256(
                _read(PARENT)["entropy_credit_scope"]
            ),
            "task_runtime_input_keys": ["opaque_id", "question"],
            "task_count": 8,
            "science_contract_mutable_by_source_build": False,
        }
        or compatibility != compatibility_contract()
        or compatibility.get("compatible") is not True
        or compatibility.get("runtime_owned_task_union_wrapper_call_count") != 1
        or compatibility.get("double_task_union_wrapper_allowed") is not False
        or compatibility.get("thin_title_backfill_or_second_runtime_import_markers")
        != []
        or work.get("planned_runtime_sources")
        != [str(path) for path in PLANNED_RUNTIME_SOURCES]
        or work.get("planned_audit_and_test_sources")
        != [str(path) for path in PLANNED_AUDIT_SOURCES]
        or work.get("required_runtime_contracts") != list(PLANNED_RUNTIME_KEYS)
        or work.get("planned_sources_pristine") is not True
        or work.get("future_result_and_output_surfaces_pristine") is not True
        or work.get("append_only_implementation") is not True
        or work.get("private_population_or_truth_not_in_forward_manifest")
        is not True
        or work.get("source_build_may_open_private_population") is not False
        or work.get("package_audit_may_open_private_population") is not False
        or tests.get("passed") is not True
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("expected") != EXPECTED_TESTS
        or not isinstance(tests.get("suites"), list)
        or [
            (row.get("path"), row.get("expected"), row.get("observed"), row.get("passed"))
            for row in tests.get("suites", [])
            if isinstance(row, Mapping)
        ]
        != [
            (str(path), expected, expected, True)
            for path, expected in TEST_SUITES
        ]
        or tests.get("network_model_search_fetch_benchmark_or_evaluator_called")
        is not False
        or label
        != {
            "privileged_accesses": [],
            "evaluator_or_gold_imports": [],
            "passed": True,
        }
        or state.get("protected_watchers") != _watchers()
        or state.get("shared_api_lease_inactive") is not True
        or state.get("v24765_runner_active") is not False
        or git != {"repository_clean": True, "head_equals_target_main": True}
        or copied.get("source_policy")
        != {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
        }
        or not isinstance(findings, list)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "v24765_control_plane_source_implementation_and_local_tests": bool(valid),
            "v24766_package_audit_source_implementation": bool(valid),
            "source_commit_and_push": bool(valid),
            "package_audit_artifact_generation": False,
            "preactivation_audit": False,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.64 readiness audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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
    _publish(ROOT / OUTPUT, audit)
    print(
        json.dumps(
            {
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "output": str(OUTPUT),
                "source_build_authorized": audit["authorization"][
                    "v24765_control_plane_source_implementation_and_local_tests"
                ],
                "tests": audit["tests"]["observed"],
            },
            sort_keys=True,
        )
    )
