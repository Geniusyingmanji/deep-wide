#!/usr/bin/env python3
"""Reproduce and audit the immutable V2.46.42 ROR task selection."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24637_external_contract import (  # noqa: E402
    ENTITY_GROUPS as AIRPORTS,
)
from deepwide_agent.v24639_ror_external_contract import (  # noqa: E402
    ENTITY_GROUPS as ROR39,
)
from deepwide_agent.v24640_ror_external_contract import (  # noqa: E402
    ENTITY_GROUPS as ROR40,
)
from deepwide_agent.v24642_ror_external_contract import (  # noqa: E402
    DATE,
    ENTITY_GROUPS,
    payload_sha256,
)
from scripts import v24625_predicate_binding_external_gate as history  # noqa: E402
from scripts.build_v24642_ror_gold import (  # noqa: E402
    COMMIT,
    DIRECTORY_TREE_SHA1,
    RECORDS,
    SLICE_START,
    SLICE_STOP,
    VERSION,
)


OUTPUT = Path(f"results/v24642_ror_selection_build_audit_v1_{DATE}.json")


def fetch_json(url: str) -> tuple[bytes, dict]:
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.42 selection expected object")
    return raw, value


def main() -> None:
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)
    tree_raw, tree = fetch_json(
        "https://api.github.com/repos/ror-community/ror-records/git/trees/"
        + DIRECTORY_TREE_SHA1
    )
    entries = [
        item
        for item in tree.get("tree", [])
        if isinstance(item, dict)
        and item.get("type") == "blob"
        and str(item.get("path", "")).endswith(".json")
    ]
    selected_entries = entries[SLICE_START:SLICE_STOP]
    if (
        tree.get("truncated") is not False
        or len(entries) != 3_482
        or len(selected_entries) != 1_000
        or selected_entries[0].get("path") != "01qrts582.json"
        or selected_entries[-1].get("path") != "03ewc1h61.json"
    ):
        raise RuntimeError("V2.46.42 ROR tree slice drifted")

    def fetch_record(entry: dict) -> tuple[dict, bytes, dict]:
        path = str(entry["path"])
        raw, value = fetch_json(
            "https://raw.githubusercontent.com/ror-community/ror-records/"
            f"{COMMIT}/{VERSION}/{path}"
        )
        blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw, usedforsecurity=False
        ).hexdigest()
        if blob != entry.get("sha"):
            raise RuntimeError("V2.46.42 selection record blob drifted")
        return entry, raw, value

    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        records = list(executor.map(fetch_record, selected_entries))

    historical = {
        entity
        for question in history._prior_questions() + history.QUESTIONS
        for entity in history.population._question_entity_vector(question)
    }
    historical.update(entity for group in AIRPORTS for entity in group)
    historical.update(entity for group in ROR39 for entity in group)
    historical.update(entity for group in ROR40 for entity in group)
    canonical = history.population._canonical_entity
    historical_canonical = {canonical(entity) for entity in historical}
    candidates = []
    country_counts: Counter[str] = Counter()
    for entry, raw, value in records:
        labels = [
            name["value"].strip()
            for name in value.get("names", [])
            if "ror_display" in name.get("types", [])
            and str(name.get("value", "")).strip()
        ]
        locations = value.get("locations") or []
        country = (
            (locations[0].get("geonames_details") or {}).get("country_code")
            if locations
            else None
        )
        record_id = str(entry["path"])[:-5]
        if (
            value.get("status") != "active"
            or len(labels) != 1
            or not country
            or "(" in labels[0]
            or ")" in labels[0]
            or canonical(labels[0]) in historical_canonical
        ):
            continue
        candidates.append(
            {
                "rank": hashlib.sha256(
                    f"{COMMIT}:v24642:{record_id}".encode()
                ).hexdigest(),
                "label": labels[0],
                "record_id": record_id,
                "blob": str(entry["sha"]),
                "country": str(country),
                "bytes_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        country_counts[str(country)] += 1
    candidates.sort(key=lambda item: (item["rank"], item["record_id"]))
    selected = []
    selected_country: Counter[str] = Counter()
    for item in candidates:
        if selected_country[item["country"]] >= 3:
            continue
        selected.append(item)
        selected_country[item["country"]] += 1
        if len(selected) == 48:
            break
    interleaved = [item for group in zip(selected[:12], selected[12:24], selected[24:36], selected[36:48], strict=True) for item in group]
    expected = [
        {
            "label": entity,
            "record_id": record_id,
            "blob": blob,
            "country": country,
        }
        for group, records_ in zip(ENTITY_GROUPS, RECORDS, strict=True)
        for entity, (record_id, blob, country) in zip(group, records_, strict=True)
    ]
    observed = [
        {key: item[key] for key in ("label", "record_id", "blob", "country")}
        for item in interleaved
    ]
    findings = []
    if len(historical) != 4_384 or len(historical_canonical) != 4_384:
        findings.append("historical_population_drifted")
    if len(candidates) != 541 or len(country_counts) != 46:
        findings.append("candidate_population_drifted")
    if sum(min(3, amount) for amount in country_counts.values()) != 73:
        findings.append("country_cap_capacity_drifted")
    if (
        len(selected) != 48
        or len(selected_country) != 32
        or max(selected_country.values(), default=0) != 3
    ):
        findings.append("selected_country_balance_drifted")
    if observed != expected:
        findings.append("selected_vector_drifted")
    value_out = {
        "artifact_version": 1,
        "role": "v24642_ror_selection_build_audit",
        "commit": COMMIT,
        "version": VERSION,
        "directory_tree_sha1": DIRECTORY_TREE_SHA1,
        "directory_tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
        "tree_json_record_count": len(entries),
        "slice_start_inclusive": SLICE_START,
        "slice_stop_exclusive": SLICE_STOP,
        "slice_first_path": selected_entries[0]["path"],
        "slice_last_path": selected_entries[-1]["path"],
        "historical_entity_count": len(historical),
        "historical_canonical_count": len(historical_canonical),
        "candidate_count": len(candidates),
        "candidate_country_count": len(country_counts),
        "country_cap3_capacity": sum(min(3, amount) for amount in country_counts.values()),
        "selected_count": len(selected),
        "selected_country_count": len(selected_country),
        "selected_country_max": max(selected_country.values(), default=0),
        "selection_rule": "ror_tree_json_positions_1000_1999_active_unique_display_no_parenthetical_country_prior_4384_entity_disjoint_sha256_rank_country_cap3_quartile_interleaved_groups",
        "historical_canonical_sha256": payload_sha256(sorted(historical_canonical)),
        "selected_visible_vector_sha256": payload_sha256(
            [item["label"] for item in interleaved]
        ),
        "selected_record_vector_sha256": payload_sha256(
            [
                {
                    "record_id": item["record_id"],
                    "blob": item["blob"],
                    "country": item["country"],
                    "bytes_sha256": item["bytes_sha256"],
                }
                for item in interleaved
            ]
        ),
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_evaluator_called": False,
        "github_raw_record_reads_for_immutable_selection_audit": 1_000,
        "authorization": {
            "control_surface_design": not findings,
            "external_launch": False,
            "dev64": False,
            "exact220": False,
        },
    }
    value_out["audit_sha256"] = payload_sha256(value_out)
    if findings:
        raise RuntimeError("V2.46.42 selection audit failed: " + ",".join(findings))
    path = ROOT / OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value_out, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
