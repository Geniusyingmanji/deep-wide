#!/usr/bin/env python3
"""Post-freeze evaluator for the V2.49.34 external gate."""

from __future__ import annotations

import copy
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24934_contextual_record_external_contract as contract  # noqa: E402
from scripts import evaluate_v24923_target_value_external as base  # noqa: E402


_OBSERVATION = re.compile(r"^(.+?)\s+\[([A-Z]{3})\]:\s*(\S.*)$")
_INHERITED_PUBLISH = base._publish


def build_gold(
    tasks: Sequence[Mapping[str, Any]],
    pages: Mapping[str, Any],
) -> dict[str, list[dict[str, str]]]:
    """Parse frozen ordinary-text observations only after prediction freeze."""

    raw_pages = pages.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != len(contract.TARGETS):
        raise RuntimeError("V2.49.34 evaluator page vector drifted")
    page_values: list[dict[str, str]] = []
    for page in raw_pages:
        if not isinstance(page, Mapping):
            raise RuntimeError("V2.49.34 evaluator page drifted")
        values: dict[str, str] = {}
        for line in str(page.get("content", "")).splitlines():
            match = _OBSERVATION.match(line.strip())
            if match is not None and match.group(2) not in values:
                values[match.group(2)] = match.group(3).strip()
        if len(values) < 170:
            raise RuntimeError("V2.49.34 evaluator observation capacity drifted")
        page_values.append(values)
    output: dict[str, list[dict[str, str]]] = {}
    for task in contract.validate_task_vector(tasks):
        output[task["opaque_id"]] = [
            {
                # The inherited evaluator uses this generic row-identity key;
                # the visible prediction header remains contract.visible_columns()[0].
                "Country": name,
                **{
                    contract.visible_columns()[index + 1]: page_values[index][iso3]
                    for index in range(len(contract.TARGETS))
                },
            }
            for name, iso3 in contract.parse_visible_entities(task["question"])
        ]
    return output


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    """Write native V2.49.34 roles while reusing the frozen evaluator engine."""

    copied = copy.deepcopy(dict(value))
    if path == ROOT / contract.EVALUATOR_PROTOCOL:
        copied["role"] = (
            "v24934_contextual_record_external_evaluator_preregistration"
        )
        copied["primary_comparison"] = (
            "contextual_record_30k_minus_unicode_total_30k"
        )
        copied["arm_algorithms"] = {
            "parent_30k": "v24928_unicode_total_visible_row_sparse_table_compactor_v1",
            "target_value_30k": (
                "v24933_unicode_total_contextual_record_value_projector_v1"
            ),
        }
        seal = "protocol_payload_sha256"
    elif path == ROOT / contract.RESULT:
        copied["role"] = "v24934_contextual_record_external_result"
        copied["status"] = (
            "contextual_record_external_go"
            if copied.get("passed") is True
            else "contextual_record_external_no_go"
        )
        copied["arm_algorithms"] = {
            "parent_30k": "v24928_unicode_total_visible_row_sparse_table_compactor_v1",
            "target_value_30k": (
                "v24933_unicode_total_contextual_record_value_projector_v1"
            ),
        }
        seal = "result_payload_sha256"
    elif path == ROOT / contract.POSTAUDIT:
        copied["role"] = "v24934_contextual_record_external_postresult_audit"
        seal = "audit_payload_sha256"
    else:
        raise RuntimeError("V2.49.34 evaluator attempted an unknown output surface")
    copied.pop(seal, None)
    copied[seal] = contract.payload_sha256(copied)
    _INHERITED_PUBLISH(path, copied)


def configure() -> None:
    base.contract = contract
    base.build_gold = build_gold
    base._publish = _publish


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
