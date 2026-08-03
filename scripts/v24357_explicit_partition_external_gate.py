#!/usr/bin/env python3
"""Benchmark-external real-transport gate for V2.43.54--56.

Twelve fixed public-web tasks run once through a 9-proposal/1-hidden-verifier
source partition.  The parent candidate must be produced from proposal pages
alone; the hidden page may only retain or revert that candidate.  Private task
artifacts are replay-validated inside a temporary directory and deleted.  Only
content-free aggregates persist.

No benchmark manifest, mapping, gold, label, evaluator, or score surface is
opened or authorized.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
    run_observed_subprocess,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24356_explicit_partition_runner import (  # noqa: E402
    build_envelope,
    run_v24356_task,
    validate_envelope,
    validate_observed_bundle,
)
from scripts import v24345_semantic_active_natural_admission as task_source  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260803"
PROTOCOL_ID = "v24357_explicit_partition_external_gate_v1"
PROTOCOL = Path(f"results/v24357_explicit_partition_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24357_explicit_partition_external_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24357_explicit_partition_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24357_explicit_partition_external_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24357_explicit_partition_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24357_explicit_partition_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24357_explicit_partition_external_postresult_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24356_explicit_partition_build_audit_v1_{DATE}.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_explicit_partition_entropy_gate"
RUNNER_MARKER = "scripts/v24357_explicit_partition_external_gate.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
SELECTED = 12
EXECUTOR_COUNT = 8
MODEL_SLOT_CAP = 2
TASK_WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
BATCH_WALL_CEILING_SECONDS = 300.0
LIMITS = ScoreFirstLimits(
    wall_seconds=TASK_WALL_SECONDS,
    model_calls=3,
    search_queries=4,
    fetch_targets=10,
    search_results_per_query=3,
    evidence_chars=60_000,
    page_chars=5_000,
    plan_output_tokens=4_000,
    synthesis_output_tokens=30_000,
    repair_output_tokens=12_000,
)
GATES = {
    "selected": SELECTED,
    "executor_count": EXECUTOR_COUNT,
    "model_slot_cap": MODEL_SLOT_CAP,
    "maximum_batch_wall_seconds": BATCH_WALL_CEILING_SECONDS,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 4,
    "maximum_fetch_helper_failures": 4,
    "maximum_deadline_exhausted_tasks": 0,
    "minimum_explicit_partition_observed_tasks": 8,
    "minimum_parent_semantic_catalog_tasks": 8,
    "minimum_hidden_page_tasks": 8,
    "minimum_parent_candidate_tasks": 1,
    "minimum_utility_aligned_tasks": 1,
    "minimum_final_nonidentity_tasks": 1,
}
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24333_programmatic_support_catalog.py",
    "src/deepwide_agent/v24334_support_catalog_revision_gate.py",
    "src/deepwide_agent/v24335_programmatic_support_runtime.py",
    "src/deepwide_agent/v24341_semantic_evidence_projection.py",
    "src/deepwide_agent/v24342_semantic_active_runtime.py",
    "src/deepwide_agent/v24348_structural_table_normalizer.py",
    "src/deepwide_agent/v24349_structural_semantic_runtime.py",
    "src/deepwide_agent/v24354_explicit_partition_utility.py",
    "src/deepwide_agent/v24355_explicit_partition_runtime.py",
    "src/deepwide_agent/v24356_explicit_partition_runner.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/v24345_semantic_active_natural_admission.py",
    "scripts/v24357_explicit_partition_external_gate.py",
    "tests/test_v24354_explicit_partition_utility.py",
    "tests/test_v24355_explicit_partition_runtime.py",
    "tests/test_v24356_explicit_partition_runner.py",
    "tests/test_v24357_explicit_partition_external_gate.py",
)
TEST_FILES = (
    "tests/test_v24354_explicit_partition_utility.py",
    "tests/test_v24355_explicit_partition_runtime.py",
    "tests/test_v24356_explicit_partition_runner.py",
    "tests/test_v24357_explicit_partition_external_gate.py",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
URL = re.compile(r"https?://", re.IGNORECASE)


def neutral_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED:
        raise ValueError("V2.43.57 neutral ordinal is invalid")
    return validate_visible_task(task_source.neutral_task(ordinal))


def partition_seed(ordinal: int) -> str:
    neutral_task(ordinal)
    return hashlib.sha256(
        f"{PROTOCOL_ID}|one-host-explicit-preproposal-partition|{ordinal}".encode(
            "utf-8"
        )
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.43.57 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.57 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.43.57 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _future(root: Path, values: Sequence[Path]) -> bool:
    return all(not (root / path).exists() and not (root / path).is_symlink() for path in values)


def _port_listening() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    if (
        value.get("role") != "v24356_explicit_partition_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "benchmark_external_explicit_partition_gate_design"
        )
        is not True
        or value.get("authorization", {}).get("benchmark_launch") is not False
        or value.get("authorization", {}).get("new_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.57 parent audit drifted")
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    LIMITS.validate()
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    seeds = [partition_seed(index) for index in range(1, SELECTED + 1)]
    if require_pristine and not _future(
        root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.57 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24357_explicit_partition_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "scope": "benchmark_external_real_web_explicit_partition_entropy_gate",
        "task_contract": {
            "selected": SELECTED,
            "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
            "task_vector_validated_in_memory_before_protocol": len(tasks) == SELECTED,
            "synthetic_identifiers_not_selected_from_benchmark": True,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "questions_inherited_from_frozen_external_task_source": True,
            "question_or_opaque_id_persisted": False,
        },
        "partition": {
            "seed_sha256_vector": seeds,
            "seed_depends_only_on_protocol_and_fixed_ordinal": True,
            "partition_precedes_fetch_and_candidate": True,
            "proposal_source_cap": 9,
            "verifier_source_cap": 1,
            "successful_pages_may_be_strict_partition_subsets": True,
            "parent_support_set_and_evidence_ids_reused_without_rebuild": True,
            "hidden_verifier_can_only_retain_or_revert": True,
        },
        "provider": {
            "proxy_url": f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "max_retries": 2,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
        },
        "budget": {
            "task_wall_seconds": TASK_WALL_SECONDS,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "model_calls": 3,
            "search_queries": 4,
            "fetch_targets_total": 10,
            "page_characters": LIMITS.page_chars,
            "single_batch_no_resume_retry_skip_or_selective_rerun": True,
        },
        "gates": dict(GATES),
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_external_explicit_partition_probe_design": True,
            "external_probe_launch": False,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
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
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = protocol.get("surface_manifest")
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    seeds = [partition_seed(index) for index in range(1, SELECTED + 1)]
    if (
        protocol.get("role") != "v24357_explicit_partition_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("gates") != GATES
        or protocol.get("task_contract", {}).get("selected") != SELECTED
        or protocol.get("task_contract", {}).get("fixed_ordinal_vector")
        != list(range(1, SELECTED + 1))
        or protocol.get("task_contract", {}).get(
            "task_vector_validated_in_memory_before_protocol"
        )
        is not (len(tasks) == SELECTED)
        or protocol.get("partition", {}).get("seed_sha256_vector") != seeds
        or len(set(seeds)) != SELECTED
        or protocol.get("partition", {}).get("proposal_source_cap") != 9
        or protocol.get("partition", {}).get("verifier_source_cap") != 1
        or protocol.get("provider", {}).get("executor_count") != EXECUTOR_COUNT
        or protocol.get("provider", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or protocol.get("budget", {}).get("fetch_targets_total") != 10
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(protocol.get("source_policy", {}).values())
        or protocol.get("authorization", {}).get(
            "one_external_explicit_partition_probe_design"
        )
        is not True
        or any(
            enabled
            for key, enabled in protocol.get("authorization", {}).items()
            if key != "one_external_explicit_partition_probe_design"
        )
        or protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.57 protocol drifted")
    _parent(root)
    return protocol


def _run_tests() -> dict[str, bool]:
    output: dict[str, bool] = {}
    for relative in TEST_FILES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-v"],
            cwd=ROOT,
            env={
                "HOME": str(Path.home()),
                "USER": os.environ.get("USER", "azureuser"),
                "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=180,
            check=False,
        )
        output[relative] = completed.returncode == 0
    return output


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    pristine = _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT))
    tests = _run_tests()
    port = _port_listening()
    lease = lease_observation(root, Path("/proc"))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    watchers = protected_watcher_snapshot()
    parent_watchers = _parent(root)["closure"]["protected_watchers"]
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not all(tests.values()):
        findings.append("focused_tests_failed")
    if not port:
        findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if head != remote:
        findings.append("protocol_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if watchers != parent_watchers:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24357_explicit_partition_external_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "fixed_external_task_and_partition_vector_frozen": True,
            "focused_tests": tests,
            "keyless_proxy_listening_without_api_request": port,
            "shared_api_lease_inactive": lease.get("active") is False,
            "protocol_commit_pushed": head == remote,
            "worktree_clean": clean,
            "future_surface_pristine": pristine,
            "protected_watchers_unchanged": watchers == parent_watchers,
            "benchmark_or_evaluator_surface_authorized": False,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "parent_sha256": sha256(root / PARENT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
            "head": head,
            "target_main": remote,
        },
        "authorization": {
            "one_external_explicit_partition_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.57 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    if (
        value.get("role") != "v24357_explicit_partition_external_preactivation_audit"
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("provenance", {}).get("protocol_sha256") != sha256(root / PROTOCOL)
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.57 preaudit drifted")
    validate_protocol(root)
    return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    audit = validate_preaudit(root)
    findings: list[str] = []
    if not _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        findings.append("activation_or_execution_surface_not_pristine")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24357_explicit_partition_external_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "selected": SELECTED,
        "executor_count": EXECUTOR_COUNT,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_external_explicit_partition_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.57 activation failed")
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, ACTIVATION)
    if (
        value.get("role") != "v24357_explicit_partition_external_activation"
        or value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.57 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.43.57 execution surface is not pristine")
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    findings: list[str] = []
    if head != remote:
        findings.append("activation_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24357_explicit_partition_external_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "ready" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected": SELECTED,
        "executor_count": EXECUTOR_COUNT,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": activation["protected_watchers"],
        "api_called_before_execution_start": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_or_evaluator_authorized": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.57 execution start failed: " + ",".join(findings))
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, EXECUTION_START)
    if (
        value.get("role") != "v24357_explicit_partition_external_execution_start"
        or value.get("status") != "ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("api_called_before_execution_start") is not False
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.43.57 execution-start drifted")
    validate_activation(root)
    return value


def _environment() -> dict[str, str]:
    return {
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def _child(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal)
    task = neutral_task(ordinal)
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    result_path = directory / "result.json"
    model_path = directory / "model_slot_receipt.json"
    transport_path = directory / "transport_health.json"

    def action() -> None:
        deadline = time.monotonic() + TASK_WALL_SECONDS
        model = build_deadline_model(
            url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            model_name="gpt-5.6-sol",
            reasoning_effort="low",
            service_tier="priority",
            static_timeout_seconds=TASK_WALL_SECONDS,
            max_retries=2,
            slot_directory=Path(args.slots),
            output_root=output_root,
            slot_cap=MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
        )
        search = DeadlineAwareNativeSearchClient(
            f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "gpt-5.6-sol",
            reasoning_effort="low",
            service_tier="priority",
            timeout=TASK_WALL_SECONDS,
            max_retries=2,
            max_workers=1,
            batch_size=8,
            search_context_size="medium",
            max_output_tokens=7_000,
            fetch_pages=False,
            fetch_workers=8,
            fetch_timeout=20,
            max_page_chars=LIMITS.page_chars,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
        )
        outcome = run_v24356_task(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed(ordinal),
            limits=LIMITS,
            monotonic=time.monotonic,
        )
        _write_new(model_path, outcome.model_slot_receipt)
        _write_new(transport_path, outcome.transport_health)
        _write_new(result_path, build_envelope(outcome))

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name="result.json",
        model_receipt_name="model_slot_receipt.json",
        transport_receipt_name="transport_health.json",
        terminal_name="child_terminal_receipt.json",
    )


def _integer(source: object, name: str) -> int:
    raw = source.get(name) if isinstance(source, Mapping) else None
    return int(raw) if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0 else 0


def _number(source: object, name: str) -> float:
    raw = source.get(name) if isinstance(source, Mapping) else None
    return (
        float(raw)
        if isinstance(raw, (int, float))
        and not isinstance(raw, bool)
        and math.isfinite(float(raw))
        and float(raw) >= 0
        else 0.0
    )


TASK_CHECK_NAMES = (
    "parent_success",
    "all_parent_artifacts_valid",
    "effect_accounting_complete",
    "structural_shared_normalization",
    "partition_precedes_fetch_candidate",
    "source_partition_disjoint",
    "hidden_verifier_prompt_excluded",
    "hidden_verifier_no_new_candidate",
    "parent_support_ids_reused",
    "partition_or_fail_closed",
    "fetch_budget_transport_conserved",
    "model_slot_conserved",
    "private_replay_valid",
    "deadline_not_exhausted",
)


def _task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "parent_success": value.get("parent_taxonomy") == "success",
        "all_parent_artifacts_valid": value.get("all_parent_artifacts_valid") is True,
        "effect_accounting_complete": value.get("effect_accounting_complete") is True,
        "structural_shared_normalization": value.get("structural_shared_normalization") is True,
        "partition_precedes_fetch_candidate": value.get("partition_precedes_fetch_candidate") is True,
        "source_partition_disjoint": value.get("source_partition_disjoint") is True,
        "hidden_verifier_prompt_excluded": value.get("hidden_verifier_prompt_excluded") is True,
        "hidden_verifier_no_new_candidate": value.get("hidden_verifier_no_new_candidate") is True,
        "parent_support_ids_reused": value.get("parent_support_ids_reused") is True,
        "partition_or_fail_closed": value.get("observed_pages_respect_frozen_partition") is True
        or value.get("candidate_changed_cells_after_hidden_verifier") == 0,
        "fetch_budget_transport_conserved": (
            value.get("total_fetch_calls")
            == value.get("parent_fetch_calls") + value.get("hidden_verifier_fetch_calls")
            == value.get("hard_fetch_helper_calls") + value.get("fetch_deadline_rejections")
            and 0 <= int(value.get("total_fetch_calls", -1)) <= 10
        ),
        "model_slot_conserved": value.get("model_requests") == value.get("slot_acquisitions"),
        "private_replay_valid": value.get("private_replay_valid") is True,
        "deadline_not_exhausted": value.get("deadline_exhausted") is False,
    }


def _task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    validate_parent_receipt(parent)
    wrapped = envelope.get("result") if isinstance(envelope, Mapping) else None
    parent_result = wrapped.get("parent_result") if isinstance(wrapped, Mapping) else None
    semantic = parent_result.get("semantic_result") if isinstance(parent_result, Mapping) else None
    core = semantic.get("core_result") if isinstance(semantic, Mapping) else None
    core_receipt = core.get("shared_prefix_revision_receipt") if isinstance(core, Mapping) else None
    structural = parent_result.get("structural_receipt") if isinstance(parent_result, Mapping) else None
    hidden = wrapped.get("hidden_verifier_receipt") if isinstance(wrapped, Mapping) else None
    partition = hidden.get("partition_receipt") if isinstance(hidden, Mapping) else None
    private = wrapped.get("private_replay_state") if isinstance(wrapped, Mapping) else None
    catalog = private.get("utility_catalog") if isinstance(private, Mapping) else None
    proposal_catalog = (
        semantic.get("semantic_active_private_state", {}).get("semantic_active_catalog")
        if isinstance(semantic, Mapping)
        else None
    )
    slot = envelope.get("model_slot_receipt") if isinstance(envelope, Mapping) else None
    transport = envelope.get("transport_health") if isinstance(envelope, Mapping) else None
    cost = core.get("cost") if isinstance(core, Mapping) else None
    model_cost = cost.get("model") if isinstance(cost, Mapping) else None
    search_cost = cost.get("search") if isinstance(cost, Mapping) else None
    raw_slot_counts = slot.get("slot_acquisition_counts") if isinstance(slot, Mapping) else None
    slot_counts = (
        [int(item) for item in raw_slot_counts]
        if isinstance(raw_slot_counts, list)
        and len(raw_slot_counts) == MODEL_SLOT_CAP
        and all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in raw_slot_counts)
        else [0] * MODEL_SLOT_CAP
    )
    baseline = wrapped.get("baseline_prediction") if isinstance(wrapped, Mapping) else None
    candidate = wrapped.get("candidate_prediction") if isinstance(wrapped, Mapping) else None
    before = _integer(hidden, "candidate_changed_cells_before_hidden_verifier")
    after = _integer(hidden, "candidate_changed_cells_after_hidden_verifier")
    parent_eligible = (
        _integer(proposal_catalog, "eligible_support_set_count")
        if isinstance(proposal_catalog, Mapping)
        else 0
    )
    value = {
        "ordinal": ordinal,
        "wall_seconds": round(float(parent.get("elapsed_seconds", 0.0)), 6),
        "parent_taxonomy": parent.get("failure_taxonomy"),
        "all_parent_artifacts_valid": all(
            parent.get(name) is True
            for name in (
                "child_terminal_receipt_present",
                "child_terminal_receipt_valid",
                "result_envelope_present",
                "result_envelope_valid",
                "model_receipt_present",
                "model_receipt_valid",
                "transport_receipt_present",
                "transport_receipt_valid",
            )
        ),
        "completion_kind": core.get("completion_kind") if isinstance(core, Mapping) else None,
        "effect_accounting_complete": core_receipt.get("effect_accounting_complete") if isinstance(core_receipt, Mapping) else False,
        "structural_shared_normalization": structural.get("same_normalized_baseline_for_baseline_and_candidate") if isinstance(structural, Mapping) else False,
        "partition_precedes_fetch_candidate": partition.get("source_partition_precedes_fetch_and_candidate_discovery") if isinstance(partition, Mapping) else False,
        "source_partition_disjoint": partition.get("proposal_and_verifier_sources_disjoint") if isinstance(partition, Mapping) else False,
        "hidden_verifier_prompt_excluded": hidden.get("hidden_verifier_pages_used_for_candidate_generation_or_model_prompt") is False if isinstance(hidden, Mapping) else False,
        "hidden_verifier_no_new_candidate": hidden.get("new_candidate_value_generated_by_hidden_verifier") is False if isinstance(hidden, Mapping) else False,
        "parent_support_ids_reused": hidden.get("parent_support_set_ids_reused_without_rebuild") is True if isinstance(hidden, Mapping) else False,
        "observed_pages_respect_frozen_partition": hidden.get("observed_pages_respect_frozen_partition") is True if isinstance(hidden, Mapping) else False,
        "parent_semantic_catalog_present": hidden.get("parent_semantic_catalog_present") is True if isinstance(hidden, Mapping) else False,
        "selected_source_count": _integer(partition, "selected_source_count"),
        "proposal_source_count": _integer(partition, "proposal_source_count"),
        "verifier_source_count": _integer(partition, "verifier_source_count"),
        "verifier_source_cap": _integer(partition, "verifier_source_cap"),
        "parent_proposal_page_count": _integer(hidden, "parent_proposal_page_count"),
        "hidden_verifier_page_count": _integer(hidden, "hidden_verifier_page_count"),
        "parent_fetch_calls": _integer(hidden, "parent_fetch_calls"),
        "hidden_verifier_fetch_calls": _integer(hidden, "hidden_verifier_fetch_calls"),
        "total_fetch_calls": _integer(hidden, "total_fetch_calls"),
        "parent_eligible_support_set_count": parent_eligible,
        "candidate_changed_cells_before_hidden_verifier": before,
        "candidate_changed_cells_after_hidden_verifier": after,
        "hidden_verifier_admitted_cells": _integer(hidden, "hidden_verifier_admitted_cells"),
        "hidden_verifier_reverted_cells": _integer(hidden, "hidden_verifier_reverted_cells"),
        "proposal_conditional_entropy_reduction_nats": _number(hidden, "proposal_conditional_entropy_reduction_nats"),
        "utility_aligned_entropy_credit_nats": _number(hidden, "utility_aligned_entropy_credit_nats"),
        "utility_set_count": _integer(catalog, "utility_aligned_support_set_count"),
        "final_candidate_nonidentity": isinstance(baseline, str) and isinstance(candidate, str) and baseline != candidate,
        "model_requests": _integer(model_cost, "requests"),
        "model_attempts": _integer(model_cost, "attempts"),
        "model_total_tokens": _integer(model_cost, "total_tokens"),
        "slot_acquisitions": _integer(slot, "acquisitions"),
        "slot_timeouts": _integer(slot, "slot_timeouts"),
        "provider_deadline_failures": _integer(slot, "provider_deadline_failures"),
        "slot_total_wait_seconds": _number(slot, "total_wait_seconds"),
        "slot_max_wait_seconds": _number(slot, "max_wait_seconds"),
        "slot_acquisition_counts": slot_counts,
        "search_calls": _integer(search_cost, "calls"),
        "fetch_failures": _integer(search_cost, "fetch_failures"),
        "search_total_tokens": _integer(search_cost, "total_tokens"),
        "hosted_search_attempts": _integer(transport, "hosted_search_attempts"),
        "hosted_search_deadline_failures": _integer(transport, "hosted_search_deadline_failures"),
        "hard_fetch_helper_calls": _integer(transport, "hard_fetch_helper_calls"),
        "hard_fetch_deadline_failures": _integer(transport, "hard_fetch_deadline_failures"),
        "fetch_deadline_rejections": _integer(transport, "fetch_deadline_rejections"),
        "fetch_helper_failures": _integer(transport, "fetch_helper_failures"),
        "deadline_exhausted": transport.get("deadline_exhausted") is True if isinstance(transport, Mapping) else True,
        "private_replay_valid": isinstance(wrapped, Mapping),
    }
    value["checks"] = _task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    counts = (
        "selected_source_count",
        "proposal_source_count",
        "verifier_source_count",
        "verifier_source_cap",
        "parent_proposal_page_count",
        "hidden_verifier_page_count",
        "parent_fetch_calls",
        "hidden_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_eligible_support_set_count",
        "candidate_changed_cells_before_hidden_verifier",
        "candidate_changed_cells_after_hidden_verifier",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "utility_set_count",
        "model_requests",
        "model_attempts",
        "model_total_tokens",
        "slot_acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
        "search_calls",
        "fetch_failures",
        "search_total_tokens",
        "hosted_search_attempts",
        "hosted_search_deadline_failures",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
    )
    booleans = (
        "all_parent_artifacts_valid",
        "effect_accounting_complete",
        "structural_shared_normalization",
        "partition_precedes_fetch_candidate",
        "source_partition_disjoint",
        "hidden_verifier_prompt_excluded",
        "hidden_verifier_no_new_candidate",
        "parent_support_ids_reused",
        "observed_pages_respect_frozen_partition",
        "parent_semantic_catalog_present",
        "final_candidate_nonidentity",
        "deadline_exhausted",
        "private_replay_valid",
        "passed",
    )
    numerics = (
        "wall_seconds",
        "proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
        "slot_total_wait_seconds",
        "slot_max_wait_seconds",
    )
    checks = value.get("checks")
    if (
        isinstance(value.get("ordinal"), bool)
        or not isinstance(value.get("ordinal"), int)
        or not 1 <= int(value["ordinal"]) <= SELECTED
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in counts
        )
        or any(not isinstance(value.get(name), bool) for name in booleans)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in numerics
        )
        or not isinstance(value.get("slot_acquisition_counts"), list)
        or len(value["slot_acquisition_counts"]) != MODEL_SLOT_CAP
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value["slot_acquisition_counts"])
        or sum(value["slot_acquisition_counts"]) != value["slot_acquisitions"]
        or value["selected_source_count"]
        != value["proposal_source_count"] + value["verifier_source_count"]
        or value["verifier_source_count"] > value["verifier_source_cap"]
        or value["verifier_source_cap"] not in {0, 1}
        or value["hidden_verifier_fetch_calls"] != value["verifier_source_count"]
        or value["candidate_changed_cells_after_hidden_verifier"]
        > value["candidate_changed_cells_before_hidden_verifier"]
        or value["hidden_verifier_reverted_cells"]
        != value["candidate_changed_cells_before_hidden_verifier"]
        - value["candidate_changed_cells_after_hidden_verifier"]
        or value["hidden_verifier_admitted_cells"]
        != value["candidate_changed_cells_after_hidden_verifier"]
        or value["final_candidate_nonidentity"]
        is not (value["candidate_changed_cells_after_hidden_verifier"] > 0)
        or value["utility_aligned_entropy_credit_nats"]
        > value["proposal_conditional_entropy_reduction_nats"] + 1e-12
        or (
            value["observed_pages_respect_frozen_partition"] is False
            and value["candidate_changed_cells_after_hidden_verifier"] != 0
        )
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or dict(checks) != _task_checks(value)
        or value["passed"] is not all(checks.values())
    ):
        raise RuntimeError("V2.43.57 task projection drifted")
    return dict(value)


def _local_failure(ordinal: int) -> dict[str, Any]:
    value = {
        "ordinal": ordinal,
        "wall_seconds": 0.0,
        "parent_taxonomy": "local_projection_failure",
        "all_parent_artifacts_valid": False,
        "completion_kind": None,
        "effect_accounting_complete": False,
        "structural_shared_normalization": False,
        "partition_precedes_fetch_candidate": False,
        "source_partition_disjoint": False,
        "hidden_verifier_prompt_excluded": False,
        "hidden_verifier_no_new_candidate": False,
        "parent_support_ids_reused": False,
        "observed_pages_respect_frozen_partition": False,
        "parent_semantic_catalog_present": False,
        "selected_source_count": 0,
        "proposal_source_count": 0,
        "verifier_source_count": 0,
        "verifier_source_cap": 0,
        "parent_proposal_page_count": 0,
        "hidden_verifier_page_count": 0,
        "parent_fetch_calls": 0,
        "hidden_verifier_fetch_calls": 0,
        "total_fetch_calls": 0,
        "parent_eligible_support_set_count": 0,
        "candidate_changed_cells_before_hidden_verifier": 0,
        "candidate_changed_cells_after_hidden_verifier": 0,
        "hidden_verifier_admitted_cells": 0,
        "hidden_verifier_reverted_cells": 0,
        "proposal_conditional_entropy_reduction_nats": 0.0,
        "utility_aligned_entropy_credit_nats": 0.0,
        "utility_set_count": 0,
        "final_candidate_nonidentity": False,
        "model_requests": 0,
        "model_attempts": 0,
        "model_total_tokens": 0,
        "slot_acquisitions": 0,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "slot_total_wait_seconds": 0.0,
        "slot_max_wait_seconds": 0.0,
        "slot_acquisition_counts": [0] * MODEL_SLOT_CAP,
        "search_calls": 0,
        "fetch_failures": 0,
        "search_total_tokens": 0,
        "hosted_search_attempts": 0,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": True,
        "private_replay_valid": False,
    }
    value["checks"] = _task_checks(value)
    value["passed"] = False
    validate_task_projection(value)
    return value


def _run_one(
    root: Path,
    output_root: Path,
    slots: Path,
    directory: Path,
    ordinal: int,
) -> dict[str, Any]:
    result_path = directory / "result.json"
    model_path = directory / "model_slot_receipt.json"
    transport_path = directory / "transport_health.json"

    def result_validator(value: Mapping[str, Any]) -> object:
        envelope = validate_envelope(value)
        if model_path.is_file() and transport_path.is_file():
            validate_observed_bundle(
                envelope,
                model_slot_receipt=json.loads(model_path.read_text(encoding="utf-8")),
                transport_health=json.loads(transport_path.read_text(encoding="utf-8")),
                expected_cap=MODEL_SLOT_CAP,
            )
        return envelope

    outcome = run_observed_subprocess(
        cwd=root,
        output_root=output_root,
        directory=directory,
        command=[
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / RUNNER_MARKER),
            "child",
            "--ordinal",
            str(ordinal),
            "--output-root",
            str(output_root),
            "--directory",
            str(directory),
            "--slots",
            str(slots),
        ],
        environment=_environment(),
        timeout_seconds=PARENT_TIMEOUT_SECONDS,
        result_validator=result_validator,
        model_receipt_validator=lambda value: validate_model_receipt(
            value, expected_cap=MODEL_SLOT_CAP
        ),
        transport_receipt_validator=validate_transport_health,
        result_name="result.json",
        model_receipt_name="model_slot_receipt.json",
        transport_receipt_name="transport_health.json",
        terminal_name="child_terminal_receipt.json",
        parent_name="parent_exit_receipt.json",
    )
    parent = validate_parent_receipt(outcome.receipt)
    envelope = (
        json.loads(result_path.read_text(encoding="utf-8"))
        if parent["failure_taxonomy"] == "success"
        else None
    )
    return _task_projection(ordinal, parent, envelope)


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]], batch_wall_seconds: float
) -> dict[str, Any]:
    values = [dict(task) for task in tasks]
    [validate_task_projection(task) for task in values]
    values.sort(key=lambda item: item["ordinal"])
    completion_counts = Counter(str(task["completion_kind"]) for task in values)
    summary = {
        "selected": len(values),
        "terminal_success_tasks": sum(task["parent_taxonomy"] == "success" for task in values),
        "structurally_passed_tasks": sum(task["passed"] is True for task in values),
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "throughput_tasks_per_minute": round(len(values) / max(float(batch_wall_seconds), 1e-9) * 60, 6),
        "completion_kinds": dict(sorted(completion_counts.items())),
        "explicit_partition_observed_tasks": sum(task["observed_pages_respect_frozen_partition"] is True for task in values),
        "parent_semantic_catalog_tasks": sum(task["parent_semantic_catalog_present"] is True for task in values),
        "hidden_page_tasks": sum(task["hidden_verifier_page_count"] > 0 for task in values),
        "parent_eligible_support_tasks": sum(task["parent_eligible_support_set_count"] > 0 for task in values),
        "parent_eligible_support_set_count": sum(task["parent_eligible_support_set_count"] for task in values),
        "parent_candidate_tasks": sum(task["candidate_changed_cells_before_hidden_verifier"] > 0 for task in values),
        "utility_aligned_tasks": sum(task["utility_aligned_entropy_credit_nats"] > 0 for task in values),
        "final_nonidentity_tasks": sum(task["final_candidate_nonidentity"] is True for task in values),
        "hidden_verifier_admitted_cells": sum(task["hidden_verifier_admitted_cells"] for task in values),
        "hidden_verifier_reverted_cells": sum(task["hidden_verifier_reverted_cells"] for task in values),
        "proposal_conditional_entropy_reduction_nats": round(sum(task["proposal_conditional_entropy_reduction_nats"] for task in values), 12),
        "utility_aligned_entropy_credit_nats": round(sum(task["utility_aligned_entropy_credit_nats"] for task in values), 12),
        "proposal_sources": sum(task["proposal_source_count"] for task in values),
        "verifier_sources": sum(task["verifier_source_count"] for task in values),
        "proposal_pages": sum(task["parent_proposal_page_count"] for task in values),
        "hidden_verifier_pages": sum(task["hidden_verifier_page_count"] for task in values),
        "model_requests": sum(task["model_requests"] for task in values),
        "model_attempts": sum(task["model_attempts"] for task in values),
        "model_total_tokens": sum(task["model_total_tokens"] for task in values),
        "slot_acquisitions": sum(task["slot_acquisitions"] for task in values),
        "slot_timeouts": sum(task["slot_timeouts"] for task in values),
        "provider_deadline_failures": sum(task["provider_deadline_failures"] for task in values),
        "slot_total_wait_seconds": round(sum(task["slot_total_wait_seconds"] for task in values), 6),
        "slot_max_wait_seconds": round(max((task["slot_max_wait_seconds"] for task in values), default=0), 6),
        "search_calls": sum(task["search_calls"] for task in values),
        "fetch_calls": sum(task["total_fetch_calls"] for task in values),
        "fetch_failures": sum(task["fetch_failures"] for task in values),
        "hosted_search_attempts": sum(task["hosted_search_attempts"] for task in values),
        "hosted_search_deadline_failures": sum(task["hosted_search_deadline_failures"] for task in values),
        "hard_fetch_helper_calls": sum(task["hard_fetch_helper_calls"] for task in values),
        "hard_fetch_deadline_failures": sum(task["hard_fetch_deadline_failures"] for task in values),
        "fetch_deadline_rejections": sum(task["fetch_deadline_rejections"] for task in values),
        "fetch_helper_failures": sum(task["fetch_helper_failures"] for task in values),
        "deadline_exhausted_tasks": sum(task["deadline_exhausted"] is True for task in values),
        "all_private_replay_valid": all(task["private_replay_valid"] is True for task in values),
        "all_source_partitions_disjoint": all(task["source_partition_disjoint"] is True for task in values),
        "all_hidden_pages_excluded_from_parent_prompt": all(task["hidden_verifier_prompt_excluded"] is True for task in values),
        "all_fetch_budgets_conserved": all(task["checks"]["fetch_budget_transport_conserved"] is True for task in values),
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    checks = {
        "exact_selected": len(values) == SELECTED,
        "exact_ordinal_vector": [task["ordinal"] for task in values] == list(range(1, SELECTED + 1)),
        "all_tasks_structurally_passed": summary["structurally_passed_tasks"] == SELECTED,
        "batch_wall_within_ceiling": summary["batch_wall_seconds"] <= GATES["maximum_batch_wall_seconds"],
        "slot_timeouts": summary["slot_timeouts"] <= GATES["maximum_slot_timeouts"],
        "provider_deadline_failures": summary["provider_deadline_failures"] <= GATES["maximum_provider_deadline_failures"],
        "hosted_search_deadline_failures": summary["hosted_search_deadline_failures"] <= GATES["maximum_hosted_search_deadline_failures"],
        "hard_fetch_deadline_failures": summary["hard_fetch_deadline_failures"] <= GATES["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": summary["fetch_helper_failures"] <= GATES["maximum_fetch_helper_failures"],
        "deadline_exhausted_tasks": summary["deadline_exhausted_tasks"] <= GATES["maximum_deadline_exhausted_tasks"],
        "explicit_partition_observed_tasks": summary["explicit_partition_observed_tasks"] >= GATES["minimum_explicit_partition_observed_tasks"],
        "parent_semantic_catalog_tasks": summary["parent_semantic_catalog_tasks"] >= GATES["minimum_parent_semantic_catalog_tasks"],
        "hidden_page_tasks": summary["hidden_page_tasks"] >= GATES["minimum_hidden_page_tasks"],
        "parent_candidate_tasks": summary["parent_candidate_tasks"] >= GATES["minimum_parent_candidate_tasks"],
        "utility_aligned_tasks": summary["utility_aligned_tasks"] >= GATES["minimum_utility_aligned_tasks"],
        "final_nonidentity_tasks": summary["final_nonidentity_tasks"] >= GATES["minimum_final_nonidentity_tasks"],
        "utility_final_alignment": summary["utility_aligned_tasks"] == summary["final_nonidentity_tasks"],
        "admitted_cell_conservation": summary["hidden_verifier_admitted_cells"] >= summary["final_nonidentity_tasks"],
        "all_private_replay_valid": summary["all_private_replay_valid"] is True,
        "all_source_partitions_disjoint": summary["all_source_partitions_disjoint"] is True,
        "all_hidden_pages_excluded_from_parent_prompt": summary["all_hidden_pages_excluded_from_parent_prompt"] is True,
        "all_fetch_budgets_conserved": summary["all_fetch_budgets_conserved"] is True,
    }
    return {**summary, "checks": checks, "passed": all(checks.values())}


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    encoded = json.dumps(value, ensure_ascii=False)
    aggregate = value.get("aggregate")
    if (
        value.get("role") != "v24357_explicit_partition_external_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(aggregate, Mapping)
        or value.get("selected") != SELECTED
        or value.get("executor_count") != EXECUTOR_COUNT
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("temporary_execution_directory_remaining") is not False
        or value.get("task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("resume_retry_skip_or_revaluation") is not False
        or value.get("passed") is not aggregate.get("passed")
        or seal != payload_sha256(unsigned)
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
    ):
        raise RuntimeError("V2.43.57 public result drifted or contains task content")
    return dict(value)


def _git_ready(root: Path) -> bool:
    if (
        _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
        or _git(root, "status", "--porcelain")
    ):
        return False
    try:
        _git(root, "ls-files", "--error-unmatch", str(EXECUTION_START))
    except subprocess.CalledProcessError:
        return False
    return True


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    if not _future(root, (RESULT, DECISION, POSTAUDIT)) or not _git_ready(root):
        raise RuntimeError("V2.43.57 result/git surface is not ready")
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            directories: list[Path] = []
            for ordinal in range(1, SELECTED + 1):
                directory = output_root / f"task_{ordinal:02d}"
                directory.mkdir()
                directories.append(directory)
            tasks: list[dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=EXECUTOR_COUNT) as pool:
                futures = [
                    pool.submit(_run_one, root, output_root, slots, directory, ordinal)
                    for ordinal, directory in enumerate(directories, start=1)
                ]
                for ordinal, future in enumerate(futures, start=1):
                    try:
                        tasks.append(future.result())
                    except Exception:
                        tasks.append(_local_failure(ordinal))
            aggregate = aggregate_tasks(tasks, max(0.0, time.monotonic() - started))
        value = {
            "artifact_version": 1,
            "role": "v24357_explicit_partition_external_result",
            "protocol_id": PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": SELECTED,
            "executor_count": EXECUTOR_COUNT,
            "model_slot_cap": MODEL_SLOT_CAP,
            "aggregate": aggregate,
            "passed": aggregate["passed"],
            "temporary_execution_directory_remaining": False,
            "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "provenance": {
                "protocol_sha256": sha256(root / PROTOCOL),
                "preactivation_audit_sha256": sha256(root / PREAUDIT),
                "activation_sha256": sha256(root / ACTIVATION),
                "execution_start_sha256": sha256(root / EXECUTION_START),
                "surface_manifest_sha256": protocol["surface_manifest_sha256"],
            },
        }
        value["result_payload_sha256"] = payload_sha256(value)
        validate_public_result(value)
        publish(root / RESULT, value)
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        raise RuntimeError("V2.43.57 protected watcher identity drifted")
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = validate_public_result(_read(root, RESULT))
    passed = result["passed"] is True
    aggregate = result["aggregate"]
    observed_keys = (
        "selected",
        "terminal_success_tasks",
        "structurally_passed_tasks",
        "batch_wall_seconds",
        "throughput_tasks_per_minute",
        "completion_kinds",
        "explicit_partition_observed_tasks",
        "parent_semantic_catalog_tasks",
        "hidden_page_tasks",
        "parent_eligible_support_tasks",
        "parent_eligible_support_set_count",
        "parent_candidate_tasks",
        "utility_aligned_tasks",
        "final_nonidentity_tasks",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
        "proposal_sources",
        "verifier_sources",
        "proposal_pages",
        "hidden_verifier_pages",
        "model_requests",
        "slot_timeouts",
        "provider_deadline_failures",
        "hosted_search_deadline_failures",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
        "deadline_exhausted_tasks",
    )
    value = {
        "artifact_version": 1,
        "role": "v24357_explicit_partition_external_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "explicit_partition_external_go" if passed else "explicit_partition_external_no_go",
        "passed": passed,
        "failed_checks": sorted(name for name, check in aggregate["checks"].items() if not check),
        "observed": {key: aggregate[key] for key in observed_keys},
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
        },
        "claim_scope": {
            "benchmark_external_real_web_explicit_partition_activation_measured": True,
            "parent_support_binding_and_hidden_prompt_boundary_measured": True,
            "independent_utility_aligned_entropy_credit_measured": True,
            "benchmark_quality_measured": False,
            "entropy_quality_improvement_proven": False,
            "future_population_or_sota_supported": False,
        },
        "authorization": {
            "fresh_paired_dev64_design": passed,
            "fresh_paired_dev64_launch": False,
            "new_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return value


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    decision = _read(root, DECISION)
    findings: list[str] = []
    if lease_observation(root, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    if protected_watcher_snapshot() != _read(root, EXECUTION_START)["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24357_explicit_partition_external_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(root / RESULT),
        "decision_sha256": sha256(root / DECISION),
        "decision_status": decision["status"],
        "temporary_execution_directory_remaining": False,
        "shared_api_lease_active": False,
        "protected_watchers": protected_watcher_snapshot(),
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_paired_dev64_design": decision["passed"] and not findings,
            "fresh_paired_dev64_launch": False,
            "new_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("protocol", "preaudit", "activation", "start", "run", "finalize", "child"),
    )
    parser.add_argument("--ordinal")
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--slots")
    args = parser.parse_args()
    if args.command == "protocol":
        publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe()
    elif args.command == "finalize":
        publish(ROOT / DECISION, build_decision())
        publish(ROOT / POSTAUDIT, build_postaudit())
    elif args.command == "child":
        _child(args)


if __name__ == "__main__":
    main()
