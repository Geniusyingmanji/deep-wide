#!/usr/bin/env python3
"""Freeze the fresh V2.47.83 projection-funnel mechanism population.

The selector reconstructs the 4,784 consumed ROR identities exclusively from
visible contracts, applies the rule and country cap fixed by the public
V2.47.83 capacity precheck, and publishes three physically separated surfaces:

* a content-free public population receipt;
* evaluator-only truth and immutable-record provenance; and
* a visible-only task contract whose forward payload is ``opaque_id`` plus
  ``question``.

It never opens a prior private population or V2.47.80 output and never calls a
model, hosted search, benchmark forward, evaluator, or quality surface.  The
result authorizes only an inert V2.47.84 protocol design, not activation,
launch, dev64, exact-220, entropy credit, leaderboard, or SOTA claims.
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

from deepwide_agent import v24779_staged_fallback_contract as v24779_contract  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24727_dual_namespace_population as source  # noqa: E402
from scripts import design_v24779_staged_fallback_population as history  # noqa: E402
from scripts import record_v24783_projection_population_capacity_precheck as precheck  # noqa: E402


DATE = "20260807"
PARENT = precheck.OUTPUT
OUTPUT = Path(f"results/v24783_projection_funnel_population_design_v1_{DATE}.json")
PRIVATE = Path(
    f"evaluation/v24783_projection_funnel_population_private_v1_{DATE}.json"
)
CONTRACT = Path("src/deepwide_agent/v24783_projection_funnel_contract.py")

SELECTED_COUNT = 32
TASK_SIZE = 4
COUNTRY_CAP = 7
EXPECTED_PRE_V24779_HISTORY = 4_752
EXPECTED_V24779 = 32
EXPECTED_HISTORY = EXPECTED_PRE_V24779_HISTORY + EXPECTED_V24779
EXPECTED_TREE_RECORDS = 3_482
EXPECTED_ELIGIBLE = 1_218
EXPECTED_CANONICAL_UNIQUE = 1_216
EXPECTED_CANDIDATE_COUNTRIES = 5
EXPECTED_SELECTED_COUNTRY_VECTOR = [4, 7, 7, 7, 7]
PRIOR_TREE_READS = 2
PRIOR_RECORD_READS = 6_964
RANK_SEED = "v24783"
FETCH_WORKERS = 24
EARLIEST_YEAR = 1000
LATEST_YEAR = 2025
SELECTION_RULE = (
    "immutable_ror_v211_active_any_nonempty_type_exact_safe_display_"
    "prior4784_disjoint_established_1000_2025_country_present_"
    "v24783_hash_rank_country_cap7"
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
        raise RuntimeError(f"V2.47.83 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.83 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    shared = value.get("shared_constraints", {})
    curve = value.get("probe_results", {}).get("all_types_capacity_curve", {})
    return bool(
        precheck.validate_record(value) == value
        and value.get("role")
        == "v24783_projection_population_capacity_precheck"
        and shared.get("historical_visible_and_canonical_entity_count")
        == EXPECTED_HISTORY
        and shared.get("fixed_rank_seed") == RANK_SEED
        and shared.get("selected_count") == SELECTED_COUNT
        and curve.get("eligible_record_count") == EXPECTED_ELIGIBLE
        and curve.get("canonical_unique_candidate_count")
        == EXPECTED_CANONICAL_UNIQUE
        and curve.get("candidate_country_count") == EXPECTED_CANDIDATE_COUNTRIES
        and curve.get("minimum_feasible_country_cap") == COUNTRY_CAP
        and curve.get("country_count_vector_at_minimum_cap_sorted")
        == EXPECTED_SELECTED_COUNTRY_VECTOR
        and value.get("authorization", {}).get(
            "implement_exact_v24783_population_rule"
        )
        is True
        and value.get("authorization", {}).get("activation_or_external_launch")
        is False
        and value.get("authorization", {}).get("exact220") is False
        and _sealed(value, "record_payload_sha256")
    )


def _normalizer() -> Callable[[str], str]:
    return history.base.base.eligibility.source.ror_base.history.population._canonical_entity


def historical_entities() -> tuple[set[str], set[str]]:
    """Rebuild all consumed identities without opening prior private truth."""

    visible, canonical = history.historical_entities()
    successor = {
        entity for group in v24779_contract.ENTITY_GROUPS for entity in group
    }
    normalizer = _normalizer()
    successor_canonical = {normalizer(entity) for entity in successor}
    if (
        len(visible) != EXPECTED_PRE_V24779_HISTORY
        or len(canonical) != EXPECTED_PRE_V24779_HISTORY
        or len(successor) != EXPECTED_V24779
        or len(successor_canonical) != EXPECTED_V24779
        or visible.intersection(successor)
        or canonical.intersection(successor_canonical)
    ):
        raise RuntimeError("V2.47.83 prior visible identity vector drifted")
    visible.update(successor)
    canonical.update(successor_canonical)
    if (
        len(visible) != EXPECTED_HISTORY
        or len(canonical) != EXPECTED_HISTORY
        or "" in canonical
    ):
        raise RuntimeError("V2.47.83 historical identity population drifted")
    return visible, canonical


def ranked_entries(tree_raw: bytes) -> list[tuple[str, str]]:
    entries = source.parse_ror_tree(tree_raw)
    return sorted(
        entries,
        key=lambda item: (
            hashlib.sha256(
                f"{source.ROR_COMMIT}:{RANK_SEED}:{item[0][:-5]}".encode()
            ).hexdigest(),
            item[0],
        ),
    )


def _safe_visible(value: object, *, maximum: int = 160) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if (
        not text
        or len(text) > maximum
        or any(character in text for character in "|\r\n\"\\")
    ):
        return None
    return text


def record_candidate(
    path: str,
    blob_sha1: str,
    raw: bytes,
    value: Mapping[str, Any],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
) -> dict[str, Any] | None:
    record_id = path[:-5] if path.endswith(".json") else ""
    names = value.get("names")
    display_values = (
        [
            item.get("value")
            for item in names
            if isinstance(item, Mapping)
            and isinstance(item.get("types"), list)
            and "ror_display" in item["types"]
        ]
        if isinstance(names, list)
        else []
    )
    label = _safe_visible(display_values[0]) if len(display_values) == 1 else None
    locations = value.get("locations")
    details = (
        locations[0].get("geonames_details")
        if isinstance(locations, list)
        and locations
        and isinstance(locations[0], Mapping)
        else None
    )
    country = (
        _safe_visible(details.get("country_name"), maximum=80)
        if isinstance(details, Mapping)
        else None
    )
    country_code = (
        str(details.get("country_code", "")).upper()
        if isinstance(details, Mapping)
        else ""
    )
    established = value.get("established")
    types = value.get("types")
    normalized_types = (
        sorted(
            {
                item.strip().casefold()
                for item in types
                if isinstance(item, str) and item.strip()
            }
        )
        if isinstance(types, list)
        else []
    )
    folded = canonical(label) if label is not None else ""
    if (
        not record_id
        or value.get("status") != "active"
        or value.get("id") != f"https://ror.org/{record_id}"
        or not normalized_types
        or label is None
        or any(character in label for character in "()")
        or not folded
        or folded in historical_canonical
        or isinstance(established, bool)
        or not isinstance(established, int)
        or not EARLIEST_YEAR <= established <= LATEST_YEAR
        or country is None
        or re.fullmatch(r"[A-Z]{2}", country_code) is None
    ):
        return None
    computed_blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    if computed_blob != blob_sha1:
        raise RuntimeError("V2.47.83 immutable ROR blob drifted")
    return {
        "rank": hashlib.sha256(
            f"{source.ROR_COMMIT}:{RANK_SEED}:{record_id}".encode()
        ).hexdigest(),
        "label": label,
        "canonical": folded,
        "record_id": record_id,
        "founded": str(established),
        "country": country,
        "country_code": country_code,
        "ror_types": normalized_types,
        "git_blob_sha1": blob_sha1,
        "record_bytes_sha256": hashlib.sha256(raw).hexdigest(),
    }


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
        raise ValueError("V2.47.83 selection envelope drifted")
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
        or max(countries.values(), default=0) > country_cap
    ):
        raise RuntimeError("V2.47.83 selected vector drifted")
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
        raise RuntimeError("V2.47.83 immutable tree vector drifted")

    def fetch_one(entry: tuple[str, str]):
        path, blob = entry
        raw = source._fetch(
            source.ROR_RAW_PREFIX + path,
            limit=source.MAX_ROR_RECORD_BYTES,
        )
        return source.validate_ror_blob(path, blob, raw)

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
        raise RuntimeError("V2.47.83 visible identity vector drifted")
    questions = tuple(
        question(labels[offset : offset + TASK_SIZE])
        for offset in range(0, SELECTED_COUNT, TASK_SIZE)
    )
    body = f'''"""Visible-only task contract for the V2.47.83 projection-funnel population."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24783_projection_funnel_external_contract_v1"
QUESTIONS = {pprint.pformat(questions, width=100, sort_dicts=False)}


def task_vector() -> list[dict[str, str]]:
    return [
        {{
            "opaque_id": "task_" + hashlib.sha256(
                f"v24783:{{position}}:{{question}}".encode("utf-8")
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
    expected_metrics = {
        "eligible_record_count": EXPECTED_ELIGIBLE,
        "canonical_unique_candidate_count": EXPECTED_CANONICAL_UNIQUE,
        "candidate_country_count": EXPECTED_CANDIDATE_COUNTRIES,
        "selected_country_count": len(EXPECTED_SELECTED_COUNTRY_VECTOR),
        "selected_country_max": COUNTRY_CAP,
        "selected_country_count_vector_sorted": EXPECTED_SELECTED_COUNTRY_VECTOR,
    }
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
        or dict(metrics) != expected_metrics
    ):
        raise RuntimeError("V2.47.83 production population surface drifted")
    private = {
        "artifact_version": 1,
        "role": "v24783_projection_funnel_evaluator_only_population",
        "created_at_unix": int(now),
        "source_commit": source.ROR_COMMIT,
        "source_version": source.ROR_VERSION,
        "source_tree_sha1": source.ROR_TREE_SHA1,
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
        "role": "v24783_projection_funnel_population_design",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parent_capacity_precheck_sha256": _sha256(ROOT / PARENT),
        "source": {
            "commit": source.ROR_COMMIT,
            "version": source.ROR_VERSION,
            "tree_sha1": source.ROR_TREE_SHA1,
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
                "through_v24774": EXPECTED_PRE_V24779_HISTORY,
                "v24779": EXPECTED_V24779,
            },
            "selected_entity_count": len(selected),
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
        },
        "eligibility_and_selection": {
            "rule": SELECTION_RULE,
            "all_nonempty_ror_type_vectors_allowed": True,
            "exactly_one_safe_ror_display_name": True,
            "display_name_parentheses_allowed": False,
            "established_year_minimum": EARLIEST_YEAR,
            "established_year_maximum": LATEST_YEAR,
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
        "selection_timing": {
            "rule_cap_rank_and_eligibility_frozen_before_population_generation": True,
            "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
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
            "projection_funnel_effect_measured": False,
            "deepwidebench_quality_or_score_measured": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota_measured": False,
        },
        "authorization": {
            "inert_v24784_protocol_design": True,
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
    timing = copied.get("selection_timing", {})
    separation = copied.get("surface_separation", {})
    network = copied.get("network", {})
    if (
        copied.get("role") != "v24783_projection_funnel_population_design"
        or source_value.get("commit") != source.ROR_COMMIT
        or source_value.get("version") != source.ROR_VERSION
        or source_value.get("tree_sha1") != source.ROR_TREE_SHA1
        or source_value.get("tree_record_count") != EXPECTED_TREE_RECORDS
        or source_value.get("fixed_rank_seed") != RANK_SEED
        or source_value.get("current_generation_tree_reads") != 1
        or source_value.get("current_generation_record_reads")
        != EXPECTED_TREE_RECORDS
        or source_value.get("cumulative_preselection_tree_reads") != 3
        or source_value.get("cumulative_preselection_record_reads") != 10_446
        or freshness
        != {
            "historical_visible_entity_count": EXPECTED_HISTORY,
            "historical_canonical_entity_count": EXPECTED_HISTORY,
            "historical_breakdown": {
                "through_v24774": EXPECTED_PRE_V24779_HISTORY,
                "v24779": EXPECTED_V24779,
            },
            "selected_entity_count": SELECTED_COUNT,
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
        }
        or selection.get("rule") != SELECTION_RULE
        or selection.get("eligible_record_count") != EXPECTED_ELIGIBLE
        or selection.get("canonical_unique_candidate_count")
        != EXPECTED_CANONICAL_UNIQUE
        or selection.get("candidate_country_count")
        != EXPECTED_CANDIDATE_COUNTRIES
        or selection.get("country_cap") != COUNTRY_CAP
        or selection.get("selected_country_count_vector_sorted")
        != EXPECTED_SELECTED_COUNTRY_VECTOR
        or selection.get("selected_count") != SELECTED_COUNT
        or copied.get("task_shape", {}).get("task_count")
        != SELECTED_COUNT // TASK_SIZE
        or copied.get("task_shape", {}).get("rows_per_task") != TASK_SIZE
        or timing
        != {
            "rule_cap_rank_and_eligibility_frozen_before_population_generation": True,
            "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
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
            "cumulative_capacity_plus_generation_tree_reads": 3,
            "cumulative_capacity_plus_generation_record_reads": 10_446,
            "model_search_benchmark_forward_or_evaluator_calls": 0,
        }
        or copied.get("authorization")
        != {
            "inert_v24784_protocol_design": True,
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
        raise RuntimeError("V2.47.83 population design drifted")
    return copied


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.83 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.83 capacity precheck parent drifted")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.83 population surface exists")

    tree_raw = source._fetch(source.ROR_TREE_URL, limit=source.MAX_ROR_TREE_BYTES)
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
