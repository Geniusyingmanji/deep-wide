#!/usr/bin/env python3
"""Freeze a fresh population for the V2.47.78 staged-fallback mechanism gate.

The selector rebuilds the 4,752 already-consumed visible ROR identities from
public visible-only contracts, applies a new fixed rank seed to the immutable
ROR v2.11 snapshot, and publishes physically separated public, evaluator-only,
and visible-only surfaces.  It does not read prior evaluator truth, pages,
queries, predictions, quality, or scores and does not call a model, hosted
search, benchmark forward, or evaluator.

V2.47.77 authorizes only this fresh population and the inert protocol design.
This script does not authorize preactivation, activation, launch, dev64,
exact-220, entropy credit, leaderboard, or SOTA claims.
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

from deepwide_agent import v24774_visible_entity_fair_contract as v24774_contract  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24774_visible_entity_fair_population as base  # noqa: E402
from scripts import diagnose_v24777_v24775_fetch_fallback as diagnosis  # noqa: E402


DATE = "20260807"
PARENT = diagnosis.OUTPUT
OUTPUT = Path(f"results/v24779_staged_fallback_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24779_staged_fallback_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24779_staged_fallback_contract.py")
RUNTIME = Path("src/deepwide_agent/v24778_staged_fetch_fallback_runtime.py")
RUNTIME_TEST = Path("tests/test_v24778_staged_fetch_fallback_runtime.py")

SELECTED_COUNT = 32
TASK_SIZE = 4
COUNTRY_CAP = 16
EXPECTED_PRE_V24774_HISTORY = 4_720
EXPECTED_V24774 = 32
EXPECTED_HISTORY = EXPECTED_PRE_V24774_HISTORY + EXPECTED_V24774
RANK_SEED = "v24779"
FETCH_WORKERS = 24


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
        raise RuntimeError(f"V2.47.79 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.79 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return bool(
        diagnosis.validate_diagnosis(value) == value
        and value.get("role")
        == "v24777_v24775_postfreeze_fetch_fallback_diagnosis"
        and value.get("status")
        == "staged_eight_plus_two_fallback_is_next_equal_budget_falsification"
        and value.get("record_scope_sensitivity", {})
        .get("strict_exact_record", {})
        .get("safe_two_source_same_value_pair_count")
        == 0
        and value.get("diagnosis", {}).get(
            "reserve_source_is_known_to_be_fetchable_or_same_value"
        )
        is False
        and value.get("authorization", {}).get(
            "append_only_equal_budget_staged_fetch_runtime_design"
        )
        is True
        and value.get("authorization", {}).get(
            "append_only_fresh_population_design"
        )
        is True
        and value.get("authorization", {}).get(
            "same_population_forward_retry_resume_or_rerun"
        )
        is False
        and value.get("authorization", {}).get(
            "fresh_external_activation_or_launch"
        )
        is False
        and value.get("authorization", {}).get("paired_dev64") is False
        and value.get("authorization", {}).get("exact220") is False
        and _sealed(value, "diagnosis_payload_sha256")
    )


def historical_entities() -> tuple[set[str], set[str]]:
    """Rebuild all consumed identities from visible contracts only."""

    visible, canonical = base.base.historical_entities()
    v24774 = {
        entity for group in v24774_contract.ENTITY_GROUPS for entity in group
    }
    normalizer = base.base.eligibility.source.ror_base.history.population._canonical_entity
    v24774_canonical = {normalizer(entity) for entity in v24774}
    if (
        len(visible) != EXPECTED_PRE_V24774_HISTORY
        or len(canonical) != EXPECTED_PRE_V24774_HISTORY
        or len(v24774) != EXPECTED_V24774
        or len(v24774_canonical) != EXPECTED_V24774
        or visible.intersection(v24774)
        or canonical.intersection(v24774_canonical)
    ):
        raise RuntimeError("V2.47.79 prior visible vectors drifted")
    visible.update(v24774)
    canonical.update(v24774_canonical)
    if (
        len(visible) != EXPECTED_HISTORY
        or len(canonical) != EXPECTED_HISTORY
        or "" in canonical
    ):
        raise RuntimeError("V2.47.79 historical identity population drifted")
    return visible, canonical


def ranked_entries(tree_raw: bytes) -> list[tuple[str, str]]:
    entries = base.base.eligibility.source.parse_ror_tree(tree_raw)
    return sorted(
        entries,
        key=lambda item: (
            hashlib.sha256(
                f"{base.base.eligibility.source.ROR_COMMIT}:{RANK_SEED}:{item[0][:-5]}".encode()
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
    candidate = base.base.record_candidate(
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
        f"{base.base.eligibility.source.ROR_COMMIT}:{RANK_SEED}:{copied['record_id']}".encode()
    ).hexdigest()
    return copied


def select_records(
    records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
    selected_count: int = SELECTED_COUNT,
    country_cap: int = COUNTRY_CAP,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if (
        isinstance(selected_count, bool)
        or not isinstance(selected_count, int)
        or selected_count <= 0
        or selected_count % TASK_SIZE
        or isinstance(country_cap, bool)
        or not isinstance(country_cap, int)
        or country_cap != COUNTRY_CAP
    ):
        raise ValueError("V2.47.79 selection envelope drifted")
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
    if (
        len(selected) != selected_count
        or len({str(item["label"]) for item in selected}) != selected_count
        or len({str(item["canonical"]) for item in selected}) != selected_count
        or any(str(item["canonical"]) in historical_canonical for item in selected)
        or max(countries.values(), default=0) > country_cap
    ):
        raise RuntimeError("V2.47.79 selected vector drifted")
    return selected, {
        "eligible_record_count": len(eligible),
        "canonical_unique_candidate_count": len(candidates),
        "candidate_country_count": len(
            {str(item["country_code"]) for item in candidates}
        ),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
    }


def fetch_records(
    entries: Sequence[tuple[str, str]],
) -> list[tuple[str, str, bytes, Mapping[str, Any]]]:
    def fetch_one(entry: tuple[str, str]):
        path, blob = entry
        raw = base.base.eligibility.source._fetch(
            base.base.eligibility.source.ROR_RAW_PREFIX + path,
            limit=base.base.eligibility.source.MAX_ROR_RECORD_BYTES,
        )
        return base.base.eligibility.source.validate_ror_blob(path, blob, raw)

    with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        return list(executor.map(fetch_one, entries))


def question(group: Sequence[str]) -> str:
    rows = "\n".join(
        f"{index}. {entity}" for index, entity in enumerate(group, 1)
    )
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
        raise RuntimeError("V2.47.79 contract identity vector drifted")
    groups = tuple(
        tuple(labels[offset : offset + TASK_SIZE])
        for offset in range(0, len(labels), TASK_SIZE)
    )
    questions = tuple(question(group) for group in groups)
    body = f'''"""Visible-only contract for the V2.47.79 staged-fallback mechanism gate."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24779_staged_fallback_external_contract_v1"
ENTITY_GROUPS = {pprint.pformat(groups, width=100, sort_dicts=False)}
QUESTIONS = {pprint.pformat(questions, width=100, sort_dicts=False)}


def task_vector() -> list[dict[str, str]]:
    return [
        {{
            "opaque_id": "task_" + hashlib.sha256(
                f"v24779:{{position}}:{{question}}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }}
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = ["ENTITY_GROUPS", "POLICY_ID", "QUESTIONS", "copy_task_vector", "task_vector"]
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
    metrics: Mapping[str, int],
    historical_visible: set[str],
    historical_canonical: set[str],
    now: int,
    git_head: str,
) -> tuple[dict[str, Any], bytes, bytes]:
    normalizer = base.base.eligibility.source.ror_base.history.population._canonical_entity
    selected_labels = [str(item["label"]) for item in selected]
    selected_canonical = {normalizer(label) for label in selected_labels}
    if (
        len(selected_labels) != SELECTED_COUNT
        or len(set(selected_labels)) != SELECTED_COUNT
        or len(selected_canonical) != SELECTED_COUNT
        or historical_visible.intersection(selected_labels)
        or historical_canonical.intersection(selected_canonical)
    ):
        raise RuntimeError("V2.47.79 freshness surface drifted")
    private = {
        "artifact_version": 1,
        "role": "v24779_staged_fallback_evaluator_only_population",
        "created_at_unix": int(now),
        "source_commit": base.base.eligibility.source.ROR_COMMIT,
        "source_version": base.base.eligibility.source.ROR_VERSION,
        "source_tree_sha1": base.base.eligibility.source.ROR_TREE_SHA1,
        "selection_rule": (
            "immutable_ror_v211_active_education_exact_display_prior4752_disjoint_"
            "established_1000_2025_country_present_v24779_hash_rank_country_cap16"
        ),
        "records": [
            {
                key: item[key]
                for key in (
                    "label",
                    "record_id",
                    "founded",
                    "country",
                    "country_code",
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
        "role": "v24779_staged_fallback_population_design",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parents": {
            "v24777_diagnosis_sha256": _sha256(ROOT / PARENT),
            "v24778_runtime_sha256": _sha256(ROOT / RUNTIME),
            "v24778_runtime_test_sha256": _sha256(ROOT / RUNTIME_TEST),
        },
        "source": {
            "commit": base.base.eligibility.source.ROR_COMMIT,
            "version": base.base.eligibility.source.ROR_VERSION,
            "tree_sha1": base.base.eligibility.source.ROR_TREE_SHA1,
            "tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
            "tree_record_count": len(entries),
            "fixed_rank_seed": RANK_SEED,
            "record_reads": len(records),
        },
        "freshness": {
            "historical_visible_entity_count": len(historical_visible),
            "historical_canonical_entity_count": len(historical_canonical),
            "historical_breakdown": {
                "through_v24760": EXPECTED_PRE_V24774_HISTORY,
                "v24774": EXPECTED_V24774,
            },
            "selected_entity_count": len(selected),
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
            **dict(metrics),
        },
        "task_shape": {
            "task_count": len(selected) // TASK_SIZE,
            "rows_per_task": TASK_SIZE,
            "total_rows": len(selected),
            "columns": ["Organization", "Founded", "Country"],
            "value_cells_per_task": TASK_SIZE * 2,
        },
        "selection_timing": {
            "rank_and_eligibility_frozen_before_search_or_model_outcome": True,
            "prior_search_query_url_page_prediction_or_quality_read": False,
            "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "v24774_private_population_opened_or_hashed": False,
        },
        "population_limitations": {
            "country_cap": COUNTRY_CAP,
            "selected_country_count": int(metrics["selected_country_count"]),
            "geographically_balanced_quality_population": False,
            "mechanism_falsification_population_only": True,
        },
        "visible_identity_vector_sha256": payload_sha256(selected_labels),
        "private_record_vector_sha256": payload_sha256(
            [
                {
                    key: item[key]
                    for key in (
                        "record_id",
                        "founded",
                        "country",
                        "country_code",
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
            "immutable_ror_tree_reads": 1,
            "immutable_ror_record_reads": len(records),
            "model_search_benchmark_forward_or_evaluator_calls": 0,
        },
        "claim_scope": {
            "benchmark_external_mechanism_population_only": True,
            "staged_fallback_effect_measured": False,
            "deepwidebench_quality_or_score_measured": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota_measured": False,
        },
        "authorization": {
            "inert_external_protocol_publication": True,
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
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    freshness = copied.get("freshness", {})
    timing = copied.get("selection_timing", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("role") != "v24779_staged_fallback_population_design"
        or freshness.get("historical_visible_entity_count") != EXPECTED_HISTORY
        or freshness.get("historical_canonical_entity_count") != EXPECTED_HISTORY
        or freshness.get("historical_breakdown")
        != {"through_v24760": EXPECTED_PRE_V24774_HISTORY, "v24774": EXPECTED_V24774}
        or freshness.get("selected_entity_count") != SELECTED_COUNT
        or freshness.get("literal_overlap_with_history") != 0
        or freshness.get("canonical_overlap_with_history") != 0
        or freshness.get("selected_country_max", COUNTRY_CAP + 1) > COUNTRY_CAP
        or copied.get("task_shape", {}).get("task_count") != SELECTED_COUNT // TASK_SIZE
        or copied.get("task_shape", {}).get("rows_per_task") != TASK_SIZE
        or copied.get("population_limitations", {}).get("country_cap") != COUNTRY_CAP
        or copied.get("population_limitations", {}).get(
            "geographically_balanced_quality_population"
        )
        is not False
        or timing
        != {
            "rank_and_eligibility_frozen_before_search_or_model_outcome": True,
            "prior_search_query_url_page_prediction_or_quality_read": False,
            "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "v24774_private_population_opened_or_hashed": False,
        }
        or copied.get("network", {}).get("model_search_benchmark_forward_or_evaluator_calls")
        != 0
        or authorization
        != {
            "inert_external_protocol_publication": True,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.79 population design drifted")
    return copied


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.79 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.79 diagnosis parent drifted")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.79 population surface exists")

    tree_raw = base.base.eligibility.source._fetch(
        base.base.eligibility.source.ROR_TREE_URL,
        limit=base.base.eligibility.source.MAX_ROR_TREE_BYTES,
    )
    entries = ranked_entries(tree_raw)
    records = fetch_records(entries)
    historical_visible, historical_canonical = historical_entities()
    normalizer = base.base.eligibility.source.ror_base.history.population._canonical_entity
    selected, metrics = select_records(
        records,
        historical_canonical=historical_canonical,
        canonical=normalizer,
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
                "literal_overlap": 0,
                "canonical_overlap": 0,
                "activation_authorized": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
