#!/usr/bin/env python3
"""Freeze an outcome-blind ROR/Crossref/OpenAlex external population.

The DOI vector and ROR ranking seed are fixed in source.  DOI absence is
checked against PRESELECTION_COMMIT, before this source existed.  ROR members
are the first eligible records under a fixed hash order in an immutable Git
tree after rebuilding all previously consumed ROR identity surfaces.  No
Crossref, OpenAlex, ROR API, benchmark, model, evaluator, or score endpoint is
called by this design program.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24733_dual_namespace_contract import (  # noqa: E402
    ROR_ENTITY_GROUPS as V24737_ROR_GROUPS,
)
from scripts import design_v24727_dual_namespace_population as ror_base  # noqa: E402


DATE = "20260806"
PRESELECTION_COMMIT = "1b46d2c"
OUTPUT = Path(f"results/v24744_cross_domain_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24744_cross_domain_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24744_cross_domain_contract.py")

ROR_SELECTED_COUNT = 8
ROR_TASK_SIZE = 4
ROR_COUNTRY_CAP = 2
DOI_TASK_SIZE = 4
EXPECTED_PRIOR_ROR_COUNT = 4_672
MAX_ROR_RECORD_FETCHES = 512

OFFICIAL_CROSSREF_DOIS = (
    "10.1038/171737a0",
    "10.1038/227680a0",
    "10.1038/35057062",
    "10.1038/nature14539",
    "10.1038/nature16961",
    "10.1038/s41586-018-0337-2",
    "10.1038/s41586-021-03819-2",
    "10.1126/science.1058040",
)
ORDINARY_DUAL_SOURCE_DOIS = (
    "10.1126/science.169.3946.635",
    "10.1126/science.286.5439.509",
    "10.1109/5.771073",
    "10.1109/CVPR.2016.90",
    "10.1145/1327452.1327492",
    "10.1145/2939672.2939785",
    "10.1016/j.cell.2011.02.013",
    "10.1073/pnas.0506580102",
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


def _publish(path: Path, value: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def doi_population_rows() -> list[dict[str, Any]]:
    vector = list(OFFICIAL_CROSSREF_DOIS + ORDINARY_DUAL_SOURCE_DOIS)
    if (
        len(vector) != 16
        or len({value.casefold() for value in vector}) != 16
        or any("|" in value or "\n" in value for value in vector)
    ):
        raise RuntimeError("V2.47.44 DOI vector drifted")
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
            raise RuntimeError("V2.47.44 DOI absence proof failed")
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
        raise RuntimeError("V2.47.44 DOI was present before selection")
    return rows


def prior_ror_entities() -> tuple[set[str], set[str]]:
    visible, _canonical = ror_base.prior_ror_entities()
    latest = {entity for group in V24737_ROR_GROUPS for entity in group}
    if len(latest) != 48:
        raise RuntimeError("V2.47.44 V2.47.37 ROR population drifted")
    visible.update(latest)
    canonicalizer = ror_base.ror_base.history.population._canonical_entity
    canonical = {canonicalizer(entity) for entity in visible}
    if (
        len(visible) != EXPECTED_PRIOR_ROR_COUNT
        or len(canonical) != EXPECTED_PRIOR_ROR_COUNT
        or "" in canonical
    ):
        raise RuntimeError("V2.47.44 prior ROR history drifted")
    return visible, canonical


def ranked_ror_entries(tree_raw: bytes) -> list[tuple[str, str, str]]:
    entries = ror_base.parse_ror_tree(tree_raw)
    ranked = []
    for path, blob in entries:
        record_id = path[:-5]
        rank = hashlib.sha256(
            f"{ror_base.ROR_COMMIT}:v24744:{record_id}".encode("utf-8")
        ).hexdigest()
        ranked.append((rank, path, blob))
    ranked.sort()
    return ranked


def select_ror_records(
    ranked_records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    require_complete: bool = True,
) -> list[dict[str, str]]:
    canonicalizer = ror_base.ror_base.history.population._canonical_entity
    selected: list[dict[str, str]] = []
    country_counts: Counter[str] = Counter()
    for rank, path, raw, value in ranked_records:
        blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw,
            usedforsecurity=False,
        ).hexdigest()
        item = ror_base._ror_candidate(
            path=path,
            blob_sha1=blob,
            raw=raw,
            value=value,
            historical_canonical=historical_canonical,
            canonical=canonicalizer,
        )
        if item is None or country_counts[item["country"]] >= ROR_COUNTRY_CAP:
            continue
        item = dict(item)
        item["rank"] = rank
        selected.append(item)
        country_counts[item["country"]] += 1
        if len(selected) == ROR_SELECTED_COUNT:
            break
    if (
        (require_complete and len(selected) != ROR_SELECTED_COUNT)
        or len({item["label"] for item in selected}) != len(selected)
        or len({item["canonical"] for item in selected}) != len(selected)
        or any(item["canonical"] in historical_canonical for item in selected)
        or max(country_counts.values(), default=0) > ROR_COUNTRY_CAP
    ):
        raise RuntimeError("V2.47.44 selected ROR vector drifted")
    return selected


def _groups(values: Sequence[str], size: int) -> tuple[tuple[str, ...], ...]:
    if not values or len(values) % size:
        raise ValueError("V2.47.44 grouping drifted")
    return tuple(
        tuple(values[index : index + size])
        for index in range(0, len(values), size)
    )


def contract_source(ror_records: Sequence[Mapping[str, str]]) -> bytes:
    ror_groups = _groups([item["label"] for item in ror_records], ROR_TASK_SIZE)
    official_groups = _groups(OFFICIAL_CROSSREF_DOIS, DOI_TASK_SIZE)
    ordinary_groups = _groups(ORDINARY_DUAL_SOURCE_DOIS, DOI_TASK_SIZE)
    body = f'''"""Visible-only contract for V2.47.44 cross-domain binding."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24744_cross_domain_visible_contract_v1"
ROR_GROUPS = {ror_groups!r}
OFFICIAL_CROSSREF_DOI_GROUPS = {official_groups!r}
ORDINARY_DUAL_SOURCE_DOI_GROUPS = {ordinary_groups!r}


def _ror_question(group: tuple[str, ...]) -> str:
    rows = "\\n".join(f"{{index}}. {{value}}" for index, value in enumerate(group, 1))
    return (
        "Use public registry records to complete one Markdown table.\\n"
        "<ENTITIES>\\n" + rows + "\\n</ENTITIES>\\n"
        "The column names are: Organization, ROR ID, Country code. "
        "Use the 9-character ROR suffix and ISO 3166-1 alpha-2 code. "
        "Use Unknown when an exact structured record is unavailable."
    )


def _doi_question(group: tuple[str, ...], *, ordinary: bool) -> str:
    rows = "\\n".join(f"{{index}}. {{value}}" for index, value in enumerate(group, 1))
    evidence = (
        "Require the same value from the Crossref and OpenAlex structured records."
        if ordinary
        else "Use the exact-address Crossref registry record."
    )
    return (
        "Use public structured records to complete one Markdown table.\\n"
        "<DOIS>\\n" + rows + "\\n</DOIS>\\n"
        "The column names are: DOI, Title, Year. " + evidence + " "
        "Use Unknown when the required structured support is unavailable."
    )


QUESTIONS = tuple(_ror_question(group) for group in ROR_GROUPS) + tuple(
    _doi_question(group, ordinary=False) for group in OFFICIAL_CROSSREF_DOI_GROUPS
) + tuple(
    _doi_question(group, ordinary=True) for group in ORDINARY_DUAL_SOURCE_DOI_GROUPS
)


def task_vector() -> list[dict[str, str]]:
    return [
        {{
            "opaque_id": "task_" + hashlib.sha256(
                f"v24744:{{position}}:{{question}}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }}
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = [
    "OFFICIAL_CROSSREF_DOI_GROUPS",
    "ORDINARY_DUAL_SOURCE_DOI_GROUPS",
    "POLICY_ID",
    "QUESTIONS",
    "ROR_GROUPS",
    "copy_task_vector",
    "task_vector",
]
'''
    return body.encode("utf-8")


def main() -> None:
    if _git_text("status", "--porcelain") or _git_text(
        "rev-parse", "HEAD"
    ) != _git_text("rev-parse", "target/main"):
        raise RuntimeError("V2.47.44 population design requires clean pushed HEAD")
    if _git("merge-base", "--is-ancestor", PRESELECTION_COMMIT, "HEAD", check=False).returncode:
        raise RuntimeError("V2.47.44 preselection commit is not an ancestor")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.44 population surface exists")

    doi_rows = doi_population_rows()
    tree_raw = ror_base._fetch(ror_base.ROR_TREE_URL, limit=ror_base.MAX_ROR_TREE_BYTES)
    ranked_entries = ranked_ror_entries(tree_raw)
    _history, historical_canonical = prior_ror_entities()
    fetched: list[tuple[str, str, bytes, Mapping[str, Any]]] = []
    selected: list[dict[str, str]] = []
    for rank, path, blob in ranked_entries[:MAX_ROR_RECORD_FETCHES]:
        raw = ror_base._fetch(
            ror_base.ROR_RAW_PREFIX + path,
            limit=ror_base.MAX_ROR_RECORD_BYTES,
        )
        _path, _blob, _raw, value = ror_base.validate_ror_blob(path, blob, raw)
        fetched.append((rank, path, raw, value))
        selected = select_ror_records(
            fetched,
            historical_canonical=historical_canonical,
            require_complete=False,
        )
        if len(selected) == ROR_SELECTED_COUNT:
            break
    if len(selected) != ROR_SELECTED_COUNT:
        raise RuntimeError("V2.47.44 deterministic ROR prefix lacks capacity")

    now = int(time.time())
    private = {
        "artifact_version": 1,
        "role": "v24744_cross_domain_private_population",
        "created_at_unix": now,
        "ror": {
            "commit": ror_base.ROR_COMMIT,
            "version": ror_base.ROR_VERSION,
            "directory_tree_sha1": ror_base.ROR_TREE_SHA1,
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
        "role": "v24744_cross_domain_population_design",
        "created_at_unix": now,
        "preselection_commit": _git_text("rev-parse", PRESELECTION_COMMIT),
        "git_head": _git_text("rev-parse", "HEAD"),
        "selection_timing": {
            "doi_vector_and_ror_seed_frozen_before_endpoint_outcome": True,
            "crossref_openalex_or_ror_api_called": False,
            "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        },
        "ror": {
            "source_commit": ror_base.ROR_COMMIT,
            "source_tree_sha1": ror_base.ROR_TREE_SHA1,
            "tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
            "historical_entity_count": EXPECTED_PRIOR_ROR_COUNT,
            "fixed_rank_seed": "v24744",
            "record_fetch_prefix_count": len(fetched),
            "selected_count": len(selected),
            "country_count": len({item["country"] for item in selected}),
            "country_max": max(Counter(item["country"] for item in selected).values()),
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
            "ror_tasks": len(selected) // ROR_TASK_SIZE,
            "official_crossref_tasks": len(OFFICIAL_CROSSREF_DOIS) // DOI_TASK_SIZE,
            "ordinary_dual_source_tasks": len(ORDINARY_DUAL_SOURCE_DOIS)
            // DOI_TASK_SIZE,
            "total_tasks": 6,
            "total_rows": 24,
        },
        "private_file_sha256": hashlib.sha256(private_raw).hexdigest(),
        "visible_contract_sha256": hashlib.sha256(contract_raw).hexdigest(),
        "authorization": {
            "cross_domain_adapter_and_gate_build": True,
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
