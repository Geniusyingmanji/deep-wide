#!/usr/bin/env python3
"""Run the frozen neutral V2.42.79 synthesis factorial probe."""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import extract_response_text  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    extract_valid_markdown_table,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts import preregister_v24279_synthesis_factorial as prereg  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    sha256,
)


ARM_KEYS = frozenset(
    {
        "case",
        "arm",
        "reasoning",
        "format",
        "terminal",
        "failure_type",
        "http_status",
        "response_status",
        "incomplete_reason",
        "wall_seconds",
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "cached_input_tokens",
        "total_tokens",
        "request_body_bytes",
        "row_count",
        "column_count",
        "nonempty_cell_count",
        "exact_cell_match_count",
        "expected_cell_count",
        "canonical_markdown_valid",
        "response_text_or_hash_persisted",
        "synthetic_evidence_value_persisted",
        "benchmark_question_query_url_page_prediction_answer_task_id_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
)


def _schema() -> dict[str, Any]:
    row = {
        "type": "object",
        "properties": {
            name: {"type": "string", "minLength": 1, "maxLength": 160}
            for name in prereg.COLUMNS
        },
        "required": list(prereg.COLUMNS),
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "items": row,
                "minItems": prereg.ROWS_PER_CASE,
                "maxItems": prereg.ROWS_PER_CASE,
            }
        },
        "required": ["rows"],
        "additionalProperties": False,
    }


def _format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "neutral_exact_table_rows_v1",
        "strict": True,
        "schema": _schema(),
    }


def _prompt(case: Mapping[str, Any], *, strict: bool) -> tuple[str, str]:
    system = (
        "Use only the supplied synthetic records. Never use outside facts. "
        "Preserve every cell exactly, emit exactly three rows, and never add, "
        "remove, summarize, or rewrite a value. "
        + (
            "Return only the object required by the strict response schema."
            if strict
            else "Return exactly one fenced Markdown table and no prose."
        )
    )
    records = "\n".join(
        f"ROW {index}: "
        + "; ".join(f"{name}={row[name]}" for name in prereg.COLUMNS)
        for index, row in enumerate(case["rows"], start=1)
    )
    user = (
        "Required columns in this exact order: "
        + ", ".join(prereg.COLUMNS)
        + "\n\nSYNTHETIC RECORDS:\n"
        + records
    )
    return system, user


def _body(case: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    strict = item["format"] == "strict_json"
    system, user = _prompt(case, strict=strict)
    body: dict[str, Any] = {
        "model": prereg.PROVIDER["model"],
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_output_tokens": prereg.PROVIDER["max_output_tokens"],
        "reasoning": {"effort": item["reasoning"]},
        "service_tier": prereg.PROVIDER["service_tier"],
    }
    if strict:
        body["text"] = {"format": _format()}
    return body


def _split(line: str) -> list[str]:
    return [value.strip() for value in line.strip().strip("|").split("|")]


def _free_rows(text: str) -> tuple[list[dict[str, str]], bool]:
    canonical, errors = extract_valid_markdown_table(text, list(prereg.COLUMNS))
    if canonical is None or errors:
        return [], False
    lines = [line for line in canonical.splitlines() if line.strip()]
    if len(lines) < 5 or lines[0].strip().casefold() != "```markdown" or lines[-1].strip() != "```":
        return [], False
    header = _split(lines[1])
    rows = [dict(zip(header, _split(line), strict=True)) for line in lines[3:-1]]
    return rows, True


def _strict_rows(text: str) -> tuple[list[dict[str, str]], bool]:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return [], False
    rows = value.get("rows") if isinstance(value, dict) and set(value) == {"rows"} else None
    if (
        not isinstance(rows, list)
        or len(rows) != prereg.ROWS_PER_CASE
        or any(
            not isinstance(row, dict)
            or set(row) != set(prereg.COLUMNS)
            or any(not isinstance(row[name], str) or not row[name] for name in prereg.COLUMNS)
            for row in rows
        )
    ):
        return [], False
    return [dict(row) for row in rows], True


def _render(rows: Sequence[Mapping[str, str]]) -> str:
    lines = [
        "```markdown",
        "| " + " | ".join(prereg.COLUMNS) + " |",
        "| " + " | ".join("---" for _ in prereg.COLUMNS) + " |",
    ]
    lines.extend(
        "| " + " | ".join(str(row[name]) for name in prereg.COLUMNS) + " |"
        for row in rows
    )
    lines.append("```")
    return "\n".join(lines)


def _evaluate_rows(
    case: Mapping[str, Any], rows: Sequence[Mapping[str, str]], parsed: bool
) -> dict[str, Any]:
    canonical = False
    if parsed:
        rendered = _render(rows)
        canonical_value, errors = extract_valid_markdown_table(
            rendered, list(prereg.COLUMNS)
        )
        canonical = canonical_value == rendered and not errors
    nonempty = sum(
        bool(str(row.get(name, "")).strip())
        for row in rows
        for name in prereg.COLUMNS
    )
    exact = sum(
        index < len(rows) and str(rows[index].get(name, "")) == expected[name]
        for index, expected in enumerate(case["rows"])
        for name in prereg.COLUMNS
    )
    return {
        "row_count": len(rows),
        "column_count": len(prereg.COLUMNS) if rows else 0,
        "nonempty_cell_count": nonempty,
        "exact_cell_match_count": exact,
        "expected_cell_count": prereg.CELLS_PER_CASE,
        "canonical_markdown_valid": canonical,
    }


def _usage(payload: Mapping[str, Any]) -> dict[str, int]:
    usage = payload.get("usage") if isinstance(payload.get("usage"), Mapping) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), Mapping) else {}
    input_details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), Mapping) else {}
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": int(output_details.get("reasoning_tokens", 0) or 0),
        "cached_input_tokens": int(input_details.get("cached_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0)
        or input_tokens + output_tokens,
    }


def _run_arm(item: Mapping[str, Any]) -> dict[str, Any]:
    case = prereg.SYNTHETIC_CASES[item["case"] - 1]
    body = _body(case, item)
    started = time.monotonic()
    failure: str | None = None
    status: int | None = None
    payload: dict[str, Any] = {}
    try:
        response = requests.post(
            prereg.PROVIDER["endpoint"],
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=prereg.PROVIDER["timeout_seconds"],
        )
        status = response.status_code
        decoded = response.json()
        if not isinstance(decoded, dict):
            raise TypeError("provider payload is not an object")
        payload = decoded
        if status != 200:
            failure = "HttpStatus"
    except Exception as exc:  # noqa: BLE001 - persist class only
        failure = type(exc).__name__
    text = extract_response_text(payload) if payload else ""
    if item["format"] == "strict_json":
        rows, parsed = _strict_rows(text)
    else:
        rows, parsed = _free_rows(text)
    shape = _evaluate_rows(case, rows, parsed)
    usage = _usage(payload)
    incomplete = payload.get("incomplete_details") if isinstance(payload.get("incomplete_details"), Mapping) else {}
    response_status = str(payload.get("status") or "absent")
    if failure is None and (response_status != "completed" or not parsed):
        failure = "IncompleteOrInvalidOutput"
    value = {
        "case": item["case"],
        "arm": item["arm"],
        "reasoning": item["reasoning"],
        "format": item["format"],
        "terminal": True,
        "failure_type": failure,
        "http_status": status,
        "response_status": response_status,
        "incomplete_reason": str(incomplete.get("reason") or ""),
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        **usage,
        "request_body_bytes": len(
            json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        ),
        **shape,
        "response_text_or_hash_persisted": False,
        "synthetic_evidence_value_persisted": False,
        "benchmark_question_query_url_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    validate_arm(value)
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.79 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.79 {label} is invalid")
    return number


def validate_arm(value: Mapping[str, Any]) -> None:
    arm_map = {arm["name"]: arm for arm in prereg.ARMS}
    if (
        set(value) != ARM_KEYS
        or value.get("arm") not in arm_map
        or value.get("reasoning") != arm_map[value["arm"]]["reasoning"]
        or value.get("format") != arm_map[value["arm"]]["format"]
        or isinstance(value.get("case"), bool)
        or not isinstance(value.get("case"), int)
        or not 1 <= value["case"] <= prereg.CASE_COUNT
        or value.get("terminal") is not True
        or value.get("failure_type") is not None
        and not isinstance(value.get("failure_type"), str)
        or value.get("http_status") is not None
        and (isinstance(value.get("http_status"), bool) or not isinstance(value.get("http_status"), int))
        or not isinstance(value.get("response_status"), str)
        or not isinstance(value.get("incomplete_reason"), str)
        or value.get("response_text_or_hash_persisted") is not False
        or value.get("synthetic_evidence_value_persisted") is not False
        or value.get(
            "benchmark_question_query_url_page_prediction_answer_task_id_or_hash_persisted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.79 arm schema drifted")
    _finite(value.get("wall_seconds"), "wall")
    for name in (
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "cached_input_tokens",
        "total_tokens",
        "request_body_bytes",
        "row_count",
        "column_count",
        "nonempty_cell_count",
        "exact_cell_match_count",
        "expected_cell_count",
    ):
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise RuntimeError("V2.42.79 arm counter drifted")
    if (
        not isinstance(value.get("canonical_markdown_valid"), bool)
        or value["exact_cell_match_count"] > value["expected_cell_count"]
        or value["nonempty_cell_count"] > value["expected_cell_count"]
    ):
        raise RuntimeError("V2.42.79 arm shape accounting drifted")


def _aggregate(rows: Sequence[Mapping[str, Any]], arm: str) -> dict[str, Any]:
    values = [row for row in rows if row["arm"] == arm]
    if len(values) != prereg.CASE_COUNT:
        raise RuntimeError("V2.42.79 arm count drifted")
    return {
        "selected": len(values),
        "terminal": sum(row["terminal"] is True for row in values),
        "failures": sum(row["failure_type"] is not None for row in values),
        "http_200": sum(row["http_status"] == 200 for row in values),
        "completed": sum(row["response_status"] == "completed" for row in values),
        "canonical_markdown_valid": sum(row["canonical_markdown_valid"] is True for row in values),
        "row_count": sum(row["row_count"] for row in values),
        "nonempty_cell_count": sum(row["nonempty_cell_count"] for row in values),
        "exact_cell_match_count": sum(row["exact_cell_match_count"] for row in values),
        "wall_seconds_sum": round(sum(float(row["wall_seconds"]) for row in values), 6),
        "input_tokens": sum(row["input_tokens"] for row in values),
        "output_tokens": sum(row["output_tokens"] for row in values),
        "reasoning_tokens": sum(row["reasoning_tokens"] for row in values),
        "cached_input_tokens": sum(row["cached_input_tokens"] for row in values),
        "total_tokens": sum(row["total_tokens"] for row in values),
        "request_body_bytes": sum(row["request_body_bytes"] for row in values),
    }


def _ratio(candidate: int | float, baseline: int | float) -> float:
    return float(candidate) / float(baseline) if float(baseline) > 0 else math.inf


def summarize(
    protocol: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], batch_wall: float
) -> dict[str, Any]:
    values = [dict(row) for row in rows]
    for row in values:
        validate_arm(row)
    expected = sorted(
        (case, arm["name"])
        for case in range(1, prereg.CASE_COUNT + 1)
        for arm in prereg.ARMS
    )
    if sorted((row["case"], row["arm"]) for row in values) != expected:
        raise RuntimeError("V2.42.79 factorial result coverage drifted")
    arms = {arm["name"]: _aggregate(values, arm["name"]) for arm in prereg.ARMS}
    baseline = arms["low_free"]
    ratios: dict[str, dict[str, float]] = {}
    eligibility: dict[str, dict[str, Any]] = {}
    for name, thresholds in protocol["gates"]["candidate_thresholds"].items():
        candidate = arms[name]
        ratio = {
            "input_tokens": _ratio(candidate["input_tokens"], baseline["input_tokens"]),
            "output_tokens": _ratio(candidate["output_tokens"], baseline["output_tokens"]),
            "total_tokens": _ratio(candidate["total_tokens"], baseline["total_tokens"]),
            "wall_seconds_sum": _ratio(candidate["wall_seconds_sum"], baseline["wall_seconds_sum"]),
        }
        ratios[name] = ratio
        quality = (
            candidate["failures"] == 0
            and candidate["http_200"] == prereg.CASE_COUNT
            and candidate["completed"] == prereg.CASE_COUNT
            and candidate["canonical_markdown_valid"] == prereg.CASE_COUNT
            and candidate["row_count"] == prereg.CASE_COUNT * prereg.ROWS_PER_CASE
            and candidate["nonempty_cell_count"]
            == protocol["gates"]["required_nonempty_cells_per_arm"]
            and candidate["exact_cell_match_count"]
            == protocol["gates"]["required_exact_cell_matches_per_arm"]
        )
        checks = {
            "exact_content_preservation": quality,
            "input_token_ratio": ratio["input_tokens"]
            <= thresholds["maximum_input_token_ratio"],
            "output_token_ratio": ratio["output_tokens"]
            <= thresholds["maximum_output_token_ratio"],
            "total_token_ratio": ratio["total_tokens"]
            <= thresholds["maximum_total_token_ratio"],
            "wall_sum_ratio": ratio["wall_seconds_sum"]
            <= thresholds["maximum_wall_sum_ratio"],
        }
        eligibility[name] = {"checks": checks, "eligible": all(checks.values())}
    baseline_valid = (
        baseline["failures"] == 0
        and baseline["http_200"] == prereg.CASE_COUNT
        and baseline["completed"] == prereg.CASE_COUNT
        and baseline["canonical_markdown_valid"] == prereg.CASE_COUNT
        and baseline["row_count"] == prereg.CASE_COUNT * prereg.ROWS_PER_CASE
        and baseline["nonempty_cell_count"]
        == protocol["gates"]["required_nonempty_cells_per_arm"]
        and baseline["exact_cell_match_count"]
        == protocol["gates"]["required_exact_cell_matches_per_arm"]
    )
    eligible = [name for name, item in eligibility.items() if item["eligible"]]
    tie_order = protocol["gates"]["selection_order_after_eligibility"][2:]
    if set(tie_order) != set(protocol["gates"]["candidate_thresholds"]):
        raise RuntimeError("V2.42.79 selection tie order drifted")
    selected = (
        min(
            eligible,
            key=lambda name: (
                arms[name]["total_tokens"],
                arms[name]["wall_seconds_sum"],
                tie_order.index(name),
            ),
        )
        if eligible
        else None
    )
    pair_directions: dict[str, dict[str, dict[str, int]]] = {}
    for candidate in ("none_free", "low_strict", "none_strict"):
        directions: dict[str, dict[str, int]] = {}
        for field in ("total_tokens", "output_tokens", "wall_seconds"):
            better = tie = worse = 0
            for case in range(1, prereg.CASE_COUNT + 1):
                base_row = next(row for row in values if row["case"] == case and row["arm"] == "low_free")
                candidate_row = next(row for row in values if row["case"] == case and row["arm"] == candidate)
                delta = float(candidate_row[field]) - float(base_row[field])
                if abs(delta) <= 1e-12:
                    tie += 1
                elif delta < 0:
                    better += 1
                else:
                    worse += 1
            directions[field] = {"candidate_better": better, "tie": tie, "candidate_worse": worse}
        pair_directions[candidate] = directions
    return {
        "arms": arms,
        "candidate_over_low_free": ratios,
        "eligibility": eligibility,
        "pair_directions": pair_directions,
        "batch_wall_seconds": round(max(0.0, float(batch_wall)), 6),
        "baseline_valid": baseline_valid,
        "eligible_candidates": sorted(eligible),
        "selected_candidate": selected,
        "passed": baseline_valid
        and selected is not None
        and float(batch_wall) <= protocol["gates"]["maximum_batch_wall_seconds"],
    }


def validate_result(value: Mapping[str, Any], root: Path = ROOT) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    protocol = prereg.validate_protocol(root)
    rows = value.get("outcomes")
    summary = value.get("summary")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24279_neutral_synthesis_factorial_result"
        or value.get("protocol_id") != prereg.PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(root / prereg.OUTPUT)
        or not isinstance(rows, list)
        or len(rows) != prereg.CASE_COUNT * len(prereg.ARMS)
        or not isinstance(summary, Mapping)
        or summary != summarize(protocol, rows, float(summary["batch_wall_seconds"]))
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.79 result drifted")


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def run(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = prereg.validate_protocol(root)
    if (root / prereg.RESULT).exists() or (root / prereg.RESULT).is_symlink():
        raise FileExistsError(root / prereg.RESULT)
    outcomes: list[dict[str, Any]] = []
    started = time.monotonic()
    lease = protocol["lease"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / lease["path"],
    ):
        for wave in protocol["factorial_contract"]["schedule"]:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=prereg.ARM_CONCURRENCY,
                thread_name_prefix="v24279-synthesis-factorial",
            ) as pool:
                futures = [pool.submit(_run_arm, item) for item in wave]
                outcomes.extend(future.result() for future in futures)
    batch_wall = max(0.0, time.monotonic() - started)
    summary = summarize(protocol, outcomes, batch_wall)
    value = {
        "artifact_version": 1,
        "role": "v24279_neutral_synthesis_factorial_result",
        "created_at_unix": int(time.time()),
        "protocol_id": prereg.PROTOCOL_ID,
        "protocol_sha256": sha256(root / prereg.OUTPUT),
        "outcomes": sorted(outcomes, key=lambda row: (row["case"], row["arm"])),
        "summary": summary,
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
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(value, root)
    publish_new(root / prereg.RESULT, value)
    return value


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "path": str(prereg.RESULT),
                "sha256": sha256(ROOT / prereg.RESULT),
                "passed": result["summary"]["passed"],
                "eligible_candidates": result["summary"]["eligible_candidates"],
                "selected_candidate": result["summary"]["selected_candidate"],
            },
            sort_keys=True,
        )
    )
