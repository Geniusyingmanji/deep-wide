#!/usr/bin/env python3
"""Run the fresh native-layout mutual partial-signature external gate."""

from __future__ import annotations

import hashlib
import html
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import native_search  # noqa: E402
from deepwide_agent import v24945_injective_schema_signature_ledger as baseline  # noqa: E402
from deepwide_agent import v24949_mutual_partial_signature_ledger as candidate  # noqa: E402
from deepwide_agent import v24951_partial_signature_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as population  # noqa: E402


_INHERITED_BUILD_FORWARD_AUDIT = engine.build_forward_audit


def _rank(iso3: str) -> str:
    return hashlib.sha256(f"{contract.SELECTION_SEED}:{iso3}".encode()).hexdigest()


def _cohorts() -> list[str]:
    values = sorted(
        (f"C{index:02X}" for index in range(256)),
        key=lambda value: (
            hashlib.sha256(f"{contract.COHORT_SEED}:{value}".encode()).hexdigest(),
            value,
        ),
    )
    return values[: contract.SELECTED_COUNT]


def _filler(iso3: str, ordinal: int) -> list[str]:
    return [
        (
            f"partial-archive-{index:02d}-{iso3}-{ordinal:02d}-"
            + hashlib.sha256(
                f"v24951-native-padding:{iso3}:{ordinal}:{index}".encode()
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
    headers = [
        *contract.native_page_columns(),
        *(f"Archive metadata {index}" for index in range(8)),
    ]
    rows: list[list[str]] = []
    for ordinal, (iso3, record) in enumerate(records):
        is_target = ordinal % 2 == 0
        assigned = cohort if is_target else other
        if is_target:
            target_iso3.append(iso3)
        rows.append(
            [record["name"], assigned, iso3, record["value"], *_filler(iso3, ordinal)]
        )
    if len(target_iso3) != contract.ROWS_PER_TASK:
        raise RuntimeError("V2.49.51 task target row denominator drifted")
    raw_html = (
        "<html><body><table><thead><tr>"
        + "".join(f"<th>{html.escape(value)}</th>" for value in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>"
            + "".join(f"<td>{html.escape(value)}</td>" for value in row)
            + "</tr>"
            for row in rows
        )
        + "</tbody></table></body></html>"
    )
    _title, content = native_search.html_to_text(raw_html)
    lines = [line for line in content.splitlines() if line]
    if (
        lines[0].split(" | ") != headers
        or len(lines) != contract.PAGE_ROWS_PER_TASK + 1
        or not 12_000 < len(content) < 80_000
    ):
        raise RuntimeError("V2.49.51 native HTML-to-text layout drifted")
    return {
        "title": "Official agricultural land table",
        "url": contract.TARGET_URLS[0],
        "content": content,
    }, target_iso3


def build_snapshot(
    catalog_blob: bytes, target_blobs: list[bytes]
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    catalog = engine.parse_catalog(catalog_blob)
    if len(target_blobs) != 1:
        raise RuntimeError("V2.49.51 target response vector drifted")
    _source, values = population.parse_target(
        target_blobs[0], dict(contract.TARGETS[0]), contract.TARGET_URLS[0]
    )
    eligible = sorted(
        (
            iso3
            for iso3 in set(catalog).intersection(values)
            if catalog[iso3]["region_id"] not in {"NA", ""}
        ),
        key=lambda iso3: (_rank(iso3), iso3),
    )
    if len(eligible) < contract.SELECTED_RECORD_COUNT:
        raise RuntimeError("V2.49.51 complete record capacity drifted")
    selected = eligible[: contract.SELECTED_RECORD_COUNT]
    target_pool = selected[: contract.SELECTED_ENTITY_COUNT]
    distractor_pool = selected[contract.SELECTED_ENTITY_COUNT :]
    if len(distractor_pool) != contract.DISTRACTOR_ROWS_PER_TASK:
        raise RuntimeError("V2.49.51 distractor denominator drifted")
    pages: list[dict[str, str]] = []
    tasks: list[dict[str, str]] = []
    selected_targets: list[list[str]] = []
    cohorts = _cohorts()
    for index, cohort in enumerate(cohorts):
        target_iso3 = target_pool[
            index * contract.ROWS_PER_TASK : (index + 1) * contract.ROWS_PER_TASK
        ]
        iso3s = [
            value
            for pair in zip(target_iso3, distractor_pool, strict=True)
            for value in pair
        ]
        records = [
            (
                iso3,
                {"name": catalog[iso3]["name"], "value": values[iso3]["value"]},
            )
            for iso3 in iso3s
        ]
        page, task_targets = _task_page(records, cohort, index)
        pages.append(page)
        selected_targets.append(task_targets)
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
            f"v24951:{cohort}:{','.join(iso3s)}".encode()
        ).hexdigest()[:24]
        tasks.append({"opaque_id": opaque, "question": question})
    tasks = contract.validate_task_vector(tasks)
    bundle: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24951_frozen_native_html_to_text_public_pages",
        "pages": pages,
        "target_keys": list(contract.TARGET_KEYS),
        "same_page_vector_for_both_arms": True,
        "page_representation_fixed_before_arm_branch": True,
        "native_html_rendered_then_production_html_to_text": True,
        "task_page_alignment_by_ordinal": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    bundle["bundle_payload_sha256"] = contract.payload_sha256(bundle)
    freeze: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24951_native_layout_snapshot_freeze",
        "catalog_response_sha256": hashlib.sha256(catalog_blob).hexdigest(),
        "target_response_sha256": [hashlib.sha256(target_blobs[0]).hexdigest()],
        "rendered_page_character_counts": [len(page["content"]) for page in pages],
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_records": contract.SELECTED_RECORD_COUNT,
        "selected_target_entities": contract.SELECTED_ENTITY_COUNT,
        "selected_target_iso3_sha256": contract.payload_sha256(selected_targets),
        "cohort_vector_sha256": contract.payload_sha256(cohorts),
        "selection_seed_sha256": hashlib.sha256(
            contract.SELECTION_SEED.encode()
        ).hexdigest(),
        "cohort_seed_sha256": hashlib.sha256(
            contract.COHORT_SEED.encode()
        ).hexdigest(),
        "official_responses_fetched_once_before_arm_branch": True,
        "native_html_to_text_completed_before_arm_branch": True,
        "same_frozen_pages_required_for_both_arms": True,
        "gold_mapping_or_evaluator_created_or_opened": False,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    return bundle, tasks, freeze


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    value = _INHERITED_BUILD_FORWARD_AUDIT(now=now)
    projections = engine._read_jsonl(ROOT / contract.PROJECTIONS)
    parents = [row["projection_receipts"]["parent_30k"] for row in projections]
    candidates = [
        row["projection_receipts"]["target_value_30k"] for row in projections
    ]
    parent_valid = all(
        row.get("role") == "v24951_content_free_full_signature_parent_receipt"
        and row.get("policy_id") == baseline.POLICY_ID
        and row.get("entropy_or_information_gain_assigns_credit") is False
        for row in parents
    )
    candidate_valid = all(
        row.get("role") == "v24951_content_free_partial_signature_candidate_receipt"
        and row.get("policy_id") == candidate.POLICY_ID
        and row.get("entropy_or_information_gain_assigns_credit") is False
        for row in candidates
    )
    parent_observations = sum(
        int(row["admissible_bound_observation_count"]) for row in parents
    )
    admissible = sum(
        int(row["admissible_bound_observation_count"]) for row in candidates
    )
    retained = sum(
        int(row["retained_admissible_bound_observation_count"]) for row in candidates
    )
    discovered = sum(int(row["discovered_row_key_count"]) for row in candidates)
    partial_headers = sum(
        int(row["partial_header_bound_table_count"]) for row in candidates
    )
    gate = engine._read(ROOT / contract.PROTOCOL)["execution"][
        "mechanism_gate_before_evaluator"
    ]
    exposed = (
        parent_observations == int(gate["required_parent_admissible_observations"])
        and admissible >= int(gate["minimum_candidate_admissible_bound_observations"])
        and retained >= int(gate["minimum_candidate_retained_bound_observations"])
        and discovered >= int(gate["minimum_candidate_discovered_row_keys"])
        and partial_headers >= int(gate["minimum_partial_header_bound_tables"])
        and admissible - parent_observations
        >= int(gate["minimum_incremental_target_observations"])
    )
    value["checks"]["parent_receipts_valid"] = parent_valid
    value["checks"]["candidate_receipts_valid"] = candidate_valid
    value["checks"]["partial_signature_candidate_receipts_valid"] = candidate_valid
    value["checks"]["native_layout_partial_signature_mechanism_exposed"] = exposed
    value["mechanism_gate"].update(
        {
            "observed_parent_admissible_bound_observations": parent_observations,
            "observed_candidate_admissible_bound_observations": admissible,
            "observed_candidate_retained_bound_observations": retained,
            "observed_candidate_discovered_row_keys": discovered,
            "observed_partial_header_bound_tables": partial_headers,
            "observed_incremental_target_observations": (
                admissible - parent_observations
            ),
        }
    )
    value["mechanism_gate"]["passed"] = (
        value["mechanism_gate"]["passed"]
        and parent_valid
        and candidate_valid
        and exposed
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
    population.contract = contract
    engine.contract = contract
    engine.parse_target = population.parse_target
    engine.build_snapshot = build_snapshot
    engine.build_forward_audit = build_forward_audit


def main() -> None:
    configure()
    engine.main()


if __name__ == "__main__":
    main()
