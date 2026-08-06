#!/usr/bin/env python3
"""Design the fresh evaluator-isolated ROR population for V2.46.50.

This design-time reader consumes the final unused slice of the immutable ROR
v2.11 tree.  It excludes every prior visible entity, filters query-ambiguous
identity literals, and publishes a private evaluator vector plus a content-free
public population audit.  It grants no launch or evaluator authority.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24645_ror_external_contract import (  # noqa: E402
    ENTITY_GROUPS as ROR45,
)
from scripts import design_v24645_ror_population as prior  # noqa: E402


DATE = "20260806"
COMMIT = prior.COMMIT
VERSION = prior.VERSION
DIRECTORY_TREE_SHA1 = prior.DIRECTORY_TREE_SHA1
SLICE_START = 3_000
SLICE_STOP = 3_482
SELECTED_COUNT = 48
COUNTRY_CAP = 4
PARENT = Path(f"results/v24649_unknown_target_structured_build_audit_v2_{DATE}.json")
PRIVATE = Path(f"evaluation/v24650_ror_population_private_v1_{DATE}.json")
OUTPUT = Path(f"results/v24650_ror_population_design_v1_{DATE}.json")


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.50 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return (
        value.get("role") == "v24649_unknown_target_structured_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("supersedes", {}).get("v1_authorizes_successor_use") is False
        and value.get("authorization", {}).get(
            "fresh_external_population_and_protocol_design"
        )
        is True
        and value.get("authorization", {}).get(
            "fresh_external_activation_or_launch"
        )
        is False
        and _sealed(value, "audit_payload_sha256")
    )


def historical_entities() -> tuple[set[str], set[str]]:
    visible, canonical = prior.historical_entities()
    visible.update(entity for group in ROR45 for entity in group)
    normalizer = prior.history.population._canonical_entity
    canonical = {normalizer(entity) for entity in visible}
    if len(visible) != 4_480 or len(canonical) != 4_480 or "" in canonical:
        raise RuntimeError("V2.46.50 historical population drifted")
    return visible, canonical


def _record_candidate(
    entry: Mapping[str, Any],
    raw: bytes,
    value: Mapping[str, Any],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
) -> dict[str, str] | None:
    candidate = prior._record_candidate(
        entry,
        raw,
        value,
        historical_canonical=historical_canonical,
        canonical=canonical,
    )
    if candidate is None or any(
        character in candidate["label"] for character in ('"', "\\")
    ):
        return None
    record_id = candidate["record_id"]
    return {
        **candidate,
        "rank": hashlib.sha256(
            f"{COMMIT}:v24650:{record_id}".encode("utf-8")
        ).hexdigest(),
    }


def select_records(
    records: Sequence[tuple[Mapping[str, Any], bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    eligible = [
        candidate
        for entry, raw, value in records
        if (
            candidate := _record_candidate(
                entry,
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
    selected: list[dict[str, str]] = []
    countries: Counter[str] = Counter()
    for item in candidates:
        if countries[item["country"]] >= COUNTRY_CAP:
            continue
        selected.append(item)
        countries[item["country"]] += 1
        if len(selected) == SELECTED_COUNT:
            break
    if len(selected) != SELECTED_COUNT:
        raise RuntimeError("V2.46.50 final immutable slice lacks selection capacity")
    quarter = SELECTED_COUNT // 4
    interleaved = [
        item
        for group in zip(
            selected[:quarter],
            selected[quarter : 2 * quarter],
            selected[2 * quarter : 3 * quarter],
            selected[3 * quarter :],
            strict=True,
        )
        for item in group
    ]
    if (
        len({item["label"] for item in interleaved}) != SELECTED_COUNT
        or len({item["canonical"] for item in interleaved}) != SELECTED_COUNT
        or any(item["canonical"] in historical_canonical for item in interleaved)
        or any(any(character in item["label"] for character in ('"', "\\")) for item in interleaved)
    ):
        raise RuntimeError("V2.46.50 selected identity vector drifted")
    country_counts = Counter(item["country"] for item in candidates)
    return interleaved, {
        "eligible_record_count_before_slice_canonical_uniqueness": len(eligible),
        "candidate_count": len(candidates),
        "candidate_country_count": len(country_counts),
        "country_cap4_capacity": sum(
            min(COUNTRY_CAP, amount) for amount in country_counts.values()
        ),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
    }


def _fetch_json(url: str) -> tuple[bytes, dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.50 immutable ROR response expected object")
    return raw, value


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.50 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.46.50 parent build audit drifted")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.46.50 population design surface exists")

    tree_raw, tree = _fetch_json(
        "https://api.github.com/repos/ror-community/ror-records/git/trees/"
        + DIRECTORY_TREE_SHA1
    )
    entries = [
        item
        for item in tree.get("tree", [])
        if isinstance(item, Mapping)
        and item.get("type") == "blob"
        and str(item.get("path", "")).endswith(".json")
    ]
    selected_entries = entries[SLICE_START:SLICE_STOP]
    if (
        tree.get("truncated") is not False
        or len(entries) != 3_482
        or len(selected_entries) != 482
    ):
        raise RuntimeError("V2.46.50 immutable ROR tree slice drifted")

    def fetch_record(
        entry: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], bytes, Mapping[str, Any]]:
        raw, value = _fetch_json(
            "https://raw.githubusercontent.com/ror-community/ror-records/"
            f"{COMMIT}/{VERSION}/{entry['path']}"
        )
        blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw,
            usedforsecurity=False,
        ).hexdigest()
        if blob != entry.get("sha"):
            raise RuntimeError("V2.46.50 ROR record Git blob drifted")
        return entry, raw, value

    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        records = list(executor.map(fetch_record, selected_entries))
    historical, historical_canonical = historical_entities()
    selected, metrics = select_records(
        records,
        historical_canonical=historical_canonical,
        canonical=prior.history.population._canonical_entity,
    )
    selection_rule = (
        "ror_tree_json_positions_3000_3481_active_unique_ror_display_"
        "globally_unique_slice_canonical_no_parenthetical_table_break_quote_or_backslash_"
        "prior_4480_entity_disjoint_sha256_rank_country_cap4_quartile_interleaved_groups"
    )
    private = {
        "artifact_version": 1,
        "role": "v24650_ror_evaluator_only_population",
        "created_at_unix": int(time.time()),
        "commit": COMMIT,
        "version": VERSION,
        "directory_tree_sha1": DIRECTORY_TREE_SHA1,
        "slice_start_inclusive": SLICE_START,
        "slice_stop_exclusive": SLICE_STOP,
        "selection_rule": selection_rule,
        "records": [
            {
                key: item[key]
                for key in (
                    "label",
                    "record_id",
                    "git_blob_sha1",
                    "country",
                    "record_bytes_sha256",
                )
            }
            for item in selected
        ],
        "forward_import_or_runtime_read_authorized": False,
        "gold_evaluator_or_quality_read_before_prediction_freeze_authorized": False,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    public = {
        "artifact_version": 1,
        "role": "v24650_ror_population_design",
        "created_at_unix": int(time.time()),
        "parent_build_audit_sha256": _sha256(ROOT / PARENT),
        "git_head": _git("rev-parse", "HEAD"),
        "commit": COMMIT,
        "version": VERSION,
        "directory_tree_sha1": DIRECTORY_TREE_SHA1,
        "directory_tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
        "tree_json_record_count": len(entries),
        "slice_start_inclusive": SLICE_START,
        "slice_stop_exclusive": SLICE_STOP,
        "slice_first_path": str(selected_entries[0]["path"]),
        "slice_last_path": str(selected_entries[-1]["path"]),
        "historical_entity_count": len(historical),
        "historical_canonical_count": len(historical_canonical),
        **metrics,
        "selected_count": len(selected),
        "selection_rule": selection_rule,
        "historical_canonical_sha256": payload_sha256(
            sorted(historical_canonical)
        ),
        "selected_visible_vector_sha256": payload_sha256(
            [item["label"] for item in selected]
        ),
        "selected_record_vector_sha256": payload_sha256(
            [
                {
                    "record_id": item["record_id"],
                    "git_blob_sha1": item["git_blob_sha1"],
                    "country": item["country"],
                    "record_bytes_sha256": item["record_bytes_sha256"],
                }
                for item in selected
            ]
        ),
        "private_population_file_sha256": None,
        "network": {
            "immutable_github_tree_reads": 1,
            "immutable_github_raw_record_reads": len(records),
            "model_search_benchmark_or_evaluator_calls": 0,
        },
        "privacy": {
            "selected_label_record_id_country_or_gold_emitted": False,
            "private_vector_under_evaluation_directory": True,
            "forward_import_or_runtime_read_authorized": False,
        },
        "authorization": {
            "visible_contract_and_evaluator_gold_design": True,
            "external_protocol_design": True,
            "activation_or_launch": False,
            "dev64_or_exact220": False,
            "evaluator_access": False,
        },
    }
    _publish(ROOT / PRIVATE, private)
    public["private_population_file_sha256"] = _sha256(ROOT / PRIVATE)
    public["design_sha256"] = payload_sha256(public)
    _publish(ROOT / OUTPUT, public)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "private": str(PRIVATE),
                "selected_count": len(selected),
                "design_sha256": public["design_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
