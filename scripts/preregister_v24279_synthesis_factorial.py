#!/usr/bin/env python3
"""Freeze a neutral 2x2 synthesis-reasoning/format factorial probe."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24279_neutral_synthesis_factorial_preregistration"
PROTOCOL_ID = "v24279_reasoning_format_neutral_synthesis_factorial_v1"
OUTPUT = Path(
    "results/v24279_synthesis_factorial_preregistration_v1_20260803.json"
)
RESULT = Path("results/v24279_synthesis_factorial_result_v1_20260803.json")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
CASE_COUNT = 8
WAVES = 4
CASES_PER_WAVE = 2
ARM_CONCURRENCY = 8
ROWS_PER_CASE = 3
COLUMNS = ("Feature", "Version", "Status")
CELLS_PER_CASE = ROWS_PER_CASE * len(COLUMNS)
ARMS = (
    {"name": "low_free", "reasoning": "low", "format": "free_markdown"},
    {"name": "none_free", "reasoning": "none", "format": "free_markdown"},
    {"name": "low_strict", "reasoning": "low", "format": "strict_json"},
    {"name": "none_strict", "reasoning": "none", "format": "strict_json"},
)
SYNTHETIC_CASES = tuple(
    {
        "case": case,
        "rows": tuple(
            {
                "Feature": f"Synthetic Feature M{case:02d}{row:02d}A",
                "Version": f"v-M{case:02d}{row:02d}B",
                "Status": f"status-M{case:02d}{row:02d}C",
            }
            for row in range(1, ROWS_PER_CASE + 1)
        ),
    }
    for case in range(1, CASE_COUNT + 1)
)
PROVIDER = {
    "endpoint": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "service_tier": "priority",
    "timeout_seconds": 180,
    "max_output_tokens": 4000,
    "attempts_per_arm": 1,
}
GATES = {
    "maximum_batch_wall_seconds": 180.0,
    "required_exact_cell_matches_per_arm": CASE_COUNT * CELLS_PER_CASE,
    "required_nonempty_cells_per_arm": CASE_COUNT * CELLS_PER_CASE,
    "maximum_failures_per_arm": 0,
    "candidate_thresholds": {
        "none_free": {
            "maximum_input_token_ratio": 1.10,
            "maximum_output_token_ratio": 0.70,
            "maximum_total_token_ratio": 0.75,
            "maximum_wall_sum_ratio": 0.80,
        },
        "low_strict": {
            "maximum_input_token_ratio": 1.30,
            "maximum_output_token_ratio": 0.90,
            "maximum_total_token_ratio": 0.95,
            "maximum_wall_sum_ratio": 0.90,
        },
        "none_strict": {
            "maximum_input_token_ratio": 1.30,
            "maximum_output_token_ratio": 0.70,
            "maximum_total_token_ratio": 0.80,
            "maximum_wall_sum_ratio": 0.80,
        },
    },
    "selection_order_after_eligibility": [
        "minimum_total_tokens",
        "minimum_wall_sum_seconds",
        "none_strict",
        "none_free",
        "low_strict",
    ],
}
FORWARD_FILES = (
    "src/deepwide_agent/clients.py",
    "scripts/deepwide_api_lease.py",
    "scripts/preregister_v24279_synthesis_factorial.py",
    "scripts/probe_v24279_synthesis_factorial.py",
)
CONTROL_FILES = ("tests/test_probe_v24279_synthesis_factorial.py",)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.79 path is noncanonical")
    path = root / raw
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.79 expected ordinary file: {relative}")
    return path


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.42.79 credential literal in {relative}")
        value[relative] = sha256(path)
    return value


def schedule() -> list[list[dict[str, Any]]]:
    waves: list[list[dict[str, Any]]] = []
    for wave in range(WAVES):
        values: list[dict[str, Any]] = []
        for case in range(
            wave * CASES_PER_WAVE + 1,
            (wave + 1) * CASES_PER_WAVE + 1,
        ):
            rotation = (case - 1) % len(ARMS)
            ordered = (*ARMS[rotation:], *ARMS[:rotation])
            values.extend(
                {
                    "case": case,
                    "arm": arm["name"],
                    "reasoning": arm["reasoning"],
                    "format": arm["format"],
                }
                for arm in ordered
            )
        waves.append(values)
    validate_schedule(waves)
    return waves


def validate_schedule(value: object) -> None:
    if not isinstance(value, list) or len(value) != WAVES:
        raise RuntimeError("V2.42.79 schedule wave drifted")
    flattened: list[tuple[int, str]] = []
    arm_map = {arm["name"]: arm for arm in ARMS}
    for wave in value:
        if not isinstance(wave, list) or len(wave) != ARM_CONCURRENCY:
            raise RuntimeError("V2.42.79 schedule concurrency drifted")
        for item in wave:
            if (
                not isinstance(item, Mapping)
                or set(item) != {"case", "arm", "reasoning", "format"}
                or item.get("arm") not in arm_map
                or item.get("reasoning") != arm_map[item["arm"]]["reasoning"]
                or item.get("format") != arm_map[item["arm"]]["format"]
                or isinstance(item.get("case"), bool)
                or not isinstance(item.get("case"), int)
                or not 1 <= item["case"] <= CASE_COUNT
            ):
                raise RuntimeError("V2.42.79 schedule item drifted")
            flattened.append((item["case"], item["arm"]))
    if sorted(flattened) != sorted(
        (case, arm["name"])
        for case in range(1, CASE_COUNT + 1)
        for arm in ARMS
    ):
        raise RuntimeError("V2.42.79 factorial coverage drifted")


def _validate_cases() -> None:
    if len(SYNTHETIC_CASES) != CASE_COUNT:
        raise RuntimeError("V2.42.79 case count drifted")
    markers: set[str] = set()
    for case in SYNTHETIC_CASES:
        if set(case) != {"case", "rows"} or len(case["rows"]) != ROWS_PER_CASE:
            raise RuntimeError("V2.42.79 case shape drifted")
        for row in case["rows"]:
            if set(row) != set(COLUMNS) or any(not str(row[name]) for name in COLUMNS):
                raise RuntimeError("V2.42.79 cell shape drifted")
            for cell in row.values():
                marker = str(cell).rsplit("M", 1)[-1]
                if marker in markers:
                    raise RuntimeError("V2.42.79 marker reuse drifted")
                markers.add(marker)
    if len(markers) != CASE_COUNT * CELLS_PER_CASE:
        raise RuntimeError("V2.42.79 marker count drifted")


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _validate_cases()
    if require_pristine and (
        (root / RESULT).exists() or (root / RESULT).is_symlink()
    ):
        raise RuntimeError("V2.42.79 result surface is not pristine")
    forward = _manifest(root, FORWARD_FILES)
    control = _manifest(root, CONTROL_FILES)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "neutral_synthetic_evidence_synthesis_factorial_only",
        "factorial_contract": {
            "case_count": CASE_COUNT,
            "rows_per_case": ROWS_PER_CASE,
            "columns": list(COLUMNS),
            "cells_per_case": CELLS_PER_CASE,
            "arms": [dict(arm) for arm in ARMS],
            "waves": WAVES,
            "cases_per_wave": CASES_PER_WAVE,
            "arm_concurrency": ARM_CONCURRENCY,
            "same_visible_schema_and_evidence_within_case": True,
            "case_set_sha256": payload_sha256(SYNTHETIC_CASES),
            "synthetic_evidence_or_output_value_persisted_in_result": False,
            "schedule": schedule(),
        },
        "provider": dict(PROVIDER),
        "gates": dict(GATES),
        "lease": {
            "path": str(LEASE),
            "owner": "v24279_synthesis_factorial_v1",
            "purpose": "neutral_reasoning_format_synthesis_factorial",
            "nonblocking_single_owner": True,
        },
        "forward_manifest": forward,
        "forward_manifest_sha256": payload_sha256(forward),
        "control_manifest": control,
        "control_manifest_sha256": payload_sha256(control),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "benchmark_question_query_url_page_prediction_answer_task_id_or_hash_persisted": False,
            "synthetic_evidence_or_generated_output_value_persisted_in_result": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "search_fetch_or_official_evaluator_called": False,
        },
        "authorization": {
            "benchmark_launch": False,
            "dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(
    root: Path = ROOT,
    path: Path = OUTPUT,
    *,
    value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else read_object(_ordinary(root, path))
    unsigned = dict(protocol)
    seal = unsigned.pop("protocol_payload_sha256", None)
    factorial = protocol.get("factorial_contract")
    source = protocol.get("source_policy")
    authorization = protocol.get("authorization")
    if (
        protocol.get("role") != ROLE
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "neutral_synthetic_evidence_synthesis_factorial_only"
        or not isinstance(factorial, Mapping)
        or factorial.get("case_count") != CASE_COUNT
        or factorial.get("rows_per_case") != ROWS_PER_CASE
        or factorial.get("columns") != list(COLUMNS)
        or factorial.get("arms") != [dict(arm) for arm in ARMS]
        or factorial.get("case_set_sha256") != payload_sha256(SYNTHETIC_CASES)
        or factorial.get("synthetic_evidence_or_output_value_persisted_in_result")
        is not False
        or protocol.get("provider") != PROVIDER
        or protocol.get("gates") != GATES
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.79 protocol identity drifted")
    validate_schedule(factorial.get("schedule"))
    _validate_cases()
    for name, files, seal_name in (
        ("forward", FORWARD_FILES, "forward_manifest_sha256"),
        ("control", CONTROL_FILES, "control_manifest_sha256"),
    ):
        manifest = protocol.get(f"{name}_manifest")
        if (
            not isinstance(manifest, Mapping)
            or set(manifest) != set(files)
            or protocol.get(seal_name) != payload_sha256(manifest)
            or any(
                sha256(_ordinary(root, relative)) != digest
                for relative, digest in manifest.items()
            )
        ):
            raise RuntimeError(f"V2.42.79 {name} manifest drifted")
    return protocol


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    protocol = build_protocol()
    publish_new(ROOT / OUTPUT, protocol)
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}, sort_keys=True))
