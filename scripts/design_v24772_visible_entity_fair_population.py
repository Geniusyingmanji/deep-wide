#!/usr/bin/env python3
"""Freeze the fresh V2.47.72 visible-entity-fair external population.

V2.47.71 authorizes only a new, disjoint benchmark-external protocol design.
This selector therefore rebuilds the 4,720 previously consumed ROR identities,
uses a new fixed rank seed over the immutable ROR v2.11 tree, and publishes
three physically separated surfaces:

* a content-free public design receipt;
* evaluator-only field truth and immutable-record provenance; and
* a visible-only ``{opaque_id, question}`` contract.

It does not call a model, hosted search, benchmark forward, or evaluator and
does not authorize preactivation, activation, launch, dev64, or exact-220.
"""

from __future__ import annotations

import ast
import concurrent.futures
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

from deepwide_agent import v24750_host_local_contract as v24750_contract  # noqa: E402
from deepwide_agent import v24760_zero_effect_external_contract as v24760_contract  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24758_zero_effect_population as eligibility  # noqa: E402
from scripts import design_v24760_zero_effect_population as prior  # noqa: E402


DATE = "20260807"
PARENT = Path(f"results/v24771_visible_entity_fair_build_audit_v1_{DATE}.json")
OUTPUT = Path(f"results/v24772_visible_entity_fair_population_design_v1_{DATE}.json")
PRIVATE = Path(f"evaluation/v24772_visible_entity_fair_population_private_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24772_visible_entity_fair_contract.py")

SELECTED_COUNT = 32
TASK_SIZE = 4
COUNTRY_CAP = 11
EXPECTED_BASE_HISTORY = 4_680
EXPECTED_V24750 = 8
EXPECTED_V24760 = 32
EXPECTED_HISTORY = 4_720
RANK_SEED = "v24772"
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
        raise RuntimeError("V2.47.72 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.72 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return bool(
        value.get("role") == "v24771_visible_entity_fair_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("implementation_contract", {}).get("valid") is True
        and value.get("label_blind_audit", {}).get("passed") is True
        and value.get("authorization", {}).get(
            "fresh_disjoint_external_protocol_design"
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
        and _sealed(value, "audit_payload_sha256")
    )


def historical_entities() -> tuple[set[str], set[str]]:
    """Rebuild all 4,720 consumed ROR identities without opening private truth."""

    visible, _canonical = eligibility.historical_entities()
    v24750 = {
        entity for group in v24750_contract.ROR_GROUPS for entity in group
    }
    v24760 = {
        entity for group in v24760_contract.ENTITY_GROUPS for entity in group
    }
    normalizer = eligibility.source.ror_base.history.population._canonical_entity
    if (
        len(visible) != EXPECTED_BASE_HISTORY
        or len(v24750) != EXPECTED_V24750
        or len(v24760) != EXPECTED_V24760
        or v24750 & v24760
        or {normalizer(entity) for entity in v24750}
        & {normalizer(entity) for entity in v24760}
    ):
        raise RuntimeError("V2.47.72 prior visible vectors drifted")
    visible.update(v24750)
    visible.update(v24760)
    canonical = {normalizer(entity) for entity in visible}
    if (
        len(visible) != EXPECTED_HISTORY
        or len(canonical) != EXPECTED_HISTORY
        or "" in canonical
    ):
        raise RuntimeError("V2.47.72 historical ROR population drifted")
    return visible, canonical


def ranked_entries(tree_raw: bytes) -> list[tuple[str, str]]:
    entries = eligibility.source.parse_ror_tree(tree_raw)
    return sorted(
        entries,
        key=lambda item: (
            hashlib.sha256(
                f"{eligibility.source.ROR_COMMIT}:{RANK_SEED}:{item[0][:-5]}".encode()
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
    candidate = eligibility.record_candidate(
        path,
        blob_sha1,
        raw,
        value,
        historical_canonical=historical_canonical,
        canonical=canonical,
    )
    if candidate is None:
        return None
    copied = dict(candidate)
    copied["rank"] = hashlib.sha256(
        f"{eligibility.source.ROR_COMMIT}:{RANK_SEED}:{copied['record_id']}".encode()
    ).hexdigest()
    return copied


def select_records(
    records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
    selected_count: int = SELECTED_COUNT,
    country_cap: int = COUNTRY_CAP,
    require_complete: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if (
        isinstance(selected_count, bool)
        or selected_count <= 0
        or selected_count % TASK_SIZE
        or isinstance(country_cap, bool)
        or country_cap != COUNTRY_CAP
    ):
        raise ValueError("V2.47.72 selection envelope drifted")
    eligible_records = [
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
    canonical_counts = Counter(str(item["canonical"]) for item in eligible_records)
    candidates = [
        item
        for item in eligible_records
        if canonical_counts[str(item["canonical"])] == 1
    ]
    candidates.sort(key=lambda item: (item["rank"], item["record_id"]))
    selected: list[dict[str, Any]] = []
    countries: Counter[str] = Counter()
    for item in candidates:
        if countries[str(item["country_code"])] >= country_cap:
            continue
        selected.append(item)
        countries[str(item["country_code"])] += 1
        if len(selected) == selected_count:
            break
    if (
        (require_complete and len(selected) != selected_count)
        or len({item["label"] for item in selected}) != len(selected)
        or len({item["canonical"] for item in selected}) != len(selected)
        or any(item["canonical"] in historical_canonical for item in selected)
        or max(countries.values(), default=0) > country_cap
    ):
        raise RuntimeError("V2.47.72 selected vector drifted")
    return selected, {
        "eligible_record_count": len(eligible_records),
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
        raw = eligibility.source._fetch(
            eligibility.source.ROR_RAW_PREFIX + path,
            limit=eligibility.source.MAX_ROR_RECORD_BYTES,
        )
        return eligibility.source.validate_ror_blob(path, blob, raw)

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
        raise RuntimeError("V2.47.72 contract identity vector drifted")
    groups = tuple(
        tuple(labels[offset : offset + TASK_SIZE])
        for offset in range(0, len(labels), TASK_SIZE)
    )
    questions = tuple(question(group) for group in groups)
    body = f'''"""Visible-only contract for the V2.47.72 fair-recovery external gate."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24772_visible_entity_fair_external_contract_v1"
ENTITY_GROUPS = {pprint.pformat(groups, width=100, sort_dicts=False)}
QUESTIONS = {pprint.pformat(questions, width=100, sort_dicts=False)}


def task_vector() -> list[dict[str, str]]:
    return [
        {{
            "opaque_id": "task_" + hashlib.sha256(
                f"v24772:{{position}}:{{question}}".encode("utf-8")
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
        raise RuntimeError("V2.47.72 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.72 build-audit parent drifted")
    surfaces = (ROOT / OUTPUT, ROOT / PRIVATE, ROOT / CONTRACT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.72 population surface exists")

    tree_raw = eligibility.source._fetch(
        eligibility.source.ROR_TREE_URL,
        limit=eligibility.source.MAX_ROR_TREE_BYTES,
    )
    entries = ranked_entries(tree_raw)
    _history, historical_canonical = historical_entities()
    normalizer = eligibility.source.ror_base.history.population._canonical_entity
    # Read the complete immutable tree before checking canonical uniqueness.
    # Stopping after a sufficient prefix could silently accept an identity
    # whose canonical duplicate appears later in the snapshot.
    fetched = fetch_records(entries)
    selected, metrics = select_records(
        fetched,
        historical_canonical=historical_canonical,
        canonical=normalizer,
    )

    now = int(time.time())
    private = {
        "artifact_version": 1,
        "role": "v24772_visible_entity_fair_evaluator_only_population",
        "created_at_unix": now,
        "source_commit": eligibility.source.ROR_COMMIT,
        "source_version": eligibility.source.ROR_VERSION,
        "source_tree_sha1": eligibility.source.ROR_TREE_SHA1,
        "selection_rule": (
            "immutable_ror_v211_active_education_exact_display_prior4720_disjoint_"
            "established_1000_2025_country_present_v24772_hash_rank_country_cap11"
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
        "role": "v24772_visible_entity_fair_population_design",
        "created_at_unix": now,
        "git_head": _git("rev-parse", "HEAD"),
        "parent_build_audit_sha256": _sha256(ROOT / PARENT),
        "source": {
            "commit": eligibility.source.ROR_COMMIT,
            "version": eligibility.source.ROR_VERSION,
            "tree_sha1": eligibility.source.ROR_TREE_SHA1,
            "tree_bytes_sha256": hashlib.sha256(tree_raw).hexdigest(),
            "tree_record_count": len(entries),
            "fixed_rank_seed": RANK_SEED,
            "record_reads": len(fetched),
        },
        "freshness": {
            "historical_visible_entity_count": EXPECTED_HISTORY,
            "historical_canonical_entity_count": EXPECTED_HISTORY,
            "historical_breakdown": {
                "pre_v24750": EXPECTED_BASE_HISTORY,
                "v24750": EXPECTED_V24750,
                "v24760": EXPECTED_V24760,
            },
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
        "claim_scope": {
            "benchmark_external_mechanism_population_only": True,
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
                "output": str(OUTPUT),
                "private": str(PRIVATE),
                "record_reads": len(fetched),
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
