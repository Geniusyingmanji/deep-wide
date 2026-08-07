#!/usr/bin/env python3
"""Freeze the fresh V2.47.89 cross-tab mechanism population.

V2.47.87 failed its fixed country cap before publishing any population
surface.  V2.47.88 reproduced the failure with aggregate counts and proved
that cap 10 is the minimum feasible value.  This append-only successor changes
only the rank seed and country cap; eligibility, immutable ROR v2.11 source,
history exclusion, 8x4 task shape, visible prompt, physical separation, and
future row-major single-Unknown targeting contract are unchanged.

The script reads one immutable tree and 3,482 immutable records.  It never
opens prior private populations, V2.47.84 output/page/prediction, benchmark
mapping/labels/gold, score, reward, or evaluator data.  It calls no model,
hosted search, benchmark forward, quality surface, or evaluator and authorizes
only a later inert protocol design.
"""

from __future__ import annotations

import ast
import concurrent.futures
import copy
import hashlib
import json
import os
import pprint
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24787_cross_tab_population as failed  # noqa: E402
from scripts import diagnose_v24788_v24787_population_capacity as parent  # noqa: E402


DATE = "20260807"
PARENT = parent.OUTPUT
OUTPUT = Path(f"results/v24789_cross_tab_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24789_cross_tab_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24789_cross_tab_population_contract.py")

SELECTED_COUNT = failed.SELECTED_COUNT
TASK_SIZE = failed.TASK_SIZE
COUNTRY_CAP = 10
EXPECTED_HISTORY = failed.EXPECTED_HISTORY
EXPECTED_TREE_RECORDS = failed.EXPECTED_TREE_RECORDS
EXPECTED_ELIGIBLE = 1_186
EXPECTED_CANONICAL_UNIQUE = 1_184
EXPECTED_CANDIDATE_COUNTRIES = 4
RANK_SEED = "v24789"
FETCH_WORKERS = 24
PRIOR_TREE_READS = 5
PRIOR_RECORD_READS = 17_410
SELECTION_RULE = (
    "immutable_ror_v211_active_any_nonempty_type_exact_safe_display_"
    "prior4816_disjoint_established_1000_2025_country_present_"
    "v24789_hash_rank_country_cap10"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.89 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.89 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    try:
        parent.validate_diagnosis(value)
    except RuntimeError:
        return False
    capacity = value.get("content_free_capacity", {})
    return bool(
        value.get("role") == "v24788_v24787_population_capacity_diagnosis"
        and capacity.get("eligible_record_count") == EXPECTED_ELIGIBLE
        and capacity.get("canonical_unique_candidate_count")
        == EXPECTED_CANONICAL_UNIQUE
        and capacity.get("eligible_country_count") == EXPECTED_CANDIDATE_COUNTRIES
        and capacity.get("minimum_feasible_cap") == COUNTRY_CAP
        and value.get("authorization", {}).get(
            "append_only_fresh_population_successor_design"
        )
        is True
        and value.get("authorization", {}).get("repaired_country_cap")
        == COUNTRY_CAP
        and value.get("authorization", {}).get(
            "same_seed_retry_resume_or_supplement"
        )
        is False
        and value.get("authorization", {}).get(
            "trusted_child_integration_or_runner_build"
        )
        is False
        and value.get("authorization", {}).get("activation_or_external_launch")
        is False
        and _sealed(value, "diagnosis_payload_sha256")
    )


def historical_entities() -> tuple[set[str], set[str]]:
    visible, canonical = failed.historical_entities()
    if len(visible) != EXPECTED_HISTORY or len(canonical) != EXPECTED_HISTORY:
        raise RuntimeError("V2.47.89 historical identity population drifted")
    return visible, canonical


def _normalizer() -> Callable[[str], str]:
    return failed._normalizer()


def ranked_entries(tree_raw: bytes) -> list[tuple[str, str]]:
    entries = failed.base.source.parse_ror_tree(tree_raw)
    return sorted(
        entries,
        key=lambda item: (
            hashlib.sha256(
                f"{failed.base.source.ROR_COMMIT}:{RANK_SEED}:{item[0][:-5]}".encode()
            ).hexdigest(),
            item[0],
        ),
    )


def record_candidate(
    path: str,
    blob_sha1: str,
    raw: bytes,
    value: Mapping[str, Any],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
) -> dict[str, Any] | None:
    candidate = failed.record_candidate(
        path,
        blob_sha1,
        raw,
        value,
        historical_canonical=historical_canonical,
        canonical=canonical,
    )
    if candidate is None:
        return None
    copied = copy.deepcopy(candidate)
    copied["rank"] = hashlib.sha256(
        f"{failed.base.source.ROR_COMMIT}:{RANK_SEED}:{copied['record_id']}".encode()
    ).hexdigest()
    return copied


def select_records(
    records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
    selected_count: int = SELECTED_COUNT,
    country_cap: int = COUNTRY_CAP,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if (
        isinstance(selected_count, bool)
        or not isinstance(selected_count, int)
        or selected_count != SELECTED_COUNT
        or isinstance(country_cap, bool)
        or not isinstance(country_cap, int)
        or country_cap != COUNTRY_CAP
    ):
        raise ValueError("V2.47.89 selection envelope drifted")
    eligible = [
        candidate
        for path, blob, raw, value in records
        if (
            candidate := record_candidate(
                path,
                blob,
                raw,
                value,
                historical_canonical=historical_canonical,
                canonical=canonical,
            )
        )
        is not None
    ]
    canonical_counts = Counter(str(item["canonical"]) for item in eligible)
    candidates = [
        item for item in eligible if canonical_counts[str(item["canonical"])] == 1
    ]
    candidates.sort(key=lambda item: (item["rank"], item["record_id"]))
    selected: list[dict[str, Any]] = []
    countries: Counter[str] = Counter()
    for item in candidates:
        country = str(item["country_code"])
        if countries[country] >= country_cap:
            continue
        selected.append(item)
        countries[country] += 1
        if len(selected) == selected_count:
            break
    metrics = {
        "eligible_record_count": len(eligible),
        "canonical_unique_candidate_count": len(candidates),
        "candidate_country_count": len(
            {str(item["country_code"]) for item in candidates}
        ),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
        "selected_country_count_vector_sorted": sorted(countries.values()),
    }
    vector = metrics["selected_country_count_vector_sorted"]
    if (
        len(selected) != SELECTED_COUNT
        or len({str(item["label"]) for item in selected}) != SELECTED_COUNT
        or len({str(item["canonical"]) for item in selected}) != SELECTED_COUNT
        or any(str(item["canonical"]) in historical_canonical for item in selected)
        or metrics["eligible_record_count"] != EXPECTED_ELIGIBLE
        or metrics["canonical_unique_candidate_count"]
        != EXPECTED_CANONICAL_UNIQUE
        or metrics["candidate_country_count"] != EXPECTED_CANDIDATE_COUNTRIES
        or metrics["selected_country_count"] != len(vector)
        or len(vector) != EXPECTED_CANDIDATE_COUNTRIES
        or sum(vector) != SELECTED_COUNT
        or metrics["selected_country_max"] != max(vector)
        or max(vector) > COUNTRY_CAP
    ):
        raise RuntimeError("V2.47.89 selected vector drifted")
    return selected, metrics


def fetch_records(
    entries: Sequence[tuple[str, str]],
) -> list[tuple[str, str, bytes, Mapping[str, Any]]]:
    if (
        len(entries) != EXPECTED_TREE_RECORDS
        or len({path for path, _blob in entries}) != EXPECTED_TREE_RECORDS
    ):
        raise RuntimeError("V2.47.89 immutable tree vector drifted")

    def fetch_one(entry: tuple[str, str]):
        path, blob = entry
        raw = failed.base.source._fetch(
            failed.base.source.ROR_RAW_PREFIX + path,
            limit=failed.base.source.MAX_ROR_RECORD_BYTES,
        )
        return failed.base.source.validate_ror_blob(path, blob, raw)

    with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        return list(executor.map(fetch_one, entries))


def question(group: Sequence[str]) -> str:
    return failed.question(group)


def contract_source(records: Sequence[Mapping[str, Any]]) -> bytes:
    labels = [str(item["label"]) for item in records]
    if len(labels) != SELECTED_COUNT or len(set(labels)) != SELECTED_COUNT:
        raise RuntimeError("V2.47.89 visible identity vector drifted")
    questions = tuple(
        question(labels[offset : offset + TASK_SIZE])
        for offset in range(0, SELECTED_COUNT, TASK_SIZE)
    )
    body = f'''"""Visible-only task contract for the V2.47.89 cross-tab population."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24789_cross_tab_external_contract_v1"
QUESTIONS = {pprint.pformat(questions, width=100, sort_dicts=False)}


def task_vector() -> list[dict[str, str]]:
    return [
        {{
            "opaque_id": "task_" + hashlib.sha256(
                f"v24789:{{position}}:{{question}}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }}
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = ["POLICY_ID", "QUESTIONS", "copy_task_vector", "task_vector"]
'''
    ast.parse(body)
    return body.encode("utf-8")


def _publish(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def build_surfaces(
    *,
    tree_raw: bytes,
    entries: Sequence[tuple[str, str]],
    records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    selected: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    historical_visible: set[str],
    historical_canonical: set[str],
    now: int,
    git_head: str,
) -> tuple[dict[str, Any], bytes, bytes]:
    selected_labels = [str(item["label"]) for item in selected]
    selected_canonical = {_normalizer()(label) for label in selected_labels}
    vector = list(metrics.get("selected_country_count_vector_sorted", []))
    if (
        len(entries) != EXPECTED_TREE_RECORDS
        or len(records) != EXPECTED_TREE_RECORDS
        or len(selected_labels) != SELECTED_COUNT
        or len(set(selected_labels)) != SELECTED_COUNT
        or len(selected_canonical) != SELECTED_COUNT
        or len(historical_visible) != EXPECTED_HISTORY
        or len(historical_canonical) != EXPECTED_HISTORY
        or historical_visible.intersection(selected_labels)
        or historical_canonical.intersection(selected_canonical)
        or int(metrics.get("eligible_record_count", -1)) != EXPECTED_ELIGIBLE
        or int(metrics.get("canonical_unique_candidate_count", -1))
        != EXPECTED_CANONICAL_UNIQUE
        or int(metrics.get("candidate_country_count", -1))
        != EXPECTED_CANDIDATE_COUNTRIES
        or int(metrics.get("selected_country_count", -1)) != len(vector)
        or len(vector) != EXPECTED_CANDIDATE_COUNTRIES
        or sum(vector) != SELECTED_COUNT
        or int(metrics.get("selected_country_max", -1)) != max(vector)
        or max(vector, default=COUNTRY_CAP + 1) > COUNTRY_CAP
    ):
        raise RuntimeError("V2.47.89 production population surface drifted")

    private = {
        "artifact_version": 1,
        "role": "v24789_cross_tab_evaluator_only_population",
        "created_at_unix": int(now),
        "source_commit": failed.base.source.ROR_COMMIT,
        "source_version": failed.base.source.ROR_VERSION,
        "source_tree_sha1": failed.base.source.ROR_TREE_SHA1,
        "selection_rule": SELECTION_RULE,
        "records": [
            {
                key: copy.deepcopy(item[key])
                for key in (
                    "label",
                    "record_id",
                    "founded",
                    "country",
                    "country_code",
                    "ror_types",
                    "git_blob_sha1",
                    "record_bytes_sha256",
                )
            }
            for item in selected
        ],
        "forward_import_or_runtime_read_authorized": False,
        "quality_or_evaluator_read_before_prediction_freeze_authorized": False,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    private_raw = (
        json.dumps(private, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    visible_raw = contract_source(selected)
    public = {
        "artifact_version": 1,
        "role": "v24789_cross_tab_population_design",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parent_v24788_diagnosis_sha256": _sha256(ROOT / PARENT),
        "failed_predecessor": {
            "version": "v24787",
            "rank_seed": failed.RANK_SEED,
            "country_cap": failed.COUNTRY_CAP,
            "failed_cap_capacity": 28,
            "all_surfaces_pristine": True,
            "same_seed_retry_resume_or_supplement": False,
        },
        "source": {
            "commit": failed.base.source.ROR_COMMIT,
            "version": failed.base.source.ROR_VERSION,
            "tree_sha1": failed.base.source.ROR_TREE_SHA1,
            "tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
            "tree_record_count": len(entries),
            "fixed_rank_seed": RANK_SEED,
            "current_generation_tree_reads": 1,
            "current_generation_record_reads": len(records),
            "cumulative_preselection_tree_reads": PRIOR_TREE_READS + 1,
            "cumulative_preselection_record_reads": PRIOR_RECORD_READS
            + len(records),
        },
        "freshness": {
            "historical_visible_entity_count": len(historical_visible),
            "historical_canonical_entity_count": len(historical_canonical),
            "selected_entity_count": len(selected),
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
            "task_cluster_overlap_by_entity": 0,
        },
        "eligibility_and_selection": {
            "rule": SELECTION_RULE,
            "same_eligibility_as_failed_v24787": True,
            "only_rank_seed_and_country_cap_changed": True,
            "country_cap_is_v24788_minimum_feasible": True,
            "country_cap": COUNTRY_CAP,
            **copy.deepcopy(dict(metrics)),
            "selected_count": len(selected),
        },
        "task_shape": {
            "task_count": len(selected) // TASK_SIZE,
            "rows_per_task": TASK_SIZE,
            "total_rows": len(selected),
            "columns": ["Organization", "Founded", "Country"],
            "value_cells_per_task": TASK_SIZE * 2,
        },
        "future_target_selection_contract": {
            "implemented_by_population_design": False,
            "baseline_prediction_must_be_frozen_before_target_selection": True,
            "maximum_selected_baseline_unknown_target_per_task": 1,
            "selection_order": "canonical_table_row_major_value_cells",
            "zero_baseline_unknown_target_disposition": "no_target_mechanism_failure",
            "private_truth_provenance_quality_or_evaluator_used_for_selection": False,
            "target_selection_uses_only_current_visible_task_and_frozen_baseline": True,
            "two_independent_same_value_safety_gate_relaxed": False,
            "cross_task_or_cross_group_aggregation_used_as_joint": False,
        },
        "selection_timing": {
            "rule_cap_rank_and_eligibility_frozen_before_population_generation": True,
            "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_hosted_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "surface_separation": {
            "public_selected_identity_field_value_url_page_emitted": False,
            "evaluator_truth_and_provenance_physically_separated": True,
            "visible_forward_task_keys": ["opaque_id", "question"],
            "private_surface_forward_read_authorized": False,
        },
        "visible_identity_vector_sha256": payload_sha256(selected_labels),
        "private_record_vector_sha256": payload_sha256(
            [
                {
                    key: copy.deepcopy(item[key])
                    for key in (
                        "record_id",
                        "founded",
                        "country",
                        "country_code",
                        "ror_types",
                        "git_blob_sha1",
                        "record_bytes_sha256",
                    )
                }
                for item in selected
            ]
        ),
        "private_population_file_sha256": hashlib.sha256(private_raw).hexdigest(),
        "visible_contract_sha256": hashlib.sha256(visible_raw).hexdigest(),
        "network": {
            "current_immutable_ror_tree_reads": 1,
            "current_immutable_ror_record_reads": len(records),
            "cumulative_capacity_plus_generation_tree_reads": PRIOR_TREE_READS + 1,
            "cumulative_capacity_plus_generation_record_reads": PRIOR_RECORD_READS
            + len(records),
            "model_search_benchmark_forward_or_evaluator_calls": 0,
        },
        "claim_scope": {
            "benchmark_external_mechanism_population_only": True,
            "cross_tab_or_targeted_mechanism_effect_measured": False,
            "deepwidebench_quality_or_score_measured": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota_measured": False,
        },
        "authorization": {
            "append_only_inert_successor_protocol_design": True,
            "trusted_child_integration_or_runner_build": False,
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
    public["design_payload_sha256"] = payload_sha256(public)
    return public, private_raw, visible_raw


def validate_public(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    source = copied.get("source", {})
    freshness = copied.get("freshness", {})
    selection = copied.get("eligibility_and_selection", {})
    target = copied.get("future_target_selection_contract", {})
    timing = copied.get("selection_timing", {})
    separation = copied.get("surface_separation", {})
    network = copied.get("network", {})
    if (
        copied.get("role") != "v24789_cross_tab_population_design"
        or copied.get("failed_predecessor")
        != {
            "version": "v24787",
            "rank_seed": "v24787",
            "country_cap": 8,
            "failed_cap_capacity": 28,
            "all_surfaces_pristine": True,
            "same_seed_retry_resume_or_supplement": False,
        }
        or source.get("commit") != failed.base.source.ROR_COMMIT
        or source.get("version") != failed.base.source.ROR_VERSION
        or source.get("tree_sha1") != failed.base.source.ROR_TREE_SHA1
        or source.get("tree_record_count") != EXPECTED_TREE_RECORDS
        or source.get("fixed_rank_seed") != RANK_SEED
        or source.get("current_generation_tree_reads") != 1
        or source.get("current_generation_record_reads") != EXPECTED_TREE_RECORDS
        or source.get("cumulative_preselection_tree_reads") != 6
        or source.get("cumulative_preselection_record_reads") != 20_892
        or freshness
        != {
            "historical_visible_entity_count": EXPECTED_HISTORY,
            "historical_canonical_entity_count": EXPECTED_HISTORY,
            "selected_entity_count": SELECTED_COUNT,
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
            "task_cluster_overlap_by_entity": 0,
        }
        or selection.get("rule") != SELECTION_RULE
        or selection.get("same_eligibility_as_failed_v24787") is not True
        or selection.get("only_rank_seed_and_country_cap_changed") is not True
        or selection.get("country_cap_is_v24788_minimum_feasible") is not True
        or selection.get("country_cap") != COUNTRY_CAP
        or selection.get("eligible_record_count") != EXPECTED_ELIGIBLE
        or selection.get("canonical_unique_candidate_count")
        != EXPECTED_CANONICAL_UNIQUE
        or selection.get("candidate_country_count") != EXPECTED_CANDIDATE_COUNTRIES
        or not isinstance(selection.get("selected_country_count_vector_sorted"), list)
        or len(selection["selected_country_count_vector_sorted"])
        != EXPECTED_CANDIDATE_COUNTRIES
        or sum(selection["selected_country_count_vector_sorted"])
        != SELECTED_COUNT
        or max(selection["selected_country_count_vector_sorted"], default=COUNTRY_CAP + 1)
        > COUNTRY_CAP
        or selection.get("selected_country_count")
        != len(selection["selected_country_count_vector_sorted"])
        or selection.get("selected_country_max")
        != max(selection["selected_country_count_vector_sorted"])
        or selection.get("selected_count") != SELECTED_COUNT
        or copied.get("task_shape", {}).get("task_count") != 8
        or copied.get("task_shape", {}).get("rows_per_task") != 4
        or target
        != {
            "implemented_by_population_design": False,
            "baseline_prediction_must_be_frozen_before_target_selection": True,
            "maximum_selected_baseline_unknown_target_per_task": 1,
            "selection_order": "canonical_table_row_major_value_cells",
            "zero_baseline_unknown_target_disposition": "no_target_mechanism_failure",
            "private_truth_provenance_quality_or_evaluator_used_for_selection": False,
            "target_selection_uses_only_current_visible_task_and_frozen_baseline": True,
            "two_independent_same_value_safety_gate_relaxed": False,
            "cross_task_or_cross_group_aggregation_used_as_joint": False,
        }
        or timing
        != {
            "rule_cap_rank_and_eligibility_frozen_before_population_generation": True,
            "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_hosted_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        }
        or separation
        != {
            "public_selected_identity_field_value_url_page_emitted": False,
            "evaluator_truth_and_provenance_physically_separated": True,
            "visible_forward_task_keys": ["opaque_id", "question"],
            "private_surface_forward_read_authorized": False,
        }
        or network
        != {
            "current_immutable_ror_tree_reads": 1,
            "current_immutable_ror_record_reads": EXPECTED_TREE_RECORDS,
            "cumulative_capacity_plus_generation_tree_reads": 6,
            "cumulative_capacity_plus_generation_record_reads": 20_892,
            "model_search_benchmark_forward_or_evaluator_calls": 0,
        }
        or copied.get("authorization")
        != {
            "append_only_inert_successor_protocol_design": True,
            "trusted_child_integration_or_runner_build": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "design_payload_sha256")
    ):
        raise RuntimeError("V2.47.89 population design drifted")
    return copied


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.89 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.89 parent diagnosis drifted")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (failed.OUTPUT, failed.PRIVATE, failed.CONTRACT)
    ):
        raise RuntimeError("V2.47.87 failed surfaces are not pristine")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.89 population surface exists")

    tree_raw = failed.base.source._fetch(
        failed.base.source.ROR_TREE_URL,
        limit=failed.base.source.MAX_ROR_TREE_BYTES,
    )
    entries = ranked_entries(tree_raw)
    records = fetch_records(entries)
    historical_visible, historical_canonical = historical_entities()
    selected, metrics = select_records(
        records,
        historical_canonical=historical_canonical,
        canonical=_normalizer(),
    )
    public, private_raw, visible_raw = build_surfaces(
        tree_raw=tree_raw,
        entries=entries,
        records=records,
        selected=selected,
        metrics=metrics,
        historical_visible=historical_visible,
        historical_canonical=historical_canonical,
        now=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    validate_public(public)
    public_raw = (
        json.dumps(public, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    created: list[Path] = []
    try:
        for relative, raw in (
            (PRIVATE, private_raw),
            (CONTRACT, visible_raw),
            (OUTPUT, public_raw),
        ):
            path = ROOT / relative
            _publish(path, raw)
            created.append(path)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "selected_entities": len(selected),
                "historical_entities": len(historical_visible),
                "selected_country_count_vector_sorted": metrics[
                    "selected_country_count_vector_sorted"
                ],
                "current_tree_reads": 1,
                "current_record_reads": len(records),
                "cumulative_tree_reads": PRIOR_TREE_READS + 1,
                "cumulative_record_reads": PRIOR_RECORD_READS + len(records),
                "activation_authorized": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
