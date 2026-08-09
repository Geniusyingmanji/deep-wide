#!/usr/bin/env python3
"""Run the frozen V2.49.34 contextual-record shared-prefix gate once."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24934_contextual_record_external_contract as contract  # noqa: E402
from deepwide_agent import v24921_target_value_coverage_projector as target_value  # noqa: E402
from deepwide_agent import v24928_unicode_total_visible_row_compactor as unicode_total  # noqa: E402
from deepwide_agent import v24933_contextual_record_value_projector as candidate  # noqa: E402
from scripts import run_v24923_target_value_external as base  # noqa: E402


_INHERITED_BUILD_FORWARD_AUDIT = base.build_forward_audit


def parse_target(
    blob: bytes, target: dict[str, str], url: str
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Render one official response as ordinary section/record text."""

    value = json.loads(blob)
    records = value[1] if isinstance(value, list) and len(value) == 2 else None
    if not isinstance(records, list):
        raise RuntimeError("V2.49.34 target response schema drifted")
    rows: list[tuple[str, str, str]] = []
    values: dict[str, dict[str, str]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("value") is None:
            continue
        country = record.get("country") or {}
        name = str(country.get("value", "")).strip()
        iso3 = str(record.get("countryiso3code", "")).strip().upper()
        if not name or len(iso3) != 3 or iso3 in values:
            continue
        rendered = str(record["value"])
        rows.append((name, iso3, rendered))
        values[iso3] = {"name": name, "value": rendered}
    if len(values) < 170:
        raise RuntimeError("V2.49.34 target response capacity drifted")
    coverage = "\n".join(f"- {name} [{iso3}]" for name, iso3, _value in rows)
    observations = "\n".join(
        f"{name} [{iso3}]: {rendered}" for name, iso3, rendered in rows
    )
    content = (
        "# Country coverage index\n\n"
        + coverage
        + "\n\n# "
        + f"{target['label']} [{target['indicator']}] @{target['year']}"
        + " official observations\n\n"
        + observations
    )
    if not 8_000 < len(content) <= 30_000:
        raise RuntimeError("V2.49.34 rendered ordinary-text page capacity drifted")
    return {
        "title": f"World Bank official indicator {target['indicator']} {target['year']}",
        "url": url,
        "content": content,
    }, values


def build_visible_tasks(
    catalog: dict[str, dict[str, str]],
    values: list[dict[str, dict[str, str]]],
) -> list[dict[str, str]]:
    common = set(catalog).intersection(*(set(value) for value in values))
    eligible = sorted(
        (
            iso3
            for iso3 in common
            if catalog[iso3]["region_id"] not in {"NA", ""}
        ),
        key=lambda iso3: (
            hashlib.sha256(
                f"{contract.SELECTION_SEED}:{iso3}".encode()
            ).hexdigest(),
            iso3,
        ),
    )
    if len(eligible) < contract.SELECTED_ENTITY_COUNT:
        raise RuntimeError("V2.49.34 complete entity capacity drifted")
    selected = eligible[: contract.SELECTED_ENTITY_COUNT]
    columns = contract.visible_columns()
    tasks = []
    for index in range(contract.SELECTED_COUNT):
        group = selected[
            index * contract.ROWS_PER_TASK : (index + 1) * contract.ROWS_PER_TASK
        ]
        entities = "\n".join(
            f"{ordinal}. {catalog[iso3]['name']} [{iso3}]"
            for ordinal, iso3 in enumerate(group, 1)
        )
        question = (
            "Return exactly one Markdown table and no prose. Column names: "
            + " | ".join(columns)
            + ". Include exactly the requested entity rows in the visible order. "
            "Preserve numeric decimal spelling shown in supplied official pages; "
            "use Unknown only if absent.\n<ENTITIES>\n"
            + entities
            + "\n</ENTITIES>"
        )
        opaque = "task_" + hashlib.sha256(
            f"v24934:{','.join(group)}".encode()
        ).hexdigest()[:24]
        tasks.append({"opaque_id": opaque, "question": question})
    return contract.validate_task_vector(tasks)


def build_snapshot(
    catalog_blob: bytes, target_blobs: list[bytes]
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    catalog = base.parse_catalog(catalog_blob)
    pages = []
    values = []
    for blob, target, url in zip(
        target_blobs, contract.TARGETS, contract.TARGET_URLS, strict=True
    ):
        page, target_values = parse_target(blob, dict(target), url)
        pages.append(page)
        values.append(target_values)
    tasks = build_visible_tasks(catalog, values)
    bundle: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24934_frozen_shared_ordinary_text_pages",
        "pages": pages,
        "target_keys": list(contract.TARGET_KEYS),
        "same_page_vector_for_both_arms": True,
        "page_representation_fixed_before_arm_branch": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    bundle["bundle_payload_sha256"] = contract.payload_sha256(bundle)
    freeze: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24934_snapshot_freeze",
        "catalog_response_sha256": hashlib.sha256(catalog_blob).hexdigest(),
        "target_response_sha256": [
            hashlib.sha256(blob).hexdigest() for blob in target_blobs
        ],
        "rendered_page_character_counts": [len(page["content"]) for page in pages],
        "complete_entity_intersection": len(
            set(catalog).intersection(*(set(value) for value in values))
        ),
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_entities": contract.SELECTED_ENTITY_COUNT,
        "selection_seed_sha256": hashlib.sha256(
            contract.SELECTION_SEED.encode()
        ).hexdigest(),
        "official_responses_fetched_once_before_arm_branch": True,
        "same_frozen_pages_required_for_both_arms": True,
        "gold_mapping_or_evaluator_created_or_opened": False,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    return bundle, tasks, freeze


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    """Validate inherited invariants and native V2.49.34 receipt identities."""

    inherited_read_jsonl = base._read_jsonl

    def compatible_read_jsonl(path: Path) -> list[dict[str, Any]]:
        rows = inherited_read_jsonl(path)
        if path.resolve() != (ROOT / contract.PROJECTIONS).resolve():
            return rows
        projected = copy.deepcopy(rows)
        for row in projected:
            receipts = row.get("projection_receipts") or {}
            parent_receipt = receipts.get("parent_30k") or {}
            candidate_receipt = receipts.get("target_value_30k") or {}
            receipts["parent_30k"] = {
                **parent_receipt,
                "role": "v24846_content_free_projection_receipt",
                "orphan_selected_table_continuation_block_count": 0,
            }
            native = candidate_receipt.get("candidate_receipt") or {}
            receipts["target_value_30k"] = {
                **candidate_receipt,
                "role": "v24921_content_free_target_value_coverage_receipt",
                "orphan_selected_table_continuation_block_count": int(
                    native.get(
                        "orphan_selected_table_continuation_block_count", -1
                    )
                ),
            }
        return projected

    base._read_jsonl = compatible_read_jsonl
    try:
        value = _INHERITED_BUILD_FORWARD_AUDIT(now=now)
    finally:
        base._read_jsonl = inherited_read_jsonl

    rows = inherited_read_jsonl(ROOT / contract.PROJECTIONS)
    parent_receipts = [
        (row.get("projection_receipts") or {}).get("parent_30k") or {}
        for row in rows
    ]
    candidate_receipts = [
        (row.get("projection_receipts") or {}).get("target_value_30k") or {}
        for row in rows
    ]

    def wrapper_sealed(receipt: dict[str, Any]) -> bool:
        unsigned = dict(receipt)
        seal = unsigned.pop("receipt_payload_sha256", None)
        return seal == contract.payload_sha256(unsigned)

    native_checks = {
        "native_projection_denominator_exact": len(rows) == contract.SELECTED_COUNT,
        "native_parent_receipts_valid": all(
            receipt.get("role")
            == "v24934_content_free_unicode_total_baseline_receipt"
            and receipt.get("policy_id") == unicode_total.POLICY_ID
            and wrapper_sealed(receipt)
            and target_value.validate_receipt(receipt["projection_receipt"])
            == receipt["projection_receipt"]
            and unicode_total.validate_receipt(receipt["compaction_receipt"])
            == receipt["compaction_receipt"]
            for receipt in parent_receipts
        ),
        "native_candidate_receipts_valid": all(
            receipt.get("role")
            == "v24934_content_free_contextual_candidate_receipt"
            and receipt.get("policy_id") == candidate.POLICY_ID
            and wrapper_sealed(receipt)
            and candidate.validate_receipt(receipt["candidate_receipt"])
            == receipt["candidate_receipt"]
            for receipt in candidate_receipts
        ),
        "arm_algorithm_identity_bound": contract.ARMS
        == ("parent_30k", "target_value_30k"),
    }
    contextual_supported = sum(
        int(receipt.get("supported_contextual_target_value_pair_count", 0))
        for receipt in candidate_receipts
    )
    contextual_retained = sum(
        int(receipt.get("retained_contextual_target_value_pair_count", 0))
        for receipt in candidate_receipts
    )
    protocol = base._read(ROOT / contract.PROTOCOL)
    contextual_minimum = int(
        protocol["execution"]["mechanism_gate_before_evaluator"]
        ["minimum_retained_contextual_target_value_pairs"]
    )
    native_checks["contextual_pair_mechanism_gate"] = (
        contextual_retained >= contextual_minimum
    )
    value["checks"].update(native_checks)
    value["findings"] = sorted(
        name for name, passed in value["checks"].items() if not passed
    )
    value["role"] = "v24934_contextual_record_external_forward_audit"
    value["created_at_unix"] = int(time.time()) if now is None else int(now)
    value["inherited_harness_role_adapter"] = {
        "base": "v24923_target_value_external_forward_audit",
        "native_protocol_id": contract.PROTOCOL_ID,
        "parent_algorithm": unicode_total.POLICY_ID,
        "candidate_algorithm": candidate.POLICY_ID,
    }
    value["mechanism_gate"].update(
        {
            "minimum_retained_contextual_target_value_pairs": contextual_minimum,
            "observed_supported_contextual_target_value_pairs": contextual_supported,
            "observed_retained_contextual_target_value_pairs": contextual_retained,
        }
    )
    value["mechanism_gate"]["passed"] = (
        value["mechanism_gate"]["passed"]
        and native_checks["contextual_pair_mechanism_gate"]
    )
    value["audit_valid"] = not value["findings"]
    value["authorization"]["postfreeze_external_evaluator_protocol"] = (
        value["audit_valid"] and value["mechanism_gate"]["passed"]
    )
    value.pop("audit_payload_sha256", None)
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def configure() -> None:
    base.contract = contract
    base.parse_target = parse_target
    base.build_visible_tasks = build_visible_tasks
    base.build_snapshot = build_snapshot
    base.build_forward_audit = build_forward_audit


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
