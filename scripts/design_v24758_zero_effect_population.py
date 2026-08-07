#!/usr/bin/env python3
"""Freeze a fresh population for the V2.47.56 zero-effect integration gate.

Selection is deterministic over one immutable ROR snapshot.  It excludes all
previously consumed ROR identity surfaces, uses no search/model/benchmark
outcome, and publishes three physically separated surfaces:

* a content-free public population-design receipt;
* evaluator-only record provenance and field values; and
* a visible-only ``{opaque_id, question}`` contract containing entity names.

This program grants protocol-publication authority only.  It cannot activate,
launch, evaluate, resume, retry, or selectively rerun an experiment.
"""

from __future__ import annotations

import ast
import concurrent.futures
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

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24727_dual_namespace_population as source  # noqa: E402
from scripts import design_v24750_host_local_population as history  # noqa: E402


DATE = "20260806"
PARENT = Path(f"results/v24757_zero_effect_integration_build_audit_v1_{DATE}.json")
OUTPUT = Path(f"results/v24758_zero_effect_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24758_zero_effect_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24758_zero_effect_external_contract.py")

SELECTED_COUNT = 32
TASK_SIZE = 4
COUNTRY_CAP = 4
EXPECTED_HISTORY = 4_680
FETCH_WORKERS = 24
FETCH_BATCH = 128
MAX_FETCH_PREFIX = 3_482
RANK_SEED = "v24758"
EARLIEST_YEAR = 1000
LATEST_YEAR = 2025


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
        raise RuntimeError("V2.47.58 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.58 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return bool(
        value.get("role") == "v24757_zero_effect_integration_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("tests", {}).get("observed") == 29
        and value.get("authorization", {}).get(
            "fresh_external_population_and_protocol_design"
        )
        is True
        and value.get("authorization", {}).get("external_launch") is False
        and value.get("authorization", {}).get("exact220") is False
        and _sealed(value, "audit_payload_sha256")
    )


def historical_entities() -> tuple[set[str], set[str]]:
    visible, canonical = history.prior_ror_entities()
    if (
        len(visible) != EXPECTED_HISTORY
        or len(canonical) != EXPECTED_HISTORY
        or "" in canonical
    ):
        raise RuntimeError("V2.47.58 historical ROR population drifted")
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
    text = " ".join(str(value or "").split())
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
    locations = value.get("locations")
    displays = (
        [
            _safe_visible(item.get("value"))
            for item in names
            if isinstance(item, Mapping) and "ror_display" in item.get("types", [])
        ]
        if isinstance(names, list)
        else []
    )
    displays = [item for item in displays if item is not None]
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
    label = displays[0] if len(displays) == 1 else None
    folded = canonical(label) if label is not None else ""
    if (
        not record_id
        or value.get("status") != "active"
        or value.get("id") != f"https://ror.org/{record_id}"
        or not isinstance(types, list)
        or "education" not in {str(item).casefold() for item in types}
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
        raise RuntimeError("V2.47.58 immutable ROR blob drifted")
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
        "git_blob_sha1": blob_sha1,
        "record_bytes_sha256": hashlib.sha256(raw).hexdigest(),
    }


def select_records(
    records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
    selected_count: int = SELECTED_COUNT,
    task_size: int = TASK_SIZE,
    country_cap: int = COUNTRY_CAP,
    require_complete: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if (
        isinstance(selected_count, bool)
        or selected_count <= 0
        or isinstance(task_size, bool)
        or task_size <= 0
        or selected_count % task_size
        or isinstance(country_cap, bool)
        or country_cap <= 0
    ):
        raise ValueError("V2.47.58 selection envelope drifted")
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
    canonical_counts = Counter(item["canonical"] for item in eligible)
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
        (require_complete and len(selected) != selected_count)
        or len({item["label"] for item in selected}) != len(selected)
        or len({item["canonical"] for item in selected}) != len(selected)
        or any(item["canonical"] in historical_canonical for item in selected)
        or max(countries.values(), default=0) > country_cap
    ):
        raise RuntimeError("V2.47.58 selected ROR vector drifted")
    return selected, {
        "eligible_record_count": len(eligible),
        "canonical_unique_candidate_count": len(candidates),
        "candidate_country_count": len(
            {item["country_code"] for item in candidates}
        ),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
    }


def fetch_records(
    entries: Sequence[tuple[str, str]],
) -> list[tuple[str, str, bytes, Mapping[str, Any]]]:
    def fetch_one(entry: tuple[str, str]):
        path, blob = entry
        raw = source._fetch(source.ROR_RAW_PREFIX + path, limit=source.MAX_ROR_RECORD_BYTES)
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
        raise RuntimeError("V2.47.58 contract identity vector drifted")
    groups = tuple(
        tuple(labels[offset : offset + TASK_SIZE])
        for offset in range(0, len(labels), TASK_SIZE)
    )
    questions = tuple(question(group) for group in groups)
    body = f'''"""Visible-only contract for the V2.47.58 zero-effect external gate."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24758_zero_effect_external_visible_contract_v1"
ENTITY_GROUPS = {pprint.pformat(groups, width=100, sort_dicts=False)}
QUESTIONS = {pprint.pformat(questions, width=100, sort_dicts=False)}


def task_vector() -> list[dict[str, str]]:
    return [
        {{
            "opaque_id": "task_" + hashlib.sha256(
                f"v24758:{{position}}:{{question}}".encode("utf-8")
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


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.58 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.58 parent build audit drifted")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.58 population surface exists")

    tree_raw = source._fetch(source.ROR_TREE_URL, limit=source.MAX_ROR_TREE_BYTES)
    entries = ranked_entries(tree_raw)
    _history, historical_canonical = historical_entities()
    normalizer = source.ror_base.history.population._canonical_entity
    fetched: list[tuple[str, str, bytes, Mapping[str, Any]]] = []
    selected: list[dict[str, Any]] = []
    metrics: dict[str, int] = {}
    for offset in range(0, min(MAX_FETCH_PREFIX, len(entries)), FETCH_BATCH):
        fetched.extend(fetch_records(entries[offset : offset + FETCH_BATCH]))
        selected, metrics = select_records(
            fetched,
            historical_canonical=historical_canonical,
            canonical=normalizer,
            require_complete=False,
        )
        if len(selected) == SELECTED_COUNT:
            break
    if len(selected) != SELECTED_COUNT:
        raise RuntimeError("V2.47.58 deterministic ROR prefix lacks capacity")

    now = int(time.time())
    private = {
        "artifact_version": 1,
        "role": "v24758_zero_effect_evaluator_only_population",
        "created_at_unix": now,
        "source_commit": source.ROR_COMMIT,
        "source_version": source.ROR_VERSION,
        "source_tree_sha1": source.ROR_TREE_SHA1,
        "selection_rule": (
            "immutable_ror_v211_active_education_exact_display_prior4680_disjoint_"
            "established_1000_2025_country_present_v24758_hash_rank_country_cap4"
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
        "role": "v24758_zero_effect_population_design",
        "created_at_unix": now,
        "git_head": _git("rev-parse", "HEAD"),
        "parent_build_audit_sha256": _sha256(ROOT / PARENT),
        "source": {
            "commit": source.ROR_COMMIT,
            "version": source.ROR_VERSION,
            "tree_sha1": source.ROR_TREE_SHA1,
            "tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
            "tree_record_count": len(entries),
            "fixed_rank_seed": RANK_SEED,
            "fetched_rank_prefix_count": len(fetched),
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
            "immutable_ror_record_reads": len(fetched),
            "model_search_benchmark_or_evaluator_calls": 0,
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
                "fetched_rank_prefix_count": len(fetched),
                "output": str(OUTPUT),
                "private": str(PRIVATE),
                "selected_count": len(selected),
                "task_count": len(selected) // TASK_SIZE,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
