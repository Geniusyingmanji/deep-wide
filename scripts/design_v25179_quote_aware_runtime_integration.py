#!/usr/bin/env python3
"""Freeze the build-only V2.51.79 quote-aware runtime integration design."""

from __future__ import annotations

import ast
import copy
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

from scripts import audit_v25178_quote_aware_normalizer_build as parent  # noqa: E402


DATE = "20260812"
ROLE = "v25179_quote_aware_runtime_integration_design"
OUTPUT = Path(f"results/v25179_quote_aware_runtime_integration_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25179_quote_aware_runtime_integration.py")
TEST = Path("tests/test_design_v25179_quote_aware_runtime_integration.py")
PARENT_AUDIT = parent.OUTPUT
EXPECTED_PARENT_AUDIT_SHA256 = (
    "d4394e1f581b6963e67c6662d3dec2a3f80dbf3817f0c6d5dd394a984dc04763"
)
EXPECTED_NORMALIZER_SHA256 = (
    "12cb76288b69b588d472ca8dcbbda169e676a73b48e61880c192902b0816e95d"
)
RUNTIME_PARENT = Path(
    "src/deepwide_agent/v25165_observed_vertical_key_value_runtime.py"
)
SPARSE_PARENT = Path("src/deepwide_agent/v25135_sparse_production_runtime.py")


def _ordinary(relative: Path) -> Path:
    return parent.base._ordinary(relative)


def _parent_barrier() -> bool:
    raw = json.loads(_ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    checked = parent.validate_audit(raw)
    authorization = checked["authorization"]
    return bool(
        parent.base.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_SHA256
        and parent.base.sha256(parent.NORMALIZER_SOURCE)
        == EXPECTED_NORMALIZER_SHA256
        and checked["audit_valid"] is True
        and checked["findings"] == []
        and checked["tests"]["expected"] == 37
        and checked["tests"]["observed"] == 37
        and authorization["pure_normalizer_build_valid"] is True
        and authorization["runtime_integration_design"] is True
        and authorization["runtime_integration_implementation"] is False
        and authorization["fresh_external_protocol_or_launch"] is False
        and authorization["old_population_retry_resume_rerun_or_reuse"] is False
        and authorization["binding_successor_design"] is False
        and authorization["vertical_binding_policy_change"] is False
        and authorization["evaluator_or_deepwidebench_or_sota"] is False
    )


def integration_contract() -> dict[str, Any]:
    return {
        "parent_runtime": str(RUNTIME_PARENT),
        "sparse_parent": str(SPARSE_PARENT),
        "normalizer": str(parent.NORMALIZER_SOURCE),
        "only_treatment": "conditional_unambiguous_backslash_escaped_pipe_representation_repair",
        "provider_seam": "first_production_synthesis_response_before_sparse_parent_normalization",
        "raw_response_observed_before_repair": True,
        "frozen_exact_or_existing_normalized_output_is_never_rewritten": True,
        "repair_activates_only_after_frozen_normalizers_reject": True,
        "repair_requires_single_exact_header_width_exact_nonempty_table": True,
        "repair_requires_at_least_one_unambiguous_single_backslash_escaped_pipe": True,
        "ambiguous_backslash_row_width_entity_collision_multiple_table_or_partial_row_fails_closed": True,
        "internal_pipe_free_entity_table_passes_through_frozen_candidate_chain": True,
        "parent_plan_grounded_retrieval_candidate_selection_projection_and_failure_logic_unchanged": True,
        "outer_publication_runs_only_after_parent_terminal_validation": True,
        "final_entity_coordinates_must_be_subset_of_production_entity_coordinates": True,
        "new_or_moved_entity_causes_candidate_publication_to_fall_back_to_completed_production": True,
        "final_csv_quoting_preserves_public_loader_column_shape": True,
        "adjacent_pipe_whitespace_canonicalization_is_counted_not_hidden": True,
        "production_and_final_public_predictions_are_separately_hashed_and_parent_internal_result_remains_bound": True,
        "query_fetch_model_context_token_wall_network_and_concurrency_caps_unchanged": True,
        "observer_or_normalizer_failure_never_erases_completed_parent_prediction": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "old_v25175_population_retry_resume_rerun_or_reuse": False,
        "external_protocol_evaluator_deepwidebench_or_sota_authorized": False,
    }


def _semantic_checks() -> dict[str, bool]:
    source = _ordinary(SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    privileged = {
        str(node.slice.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value
        in {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
    }
    return {
        "parent_clean_build_audit_bound": _parent_barrier(),
        "direct_design_privileged_field_access_zero": not privileged,
        "credential_literal_zero": parent.base.SECRET.search(source) is None,
        "runtime_parent_and_sparse_parent_tracked": parent.base._tracked(
            RUNTIME_PARENT
        )
        and parent.base._tracked(SPARSE_PARENT),
        "shared_api_lease_inactive": parent.base._lease_inactive(),
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True
            for row in parent.base._watchers().values()
        ),
        "no_external_effect_performed": True,
    }


def build_design(*, now: int | None = None) -> dict[str, Any]:
    checks = _semantic_checks()
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": parent.base.sha256(PARENT_AUDIT),
        },
        "normalizer_source": {
            "path": str(parent.NORMALIZER_SOURCE),
            "sha256": parent.base.sha256(parent.NORMALIZER_SOURCE),
        },
        "integration_contract": integration_contract(),
        "checks": checks,
        "findings": findings,
        "design_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "quote_aware_runtime_integration_implementation_build_only": not findings,
            "fresh_external_protocol_or_launch": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
        },
    }
    value["design_payload_sha256"] = parent.payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("parent_audit")
        != {"path": str(PARENT_AUDIT), "sha256": EXPECTED_PARENT_AUDIT_SHA256}
        or copied.get("normalizer_source")
        != {
            "path": str(parent.NORMALIZER_SOURCE),
            "sha256": EXPECTED_NORMALIZER_SHA256,
        }
        or copied.get("integration_contract") != integration_contract()
        or copied.get("design_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "quote_aware_runtime_integration_implementation_build_only": True,
            "fresh_external_protocol_or_launch": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
        }
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.79 runtime integration design drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
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


def main() -> None:
    value = build_design()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "design_valid": value["design_valid"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
