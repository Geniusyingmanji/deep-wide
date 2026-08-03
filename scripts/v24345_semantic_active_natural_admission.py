#!/usr/bin/env python3
"""Benchmark-external natural-admission gate for V2.43.42/43.

Twelve fixed heterogeneous public-web tasks run once with executor concurrency
eight and a shared GPT slot cap of two.  Task-private pages, projections,
proposals, predictions, and gate results exist only inside a temporary root and
are replay-validated before deletion.  The persistent result is an aggregate of
content-free counts.  No benchmark manifest, mapping, gold, evaluator, or score
surface is imported or opened.
"""

from __future__ import annotations

import argparse
import concurrent.futures
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
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_parent_receipt,
)
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
from deepwide_agent.v24343_semantic_active_runner import (  # noqa: E402
    build_envelope,
    run_v24343_task,
    validate_envelope,
    validate_observed_bundle,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260803"
PROTOCOL_ID = "v24345_semantic_active_natural_admission_v1"
PROTOCOL = Path(f"results/v24345_natural_admission_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24345_natural_admission_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24345_natural_admission_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24345_natural_admission_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24345_natural_admission_result_v1_{DATE}.json")
DECISION = Path(f"results/v24345_natural_admission_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24345_natural_admission_postresult_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24344_semantic_active_runtime_build_audit_v1_{DATE}.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24345_semantic_active_natural_admission_v1"
LEASE_PURPOSE = "benchmark_external_semantic_active_natural_admission"
RUNNER_MARKER = "scripts/v24345_semantic_active_natural_admission.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
SELECTED = 12
EXECUTOR_COUNT = 8
MODEL_SLOT_CAP = 2
TASK_WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
BATCH_WALL_CEILING_SECONDS = 300.0
MAXIMUM_SLOT_TIMEOUTS = 0
MAXIMUM_PROVIDER_DEADLINE_FAILURES = 0
MAXIMUM_HARD_FETCH_DEADLINE_FAILURES = 4
MAXIMUM_FETCH_HELPER_FAILURES = 4
MAXIMUM_DEADLINE_EXHAUSTED_TASKS = 0
MINIMUM_BUILT_CATALOG_TASKS = 12
MINIMUM_SEMANTIC_PROJECTION_TASKS = 1
MINIMUM_ELIGIBLE_SUPPORT_TASKS = 1
MINIMUM_REVISION_ADMITTED_TASKS = 1
MINIMUM_REVISION_GATE_TASKS = 1
MINIMUM_CANDIDATE_NONIDENTITY_TASKS = 1
MINIMUM_ADMITTED_CELL_CHANGES = 1
MINIMUM_ENTROPY_POSITIVE_TASKS = 1
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
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
    "src/deepwide_agent/v24339_active_evidence_support.py",
    "src/deepwide_agent/v24341_semantic_evidence_projection.py",
    "src/deepwide_agent/v24342_semantic_active_runtime.py",
    "src/deepwide_agent/v24343_semantic_active_runner.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/v24345_semantic_active_natural_admission.py",
    "tests/test_v24345_semantic_active_natural_admission.py",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
URL = re.compile(r"https?://", re.IGNORECASE)
CONTENT_LITERALS = (
    "Apache Software Foundation",
    "Boeing 787",
    "Git",
    "Hubble Space Telescope",
    "World Health Organization",
    "Mount Everest",
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
    "Use public web sources to return one Markdown table about Apache Software Foundation, Eclipse Foundation, Blender Foundation, Open Knowledge Foundation, Document Foundation, Rust Foundation, Python Software Foundation, and Linux Foundation. The column names are: Organization, Founding year. Return one table only.",
    "Use public web sources to return one Markdown table about Boeing 787, Airbus A350, Embraer E195-E2, Bombardier Global 7500, COMAC C919, Irkut MC-21, Gulfstream G700, and HondaJet. The column names are: Aircraft, First flight year. Return one table only.",
    "Use public web sources to return one Markdown table about Git, Mercurial, Subversion, CMake, Meson, Bazel, Gradle, and Ninja. The column names are: Software, Initial release year. Return one table only.",
    "Use public web sources to return one Markdown table about Hubble Space Telescope, James Webb Space Telescope, Kepler Space Telescope, TESS, Gaia, Euclid, Chandra X-ray Observatory, and Spitzer Space Telescope. The column names are: Telescope, Launch year. Return one table only.",
    "Use public web sources to return one Markdown table about World Health Organization, International Monetary Fund, World Bank, UNESCO, UNICEF, UNDP, International Labour Organization, and World Trade Organization. The column names are: Organization, Headquarters city. Return one table only.",
    "Use public web sources to return one Markdown table about University of Oxford, University of Cambridge, Imperial College London, University College London, University of Edinburgh, University of Manchester, King's College London, and University of Bristol. The column names are: University, Founding year. Return one table only.",
    "Use public web sources to return one Markdown table about Mount Everest, K2, Kangchenjunga, Lhotse, Makalu, Cho Oyu, Dhaulagiri I, and Manaslu. The column names are: Mountain, Elevation metres. Return one table only.",
    "Use public web sources to return one Markdown table about Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. The column names are: Planet, Mean radius kilometres. Return one table only.",
    "Use public web sources to return one Markdown table about Mozilla Foundation, Wikimedia Foundation, Nobel Foundation, Raspberry Pi Foundation, GNOME Foundation, KDE e.V., Free Software Foundation, and Electronic Frontier Foundation. The column names are: Organization, Founding year. Return one table only.",
    "Use public web sources to return one Markdown table about European Space Agency, NASA, JAXA, Canadian Space Agency, Indian Space Research Organisation, Australian Space Agency, Italian Space Agency, and German Aerospace Center. The column names are: Agency, Headquarters country. Return one table only.",
    "Use public web sources to return one Markdown table about Falcon 9, Ariane 5, Atlas V, Delta IV Heavy, Electron, H-IIA, Long March 5, and Vega. The column names are: Launch vehicle, First flight year. Return one table only.",
    "Use public web sources to return one Markdown table about Ubuntu, Fedora Linux, Debian, Arch Linux, openSUSE, FreeBSD, OpenBSD, and NetBSD. The column names are: Operating system, Initial release year. Return one table only.",
)
GATES = {
    "selected": SELECTED,
    "executor_count": EXECUTOR_COUNT,
    "model_slot_cap": MODEL_SLOT_CAP,
    "maximum_batch_wall_seconds": BATCH_WALL_CEILING_SECONDS,
    "maximum_slot_timeouts": MAXIMUM_SLOT_TIMEOUTS,
    "maximum_provider_deadline_failures": MAXIMUM_PROVIDER_DEADLINE_FAILURES,
    "maximum_hard_fetch_deadline_failures": MAXIMUM_HARD_FETCH_DEADLINE_FAILURES,
    "maximum_fetch_helper_failures": MAXIMUM_FETCH_HELPER_FAILURES,
    "maximum_deadline_exhausted_tasks": MAXIMUM_DEADLINE_EXHAUSTED_TASKS,
    "minimum_built_catalog_tasks": MINIMUM_BUILT_CATALOG_TASKS,
    "minimum_semantic_projection_tasks": MINIMUM_SEMANTIC_PROJECTION_TASKS,
    "minimum_eligible_support_tasks": MINIMUM_ELIGIBLE_SUPPORT_TASKS,
    "minimum_revision_admitted_tasks": MINIMUM_REVISION_ADMITTED_TASKS,
    "minimum_revision_gate_tasks": MINIMUM_REVISION_GATE_TASKS,
    "minimum_candidate_nonidentity_tasks": MINIMUM_CANDIDATE_NONIDENTITY_TASKS,
    "minimum_admitted_cell_changes": MINIMUM_ADMITTED_CELL_CHANGES,
    "minimum_entropy_positive_tasks": MINIMUM_ENTROPY_POSITIVE_TASKS,
}


def neutral_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED:
        raise ValueError("V2.43.45 neutral ordinal is invalid")
    return validate_visible_task(
        {
            "opaque_id": f"task_{0x243450 + ordinal:024x}",
            "question": QUESTIONS[ordinal - 1],
        }
    )


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
        raise RuntimeError("V2.43.45 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.45 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
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
            raise RuntimeError("V2.43.45 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _port_listening() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _future(root: Path, values: Sequence[Path]) -> bool:
    return all(not (root / path).exists() and not (root / path).is_symlink() for path in values)


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    if (
        value.get("role") != "v24344_semantic_active_runtime_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "benchmark_external_natural_admission_probe_design"
        )
        is not True
        or value.get("authorization", {}).get("benchmark_launch") is not False
        or value.get("authorization", {}).get("new_exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.45 parent audit drifted")
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    LIMITS.validate()
    tasks = [neutral_task(index) for index in range(1, SELECTED + 1)]
    if require_pristine and not _future(
        root, (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.45 future surface is not pristine")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24345_semantic_active_natural_admission_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "scope": "benchmark_external_heterogeneous_real_web_natural_admission_gate",
        "task_contract": {
            "selected": SELECTED,
            "fixed_ordinal_vector": list(range(1, SELECTED + 1)),
            "task_vector_validated_in_memory_before_protocol": len(tasks) == SELECTED,
            "synthetic_identifiers_not_selected_from_benchmark": True,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "questions_frozen_in_source_before_protocol": True,
            "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
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
            "fetch_targets": 10,
            "core_fetch_targets": 7,
            "reserve_fetch_targets": 3,
            "single_batch_no_resume_retry_skip_or_selective_rerun": True,
        },
        "causal_boundary": {
            "same_fixed_raw_pages_for_baseline_and_candidate": True,
            "all_fetch_attempts_before_baseline_synthesis": True,
            "candidate_only_adds_semantic_projection_catalog_and_entropy_gate": True,
            "baseline_never_receives_programmatic_projection_text": True,
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
            "one_natural_admission_probe_design": True,
            "natural_admission_probe_launch": False,
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
    if (
        protocol.get("role")
        != "v24345_semantic_active_natural_admission_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("gates") != GATES
        or protocol.get("task_contract", {}).get("selected") != SELECTED
        or protocol.get("task_contract", {}).get("fixed_ordinal_vector")
        != list(range(1, SELECTED + 1))
        or protocol.get("task_contract", {}).get(
            "task_vector_validated_in_memory_before_protocol"
        )
        is not (len(tasks) == SELECTED)
        or protocol.get("provider", {}).get("executor_count") != EXECUTOR_COUNT
        or protocol.get("provider", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or protocol.get("causal_boundary")
        != {
            "same_fixed_raw_pages_for_baseline_and_candidate": True,
            "all_fetch_attempts_before_baseline_synthesis": True,
            "candidate_only_adds_semantic_projection_catalog_and_entropy_gate": True,
            "baseline_never_receives_programmatic_projection_text": True,
        }
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(protocol.get("source_policy", {}).values())
        or protocol.get("authorization", {}).get("one_natural_admission_probe_design")
        is not True
        or any(
            enabled
            for key, enabled in protocol.get("authorization", {}).items()
            if key != "one_natural_admission_probe_design"
        )
        or protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.45 protocol drifted")
    _parent(root)
    return protocol


def _run_test() -> bool:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(ROOT / "tests/test_v24345_semantic_active_natural_admission.py"),
            "-v",
        ],
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
    return completed.returncode == 0


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    pristine = _future(root, (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT))
    tests = _run_test()
    port = _port_listening()
    lease = lease_observation(root, Path("/proc"))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not tests:
        findings.append("focused_tests_failed")
    if not port:
        findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if head != remote:
        findings.append("protocol_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    value = {
        "artifact_version": 1,
        "role": "v24345_semantic_active_natural_admission_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "fixed_heterogeneous_task_vector_frozen": True,
            "focused_tests_passed": tests,
            "keyless_proxy_listening_without_api_request": port,
            "shared_api_lease_inactive": lease.get("active") is False,
            "protocol_commit_pushed": head == remote,
            "worktree_clean": clean,
            "future_surface_pristine": pristine,
            "benchmark_or_evaluator_surface_authorized": False,
        },
        "protected_watchers": protected_watcher_snapshot(),
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
            "one_natural_admission_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.45 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    if (
        value.get("role")
        != "v24345_semantic_active_natural_admission_preactivation_audit"
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("provenance", {}).get("protocol_sha256") != sha256(root / PROTOCOL)
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.45 preaudit drifted")
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
        "role": "v24345_semantic_active_natural_admission_activation",
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
            "one_natural_admission_probe_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.45 activation failed")
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, ACTIVATION)
    if (
        value.get("role") != "v24345_semantic_active_natural_admission_activation"
        or value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.45 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    activation = validate_activation(root)
    if not _future(root, (EXECUTION_START, RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.43.45 execution surface is not pristine")
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
        "role": "v24345_semantic_active_natural_admission_execution_start",
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
        raise RuntimeError("V2.43.45 execution start failed: " + ",".join(findings))
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, EXECUTION_START)
    if (
        value.get("role")
        != "v24345_semantic_active_natural_admission_execution_start"
        or value.get("status") != "ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("api_called_before_execution_start") is not False
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.43.45 execution-start drifted")
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
        started = time.monotonic()
        deadline = started + TASK_WALL_SECONDS
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
        outcome = run_v24343_task(
            task, model=model, search=search, limits=LIMITS, monotonic=time.monotonic
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


def _task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    validate_parent_receipt(parent)
    wrapped = envelope.get("result") if isinstance(envelope, Mapping) else None
    core = wrapped.get("core_result") if isinstance(wrapped, Mapping) else None
    mechanism = (
        wrapped.get("semantic_active_receipt") if isinstance(wrapped, Mapping) else None
    )
    private = (
        wrapped.get("semantic_active_private_state") if isinstance(wrapped, Mapping) else None
    )
    slot = envelope.get("model_slot_receipt") if isinstance(envelope, Mapping) else None
    transport = envelope.get("transport_health") if isinstance(envelope, Mapping) else None
    receipt = (
        core.get("shared_prefix_revision_receipt") if isinstance(core, Mapping) else None
    )
    prefix = receipt.get("prefix_bundle") if isinstance(receipt, Mapping) else None
    cost = core.get("cost") if isinstance(core, Mapping) else None
    model_cost = cost.get("model") if isinstance(cost, Mapping) else None
    search_cost = cost.get("search") if isinstance(cost, Mapping) else None
    slot_counts = slot.get("slot_acquisition_counts") if isinstance(slot, Mapping) else [0, 0]
    gate = (
        private.get("revision_gate_result") if isinstance(private, Mapping) else None
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
        "result_status": core.get("status") if isinstance(core, Mapping) else None,
        "completion_kind": core.get("completion_kind") if isinstance(core, Mapping) else None,
        "effect_accounting_complete": receipt.get("effect_accounting_complete") if isinstance(receipt, Mapping) else None,
        "prefix_status": receipt.get("prefix_status") if isinstance(receipt, Mapping) else None,
        "prefix_producer_execution_count": prefix.get("producer_execution_count") if isinstance(prefix, Mapping) else None,
        "logical_model_admissions": _integer(receipt, "logical_model_admissions"),
        "provider_model_requests": _integer(receipt, "provider_model_requests"),
        "provider_model_attempts": _integer(receipt, "provider_model_attempts"),
        "pre_provider_model_rejections": _integer(receipt, "pre_provider_model_rejections"),
        "slot_acquisitions": _integer(slot, "acquisitions"),
        "slot_timeouts": _integer(slot, "slot_timeouts"),
        "provider_deadline_failures": _integer(slot, "provider_deadline_failures"),
        "slot_total_wait_seconds": _number(slot, "total_wait_seconds"),
        "slot_max_wait_seconds": _number(slot, "max_wait_seconds"),
        "slot_acquisition_counts": list(slot_counts) if isinstance(slot_counts, list) else [0, 0],
        "core_logical_queries": _integer(receipt, "core_logical_queries"),
        "search_provider_effects": _integer(receipt, "core_search_provider_effects") + _integer(receipt, "reserve_search_provider_effects"),
        "core_fetch_targets": _integer(receipt, "core_fetch_targets"),
        "reserve_fetch_targets": _integer(receipt, "reserve_fetch_targets"),
        "core_usable_pages": _integer(receipt, "core_usable_pages"),
        "reserve_usable_pages": _integer(receipt, "reserve_usable_pages"),
        "repeated_upstream_effects": sum(
            receipt.get(name, 0)
            for name in (
                "repeated_plan_model_effects_by_branches",
                "repeated_core_search_effects_by_branches",
                "repeated_core_fetch_effects_by_branches",
            )
        )
        if isinstance(receipt, Mapping)
        else 0,
        "catalog_status": mechanism.get("catalog_status") if isinstance(mechanism, Mapping) else None,
        "shared_raw_pages": bool(mechanism.get("baseline_and_candidate_share_exact_raw_pages")) if isinstance(mechanism, Mapping) else False,
        "fetch_before_baseline": bool(mechanism.get("all_fetch_attempts_precede_baseline_model_admission")) if isinstance(mechanism, Mapping) else False,
        "candidate_only_structure": bool(mechanism.get("candidate_only_adds_semantic_projection_support_structure")) if isinstance(mechanism, Mapping) else False,
        "core_page_count": _integer(mechanism, "core_page_count"),
        "reserve_page_count": _integer(mechanism, "reserve_page_count"),
        "semantic_projection_count": _integer(mechanism, "semantic_projection_count"),
        "eligible_support_set_count": _integer(mechanism, "eligible_support_set_count"),
        "eligible_support_scope_counts": dict(mechanism.get("eligible_support_scope_counts", {})) if isinstance(mechanism, Mapping) else {},
        "revision_model_admitted": mechanism.get("revision_model_admitted") if isinstance(mechanism, Mapping) else None,
        "revision_model_returned": mechanism.get("revision_model_returned") if isinstance(mechanism, Mapping) else None,
        "revision_gate_applied": mechanism.get("revision_gate_applied") if isinstance(mechanism, Mapping) else None,
        "third_model_call_skipped_no_eligible_support": mechanism.get("third_model_call_skipped_no_eligible_support") if isinstance(mechanism, Mapping) else None,
        "candidate_identity_handoff": mechanism.get("candidate_identity_handoff") if isinstance(mechanism, Mapping) else None,
        "proposed_cell_changes": _integer(mechanism, "proposed_cell_changes"),
        "admitted_cell_changes": _integer(mechanism, "admitted_cell_changes"),
        "entropy_positive": bool(_number(mechanism, "credited_conditional_entropy_reduction_nats") > 0),
        "admitted_support_scope_counts": dict(mechanism.get("admitted_support_scope_counts", {})) if isinstance(mechanism, Mapping) else {},
        "gate_private_replay_present": isinstance(gate, Mapping) if isinstance(mechanism, Mapping) and mechanism.get("revision_gate_applied") is True else gate is None,
        "private_replay_valid": isinstance(wrapped, Mapping),
        "model_requests": _integer(model_cost, "requests"),
        "model_attempts": _integer(model_cost, "attempts"),
        "model_total_tokens": _integer(model_cost, "total_tokens"),
        "search_calls": _integer(search_cost, "calls"),
        "fetch_calls": _integer(search_cost, "fetch_calls"),
        "fetch_failures": _integer(search_cost, "fetch_failures"),
        "search_total_tokens": _integer(search_cost, "total_tokens"),
        "hosted_search_deadline_failures": _integer(transport, "hosted_search_deadline_failures"),
        "hard_fetch_helper_calls": _integer(transport, "hard_fetch_helper_calls"),
        "hard_fetch_deadline_failures": _integer(transport, "hard_fetch_deadline_failures"),
        "fetch_deadline_rejections": _integer(transport, "fetch_deadline_rejections"),
        "fetch_helper_failures": _integer(transport, "fetch_helper_failures"),
        "deadline_exhausted": transport.get("deadline_exhausted") if isinstance(transport, Mapping) else True,
    }
    value["checks"] = _task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def _task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "parent_success": value.get("parent_taxonomy") == "success",
        "all_parent_artifacts_valid": value.get("all_parent_artifacts_valid") is True,
        "result_completed": value.get("result_status") == "completed",
        "effect_accounting_complete": value.get("effect_accounting_complete") is True,
        "prefix_frozen_once": value.get("prefix_status") == "frozen" and value.get("prefix_producer_execution_count") == 1,
        "model_effect_range": 2 <= value.get("logical_model_admissions", 0) <= 3,
        "model_conservation": value.get("logical_model_admissions") == value.get("slot_acquisitions") + value.get("slot_timeouts") and value.get("provider_model_requests") == value.get("slot_acquisitions") and value.get("pre_provider_model_rejections") == value.get("slot_timeouts"),
        "no_slot_or_provider_deadline_failure": value.get("slot_timeouts") == 0 and value.get("provider_deadline_failures") == 0,
        "four_logical_queries": value.get("core_logical_queries") == 4,
        "one_hosted_search_effect": value.get("search_provider_effects") == 1,
        "exact_core_reserve_fetch_targets": value.get("core_fetch_targets") == 7 and value.get("reserve_fetch_targets") == 3,
        "core_and_reserve_usable": value.get("core_usable_pages", 0) >= 1 and value.get("reserve_usable_pages", 0) >= 1,
        "shared_raw_pages": value.get("shared_raw_pages") is True,
        "fetch_before_baseline": value.get("fetch_before_baseline") is True,
        "candidate_only_structure": value.get("candidate_only_structure") is True,
        "catalog_state_valid": value.get("catalog_status") in {"built_empty", "built_eligible", "not_built_ineligible_path"},
        "revision_policy_consistent": (
            value.get("catalog_status") == "built_empty"
            and value.get("revision_model_admitted") is False
            and value.get("third_model_call_skipped_no_eligible_support") is True
        )
        or (
            value.get("catalog_status") == "built_eligible"
            and value.get("revision_model_admitted") is True
        )
        or (
            value.get("catalog_status") == "not_built_ineligible_path"
            and value.get("revision_model_admitted") is False
        ),
        "private_replay_valid": value.get("private_replay_valid") is True and value.get("gate_private_replay_present") is True,
        "fetch_conservation": value.get("fetch_calls") == value.get("hard_fetch_helper_calls") + value.get("fetch_deadline_rejections"),
        "deadline_not_exhausted": value.get("deadline_exhausted") is False,
        "no_repeated_upstream_effect": value.get("repeated_upstream_effects") == 0,
        "within_parent_wall": value.get("wall_seconds", 10**9) <= PARENT_TIMEOUT_SECONDS,
    }


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(value, ensure_ascii=False)
    if (
        value.get("passed") is not all(value.get("checks", {}).values())
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
        or any(literal in encoded for literal in CONTENT_LITERALS)
        or not isinstance(value.get("slot_acquisition_counts"), list)
        or len(value["slot_acquisition_counts"]) != MODEL_SLOT_CAP
        or sum(value["slot_acquisition_counts"]) != value.get("slot_acquisitions")
    ):
        raise RuntimeError("V2.43.45 task projection drifted or contains content")
    return dict(value)


def _local_failure(ordinal: int) -> dict[str, Any]:
    value = {
        "ordinal": ordinal,
        "wall_seconds": 0.0,
        "parent_taxonomy": "local_projection_failure",
        "all_parent_artifacts_valid": False,
        "result_status": None,
        "completion_kind": None,
        "effect_accounting_complete": False,
        "prefix_status": None,
        "prefix_producer_execution_count": None,
        "logical_model_admissions": 0,
        "provider_model_requests": 0,
        "provider_model_attempts": 0,
        "pre_provider_model_rejections": 0,
        "slot_acquisitions": 0,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "slot_total_wait_seconds": 0.0,
        "slot_max_wait_seconds": 0.0,
        "slot_acquisition_counts": [0, 0],
        "core_logical_queries": 0,
        "search_provider_effects": 0,
        "core_fetch_targets": 0,
        "reserve_fetch_targets": 0,
        "core_usable_pages": 0,
        "reserve_usable_pages": 0,
        "repeated_upstream_effects": 0,
        "catalog_status": None,
        "shared_raw_pages": False,
        "fetch_before_baseline": False,
        "candidate_only_structure": False,
        "core_page_count": 0,
        "reserve_page_count": 0,
        "semantic_projection_count": 0,
        "eligible_support_set_count": 0,
        "eligible_support_scope_counts": {},
        "revision_model_admitted": None,
        "revision_model_returned": None,
        "revision_gate_applied": None,
        "third_model_call_skipped_no_eligible_support": None,
        "candidate_identity_handoff": None,
        "proposed_cell_changes": 0,
        "admitted_cell_changes": 0,
        "entropy_positive": False,
        "admitted_support_scope_counts": {},
        "gate_private_replay_present": False,
        "private_replay_valid": False,
        "model_requests": 0,
        "model_attempts": 0,
        "model_total_tokens": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "fetch_failures": 0,
        "search_total_tokens": 0,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": True,
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
    status_counts = Counter(str(task["catalog_status"]) for task in values)
    completion_counts = Counter(str(task["completion_kind"]) for task in values)
    eligible_scope_counts: Counter[str] = Counter()
    admitted_scope_counts: Counter[str] = Counter()
    for task in values:
        eligible_scope_counts.update(task["eligible_support_scope_counts"])
        admitted_scope_counts.update(task["admitted_support_scope_counts"])
    summary = {
        "selected": len(values),
        "terminal_success_tasks": sum(task["parent_taxonomy"] == "success" for task in values),
        "structurally_passed_tasks": sum(task["passed"] is True for task in values),
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "throughput_tasks_per_minute": round(
            len(values) / max(float(batch_wall_seconds), 1e-9) * 60, 6
        ),
        "completion_kinds": dict(sorted(completion_counts.items())),
        "catalog_statuses": dict(sorted(status_counts.items())),
        "built_catalog_tasks": sum(str(task["catalog_status"]).startswith("built_") for task in values),
        "semantic_projection_tasks": sum(task["semantic_projection_count"] > 0 for task in values),
        "semantic_projection_count": sum(task["semantic_projection_count"] for task in values),
        "eligible_support_tasks": sum(task["eligible_support_set_count"] > 0 for task in values),
        "eligible_support_set_count": sum(task["eligible_support_set_count"] for task in values),
        "eligible_support_scope_counts": dict(sorted(eligible_scope_counts.items())),
        "revision_admitted_tasks": sum(task["revision_model_admitted"] is True for task in values),
        "revision_returned_tasks": sum(task["revision_model_returned"] is True for task in values),
        "revision_gate_tasks": sum(task["revision_gate_applied"] is True for task in values),
        "candidate_nonidentity_tasks": sum(task["candidate_identity_handoff"] is False for task in values),
        "proposed_cell_changes": sum(task["proposed_cell_changes"] for task in values),
        "admitted_cell_changes": sum(task["admitted_cell_changes"] for task in values),
        "entropy_positive_tasks": sum(task["entropy_positive"] is True for task in values),
        "admitted_support_scope_counts": dict(sorted(admitted_scope_counts.items())),
        "model_requests": sum(task["model_requests"] for task in values),
        "model_attempts": sum(task["model_attempts"] for task in values),
        "model_total_tokens": sum(task["model_total_tokens"] for task in values),
        "slot_acquisitions": sum(task["slot_acquisitions"] for task in values),
        "slot_timeouts": sum(task["slot_timeouts"] for task in values),
        "provider_deadline_failures": sum(task["provider_deadline_failures"] for task in values),
        "slot_total_wait_seconds": round(sum(task["slot_total_wait_seconds"] for task in values), 6),
        "slot_max_wait_seconds": round(max((task["slot_max_wait_seconds"] for task in values), default=0), 6),
        "search_calls": sum(task["search_calls"] for task in values),
        "fetch_calls": sum(task["fetch_calls"] for task in values),
        "fetch_failures": sum(task["fetch_failures"] for task in values),
        "hard_fetch_deadline_failures": sum(task["hard_fetch_deadline_failures"] for task in values),
        "fetch_helper_failures": sum(task["fetch_helper_failures"] for task in values),
        "deadline_exhausted_tasks": sum(task["deadline_exhausted"] is True for task in values),
        "all_private_replay_valid": all(task["private_replay_valid"] is True for task in values),
        "all_shared_raw_pages": all(task["shared_raw_pages"] is True for task in values),
        "all_fetch_before_baseline": all(task["fetch_before_baseline"] is True for task in values),
        "all_candidate_only_structure": all(task["candidate_only_structure"] is True for task in values),
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
        "hard_fetch_deadline_failures": summary["hard_fetch_deadline_failures"] <= GATES["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": summary["fetch_helper_failures"] <= GATES["maximum_fetch_helper_failures"],
        "deadline_exhausted_tasks": summary["deadline_exhausted_tasks"] <= GATES["maximum_deadline_exhausted_tasks"],
        "built_catalog_tasks": summary["built_catalog_tasks"] >= GATES["minimum_built_catalog_tasks"],
        "semantic_projection_tasks": summary["semantic_projection_tasks"] >= GATES["minimum_semantic_projection_tasks"],
        "eligible_support_tasks": summary["eligible_support_tasks"] >= GATES["minimum_eligible_support_tasks"],
        "revision_admitted_tasks": summary["revision_admitted_tasks"] >= GATES["minimum_revision_admitted_tasks"],
        "revision_gate_tasks": summary["revision_gate_tasks"] >= GATES["minimum_revision_gate_tasks"],
        "candidate_nonidentity_tasks": summary["candidate_nonidentity_tasks"] >= GATES["minimum_candidate_nonidentity_tasks"],
        "admitted_cell_changes": summary["admitted_cell_changes"] >= GATES["minimum_admitted_cell_changes"],
        "entropy_positive_tasks": summary["entropy_positive_tasks"] >= GATES["minimum_entropy_positive_tasks"],
        "candidate_entropy_alignment": summary["candidate_nonidentity_tasks"] == summary["entropy_positive_tasks"],
        "admission_scope_conservation": sum(summary["admitted_support_scope_counts"].values()) == summary["admitted_cell_changes"],
        "all_private_replay_valid": summary["all_private_replay_valid"] is True,
        "all_shared_raw_pages": summary["all_shared_raw_pages"] is True,
        "all_fetch_before_baseline": summary["all_fetch_before_baseline"] is True,
        "all_candidate_only_structure": summary["all_candidate_only_structure"] is True,
    }
    return {**summary, "checks": checks, "passed": all(checks.values())}


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    encoded = json.dumps(value, ensure_ascii=False)
    aggregate = value.get("aggregate")
    if (
        value.get("role") != "v24345_semantic_active_natural_admission_result"
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
        or any(literal in encoded for literal in CONTENT_LITERALS)
    ):
        raise RuntimeError("V2.43.45 public result drifted or contains task content")
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
        raise RuntimeError("V2.43.45 result/git surface is not ready")
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
                    pool.submit(
                        _run_one, root, output_root, slots, directory, ordinal
                    )
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
            "role": "v24345_semantic_active_natural_admission_result",
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
        raise RuntimeError("V2.43.45 protected watcher identity drifted")
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = validate_public_result(_read(root, RESULT))
    passed = result["passed"] is True
    aggregate = result["aggregate"]
    value = {
        "artifact_version": 1,
        "role": "v24345_semantic_active_natural_admission_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "natural_admission_go" if passed else "natural_admission_no_go",
        "passed": passed,
        "failed_checks": sorted(
            name for name, check in aggregate["checks"].items() if not check
        ),
        "observed": {
            key: aggregate[key]
            for key in (
                "selected",
                "terminal_success_tasks",
                "structurally_passed_tasks",
                "batch_wall_seconds",
                "throughput_tasks_per_minute",
                "catalog_statuses",
                "semantic_projection_tasks",
                "semantic_projection_count",
                "eligible_support_tasks",
                "eligible_support_set_count",
                "eligible_support_scope_counts",
                "revision_admitted_tasks",
                "revision_gate_tasks",
                "candidate_nonidentity_tasks",
                "proposed_cell_changes",
                "admitted_cell_changes",
                "entropy_positive_tasks",
                "admitted_support_scope_counts",
                "model_requests",
                "slot_timeouts",
                "provider_deadline_failures",
                "hard_fetch_deadline_failures",
                "fetch_helper_failures",
                "deadline_exhausted_tasks",
            )
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
        },
        "claim_scope": {
            "benchmark_external_real_web_mechanism_activation_measured": True,
            "same_raw_evidence_causal_boundary_measured": True,
            "benchmark_quality_measured": False,
            "entropy_quality_improvement_proven": False,
            "future_population_or_sota_supported": False,
        },
        "authorization": {
            "fresh_paired_benchmark_design": passed,
            "fresh_paired_benchmark_launch": False,
            "additional_dev64_or_exact220": False,
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
        "role": "v24345_semantic_active_natural_admission_postresult_audit",
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
            "fresh_paired_benchmark_design": decision["passed"] and not findings,
            "fresh_paired_benchmark_launch": False,
            "additional_dev64_or_exact220": False,
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
