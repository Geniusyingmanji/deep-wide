#!/usr/bin/env python3
"""Run the fresh V2.49.37 layout-diverse contextual-record gate once."""

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

from deepwide_agent import v24937_layout_diverse_contextual_external_contract as contract  # noqa: E402
from deepwide_agent import v24933_contextual_record_value_projector as candidate  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24934_contextual_record_external as parent  # noqa: E402


_INHERITED_BUILD_FORWARD_AUDIT = parent.build_forward_audit


def parse_target(
    blob: bytes, target: dict[str, str], url: str
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    value = json.loads(blob)
    records = value[1] if isinstance(value, list) and len(value) == 2 else None
    if not isinstance(records, list):
        raise RuntimeError("V2.49.37 target response schema drifted")
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
        raise RuntimeError("V2.49.37 target response capacity drifted")
    coverage = "\n".join(f"- {name} [{iso3}]" for name, iso3, _value in rows)
    target_label = f"{target['label']} [{target['indicator']}] @{target['year']}"
    if target["layout"] == "markdown_heading_colon_records":
        # Blank record boundaries keep each ordinary record independently
        # selectable under the unchanged 5k/page cap.  This is a page-layout
        # treatment shared by both arms, not a task-conditioned reorder.
        observations = "\n\n".join(
            f"{name} [{iso3}]: {rendered}" for name, iso3, rendered in rows
        )
        content = (
            "# Country coverage index\n\n"
            + coverage
            + "\n\n# "
            + target_label
            + " official observations\n\n"
            + observations
        )
    elif target["layout"] == "plain_target_label_bullet_equals_records":
        observations = "\n\n".join(
            f"- {name} [{iso3}] = {rendered}" for name, iso3, rendered in rows
        )
        content = (
            "Country coverage index:\n\n"
            + coverage
            + "\n\n"
            + target_label
            + " official records:\n\n"
            + observations
        )
    else:
        raise RuntimeError("V2.49.37 target layout drifted")
    if not 8_000 < len(content) <= 30_000:
        raise RuntimeError("V2.49.37 rendered ordinary-text page capacity drifted")
    return {
        "title": f"World Bank official indicator {target['indicator']} {target['year']}",
        "url": url,
        "content": content,
        "layout": target["layout"],
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
            hashlib.sha256(f"{contract.SELECTION_SEED}:{iso3}".encode()).hexdigest(),
            iso3,
        ),
    )
    if len(eligible) < contract.SELECTED_ENTITY_COUNT:
        raise RuntimeError("V2.49.37 complete entity capacity drifted")
    selected = eligible[: contract.SELECTED_ENTITY_COUNT]
    columns = contract.visible_columns()
    tasks: list[dict[str, str]] = []
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
            f"v24937:{','.join(group)}".encode()
        ).hexdigest()[:24]
        tasks.append({"opaque_id": opaque, "question": question})
    return contract.validate_task_vector(tasks)


def build_snapshot(
    catalog_blob: bytes, target_blobs: list[bytes]
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    catalog = engine.parse_catalog(catalog_blob)
    pages: list[dict[str, str]] = []
    values: list[dict[str, dict[str, str]]] = []
    for blob, target, url in zip(
        target_blobs, contract.TARGETS, contract.TARGET_URLS, strict=True
    ):
        page, target_values = parse_target(blob, dict(target), url)
        pages.append(page)
        values.append(target_values)
    tasks = build_visible_tasks(catalog, values)
    bundle: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24937_frozen_shared_layout_diverse_ordinary_text_pages",
        "pages": pages,
        "target_keys": list(contract.TARGET_KEYS),
        "layout_vector": [target["layout"] for target in contract.TARGETS],
        "same_page_vector_for_both_arms": True,
        "page_representation_fixed_before_arm_branch": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    bundle["bundle_payload_sha256"] = contract.payload_sha256(bundle)
    freeze: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24937_snapshot_freeze",
        "catalog_response_sha256": hashlib.sha256(catalog_blob).hexdigest(),
        "target_response_sha256": [hashlib.sha256(blob).hexdigest() for blob in target_blobs],
        "rendered_page_character_counts": [len(page["content"]) for page in pages],
        "layout_vector": [target["layout"] for target in contract.TARGETS],
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
    """Require natural contextual-pair exposure in both frozen layouts."""

    value = _INHERITED_BUILD_FORWARD_AUDIT(now=now)
    tasks = engine._read_jsonl(ROOT / contract.VISIBLE_TASKS)
    pages = engine._read(ROOT / contract.FROZEN_PAGES).get("pages")
    if not isinstance(pages, list) or len(pages) != len(contract.TARGETS):
        raise RuntimeError("V2.49.37 layout audit page vector drifted")
    layout_aggregate: dict[str, dict[str, int]] = {}
    for page, target in zip(pages, contract.TARGETS, strict=True):
        layout = str(target["layout"])
        supported = 0
        retained = 0
        for task in contract.validate_task_vector(tasks):
            projection = candidate.build_projection(task["question"], [page])
            receipt = projection["content_free_receipt"]
            supported += int(
                receipt["supported_contextual_target_value_pair_count"]
            )
            retained += int(
                receipt["retained_contextual_target_value_pair_count"]
            )
        layout_aggregate[layout] = {
            "tasks": contract.SELECTED_COUNT,
            "supported_contextual_target_value_pairs": supported,
            "retained_contextual_target_value_pairs": retained,
        }
    layouts_engaged = sum(
        row["supported_contextual_target_value_pairs"] > 0
        and row["retained_contextual_target_value_pairs"] > 0
        for row in layout_aggregate.values()
    )
    minimum = int(
        engine._read(ROOT / contract.PROTOCOL)["execution"]
        ["mechanism_gate_before_evaluator"]
        ["minimum_layouts_with_contextual_pairs"]
    )
    value["layout_mechanism_aggregate"] = layout_aggregate
    value["mechanism_gate"]["minimum_layouts_with_contextual_pairs"] = minimum
    value["mechanism_gate"]["observed_layouts_with_contextual_pairs"] = (
        layouts_engaged
    )
    value["checks"]["both_frozen_layouts_contextually_engaged"] = (
        layouts_engaged >= minimum == len(contract.TARGETS)
    )
    value["mechanism_gate"]["passed"] = (
        value["mechanism_gate"]["passed"]
        and value["checks"]["both_frozen_layouts_contextually_engaged"]
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
    parent.contract = contract
    parent.base.contract = contract
    engine.contract = contract
    engine.parse_target = parse_target
    engine.build_visible_tasks = build_visible_tasks
    engine.build_snapshot = build_snapshot
    engine.build_forward_audit = build_forward_audit


def main() -> None:
    configure()
    engine.main()


if __name__ == "__main__":
    main()
