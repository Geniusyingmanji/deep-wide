#!/usr/bin/env python3
"""Aggregate-only replay of V2.52.89 on consumed external artifacts.

The replay compares two already-frozen representations of the same consumed
World Bank population: the shared Markdown pages used by V2.49.23 and their
official raw JSON responses.  It also audits whether the consumed PyPI
artifacts retain same-forward raw bytes that can be replayed by the binder.

No task question, identity, cell value, prediction, URL, gold, evaluator row,
or correctness signal is emitted.  This diagnostic performs no external
effect and cannot authorize a population freeze or launch.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24859_full_evidence_coverage_revision as evidence  # noqa: E402
from deepwide_agent import v24923_target_value_external_contract as worldbank  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from deepwide_agent import v25289_monotone_unknown_fill as binder  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import diagnose_v25292_monotone_unknown_fill_eligibility as parent  # noqa: E402


DATE = "20260813"
ROLE = "v25293_external_binder_reachability_diagnosis"
OUTPUT = Path(f"results/v25293_external_binder_reachability_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25293_external_binder_reachability.py")
TEST = Path("tests/test_diagnose_v25293_external_binder_reachability.py")

PARENT_DIAGNOSIS = parent.OUTPUT
WB_ROOT = Path("outputs/v24923_target_value_external_v1_20260808")
WB_PAGES = WB_ROOT / "snapshot/frozen_pages.json"
WB_SNAPSHOT_FREEZE = WB_ROOT / "snapshot/snapshot_freeze.json"
WB_PREDICTIONS = WB_ROOT / "frozen_predictions.jsonl"
WB_PREDICTION_FREEZE = WB_ROOT / "prediction_freeze.json"
WB_FORWARD_AUDIT = Path(
    "results/v24923_target_value_external_forward_audit_v1_20260808.json"
)
WB_RAW_RESPONSES = tuple(
    WB_ROOT / f"snapshot/target_responses/response_{index:02d}.bin"
    for index in range(1, 5)
)

PYPI_ROOT = Path("outputs/v25048_atomic_pypi_representation_v1_20260811")
PYPI_TASK_RESULTS = PYPI_ROOT / "frozen_task_results.jsonl"
PYPI_PUBLIC_SNAPSHOT = PYPI_ROOT / "postprediction_public_pypi_snapshot.jsonl"
PYPI_PREDICTION_FREEZE = PYPI_ROOT / "prediction_freeze.json"
PYPI_FORWARD_RESULT = Path(
    "results/v25048_atomic_pypi_forward_result_v1_20260811.json"
)
PYPI_FORWARD_AUDIT = Path(
    "results/v25048_atomic_pypi_forward_audit_v1_20260811.json"
)

FIXED_INPUTS = {
    PARENT_DIAGNOSIS: "ecb873042ccd701502f123435abde24890f0bdf3d44781fe3a8d9085ab2bdadb",
    WB_PAGES: "8b3126c3a4e4b2fd7c18830446985eff24dc97e299db18c138a075262c5138ce",
    WB_SNAPSHOT_FREEZE: "f3dc37d391f20b4dfaa68fccfc68c9a985ed429c0ff77ad42a3a7022d15fc0a3",
    WB_PREDICTIONS: "52f3d5c3d5ed97206827a9ef0e8e4d24403f53820d4a7ee10f2bf1e6af0db0d7",
    WB_PREDICTION_FREEZE: "2883dacf06958897ebac51845a857ca2991e72e7257d22ae8b8030a53508b279",
    WB_FORWARD_AUDIT: "2fecc2263bec533a8569bd028727df8f3c6d5893743b5ad454c5093fd0c73055",
    PYPI_TASK_RESULTS: "65d1f5f73c501e4f469162813685824e1415e76d9ae76e9559bc174e70a6eb66",
    PYPI_PUBLIC_SNAPSHOT: "458654a23cfec66e95612e1927583be4bd474f7d09c06cce3d5c0fd4f41115fc",
    PYPI_PREDICTION_FREEZE: "968979d9e97dffa68eac251038e516767f4552fd55d5643703a58726ce216681",
    PYPI_FORWARD_RESULT: "626ce8a79e4d8ef911cd5a5325b0bc90662e552be7c281619b6934b24a46f9c4",
    PYPI_FORWARD_AUDIT: "552b9747507dab5e3f45ba04089b3523ece3e4e68f2d26f6c504fdee2dde71b8",
    **{
        path: digest
        for path, digest in zip(
            WB_RAW_RESPONSES,
            (
                "e717d221f235269e77fdbad4e154d822b2ab1346edf0a88bfb04583d5bb4429b",
                "6e5cc7250a4206e9ddab0a6ba632eda50124649e6d26bf4dfc64507a7f760af0",
                "49e8efc1d1c06ea3c02118e1843ffe727e181094ace2f081f9d5e8940dd9368d",
                "e3719c8fa9a6d68eef3bf97a603232c21ee077c9b1159594824396db27e826f2",
            ),
            strict=True,
        )
    },
}

ARMS = ("parent_30k", "target_value_30k")
EXPECTED_WORLD_BANK = {
    "rendered_markdown": {
        "parent_30k": {
            "task_count": 12,
            "parse_valid_tasks": 12,
            "unknown_value_cells": 176,
            "cells_with_any_bound_value": 128,
            "cells_with_unique_nonconflicting_support": 128,
            "cells_with_multiple_bound_values": 0,
            "tasks_with_unique_nonconflicting_support": 9,
        },
        "target_value_30k": {
            "task_count": 12,
            "parse_valid_tasks": 12,
            "unknown_value_cells": 164,
            "cells_with_any_bound_value": 136,
            "cells_with_unique_nonconflicting_support": 136,
            "cells_with_multiple_bound_values": 0,
            "tasks_with_unique_nonconflicting_support": 10,
        },
    },
    "raw_official_json": {
        "parent_30k": {
            "task_count": 12,
            "parse_valid_tasks": 12,
            "unknown_value_cells": 176,
            "cells_with_any_bound_value": 0,
            "cells_with_unique_nonconflicting_support": 0,
            "cells_with_multiple_bound_values": 0,
            "tasks_with_unique_nonconflicting_support": 0,
        },
        "target_value_30k": {
            "task_count": 12,
            "parse_valid_tasks": 12,
            "unknown_value_cells": 164,
            "cells_with_any_bound_value": 0,
            "cells_with_unique_nonconflicting_support": 0,
            "cells_with_multiple_bound_values": 0,
            "tasks_with_unique_nonconflicting_support": 0,
        },
    },
}

EXPECTED_PYPI = {
    "task_result_rows": 20,
    "public_snapshot_rows": 20,
    "same_forward_raw_response_bytes_persisted": False,
    "raw_response_content_replayable": False,
    "binder_reachability_reconstructable": False,
    "record_projection_persisted_after_prediction_freeze": True,
    "record_projection_is_not_same_forward_raw_page_bytes": True,
    "domain_intrinsically_rejected": False,
}

CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "source_and_test_tracked",
        "fixed_inputs_exact",
        "parent_diagnosis_valid_and_design_only",
        "worldbank_snapshot_and_prediction_freezes_valid",
        "worldbank_forward_audit_valid_and_label_blind",
        "worldbank_rendered_markdown_reachability_exact_nonzero",
        "worldbank_raw_json_reachability_exact_zero",
        "representation_difference_not_interpreted_as_quality_effect",
        "pypi_same_forward_raw_bytes_absent",
        "pypi_absence_not_interpreted_as_domain_failure",
        "aggregate_output_contains_no_task_or_cell_content",
        "no_external_effect_performed",
    }
)


def _read_object(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.93 expected a repository JSON object")
    return value


def _read_jsonl(relative: Path, expected: int) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    with base._ordinary(relative).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("V2.52.93 expected JSONL objects")
            values.append(value)
    if len(values) != expected:
        raise RuntimeError("V2.52.93 JSONL denominator drifted")
    return values


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    signature = unsigned.pop(field, None)
    return signature == seal.payload_sha256(unsigned)


def _fixed_inputs() -> dict[str, str]:
    observed = {str(path): base.sha256(path) for path in FIXED_INPUTS}
    expected = {str(path): digest for path, digest in FIXED_INPUTS.items()}
    if observed != expected:
        raise RuntimeError("V2.52.93 fixed input hash drifted")
    return observed


def _parent_barrier() -> dict[str, Any]:
    value = parent.validate_diagnosis(_read_object(PARENT_DIAGNOSIS))
    authorization = value["authorization"]
    if (
        value["diagnosis_valid"] is not True
        or value["findings"] != []
        or authorization[
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design"
        ]
        is not True
        or authorization["external_activation_or_launch"] is not False
        or authorization["postfreeze_evaluator"] is not False
    ):
        raise RuntimeError("V2.52.93 parent diagnosis barrier failed")
    return value


def _worldbank_barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bundle = _read_object(WB_PAGES)
    snapshot = _read_object(WB_SNAPSHOT_FREEZE)
    prediction_freeze = _read_object(WB_PREDICTION_FREEZE)
    audit = _read_object(WB_FORWARD_AUDIT)
    rows = _read_jsonl(WB_PREDICTIONS, 12)
    unsigned_bundle = dict(bundle)
    bundle_signature = unsigned_bundle.pop("bundle_payload_sha256", None)
    if (
        bundle_signature != seal.payload_sha256(unsigned_bundle)
        or not _sealed(snapshot, "freeze_payload_sha256")
        or not _sealed(prediction_freeze, "freeze_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
        or bundle.get("role") != "v24923_frozen_shared_public_pages"
        or bundle.get("same_page_vector_for_both_arms") is not True
        or bundle.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or not isinstance(bundle.get("pages"), list)
        or len(bundle["pages"]) != 4
        or snapshot.get("official_responses_fetched_once_before_arm_branch")
        is not True
        or snapshot.get("same_frozen_pages_required_for_both_arms") is not True
        or snapshot.get("gold_mapping_or_evaluator_created_or_opened") is not False
        or prediction_freeze.get("all_predictions_terminal_before_evaluator_open")
        is not True
        or prediction_freeze.get("selected_tasks") != 12
        or prediction_freeze.get("predictions_sha256") != FIXED_INPUTS[WB_PREDICTIONS]
        or audit.get("role") != "v24923_target_value_external_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("private_gold_mapping_or_evaluator_opened_or_hashed")
        is not False
        or audit.get("network_model_fetch_or_evaluator_called_by_audit") is not False
        or any(
            set(row)
            != {
                "opaque_id",
                "prediction_sha256",
                "predictions",
                "retry_resume_skip_or_selective_rerun",
            }
            or set(row.get("predictions") or {}) != set(ARMS)
            or row.get("retry_resume_skip_or_selective_rerun") is not False
            for row in rows
        )
    ):
        raise RuntimeError("V2.52.93 World Bank authority drifted")
    return bundle, rows


def _integral_pages(
    pages: Sequence[Mapping[str, Any]], *, contents: Sequence[str] | None = None
) -> tuple[evidence.EvidencePage, ...]:
    if contents is not None and len(contents) != len(pages):
        raise RuntimeError("V2.52.93 page content vector drifted")
    values = []
    for index, page in enumerate(pages, 1):
        values.append(
            {
                "evidence_id": f"E{index:04d}",
                "url": page.get("url"),
                "raw_content": (
                    contents[index - 1]
                    if contents is not None
                    else page.get("content")
                ),
                # The old page schema predates this field.  Integrity is
                # restored only after the exact snapshot/audit barrier above.
                "fetch_integrity": True,
            }
        )
    return evidence.prepare_evidence_pages(values)


def _arm_reachability(
    rows: Sequence[Mapping[str, Any]],
    pages: Sequence[evidence.EvidencePage],
    *,
    arm: str,
) -> dict[str, int]:
    counts = Counter()
    for item in rows:
        prediction = (item.get("predictions") or {}).get(arm)
        try:
            columns, table_rows = evidence._matrix(prediction)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("V2.52.93 frozen prediction table drifted") from exc
        counts["parse_valid_tasks"] += 1
        supported_on_task = 0
        for row in table_rows:
            for index, column in enumerate(columns[1:], 1):
                if not evidence._is_unknown(row[index]):
                    continue
                counts["unknown_value_cells"] += 1
                values: set[str] = set()
                for page in pages:
                    values.update(binder._bound_values(page, row[0], column))
                if values:
                    counts["cells_with_any_bound_value"] += 1
                if len(values) > 1:
                    counts["cells_with_multiple_bound_values"] += 1
                admissible = []
                for value in values:
                    support, conflict = binder._support_and_conflict(
                        pages,
                        row_key=row[0],
                        column=column,
                        value=value,
                    )
                    if (
                        support >= binder.MINIMUM_SUPPORTING_PAGES
                        and conflict <= binder.MAXIMUM_CONFLICTING_BOUND_VALUES
                    ):
                        admissible.append(value)
                if len(admissible) == 1:
                    counts["cells_with_unique_nonconflicting_support"] += 1
                    supported_on_task += 1
        if supported_on_task:
            counts["tasks_with_unique_nonconflicting_support"] += 1
    return {
        "task_count": len(rows),
        "parse_valid_tasks": counts["parse_valid_tasks"],
        "unknown_value_cells": counts["unknown_value_cells"],
        "cells_with_any_bound_value": counts["cells_with_any_bound_value"],
        "cells_with_unique_nonconflicting_support": counts[
            "cells_with_unique_nonconflicting_support"
        ],
        "cells_with_multiple_bound_values": counts[
            "cells_with_multiple_bound_values"
        ],
        "tasks_with_unique_nonconflicting_support": counts[
            "tasks_with_unique_nonconflicting_support"
        ],
    }


def _worldbank_reachability() -> dict[str, Any]:
    bundle, rows = _worldbank_barrier()
    pages = bundle["pages"]
    rendered = _integral_pages(pages)
    raw_contents = [
        base._ordinary(path).read_bytes().decode("utf-8")
        for path in WB_RAW_RESPONSES
    ]
    raw = _integral_pages(pages, contents=raw_contents)
    representations = {
        "rendered_markdown": {
            arm: _arm_reachability(rows, rendered, arm=arm) for arm in ARMS
        },
        "raw_official_json": {
            arm: _arm_reachability(rows, raw, arm=arm) for arm in ARMS
        },
    }
    if representations != EXPECTED_WORLD_BANK:
        raise RuntimeError("V2.52.93 World Bank aggregate drifted")
    return {
        "consumed_population_task_count": 12,
        "shared_page_count": 4,
        "representations": representations,
        "actual_third_slot_proposal_replayed": False,
        "actual_supported_fill_observed": False,
        "actual_candidate_prediction_change_observed": False,
        "quality_or_correctness_read": False,
        "interpretation": (
            "proposal_independent_binder_support_surface_only_not_a_treatment_effect"
        ),
    }


def _pypi_persistence() -> dict[str, Any]:
    tasks = _read_jsonl(PYPI_TASK_RESULTS, 20)
    snapshot = _read_jsonl(PYPI_PUBLIC_SNAPSHOT, 20)
    prediction_freeze = _read_object(PYPI_PREDICTION_FREEZE)
    forward = _read_object(PYPI_FORWARD_RESULT)
    audit = _read_object(PYPI_FORWARD_AUDIT)
    forbidden_raw_keys = {
        "raw_response",
        "raw_response_text",
        "raw_response_bytes_base64",
        "page_content",
        "same_forward_public_pages",
    }
    if (
        prediction_freeze.get("role") != "v25048_atomic_pypi_prediction_freeze"
        or prediction_freeze.get("task_count") != 20
        or prediction_freeze.get(
            "public_snapshot_present_before_prediction_freeze"
        )
        is not False
        or forward.get("role") != "v25048_atomic_pypi_forward_result"
        or (forward.get("aggregate") or {}).get("terminal_tasks") != 20
        or audit.get("role")
        != "v25048_atomic_pypi_representation_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not all(not forbidden_raw_keys.intersection(row) for row in tasks)
        or not all(not forbidden_raw_keys.intersection(row) for row in snapshot)
        or not all(
            row.get("published_after_prediction_freeze") is True
            and "record" in row
            and "raw_response_sha256" in row
            and "raw_response_bytes" in row
            for row in snapshot
        )
    ):
        raise RuntimeError("V2.52.93 PyPI persistence authority drifted")
    return copy.deepcopy(EXPECTED_PYPI)


def _decision() -> dict[str, Any]:
    return {
        "next_design_domain": "world_bank_official_json_to_frozen_markdown",
        "selection_basis": (
            "mechanical_row_column_value_reachability_and_independent_official_gold_capability"
        ),
        "historical_correctness_or_per_task_score_used_for_domain_selection": False,
        "worldbank_consumed_population_reusable": False,
        "worldbank_fresh_disjoint_population_required": True,
        "worldbank_renderer_is_part_of_the_treatment_protocol": True,
        "raw_json_is_not_natively_parseable_by_v25289": True,
        "pypi_not_selected_from_existing_artifacts_because_same_forward_raw_bytes_are_absent": True,
        "pypi_intrinsically_rejected": False,
        "actual_supported_fill_or_prediction_change_established": False,
        "quality_gain_or_deepwidebench_transfer_established": False,
        "next_step": "fresh_disjoint_worldbank_shared_prefix_protocol_design_only",
    }


def build_diagnosis(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    fixed = _fixed_inputs()
    parent_value = _parent_barrier()
    worldbank_observed = _worldbank_reachability()
    pypi_observed = _pypi_persistence()
    source_hashes = {str(path): base.sha256(path) for path in (SOURCE, TEST)}
    untracked = sorted(
        str(path)
        for path in (SOURCE, TEST)
        if tracked and not base._tracked(path)
    )
    checks = {
        "git_clean_head_equals_target_main": clean and head == target,
        "source_and_test_tracked": not untracked,
        "fixed_inputs_exact": fixed
        == {str(path): digest for path, digest in FIXED_INPUTS.items()},
        "parent_diagnosis_valid_and_design_only": (
            parent_value["diagnosis_valid"] is True
            and parent_value["findings"] == []
        ),
        "worldbank_snapshot_and_prediction_freezes_valid": True,
        "worldbank_forward_audit_valid_and_label_blind": True,
        "worldbank_rendered_markdown_reachability_exact_nonzero": (
            worldbank_observed["representations"]["rendered_markdown"]
            == EXPECTED_WORLD_BANK["rendered_markdown"]
            and worldbank_observed["representations"]["rendered_markdown"]
            ["parent_30k"]["cells_with_unique_nonconflicting_support"]
            > 0
        ),
        "worldbank_raw_json_reachability_exact_zero": (
            worldbank_observed["representations"]["raw_official_json"]
            == EXPECTED_WORLD_BANK["raw_official_json"]
        ),
        "representation_difference_not_interpreted_as_quality_effect": (
            worldbank_observed["actual_third_slot_proposal_replayed"] is False
            and worldbank_observed["actual_supported_fill_observed"] is False
            and worldbank_observed[
                "actual_candidate_prediction_change_observed"
            ]
            is False
        ),
        "pypi_same_forward_raw_bytes_absent": (
            pypi_observed["same_forward_raw_response_bytes_persisted"] is False
            and pypi_observed["binder_reachability_reconstructable"] is False
        ),
        "pypi_absence_not_interpreted_as_domain_failure": (
            pypi_observed["domain_intrinsically_rejected"] is False
        ),
        "aggregate_output_contains_no_task_or_cell_content": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "source_hashes": source_hashes,
        "fixed_inputs": fixed,
        "worldbank_observed": worldbank_observed,
        "pypi_observed": pypi_observed,
        "decision": _decision(),
        "content_policy": {
            "consumed_prediction_tables_opened_only_for_unknown_and_binder_reachability": True,
            "consumed_public_page_bytes_opened": True,
            "pypi_persistence_schema_opened_but_record_values_not_used": True,
            "task_question_identity_url_page_cell_value_prediction_or_content_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_metric_score_reward_or_correctness_opened": False,
            "historical_per_task_correctness_used_for_selection_or_routing": False,
            "aggregate_only_output": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read_for_runtime_routing": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_worldbank_shared_prefix_protocol_design": not findings,
            "population_selection_or_freeze": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "candidate_quality_avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = seal.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("diagnosis_payload_sha256", None)
    git = copied.get("git") or {}
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    authorization = copied.get("authorization") or {}
    policy = copied.get("content_policy") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    expected_source_hashes = {
        str(path): base.sha256(path) for path in (SOURCE, TEST)
    }
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "source_hashes",
            "fixed_inputs",
            "worldbank_observed",
            "pypi_observed",
            "decision",
            "content_policy",
            "checks",
            "findings",
            "diagnosis_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read_for_runtime_routing",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("equal") is not (git.get("head") == git.get("target_main"))
        or not isinstance(git.get("clean"), bool)
        or copied.get("source_hashes") != expected_source_hashes
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in FIXED_INPUTS.items()}
        or copied.get("worldbank_observed")
        != {
            "consumed_population_task_count": 12,
            "shared_page_count": 4,
            "representations": EXPECTED_WORLD_BANK,
            "actual_third_slot_proposal_replayed": False,
            "actual_supported_fill_observed": False,
            "actual_candidate_prediction_change_observed": False,
            "quality_or_correctness_read": False,
            "interpretation": "proposal_independent_binder_support_surface_only_not_a_treatment_effect",
        }
        or copied.get("pypi_observed") != EXPECTED_PYPI
        or copied.get("decision") != _decision()
        or policy
        != {
            "consumed_prediction_tables_opened_only_for_unknown_and_binder_reachability": True,
            "consumed_public_page_bytes_opened": True,
            "pypi_persistence_schema_opened_but_record_values_not_used": True,
            "task_question_identity_url_page_cell_value_prediction_or_content_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_metric_score_reward_or_correctness_opened": False,
            "historical_per_task_correctness_used_for_selection_or_routing": False,
            "aggregate_only_output": True,
        }
        or set(checks) != CHECK_NAMES
        or any(not isinstance(passed, bool) for passed in checks.values())
        or findings != expected_findings
        or copied.get("diagnosis_valid") is not (not expected_findings)
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read_for_runtime_routing"
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
            "fresh_disjoint_worldbank_shared_prefix_protocol_design": not expected_findings,
            "population_selection_or_freeze": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "candidate_quality_avg_at_4_leaderboard_or_sota": False,
        }
        or signature != seal.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.93 diagnosis drifted")
    encoded = json.dumps(copied, ensure_ascii=False, sort_keys=True)
    if parent.OPAQUE.search(encoded) is not None or "https://" in encoded:
        raise ValueError("V2.52.93 diagnosis leaked task or page content")
    return copied


def main() -> None:
    value = build_diagnosis()
    base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "next_design_domain": value["decision"]["next_design_domain"],
                "worldbank_parent_supported_tasks": value["worldbank_observed"]
                ["representations"]["rendered_markdown"]["parent_30k"]
                ["tasks_with_unique_nonconflicting_support"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
