#!/usr/bin/env python3
"""Read-only order-independent audit of the V2.50.53 persisted snapshot."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25049_page_self_identified_record as representation  # noqa: E402
from deepwide_agent import v25053_cran_unconditional_denominator_contract as contract  # noqa: E402


def validate_rows(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(values) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.53 persisted snapshot denominator drifted")
    freeze_sha256 = contract.sha256(ROOT / contract.PREDICTION_FREEZE)
    expected_keys = {
        "index", "opaque_id", "project", "preparation_ready",
        "endpoint_sha256", "raw_response_sha256", "raw_response_bytes",
        "decoded_page_sha256", "decoded_page_characters", "http_status",
        "record", "prediction_freeze_sha256", "published_after_prediction_freeze",
    }
    output: list[dict[str, Any]] = []
    for index, raw in enumerate(values):
        row = dict(raw)
        ready = row.get("preparation_ready") is True
        record = row.get("record")
        ready_surface = bool(
            ready
            and isinstance(row.get("raw_response_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", row["raw_response_sha256"])
            and isinstance(row.get("raw_response_bytes"), int)
            and not isinstance(row.get("raw_response_bytes"), bool)
            and row["raw_response_bytes"] > 0
            and isinstance(row.get("decoded_page_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", row["decoded_page_sha256"])
            and isinstance(row.get("decoded_page_characters"), int)
            and not isinstance(row.get("decoded_page_characters"), bool)
            and row["decoded_page_characters"] > 0
            and row.get("http_status") == 200
            and isinstance(record, Mapping)
            and set(record) == set(contract.COLUMNS)
            and all(
                isinstance(record[column], str)
                and record[column]
                and not any(character in record[column] for character in "|\r\n\x00")
                for column in contract.COLUMNS
            )
            and representation._identity_key(record["Package"])
            == representation._identity_key(contract.PROJECTS[index])
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["Published"])
        )
        failure_surface = bool(
            not ready
            and row.get("raw_response_sha256") is None
            and row.get("raw_response_bytes") is None
            and row.get("decoded_page_sha256") is None
            and row.get("decoded_page_characters") is None
            and isinstance(row.get("http_status"), int)
            and not isinstance(row.get("http_status"), bool)
            and row["http_status"] >= 0
            and record is None
        )
        if (
            set(row) != expected_keys
            or row.get("index") != index
            or row.get("opaque_id") != contract.task_vector()[index]["opaque_id"]
            or row.get("project") != contract.PROJECTS[index]
            or not isinstance(row.get("preparation_ready"), bool)
            or row.get("endpoint_sha256")
            != hashlib.sha256(contract.endpoint_vector()[index].encode()).hexdigest()
            or not (ready_surface or failure_surface)
            or row.get("prediction_freeze_sha256") != freeze_sha256
            or row.get("published_after_prediction_freeze") is not True
        ):
            raise RuntimeError("V2.50.53 persisted snapshot row drifted")
        output.append(row)
    return output


def main() -> None:
    path = contract.ordinary(ROOT, contract.PUBLIC_SNAPSHOT, tracked=True)
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    checked = validate_rows(values)
    print(
        json.dumps(
            {
                "role": "v25053_persisted_snapshot_read_only_audit",
                "rows": len(checked),
                "ready_rows": sum(row["preparation_ready"] for row in checked),
                "valid": True,
                "prediction_or_snapshot_modified": False,
                "network_model_fetch_or_evaluator_called": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
