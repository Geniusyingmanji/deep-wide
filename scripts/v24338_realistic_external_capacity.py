#!/usr/bin/env python3
"""Benchmark-external realistic 4/8-executor capacity ladder for V2.43.36.

Eight heterogeneous visible-only public-web tasks exercise the same programmatic
support runtime under a shared cross-process GPT cap of two.  The level-4 and
level-8 batches use disjoint task sets; nothing is resumed or selectively
retried. Persistent output is content-free aggregate accounting only.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import socket
import statistics
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

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import parent_receipt, validate_parent_receipt  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import run_child_with_terminal_receipt, run_observed_subprocess  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model_receipt  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import DeadlineAwareNativeSearchClient, validate_transport_health  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256, protected_watcher_snapshot, sha256  # noqa: E402
from deepwide_agent.v24336_programmatic_support_runner import build_envelope, run_v24336_task, validate_envelope, validate_observed_bundle  # noqa: E402
from scripts import v24337_programmatic_support_transport_smoke as parent  # noqa: E402
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260803"
PROTOCOL_ID = "v24338_realistic_external_programmatic_support_capacity_v1"
PROTOCOL = Path(f"results/v24338_realistic_capacity_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24338_realistic_capacity_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24338_realistic_capacity_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24338_realistic_capacity_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24338_realistic_capacity_result_v1_{DATE}.json")
DECISION = Path(f"results/v24338_realistic_capacity_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24338_realistic_capacity_postresult_audit_v1_{DATE}.json")
PARENT_DECISION = parent.DECISION
PARENT_AUDIT = parent.POSTAUDIT
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24338_realistic_external_capacity_v1"
LEASE_PURPOSE = "benchmark_external_realistic_programmatic_support_capacity_4_8"
RUNNER_MARKER = "scripts/v24338_realistic_external_capacity.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
MODEL_SLOT_CAP = 2
LEVELS = (4, 8)
TASK_WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
LEVEL_BATCH_WALL_CEILINGS = {4: 180.0, 8: 300.0}
MAXIMUM_SLOT_TIMEOUTS = 0
MAXIMUM_PROVIDER_DEADLINE_FAILURES = 0
MAXIMUM_HARD_FETCH_DEADLINE_FAILURES = 4
MAXIMUM_FETCH_HELPER_FAILURES = 4
MAXIMUM_DEADLINE_EXHAUSTED_TASKS = 0
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24333_programmatic_support_catalog.py",
    "src/deepwide_agent/v24334_support_catalog_revision_gate.py",
    "src/deepwide_agent/v24335_programmatic_support_runtime.py",
    "src/deepwide_agent/v24336_programmatic_support_runner.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/deepwide_api_lease.py",
    "scripts/v24338_realistic_external_capacity.py",
    "tests/test_v24338_realistic_external_capacity.py",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(value) for value in SECRET_PREFIXES) + r")[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
URL = re.compile(r"https?://", re.IGNORECASE)
CONTENT_LITERALS = (
    "Python Software Foundation",
    "World Health Organization",
    "International Monetary Fund",
    "European Space Agency",
    "Nobel Foundation",
)
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
QUESTIONS = (
    "Use public web sources to return one Markdown table about Python Software Foundation, Linux Foundation, and Apache Software Foundation. The column names are: Organization, Headquarters country. Return one table only.",
    "Use public web sources to return one Markdown table about World Health Organization, International Monetary Fund, and World Bank. The column names are: Organization, Headquarters city. Return one table only.",
    "Use public web sources to return one Markdown table about European Space Agency, NASA, and JAXA. The column names are: Agency, Founding year. Return one table only.",
    "Use public web sources to return one Markdown table about Nobel Foundation, Wikimedia Foundation, and Mozilla Foundation. The column names are: Organization, Founding year. Return one table only.",
    "Use public web sources to return one Markdown table about University of Oxford, University of Cambridge, and Imperial College London. The column names are: University, City. Return one table only.",
    "Use public web sources to return one Markdown table about Boeing 787, Airbus A350, and Embraer E195-E2. The column names are: Aircraft, First flight year. Return one table only.",
    "Use public web sources to return one Markdown table about Mount Everest, K2, and Kangchenjunga. The column names are: Mountain, Elevation metres. Return one table only.",
    "Use public web sources to return one Markdown table about Mercury, Venus, and Mars. The column names are: Planet, Mean radius kilometres. Return one table only.",
    "Use public web sources to return one Markdown table about UNESCO, UNICEF, and UNDP. The column names are: Organization, Headquarters city. Return one table only.",
    "Use public web sources to return one Markdown table about Git, Mercurial, and Subversion. The column names are: Software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Tokyo, Seoul, and Singapore. The column names are: City, Country. Return one table only.",
    "Use public web sources to return one Markdown table about Hubble Space Telescope, James Webb Space Telescope, and Kepler Space Telescope. The column names are: Telescope, Launch year. Return one table only.",
)


def neutral_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= 12:
        raise ValueError("V2.43.38 neutral ordinal is invalid")
    return validate_visible_task({"opaque_id": f"task_{0x243380 + ordinal:024x}", "question": QUESTIONS[ordinal - 1]})


def level_ordinals(level: int) -> list[int]:
    if level == 4:
        return list(range(1, 5))
    if level == 8:
        return list(range(5, 13))
    raise ValueError("V2.43.38 level drifted")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if raw.is_absolute() or ".." in raw.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError("V2.43.38 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.38 expected a JSON object")
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


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.43.38 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _port_listening() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    decision = _read(root, PARENT_DECISION)
    audit = _read(root, PARENT_AUDIT)
    if (
        decision.get("role") != "v24337_programmatic_support_transport_decision"
        or decision.get("status") != "neutral_transport_go"
        or decision.get("passed") is not True
        or decision.get("authorization", {}).get("realistic_external_capacity_ladder_design") is not True
        or not _sealed(decision, "decision_payload_sha256")
        or audit.get("role") != "v24337_programmatic_support_transport_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("realistic_external_capacity_ladder_design") is not True
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.38 parent evidence drifted")
    return decision, audit


def _future(root: Path, paths: Sequence[Path]) -> bool:
    return all(not (root / path).exists() and not (root / path).is_symlink() for path in paths)


def build_protocol(root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    LIMITS.validate()
    tasks = [neutral_task(index) for index in range(1, 13)]
    if require_pristine and not _future(root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.43.38 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24338_realistic_external_capacity_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"decision_path": str(PARENT_DECISION), "decision_sha256": sha256(root / PARENT_DECISION), "audit_path": str(PARENT_AUDIT), "audit_sha256": sha256(root / PARENT_AUDIT)},
        "scope": "benchmark_external_heterogeneous_realistic_capacity_levels_4_8",
        "task_contract": {"selected": 12, "levels": list(LEVELS), "level_task_counts": {"4": 4, "8": 8}, "level_ordinal_vectors": {"4": level_ordinals(4), "8": level_ordinals(8)}, "levels_use_disjoint_tasks": True, "task_vector_validated_in_memory_before_protocol": len(tasks) == 12, "runtime_input_keys_exactly_opaque_id_and_question": True, "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False},
        "provider": {"model": "gpt-5.6-sol", "model_slot_cap": MODEL_SLOT_CAP, "reasoning_effort": "low", "service_tier": "priority", "max_retries": 2},
        "runtime": {"task_wall_seconds": TASK_WALL_SECONDS, "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS, "level_batch_wall_ceilings": {str(key): value for key, value in LEVEL_BATCH_WALL_CEILINGS.items()}, "stop_on_first_failed_level": True, "no_resume_retry_task_skip_or_selective_rerun": True},
        "gates": {"maximum_slot_timeouts": MAXIMUM_SLOT_TIMEOUTS, "maximum_provider_deadline_failures": MAXIMUM_PROVIDER_DEADLINE_FAILURES, "maximum_hard_fetch_deadline_failures": MAXIMUM_HARD_FETCH_DEADLINE_FAILURES, "maximum_fetch_helper_failures": MAXIMUM_FETCH_HELPER_FAILURES, "maximum_deadline_exhausted_tasks": MAXIMUM_DEADLINE_EXHAUSTED_TASKS, "required_all_task_accounting_complete": True, "required_private_replay_valid": True},
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {"benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False, "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False, "credential_value_read_persisted_hashed_or_emitted": False, "official_evaluator_called": False},
        "authorization": {"realistic_external_capacity_design": True, "capacity_launch": False, "benchmark_launch": False, "exact220": False, "evaluator": False, "leaderboard_or_sota": False},
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(root: Path = ROOT, *, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    tasks = [neutral_task(index) for index in range(1, 13)]
    manifest = protocol.get("surface_manifest")
    if (
        protocol.get("role") != "v24338_realistic_external_capacity_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("task_contract", {}).get("task_vector_validated_in_memory_before_protocol") is not True
        or protocol.get("task_contract", {}).get("levels") != list(LEVELS)
        or protocol.get("task_contract", {}).get("level_ordinal_vectors") != {"4": level_ordinals(4), "8": level_ordinals(8)}
        or protocol.get("provider", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(protocol.get("source_policy", {}).values())
        or protocol.get("authorization", {}).get("realistic_external_capacity_design") is not True
        or any(enabled for key, enabled in protocol.get("authorization", {}).items() if key != "realistic_external_capacity_design")
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.38 protocol drifted")
    _parent(root)
    return protocol


def _run_test() -> bool:
    completed = subprocess.run([str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / "tests/test_v24338_realistic_external_capacity.py"), "-v"], cwd=ROOT, env={"HOME": str(Path.home()), "USER": os.environ.get("USER", "azureuser"), "LOGNAME": os.environ.get("LOGNAME", "azureuser"), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180, check=False)
    return completed.returncode == 0


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    pristine = _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT))
    tests = _run_test()
    port = _port_listening()
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if not pristine: findings.append("future_surface_not_pristine")
    if not tests: findings.append("focused_tests_failed")
    if not port: findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False: findings.append("shared_api_lease_active")
    value = {"artifact_version": 1, "role": "v24338_realistic_external_capacity_preactivation_audit", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "checks": {"protocol_valid_and_sealed": True, "heterogeneous_disjoint_task_vector_frozen": True, "focused_tests_passed": tests, "keyless_proxy_listening_without_api_request": port, "shared_api_lease_inactive": lease.get("active") is False, "future_surface_pristine": pristine, "benchmark_or_evaluator_surface_authorized": False}, "protected_watchers": protected_watcher_snapshot(), "findings": findings, "audit_valid": not findings, "launch_authorized": not findings, "provenance": {"protocol_sha256": sha256(root / PROTOCOL), "parent_decision_sha256": sha256(root / PARENT_DECISION), "parent_audit_sha256": sha256(root / PARENT_AUDIT), "surface_manifest_sha256": protocol["surface_manifest_sha256"]}, "authorization": {"one_capacity_launch": not findings, "benchmark_launch": False, "exact220": False, "evaluator": False}}
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.43.38 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(); value = _read(root, PREAUDIT)
    if value.get("role") != "v24338_realistic_external_capacity_preactivation_audit" or value.get("findings") != [] or value.get("audit_valid") is not True or value.get("launch_authorized") is not True or value.get("protected_watchers") != protected_watcher_snapshot() or value.get("provenance", {}).get("protocol_sha256") != sha256(root / PROTOCOL) or not _sealed(value, "audit_payload_sha256"): raise RuntimeError("V2.43.38 preaudit drifted")
    validate_protocol(root); return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve(); protocol = validate_protocol(root); audit = validate_preaudit(root); findings: list[str] = []
    if not _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)): findings.append("activation_or_execution_surface_not_pristine")
    if lease_observation(root, Path("/proc")).get("active") is not False: findings.append("shared_api_lease_active")
    if not _port_listening(): findings.append("keyless_proxy_not_listening")
    value = {"artifact_version": 1, "role": "v24338_realistic_external_capacity_activation", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "status": "active" if not findings else "rejected", "findings": findings, "launch_authorized": not findings, "protocol_sha256": sha256(root / PROTOCOL), "preactivation_audit_sha256": sha256(root / PREAUDIT), "surface_manifest_sha256": protocol["surface_manifest_sha256"], "levels": list(LEVELS), "model_slot_cap": MODEL_SLOT_CAP, "protected_watchers": audit["protected_watchers"], "network_model_search_fetch_evaluator_or_api_called": False, "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False, "authorization": {"one_capacity_launch": not findings, "benchmark_launch": False, "exact220": False, "evaluator": False}}
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.43.38 activation failed")
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(); value = _read(root, ACTIVATION)
    if value.get("role") != "v24338_realistic_external_capacity_activation" or value.get("status") != "active" or value.get("findings") != [] or value.get("launch_authorized") is not True or value.get("protocol_sha256") != sha256(root / PROTOCOL) or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT) or value.get("protected_watchers") != protected_watcher_snapshot() or not _sealed(value, "activation_payload_sha256"): raise RuntimeError("V2.43.38 activation drifted")
    validate_preaudit(root); return value


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20).stdout.strip()


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve(); validate_protocol(root); activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)): raise RuntimeError("V2.43.38 execution surface is not pristine")
    head = _git(root, "rev-parse", "HEAD"); remote = _git(root, "rev-parse", "target/main"); findings: list[str] = []
    if head != remote: findings.append("activation_commit_not_pushed")
    if lease_observation(root, Path("/proc")).get("active") is not False: findings.append("shared_api_lease_active")
    if not _port_listening(): findings.append("keyless_proxy_not_listening")
    value = {"artifact_version": 1, "role": "v24338_realistic_external_capacity_execution_start", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "status": "ready" if not findings else "rejected", "findings": findings, "execution_authorized": not findings, "activation_base_commit": head, "target_main_at_start": remote, "protocol_sha256": sha256(root / PROTOCOL), "activation_sha256": sha256(root / ACTIVATION), "levels": list(LEVELS), "model_slot_cap": MODEL_SLOT_CAP, "protected_watchers": activation["protected_watchers"], "api_called_before_execution_start": False, "runtime_input_exactly_opaque_id_and_question": True, "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False, "benchmark_or_evaluator_authorized": False}
    value["execution_start_payload_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.43.38 execution start failed")
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(); value = _read(root, EXECUTION_START)
    if value.get("role") != "v24338_realistic_external_capacity_execution_start" or value.get("status") != "ready" or value.get("findings") != [] or value.get("execution_authorized") is not True or value.get("protocol_sha256") != sha256(root / PROTOCOL) or value.get("activation_sha256") != sha256(root / ACTIVATION) or value.get("protected_watchers") != protected_watcher_snapshot() or value.get("api_called_before_execution_start") is not False or not _sealed(value, "execution_start_payload_sha256"): raise RuntimeError("V2.43.38 execution-start drifted")
    validate_activation(root); return value


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle: json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _child(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal); task = neutral_task(ordinal); output_root = Path(args.output_root); directory = Path(args.directory); result_path = directory / "result.json"; model_path = directory / "model_slot_receipt.json"; transport_path = directory / "transport_health.json"
    def action() -> None:
        started = time.monotonic(); deadline = started + TASK_WALL_SECONDS
        model = build_deadline_model(url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses", model_name="gpt-5.6-sol", reasoning_effort="low", service_tier="priority", static_timeout_seconds=TASK_WALL_SECONDS, max_retries=2, slot_directory=Path(args.slots), output_root=output_root, slot_cap=MODEL_SLOT_CAP, pool_id=POOL_ID, absolute_deadline=deadline, cleanup_reserve_seconds=5.0, minimum_attempt_seconds=0.05)
        search = DeadlineAwareNativeSearchClient(f"http://{PROXY_HOST}:{PROXY_PORT}/responses", "gpt-5.6-sol", reasoning_effort="low", service_tier="priority", timeout=TASK_WALL_SECONDS, max_retries=2, max_workers=1, batch_size=8, search_context_size="medium", max_output_tokens=7_000, fetch_pages=False, fetch_workers=8, fetch_timeout=20, max_page_chars=LIMITS.page_chars, hard_fetch_deadline_seconds=25, absolute_deadline=deadline, cleanup_reserve_seconds=5.0, minimum_attempt_seconds=0.05)
        outcome = run_v24336_task(task, model=model, search=search, limits=LIMITS, monotonic=time.monotonic); _write_new(model_path, outcome.model_slot_receipt); _write_new(transport_path, outcome.transport_health); _write_new(result_path, build_envelope(outcome))
    run_child_with_terminal_receipt(output_root=output_root, directory=directory, action=action, result_name="result.json", model_receipt_name="model_slot_receipt.json", transport_receipt_name="transport_health.json", terminal_name="child_terminal_receipt.json")


def _environment() -> dict[str, str]:
    return {"HOME": str(Path.home()), "USER": os.environ.get("USER", "azureuser"), "LOGNAME": os.environ.get("LOGNAME", "azureuser"), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}


def _task_projection(ordinal: int, parent_receipt_value: Mapping[str, Any], envelope: Mapping[str, Any] | None) -> dict[str, Any]:
    validate_parent_receipt(parent_receipt_value); wrapped = envelope.get("result") if isinstance(envelope, Mapping) else None; core = wrapped.get("core_result") if isinstance(wrapped, Mapping) else None; support = wrapped.get("support_runtime_receipt") if isinstance(wrapped, Mapping) else None; slot = envelope.get("model_slot_receipt") if isinstance(envelope, Mapping) else None; transport = envelope.get("transport_health") if isinstance(envelope, Mapping) else None; receipt = core.get("shared_prefix_revision_receipt") if isinstance(core, Mapping) else None; prefix = receipt.get("prefix_bundle") if isinstance(receipt, Mapping) else None; cost = core.get("cost") if isinstance(core, Mapping) else None; model_cost = cost.get("model") if isinstance(cost, Mapping) else None; search_cost = cost.get("search") if isinstance(cost, Mapping) else None
    def integer(source: object, name: str) -> int:
        raw = source.get(name) if isinstance(source, Mapping) else None; return int(raw) if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0 else 0
    def number(source: object, name: str) -> float:
        raw = source.get(name) if isinstance(source, Mapping) else None; return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(float(raw)) and float(raw) >= 0 else 0.0
    slot_counts = slot.get("slot_acquisition_counts") if isinstance(slot, Mapping) else [0, 0]
    value = {
        "ordinal": ordinal, "wall_seconds": round(float(parent_receipt_value.get("elapsed_seconds", 0.0)), 6), "parent_taxonomy": parent_receipt_value.get("failure_taxonomy"),
        "all_parent_artifacts_valid": all(parent_receipt_value.get(name) is True for name in ("child_terminal_receipt_present", "child_terminal_receipt_valid", "result_envelope_present", "result_envelope_valid", "model_receipt_present", "model_receipt_valid", "transport_receipt_present", "transport_receipt_valid")),
        "result_status": core.get("status") if isinstance(core, Mapping) else None, "completion_kind": core.get("completion_kind") if isinstance(core, Mapping) else None, "effect_accounting_complete": receipt.get("effect_accounting_complete") if isinstance(receipt, Mapping) else None, "prefix_status": receipt.get("prefix_status") if isinstance(receipt, Mapping) else None, "prefix_producer_execution_count": prefix.get("producer_execution_count") if isinstance(prefix, Mapping) else None,
        "logical_model_admissions": integer(receipt, "logical_model_admissions"), "provider_model_requests": integer(receipt, "provider_model_requests"), "provider_model_attempts": integer(receipt, "provider_model_attempts"), "pre_provider_model_rejections": integer(receipt, "pre_provider_model_rejections"), "slot_acquisitions": integer(slot, "acquisitions"), "slot_timeouts": integer(slot, "slot_timeouts"), "provider_deadline_failures": integer(slot, "provider_deadline_failures"), "slot_total_wait_seconds": number(slot, "total_wait_seconds"), "slot_max_wait_seconds": number(slot, "max_wait_seconds"), "slot_acquisition_counts": list(slot_counts) if isinstance(slot_counts, list) else [0, 0],
        "core_logical_queries": integer(receipt, "core_logical_queries"), "search_provider_effects": integer(receipt, "core_search_provider_effects") + integer(receipt, "reserve_search_provider_effects"), "core_fetch_targets": integer(receipt, "core_fetch_targets"), "reserve_fetch_targets": integer(receipt, "reserve_fetch_targets"), "core_usable_pages": integer(receipt, "core_usable_pages"), "reserve_usable_pages": integer(receipt, "reserve_usable_pages"), "repeated_upstream_effects": sum(receipt.get(name, 0) for name in ("repeated_plan_model_effects_by_branches", "repeated_core_search_effects_by_branches", "repeated_core_fetch_effects_by_branches")) if isinstance(receipt, Mapping) else 0,
        "catalog_status": support.get("catalog_status") if isinstance(support, Mapping) else None, "catalog_target_count": integer(support, "catalog_target_count"), "catalog_page_count": integer(support, "catalog_page_count"), "catalog_independent_source_count": integer(support, "catalog_independent_source_count"), "catalog_candidate_groups_considered": integer(support, "catalog_candidate_groups_considered"), "catalog_eligible_support_set_count": integer(support, "catalog_eligible_support_set_count"), "catalog_quarantined_candidate_groups": dict(support.get("catalog_quarantined_candidate_groups", {})) if isinstance(support, Mapping) else {}, "catalog_built_before_revision": support.get("catalog_built_before_revision_model_admission") if isinstance(support, Mapping) else None, "revision_model_admitted": support.get("revision_model_admitted") if isinstance(support, Mapping) else None, "third_model_call_skipped_no_eligible_support": support.get("third_model_call_skipped_no_eligible_support") if isinstance(support, Mapping) else None, "candidate_identity_handoff": support.get("candidate_identity_handoff") if isinstance(support, Mapping) else None, "admitted_cell_changes": integer(support, "admitted_cell_changes"), "credited_entropy_positive": bool(number(support, "credited_conditional_entropy_reduction_nats") > 0), "private_replay_valid": isinstance(wrapped, Mapping),
        "model_requests": integer(model_cost, "requests"), "model_attempts": integer(model_cost, "attempts"), "model_total_tokens": integer(model_cost, "total_tokens"), "search_calls": integer(search_cost, "calls"), "fetch_calls": integer(search_cost, "fetch_calls"), "fetch_failures": integer(search_cost, "fetch_failures"), "search_total_tokens": integer(search_cost, "total_tokens"), "hosted_search_deadline_failures": integer(transport, "hosted_search_deadline_failures"), "hard_fetch_helper_calls": integer(transport, "hard_fetch_helper_calls"), "hard_fetch_deadline_failures": integer(transport, "hard_fetch_deadline_failures"), "fetch_deadline_rejections": integer(transport, "fetch_deadline_rejections"), "fetch_helper_failures": integer(transport, "fetch_helper_failures"), "deadline_exhausted": transport.get("deadline_exhausted") if isinstance(transport, Mapping) else True,
        "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False, "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["checks"] = _task_checks(value); value["passed"] = all(value["checks"].values()); validate_task_projection(value); return value


def _task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "parent_success": value.get("parent_taxonomy") == "success", "all_parent_artifacts_valid": value.get("all_parent_artifacts_valid") is True, "result_completed": value.get("result_status") == "completed", "effect_accounting_complete": value.get("effect_accounting_complete") is True, "prefix_frozen_once": value.get("prefix_status") == "frozen" and value.get("prefix_producer_execution_count") == 1,
        "model_effect_range": 2 <= value.get("logical_model_admissions", 0) <= 3, "model_conservation": value.get("logical_model_admissions") == value.get("slot_acquisitions") + value.get("slot_timeouts") and value.get("provider_model_requests") == value.get("slot_acquisitions") and value.get("pre_provider_model_rejections") == value.get("slot_timeouts"), "no_slot_or_provider_deadline_failure": value.get("slot_timeouts") == 0 and value.get("provider_deadline_failures") == 0, "four_logical_queries": value.get("core_logical_queries") == 4, "hosted_search_effect": 1 <= value.get("search_provider_effects", 0) <= 2, "exact_core_reserve_fetch_targets": value.get("core_fetch_targets") == 7 and value.get("reserve_fetch_targets") == 3, "core_and_reserve_usable": value.get("core_usable_pages", 0) >= 1 and value.get("reserve_usable_pages", 0) >= 1, "catalog_built_and_replayed": value.get("catalog_status") in {"built_empty", "built_eligible"} and value.get("catalog_built_before_revision") is True and value.get("private_replay_valid") is True, "revision_policy_consistent": (value.get("catalog_status") == "built_empty" and value.get("revision_model_admitted") is False and value.get("third_model_call_skipped_no_eligible_support") is True) or (value.get("catalog_status") == "built_eligible" and value.get("revision_model_admitted") is True), "fetch_conservation": value.get("fetch_calls") == value.get("hard_fetch_helper_calls") + value.get("fetch_deadline_rejections"), "deadline_not_exhausted": value.get("deadline_exhausted") is False, "no_repeated_upstream_effect": value.get("repeated_upstream_effects") == 0, "within_parent_wall": value.get("wall_seconds", 10**9) <= PARENT_TIMEOUT_SECONDS,
    }


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(value, ensure_ascii=False)
    if value.get("passed") is not all(value.get("checks", {}).values()) or value.get("task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted") is not False or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False or OPAQUE.search(encoded) or URL.search(encoded) or SECRET.search(encoded) or any(literal in encoded for literal in CONTENT_LITERALS): raise RuntimeError("V2.43.38 task projection drifted or contains content")
    if not isinstance(value.get("slot_acquisition_counts"), list) or len(value["slot_acquisition_counts"]) != MODEL_SLOT_CAP or sum(value["slot_acquisition_counts"]) != value.get("slot_acquisitions"): raise RuntimeError("V2.43.38 slot projection drifted")
    return dict(value)


def summarize_level(level: int, tasks: Sequence[Mapping[str, Any]], batch_wall_seconds: float) -> dict[str, Any]:
    if level not in LEVELS or len(tasks) != level: raise RuntimeError("V2.43.38 level shape drifted")
    values = [dict(task) for task in tasks]; [validate_task_projection(task) for task in values]; values.sort(key=lambda item: item["ordinal"]); walls = [float(task["wall_seconds"]) for task in values]; batch = max(0.0, float(batch_wall_seconds)); kinds = Counter(task["catalog_status"] for task in values)
    checks = {"exact_ordinals": [task["ordinal"] for task in values] == level_ordinals(level), "all_tasks_passed": all(task["passed"] for task in values), "batch_wall_within_ceiling": batch <= LEVEL_BATCH_WALL_CEILINGS[level], "aggregate_slot_conservation": sum(sum(task["slot_acquisition_counts"]) for task in values) == sum(task["slot_acquisitions"] for task in values), "slot_timeouts": sum(task["slot_timeouts"] for task in values) <= MAXIMUM_SLOT_TIMEOUTS, "provider_deadline_failures": sum(task["provider_deadline_failures"] for task in values) <= MAXIMUM_PROVIDER_DEADLINE_FAILURES, "hard_fetch_deadline_failures": sum(task["hard_fetch_deadline_failures"] for task in values) <= MAXIMUM_HARD_FETCH_DEADLINE_FAILURES, "fetch_helper_failures": sum(task["fetch_helper_failures"] for task in values) <= MAXIMUM_FETCH_HELPER_FAILURES, "deadline_exhausted_tasks": sum(task["deadline_exhausted"] is True for task in values) <= MAXIMUM_DEADLINE_EXHAUSTED_TASKS}
    return {"executor_count": level, "selected": level, "model_slot_cap": MODEL_SLOT_CAP, "batch_wall_seconds": round(batch, 6), "batch_wall_ceiling_seconds": LEVEL_BATCH_WALL_CEILINGS[level], "throughput_tasks_per_minute": round(level / batch * 60, 6), "task_wall_sum_seconds": round(sum(walls), 6), "task_wall_mean_seconds": round(statistics.mean(walls), 6), "task_wall_p95_seconds": round(sorted(walls)[math.ceil(0.95 * len(walls)) - 1], 6), "task_wall_max_seconds": round(max(walls), 6), "model_requests": sum(task["model_requests"] for task in values), "model_attempts": sum(task["model_attempts"] for task in values), "slot_acquisitions": sum(task["slot_acquisitions"] for task in values), "slot_timeouts": sum(task["slot_timeouts"] for task in values), "slot_total_wait_seconds": round(sum(task["slot_total_wait_seconds"] for task in values), 6), "slot_max_wait_seconds": round(max(task["slot_max_wait_seconds"] for task in values), 6), "provider_deadline_failures": sum(task["provider_deadline_failures"] for task in values), "fetch_calls": sum(task["fetch_calls"] for task in values), "hard_fetch_deadline_failures": sum(task["hard_fetch_deadline_failures"] for task in values), "fetch_helper_failures": sum(task["fetch_helper_failures"] for task in values), "deadline_exhausted_tasks": sum(task["deadline_exhausted"] is True for task in values), "catalog_statuses": dict(sorted(kinds.items())), "catalog_eligible_support_sets": sum(task["catalog_eligible_support_set_count"] for task in values), "revision_model_admitted_tasks": sum(task["revision_model_admitted"] is True for task in values), "third_model_call_skipped_tasks": sum(task["third_model_call_skipped_no_eligible_support"] is True for task in values), "entropy_positive_tasks": sum(task["credited_entropy_positive"] is True for task in values), "candidate_nonidentity_tasks": sum(task["candidate_identity_handoff"] is False for task in values), "tasks": values, "checks": checks, "passed": all(checks.values())}


def _local_failure(ordinal: int, directory: Path | None = None) -> dict[str, Any]:
    parent_path = directory / "parent_exit_receipt.json" if directory else None
    model_path = directory / "model_slot_receipt.json" if directory else None
    transport_path = directory / "transport_health.json" if directory else None
    parent_value = parent_receipt(return_code=None, timed_out=False, elapsed_seconds=0, subprocess_exception=True, child_terminal_receipt_present=False, child_terminal_receipt_valid=False, result_envelope_present=False, result_envelope_valid=False, model_receipt_present=False, model_receipt_valid=False, transport_receipt_present=False, transport_receipt_valid=False)
    if parent_path is not None and parent_path.is_file() and not parent_path.is_symlink():
        try: parent_value = validate_parent_receipt(json.loads(parent_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError): pass
    value = _task_projection(ordinal, parent_value, None)
    if model_path is not None and model_path.is_file() and not model_path.is_symlink():
        try:
            model = validate_model_receipt(json.loads(model_path.read_text(encoding="utf-8")), expected_cap=MODEL_SLOT_CAP)
            value.update({"slot_acquisitions": int(model["acquisitions"]), "slot_timeouts": int(model["slot_timeouts"]), "provider_deadline_failures": int(model["provider_deadline_failures"]), "slot_total_wait_seconds": float(model["total_wait_seconds"]), "slot_max_wait_seconds": float(model["max_wait_seconds"]), "slot_acquisition_counts": list(model["slot_acquisition_counts"]), "model_requests": int(model["acquisitions"]), "model_attempts": int(model["acquisitions"]), "logical_model_admissions": 0, "provider_model_requests": 0, "provider_model_attempts": 0, "pre_provider_model_rejections": 0})
        except (OSError, ValueError, json.JSONDecodeError): pass
    if transport_path is not None and transport_path.is_file() and not transport_path.is_symlink():
        try:
            transport = validate_transport_health(json.loads(transport_path.read_text(encoding="utf-8")))
            value.update({"hard_fetch_helper_calls": int(transport["hard_fetch_helper_calls"]), "hard_fetch_deadline_failures": int(transport["hard_fetch_deadline_failures"]), "fetch_deadline_rejections": int(transport["fetch_deadline_rejections"]), "fetch_helper_failures": int(transport["fetch_helper_failures"]), "hosted_search_deadline_failures": int(transport["hosted_search_deadline_failures"]), "deadline_exhausted": bool(transport["deadline_exhausted"]), "fetch_calls": int(transport["hard_fetch_helper_calls"]) + int(transport["fetch_deadline_rejections"])})
        except (OSError, ValueError, json.JSONDecodeError): pass
    value["effect_accounting_complete"] = False
    value["checks"] = _task_checks(value)
    value["passed"] = False
    return value


def _run_one(root: Path, output_root: Path, slots: Path, directory: Path, ordinal: int) -> dict[str, Any]:
    result_path = directory / "result.json"; model_path = directory / "model_slot_receipt.json"; transport_path = directory / "transport_health.json"
    def result_validator(value: Mapping[str, Any]) -> object:
        envelope = validate_envelope(value)
        if model_path.is_file() and transport_path.is_file(): validate_observed_bundle(envelope, model_slot_receipt=json.loads(model_path.read_text(encoding="utf-8")), transport_health=json.loads(transport_path.read_text(encoding="utf-8")), expected_cap=MODEL_SLOT_CAP)
        return envelope
    outcome = run_observed_subprocess(cwd=root, output_root=output_root, directory=directory, command=[str(root / ".venv-eval/bin/python"), "-I", "-B", str(root / RUNNER_MARKER), "child", "--ordinal", str(ordinal), "--output-root", str(output_root), "--directory", str(directory), "--slots", str(slots)], environment=_environment(), timeout_seconds=PARENT_TIMEOUT_SECONDS, result_validator=result_validator, model_receipt_validator=lambda value: validate_model_receipt(value, expected_cap=MODEL_SLOT_CAP), transport_receipt_validator=validate_transport_health, result_name="result.json", model_receipt_name="model_slot_receipt.json", transport_receipt_name="transport_health.json", terminal_name="child_terminal_receipt.json", parent_name="parent_exit_receipt.json")
    parent_value = validate_parent_receipt(outcome.receipt); envelope = json.loads(result_path.read_text(encoding="utf-8")) if parent_value["failure_taxonomy"] == "success" else None; return _task_projection(ordinal, parent_value, envelope)


def _git_ready(root: Path) -> bool:
    if _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main") or _git(root, "status", "--porcelain"): return False
    try: _git(root, "ls-files", "--error-unmatch", str(EXECUTION_START))
    except subprocess.CalledProcessError: return False
    return True


def run_capacity(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(); protocol = validate_protocol(root); validate_preaudit(root); activation = validate_activation(root); validate_execution_start(root)
    if not _future(root, (RESULT, DECISION, POSTAUDIT)) or not _git_ready(root): raise RuntimeError("V2.43.38 result/git surface not ready")
    levels: list[dict[str, Any]] = []
    with acquire_deepwide_api_lease(root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary); slots = output_root / "slots"; slots.mkdir(); [(slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8") for index in range(1, MODEL_SLOT_CAP + 1)]
            for level in LEVELS:
                level_root = output_root / f"level_{level:02d}"; level_root.mkdir(); ordinals = level_ordinals(level); directories = []
                for ordinal in ordinals: directory = level_root / f"task_{ordinal:02d}"; directory.mkdir(); directories.append(directory)
                started = time.monotonic()
                with concurrent.futures.ThreadPoolExecutor(max_workers=level) as pool:
                    futures = [pool.submit(_run_one, root, output_root, slots, directory, ordinal) for directory, ordinal in zip(directories, ordinals, strict=True)]; tasks = []
                    for ordinal, directory, future in zip(
                        ordinals, directories, futures, strict=True
                    ):
                        try: tasks.append(future.result())
                        except Exception: tasks.append(_local_failure(ordinal, directory))
                summary = summarize_level(level, tasks, max(0.0, time.monotonic() - started)); levels.append(summary)
                if not summary["passed"]: break
    if protected_watcher_snapshot() != activation["protected_watchers"]: raise RuntimeError("V2.43.38 watcher drifted")
    all_passed = len(levels) == len(LEVELS) and all(item["passed"] for item in levels); best = max((item for item in levels if item["passed"]), key=lambda item: item["throughput_tasks_per_minute"], default=None)
    value = {"artifact_version": 1, "role": "v24338_realistic_external_capacity_result", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()), "levels_requested": list(LEVELS), "levels_completed": [item["executor_count"] for item in levels], "levels": levels, "all_requested_levels_passed": all_passed, "recommended_executor_count": best["executor_count"] if best else None, "maximum_observed_throughput_tasks_per_minute": best["throughput_tasks_per_minute"] if best else 0, "capacity_only_exact220_projection_seconds": round(220 / best["throughput_tasks_per_minute"] * 60, 6) if best else None, "projection_is_not_benchmark_eta_or_quality_claim": True, "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False, "mapping_gold_category_question_type_split_evaluator_score_read": False, "official_evaluator_called": False, "provenance": {"protocol_sha256": sha256(root / PROTOCOL), "activation_sha256": sha256(root / ACTIVATION), "execution_start_sha256": sha256(root / EXECUTION_START), "surface_manifest_sha256": protocol["surface_manifest_sha256"]}}
    value["result_payload_sha256"] = payload_sha256(value); publish(root / RESULT, value); return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve(); result = _read(root, RESULT); passed = result.get("all_requested_levels_passed") is True
    value = {"artifact_version": 1, "role": "v24338_realistic_external_capacity_decision", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "status": "capacity_go" if passed else "capacity_no_go", "passed": passed, "recommended_executor_count": result.get("recommended_executor_count"), "maximum_observed_throughput_tasks_per_minute": result.get("maximum_observed_throughput_tasks_per_minute"), "capacity_only_exact220_projection_seconds": result.get("capacity_only_exact220_projection_seconds"), "projection_is_not_benchmark_eta_or_quality_claim": True, "provenance": {"protocol_sha256": sha256(root / PROTOCOL), "preactivation_audit_sha256": sha256(root / PREAUDIT), "activation_sha256": sha256(root / ACTIVATION), "execution_start_sha256": sha256(root / EXECUTION_START), "result_sha256": sha256(root / RESULT)}, "claim_scope": {"benchmark_external_realistic_capacity_measured": True, "benchmark_quality_measured": False, "natural_entropy_quality_improvement_proven": False, "sota_supported": False}, "authorization": {"fresh_paired_benchmark_design": passed, "benchmark_launch": False, "exact220": False, "evaluator": False, "leaderboard_or_sota": False}}
    value["decision_payload_sha256"] = payload_sha256(value); return value


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve(); decision = _read(root, DECISION); findings: list[str] = []
    if lease_observation(root, Path("/proc")).get("active") is not False: findings.append("shared_api_lease_active")
    if protected_watcher_snapshot() != _read(root, EXECUTION_START)["protected_watchers"]: findings.append("protected_watcher_identity_drifted")
    value = {"artifact_version": 1, "role": "v24338_realistic_external_capacity_postresult_audit", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "result_sha256": sha256(root / RESULT), "decision_sha256": sha256(root / DECISION), "decision_status": decision["status"], "temporary_execution_directory_remaining": False, "shared_api_lease_active": False, "protected_watchers": protected_watcher_snapshot(), "mapping_gold_category_question_type_split_evaluator_score_read": False, "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False, "network_model_search_fetch_or_evaluator_called_by_audit": False, "findings": findings, "audit_valid": not findings, "authorization": {"fresh_paired_benchmark_design": decision["passed"] and not findings, "benchmark_launch": False, "exact220": False, "evaluator": False, "leaderboard_or_sota": False}}
    value["audit_payload_sha256"] = payload_sha256(value); return value


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("protocol", "preaudit", "activation", "start", "run", "finalize", "child")); parser.add_argument("--ordinal"); parser.add_argument("--output-root"); parser.add_argument("--directory"); parser.add_argument("--slots"); args = parser.parse_args()
    if args.command == "protocol": publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit": publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation": publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start": publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run": run_capacity()
    elif args.command == "finalize": publish(ROOT / DECISION, build_decision()); publish(ROOT / POSTAUDIT, build_postaudit())
    elif args.command == "child": _child(args)


if __name__ == "__main__": main()
