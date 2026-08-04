#!/usr/bin/env python3
"""Content-free diagnosis of the V2.43.86 identity activation dead zone."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from scripts import v24386_active_verifier_external_gate as parent  # noqa: E402


DATE = "20260804"
RESULT = Path(f"results/v24387_identity_activation_dead_zone_diagnosis_v1_{DATE}.json")
PARENT_RESULT = parent.RESULT
PARENT_DECISION = parent.DECISION
PARENT_AUDIT = parent.POSTAUDIT
POLICY_ID = "v24387_identity_activation_dead_zone_diagnosis_v1"
SOURCE_FILES = (
    Path("src/deepwide_agent/v24333_programmatic_support_catalog.py"),
    Path("src/deepwide_agent/v24341_semantic_evidence_projection.py"),
    Path("src/deepwide_agent/v24349_structural_semantic_runtime.py"),
    Path("src/deepwide_agent/v24383_active_verifier_query_runtime.py"),
)


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.43.87 expected an ordinary repository artifact")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.87 expected a JSON object")
    return value


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def build(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    frozen = parent.validate_public_result(_read(root, PARENT_RESULT))
    decision = parent.validate_decision(root)
    audit = parent.validate_postaudit(root)
    aggregate = frozen["aggregate"]
    if (
        frozen["passed"] is not False
        or decision["status"] != "fresh_active_verifier_external_no_go"
        or decision["passed"] is not False
        or audit["audit_valid"] is not True
        or audit["findings"] != []
        or decision["authorization"]["fresh_paired_dev64_design"] is not False
        or decision["authorization"]["new_exact220"] is not False
        or aggregate["selected"] != 16
        or aggregate["terminal_success_tasks"] != 16
        or aggregate["structurally_passed_tasks"] != 16
        or aggregate["completion_kinds"] != {"identity_no_reserve": 16}
    ):
        raise RuntimeError("V2.43.87 parent no-go identity drifted")
    sources = {
        str(relative): sha256(_ordinary(root, relative))
        for relative in SOURCE_FILES
    }
    value = {
        "artifact_version": 1,
        "role": "v24387_identity_activation_dead_zone_diagnosis",
        "policy_id": POLICY_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(PARENT_RESULT): sha256(_ordinary(root, PARENT_RESULT)),
            str(PARENT_DECISION): sha256(_ordinary(root, PARENT_DECISION)),
            str(PARENT_AUDIT): sha256(_ordinary(root, PARENT_AUDIT)),
        },
        "source_manifest": sources,
        "source_manifest_sha256": payload_sha256(sources),
        "observed_no_go": {
            "selected": aggregate["selected"],
            "terminal_success_tasks": aggregate["terminal_success_tasks"],
            "structurally_passed_tasks": aggregate["structurally_passed_tasks"],
            "batch_wall_seconds": aggregate["batch_wall_seconds"],
            "identity_no_reserve_tasks": aggregate["completion_kinds"][
                "identity_no_reserve"
            ],
            "proposal_sources": aggregate["proposal_sources"],
            "proposal_unselected_sources": aggregate[
                "proposal_unselected_sources"
            ],
            "proposal_pages": aggregate["proposal_pages"],
            "fetch_calls": aggregate["fetch_calls"],
            "fetch_failures": aggregate["fetch_failures"],
            "parent_semantic_catalog_tasks": aggregate[
                "parent_semantic_catalog_tasks"
            ],
            "parent_eligible_support_tasks": aggregate[
                "parent_eligible_support_tasks"
            ],
            "parent_eligible_support_set_count": aggregate[
                "parent_eligible_support_set_count"
            ],
            "parent_candidate_tasks": aggregate["parent_candidate_tasks"],
            "active_query_tasks": aggregate["active_query_tasks"],
            "model_requests": aggregate["model_requests"],
            "model_attempts": aggregate["model_attempts"],
            "slot_timeouts": aggregate["slot_timeouts"],
            "provider_deadline_failures": aggregate[
                "provider_deadline_failures"
            ],
            "hosted_search_deadline_failures": aggregate[
                "hosted_search_deadline_failures"
            ],
            "hard_fetch_deadline_failures": aggregate[
                "hard_fetch_deadline_failures"
            ],
            "fetch_helper_failures": aggregate["fetch_helper_failures"],
            "deadline_exhausted_tasks": aggregate["deadline_exhausted_tasks"],
            "selected_proposal_entropy_nats": aggregate[
                "selected_proposal_entropy_nats"
            ],
            "utility_aligned_entropy_credit_nats": aggregate[
                "utility_aligned_entropy_credit_nats"
            ],
        },
        "diagnosis": {
            "proposal_acquisition_succeeded": (
                aggregate["proposal_sources"] >= 96
                and aggregate["proposal_pages"] > 0
            ),
            "baseline_synthesis_succeeded_without_recovery_failure": (
                aggregate["model_requests"] == 2 * aggregate["selected"]
                and aggregate["model_attempts"] == aggregate["model_requests"]
            ),
            "semantic_catalog_was_built_for_every_task": (
                aggregate["parent_semantic_catalog_tasks"]
                == aggregate["selected"]
            ),
            "eligible_alternative_support_was_zero_for_every_task": (
                aggregate["parent_eligible_support_tasks"] == 0
                and aggregate["parent_eligible_support_set_count"] == 0
            ),
            "candidate_revision_was_safely_short_circuited": (
                aggregate["model_requests"] == 2 * aggregate["selected"]
                and aggregate["parent_candidate_tasks"] == 0
            ),
            "active_verifier_cannot_activate_without_a_frozen_candidate": (
                aggregate["parent_candidate_tasks"] == 0
                and aggregate["active_query_tasks"] == 0
            ),
            "transport_or_deadline_is_not_the_terminal_failure": all(
                aggregate[name] == 0
                for name in (
                    "slot_timeouts",
                    "provider_deadline_failures",
                    "hosted_search_deadline_failures",
                    "hard_fetch_deadline_failures",
                    "fetch_helper_failures",
                    "deadline_exhausted_tasks",
                )
            ),
            "v24386_did_not_measure_active_query_effectiveness": (
                aggregate["active_query_tasks"] == 0
            ),
            "root_cause": "candidate_revision_requires_preexisting_eligible_alternative_support_after_baseline_consumes_the_same_proposal_evidence",
        },
        "successor_contract": {
            "baseline_freeze_precedes_uncertainty_target_selection": True,
            "all_visible_cells_can_enter_uncertainty_catalog": True,
            "active_target_selection_does_not_require_a_preexisting_candidate_change": True,
            "target_score_uses_label_blind_support_disagreement_and_epistemic_uncertainty": True,
            "active_queries_use_only_frozen_row_and_column_not_gold_or_evaluator": True,
            "maximum_selected_targets": 2,
            "maximum_active_logical_queries": 2,
            "active_queries_execute_as_one_nonrecursive_batch": True,
            "active_sources_must_be_disjoint_from_proposal_sources": True,
            "combined_proposal_and_active_evidence_is_replayed_programmatically": True,
            "new_candidate_value_requires_independent_source_support": True,
            "epistemic_credit_uses_information_gain_even_when_baseline_is_confirmed": True,
            "decision_credit_requires_a_safe_final_output_change": True,
            "epistemic_and_decision_credit_are_reported_separately": True,
            "same_v24386_task_rerun_or_revaluation_allowed": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_question_query_url_page_prediction_candidate_value_or_evidence_id_persisted": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        },
        "authorization": {
            "uncertainty_catalog_and_active_evidence_design": True,
            "external_probe_design": False,
            "external_probe_launch": False,
            "paired_dev64": False,
            "new_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    validate(root, value=value)
    return value


def validate(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    item = dict(value) if value is not None else _read(root, RESULT)
    unsigned = dict(item)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    parents = item.get("parents")
    sources = item.get("source_manifest")
    observed = item.get("observed_no_go")
    diagnosis_value = item.get("diagnosis")
    contract = item.get("successor_contract")
    source_policy = item.get("source_policy")
    authorization = item.get("authorization")
    expected_sources = {
        str(relative): sha256(_ordinary(root, relative))
        for relative in SOURCE_FILES
    }
    if (
        set(item)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "created_at_unix",
            "parents",
            "source_manifest",
            "source_manifest_sha256",
            "observed_no_go",
            "diagnosis",
            "successor_contract",
            "source_policy",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or item.get("artifact_version") != 1
        or item.get("role")
        != "v24387_identity_activation_dead_zone_diagnosis"
        or item.get("policy_id") != POLICY_ID
        or isinstance(item.get("created_at_unix"), bool)
        or not isinstance(item.get("created_at_unix"), int)
        or item["created_at_unix"] < 0
        or parents
        != {
            str(PARENT_RESULT): sha256(_ordinary(root, PARENT_RESULT)),
            str(PARENT_DECISION): sha256(_ordinary(root, PARENT_DECISION)),
            str(PARENT_AUDIT): sha256(_ordinary(root, PARENT_AUDIT)),
        }
        or sources != expected_sources
        or item.get("source_manifest_sha256") != payload_sha256(expected_sources)
        or not isinstance(observed, Mapping)
        or observed.get("selected") != 16
        or observed.get("terminal_success_tasks") != 16
        or observed.get("structurally_passed_tasks") != 16
        or observed.get("identity_no_reserve_tasks") != 16
        or observed.get("proposal_sources", 0) < 96
        or observed.get("proposal_pages", 0) <= 0
        or observed.get("parent_semantic_catalog_tasks") != 16
        or observed.get("parent_eligible_support_tasks") != 0
        or observed.get("parent_eligible_support_set_count") != 0
        or observed.get("parent_candidate_tasks") != 0
        or observed.get("active_query_tasks") != 0
        or observed.get("model_requests") != 32
        or observed.get("model_attempts") != 32
        or observed.get("selected_proposal_entropy_nats") != 0
        or observed.get("utility_aligned_entropy_credit_nats") != 0
        or not isinstance(diagnosis_value, Mapping)
        or diagnosis_value.get("root_cause")
        != "candidate_revision_requires_preexisting_eligible_alternative_support_after_baseline_consumes_the_same_proposal_evidence"
        or any(
            current is not True
            for name, current in diagnosis_value.items()
            if name != "root_cause"
        )
        or not isinstance(contract, Mapping)
        or contract.get("maximum_selected_targets") != 2
        or contract.get("maximum_active_logical_queries") != 2
        or contract.get("same_v24386_task_rerun_or_revaluation_allowed")
        is not False
        or any(
            current is not True
            for name, current in contract.items()
            if name
            not in {
                "maximum_selected_targets",
                "maximum_active_logical_queries",
                "same_v24386_task_rerun_or_revaluation_allowed",
            }
        )
        or not isinstance(source_policy, Mapping)
        or source_policy.get("runtime_boundary") != ["opaque_id", "question"]
        or any(
            current is not False
            for name, current in source_policy.items()
            if name != "runtime_boundary"
        )
        or not isinstance(authorization, Mapping)
        or authorization.get("uncertainty_catalog_and_active_evidence_design")
        is not True
        or any(
            current is not False
            for name, current in authorization.items()
            if name != "uncertainty_catalog_and_active_evidence_design"
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.87 diagnosis drifted")
    parent.validate_decision(root)
    parent.validate_postaudit(root)
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args()
    if args.command == "build":
        _write_new(ROOT / RESULT, build())
    else:
        validate()


if __name__ == "__main__":
    main()
