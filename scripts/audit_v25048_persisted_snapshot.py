#!/usr/bin/env python3
"""Read-only post-freeze audit for V2.50.48 sorted-key JSONL persistence."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25047_pypi_current_record_representation as representation  # noqa: E402
from deepwide_agent import v25048_atomic_pypi_representation_contract as contract  # noqa: E402


def validate_rows(values: list[Mapping[str, object]]) -> list[dict[str, object]]:
    """Validate exact schema/value contracts independent of JSON key order."""

    if len(values) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.48 persisted snapshot denominator drifted")
    freeze_sha256 = contract.sha256(ROOT / contract.PREDICTION_FREEZE)
    expected_keys = {
        "index", "opaque_id", "project", "endpoint_sha256",
        "raw_response_sha256", "raw_response_bytes", "http_status", "record",
        "prediction_freeze_sha256", "published_after_prediction_freeze",
    }
    output: list[dict[str, object]] = []
    for index, raw in enumerate(values):
        row = dict(raw)
        record = row.get("record") or {}
        if (
            set(row) != expected_keys
            or row.get("index") != index
            or row.get("opaque_id") != contract.task_vector()[index]["opaque_id"]
            or row.get("project") != contract.PROJECTS[index]
            or row.get("endpoint_sha256")
            != hashlib.sha256(contract.endpoint_vector()[index].encode()).hexdigest()
            or not isinstance(row.get("raw_response_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", row["raw_response_sha256"]) is None
            or isinstance(row.get("raw_response_bytes"), bool)
            or not isinstance(row.get("raw_response_bytes"), int)
            or row["raw_response_bytes"] <= 0
            or row.get("http_status") != 200
            or not isinstance(record, Mapping)
            or set(record) != set(contract.COLUMNS)
            or any(
                not isinstance(record[column], str)
                or not record[column]
                or any(character in record[column] for character in "|\r\n\x00")
                for column in contract.COLUMNS
            )
            or representation.normalize_project(record["Package"])
            != representation.normalize_project(contract.PROJECTS[index])
            or re.fullmatch(
                r"\d{4}-\d{2}-\d{2}",
                record["Latest release date (YYYY-MM-DD)"],
            ) is None
            or row.get("prediction_freeze_sha256") != freeze_sha256
            or row.get("published_after_prediction_freeze") is not True
        ):
            raise RuntimeError("V2.50.48 persisted snapshot row drifted")
        output.append(row)
    return output


def main() -> None:
    path = contract.ordinary(ROOT, contract.PUBLIC_SNAPSHOT, tracked=True)
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    checked = validate_rows(values)
    print(
        json.dumps(
            {
                "role": "v25048_persisted_snapshot_read_only_audit",
                "rows": len(checked),
                "valid": True,
                "prediction_or_snapshot_modified": False,
                "network_model_fetch_or_evaluator_called": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
