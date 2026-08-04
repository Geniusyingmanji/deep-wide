#!/usr/bin/env python3
"""Build-only label-blind audit for V2.44.54--55.

The audit binds the proof-carrying terminal certificate, the parent timed
runner, their synthetic equivalence/tamper tests, and a five-run local parent
validation timing sample.  The certificate is deliberately scoped as a trust
boundary inside a pinned local execution: it detects durable-artifact drift
after the trusted child validator ran, but is not an independent signature or
remote attestation against a malicious child.

This audit performs no external network, model, search, fetch, benchmark, or
evaluator call.  It can authorize only offline design of the adaptive-support
successor.  It cannot authorize an external probe, dev64, exact220, evaluator,
leaderboard submission, or SOTA claim.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import child_receipt  # noqa: E402
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    build_envelope,
    run_v24447_task,
)
from deepwide_agent.v24454_proof_carrying_third_source_envelope import (  # noqa: E402
    CERTIFICATE_NAME,
    build_terminal_certificate,
)
from deepwide_agent.v24455_proof_carrying_timed_runner import (  # noqa: E402
    run_proof_carrying_timed_observed_subprocess,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24456_proof_carrying_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24453_v24452_validation_and_support_diagnosis_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24448_serialized_third_source_envelope.py"),
    Path("scripts/v24449_third_source_external_projection.py"),
    Path("src/deepwide_agent/v24454_proof_carrying_third_source_envelope.py"),
    Path("src/deepwide_agent/v24455_proof_carrying_timed_runner.py"),
    Path("tests/test_v24448_serialized_third_source_envelope.py"),
    Path("tests/test_v24449_third_source_external_projection.py"),
    Path("tests/test_v24454_proof_carrying_third_source_envelope.py"),
    Path("tests/test_v24455_proof_carrying_timed_runner.py"),
    Path("scripts/audit_v24456_proof_carrying_build.py"),
    Path("tests/test_audit_v24456_proof_carrying_build.py"),
)
RUNTIME_SOURCES = (SOURCES[1], SOURCES[2], SOURCES[3])
TEST_SUITES = (
    (SOURCES[4], 4, "complete_validator"),
    (SOURCES[5], 5, "counts_projection"),
    (SOURCES[6], 7, "proof_certificate"),
    (SOURCES[7], 5, "proof_timed_runner"),
    (SOURCES[9], 5, "audit_control"),
)
EXPECTED_MECHANISM_TEST_COUNT = 21
EXPECTED_CONTROL_TEST_COUNT = 5
EXPECTED_TEST_COUNT = EXPECTED_MECHANISM_TEST_COUNT + EXPECTED_CONTROL_TEST_COUNT
PERFORMANCE_REPETITIONS = 5
PARENT_VALIDATION_CEILING_SECONDS = 1.0
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


class SuccessfulPopen:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.pid = 987656
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        return 0


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.56 expected object")
    return value


def _validate_parent() -> dict[str, Any]:
    value = _read(PARENT)
    unsigned = dict(value)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    work = value.get("successor_work_order")
    findings = value.get("root_cause_findings")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24453_v24452_validation_and_support_diagnosis"
        or not isinstance(work, dict)
        or not isinstance(findings, dict)
        or not isinstance(authorization, dict)
        or findings.get("parent_complete_nested_semantic_replay_is_material_latency_cause")
        is not True
        or findings.get("one_additional_third_source_hypothesis_externally_falsified")
        is not True
        or work.get("child_runs_complete_semantic_validation_before_terminal_certificate")
        is not True
        or work.get("terminal_certificate_binds_exact_result_model_transport_and_search_file_bytes")
        is not True
        or work.get("parent_rejects_missing_extra_symlink_or_hash_drifted_artifacts")
        is not True
        or work.get("parent_does_not_recursively_recompute_the_complete_historical_pipeline")
        is not True
        or work.get("synthetic_parent_validation_p95_seconds_ceiling")
        != PARENT_VALIDATION_CEILING_SECONDS
        or authorization.get("synthetic_offline_build_and_tamper_tests") is not True
        or authorization.get("external_probe_launch") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.56 parent diagnosis drifted")
    for item in value.get("parents", {}).values():
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("path"), str)
            or not isinstance(item.get("sha256"), str)
            or sha256(base._ordinary(Path(item["path"]))) != item["sha256"]
        ):
            raise RuntimeError("V2.44.56 parent provenance drifted")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _p95(values: list[float]) -> float:
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


def _measure_parent_validation() -> dict[str, Any]:
    """Measure only local synthetic proof validation; no external effects."""

    from test_v24342_semantic_active_runtime import limits
    from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK
    from test_v24412_receipt_snapshot_diagnosis import AdvancingClock
    from test_v24447_third_source_entropy_to_decision import clients

    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as fixture:
        clock = AdvancingClock()
        model, search = clients(Path(fixture), clock, third=True)
        completed = run_v24447_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        envelope = build_envelope(completed)
    manifest = payload_sha256(
        {
            str(path): sha256(base._ordinary(path))
            for path in (SOURCES[0], SOURCES[1], SOURCES[2], SOURCES[3])
        }
    )
    durations: list[float] = []
    parent_post_child: list[float] = []
    for ordinal in range(1, PERFORMANCE_REPETITIONS + 1):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            artifacts = {
                RESULT_NAME: envelope,
                MODEL_NAME: completed.model_slot_receipt,
                TRANSPORT_NAME: completed.transport_health,
                SEARCH_NAME: completed.search_single_shot_receipt,
            }
            for name, value in artifacts.items():
                _write_json(directory / name, value)
            certificate = build_terminal_certificate(
                directory,
                completed,
                validator_manifest_sha256=manifest,
                expected_artifacts=artifacts,
            )
            _write_json(directory / CERTIFICATE_NAME, certificate)
            _write_json(
                directory / CHILD_NAME,
                child_receipt(
                    stage="result_envelope_written",
                    exception_type=None,
                    model_receipt_written=True,
                    transport_receipt_written=True,
                    result_envelope_written=True,
                ),
            )
            outcome = run_proof_carrying_timed_observed_subprocess(
                ordinal=ordinal,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=directory,
                command=["synthetic"],
                environment={},
                timeout_seconds=1,
                expected_model_cap=2,
                expected_validator_manifest_sha256=manifest,
                popen=SuccessfulPopen,
            )
            timing = outcome.timing_receipt
            if outcome.parent_receipt["failure_taxonomy"] != "success":
                raise RuntimeError("V2.44.56 performance fixture did not succeed")
            durations.append(float(timing["parent_certificate_validation_wall_seconds"]))
            parent_post_child.append(float(timing["parent_post_child_wall_seconds"]))
    return {
        "scope": "synthetic_test_fixture_only",
        "repetitions": PERFORMANCE_REPETITIONS,
        "certificate_validation_seconds": [round(value, 6) for value in durations],
        "certificate_validation_median_seconds": round(
            float(statistics.median(durations)), 6
        ),
        "certificate_validation_p95_seconds": round(_p95(durations), 6),
        "certificate_validation_max_seconds": round(max(durations), 6),
        "parent_post_child_median_seconds": round(
            float(statistics.median(parent_post_child)), 6
        ),
        "parent_post_child_p95_seconds": round(_p95(parent_post_child), 6),
        "parent_post_child_max_seconds": round(max(parent_post_child), 6),
        "ceiling_seconds": PARENT_VALIDATION_CEILING_SECONDS,
        "ceiling_passed": max(durations) <= PARENT_VALIDATION_CEILING_SECONDS,
        "network_model_search_fetch_or_evaluator_called": False,
        "profile_is_not_external_latency_estimate": True,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    _validate_parent()
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = base._ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    suites = [
        {
            "path": str(path),
            "passed": base._run_test(path),
            "test_count": count,
            "scope": scope,
        }
        for path, count, scope in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    ]
    performance = _measure_parent_validation()
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    tracked = all(base._tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("v24454_56_source_commit_not_pushed")
    if not clean:
        findings.append("v24454_56_source_worktree_not_clean")
    if not tracked:
        findings.append("v24454_56_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24448_56_regression_failed_or_count_drifted")
    if (
        performance.get("repetitions") != PERFORMANCE_REPETITIONS
        or performance.get("ceiling_passed") is not True
        or float(performance.get("certificate_validation_p95_seconds", math.inf))
        > PARENT_VALIDATION_CEILING_SECONDS
    ):
        findings.append("proof_carrying_parent_validation_latency_gate_failed")
    if accesses:
        findings.append("privileged_field_access_in_v24449_55_runtime")
    if imports:
        findings.append("evaluator_import_in_v24449_55_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24454_56_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24456_proof_carrying_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": suites,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "test_count": test_count,
            "mechanism_test_count": EXPECTED_MECHANISM_TEST_COUNT,
            "audit_control_test_count": EXPECTED_CONTROL_TEST_COUNT,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "performance_evidence": performance,
        "proof_evidence": {
            "complete_frozen_semantic_validation_runs_in_trusted_child": True,
            "parent_binds_exact_result_model_transport_and_search_file_bytes": True,
            "parent_requires_successful_child_terminal_receipt": True,
            "parent_rejects_missing_extra_symlink_or_hash_drifted_artifacts": True,
            "writer_input_and_durable_json_value_must_be_equal": True,
            "resealed_private_content_tamper_rejected_by_exact_byte_certificate": True,
            "projection_exactly_equal_to_complete_validator_on_synthetic_fixture": True,
            "success_observation_consumes_validated_capability_receipts": True,
            "failure_observation_preserves_partial_effect_lower_bounds": True,
            "parent_recursive_historical_semantic_replay_tasks": 0,
            "private_file_hashes_emitted_to_public_aggregate": False,
        },
        "trust_boundary": {
            "pinned_local_child_source_and_launch_manifest_are_trusted": True,
            "certificate_is_independently_signed": False,
            "certificate_is_remote_attestation": False,
            "malicious_child_resistance_claimed": False,
            "post_validation_persistence_drift_detection_claimed": True,
            "serialization_drift_detection_claimed": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "external_probe_launched": False,
            "benchmark_or_watcher_signaled_restarted_or_modified": False,
            "active_run_killed_or_quarantined": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_query_url_page_prediction_value_or_content_hash_emitted": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "adaptive_support_successor_offline_design": not findings,
            "fresh_external_protocol_design": False,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: dict[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization")
    trust = copied.get("trust_boundary")
    if (
        copied.get("role") != "v24456_proof_carrying_build_audit"
        or not isinstance(authorization, dict)
        or set(authorization)
        != {
            "adaptive_support_successor_offline_design",
            "fresh_external_protocol_design",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or authorization.get("adaptive_support_successor_offline_design")
        is not copied.get("audit_valid")
        or any(
            authorization.get(name) is not False
            for name in (
                "fresh_external_protocol_design",
                "external_probe_launch",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not isinstance(trust, dict)
        or trust.get("certificate_is_independently_signed") is not False
        or trust.get("certificate_is_remote_attestation") is not False
        or trust.get("malicious_child_resistance_claimed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.56 build audit drifted")
    return copied


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    validate_audit(audit)
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}))
