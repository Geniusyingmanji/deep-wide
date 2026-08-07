#!/usr/bin/env python3
"""Freeze the append-only V2.47.60 zero-effect external population.

V2.47.59 reproduced the V2.47.58 capacity failure before any search/model
effect: country cap 4 admitted at most 17 of the required 32 entities, while
the minimum feasible cap is 11.  This successor changes only the rank seed and
country cap.  It scans the entire immutable ROR v2.11 tree, keeps the same
freshness and active-education field-completeness rules, and grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
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
from scripts import design_v24758_zero_effect_population as base  # noqa: E402
from scripts import diagnose_v24759_v24758_population_capacity as diagnosis  # noqa: E402


DATE = "20260806"
PARENT = diagnosis.OUTPUT
OUTPUT = Path(f"results/v24760_zero_effect_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24760_zero_effect_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24760_zero_effect_external_contract.py")
FAILED_V24758_SURFACES = (base.OUTPUT, base.PRIVATE, base.CONTRACT)
SELECTED_COUNT = base.SELECTED_COUNT
TASK_SIZE = base.TASK_SIZE
COUNTRY_CAP = 11
EXPECTED_HISTORY = base.EXPECTED_HISTORY
RANK_SEED = "v24760"


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
        raise RuntimeError("V2.47.60 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.60 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return bool(
        value.get("role") == "v24759_v24758_population_capacity_diagnosis"
        and value.get("content_free_capacity", {}).get(
            "exact_v24758_failure_reproduced"
        )
        is True
        and value.get("content_free_capacity", {}).get("minimum_feasible_cap")
        == COUNTRY_CAP
        and value.get("authorization", {}).get("fresh_v24760_population_design")
        is True
        and value.get("authorization", {}).get("repaired_country_cap")
        == COUNTRY_CAP
        and value.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is False
        and value.get("authorization", {}).get("exact220") is False
        and _sealed(value, "diagnosis_payload_sha256")
    )


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
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if (
        isinstance(selected_count, bool)
        or selected_count <= 0
        or selected_count % TASK_SIZE
        or isinstance(country_cap, bool)
        or country_cap != COUNTRY_CAP
    ):
        raise ValueError("V2.47.60 selection envelope drifted")
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
        item for item in eligible if canonical_counts[item["canonical"]] == 1
    ]
    candidates.sort(key=lambda item: (item["rank"], item["record_id"]))
    selected: list[dict[str, Any]] = []
    countries: Counter[str] = Counter()
    for item in candidates:
        if countries[item["country_code"]] >= country_cap:
            continue
        selected.append(item)
        countries[item["country_code"]] += 1
        if len(selected) == selected_count:
            break
    if (
        len(selected) != selected_count
        or len({item["label"] for item in selected}) != selected_count
        or len({item["canonical"] for item in selected}) != selected_count
        or any(item["canonical"] in historical_canonical for item in selected)
        or max(countries.values(), default=0) > country_cap
    ):
        raise RuntimeError("V2.47.60 selected vector drifted")
    return selected, {
        "eligible_record_count": len(eligible),
        "canonical_unique_candidate_count": len(candidates),
        "candidate_country_count": len(
            {item["country_code"] for item in candidates}
        ),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
    }


def contract_source(records: Sequence[Mapping[str, Any]]) -> bytes:
    raw = base.contract_source(records)
    text = raw.decode("utf-8").replace("V2.47.58", "V2.47.60").replace(
        "v24758", "v24760"
    )
    if "v24758" in text.casefold() or "V2.47.58" in text:
        raise RuntimeError("V2.47.60 predecessor marker remained in contract")
    return text.encode("utf-8")


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


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.60 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.60 capacity parent drifted")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in FAILED_V24758_SURFACES
    ):
        raise RuntimeError("V2.47.60 V2.47.58 failed surfaces are not pristine")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.60 population surface exists")

    tree_raw = base.source._fetch(
        base.source.ROR_TREE_URL, limit=base.source.MAX_ROR_TREE_BYTES
    )
    entries = ranked_entries(tree_raw)
    records = base.fetch_records(entries)
    _history, historical_canonical = base.historical_entities()
    normalizer = base.source.ror_base.history.population._canonical_entity
    selected, metrics = select_records(
        records,
        historical_canonical=historical_canonical,
        canonical=normalizer,
    )
    now = int(time.time())
    private = {
        "artifact_version": 1,
        "role": "v24760_zero_effect_evaluator_only_population",
        "created_at_unix": now,
        "source_commit": base.source.ROR_COMMIT,
        "source_version": base.source.ROR_VERSION,
        "source_tree_sha1": base.source.ROR_TREE_SHA1,
        "selection_rule": (
            "immutable_ror_v211_active_education_exact_display_prior4680_disjoint_"
            "established_1000_2025_country_present_v24760_hash_rank_country_cap11"
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
    contract_raw = contract_source(selected)
    public = {
        "artifact_version": 1,
        "role": "v24760_zero_effect_population_design",
        "created_at_unix": now,
        "git_head": _git("rev-parse", "HEAD"),
        "parent_capacity_diagnosis_sha256": _sha256(ROOT / PARENT),
        "source": {
            "commit": base.source.ROR_COMMIT,
            "version": base.source.ROR_VERSION,
            "tree_sha1": base.source.ROR_TREE_SHA1,
            "tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
            "tree_record_count": len(entries),
            "fixed_rank_seed": RANK_SEED,
            "record_reads": len(records),
        },
        "freshness": {
            "historical_visible_entity_count": EXPECTED_HISTORY,
            "historical_canonical_entity_count": EXPECTED_HISTORY,
            "selected_entity_count": len(selected),
            "literal_overlap_with_history": 0,
            "canonical_overlap_with_history": 0,
            **metrics,
        },
        "task_shape": {
            "task_count": len(selected) // TASK_SIZE,
            "rows_per_task": TASK_SIZE,
            "total_rows": len(selected),
            "columns": ["Organization", "Founded", "Country"],
            "value_cells_per_task": TASK_SIZE * 2,
        },
        "capacity_repair": {
            "v24758_failed_country_cap": base.COUNTRY_CAP,
            "v24758_failed_cap_capacity": 17,
            "minimum_feasible_country_cap": COUNTRY_CAP,
            "selected_country_max": metrics["selected_country_max"],
            "eligibility_rule_changed": False,
            "rank_seed_changed_for_append_only_successor": True,
            "search_or_quality_outcome_used": False,
        },
        "selection_timing": {
            "rank_and_eligibility_frozen_before_search_or_model_outcome": True,
            "generic_web_search_or_endpoint_reachability_used_for_selection": False,
            "prior_response_query_url_page_prediction_or_score_read": False,
            "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        },
        "visible_identity_vector_sha256": payload_sha256(
            [item["label"] for item in selected]
        ),
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
        "visible_contract_sha256": hashlib.sha256(contract_raw).hexdigest(),
        "network": {
            "immutable_ror_tree_reads": 1,
            "immutable_ror_record_reads": len(records),
            "model_search_benchmark_or_evaluator_calls": 0,
        },
        "claim_scope": {
            "education_organization_schema_reachability_only": True,
            "geographically_balanced_quality_population": False,
            "deepwidebench_quality_or_score_measured": False,
            "entropy_or_credit_validated": False,
        },
        "authorization": {
            "inert_external_protocol_publication": True,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    public["design_payload_sha256"] = payload_sha256(public)
    public_raw = (
        json.dumps(public, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    created: list[Path] = []
    try:
        for relative, raw in (
            (PRIVATE, private_raw),
            (CONTRACT, contract_raw),
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
                "contract": str(CONTRACT),
                "country_cap": COUNTRY_CAP,
                "output": str(OUTPUT),
                "private": str(PRIVATE),
                "selected_count": len(selected),
                "selected_country_count": metrics["selected_country_count"],
                "selected_country_max": metrics["selected_country_max"],
                "task_count": len(selected) // TASK_SIZE,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
