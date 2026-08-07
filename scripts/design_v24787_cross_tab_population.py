#!/usr/bin/env python3
"""Freeze a fresh population for the post-V2.47.86 mechanism falsification.

The selector reconstructs all 4,816 consumed ROR identities exclusively from
tracked visible contracts, applies one fixed rule to the immutable ROR v2.11
snapshot, and publishes physically separated public, evaluator-only, and
visible-only surfaces.  It never opens any prior private population, V2.47.84
output/page/prediction, benchmark mapping/label/gold, score, reward, or
evaluator surface.

The future runtime constraint is frozen here but not implemented: after its
baseline prediction is frozen, each task may choose at most the first Unknown
value cell in row-major order.  No private truth may choose the target.  A task
with no baseline Unknown has no target and counts as a mechanism failure.  The
two-independent-source safety gate remains unchanged.

This script performs immutable public source reads needed to construct the
population.  It calls no model, hosted search, benchmark forward, quality
surface, or evaluator, and authorizes no integration, runner, launch, dev64,
220, entropy-credit, leaderboard, or SOTA claim.
"""

from __future__ import annotations

import ast
import concurrent.futures
import copy
import hashlib
import json
import os
import pprint
import re
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

from deepwide_agent import v24783_projection_funnel_contract as v24783_contract  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24786_projection_support_cross_tab_build as parent  # noqa: E402
from scripts import design_v24783_projection_funnel_population as base  # noqa: E402


DATE = "20260807"
PARENT = parent.OUTPUT
OUTPUT = Path(f"results/v24787_cross_tab_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24787_cross_tab_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24787_cross_tab_population_contract.py")

SELECTED_COUNT = 32
TASK_SIZE = 4
COUNTRY_CAP = 8
EXPECTED_PRE_V24783_HISTORY = 4_784
EXPECTED_V24783 = 32
EXPECTED_HISTORY = EXPECTED_PRE_V24783_HISTORY + EXPECTED_V24783
EXPECTED_TREE_RECORDS = 3_482
PRIOR_TREE_READS = 3
PRIOR_RECORD_READS = 10_446
RANK_SEED = "v24787"
FETCH_WORKERS = 24
SELECTION_RULE = (
    "immutable_ror_v211_active_any_nonempty_type_exact_safe_display_"
    "prior4816_disjoint_established_1000_2025_country_present_"
    "v24787_hash_rank_country_cap8"
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
        raise RuntimeError(f"V2.47.87 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.87 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    try:
        parent.validate_audit(value)
    except RuntimeError:
        return False
    return bool(
        value.get("role") == "v24786_projection_support_cross_tab_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("fresh_disjoint_population_design")
        is True
        and value.get("authorization", {}).get(
            "trusted_child_integration_or_runner_build"
        )
        is False
        and value.get("authorization", {}).get("activation_or_external_launch")
        is False
        and value.get("authorization", {}).get("exact220") is False
        and value.get("source_policy", {}).get(
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed"
        )
        is False
        and _sealed(value, "audit_payload_sha256")
    )


def _normalizer() -> Callable[[str], str]:
    return base._normalizer()


def _v24783_entities() -> set[str]:
    pattern = re.compile(r"<ENTITIES>\n(.*?)\n</ENTITIES>", flags=re.DOTALL)
    entities: list[str] = []
    for question in v24783_contract.QUESTIONS:
        match = pattern.search(str(question))
        if match is None:
            raise RuntimeError("V2.47.87 prior visible entity block drifted")
        lines = match.group(1).splitlines()
        if len(lines) != TASK_SIZE:
            raise RuntimeError("V2.47.87 prior task row count drifted")
        for index, line in enumerate(lines, 1):
            prefix = f"{index}. "
            if not line.startswith(prefix) or not line[len(prefix) :].strip():
                raise RuntimeError("V2.47.87 prior visible numbering drifted")
            entities.append(line[len(prefix) :].strip())
    if len(entities) != EXPECTED_V24783 or len(set(entities)) != EXPECTED_V24783:
        raise RuntimeError("V2.47.87 prior visible identity vector drifted")
    return set(entities)


def historical_entities() -> tuple[set[str], set[str]]:
    """Rebuild all consumed identities without opening private truth."""

    visible, canonical = base.historical_entities()
    successor = _v24783_entities()
    normalizer = _normalizer()
    successor_canonical = {normalizer(entity) for entity in successor}
    if (
        len(visible) != EXPECTED_PRE_V24783_HISTORY
        or len(canonical) != EXPECTED_PRE_V24783_HISTORY
        or len(successor_canonical) != EXPECTED_V24783
        or visible.intersection(successor)
        or canonical.intersection(successor_canonical)
    ):
        raise RuntimeError("V2.47.87 historical predecessor vector drifted")
    visible.update(successor)
    canonical.update(successor_canonical)
    if (
        len(visible) != EXPECTED_HISTORY
        or len(canonical) != EXPECTED_HISTORY
        or "" in canonical
    ):
        raise RuntimeError("V2.47.87 historical identity population drifted")
    return visible, canonical


def ranked_entries(tree_raw: bytes) -> list[tuple[str, str]]:
    entries = base.source.parse_ror_tree(tree_raw)
    return sorted(
        entries,
        key=lambda item: (
            hashlib.sha256(
                f"{base.source.ROR_COMMIT}:{RANK_SEED}:{item[0][:-5]}".encode()
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
    candidate = base.record_candidate(
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
        f"{base.source.ROR_COMMIT}:{RANK_SEED}:{copied['record_id']}".encode()
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
        or selected_count <= 0
        or selected_count % TASK_SIZE
        or isinstance(country_cap, bool)
        or not isinstance(country_cap, int)
        or country_cap != COUNTRY_CAP
    ):
        raise ValueError("V2.47.87 selection envelope drifted")
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
        country_code = str(item["country_code"])
        if countries[country_code] >= country_cap:
            continue
        selected.append(item)
        countries[country_code] += 1
        if len(selected) == selected_count:
            break
    if (
        len(selected) != selected_count
        or len({str(item["label"]) for item in selected}) != selected_count
        or len({str(item["canonical"]) for item in selected}) != selected_count
        or any(str(item["canonical"]) in historical_canonical for item in selected)
        or len(countries) < 4
        or max(countries.values(), default=0) > country_cap
    ):
        raise RuntimeError("V2.47.87 selected vector drifted")
    return selected, {
        "eligible_record_count": len(eligible),
        "canonical_unique_candidate_count": len(candidates),
        "candidate_country_count": len(
            {str(item["country_code"]) for item in candidates}
        ),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
        "selected_country_count_vector_sorted": sorted(countries.values()),
    }


def fetch_records(
    entries: Sequence[tuple[str, str]],
) -> list[tuple[str, str, bytes, Mapping[str, Any]]]:
    if (
        len(entries) != EXPECTED_TREE_RECORDS
        or len({path for path, _blob in entries}) != EXPECTED_TREE_RECORDS
    ):
        raise RuntimeError("V2.47.87 immutable tree vector drifted")

    def fetch_one(entry: tuple[str, str]):
        path, blob = entry
        raw = base.source._fetch(
            base.source.ROR_RAW_PREFIX + path,
            limit=base.source.MAX_ROR_RECORD_BYTES,
        )
        return base.source.validate_ror_blob(path, blob, raw)

    with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        return list(executor.map(fetch_one, entries))


def question(group: Sequence[str]) -> str:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(group, 1))
    return (
        "Use public web sources to return one Markdown table about these organizations:\n"
        f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
        "The column names are: Organization, Founded, Country. "
        "Use a four-digit founding year and the English country name. "
        "Use Unknown unless an exact value is supported by two independent public sources. "
        "Return one table only."
    )


def contract_source(records: Sequence[Mapping[str, Any]]) -> bytes:
    labels = [str(item["label"]) for item in records]
    if len(labels) != SELECTED_COUNT or len(set(labels)) != SELECTED_COUNT:
        raise RuntimeError("V2.47.87 visible identity vector drifted")
    questions = tuple(
        question(labels[offset : offset + TASK_SIZE])
        for offset in range(0, SELECTED_COUNT, TASK_SIZE)
    )
    body = f'''"""Visible-only task contract for the V2.47.87 cross-tab population."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24787_cross_tab_external_contract_v1"
QUESTIONS = {pprint.pformat(questions, width=100, sort_dicts=False)}


def task_vector() -> list[dict[str, str]]:
    return [
        {{
            "opaque_id": "task_" + hashlib.sha256(
                f"v24787:{{position}}:{{question}}".encode("utf-8")
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
    selected_country_vector = list(metrics.get("selected_country_count_vector_sorted", []))
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
        or int(metrics.get("eligible_record_count", -1)) < SELECTED_COUNT
        or int(metrics.get("canonical_unique_candidate_count", -1)) < SELECTED_COUNT
        or int(metrics.get("candidate_country_count", -1)) < 4
        or int(metrics.get("selected_country_count", -1)) < 4
        or int(metrics.get("selected_country_max", COUNTRY_CAP + 1)) > COUNTRY_CAP
        or sum(selected_country_vector) != SELECTED_COUNT
        or max(selected_country_vector, default=COUNTRY_CAP + 1) > COUNTRY_CAP
    ):
        raise RuntimeError("V2.47.87 production population surface drifted")

    private = {
        "artifact_version": 1,
        "role": "v24787_cross_tab_evaluator_only_population",
        "created_at_unix": int(now),
        "source_commit": base.source.ROR_COMMIT,
        "source_version": base.source.ROR_VERSION,
        "source_tree_sha1": base.source.ROR_TREE_SHA1,
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
        "role": "v24787_cross_tab_population_design",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parent_v24786_build_audit_sha256": _sha256(ROOT / PARENT),
        "source": {
            "commit": base.source.ROR_COMMIT,
            "version": base.source.ROR_VERSION,
            "tree_sha1": base.source.ROR_TREE_SHA1,
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
            "historical_breakdown": {
                "through_v24779": EXPECTED_PRE_V24783_HISTORY,
                "v24783": EXPECTED_V24783,
            },
            "selected_entity_count": len(selected),
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
            "task_cluster_overlap_by_entity": 0,
        },
        "eligibility_and_selection": {
            "rule": SELECTION_RULE,
            "all_nonempty_ror_type_vectors_allowed": True,
            "exactly_one_safe_ror_display_name": True,
            "display_name_parentheses_allowed": False,
            "established_year_minimum": base.EARLIEST_YEAR,
            "established_year_maximum": base.LATEST_YEAR,
            "country_name_and_two_letter_code_required": True,
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
    source_value = copied.get("source", {})
    freshness = copied.get("freshness", {})
    selection = copied.get("eligibility_and_selection", {})
    target = copied.get("future_target_selection_contract", {})
    timing = copied.get("selection_timing", {})
    separation = copied.get("surface_separation", {})
    network = copied.get("network", {})
    vector = selection.get("selected_country_count_vector_sorted")
    if (
        copied.get("role") != "v24787_cross_tab_population_design"
        or source_value.get("commit") != base.source.ROR_COMMIT
        or source_value.get("version") != base.source.ROR_VERSION
        or source_value.get("tree_sha1") != base.source.ROR_TREE_SHA1
        or source_value.get("tree_record_count") != EXPECTED_TREE_RECORDS
        or source_value.get("fixed_rank_seed") != RANK_SEED
        or source_value.get("current_generation_tree_reads") != 1
        or source_value.get("current_generation_record_reads")
        != EXPECTED_TREE_RECORDS
        or source_value.get("cumulative_preselection_tree_reads") != 4
        or source_value.get("cumulative_preselection_record_reads") != 13_928
        or freshness
        != {
            "historical_visible_entity_count": EXPECTED_HISTORY,
            "historical_canonical_entity_count": EXPECTED_HISTORY,
            "historical_breakdown": {
                "through_v24779": EXPECTED_PRE_V24783_HISTORY,
                "v24783": EXPECTED_V24783,
            },
            "selected_entity_count": SELECTED_COUNT,
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
            "task_cluster_overlap_by_entity": 0,
        }
        or selection.get("rule") != SELECTION_RULE
        or selection.get("country_cap") != COUNTRY_CAP
        or selection.get("selected_count") != SELECTED_COUNT
        or not isinstance(vector, list)
        or len(vector) < 4
        or sum(vector) != SELECTED_COUNT
        or max(vector, default=COUNTRY_CAP + 1) > COUNTRY_CAP
        or selection.get("selected_country_count") != len(vector)
        or selection.get("selected_country_max") != max(vector)
        or selection.get("eligible_record_count", 0) < SELECTED_COUNT
        or selection.get("canonical_unique_candidate_count", 0) < SELECTED_COUNT
        or selection.get("candidate_country_count", 0) < 4
        or copied.get("task_shape", {}).get("task_count")
        != SELECTED_COUNT // TASK_SIZE
        or copied.get("task_shape", {}).get("rows_per_task") != TASK_SIZE
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
            "cumulative_capacity_plus_generation_tree_reads": 4,
            "cumulative_capacity_plus_generation_record_reads": 13_928,
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
        raise RuntimeError("V2.47.87 population design drifted")
    return copied


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.87 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.87 parent authorization drifted")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.87 population surface exists")

    tree_raw = base.source._fetch(
        base.source.ROR_TREE_URL, limit=base.source.MAX_ROR_TREE_BYTES
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
