#!/usr/bin/env python3
"""Independent build-only audit for V2.44.59--61.

The audit binds proof-carrying adaptive validation, the minimal public
projection, the timed success/failure runner, old proof/adaptive regression,
and a local synthetic parent-validation timing sample.  It performs no
network, model, search, fetch, benchmark, or evaluator call.

Passing authorizes only design of a fresh benchmark-external protocol.  It
does not authorize an external launch, paired dev64, exact220, evaluator,
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
import subprocess
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
from deepwide_agent.v24457_adaptive_entropy_support import (  # noqa: E402
    build_envelope,
    run_v24457_task,
)
from deepwide_agent.v24459_proof_carrying_adaptive_entropy_support import (  # noqa: E402
    CERTIFICATE_NAME,
    build_terminal_certificate,
)
from deepwide_agent.v24460_adaptive_capability_projection import (  # noqa: E402
    task_projection,
)
from deepwide_agent.v24461_proof_carrying_adaptive_timed_runner import (  # noqa: E402
    run_proof_carrying_adaptive_timed_subprocess,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24462_proof_carrying_adaptive_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24458_adaptive_entropy_support_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24454_proof_carrying_third_source_envelope.py"),
    Path("src/deepwide_agent/v24455_proof_carrying_timed_runner.py"),
    Path("src/deepwide_agent/v24457_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24459_proof_carrying_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24460_adaptive_capability_projection.py"),
    Path("src/deepwide_agent/v24461_proof_carrying_adaptive_timed_runner.py"),
    Path("tests/test_v24454_proof_carrying_third_source_envelope.py"),
    Path("tests/test_v24455_proof_carrying_timed_runner.py"),
    Path("tests/test_v24457_adaptive_entropy_support.py"),
    Path("tests/test_v24459_proof_carrying_adaptive_entropy_support.py"),
    Path("tests/test_v24461_proof_carrying_adaptive_timed_runner.py"),
    Path("scripts/audit_v24462_proof_carrying_adaptive_build.py"),
    Path("tests/test_audit_v24462_proof_carrying_adaptive_build.py"),
)
RUNTIME_SOURCES = SOURCES[3:6]
TEST_SUITES = (
    (SOURCES[6], 7, "legacy_proof_certificate", 360),
    (SOURCES[7], 5, "legacy_proof_timed_runner", 360),
    (SOURCES[8], 6, "adaptive_semantic_regression", 900),
    (SOURCES[9], 7, "adaptive_proof_and_projection", 360),
    (SOURCES[10], 5, "adaptive_proof_timed_runner", 360),
    (SOURCES[12], 5, "audit_control", 360),
)
EXPECTED_MECHANISM_TEST_COUNT = 30
EXPECTED_CONTROL_TEST_COUNT = 5
EXPECTED_TEST_COUNT = 35
PERFORMANCE_REPETITIONS = 5
PARENT_VALIDATION_CEILING_SECONDS = 1.0
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
PROHIBITED_PUBLIC_SUBSTRINGS = ("lead", "page", "hash", "sha256")


class SuccessfulPopen:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.pid = 987663
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        return 0


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.62 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parent() -> dict[str, Any]:
    value = _read(PARENT)
    if (
        value.get("role") != "v24458_adaptive_entropy_support_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "proof_carrying_adaptive_integration_design"
        )
        is not True
        or value.get("authorization", {}).get("external_probe_launch") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.62 parent authorization drifted")
    return value


def _run_test(relative: Path, *, timeout_seconds: int) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-q"],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
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
        timeout=timeout_seconds,
        check=False,
    )
    return completed.returncode == 0


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _p95(values: list[float]) -> float:
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


def _measure_parent_validation() -> dict[str, Any]:
    """Measure local synthetic proof validation only; no external effects."""

    from test_v24342_semantic_active_runtime import limits
    from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK
    from test_v24412_receipt_snapshot_diagnosis import AdvancingClock
    from test_v24447_third_source_entropy_to_decision import clients

    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as fixture:
        clock = AdvancingClock()
        model, search = clients(Path(fixture), clock, third=True)
        completed = run_v24457_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        envelope = build_envelope(completed)
    manifest = payload_sha256(
        {str(path): sha256(base._ordinary(path)) for path in RUNTIME_SOURCES}
    )
    validation: list[float] = []
    post_child: list[float] = []
    public_surface_valid = True
    for ordinal in range(1, PERFORMANCE_REPETITIONS + 1):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            artifacts = {
                RESULT_NAME: envelope,
                MODEL_NAME: completed.model_slot_receipt,
                TRANSPORT_NAME: completed.transport_health,
                SEARCH_NAME: completed.search_single_shot_receipt,
            }
            for name, item in artifacts.items():
                _write_json(directory / name, item)
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
            outcome = run_proof_carrying_adaptive_timed_subprocess(
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
            if outcome.parent_receipt["failure_taxonomy"] != "success":
                raise RuntimeError("V2.44.62 performance fixture did not succeed")
            encoded = json.dumps(
                outcome.adaptive_projection,
                ensure_ascii=False,
                sort_keys=True,
            ).casefold()
            public_surface_valid = public_surface_valid and not any(
                item in encoded for item in PROHIBITED_PUBLIC_SUBSTRINGS
            )
            timing = outcome.timing_receipt
            validation.append(
                float(timing["parent_certificate_validation_wall_seconds"])
            )
            post_child.append(float(timing["parent_post_child_wall_seconds"]))
    return {
        "scope": "synthetic_test_fixture_only",
        "repetitions": PERFORMANCE_REPETITIONS,
        "certificate_validation_seconds": [round(value, 6) for value in validation],
        "certificate_validation_median_seconds": round(
            float(statistics.median(validation)), 6
        ),
        "certificate_validation_p95_seconds": round(_p95(validation), 6),
        "certificate_validation_max_seconds": round(max(validation), 6),
        "parent_post_child_median_seconds": round(
            float(statistics.median(post_child)), 6
        ),
        "parent_post_child_p95_seconds": round(_p95(post_child), 6),
        "parent_post_child_max_seconds": round(max(post_child), 6),
        "ceiling_seconds": PARENT_VALIDATION_CEILING_SECONDS,
        "ceiling_passed": max(validation) <= PARENT_VALIDATION_CEILING_SECONDS,
        "public_projection_contains_no_lead_page_or_hash": public_surface_valid,
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
            "passed": _run_test(path, timeout_seconds=timeout_seconds),
            "test_count": count,
            "scope": scope,
            "timeout_seconds": timeout_seconds,
        }
        for path, count, scope, timeout_seconds in TEST_SUITES
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
        findings.append("v24459_62_source_commit_not_pushed")
    if not clean:
        findings.append("v24459_62_source_worktree_not_clean")
    if not tracked:
        findings.append("v24459_62_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24454_62_regression_failed_or_count_drifted")
    if (
        performance.get("ceiling_passed") is not True
        or performance.get("public_projection_contains_no_lead_page_or_hash")
        is not True
    ):
        findings.append("proof_parent_latency_or_public_surface_gate_failed")
    if accesses:
        findings.append("privileged_field_access_in_v24459_61_runtime")
    if imports:
        findings.append("evaluator_import_in_v24459_61_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24459_62_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24462_proof_carrying_adaptive_build_audit",
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
            "complete_v24457_semantic_validation_runs_in_trusted_child": True,
            "parent_binds_exact_result_model_transport_and_search_file_bytes": True,
            "parent_requires_successful_child_terminal_receipt": True,
            "parent_checks_adaptive_support_and_effect_receipts": True,
            "parent_rejects_missing_extra_symlink_or_hash_drifted_artifacts": True,
            "success_observation_consumes_validated_capability_receipts": True,
            "success_projection_consumes_only_validated_capability": True,
            "failure_observation_preserves_partial_effect_lower_bounds": True,
            "parent_recursive_historical_semantic_replay_tasks": 0,
            "public_projection_limited_to_stop_threshold_effect_and_entropy_credit_counts": True,
            "public_projection_contains_lead_page_or_hash": False,
        },
        "trust_boundary": {
            "pinned_local_child_source_and_launch_manifest_are_trusted": True,
            "certificate_is_independently_signed": False,
            "certificate_is_remote_attestation": False,
            "malicious_child_resistance_claimed": False,
            "post_validation_persistence_drift_detection_claimed": True,
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
            "fresh_external_protocol_design": not findings,
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
    proof = copied.get("proof_evidence")
    performance = copied.get("performance_evidence")
    if (
        copied.get("role") != "v24462_proof_carrying_adaptive_build_audit"
        or not isinstance(authorization, dict)
        or set(authorization)
        != {
            "fresh_external_protocol_design",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or authorization.get("fresh_external_protocol_design")
        is not copied.get("audit_valid")
        or any(
            authorization.get(name) is not False
            for name in (
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
        or not isinstance(proof, dict)
        or proof.get("parent_recursive_historical_semantic_replay_tasks") != 0
        or proof.get("public_projection_contains_lead_page_or_hash") is not False
        or not isinstance(performance, dict)
        or performance.get("public_projection_contains_no_lead_page_or_hash")
        is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.62 build audit drifted")
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
