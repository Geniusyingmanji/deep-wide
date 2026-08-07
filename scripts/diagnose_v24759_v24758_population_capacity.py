#!/usr/bin/env python3
"""Content-free capacity diagnosis for the failed V2.47.58 design.

The failed design produced no public, private, or visible-contract surface.
This append-only diagnosis replays only the immutable ROR eligibility rule and
publishes aggregate counts.  It never emits an identity, record id, year,
country, page, query, prediction, or benchmark field.
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
from scripts import design_v24758_zero_effect_population as design  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24759_v24758_population_capacity_diagnosis_v1_{DATE}.json")
FAILED_SURFACES = (design.OUTPUT, design.PRIVATE, design.CONTRACT)
CAP_VECTOR = tuple(range(1, 17))
EXPECTED_ELIGIBLE = 1_180
EXPECTED_CANONICAL_UNIQUE = 1_180
EXPECTED_COUNTRY_COUNT = 6
EXPECTED_COUNTRY_COUNT_HISTOGRAM = {"1": 2, "3": 1, "5": 1, "71": 1, "1099": 1}
EXPECTED_FAILED_CAPACITY = 17
EXPECTED_MINIMUM_CAP = 11


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
        raise ValueError("V2.47.59 invalid country-count vector")
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
        raise RuntimeError("V2.47.59 no feasible bounded country cap")
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
    unique = [item for item in eligible if canonical_counts[item["canonical"]] == 1]
    countries = Counter(str(item["country_code"]) for item in unique)
    return len(eligible), len(unique), countries


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
    histogram = Counter(country_counts.values())
    histogram_value = {str(key): histogram[key] for key in sorted(histogram)}
    exact_reproduction = (
        eligible_count == EXPECTED_ELIGIBLE
        and canonical_unique_count == EXPECTED_CANONICAL_UNIQUE
        and len(country_counts) == EXPECTED_COUNTRY_COUNT
        and histogram_value == EXPECTED_COUNTRY_COUNT_HISTOGRAM
        and curve[str(design.COUNTRY_CAP)] == EXPECTED_FAILED_CAPACITY
        and minimum == EXPECTED_MINIMUM_CAP
    )
    value = {
        "artifact_version": 1,
        "role": "v24759_v24758_population_capacity_diagnosis",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parents": {
            "v24757_build_audit_sha256": sha256(ROOT / design.PARENT),
            "v24758_design_source_sha256": sha256(
                ROOT / "scripts/design_v24758_zero_effect_population.py"
            ),
            "v24758_design_test_sha256": sha256(
                ROOT / "tests/test_design_v24758_zero_effect_population.py"
            ),
        },
        "failed_publication": {
            "stage": "deterministic_population_capacity_check",
            "all_v24758_output_surfaces_pristine": all(
                not (ROOT / path).exists() and not (ROOT / path).is_symlink()
                for path in FAILED_SURFACES
            ),
            "required_selected_entity_count": design.SELECTED_COUNT,
            "failed_country_cap": design.COUNTRY_CAP,
            "failed_cap_capacity": curve[str(design.COUNTRY_CAP)],
            "network_model_search_benchmark_or_evaluator_effect_before_failure": False,
            "identity_record_id_year_country_question_or_prediction_emitted": False,
        },
        "immutable_source": {
            "commit": design.source.ROR_COMMIT,
            "version": design.source.ROR_VERSION,
            "tree_sha1": design.source.ROR_TREE_SHA1,
            "tree_bytes_sha256": tree_bytes_sha256,
            "tree_record_count": tree_record_count,
            "historical_entity_count": design.EXPECTED_HISTORY,
            "eligibility_or_rank_rule_changed_during_diagnosis": False,
        },
        "content_free_capacity": {
            "eligible_record_count": eligible_count,
            "canonical_unique_candidate_count": canonical_unique_count,
            "eligible_country_count": len(country_counts),
            "country_candidate_count_histogram": histogram_value,
            "cap_vector": list(CAP_VECTOR),
            "capacity_by_cap": curve,
            "minimum_feasible_cap": minimum,
            "exact_v24758_failure_reproduced": exact_reproduction,
        },
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "identity_record_id_year_country_or_page_persisted": False,
            "quality_or_search_outcome_used_for_capacity_repair": False,
        },
        "authorization": {
            "fresh_v24760_population_design": exact_reproduction,
            "repaired_country_cap": minimum,
            "population_and_inert_protocol_publication_only": exact_reproduction,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "evaluator": False,
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
    source_value = copied.get("immutable_source", {})
    capacity = copied.get("content_free_capacity", {})
    curve = capacity.get("capacity_by_cap", {})
    minimum = minimum_feasible_cap(curve) if isinstance(curve, Mapping) else -1
    if (
        copied.get("role") != "v24759_v24758_population_capacity_diagnosis"
        or failed.get("stage") != "deterministic_population_capacity_check"
        or failed.get("all_v24758_output_surfaces_pristine") is not True
        or failed.get("required_selected_entity_count") != design.SELECTED_COUNT
        or failed.get("failed_country_cap") != design.COUNTRY_CAP
        or failed.get("failed_cap_capacity") != EXPECTED_FAILED_CAPACITY
        or failed.get("failed_cap_capacity", design.SELECTED_COUNT)
        >= design.SELECTED_COUNT
        or failed.get(
            "network_model_search_benchmark_or_evaluator_effect_before_failure"
        )
        is not False
        or failed.get(
            "identity_record_id_year_country_question_or_prediction_emitted"
        )
        is not False
        or source_value.get("commit") != design.source.ROR_COMMIT
        or source_value.get("version") != design.source.ROR_VERSION
        or source_value.get("tree_sha1") != design.source.ROR_TREE_SHA1
        or source_value.get("tree_record_count") != 3_482
        or source_value.get("historical_entity_count") != design.EXPECTED_HISTORY
        or source_value.get("eligibility_or_rank_rule_changed_during_diagnosis")
        is not False
        or capacity.get("eligible_record_count") != EXPECTED_ELIGIBLE
        or capacity.get("canonical_unique_candidate_count")
        != EXPECTED_CANONICAL_UNIQUE
        or capacity.get("eligible_country_count") != EXPECTED_COUNTRY_COUNT
        or capacity.get("country_candidate_count_histogram")
        != EXPECTED_COUNTRY_COUNT_HISTOGRAM
        or capacity.get("cap_vector") != list(CAP_VECTOR)
        or capacity.get("minimum_feasible_cap") != minimum
        or minimum != EXPECTED_MINIMUM_CAP
        or capacity.get("exact_v24758_failure_reproduced") is not True
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "fresh_v24760_population_design": True,
            "repaired_country_cap": EXPECTED_MINIMUM_CAP,
            "population_and_inert_protocol_publication_only": True,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.59 capacity diagnosis drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.59 diagnosis requires clean pushed HEAD")
    if not design._parent_valid():
        raise RuntimeError("V2.47.59 parent build audit drifted")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in FAILED_SURFACES
    ):
        raise RuntimeError("V2.47.59 failed surfaces are not pristine")
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)

    tree_raw = design.source._fetch(
        design.source.ROR_TREE_URL, limit=design.source.MAX_ROR_TREE_BYTES
    )
    entries = design.ranked_entries(tree_raw)
    records = design.fetch_records(entries)
    _visible, historical_canonical = design.historical_entities()
    normalizer = design.source.ror_base.history.population._canonical_entity
    eligible, unique, countries = candidate_counts(
        records,
        historical_canonical=historical_canonical,
        canonical=normalizer,
    )
    diagnosis = build_diagnosis(
        eligible_count=eligible,
        canonical_unique_count=unique,
        country_counts=countries,
        tree_bytes_sha256=hashlib.sha256(tree_raw).hexdigest(),
        tree_record_count=len(entries),
        now=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    _publish(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "exact_failure_reproduced": diagnosis["content_free_capacity"][
                    "exact_v24758_failure_reproduced"
                ],
                "failed_cap_capacity": diagnosis["failed_publication"][
                    "failed_cap_capacity"
                ],
                "minimum_feasible_cap": diagnosis["content_free_capacity"][
                    "minimum_feasible_cap"
                ],
                "output": str(OUTPUT),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
