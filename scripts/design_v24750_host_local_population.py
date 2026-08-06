#!/usr/bin/env python3
"""Freeze the fresh population for one host-local scheduling successor."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24744_cross_domain_contract as prior_contract  # noqa: E402
from scripts import design_v24744_cross_domain_population as prior  # noqa: E402


DATE = "20260806"
PRESELECTION_COMMIT = "04a05f3"
OUTPUT = Path(f"results/v24750_host_local_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24750_host_local_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24750_host_local_contract.py")
PARENT_DIAGNOSIS = Path(
    f"results/v24749_v24748_host_rate_limit_diagnosis_v1_{DATE}.json"
)

ROR_SELECTED_COUNT = 8
ROR_TASK_SIZE = 4
ROR_COUNTRY_CAP = 2
DOI_TASK_SIZE = 4
EXPECTED_PRIOR_ROR_COUNT = 4_680
MAX_ROR_RECORD_FETCHES = 512

OFFICIAL_CROSSREF_DOIS = (
    "10.1038/nature12373",
    "10.1038/nature12443",
    "10.1038/s41586-020-2649-2",
    "10.1038/s41586-020-03113-5",
    "10.1038/s41586-022-04815-2",
    "10.1038/s41586-023-06004-9",
    "10.1126/science.1127647",
    "10.1126/science.1151810",
)
ORDINARY_DUAL_SOURCE_DOIS = (
    "10.1126/science.1201158",
    "10.1126/science.1260419",
    "10.1109/TPAMI.2008.50",
    "10.1109/CVPR.2015.7298594",
    "10.1145/1273442.1252032",
    "10.1145/1963405.1963494",
    "10.1016/j.cell.2012.03.034",
    "10.1073/pnas.0703993104",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=check,
    )


def _git_text(*args: str) -> str:
    return _git(*args).stdout.decode("utf-8").strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> dict[str, Any]:
    value = json.loads((ROOT / PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
    if (
        not isinstance(value, Mapping)
        or value.get("role")
        != "v24749_v24748_host_rate_limit_postterminal_diagnosis"
        or value.get("authorization", {}).get(
            "fresh_host_local_scheduler_successor_design"
        )
        is not True
        or value.get("authorization", {}).get(
            "same_population_retry_resume_or_selective_rerun"
        )
        is not False
        or value.get("authorization", {}).get("fresh_external_successor_launch")
        is not False
        or not _sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.47.50 parent diagnosis drifted")
    return dict(value)


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


def doi_population_rows() -> list[dict[str, Any]]:
    vector = list(OFFICIAL_CROSSREF_DOIS + ORDINARY_DUAL_SOURCE_DOIS)
    if len(vector) != 16 or len({value.casefold() for value in vector}) != 16:
        raise RuntimeError("V2.47.50 DOI vector drifted")
    rows = []
    for position, doi in enumerate(vector, 1):
        completed = _git(
            "grep",
            "--fixed-strings",
            "--ignore-case",
            "--name-only",
            doi,
            PRESELECTION_COMMIT,
            "--",
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError("V2.47.50 DOI absence proof failed")
        paths = sorted(
            line
            for line in completed.stdout.decode("utf-8").splitlines()
            if line
        )
        rows.append(
            {
                "position": position,
                "doi": doi,
                "mode": (
                    "official_crossref_exact_record"
                    if position <= len(OFFICIAL_CROSSREF_DOIS)
                    else "ordinary_crossref_openalex_corroboration"
                ),
                "preselection_occurrence_count": len(paths),
                "preselection_paths_sha256": payload_sha256(paths),
            }
        )
    if any(row["preselection_occurrence_count"] != 0 for row in rows):
        raise RuntimeError("V2.47.50 DOI was present before selection")
    return rows


def prior_ror_entities() -> tuple[set[str], set[str]]:
    visible, _canonical = prior.prior_ror_entities()
    previous = {entity for group in prior_contract.ROR_GROUPS for entity in group}
    if len(previous) != 8:
        raise RuntimeError("V2.47.50 prior cross-domain ROR vector drifted")
    visible.update(previous)
    canonicalizer = prior.ror_base.ror_base.history.population._canonical_entity
    canonical = {canonicalizer(entity) for entity in visible}
    if (
        len(visible) != EXPECTED_PRIOR_ROR_COUNT
        or len(canonical) != EXPECTED_PRIOR_ROR_COUNT
        or "" in canonical
    ):
        raise RuntimeError("V2.47.50 prior ROR history drifted")
    return visible, canonical


def ranked_ror_entries(tree_raw: bytes) -> list[tuple[str, str, str]]:
    entries = prior.ror_base.parse_ror_tree(tree_raw)
    ranked = [
        (
            hashlib.sha256(
                f"{prior.ror_base.ROR_COMMIT}:v24750:{path[:-5]}".encode("utf-8")
            ).hexdigest(),
            path,
            blob,
        )
        for path, blob in entries
    ]
    return sorted(ranked)


def select_ror_records(
    ranked_records: list[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    require_complete: bool = True,
) -> list[dict[str, str]]:
    canonicalizer = prior.ror_base.ror_base.history.population._canonical_entity
    selected: list[dict[str, str]] = []
    countries: Counter[str] = Counter()
    for rank, path, raw, value in ranked_records:
        blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw,
            usedforsecurity=False,
        ).hexdigest()
        item = prior.ror_base._ror_candidate(
            path=path,
            blob_sha1=blob,
            raw=raw,
            value=value,
            historical_canonical=historical_canonical,
            canonical=canonicalizer,
        )
        if item is None or countries[item["country"]] >= ROR_COUNTRY_CAP:
            continue
        item = dict(item)
        item["rank"] = rank
        selected.append(item)
        countries[item["country"]] += 1
        if len(selected) == ROR_SELECTED_COUNT:
            break
    if (
        (require_complete and len(selected) != ROR_SELECTED_COUNT)
        or len({item["label"] for item in selected}) != len(selected)
        or len({item["canonical"] for item in selected}) != len(selected)
        or any(item["canonical"] in historical_canonical for item in selected)
        or max(countries.values(), default=0) > ROR_COUNTRY_CAP
    ):
        raise RuntimeError("V2.47.50 selected ROR vector drifted")
    return selected


def contract_source(records: list[Mapping[str, str]]) -> bytes:
    original_official = prior.OFFICIAL_CROSSREF_DOIS
    original_ordinary = prior.ORDINARY_DUAL_SOURCE_DOIS
    try:
        prior.OFFICIAL_CROSSREF_DOIS = OFFICIAL_CROSSREF_DOIS
        prior.ORDINARY_DUAL_SOURCE_DOIS = ORDINARY_DUAL_SOURCE_DOIS
        source = prior.contract_source(records).decode("utf-8")
    finally:
        prior.OFFICIAL_CROSSREF_DOIS = original_official
        prior.ORDINARY_DUAL_SOURCE_DOIS = original_ordinary
    return source.replace("V2.47.44", "V2.47.50").replace(
        "v24744", "v24750"
    ).encode("utf-8")


def main() -> None:
    if _git_text("status", "--porcelain") or _git_text(
        "rev-parse", "HEAD"
    ) != _git_text("rev-parse", "target/main"):
        raise RuntimeError("V2.47.50 population design requires clean pushed HEAD")
    if (
        _git("merge-base", "--is-ancestor", PRESELECTION_COMMIT, "HEAD", check=False).returncode
        != 0
    ):
        raise RuntimeError("V2.47.50 preselection commit is not an ancestor")
    _parent_valid()
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.50 population surface exists")

    doi_rows = doi_population_rows()
    tree_raw = prior.ror_base._fetch(
        prior.ror_base.ROR_TREE_URL, limit=prior.ror_base.MAX_ROR_TREE_BYTES
    )
    ranked_entries = ranked_ror_entries(tree_raw)
    _history, historical_canonical = prior_ror_entities()
    fetched: list[tuple[str, str, bytes, Mapping[str, Any]]] = []
    selected: list[dict[str, str]] = []
    for rank, path, blob in ranked_entries[:MAX_ROR_RECORD_FETCHES]:
        raw = prior.ror_base._fetch(
            prior.ror_base.ROR_RAW_PREFIX + path,
            limit=prior.ror_base.MAX_ROR_RECORD_BYTES,
        )
        _path, _blob, _raw, value = prior.ror_base.validate_ror_blob(
            path, blob, raw
        )
        fetched.append((rank, path, raw, value))
        selected = select_ror_records(
            fetched,
            historical_canonical=historical_canonical,
            require_complete=False,
        )
        if len(selected) == ROR_SELECTED_COUNT:
            break
    if len(selected) != ROR_SELECTED_COUNT:
        raise RuntimeError("V2.47.50 deterministic ROR prefix lacks capacity")

    now = int(time.time())
    private = {
        "artifact_version": 1,
        "role": "v24750_host_local_private_population",
        "created_at_unix": now,
        "ror": {
            "commit": prior.ror_base.ROR_COMMIT,
            "version": prior.ror_base.ROR_VERSION,
            "directory_tree_sha1": prior.ror_base.ROR_TREE_SHA1,
            "records": [
                {
                    key: item[key]
                    for key in (
                        "label",
                        "record_id",
                        "country",
                        "git_blob_sha1",
                        "record_bytes_sha256",
                    )
                }
                for item in selected
            ],
        },
        "doi_rows": doi_rows,
        "forward_import_or_runtime_read_authorized": False,
        "evaluator_or_quality_read_before_prediction_freeze_authorized": False,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    private_raw = (
        json.dumps(private, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    contract_raw = contract_source(selected)
    public = {
        "artifact_version": 1,
        "role": "v24750_host_local_population_design",
        "created_at_unix": now,
        "preselection_commit": _git_text("rev-parse", PRESELECTION_COMMIT),
        "git_head": _git_text("rev-parse", "HEAD"),
        "parent_diagnosis_file_sha256": _sha256(ROOT / PARENT_DIAGNOSIS),
        "selection_timing": {
            "doi_vector_and_ror_seed_frozen_before_endpoint_outcome": True,
            "crossref_openalex_or_ror_api_called": False,
            "prior_v24748_response_body_url_doi_entity_value_or_prediction_read": False,
            "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        },
        "ror": {
            "source_commit": prior.ror_base.ROR_COMMIT,
            "source_tree_sha1": prior.ror_base.ROR_TREE_SHA1,
            "tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
            "historical_entity_count": EXPECTED_PRIOR_ROR_COUNT,
            "fixed_rank_seed": "v24750",
            "record_fetch_prefix_count": len(fetched),
            "selected_count": len(selected),
            "country_count": len({item["country"] for item in selected}),
            "country_max": max(
                Counter(item["country"] for item in selected).values()
            ),
            "visible_vector_sha256": payload_sha256(
                [item["label"] for item in selected]
            ),
            "record_provenance_vector_sha256": payload_sha256(
                [
                    {
                        key: item[key]
                        for key in (
                            "record_id",
                            "country",
                            "git_blob_sha1",
                            "record_bytes_sha256",
                        )
                    }
                    for item in selected
                ]
            ),
        },
        "doi": {
            "selected_count": len(doi_rows),
            "official_exact_record_count": len(OFFICIAL_CROSSREF_DOIS),
            "ordinary_dual_source_count": len(ORDINARY_DUAL_SOURCE_DOIS),
            "all_absent_from_preselection_tree": True,
            "visible_vector_sha256": payload_sha256(
                [row["doi"] for row in doi_rows]
            ),
        },
        "task_shape": {
            "ror_tasks": 2,
            "official_crossref_tasks": 2,
            "ordinary_dual_source_tasks": 2,
            "total_tasks": 6,
            "total_rows": 24,
        },
        "private_file_sha256": hashlib.sha256(private_raw).hexdigest(),
        "visible_contract_sha256": hashlib.sha256(contract_raw).hexdigest(),
        "authorization": {
            "host_local_scheduler_and_gate_build": True,
            "external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_claim": False,
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
                "doi_count": len(doi_rows),
                "output": str(OUTPUT),
                "private": str(PRIVATE),
                "ror_fetch_prefix_count": len(fetched),
                "ror_selected_count": len(selected),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
