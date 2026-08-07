#!/usr/bin/env python3
"""Record the public-source capacity checks preceding V2.47.83 selection.

Two read-only probes inspected the immutable ROR v2.11 Git snapshot before any
V2.47.83 population, protocol, endpoint, model, hosted-search, benchmark, or
evaluator surface existed.  This script does not repeat those reads.  It
publishes their aggregate counts, including the failed non-education rule and
the capacity curve that fixed the successor's all-type country cap at seven.

No candidate identity, private field value, URL, page, prediction, benchmark
label, truth, score, or credential is recorded.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24780_staged_fallback_execution_contract as contract  # noqa: E402
from scripts import audit_v24782_projection_funnel_build as parent  # noqa: E402
from scripts import design_v24727_dual_namespace_population as source  # noqa: E402


DATE = "20260807"
OUTPUT = Path(f"results/v24783_projection_population_capacity_precheck_v1_{DATE}.json")
PARENT = parent.AUDIT
HISTORICAL_ENTITY_COUNT = 4_784
TREE_RECORD_COUNT = 3_482
PROBE_COUNT = 2


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.83 capacity precheck expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.83 capacity precheck expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return bool(
        value.get("role") == "v24782_projection_funnel_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "fresh_disjoint_population_and_inert_protocol_design"
        )
        is True
        and value.get("authorization", {}).get(
            "fresh_external_activation_or_launch"
        )
        is False
        and value.get("authorization", {}).get(
            "same_population_forward_retry_resume_or_rerun"
        )
        is False
        and _sealed(value, "audit_payload_sha256")
    )


def build_record(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_valid():
        raise RuntimeError("V2.47.83 capacity precheck parent drifted")
    value = {
        "artifact_version": 1,
        "role": "v24783_projection_population_capacity_precheck",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head_at_publication": _git("rev-parse", "HEAD"),
        "parent_build_audit_sha256": contract.sha256(ROOT / PARENT),
        "source": {
            "commit": source.ROR_COMMIT,
            "version": source.ROR_VERSION,
            "tree_sha1": source.ROR_TREE_SHA1,
            "tree_record_count": TREE_RECORD_COUNT,
            "immutable_tree_read_count": PROBE_COUNT,
            "immutable_record_read_count": PROBE_COUNT * TREE_RECORD_COUNT,
            "direct_transport_receipt_available": False,
        },
        "shared_constraints": {
            "historical_visible_and_canonical_entity_count": HISTORICAL_ENTITY_COUNT,
            "status": "active",
            "exactly_one_safe_ror_display_name": True,
            "display_name_parentheses_allowed": False,
            "established_year_minimum": 1000,
            "established_year_maximum": 2025,
            "country_name_and_two_letter_code_required": True,
            "literal_and_canonical_history_overlap_allowed": False,
            "fixed_rank_seed": "v24783",
            "selected_count": 32,
        },
        "probe_results": {
            "noneducation_country_cap4": {
                "allowed_types": [
                    "archive",
                    "company",
                    "facility",
                    "funder",
                    "government",
                    "healthcare",
                    "nonprofit",
                    "other",
                ],
                "education_excluded": True,
                "eligible_record_count": 137,
                "canonical_unique_candidate_count": 135,
                "candidate_country_count": 5,
                "country_cap": 4,
                "maximum_selected_count": 20,
                "selected_country_count": 5,
                "selected_country_max": 4,
                "complete_32": False,
            },
            "all_types_capacity_curve": {
                "all_nonempty_ror_type_vectors_allowed": True,
                "eligible_record_count": 1_218,
                "canonical_unique_candidate_count": 1_216,
                "candidate_country_count": 5,
                "capacity_by_country_cap_1_to_7": {
                    "1": 5,
                    "2": 10,
                    "3": 15,
                    "4": 20,
                    "5": 24,
                    "6": 28,
                    "7": 32,
                },
                "minimum_feasible_country_cap": 7,
                "selected_country_count_at_minimum_cap": 5,
                "selected_country_max_at_minimum_cap": 7,
                "country_count_vector_at_minimum_cap_sorted": [4, 7, 7, 7, 7],
                "complete_32": True,
            },
        },
        "selection_decision": {
            "rule": "active_any_ror_type_exact_display_history_disjoint_established_country_hash_rank_country_cap7",
            "noneducation_only_rule_rejected_for_insufficient_capacity": True,
            "all_type_country_cap7_fixed_before_model_search_or_quality_outcome": True,
            "selected_identity_or_private_value_emitted": False,
            "population_surface_created_by_capacity_probes": False,
        },
        "source_policy": {
            "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_hosted_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "implement_exact_v24783_population_rule": True,
            "inert_protocol_design": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["record_payload_sha256"] = contract.payload_sha256(value)
    return validate_record(value)


def validate_record(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    source_value = copied.get("source", {})
    shared = copied.get("shared_constraints", {})
    probes = copied.get("probe_results", {})
    noneducation = probes.get("noneducation_country_cap4", {})
    curve = probes.get("all_types_capacity_curve", {})
    decision = copied.get("selection_decision", {})
    if (
        copied.get("role") != "v24783_projection_population_capacity_precheck"
        or source_value.get("commit") != source.ROR_COMMIT
        or source_value.get("version") != source.ROR_VERSION
        or source_value.get("tree_sha1") != source.ROR_TREE_SHA1
        or source_value.get("tree_record_count") != TREE_RECORD_COUNT
        or source_value.get("immutable_tree_read_count") != PROBE_COUNT
        or source_value.get("immutable_record_read_count")
        != PROBE_COUNT * TREE_RECORD_COUNT
        or source_value.get("direct_transport_receipt_available") is not False
        or shared.get("historical_visible_and_canonical_entity_count")
        != HISTORICAL_ENTITY_COUNT
        or shared.get("fixed_rank_seed") != "v24783"
        or shared.get("selected_count") != 32
        or noneducation.get("maximum_selected_count") != 20
        or noneducation.get("complete_32") is not False
        or curve.get("capacity_by_country_cap_1_to_7")
        != {"1": 5, "2": 10, "3": 15, "4": 20, "5": 24, "6": 28, "7": 32}
        or curve.get("minimum_feasible_country_cap") != 7
        or curve.get("country_count_vector_at_minimum_cap_sorted")
        != [4, 7, 7, 7, 7]
        or curve.get("complete_32") is not True
        or decision
        != {
            "rule": "active_any_ror_type_exact_display_history_disjoint_established_country_hash_rank_country_cap7",
            "noneducation_only_rule_rejected_for_insufficient_capacity": True,
            "all_type_country_cap7_fixed_before_model_search_or_quality_outcome": True,
            "selected_identity_or_private_value_emitted": False,
            "population_surface_created_by_capacity_probes": False,
        }
        or copied.get("source_policy")
        != {
            "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_hosted_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        }
        or copied.get("authorization")
        != {
            "implement_exact_v24783_population_rule": True,
            "inert_protocol_design": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "record_payload_sha256")
    ):
        raise RuntimeError("V2.47.83 capacity precheck record drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.83 capacity record requires clean pushed HEAD")
    record = build_record()
    publish_new(ROOT / OUTPUT, record)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "prior_tree_reads": record["source"]["immutable_tree_read_count"],
                "prior_record_reads": record["source"]["immutable_record_read_count"],
                "minimum_feasible_country_cap": record["probe_results"][
                    "all_types_capacity_curve"
                ]["minimum_feasible_country_cap"],
            },
            sort_keys=True,
        )
    )
