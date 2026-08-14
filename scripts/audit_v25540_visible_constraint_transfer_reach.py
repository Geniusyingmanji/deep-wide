#!/usr/bin/env python3
"""Aggregate-only transfer audit for generic visible output constraints.

V2.55.39 stopped the IANA-only line because its exact intervention has zero
visible reach on the fixed DeepWideBench 220.  This audit examines a generic
successor surface before consuming another external population: explicit
date/year constraints, explicit numeric scales, and explicit rank/order
constraints in the same visible questions used at runtime.

The recognizers are frozen label-blind primitives from the legacy general
runtime plus one conservative explicit-order grammar defined here.  Legacy
presence is *not* treated as current capability.  The fixed V2.54.06 forward
dependency closure is inspected structurally; the legacy general runtime is
not in that closure and none of the six constraint primitives is referenced.

Only aggregate counts, source hashes, and the already-public task-vector
hashes are persisted.  No question, column, opaque id, per-task feature,
prediction, answer, score, evaluator output, URL, or page is written.  This
audit performs no model, search, fetch, evaluator, benchmark, or network
effect and authorizes no forward.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import runtime as legacy_constraints  # noqa: E402
from deepwide_agent import v24675_expanded_visible_schema as expanded_schema  # noqa: E402
from deepwide_agent import v25110_exact_visible_schema as exact_schema  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25406_grounded_membership_exact220_contract as exact220  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260814"
ROLE = "v25540_visible_constraint_transfer_reach_audit"
SOURCE = Path("scripts/audit_v25540_visible_constraint_transfer_reach.py")
TEST = Path("tests/test_audit_v25540_visible_constraint_transfer_reach.py")
OUTPUT = Path(
    f"results/v25540_visible_constraint_transfer_reach_audit_v1_{DATE}.json"
)
PARENT_DIAGNOSIS = Path(
    "results/v25539_v25538_iana_layout_no_go_diagnosis_v1_20260814.json"
)
PARENT_DIAGNOSIS_SHA256 = (
    "a16e1253b9be974f8287194dd6c901581c3e89f02dee4f9c919437af0994c62e"
)
FORWARD_AUDIT = Path(
    "results/v25406_grounded_membership_exact220_forward_audit_v1_20260813.json"
)
FORWARD_AUDIT_SHA256 = (
    "924a0adf0b5d5bed623c9ff3e2554e53c8ab5a543c25e6ee35e30d243b8b1d6b"
)
TASK_COUNT = 220
OPAQUE_VECTOR_SHA256 = (
    "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
)
QUESTION_VECTOR_SHA256 = (
    "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
)

CONSTRAINT_PRIMITIVES = (
    "requested_output_unit",
    "visible_date_output_style",
    "visible_year_ranges",
    "visible_top_k_claims",
    "normalize_supported_numeric_units",
    "promote_fixed_rank_slot_domain",
)

# Require an explicit direction/ordering construction.  Bare words such as
# "top", "ranking", or "order" alone are not sufficient.
_EXPLICIT_ORDER = re.compile(
    r"(?i)\b(?:ascending|descending|sort(?:ed)?\s+by|"
    r"in\s+(?:increasing|decreasing|chronological|reverse\s+chronological)"
    r"\s+order|ranked?\s+by|ordered?\s+by)\b|"
    r"(?:按|依).{0,40}(?:升序|降序|排列|排序)|"
    r"从(?:高到低|低到高|大到小|小到大|早到晚|晚到早)|"
    r"(?:升序|降序)排列"
)

CHECK_NAMES = frozenset(
    {
        "parent_diagnosis_hash_role_seal_and_generic_design_authority_bound",
        "fixed_exact220_forward_audit_hash_role_and_validity_bound",
        "visible_task_vector_exact220_and_hash_bound",
        "exact_and_expanded_schema_coverage_reproduced",
        "visible_membership_coverage_reproduced",
        "constraint_surfaces_have_nonzero_exact220_reach",
        "constraint_surfaces_have_broad_joint_exact220_reach",
        "legacy_general_runtime_absent_from_current_forward_closure",
        "current_forward_closure_references_none_of_six_constraint_primitives",
        "current_synthesis_receives_visible_question_but_has_no_mechanical_constraint_contract",
        "no_task_retention_replacement_ranking_or_selective_rerun",
        "mapping_gold_label_truth_score_reward_or_historical_result_not_read",
        "network_model_search_fetch_evaluator_or_benchmark_not_called",
        "entropy_information_gain_signed_credit_zero",
    }
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.40 expected JSON object")
    return value


def _parent_barriers() -> dict[str, Any]:
    if base.sha256(PARENT_DIAGNOSIS) != PARENT_DIAGNOSIS_SHA256:
        raise RuntimeError("V2.55.40 parent diagnosis hash drifted")
    if base.sha256(FORWARD_AUDIT) != FORWARD_AUDIT_SHA256:
        raise RuntimeError("V2.55.40 forward audit hash drifted")
    diagnosis = _read(PARENT_DIAGNOSIS)
    forward = _read(FORWARD_AUDIT)
    if (
        diagnosis.get("role")
        != "v25539_v25538_iana_layout_no_go_aggregate_diagnosis"
        or diagnosis.get("audit_valid") is not True
        or diagnosis.get("findings") != []
        or diagnosis.get("authorization", {}).get(
            "production_visible_generic_successor_design"
        )
        is not True
        or diagnosis.get("authorization", {}).get(
            "new_external_protocol_or_forward"
        )
        is not False
        or diagnosis.get("authorization", {}).get(
            "deepwidebench_forward_or_evaluator"
        )
        is not False
        or diagnosis.get("diagnosis_payload_sha256")
        != exact220.payload_sha256(
            {
                key: value
                for key, value in diagnosis.items()
                if key != "diagnosis_payload_sha256"
            }
        )
    ):
        raise RuntimeError("V2.55.40 parent diagnosis barrier drifted")
    if (
        forward.get("role") != "v24791_exact220_forward_audit"
        or forward.get("protocol_id") != exact220.PROTOCOL_ID
        or forward.get("audit_valid") is not True
        or forward.get("findings") != []
        or forward.get("authorization", {}).get(
            "forward_retry_resume_skip_backfill_replacement_or_rerun"
        )
        is not False
    ):
        raise RuntimeError("V2.55.40 fixed forward barrier drifted")
    return {"diagnosis": diagnosis, "forward": forward}


def _visible_surfaces() -> dict[str, Any]:
    vector = exact220.task_vector(ROOT)
    if (
        len(vector) != TASK_COUNT
        or any(set(task) != {"opaque_id", "question"} for task in vector)
        or exact220.payload_sha256([task["opaque_id"] for task in vector])
        != OPAQUE_VECTOR_SHA256
        or exact220.payload_sha256([task["question"] for task in vector])
        != QUESTION_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.40 visible task vector drifted")

    exact_count = expanded_only_count = any_schema_count = 0
    multicolumn_count = visible_membership_count = 0
    temporal: set[int] = set()
    temporal_range: set[int] = set()
    temporal_format: set[int] = set()
    numeric_scale: set[int] = set()
    rank_or_order: set[int] = set()
    top_k: set[int] = set()
    rank_column: set[int] = set()
    explicit_order: set[int] = set()
    schema_tasks: set[int] = set()
    multicolumn_tasks: set[int] = set()

    for index, task in enumerate(vector):
        question = task["question"]
        exact = tuple(exact_schema.extract_exact_visible_columns(question))
        expanded = tuple(expanded_schema.extract_expanded_visible_columns(question))
        columns = exact or expanded
        exact_count += int(bool(exact))
        expanded_only_count += int(not exact and bool(expanded))
        any_schema_count += int(bool(columns))
        multicolumn_count += int(len(columns) >= 2)
        if columns:
            schema_tasks.add(index)
        if len(columns) >= 2:
            multicolumn_tasks.add(index)
        visible_membership_count += int(bool(membership.visible_membership(question)[0]))

        if legacy_constraints.visible_year_ranges(question):
            temporal_range.add(index)
        if legacy_constraints.visible_date_output_style(question):
            temporal_format.add(index)
        if legacy_constraints.requested_output_unit(question, columns):
            numeric_scale.add(index)
        if legacy_constraints.visible_top_k_claims(question):
            top_k.add(index)
        if any(legacy_constraints._rank_column(column) for column in columns):
            rank_column.add(index)
        if _EXPLICIT_ORDER.search(question):
            explicit_order.add(index)

    temporal = temporal_range | temporal_format
    rank_or_order = top_k | rank_column | explicit_order
    any_constraint = temporal | numeric_scale | rank_or_order
    return {
        "task_count": len(vector),
        "runtime_input_keys": ["opaque_id", "question"],
        "opaque_id_vector_sha256": OPAQUE_VECTOR_SHA256,
        "visible_question_vector_sha256": QUESTION_VECTOR_SHA256,
        "exact_visible_schema_tasks": exact_count,
        "expanded_only_visible_schema_tasks": expanded_only_count,
        "any_explicit_visible_schema_tasks": any_schema_count,
        "explicit_multicolumn_schema_tasks": multicolumn_count,
        "strict_visible_membership_tasks": visible_membership_count,
        "temporal_year_range_tasks": len(temporal_range),
        "temporal_date_format_tasks": len(temporal_format),
        "temporal_constraint_union_tasks": len(temporal),
        "numeric_scale_constraint_tasks": len(numeric_scale),
        "top_k_constraint_tasks": len(top_k),
        "rank_column_tasks": len(rank_column),
        "explicit_order_direction_tasks": len(explicit_order),
        "rank_or_order_constraint_union_tasks": len(rank_or_order),
        "any_constraint_union_tasks": len(any_constraint),
        "any_constraint_with_explicit_schema_tasks": len(
            any_constraint & schema_tasks
        ),
        "any_constraint_with_multicolumn_schema_tasks": len(
            any_constraint & multicolumn_tasks
        ),
        "temporal_and_numeric_scale_overlap_tasks": len(
            temporal & numeric_scale
        ),
        "temporal_and_rank_or_order_overlap_tasks": len(
            temporal & rank_or_order
        ),
        "numeric_scale_and_rank_or_order_overlap_tasks": len(
            numeric_scale & rank_or_order
        ),
        "all_three_constraint_families_overlap_tasks": len(
            temporal & numeric_scale & rank_or_order
        ),
        "question_column_opaque_id_or_per_task_feature_persisted": False,
    }


def _constraint_reference_hits() -> tuple[tuple[str, ...], dict[str, list[str]]]:
    closure = exact220.forward_dependency_closure(ROOT)
    legacy = Path("src/deepwide_agent/runtime.py")
    hits: dict[str, list[str]] = {name: [] for name in CONSTRAINT_PRIMITIVES}
    for relative in closure:
        if relative.suffix != ".py":
            continue
        tree = ast.parse(
            (ROOT / relative).read_text(encoding="utf-8"), filename=str(relative)
        )
        for node in ast.walk(tree):
            name: str | None = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            if name in hits:
                hits[name].append(f"{relative}:{node.lineno}")
    return tuple(str(relative) for relative in closure), {
        name: sorted(set(values)) for name, values in hits.items()
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    barriers = _parent_barriers()
    exposure = _visible_surfaces()
    closure, reference_hits = _constraint_reference_hits()
    legacy_relative = "src/deepwide_agent/runtime.py"
    source_hashes = {
        str(PARENT_DIAGNOSIS): PARENT_DIAGNOSIS_SHA256,
        str(FORWARD_AUDIT): FORWARD_AUDIT_SHA256,
        str(exact220.RUNTIME): base.sha256(exact220.RUNTIME),
        "src/deepwide_agent/v25395_visible_membership_synthesis_runtime.py": base.sha256(
            Path("src/deepwide_agent/v25395_visible_membership_synthesis_runtime.py")
        ),
        "src/deepwide_agent/v25375_schema_total_changed_safe_runtime.py": base.sha256(
            Path("src/deepwide_agent/v25375_schema_total_changed_safe_runtime.py")
        ),
        "src/deepwide_agent/v24257_score_first_runtime.py": base.sha256(
            Path("src/deepwide_agent/v24257_score_first_runtime.py")
        ),
        legacy_relative: base.sha256(Path(legacy_relative)),
    }
    current_synthesis_receives_question = (
        "question=visible[\"question\"]"
        in base._ordinary(
            Path("src/deepwide_agent/v25370_shared_synthesis_changed_safe_runtime.py")
        ).read_text(encoding="utf-8")
    )
    no_constraint_references = all(not values for values in reference_hits.values())
    checks = {
        "parent_diagnosis_hash_role_seal_and_generic_design_authority_bound": bool(
            barriers["diagnosis"]
        ),
        "fixed_exact220_forward_audit_hash_role_and_validity_bound": bool(
            barriers["forward"]
        ),
        "visible_task_vector_exact220_and_hash_bound": exposure["task_count"]
        == TASK_COUNT,
        "exact_and_expanded_schema_coverage_reproduced": (
            exposure["exact_visible_schema_tasks"] == 194
            and exposure["expanded_only_visible_schema_tasks"] == 21
            and exposure["any_explicit_visible_schema_tasks"] == 215
            and exposure["explicit_multicolumn_schema_tasks"] == 212
        ),
        "visible_membership_coverage_reproduced": exposure[
            "strict_visible_membership_tasks"
        ]
        == 11,
        "constraint_surfaces_have_nonzero_exact220_reach": (
            exposure["temporal_constraint_union_tasks"] > 0
            and exposure["numeric_scale_constraint_tasks"] > 0
            and exposure["rank_or_order_constraint_union_tasks"] > 0
        ),
        "constraint_surfaces_have_broad_joint_exact220_reach": (
            exposure["any_constraint_union_tasks"] >= 120
            and exposure["any_constraint_with_explicit_schema_tasks"] >= 120
        ),
        "legacy_general_runtime_absent_from_current_forward_closure": legacy_relative
        not in closure,
        "current_forward_closure_references_none_of_six_constraint_primitives": no_constraint_references,
        "current_synthesis_receives_visible_question_but_has_no_mechanical_constraint_contract": (
            current_synthesis_receives_question and no_constraint_references
        ),
        "no_task_retention_replacement_ranking_or_selective_rerun": True,
        "mapping_gold_label_truth_score_reward_or_historical_result_not_read": True,
        "network_model_search_fetch_evaluator_or_benchmark_not_called": True,
        "entropy_information_gain_signed_credit_zero": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "frozen_inputs": source_hashes,
        "visible_transfer": exposure,
        "current_production_capability": {
            "exact220_protocol_id": exact220.PROTOCOL_ID,
            "forward_dependency_closure_file_count": len(closure),
            "legacy_general_runtime_in_forward_dependency_closure": False,
            "constraint_primitive_reference_hits": reference_hits,
            "constraint_primitive_reference_hit_count": sum(
                len(values) for values in reference_hits.values()
            ),
            "visible_question_is_in_current_synthesis_prompt": current_synthesis_receives_question,
            "schema_is_mechanically_constrained": True,
            "strict_visible_membership_is_mechanically_constrained_when_parsed": True,
            "temporal_numeric_scale_and_rank_order_are_only_model_instructions": True,
            "temporal_numeric_scale_or_rank_order_post_generation_validator": False,
            "temporal_numeric_scale_or_rank_order_deterministic_renderer": False,
            "legacy_code_presence_is_not_current_production_capability": True,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "transfer_decision": {
            "iana_only_successor": "stopped",
            "generic_visible_constraint_surface": "nonzero_transfer_reach",
            "current_production_equivalent_capability": "absent",
            "next_build_candidate": "visible_constraint_contract_for_shared_production_synthesis",
            "candidate_priority": [
                "temporal_year_range_and_date_format",
                "numeric_scale",
                "rank_top_k_and_explicit_order",
            ],
            "reason": "broad_visible_reach_with_zero_mechanical_coverage_in_current_forward_closure",
        },
        "task_rows_question_column_opaque_id_prediction_url_page_truth_evaluator_or_per_task_feature_persisted": False,
        "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "generic_visible_constraint_successor_build": not findings,
            "new_external_population_protocol_or_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = exact220.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    transfer = copied.get("visible_transfer") or {}
    capability = copied.get("current_production_capability") or {}
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or any(passed is not True for passed in checks.values())
        or copied.get("findings") != []
        or not valid
        or transfer.get("task_count") != TASK_COUNT
        or transfer.get("opaque_id_vector_sha256") != OPAQUE_VECTOR_SHA256
        or transfer.get("visible_question_vector_sha256")
        != QUESTION_VECTOR_SHA256
        or transfer.get("exact_visible_schema_tasks") != 194
        or transfer.get("expanded_only_visible_schema_tasks") != 21
        or transfer.get("any_explicit_visible_schema_tasks") != 215
        or transfer.get("strict_visible_membership_tasks") != 11
        or transfer.get("temporal_constraint_union_tasks") != 122
        or transfer.get("numeric_scale_constraint_tasks") != 23
        or transfer.get("rank_or_order_constraint_union_tasks") != 48
        or transfer.get("any_constraint_union_tasks") != 145
        or capability.get("legacy_general_runtime_in_forward_dependency_closure")
        is not False
        or capability.get("constraint_primitive_reference_hit_count") != 0
        or any(capability.get("constraint_primitive_reference_hits", {}).values())
        or capability.get("visible_question_is_in_current_synthesis_prompt")
        is not True
        or capability.get(
            "temporal_numeric_scale_and_rank_order_are_only_model_instructions"
        )
        is not True
        or copied.get("transfer_decision")
        != {
            "iana_only_successor": "stopped",
            "generic_visible_constraint_surface": "nonzero_transfer_reach",
            "current_production_equivalent_capability": "absent",
            "next_build_candidate": "visible_constraint_contract_for_shared_production_synthesis",
            "candidate_priority": [
                "temporal_year_range_and_date_format",
                "numeric_scale",
                "rank_top_k_and_explicit_order",
            ],
            "reason": "broad_visible_reach_with_zero_mechanical_coverage_in_current_forward_closure",
        }
        or copied.get(
            "task_rows_question_column_opaque_id_prediction_url_page_truth_evaluator_or_per_task_feature_persisted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "generic_visible_constraint_successor_build": valid,
            "new_external_population_protocol_or_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != exact220.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.40 visible constraint transfer audit drifted")
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
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "visible_transfer": value["visible_transfer"],
                "current_production_capability": value[
                    "current_production_capability"
                ],
                "transfer_decision": value["transfer_decision"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
