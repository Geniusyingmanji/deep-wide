#!/usr/bin/env python3
"""Content-free diagnosis of the V2.44.72 pre-effect ValidationError.

The frozen public result shows eight workers entering runtime, then exiting
with ``ValidationError`` before any model, hosted-search, or public-fetch
effect started.  This report binds that evidence to a local construction-only
counterexample: V2.44.70's hard-total-wall task-union search client satisfies
the operational transport surface but is not a nominal instance of the older
V2.43.91 task-union search class required by V2.44.38.

No task-private directory survived the run, so the report does not claim a
private traceback.  It proves that the frozen runtime deterministically rejects
the exact formal client type at the same pre-effect contract boundary, and
that a multiple-inheritance compatibility class can preserve the hard-total-
wall method resolution order while satisfying the legacy nominal check.

The report authorizes only append-only compatibility design and local tests.
It never authorizes another external population, benchmark, evaluator, or a
rerun of the V2.44.72 population.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    UncertaintyDeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    build_effect_timeout_contract,
)
from deepwide_agent.v24470_bounded_adaptive_integration import (  # noqa: E402
    HardTotalWallUncertaintyNativeSearchClient,
    build_hard_total_wall_model,
    build_hard_total_wall_search,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts import v24472_bounded_adaptive_external_gate as gate  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
REPORT = Path(f"results/v24473_v24472_nominal_transport_diagnosis_v1_{DATE}.json")
RESULT = gate.RESULT
DECISION = gate.DECISION
POSTAUDIT = gate.POSTAUDIT
LEGACY_CONTRACT_SOURCE = Path(
    "src/deepwide_agent/v24438_bounded_narrative_effect_runner.py"
)
HARD_INTEGRATION_SOURCE = Path(
    "src/deepwide_agent/v24470_bounded_adaptive_integration.py"
)
DIAGNOSIS_SOURCE = Path("scripts/diagnose_v24473_v24472_nominal_transport.py")
TEST_SOURCE = Path("tests/test_diagnose_v24473_v24472_nominal_transport.py")
SOURCES = (
    LEGACY_CONTRACT_SOURCE,
    HARD_INTEGRATION_SOURCE,
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


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.73 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> dict[str, Any]:
    result = gate.validate_public_result(_read(RESULT))
    decision = gate.validate_decision(ROOT, value=_read(DECISION))
    audit = gate.validate_postaudit(ROOT, value=_read(POSTAUDIT))
    observation = result["observation_aggregate"]
    supervision = result["supervision_aggregate"]
    if (
        result.get("selected") != 8
        or result.get("batch_wall_seconds") != 1.050554
        or result.get("passed") is not False
        or result.get("diagnostic_complete") is not False
        or observation.get("parent_taxonomy_counts")
        != {"child_nonzero_with_terminal_receipt": 8}
        or observation.get("child_stage_counts") != {"child_exception": 8}
        or observation.get("child_exception_type_counts")
        != {"ValidationError": 8}
        or observation.get("failure_stage_counts") != {"runtime": 8}
        or observation.get("failure_exception_type_counts")
        != {"ValidationError": 8}
        or observation.get("fully_observed_effect_tasks") != 8
        or observation.get("unobserved_effect_tasks") != 0
        or supervision.get("worker_success_tasks") != 0
        or supervision.get("worker_hard_timeout_tasks") != 0
        or supervision.get("worker_nonzero_tasks") != 8
        or supervision.get("checkpoint_chain_valid_tasks") != 8
        or supervision.get("last_stage_counts") != {"runtime_entered": 8}
        or any(
            supervision.get(name) != 0
            for name in (
                "model_effect_started_lower_bound",
                "model_effect_finished_lower_bound",
                "hosted_search_effect_started_lower_bound",
                "hosted_search_effect_finished_lower_bound",
                "public_fetch_effect_started_lower_bound",
                "public_fetch_effect_finished_lower_bound",
                "complete_validation_entered_tasks",
                "complete_validation_returned_tasks",
            )
        )
        or decision.get("status") != "fresh_bounded_adaptive_external_no_go"
        or decision.get("diagnostic_route") != "worker_exception_successor"
        or decision.get("authorization", {}).get("diagnostic_successor_design")
        is not True
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("shared_api_lease_active") is not False
        or not _sealed(result, "result_payload_sha256")
        or not _sealed(decision, "decision_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.73 parent closure drifted")
    return result


def _construction_probe() -> dict[str, Any]:
    """Exercise only local constructors and the legacy type contract."""

    class CompatibleHardSearch(
        HardTotalWallUncertaintyNativeSearchClient,
        UncertaintyDeadlineAwareNativeSearchClient,
    ):
        pass

    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
        output_root = Path(temporary)
        slots = output_root / "slots"
        slots.mkdir()
        for index in (1, 2):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
        deadline = time.monotonic() + 150.0
        model = build_hard_total_wall_model(
            url="http://127.0.0.1:9/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=70.0,
            max_retries=1,
            slot_directory=slots,
            output_root=output_root,
            slot_cap=2,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
            stage_callback=lambda _stage: None,
        )
        search = build_hard_total_wall_search(
            url="http://127.0.0.1:9/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=70.0,
            max_retries=1,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
            stage_callback=lambda _stage: None,
            fetch_pages=False,
        )
        before_model = model.receipt()
        before_transport = search.transport_health()
        before_search = search.single_shot_receipt()
        exception_type: str | None = None
        exception_message: str | None = None
        try:
            build_effect_timeout_contract(model, search)
        except Exception as error:  # exact fields are validated below
            exception_type = type(error).__name__
            exception_message = str(error)
        after_model = model.receipt()
        after_transport = search.transport_health()
        after_search = search.single_shot_receipt()

    model_before_effect_surface = {
        key: value
        for key, value in before_model.items()
        if key not in {"remaining_seconds_at_receipt", "receipt_payload_sha256"}
    }
    model_after_effect_surface = {
        key: value
        for key, value in after_model.items()
        if key not in {"remaining_seconds_at_receipt", "receipt_payload_sha256"}
    }

    hard_request_owner = next(
        cls.__name__
        for cls in CompatibleHardSearch.__mro__
        if "_request" in cls.__dict__
    )
    return {
        "scope": "local_constructor_and_nominal_contract_only",
        "formal_search_type": type(search).__name__,
        "legacy_required_search_type": UncertaintyDeadlineAwareNativeSearchClient.__name__,
        "formal_search_is_legacy_nominal_instance": isinstance(
            search, UncertaintyDeadlineAwareNativeSearchClient
        ),
        "formal_search_is_hard_total_wall_instance": isinstance(
            search, HardTotalWallUncertaintyNativeSearchClient
        ),
        "legacy_contract_exception_type": exception_type,
        "legacy_contract_exception_message": exception_message,
        "model_effect_surface_unchanged": (
            model_before_effect_surface == model_after_effect_surface
        ),
        "model_remaining_seconds_nonincreasing": (
            after_model["remaining_seconds_at_receipt"]
            <= before_model["remaining_seconds_at_receipt"]
        ),
        "transport_receipt_unchanged": before_transport == after_transport,
        "search_receipt_unchanged": before_search == after_search,
        "provider_model_acquisitions": after_model["acquisitions"],
        "hosted_search_attempts": after_transport["hosted_search_attempts"],
        "hard_fetch_helper_calls": after_transport["hard_fetch_helper_calls"],
        "compatible_class_is_legacy_nominal_subclass": issubclass(
            CompatibleHardSearch, UncertaintyDeadlineAwareNativeSearchClient
        ),
        "compatible_class_is_hard_total_wall_subclass": issubclass(
            CompatibleHardSearch, HardTotalWallUncertaintyNativeSearchClient
        ),
        "compatible_class_request_method_owner": hard_request_owner,
        "compatible_class_mro": [cls.__name__ for cls in CompatibleHardSearch.__mro__],
        "external_network_model_search_fetch_or_evaluator_called": False,
        "benchmark_task_or_private_content_used": False,
    }


def _source_invariants() -> dict[str, bool]:
    legacy = base._ordinary(LEGACY_CONTRACT_SOURCE).read_text(encoding="utf-8")
    integration = base._ordinary(HARD_INTEGRATION_SOURCE).read_text(encoding="utf-8")
    contract = legacy[
        legacy.index("def build_effect_timeout_contract(") : legacy.index(
            "\ndef validate_effect_timeout_contract("
        )
    ]
    hard_class = integration[
        integration.index("class HardTotalWallUncertaintyNativeSearchClient(") : integration.index(
            "\n\n@dataclass", integration.index("class HardTotalWallUncertaintyNativeSearchClient(")
        )
    ]
    return {
        "legacy_contract_uses_nominal_search_isinstance": (
            "isinstance(search, UncertaintyDeadlineAwareNativeSearchClient)" in contract
        ),
        "legacy_rejection_occurs_before_remaining_or_effect_use": (
            contract.index("isinstance(search, UncertaintyDeadlineAwareNativeSearchClient)")
            < contract.index("remaining = min(")
        ),
        "hard_search_class_omits_legacy_nominal_base": (
            "UncertaintyDeadlineAwareNativeSearchClient" not in hard_class
        ),
        "hard_search_class_retains_task_union_and_hard_transport": all(
            token in hard_class
            for token in (
                "TaskUnionSingleShotMixin",
                "HardTotalWallNativeSearchClient",
            )
        ),
    }


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result = _validate_parents()
    observation = result["observation_aggregate"]
    supervision = result["supervision_aggregate"]
    probe = _construction_probe()
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
    probe_valid = (
        probe["formal_search_is_legacy_nominal_instance"] is False
        and probe["formal_search_is_hard_total_wall_instance"] is True
        and probe["legacy_contract_exception_type"] == "ValueError"
        and probe["legacy_contract_exception_message"]
        == "V2.44.38 requires deadline-aware search transport"
        and probe["model_effect_surface_unchanged"] is True
        and probe["model_remaining_seconds_nonincreasing"] is True
        and probe["transport_receipt_unchanged"] is True
        and probe["search_receipt_unchanged"] is True
        and probe["provider_model_acquisitions"] == 0
        and probe["hosted_search_attempts"] == 0
        and probe["hard_fetch_helper_calls"] == 0
        and probe["compatible_class_is_legacy_nominal_subclass"] is True
        and probe["compatible_class_is_hard_total_wall_subclass"] is True
        and probe["compatible_class_request_method_owner"]
        == "HardTotalWallNativeSearchClient"
        and probe["external_network_model_search_fetch_or_evaluator_called"] is False
        and probe["benchmark_task_or_private_content_used"] is False
    )
    findings: list[str] = []
    if not all(invariants.values()):
        findings.append("nominal_transport_source_invariant_drifted")
    if not probe_valid:
        findings.append("local_nominal_transport_counterexample_failed")
    if not tracked:
        findings.append("v24473_diagnosis_source_not_tracked")
    if head != remote:
        findings.append("v24473_diagnosis_source_commit_not_pushed")
    if not clean:
        findings.append("v24473_diagnosis_worktree_not_clean")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if secret_hits:
        findings.append("credential_literal_in_v24473_surface")
    valid = not findings
    value = {
        "artifact_version": 1,
        "role": "v24473_v24472_nominal_transport_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(base._ordinary(RESULT))},
            "decision": {"path": str(DECISION), "sha256": sha256(base._ordinary(DECISION))},
            "postaudit": {"path": str(POSTAUDIT), "sha256": sha256(base._ordinary(POSTAUDIT))},
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "public_observation": {
            "selected": 8,
            "worker_nonzero_tasks": supervision["worker_nonzero_tasks"],
            "worker_hard_timeout_tasks": supervision["worker_hard_timeout_tasks"],
            "checkpoint_chain_valid_tasks": supervision["checkpoint_chain_valid_tasks"],
            "last_stage_counts": supervision["last_stage_counts"],
            "child_exception_type_counts": observation["child_exception_type_counts"],
            "failure_stage_counts": observation["failure_stage_counts"],
            "fully_observed_effect_tasks": observation["fully_observed_effect_tasks"],
            "model_effect_started_lower_bound": supervision["model_effect_started_lower_bound"],
            "hosted_search_effect_started_lower_bound": supervision["hosted_search_effect_started_lower_bound"],
            "public_fetch_effect_started_lower_bound": supervision["public_fetch_effect_started_lower_bound"],
        },
        "construction_probe": probe,
        "source_invariants": invariants,
        "diagnosis": {
            "formal_hard_search_rejected_by_legacy_nominal_contract": True,
            "rejection_precedes_any_model_search_or_fetch_effect": True,
            "public_failure_signature_matches_local_contract_rejection": True,
            "private_v24472_traceback_available": False,
            "nominal_mismatch_proven_as_unique_private_v24472_exception": False,
            "append_only_multiple_inheritance_compatibility_is_feasible": True,
            "hard_total_wall_request_resolution_can_remain_first": True,
            "same_v24472_population_rerun_allowed": False,
        },
        "source_policy": {
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "construction_probe_network_model_search_fetch_or_evaluator_called": False,
            "construction_probe_task_or_private_content_used": False,
        },
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
            "active_run_killed_or_quarantined": False,
        },
        "credential_literal_hits": secret_hits,
        "findings": findings,
        "diagnosis_valid": valid,
        "authorization": {
            "append_only_nominal_compatibility_design": valid,
            "local_synthetic_integration_test_design": valid,
            "same_v24472_population_rerun": False,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(
    value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(REPORT)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    valid = copied.get("findings") == []
    diagnosis = copied.get("diagnosis")
    authorization = copied.get("authorization")
    probe = copied.get("construction_probe")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v24473_v24472_nominal_transport_diagnosis"
        or copied.get("diagnosis_valid") is not valid
        or not isinstance(diagnosis, Mapping)
        or diagnosis.get("formal_hard_search_rejected_by_legacy_nominal_contract") is not True
        or diagnosis.get("rejection_precedes_any_model_search_or_fetch_effect") is not True
        or diagnosis.get("public_failure_signature_matches_local_contract_rejection") is not True
        or diagnosis.get("private_v24472_traceback_available") is not False
        or diagnosis.get("nominal_mismatch_proven_as_unique_private_v24472_exception") is not False
        or diagnosis.get("append_only_multiple_inheritance_compatibility_is_feasible") is not True
        or diagnosis.get("hard_total_wall_request_resolution_can_remain_first") is not True
        or diagnosis.get("same_v24472_population_rerun_allowed") is not False
        or not isinstance(probe, Mapping)
        or probe.get("legacy_contract_exception_type") != "ValueError"
        or probe.get("provider_model_acquisitions") != 0
        or probe.get("hosted_search_attempts") != 0
        or probe.get("hard_fetch_helper_calls") != 0
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or not isinstance(authorization, Mapping)
        or authorization.get("append_only_nominal_compatibility_design") is not valid
        or authorization.get("local_synthetic_integration_test_design") is not valid
        or authorization.get("same_v24472_population_rerun") is not False
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
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.73 diagnosis drifted")
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
