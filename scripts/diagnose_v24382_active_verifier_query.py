#!/usr/bin/env python3
"""Content-free diagnosis of the V2.43.81 adaptive-verifier no-go."""

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
from scripts import v24381_adaptive_heldout_external_gate as parent  # noqa: E402


DATE = "20260804"
RESULT = Path(f"results/v24382_active_verifier_query_diagnosis_v1_{DATE}.json")
PARENT_RESULT = parent.RESULT
PARENT_DECISION = parent.DECISION
PARENT_AUDIT = parent.POSTAUDIT
POLICY_ID = "v24382_candidate_conditioned_active_verifier_query_diagnosis_v1"


def _read(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.43.82 expected an ordinary repository artifact")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.82 expected a JSON object")
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
    frozen_result = parent.validate_public_result(_read(root, PARENT_RESULT))
    decision = parent.validate_decision(root)
    audit = parent.validate_postaudit(root)
    observed = decision["observed"]
    if (
        frozen_result["passed"] is not False
        or decision["status"] != "fresh_adaptive_heldout_external_no_go"
        or decision["passed"] is not False
        or audit["audit_valid"] is not True
        or audit["findings"] != []
        or decision["authorization"]["fresh_paired_dev64_design"] is not False
        or decision["authorization"]["new_exact220"] is not False
    ):
        raise RuntimeError("V2.43.82 parent no-go identity drifted")
    value = {
        "artifact_version": 1,
        "role": "v24382_active_verifier_query_diagnosis",
        "policy_id": POLICY_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(PARENT_RESULT): sha256(root / PARENT_RESULT),
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        },
        "observed_no_go": {
            "selected": observed["selected"],
            "terminal_success_tasks": observed["terminal_success_tasks"],
            "structurally_passed_tasks": observed["structurally_passed_tasks"],
            "batch_wall_seconds": observed["batch_wall_seconds"],
            "preverification_nonidentity_tasks": observed[
                "preverification_nonidentity_tasks"
            ],
            "preverification_candidate_changed_cells": observed[
                "preverification_candidate_changed_cells"
            ],
            "selected_verifier_sources": observed["selected_verifier_sources"],
            "hidden_verifier_pages": observed["hidden_verifier_pages"],
            "verification_record_count": observed["verification_record_count"],
            "verifier_semantic_projection_count": frozen_result["aggregate"][
                "verifier_semantic_projection_count"
            ],
            "no_independent_candidate_support_records": observed[
                "no_independent_candidate_support_records"
            ],
            "selected_proposal_entropy_nats": observed[
                "selected_proposal_entropy_nats"
            ],
            "adaptive_retained_candidate_changed_cells": observed[
                "adaptive_retained_candidate_changed_cells"
            ],
            "utility_aligned_entropy_credit_nats": observed[
                "utility_aligned_entropy_credit_nats"
            ],
        },
        "diagnosis": {
            "proposal_generation_is_not_the_terminal_failure": (
                observed["preverification_candidate_changed_cells"] > 0
                and observed["selected_proposal_entropy_nats"] > 0
            ),
            "transport_or_deadline_is_not_the_terminal_failure": all(
                observed[name] == 0
                for name in (
                    "slot_timeouts",
                    "provider_deadline_failures",
                    "hosted_search_deadline_failures",
                    "hard_fetch_deadline_failures",
                    "fetch_helper_failures",
                    "deadline_exhausted_tasks",
                )
            ),
            "candidate_conditioned_source_selection_but_not_search": True,
            "pre_candidate_heldout_pool_has_zero_semantic_projection": (
                frozen_result["aggregate"]["verifier_semantic_projection_count"]
                == 0
            ),
            "all_verification_records_lack_independent_candidate_support": (
                observed["no_independent_candidate_support_records"]
                == observed["verification_record_count"]
            ),
            "proposal_entropy_does_not_receive_utility_credit": (
                observed["selected_proposal_entropy_nats"] > 0
                and observed["utility_aligned_entropy_credit_nats"] == 0
            ),
            "root_cause": "candidate_target_unavailable_when_verifier_source_pool_was_searched",
        },
        "successor_contract": {
            "candidate_and_support_freeze_precedes_verifier_query_generation": True,
            "verifier_queries_use_only_visible_question_and_frozen_row_column_value": True,
            "maximum_selected_candidate_targets": 2,
            "maximum_active_verifier_logical_queries": 2,
            "active_verifier_queries_execute_as_one_nonrecursive_batch": True,
            "maximum_total_hosted_search_batches": 3,
            "maximum_total_logical_queries": 6,
            "proposal_fetch_cap": 8,
            "active_verifier_fetch_cap": 2,
            "total_fetch_cap": 10,
            "model_call_cap": 3,
            "active_verifier_sources_must_be_disjoint_from_proposal_sources": True,
            "active_verifier_page_cannot_generate_or_edit_candidate_value": True,
            "active_verifier_can_only_retain_or_revert_frozen_candidate": True,
            "go_requires_selected_verified_candidate_change": True,
            "go_requires_positive_utility_aligned_entropy_credit": True,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_question_query_url_page_prediction_candidate_value_or_evidence_id_persisted": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        },
        "authorization": {
            "active_verifier_runtime_and_runner_design": True,
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
    observed = item.get("observed_no_go")
    diagnosis = item.get("diagnosis")
    contract = item.get("successor_contract")
    source = item.get("source_policy")
    authorization = item.get("authorization")
    if (
        set(item)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "created_at_unix",
            "parents",
            "observed_no_go",
            "diagnosis",
            "successor_contract",
            "source_policy",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or item.get("artifact_version") != 1
        or item.get("role") != "v24382_active_verifier_query_diagnosis"
        or item.get("policy_id") != POLICY_ID
        or isinstance(item.get("created_at_unix"), bool)
        or not isinstance(item.get("created_at_unix"), int)
        or item["created_at_unix"] < 0
        or parents
        != {
            str(PARENT_RESULT): sha256(root / PARENT_RESULT),
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        }
        or not isinstance(observed, Mapping)
        or observed.get("selected") != 16
        or observed.get("terminal_success_tasks") != 16
        or observed.get("structurally_passed_tasks") != 16
        or observed.get("preverification_candidate_changed_cells", 0) <= 0
        or observed.get("selected_proposal_entropy_nats", 0) <= 0
        or observed.get("verifier_semantic_projection_count") != 0
        or observed.get("no_independent_candidate_support_records")
        != observed.get("verification_record_count")
        or observed.get("adaptive_retained_candidate_changed_cells") != 0
        or observed.get("utility_aligned_entropy_credit_nats") != 0
        or not isinstance(diagnosis, Mapping)
        or diagnosis.get("root_cause")
        != "candidate_target_unavailable_when_verifier_source_pool_was_searched"
        or any(value_ is not True for key, value_ in diagnosis.items() if key != "root_cause")
        or not isinstance(contract, Mapping)
        or any(value_ is not True for key, value_ in contract.items() if isinstance(value_, bool))
        or contract.get("maximum_selected_candidate_targets") != 2
        or contract.get("maximum_active_verifier_logical_queries") != 2
        or contract.get("maximum_total_hosted_search_batches") != 3
        or contract.get("maximum_total_logical_queries") != 6
        or contract.get("proposal_fetch_cap") != 8
        or contract.get("active_verifier_fetch_cap") != 2
        or contract.get("total_fetch_cap") != 10
        or contract.get("model_call_cap") != 3
        or not isinstance(source, Mapping)
        or source.get("runtime_boundary") != ["opaque_id", "question"]
        or any(value_ is not False for key, value_ in source.items() if key != "runtime_boundary")
        or not isinstance(authorization, Mapping)
        or authorization.get("active_verifier_runtime_and_runner_design") is not True
        or any(
            value_ is not False
            for key, value_ in authorization.items()
            if key != "active_verifier_runtime_and_runner_design"
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.82 diagnosis drifted")
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
