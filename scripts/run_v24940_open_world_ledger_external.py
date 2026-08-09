#!/usr/bin/env python3
"""Freeze public records and run V2.49.40 exactly once."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24939_schema_bound_record_ledger as candidate  # noqa: E402
from deepwide_agent import v24940_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402


_INHERITED_BUILD_FORWARD_AUDIT = engine.build_forward_audit


def parse_target(
    blob: bytes, target: dict[str, str], url: str
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    value = json.loads(blob)
    records = value[1] if isinstance(value, list) and len(value) == 2 else None
    if not isinstance(records, list):
        raise RuntimeError("V2.49.40 target response schema drifted")
    values: dict[str, dict[str, str]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("value") is None:
            continue
        country = record.get("country") or {}
        name = str(country.get("value", "")).strip()
        iso3 = str(record.get("countryiso3code", "")).strip().upper()
        if not name or len(iso3) != 3 or iso3 in values:
            continue
        values[iso3] = {"name": name, "value": str(record["value"])}
    if len(values) < contract.SELECTED_RECORD_COUNT:
        raise RuntimeError("V2.49.40 target response capacity drifted")
    return {
        "title": f"World Bank official indicator {target['indicator']} {target['year']}",
        "url": url,
        "content": "source response frozen before deterministic task transform",
    }, values


def _rank(iso3: str) -> str:
    return hashlib.sha256(
        f"{contract.SELECTION_SEED}:{iso3}".encode("utf-8")
    ).hexdigest()


def _cohorts() -> list[str]:
    values = sorted(
        (f"C{index:02X}" for index in range(256)),
        key=lambda value: (
            hashlib.sha256(
                f"{contract.COHORT_SEED}:{value}".encode("utf-8")
            ).hexdigest(),
            value,
        ),
    )
    return values[: contract.SELECTED_COUNT]


def _filler(iso3: str, ordinal: int) -> list[str]:
    # Public-derived record rows are intentionally wider than the inherited
    # 5k/page cap.  Fixed, content-free padding creates a hard projection task
    # without adding hidden labels or evaluator information.
    return [
        (
            f"archive-field-{index:02d}-{iso3}-{ordinal:02d}-"
            + hashlib.sha256(
                f"v24940-padding:{iso3}:{ordinal}:{index}".encode("utf-8")
            ).hexdigest()
            + "-public-record-provenance"
        )
        for index in range(8)
    ]


def _task_page(
    records: list[tuple[str, dict[str, str]]], cohort: str, task_index: int
) -> tuple[dict[str, str], list[str]]:
    other = f"X{task_index:02X}"
    target_iso3: list[str] = []
    headers = [*contract.visible_columns(), *(f"Archive metadata {index}" for index in range(8))]
    lines = [" | ".join(headers)]
    for ordinal, (iso3, record) in enumerate(records):
        is_target = ordinal % 2 == 0
        assigned = cohort if is_target else other
        if is_target:
            target_iso3.append(iso3)
        lines.append(
            " | ".join(
                [
                    record["name"],
                    assigned,
                    iso3,
                    record["value"],
                    *_filler(iso3, ordinal),
                ]
            )
        )
    if len(target_iso3) != contract.ROWS_PER_TASK:
        raise RuntimeError("V2.49.40 task target row denominator drifted")
    content = "\n".join(lines)
    if not 12_000 < len(content) < 80_000:
        raise RuntimeError("V2.49.40 task page capacity drifted")
    target = contract.TARGETS[0]
    return {
        "title": f"Frozen public-derived {target['indicator']} cohort page {task_index:02d}",
        "url": contract.TARGET_URLS[0],
        "content": content,
    }, target_iso3


def build_snapshot(
    catalog_blob: bytes, target_blobs: list[bytes]
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    catalog = engine.parse_catalog(catalog_blob)
    if len(target_blobs) != 1:
        raise RuntimeError("V2.49.40 target response vector drifted")
    _source_page, target_values = parse_target(
        target_blobs[0], dict(contract.TARGETS[0]), contract.TARGET_URLS[0]
    )
    eligible = sorted(
        (
            iso3
            for iso3 in set(catalog).intersection(target_values)
            if catalog[iso3]["region_id"] not in {"NA", ""}
        ),
        key=lambda iso3: (_rank(iso3), iso3),
    )
    if len(eligible) < contract.SELECTED_RECORD_COUNT:
        raise RuntimeError("V2.49.40 complete record capacity drifted")
    selected = eligible[: contract.SELECTED_RECORD_COUNT]
    cohorts = _cohorts()
    pages: list[dict[str, str]] = []
    tasks: list[dict[str, str]] = []
    selected_targets: list[list[str]] = []
    target_pool = selected[: contract.SELECTED_ENTITY_COUNT]
    distractor_pool = selected[contract.SELECTED_ENTITY_COUNT :]
    if len(distractor_pool) != contract.DISTRACTOR_ROWS_PER_TASK:
        raise RuntimeError("V2.49.40 distractor pool denominator drifted")
    for index, cohort in enumerate(cohorts):
        target_iso3s = target_pool[
            index * contract.ROWS_PER_TASK :
            (index + 1) * contract.ROWS_PER_TASK
        ]
        iso3s = [
            value
            for pair in zip(target_iso3s, distractor_pool, strict=True)
            for value in pair
        ]
        rows = [
            (
                iso3,
                {
                    "name": catalog[iso3]["name"],
                    "value": target_values[iso3]["value"],
                },
            )
            for iso3 in iso3s
        ]
        page, target_iso3 = _task_page(rows, cohort, index)
        pages.append(page)
        selected_targets.append(target_iso3)
        question = (
            "From the supplied frozen page, include every record whose Cohort is "
            + cohort
            + ". Do not include other cohorts. Return exactly one Markdown table "
            "and no prose.\nColumn names: "
            + " | ".join(contract.visible_columns())
            + "\nOutput format: table only. The visible Cohort predicate is "
            + cohort
            + "."
        )
        opaque = "task_" + hashlib.sha256(
            f"v24940:{cohort}:{','.join(iso3s)}".encode("utf-8")
        ).hexdigest()[:24]
        tasks.append({"opaque_id": opaque, "question": question})
    tasks = contract.validate_task_vector(tasks)
    bundle: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24940_frozen_open_world_public_derived_pages",
        "pages": pages,
        "target_keys": list(contract.TARGET_KEYS),
        "same_page_vector_for_both_arms": True,
        "page_representation_fixed_before_arm_branch": True,
        "task_page_alignment_by_ordinal": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    bundle["bundle_payload_sha256"] = contract.payload_sha256(bundle)
    freeze: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24940_snapshot_freeze",
        "catalog_response_sha256": hashlib.sha256(catalog_blob).hexdigest(),
        "target_response_sha256": [hashlib.sha256(target_blobs[0]).hexdigest()],
        "rendered_page_character_counts": [len(page["content"]) for page in pages],
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_records": contract.SELECTED_RECORD_COUNT,
        "selected_target_entities": contract.SELECTED_ENTITY_COUNT,
        "selected_target_iso3_sha256": contract.payload_sha256(selected_targets),
        "cohort_vector_sha256": contract.payload_sha256(cohorts),
        "selection_seed_sha256": hashlib.sha256(
            contract.SELECTION_SEED.encode("utf-8")
        ).hexdigest(),
        "cohort_seed_sha256": hashlib.sha256(
            contract.COHORT_SEED.encode("utf-8")
        ).hexdigest(),
        "official_responses_fetched_once_before_arm_branch": True,
        "same_frozen_pages_required_for_both_arms": True,
        "gold_mapping_or_evaluator_created_or_opened": False,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    return bundle, tasks, freeze


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    value = _INHERITED_BUILD_FORWARD_AUDIT(now=now)
    projections = engine._read_jsonl(ROOT / contract.PROJECTIONS)
    candidate_receipts = [
        row["projection_receipts"]["target_value_30k"]
        for row in projections
    ]
    admissible = sum(
        int(row["admissible_bound_observation_count"])
        for row in candidate_receipts
    )
    retained = sum(
        int(row["retained_admissible_bound_observation_count"])
        for row in candidate_receipts
    )
    discovered = sum(int(row["discovered_row_key_count"]) for row in candidate_receipts)
    value["mechanism_gate"].update(
        {
            "observed_admissible_bound_observations": admissible,
            "observed_retained_admissible_bound_observations": retained,
            "observed_discovered_row_keys": discovered,
        }
    )
    protocol = engine._read(ROOT / contract.PROTOCOL)
    gate = protocol["execution"]["mechanism_gate_before_evaluator"]
    value["checks"]["schema_bound_candidate_receipts_valid"] = all(
        row.get("role") == "v24940_content_free_schema_bound_candidate_receipt"
        and row.get("policy_id") == candidate.POLICY_ID
        and row.get("entropy_or_information_gain_assigns_credit") is False
        for row in candidate_receipts
    )
    value["checks"]["candidate_receipts_valid"] = value["checks"][
        "schema_bound_candidate_receipts_valid"
    ]
    value["checks"]["parent_receipts_valid"] = all(
        row.get("role") == "v24940_content_free_contextual_parent_receipt"
        and row.get("entropy_or_information_gain_assigns_credit") is False
        for row in (
            projection["projection_receipts"]["parent_30k"]
            for projection in projections
        )
    )
    value["checks"]["open_world_ledger_mechanism_exposed"] = (
        admissible >= int(gate["minimum_admissible_bound_observations"])
        and retained >= int(gate["minimum_retained_admissible_bound_observations"])
        and discovered >= int(gate["minimum_discovered_row_keys"])
    )
    value["mechanism_gate"]["passed"] = (
        value["mechanism_gate"]["passed"]
        and value["checks"]["schema_bound_candidate_receipts_valid"]
        and value["checks"]["open_world_ledger_mechanism_exposed"]
    )
    value["findings"] = sorted(
        name for name, passed in value["checks"].items() if not passed
    )
    value["audit_valid"] = not value["findings"]
    value["authorization"]["postfreeze_external_evaluator_protocol"] = (
        value["audit_valid"] and value["mechanism_gate"]["passed"]
    )
    value.pop("audit_payload_sha256", None)
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def configure() -> None:
    engine.contract = contract
    engine.parse_target = parse_target
    engine.build_snapshot = build_snapshot
    engine.build_forward_audit = build_forward_audit


def main() -> None:
    configure()
    engine.main()


if __name__ == "__main__":
    main()
