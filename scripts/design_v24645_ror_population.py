#!/usr/bin/env python3
"""Design a fresh evaluator-isolated ROR population for V2.46.45.

This is a design-time registry reader, not a forward runtime.  It consumes a
fixed immutable ROR tree slice, reconstructs all prior visible entity surfaces,
and publishes (1) an evaluator-only private selected vector and (2) a
content-free public design audit.  It never calls a model, search provider,
benchmark, or evaluator and grants no launch authority.
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
from deepwide_agent.v24637_external_contract import ENTITY_GROUPS as AIRPORTS  # noqa: E402
from deepwide_agent.v24639_ror_external_contract import ENTITY_GROUPS as ROR39  # noqa: E402
from deepwide_agent.v24640_ror_external_contract import ENTITY_GROUPS as ROR40  # noqa: E402
from deepwide_agent.v24642_ror_external_contract import ENTITY_GROUPS as ROR42  # noqa: E402
from scripts import v24625_predicate_binding_external_gate as history  # noqa: E402


DATE = "20260806"
COMMIT = "aab1443afefefa8460e69ab01bccceff0a8544d4"
VERSION = "v2.11"
DIRECTORY_TREE_SHA1 = "473b00391664ad5a782605516ba0bea5b4d14e6b"
SLICE_START = 2_000
SLICE_STOP = 3_000
SELECTED_COUNT = 48
COUNTRY_CAP = 3
PARENT = Path(f"results/v24644_primary_identity_pair_build_audit_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24645_ror_population_private_v1_{DATE}.json")
OUTPUT = Path(f"results/v24645_ror_population_design_v1_{DATE}.json")


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
        raise RuntimeError("V2.46.45 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return (
        value.get("role") == "v24644_primary_identity_pair_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "fresh_external_population_and_protocol_design"
        )
        is True
        and value.get("authorization", {}).get("fresh_external_activation_or_launch")
        is False
        and _sealed(value, "audit_payload_sha256")
    )


def historical_entities() -> tuple[set[str], set[str]]:
    visible = {
        entity
        for question in history._prior_questions() + history.QUESTIONS
        for entity in history.population._question_entity_vector(question)
    }
    for groups in (AIRPORTS, ROR39, ROR40, ROR42):
        visible.update(entity for group in groups for entity in group)
    canonical = {history.population._canonical_entity(entity) for entity in visible}
    if len(visible) != 4_432 or len(canonical) != 4_432 or "" in canonical:
        raise RuntimeError("V2.46.45 historical population drifted")
    return visible, canonical


def _record_candidate(
    entry: Mapping[str, Any],
    raw: bytes,
    value: Mapping[str, Any],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
) -> dict[str, str] | None:
    record_id = str(entry.get("path", ""))[:-5]
    labels = [
        str(name.get("value", "")).strip()
        for name in value.get("names", [])
        if isinstance(name, Mapping)
        and "ror_display" in name.get("types", [])
        and str(name.get("value", "")).strip()
    ]
    locations = value.get("locations") or []
    country = (
        (locations[0].get("geonames_details") or {}).get("country_code")
        if locations and isinstance(locations[0], Mapping)
        else None
    )
    label = labels[0] if len(labels) == 1 else ""
    folded = canonical(label) if label else ""
    if (
        value.get("status") != "active"
        or value.get("id") != f"https://ror.org/{record_id}"
        or not folded
        or folded in historical_canonical
        or not isinstance(country, str)
        or len(country) != 2
        or not country.isalpha()
        or any(character in label for character in "()|\r\n")
        or len(label) > 160
    ):
        return None
    return {
        "rank": hashlib.sha256(
            f"{COMMIT}:v24645:{record_id}".encode("utf-8")
        ).hexdigest(),
        "label": label,
        "canonical": folded,
        "record_id": record_id,
        "git_blob_sha1": str(entry.get("sha", "")),
        "country": country.upper(),
        "record_bytes_sha256": hashlib.sha256(raw).hexdigest(),
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
        raise RuntimeError("V2.46.45 fresh slice lacks selection capacity")
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
    ):
        raise RuntimeError("V2.46.45 selected identity vector drifted")
    metrics = {
        "eligible_record_count_before_slice_canonical_uniqueness": len(eligible),
        "candidate_count": len(candidates),
        "candidate_country_count": len({item["country"] for item in candidates}),
        "country_cap3_capacity": sum(
            min(COUNTRY_CAP, amount)
            for amount in Counter(item["country"] for item in candidates).values()
        ),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
    }
    return interleaved, metrics


def _fetch_json(url: str) -> tuple[bytes, dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.45 registry response was not an object")
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
        raise RuntimeError("V2.46.45 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.46.45 parent build audit drifted")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PRIVATE, OUTPUT)):
        raise FileExistsError("V2.46.45 population design surface exists")

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
        or len(selected_entries) != 1_000
    ):
        raise RuntimeError("V2.46.45 immutable ROR tree slice drifted")

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
            raise RuntimeError("V2.46.45 ROR record Git blob drifted")
        return entry, raw, value

    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        records = list(executor.map(fetch_record, selected_entries))
    historical, historical_canonical = historical_entities()
    selected, metrics = select_records(
        records,
        historical_canonical=historical_canonical,
        canonical=history.population._canonical_entity,
    )
    selection_rule = (
        "ror_tree_json_positions_2000_2999_active_unique_ror_display_"
        "globally_unique_slice_canonical_no_parenthetical_or_table_break_"
        "prior_4432_entity_disjoint_sha256_rank_country_cap3_"
        "quartile_interleaved_groups"
    )
    private = {
        "artifact_version": 1,
        "role": "v24645_ror_evaluator_only_population",
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
        "role": "v24645_ror_population_design",
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
