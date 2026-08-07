#!/usr/bin/env python3
"""Append-only capacity diagnosis for the failed V2.47.87 population.

V2.47.87 consumed one immutable ROR v2.11 tree read and 3,482 immutable
record reads, then failed its fixed country-cap-8 selection before any public,
private, or visible-contract surface was created.  This diagnosis repeats the
same public source reads and eligibility/rank rule only to publish aggregate
capacity counts and the minimum feasible country cap.  It emits no identity,
record ID, field value, country label, question, URL, page, or prediction.
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
from scripts import design_v24787_cross_tab_population as design  # noqa: E402


DATE = "20260807"
OUTPUT = Path(f"results/v24788_v24787_population_capacity_diagnosis_v1_{DATE}.json")
FAILED_SURFACES = (design.OUTPUT, design.PRIVATE, design.CONTRACT)
CAP_VECTOR = tuple(range(1, 33))


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capacity_curve(country_counts: Mapping[str, int]) -> dict[str, int]:
    if (
        not country_counts
        or any(
            not isinstance(country, str)
            or not country
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
            for country, amount in country_counts.items()
        )
    ):
        raise ValueError("V2.47.88 invalid country-count vector")
    return {
        str(cap): sum(min(cap, amount) for amount in country_counts.values())
        for cap in CAP_VECTOR
    }


def minimum_feasible_cap(curve: Mapping[str, int]) -> int:
    feasible = [
        cap
        for cap in CAP_VECTOR
        if curve.get(str(cap), -1) >= design.SELECTED_COUNT
    ]
    if not feasible:
        raise RuntimeError("V2.47.88 no feasible bounded country cap")
    return min(feasible)


def candidate_counts(
    records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
) -> tuple[int, int, Counter[str]]:
    eligible = [
        candidate
        for path, blob, raw, value in records
        if (
            candidate := design.record_candidate(
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
    unique = [
        item for item in eligible if canonical_counts[str(item["canonical"])] == 1
    ]
    return (
        len(eligible),
        len(unique),
        Counter(str(item["country_code"]) for item in unique),
    )


def build_diagnosis(
    *,
    eligible_count: int,
    canonical_unique_count: int,
    country_counts: Mapping[str, int],
    tree_bytes_sha256: str,
    tree_record_count: int,
    now: int,
    git_head: str,
) -> dict[str, Any]:
    curve = capacity_curve(country_counts)
    minimum = minimum_feasible_cap(curve)
    failed_capacity = curve[str(design.COUNTRY_CAP)]
    histogram = Counter(country_counts.values())
    reproduced = (
        eligible_count >= canonical_unique_count >= design.SELECTED_COUNT
        and failed_capacity < design.SELECTED_COUNT
        and minimum > design.COUNTRY_CAP
        and tree_record_count == design.EXPECTED_TREE_RECORDS
    )
    value = {
        "artifact_version": 1,
        "role": "v24788_v24787_population_capacity_diagnosis",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parents": {
            "v24786_build_audit_sha256": sha256(ROOT / design.PARENT),
            "v24787_design_source_sha256": sha256(
                ROOT / "scripts/design_v24787_cross_tab_population.py"
            ),
            "v24787_design_test_sha256": sha256(
                ROOT / "tests/test_design_v24787_cross_tab_population.py"
            ),
        },
        "failed_publication": {
            "stage": "deterministic_population_capacity_check",
            "all_v24787_output_surfaces_pristine": all(
                not (ROOT / path).exists() and not (ROOT / path).is_symlink()
                for path in FAILED_SURFACES
            ),
            "required_selected_entity_count": design.SELECTED_COUNT,
            "failed_country_cap": design.COUNTRY_CAP,
            "failed_cap_capacity": failed_capacity,
            "first_attempt_immutable_ror_tree_reads_before_failure": 1,
            "first_attempt_immutable_ror_record_reads_before_failure": tree_record_count,
            "diagnosis_immutable_ror_tree_reads": 1,
            "diagnosis_immutable_ror_record_reads": tree_record_count,
            "cumulative_v24787_plus_v24788_tree_reads": 2,
            "cumulative_v24787_plus_v24788_record_reads": 2 * tree_record_count,
            "model_search_benchmark_forward_or_evaluator_calls": 0,
            "identity_record_id_field_value_country_question_url_page_or_prediction_emitted": False,
        },
        "immutable_source": {
            "commit": design.base.source.ROR_COMMIT,
            "version": design.base.source.ROR_VERSION,
            "tree_sha1": design.base.source.ROR_TREE_SHA1,
            "tree_bytes_sha256": tree_bytes_sha256,
            "tree_record_count": tree_record_count,
            "historical_visible_and_canonical_entity_count": design.EXPECTED_HISTORY,
            "eligibility_or_rank_rule_changed_during_diagnosis": False,
        },
        "content_free_capacity": {
            "eligible_record_count": eligible_count,
            "canonical_unique_candidate_count": canonical_unique_count,
            "eligible_country_count": len(country_counts),
            "country_candidate_count_histogram": {
                str(key): histogram[key] for key in sorted(histogram)
            },
            "cap_vector": list(CAP_VECTOR),
            "capacity_by_cap": curve,
            "minimum_feasible_cap": minimum,
            "exact_v24787_failure_reproduced": reproduced,
        },
        "source_policy": {
            "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "identity_record_id_field_value_country_question_url_page_or_prediction_persisted": False,
            "quality_or_search_outcome_used_for_capacity_repair": False,
        },
        "authorization": {
            "append_only_fresh_population_successor_design": reproduced,
            "repaired_country_cap": minimum,
            "population_and_inert_protocol_publication_only": reproduced,
            "same_seed_retry_resume_or_supplement": False,
            "trusted_child_integration_or_runner_build": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_or_evaluator_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    failed = copied.get("failed_publication", {})
    source = copied.get("immutable_source", {})
    capacity = copied.get("content_free_capacity", {})
    curve = capacity.get("capacity_by_cap", {})
    minimum = minimum_feasible_cap(curve) if isinstance(curve, Mapping) else -1
    if (
        copied.get("role") != "v24788_v24787_population_capacity_diagnosis"
        or failed.get("stage") != "deterministic_population_capacity_check"
        or failed.get("all_v24787_output_surfaces_pristine") is not True
        or failed.get("required_selected_entity_count") != design.SELECTED_COUNT
        or failed.get("failed_country_cap") != design.COUNTRY_CAP
        or not isinstance(failed.get("failed_cap_capacity"), int)
        or failed.get("failed_cap_capacity") >= design.SELECTED_COUNT
        or failed.get("first_attempt_immutable_ror_tree_reads_before_failure") != 1
        or failed.get("first_attempt_immutable_ror_record_reads_before_failure")
        != design.EXPECTED_TREE_RECORDS
        or failed.get("diagnosis_immutable_ror_tree_reads") != 1
        or failed.get("diagnosis_immutable_ror_record_reads")
        != design.EXPECTED_TREE_RECORDS
        or failed.get("cumulative_v24787_plus_v24788_tree_reads") != 2
        or failed.get("cumulative_v24787_plus_v24788_record_reads")
        != 2 * design.EXPECTED_TREE_RECORDS
        or failed.get("model_search_benchmark_forward_or_evaluator_calls") != 0
        or failed.get(
            "identity_record_id_field_value_country_question_url_page_or_prediction_emitted"
        )
        is not False
        or source.get("commit") != design.base.source.ROR_COMMIT
        or source.get("version") != design.base.source.ROR_VERSION
        or source.get("tree_sha1") != design.base.source.ROR_TREE_SHA1
        or source.get("tree_record_count") != design.EXPECTED_TREE_RECORDS
        or source.get("historical_visible_and_canonical_entity_count")
        != design.EXPECTED_HISTORY
        or source.get("eligibility_or_rank_rule_changed_during_diagnosis") is not False
        or capacity.get("canonical_unique_candidate_count", 0) < design.SELECTED_COUNT
        or capacity.get("cap_vector") != list(CAP_VECTOR)
        or capacity.get("minimum_feasible_cap") != minimum
        or minimum <= design.COUNTRY_CAP
        or capacity.get("exact_v24787_failure_reproduced") is not True
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization", {}).get(
            "append_only_fresh_population_successor_design"
        )
        is not True
        or copied.get("authorization", {}).get("repaired_country_cap") != minimum
        or any(
            copied.get("authorization", {}).get(key) is not False
            for key in (
                "same_seed_retry_resume_or_supplement",
                "trusted_child_integration_or_runner_build",
                "preactivation_audit",
                "activation_or_external_launch",
                "quality_or_evaluator_surface_open",
                "paired_dev64",
                "exact220",
                "entropy_or_credit_experiment",
                "leaderboard_or_sota",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.88 capacity diagnosis drifted")
    return copied


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
        raise RuntimeError("V2.47.88 diagnosis requires clean pushed HEAD")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in FAILED_SURFACES
    ):
        raise RuntimeError("V2.47.87 failed surfaces are not pristine")
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)

    tree_raw = design.base.source._fetch(
        design.base.source.ROR_TREE_URL,
        limit=design.base.source.MAX_ROR_TREE_BYTES,
    )
    entries = design.ranked_entries(tree_raw)
    records = design.fetch_records(entries)
    _visible, historical_canonical = design.historical_entities()
    eligible_count, canonical_unique_count, countries = candidate_counts(
        records,
        historical_canonical=historical_canonical,
        canonical=design._normalizer(),
    )
    value = build_diagnosis(
        eligible_count=eligible_count,
        canonical_unique_count=canonical_unique_count,
        country_counts=countries,
        tree_bytes_sha256=hashlib.sha256(tree_raw).hexdigest(),
        tree_record_count=len(entries),
        now=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    raw = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    _publish(path, raw)
    print(
        json.dumps(
            {
                "failed_capacity": value["failed_publication"][
                    "failed_cap_capacity"
                ],
                "minimum_feasible_cap": value["content_free_capacity"][
                    "minimum_feasible_cap"
                ],
                "output": str(OUTPUT),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
