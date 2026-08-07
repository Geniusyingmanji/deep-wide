#!/usr/bin/env python3
"""Post-freeze reachability diagnosis for the V2.47.65 mechanism NO-GO.

This append-only diagnostic replays already-fetched pages through the frozen
V2.43.65 target-segment projector.  It performs no network, model, search,
fetch, benchmark, evaluator, or quality effect and never opens mapping, gold,
category, split, score, reward, or evaluator surfaces.  Runtime-private page
and prediction content is reduced to aggregate counts before publication.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24365_entity_segment_projection import (  # noqa: E402
    build_target_segment_catalog,
    validate_target_segment_catalog,
)
from deepwide_agent.v24743_generic_record_binding import (  # noqa: E402
    UNKNOWN,
    _baseline_matrix,
    _source_key,
)
from deepwide_agent.v24756_zero_effect_structured_integration import (  # noqa: E402
    validate_result as validate_runtime_result,
)
from deepwide_agent import v24765_zero_effect_execution_contract as contract  # noqa: E402
from scripts.correct_v24768_forward_audit_roundtrip import (  # noqa: E402
    OUTPUT as CORRECTION,
    validate_correction,
)


OUTPUT = Path(
    "results/v24769_v24765_zero_effect_reachability_diagnosis_v1_20260807.json"
)
ROLE = "v24769_v24765_zero_effect_reachability_diagnosis"
STATUS = "target_fair_acquisition_is_the_next_necessary_falsification"


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.69 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.69 expected JSON object")
    return value


def _unknown(value: object) -> bool:
    return " ".join(str(value or "").split()).casefold() in UNKNOWN


def _pages(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for raw in value["private_replay_pages"]:
        host = (urlsplit(str(raw["final_url"])).hostname or "").casefold()
        output.append(
            {
                "host": host,
                "content": str(raw["content"]),
                "fetch_integrity": raw["fetch_integrity"],
            }
        )
    return output


def _targets(
    columns: list[str], rows: list[list[str]], *, unknown_only: bool
) -> list[dict[str, str]]:
    return [
        {"row_key": row[0], "column": columns[index], "old_value": row[index]}
        for row in rows
        for index in range(1, len(columns))
        if not unknown_only or _unknown(row[index])
    ]


def _projection_counts(catalog: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_target_segment_catalog(catalog)
    base = validated["active_catalog"]["base_catalog"]
    quarantine = base["quarantined_candidate_groups"]
    return {
        "semantic_projection_count": validated["semantic_projection_count"],
        "distinct_target_value_projection_count": len(
            {
                (item["target_binding_sha256"], item["normalized_value_sha256"])
                for item in validated["projections"]
            }
        ),
        "candidate_target_value_group_count": base["candidate_groups_considered"],
        "insufficient_independence_group_count": int(
            quarantine.get("quarantine_insufficient_independence", 0)
        ),
        "eligible_support_set_count": base["eligible_support_set_count"],
        "projection_relation_kind_counts": dict(
            sorted(validated["projection_relation_kinds"].items())
        ),
        "projection_direction_counts": dict(
            sorted(validated["projection_binding_directions"].items())
        ),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    correction = validate_correction(_read(ROOT / CORRECTION))
    forward = contract.validate_forward_result(_read(ROOT / contract.FORWARD_RESULT))
    summary = contract.validate_run_summary(_read(ROOT / contract.RUN_SUMMARY))
    freeze = contract.validate_prediction_freeze(_read(ROOT / contract.PREDICTION_FREEZE))
    if (
        correction["forward_conclusion"]["mechanism_go"] is not False
        or correction["forward_conclusion"]["forward_health_go"] is not True
        or forward["terminal_arm_predictions"] != 16
        or summary["valid_task_results"] != 8
        or freeze["all_predictions_terminal_before_private_truth_or_quality_open"]
        is not True
        or correction["parents"]["forward_result_sha256"]
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or correction["parents"]["prediction_freeze_sha256"]
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or correction["parents"]["run_summary_sha256"]
        != contract.sha256(ROOT / contract.RUN_SUMMARY)
    ):
        raise RuntimeError("V2.47.69 frozen parent chain drifted")
    package = _read(ROOT / contract.PACKAGE_BUILD)
    manifest = package.get("source_manifest")
    if (
        package.get("role") != "v24766_zero_effect_package_build_audit"
        or package.get("audit_valid") is not True
        or package.get("findings") != []
        or not isinstance(manifest, Mapping)
        or manifest.get("src/deepwide_agent/v24269_task_union_discovery.py")
        != contract.sha256(ROOT / "src/deepwide_agent/v24269_task_union_discovery.py")
        or manifest.get(
            "src/deepwide_agent/v24756_zero_effect_structured_integration.py"
        )
        != contract.sha256(
            ROOT / "src/deepwide_agent/v24756_zero_effect_structured_integration.py"
        )
    ):
        raise RuntimeError("V2.47.69 frozen runtime manifest drifted")

    unknown_columns: Counter[str] = Counter()
    page_structure: Counter[str] = Counter()
    visible_identity_histogram: Counter[int] = Counter()
    unknown_identity_histogram: Counter[int] = Counter()
    all_projection_totals: Counter[str] = Counter()
    unknown_projection_totals: Counter[str] = Counter()
    all_relation_kinds: Counter[str] = Counter()
    unknown_relation_kinds: Counter[str] = Counter()
    all_directions: Counter[str] = Counter()
    unknown_directions: Counter[str] = Counter()
    unknown_entity_source_coverage: Counter[int] = Counter()
    independent_sources: set[str] = set()
    task_count = 0

    for ordinal in range(1, contract.SELECTED_COUNT + 1):
        path = ROOT / contract.TASK_ROOT / f"task_{ordinal:04d}" / contract.RESULT_NAME
        result = validate_runtime_result(_read(path))
        columns, rows = _baseline_matrix(result["predictions"]["baseline"])
        if columns != list(contract.EXPECTED_COLUMNS) or len(rows) != 4:
            raise RuntimeError("V2.47.69 frozen baseline shape drifted")
        pages = _pages(result)
        all_targets = _targets(columns, rows, unknown_only=False)
        unknown_targets = _targets(columns, rows, unknown_only=True)
        all_catalog = build_target_segment_catalog(all_targets, pages, [])
        unknown_catalog = build_target_segment_catalog(unknown_targets, pages, [])
        all_counts = _projection_counts(all_catalog)
        unknown_counts = _projection_counts(unknown_catalog)
        for name in (
            "semantic_projection_count",
            "distinct_target_value_projection_count",
            "candidate_target_value_group_count",
            "insufficient_independence_group_count",
            "eligible_support_set_count",
        ):
            all_projection_totals[name] += int(all_counts[name])
            unknown_projection_totals[name] += int(unknown_counts[name])
        all_relation_kinds.update(all_counts["projection_relation_kind_counts"])
        unknown_relation_kinds.update(unknown_counts["projection_relation_kind_counts"])
        all_directions.update(all_counts["projection_direction_counts"])
        unknown_directions.update(unknown_counts["projection_direction_counts"])

        for target in unknown_targets:
            unknown_columns[target["column"]] += 1
        visible_entities = [row[0] for row in rows]
        unknown_entities = {
            row[0]
            for row in rows
            if any(_unknown(row[index]) for index in range(1, len(columns)))
        }
        coverage: dict[str, set[str]] = {
            entity: set() for entity in unknown_entities
        }
        for page in pages:
            text = unicodedata.normalize("NFKC", page["content"])
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            visible_hits = [
                entity
                for entity in visible_entities
                if re.search(
                    rf"(?<![\w]){re.escape(entity)}(?![\w])", text, re.IGNORECASE
                )
            ]
            unknown_hits = [entity for entity in visible_hits if entity in unknown_entities]
            visible_identity_histogram[len(visible_hits)] += 1
            unknown_identity_histogram[len(unknown_hits)] += 1
            page_structure["page_count"] += 1
            page_structure["page_with_exact_visible_identity_count"] += int(
                bool(visible_hits)
            )
            page_structure["page_with_unknown_target_identity_count"] += int(
                bool(unknown_hits)
            )
            page_structure["page_with_identity_as_sole_line_count"] += int(
                any(
                    line.casefold() == entity.casefold()
                    for line in lines
                    for entity in visible_entities
                )
            )
            page_structure["page_with_identity_line_prefix_count"] += int(
                any(
                    line.casefold().startswith(entity.casefold())
                    for line in lines
                    for entity in visible_entities
                )
            )
            page_structure["page_with_four_digit_year_count"] += int(
                re.search(r"(?<!\d)(?:17|18|19|20|21)\d{2}(?!\d)", text)
                is not None
            )
            page_structure["page_with_founded_or_established_year_count"] += int(
                re.search(
                    r"(?:founded|established)[^\n.!?;]{0,80}"
                    r"(?<!\d)(?:17|18|19|20|21)\d{2}(?!\d)",
                    text,
                    re.IGNORECASE,
                )
                is not None
            )
            try:
                source = _source_key(page["host"])
            except ValueError:
                source = None
            if source is not None:
                independent_sources.add(source)
                for entity in unknown_hits:
                    coverage[entity].add(source)
        unknown_entity_source_coverage.update(len(values) for values in coverage.values())
        task_count += 1

    all_replay = {
        **{name: all_projection_totals[name] for name in all_projection_totals},
        "projection_relation_kind_counts": dict(sorted(all_relation_kinds.items())),
        "projection_direction_counts": dict(sorted(all_directions.items())),
    }
    unknown_replay = {
        **{name: unknown_projection_totals[name] for name in unknown_projection_totals},
        "projection_relation_kind_counts": dict(
            sorted(unknown_relation_kinds.items())
        ),
        "projection_direction_counts": dict(sorted(unknown_directions.items())),
    }
    expected_page_structure = {
        "page_count": 70,
        "page_with_exact_visible_identity_count": 53,
        "page_with_unknown_target_identity_count": 20,
        "page_with_identity_as_sole_line_count": 25,
        "page_with_identity_line_prefix_count": 38,
        "page_with_four_digit_year_count": 63,
        "page_with_founded_or_established_year_count": 25,
    }
    expected_all_replay = {
        "semantic_projection_count": 14,
        "distinct_target_value_projection_count": 13,
        "candidate_target_value_group_count": 43,
        "insufficient_independence_group_count": 43,
        "eligible_support_set_count": 0,
        "projection_relation_kind_counts": {"country": 5, "founding_year": 9},
        "projection_direction_counts": {"forward": 11, "leading": 3},
    }
    expected_unknown_replay = {
        "semantic_projection_count": 2,
        "distinct_target_value_projection_count": 2,
        "candidate_target_value_group_count": 4,
        "insufficient_independence_group_count": 4,
        "eligible_support_set_count": 0,
        "projection_relation_kind_counts": {"founding_year": 2},
        "projection_direction_counts": {"forward": 2},
    }
    if (
        task_count != 8
        or dict(unknown_columns) != {"Founded": 15, "Country": 4}
        or dict(page_structure) != expected_page_structure
        or all_replay != expected_all_replay
        or unknown_replay != expected_unknown_replay
        or dict(sorted(visible_identity_histogram.items())) != {0: 17, 1: 53}
        or dict(sorted(unknown_identity_histogram.items())) != {0: 50, 1: 20}
        or dict(sorted(unknown_entity_source_coverage.items()))
        != {0: 3, 1: 8, 2: 4}
        or len(independent_sources) != 29
    ):
        raise RuntimeError("V2.47.69 frozen replay aggregate drifted")

    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": STATUS,
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "roundtrip_correction_sha256": contract.sha256(ROOT / CORRECTION),
            "package_build_sha256": contract.sha256(ROOT / contract.PACKAGE_BUILD),
        },
        "frozen_forward": {
            "selected_tasks": 8,
            "terminal_arm_predictions": 16,
            "valid_task_results": 8,
            "forward_wall_seconds": summary["forward_wall_seconds"],
            "forward_health_go": True,
            "mechanism_go": False,
            "changed_task_count": 0,
            "changed_cell_count": 0,
        },
        "frozen_page_structure": {
            **expected_page_structure,
            "independent_registrable_source_count": len(independent_sources),
            "exact_visible_identity_count_per_page_histogram": {
                str(key): visible_identity_histogram[key]
                for key in sorted(visible_identity_histogram)
            },
            "unknown_target_identity_count_per_page_histogram": {
                str(key): unknown_identity_histogram[key]
                for key in sorted(unknown_identity_histogram)
            },
        },
        "baseline_unknown_surface": {
            "unknown_cell_count": sum(unknown_columns.values()),
            "unknown_cell_count_by_column": dict(unknown_columns),
            "unknown_entity_count": sum(unknown_entity_source_coverage.values()),
            "unknown_entity_exact_page_source_coverage_histogram": {
                str(key): unknown_entity_source_coverage[key]
                for key in sorted(unknown_entity_source_coverage)
            },
        },
        "strict_v24365_replay": {
            "all_value_cells_counterfactual": expected_all_replay,
            "actual_unknown_cells": expected_unknown_replay,
            "all_value_cell_replay_is_capacity_upper_bound_only": True,
            "all_value_cell_replay_is_valid_writeback_policy": False,
            "actual_unknown_cell_replay_is_policy_relevant": True,
            "candidate_target_value_group_is_eligible_support_set": False,
            "previous_informal_six_support_set_interpretation_valid": False,
        },
        "diagnosis": {
            "strict_markdown_or_entity_block_adapter_is_too_narrow_for_natural_pages": True,
            "semantic_parser_expansion_alone_reaches_two_unknown_projections": True,
            "semantic_parser_expansion_alone_reaches_any_two_source_support_set": False,
            "fetch_transport_or_wall_deadline_is_primary_bottleneck": False,
            "unknown_target_entities_have_uniform_fetch_coverage": False,
            "unknown_target_entities_with_zero_or_one_source_count": 11,
            "task_union_erases_query_local_provenance_before_first_ten_selection": True,
            "task_union_and_first_ten_diagnosis_is_source_manifest_and_code_audit": True,
            "first_ten_union_selection_guarantees_per_entity_coverage": False,
            "current_primary_bottleneck": "target_fair_retrieval_reachability_and_same_value_support_conversion_before_unchanged_two_source_gate",
            "target_fair_retrieval_alone_is_sufficient_for_safe_change": False,
            "v24765_same_population_rerun_would_be_valid": False,
        },
        "next_falsification": {
            "implementation": "visible_entity_specific_query_and_lead_scheduler",
            "fixed_visible_query_count": 4,
            "fixed_fetch_target_count": 10,
            "lead_alignment_signals": [
                "exact_visible_entity_in_title",
                "exact_visible_entity_in_normalized_url_host_or_path",
            ],
            "query_text_establishes_evidence": False,
            "round_robin_fetch_allocation_across_visible_entities": True,
            "fetched_page_text_remains_only_active_evidence": True,
            "strict_two_independent_source_support_gate_unchanged": True,
            "offline_frozen_page_replay_can_authorize_external_launch": False,
            "fresh_disjoint_eight_task_external_required": True,
            "external_mechanism_gate": "at_least_one_unknown_cell_with_two_independent_same_value_support_sources_and_safe_change",
            "paired_dev64_before_external_mechanism_go": False,
            "exact220_before_external_and_paired_dev64_go": False,
        },
        "source_policy": {
            "runtime_task_input_contract": ["opaque_id", "question"],
            "private_task_result_pages_and_predictions_opened_only_after_freeze": True,
            "private_content_persisted_in_public_diagnosis": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "same_forward_prediction_or_page_artifact_rewritten": False,
        },
        "claim_scope": {
            "mechanism_failure_localized": True,
            "semantic_parser_quality_measured": False,
            "future_round_robin_scheduler_quality_measured": False,
            "deepwidebench_quality_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "append_only_visible_entity_scheduler_implementation": True,
            "offline_frozen_page_mechanism_diagnosis": True,
            "same_population_forward_retry_resume_or_rerun": False,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    replay = copied.get("strict_v24365_replay", {})
    diagnosis = copied.get("diagnosis", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != STATUS
        or copied.get("frozen_forward", {}).get("mechanism_go") is not False
        or replay.get("all_value_cells_counterfactual", {}).get(
            "semantic_projection_count"
        )
        != 14
        or replay.get("all_value_cells_counterfactual", {}).get(
            "eligible_support_set_count"
        )
        != 0
        or replay.get("actual_unknown_cells", {}).get("semantic_projection_count")
        != 2
        or replay.get("actual_unknown_cells", {}).get("eligible_support_set_count")
        != 0
        or replay.get("candidate_target_value_group_is_eligible_support_set")
        is not False
        or replay.get("previous_informal_six_support_set_interpretation_valid")
        is not False
        or diagnosis.get("unknown_target_entities_with_zero_or_one_source_count")
        != 11
        or diagnosis.get("current_primary_bottleneck")
        != "target_fair_retrieval_reachability_and_same_value_support_conversion_before_unchanged_two_source_gate"
        or authorization
        != {
            "append_only_visible_entity_scheduler_implementation": True,
            "offline_frozen_page_mechanism_diagnosis": True,
            "same_population_forward_retry_resume_or_rerun": False,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.69 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "all_value_cell_projections": diagnosis["strict_v24365_replay"][
                    "all_value_cells_counterfactual"
                ]["semantic_projection_count"],
                "unknown_cell_projections": diagnosis["strict_v24365_replay"][
                    "actual_unknown_cells"
                ]["semantic_projection_count"],
                "unknown_cell_eligible_support_sets": diagnosis[
                    "strict_v24365_replay"
                ]["actual_unknown_cells"]["eligible_support_set_count"],
                "same_population_rerun_authorized": diagnosis["authorization"][
                    "same_population_forward_retry_resume_or_rerun"
                ],
            },
            sort_keys=True,
        )
    )
