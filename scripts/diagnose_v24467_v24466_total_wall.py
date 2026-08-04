#!/usr/bin/env python3
"""Content-free diagnosis of the V2.44.66 all-timeout NO-GO.

The frozen public result deleted every task-private directory, so it cannot
identify the exact blocking call or validation stage.  This report keeps that
limit explicit.  It combines the public aggregate with a loopback-only
slow-drip HTTP counterexample proving that ``requests(timeout=remaining)`` is
an inactivity timeout, not a total-wall deadline: both the model and hosted
search clients can return success after their shared absolute deadline.

The report also preserves the earlier synthetic validation timing without
misrepresenting it as external latency.  It authorizes only append-only design
of a true total-wall effect guard, content-free stage checkpoints, and a
bounded single-validation finalize path.  It never authorizes another
external population, dev64, exact220, evaluator access, or a quality claim.
"""

from __future__ import annotations

import json
import os
import re
import socketserver
import sys
import threading
import time
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareResponsesClient,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts import audit_v24465_single_validation_adaptive_build as build  # noqa: E402
from scripts import v24466_single_validation_adaptive_external_gate as gate  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
REPORT = Path(f"results/v24467_v24466_total_wall_diagnosis_v1_{DATE}.json")
RESULT = gate.RESULT
DECISION = gate.DECISION
POSTAUDIT = gate.POSTAUDIT
BUILD_AUDIT = build.AUDIT
MODEL_DEADLINE_SOURCE = Path("src/deepwide_agent/v24312_deadline_reliability.py")
SEARCH_DEADLINE_SOURCE = Path("src/deepwide_agent/v24316_deadline_search.py")
PERSISTENCE_SOURCE = Path(
    "src/deepwide_agent/v24464_single_validation_adaptive_persistence.py"
)
GATE_SOURCE = Path("scripts/v24466_single_validation_adaptive_external_gate.py")
DIAGNOSIS_SOURCE = Path("scripts/diagnose_v24467_v24466_total_wall.py")
TEST_SOURCE = Path("tests/test_diagnose_v24467_v24466_total_wall.py")
SOURCES = (
    MODEL_DEADLINE_SOURCE,
    SEARCH_DEADLINE_SOURCE,
    PERSISTENCE_SOURCE,
    GATE_SOURCE,
    DIAGNOSIS_SOURCE,
    TEST_SOURCE,
)
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
TOTAL_DEADLINE_SECONDS = 0.35
CLEANUP_RESERVE_SECONDS = 0.10
DRIP_SECONDS = 0.012


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.67 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    result = gate.validate_public_result(_read(RESULT))
    gate.validate_decision(ROOT, value=_read(DECISION))
    gate.validate_postaudit(ROOT, value=_read(POSTAUDIT))
    build_audit = _read(BUILD_AUDIT)
    observation = result["observation_aggregate"]
    timing = result["stage_timing_aggregate"]
    performance = build_audit.get("performance_evidence") or {}
    if (
        result.get("selected") != 8
        or result.get("effect_deadline_seconds") != 190
        or result.get("parent_timeout_seconds") != 255
        or result.get("terminal_reserve_seconds") != 65
        or result.get("one_wave") is not True
        or result.get("batch_wall_seconds") != 255.183467
        or result.get("diagnostic_complete") is not False
        or result.get("mechanism_passed") is not False
        or result.get("reliability_passed") is not False
        or result.get("parent_validation_passed") is not True
        or result.get("latency_passed") is not True
        or result.get("passed") is not False
        or observation.get("parent_taxonomy_counts")
        != {"hard_deadline_timeout": 8}
        or observation.get("success_tasks") != 0
        or observation.get("failure_tasks") != 8
        or observation.get("failure_snapshot_tasks") != 0
        or observation.get("unobserved_effect_tasks") != 8
        or timing.get("parent_success_tasks") != 0
        or timing.get("parent_failure_tasks") != 8
        or timing.get("certificate_validation_invocations") != 0
        or timing.get("recursive_historical_semantic_replay_tasks") != 0
        or timing.get("child_wall_p95_seconds") != 255.023751
        or build_audit.get("audit_valid") is not True
        or build_audit.get("findings") != []
        or performance.get("complete_validation_wall_seconds") != 32.659375
        or performance.get("fast_envelope_p95_seconds") != 0.0133
        or performance.get("profile_is_not_external_latency_estimate") is not True
        or not _sealed(result, "result_payload_sha256")
        or not _sealed(build_audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.67 parent closure drifted")
    return result, build_audit


def _slow_drip_probe() -> dict[str, Any]:
    """Prove the timeout semantic using only an ephemeral loopback server."""

    model_body = json.dumps(
        {
            "id": "loopback",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "ok"}],
                }
            ],
            "usage": {},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    search_body = json.dumps(
        {
            "output": [
                {
                    "type": "web_search_call",
                    "id": "loopback",
                    "status": "completed",
                    "action": {
                        "type": "search",
                        "query": "synthetic",
                        "sources": [],
                    },
                }
            ],
            "usage": {},
        },
        separators=(",", ":"),
    ).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            body = model_body if self.path == "/model" else search_body
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            for byte in body:
                try:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
                time.sleep(DRIP_SECONDS)

        def log_message(self, *_: object) -> None:
            return None

    class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True

    records: dict[str, dict[str, Any]] = {}
    with Server(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            model_deadline = time.monotonic() + TOTAL_DEADLINE_SECONDS
            model = DeadlineAwareResponsesClient(
                base_url + "/model",
                "synthetic",
                timeout=10,
                max_retries=1,
                absolute_deadline=model_deadline,
                cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
                minimum_attempt_seconds=0.01,
            )
            started = time.monotonic()
            model_result = model.complete("synthetic", "synthetic", max_output_tokens=1)
            model_elapsed = time.monotonic() - started
            records["model"] = {
                "elapsed_seconds": round(model_elapsed, 6),
                "returned_success": model_result.text == "ok",
                "remaining_effect_seconds_after_return": round(
                    model.remaining_effect_seconds(), 6
                ),
                "returned_after_total_deadline": time.monotonic() > model_deadline,
            }

            search_deadline = time.monotonic() + TOTAL_DEADLINE_SECONDS
            search = DeadlineAwareNativeSearchClient(
                base_url + "/search",
                "synthetic",
                timeout=10,
                max_retries=1,
                fetch_pages=False,
                max_workers=1,
                hard_fetch_deadline_seconds=25,
                absolute_deadline=search_deadline,
                cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
                minimum_attempt_seconds=0.01,
            )
            started = time.monotonic()
            search_result = search._request(["synthetic"])
            search_elapsed = time.monotonic() - started
            records["hosted_search"] = {
                "elapsed_seconds": round(search_elapsed, 6),
                "returned_success": bool(search_result.get("output")),
                "remaining_effect_seconds_after_return": round(
                    search.remaining_effect_seconds(), 6
                ),
                "returned_after_total_deadline": time.monotonic() > search_deadline,
            }
        finally:
            server.shutdown()
            thread.join(timeout=2)

    proved = all(
        record["returned_success"] is True
        and record["returned_after_total_deadline"] is True
        and record["remaining_effect_seconds_after_return"] == 0.0
        and record["elapsed_seconds"] > TOTAL_DEADLINE_SECONDS
        for record in records.values()
    )
    return {
        "scope": "ephemeral_127_0_0_1_slow_drip_http_only",
        "configured_total_deadline_seconds": TOTAL_DEADLINE_SECONDS,
        "configured_cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
        "configured_initial_effect_window_seconds": round(
            TOTAL_DEADLINE_SECONDS - CLEANUP_RESERVE_SECONDS, 6
        ),
        "drip_interval_seconds": DRIP_SECONDS,
        "model": records["model"],
        "hosted_search": records["hosted_search"],
        "both_returned_success_after_total_deadline": proved,
        "external_network_model_search_fetch_or_evaluator_called": False,
        "benchmark_task_or_private_content_used": False,
    }


def _source_invariants() -> dict[str, bool]:
    model = base._ordinary(MODEL_DEADLINE_SOURCE).read_text(encoding="utf-8")
    search = base._ordinary(SEARCH_DEADLINE_SOURCE).read_text(encoding="utf-8")
    persistence = base._ordinary(PERSISTENCE_SOURCE).read_text(encoding="utf-8")
    runner = base._ordinary(GATE_SOURCE).read_text(encoding="utf-8")
    search_request = search[search.index("    def _request(") : search.index("    def _fetch_url(")]
    model_complete = model[model.index("    def complete(") : model.index("\n\ndef _ordinary_output_directory")]
    return {
        "model_requests_timeout_is_clamped_to_remaining_effect_seconds": (
            "request_timeout = min(float(self.timeout), remaining)" in model_complete
            and "timeout=request_timeout" in model_complete
        ),
        "hosted_search_timeout_is_clamped_to_remaining_effect_seconds": (
            "timeout=min(self.static_search_timeout_seconds, remaining)"
            in search_request
        ),
        "model_request_path_has_no_hard_total_wall_timer_or_process_boundary": all(
            token not in model_complete
            for token in ("setitimer", "SIGALRM", "subprocess.Popen", "multiprocessing")
        ),
        "hosted_search_request_path_has_no_hard_total_wall_timer_or_process_boundary": all(
            token not in search_request
            for token in ("setitimer", "SIGALRM", "subprocess.Popen", "multiprocessing")
        ),
        "single_validation_still_waits_for_complete_v24457_validation_before_capability": (
            "outcome = adaptive.run_v24457_task(" in persistence
            and "if len(captured) != 1:" in persistence
            and persistence.index("outcome = adaptive.run_v24457_task(")
            < persistence.index("return ValidatedAdaptiveExecution._create(")
        ),
        "v24466_effect_and_parent_deadlines_leave_frozen_65_second_reserve": all(
            token in runner
            for token in (
                "EFFECT_DEADLINE_SECONDS = 190",
                "PARENT_TIMEOUT_SECONDS = 255",
                "TERMINAL_RESERVE_SECONDS = PARENT_TIMEOUT_SECONDS - EFFECT_DEADLINE_SECONDS",
            )
        ),
    }


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result, build_audit = _validate_parents()
    observation = result["observation_aggregate"]
    timing = result["stage_timing_aggregate"]
    performance = build_audit["performance_evidence"]
    probe = _slow_drip_probe()
    invariants = _source_invariants()
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    tracked = all(base._tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    ]
    findings: list[str] = []
    if not all(invariants.values()):
        findings.append("deadline_or_validation_source_invariant_drifted")
    if probe.get("both_returned_success_after_total_deadline") is not True:
        findings.append("loopback_total_wall_counterexample_not_reproduced")
    if not tracked:
        findings.append("v24467_diagnosis_source_not_tracked")
    if head != remote:
        findings.append("v24467_diagnosis_source_commit_not_pushed")
    if not clean:
        findings.append("v24467_diagnosis_worktree_not_clean")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if secret_hits:
        findings.append("credential_literal_in_v24467_surface")

    value = {
        "artifact_version": 1,
        "role": "v24467_v24466_total_wall_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(base._ordinary(RESULT))},
            "decision": {
                "path": str(DECISION),
                "sha256": sha256(base._ordinary(DECISION)),
            },
            "postresult_audit": {
                "path": str(POSTAUDIT),
                "sha256": sha256(base._ordinary(POSTAUDIT)),
            },
            "single_validation_build_audit": {
                "path": str(BUILD_AUDIT),
                "sha256": sha256(base._ordinary(BUILD_AUDIT)),
            },
        },
        "public_observation": {
            "selected": int(result["selected"]),
            "one_wave": bool(result["one_wave"]),
            "effect_deadline_seconds": int(result["effect_deadline_seconds"]),
            "parent_timeout_seconds": int(result["parent_timeout_seconds"]),
            "terminal_reserve_seconds": int(result["terminal_reserve_seconds"]),
            "batch_wall_seconds": float(result["batch_wall_seconds"]),
            "parent_hard_timeout_tasks": int(
                observation["parent_taxonomy_counts"]["hard_deadline_timeout"]
            ),
            "failure_snapshot_tasks": int(observation["failure_snapshot_tasks"]),
            "unobserved_effect_tasks": int(observation["unobserved_effect_tasks"]),
            "child_wall_p95_seconds": float(timing["child_wall_p95_seconds"]),
            "certificate_validation_invocations": int(
                timing["certificate_validation_invocations"]
            ),
            "recursive_historical_semantic_replay_tasks": int(
                timing["recursive_historical_semantic_replay_tasks"]
            ),
        },
        "loopback_counterexample": probe,
        "validation_budget_evidence": {
            "synthetic_complete_validation_wall_seconds": float(
                performance["complete_validation_wall_seconds"]
            ),
            "synthetic_fast_persistence_p95_seconds": float(
                performance["fast_envelope_p95_seconds"]
            ),
            "synthetic_profile_is_not_external_latency_estimate": bool(
                performance["profile_is_not_external_latency_estimate"]
            ),
            "real_external_validation_wall_seconds_observed": False,
            "real_external_terminal_reserve_adequacy_proven": False,
        },
        "diagnosis": {
            "requests_timeout_is_inactivity_not_total_wall_counterexample_proven": True,
            "current_model_and_hosted_search_can_return_success_after_absolute_deadline": True,
            "total_wall_gap_is_sufficient_to_allow_effect_overrun": True,
            "total_wall_gap_proven_as_unique_v24466_cause": False,
            "exact_v24466_blocking_call_or_validation_stage_identifiable": False,
            "private_task_directories_were_deleted_before_diagnosis": True,
            "duplicate_post_validation_recursive_envelope_replay_was_removed": True,
            "first_complete_semantic_validation_remains_before_terminal_persistence": True,
            "first_complete_validation_has_independent_total_wall_bound": False,
            "future_true_total_wall_effect_guard_required": True,
            "future_content_free_stage_checkpoint_required": True,
            "future_bounded_single_validation_finalize_required": True,
            "same_v24466_population_rerun_allowed": False,
            "benchmark_quality_measured": False,
            "sota_supported": False,
        },
        "source_invariants": invariants,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "local_loopback_http_probe_called": True,
            "external_network_model_search_fetch_or_evaluator_called": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "v24466_private_task_directories_reopened": False,
            "v24466_rerun_resume_retry_or_selective_revaluation": False,
        },
        "credential_literal_hits": secret_hits,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "true_total_wall_effect_guard_design": not findings,
            "content_free_stage_checkpoint_design": not findings,
            "bounded_single_validation_finalize_design": not findings,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    diagnosis = copied.get("diagnosis")
    authorization = copied.get("authorization")
    counterexample = copied.get("loopback_counterexample")
    findings = copied.get("findings")
    valid = findings == []
    design_fields = (
        "true_total_wall_effect_guard_design",
        "content_free_stage_checkpoint_design",
        "bounded_single_validation_finalize_design",
    )
    forbidden = (
        "external_probe_launch",
        "paired_dev64",
        "exact220",
        "evaluator",
        "leaderboard_or_sota",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v24467_v24466_total_wall_diagnosis"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied["created_at_unix"] < 0
        or not isinstance(diagnosis, Mapping)
        or diagnosis.get(
            "requests_timeout_is_inactivity_not_total_wall_counterexample_proven"
        )
        is not True
        or diagnosis.get("total_wall_gap_proven_as_unique_v24466_cause") is not False
        or diagnosis.get("exact_v24466_blocking_call_or_validation_stage_identifiable")
        is not False
        or diagnosis.get("same_v24466_population_rerun_allowed") is not False
        or diagnosis.get("benchmark_quality_measured") is not False
        or diagnosis.get("sota_supported") is not False
        or not isinstance(counterexample, Mapping)
        or counterexample.get("both_returned_success_after_total_deadline") is not True
        or counterexample.get("external_network_model_search_fetch_or_evaluator_called")
        is not False
        or copied.get("diagnosis_valid") is not valid
        or not isinstance(authorization, Mapping)
        or any(authorization.get(name) is not valid for name in design_fields)
        or any(authorization.get(name) is not False for name in forbidden)
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.67 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    report = build_report()
    validate_report(report)
    publish_new(ROOT / REPORT, report)
    print(json.dumps({"path": str(REPORT), "diagnosis_valid": report["diagnosis_valid"]}))
