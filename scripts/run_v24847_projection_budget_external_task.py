#!/usr/bin/env python3
"""Run one V2.48.47 task from a frozen shared raw-page prefix."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24842_atomic_table_header_closure as control  # noqa: E402
from deepwide_agent import v24846_atomic_table_header_30k_profile as candidate  # noqa: E402
from deepwide_agent import v24847_projection_budget_external_contract as contract  # noqa: E402


COUNTRY_BLOCK = re.compile(r"<COUNTRIES>\s*(.*?)\s*</COUNTRIES>", re.S)
COUNTRY_LINE = re.compile(r"^\s*\d+\.\s*(.*?)\s*\[([A-Z]{3})\]\s*$")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("V2.48.47 child expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.47 child expected object")
    return value


def _new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _countries(question: str) -> list[tuple[str, str]]:
    match = COUNTRY_BLOCK.search(question)
    if match is None:
        raise ValueError("V2.48.47 visible country block absent")
    output = []
    for line in match.group(1).splitlines():
        parsed = COUNTRY_LINE.match(line)
        if parsed:
            output.append((parsed.group(1).strip(), parsed.group(2)))
    if len(output) != 4 or len({iso3 for _name, iso3 in output}) != 4:
        raise ValueError("V2.48.47 visible country vector drifted")
    return output


def _prompt(question: str, evidence: str) -> str:
    return (
        "Return exactly one Markdown table and no prose. Preserve the exact requested column order. "
        "Include exactly the four requested country rows in the visible order. Read values only from "
        "the supplied frozen official World Bank pages. Preserve the numeric decimal spelling shown in "
        "the pages; use Unknown only when absent.\n\nVISIBLE TASK:\n"
        + question
        + "\n\nFROZEN OFFICIAL PAGES:\n"
        + evidence
    )


def _extract_text(response: dict[str, Any]) -> str:
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    raise ValueError("V2.48.47 synthesis response contained no text")


def _synthesize(question: str, evidence: str) -> tuple[str, dict[str, int]]:
    payload = {
        "model": contract.MODEL["name"],
        "input": _prompt(question, evidence),
        "reasoning": {"effort": contract.MODEL["reasoning_effort"]},
        "max_output_tokens": contract.MODEL["max_output_tokens"],
        "store": False,
    }
    started = time.monotonic()
    with _model_slot():
        response = requests.post(
            contract.MODEL["proxy_url"], json=payload,
            timeout=contract.MODEL["timeout_seconds"],
        )
    response.raise_for_status()
    value = response.json()
    usage = value.get("usage") if isinstance(value, dict) else None
    return _extract_text(value), {
        "input_tokens": int((usage or {}).get("input_tokens", 0)),
        "output_tokens": int((usage or {}).get("output_tokens", 0)),
        "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
    }


@contextmanager
def _model_slot():
    directory = ROOT / contract.MODEL_SLOT_DIRECTORY
    deadline = time.monotonic() + contract.TASK_WALL_SECONDS
    handles = []
    try:
        while time.monotonic() < deadline:
            for index in range(contract.MODEL_SLOT_CAP):
                path = directory / f"slot_{index:02d}.lock"
                handle = path.open("a+", encoding="utf-8")
                handles.append(handle)
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    handle.close()
                    handles.pop()
                    continue
                yield index
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                return
            time.sleep(0.01)
        raise TimeoutError("V2.48.47 model slot deadline exhausted")
    finally:
        for handle in handles:
            if not handle.closed:
                handle.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--raw-pages", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    task_path = Path(args.task)
    raw_path = Path(args.raw_pages)
    result_path = Path(args.result)
    output = (ROOT / contract.OUTPUT_ROOT).resolve()
    for path in (task_path, raw_path, result_path):
        if path.is_symlink() or not path.resolve(strict=False).is_relative_to(output):
            raise RuntimeError("V2.48.47 child path escaped output root")
    task = _read(task_path)
    if set(task) != {"opaque_id", "question"}:
        raise RuntimeError("V2.48.47 runtime input drifted")
    _countries(str(task["question"]))
    raw = _read(raw_path)
    pages = raw.get("pages")
    if not isinstance(pages, list) or len(pages) != 8:
        raise RuntimeError("V2.48.47 frozen raw pages drifted")
    arm_projection = {
        "atomic_16k": control.build_projection(str(task["question"]), pages),
        "atomic_30k": candidate.build_projection(str(task["question"]), pages),
    }
    predictions: dict[str, str] = {}
    usage: dict[str, dict[str, int]] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for arm in contract.ARMS:
        projection = arm_projection[arm]
        evidence = str(projection["projection"])
        predictions[arm], usage[arm] = _synthesize(str(task["question"]), evidence)
        if arm == "atomic_30k":
            receipts[arm] = projection["content_free_receipt"]
        else:
            receipts[arm] = {
                "projected_rendered_characters": projection["projected_rendered_characters"],
                "selected_table_continuation_block_count": projection["selected_table_continuation_block_count"],
                "table_header_dependency_addition_count": projection["table_header_dependency_addition_count"],
                "orphan_selected_table_continuation_block_count": projection["orphan_selected_table_continuation_block_count"],
                "supported_visible_requirement_group_count": projection["supported_visible_requirement_group_count"],
                "retained_supported_visible_requirement_group_count": projection["retained_supported_visible_requirement_group_count"],
                "contains_question_query_url_host_page_projection_content_or_hash": False,
            }
    value = {
        "artifact_version": 1, "role": "v24847_projection_budget_task_result",
        "opaque_id": task["opaque_id"], "status": "completed", "label_blind": True,
        "runtime_input_keys": ["opaque_id", "question"],
        "raw_page_freeze_sha256": contract.sha256(raw_path),
        "predictions": predictions,
        "prediction_sha256": {arm: contract.payload_sha256(predictions[arm]) for arm in contract.ARMS},
        "projection_receipts": receipts, "model_usage": usage,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    _new(result_path, value)


if __name__ == "__main__":
    main()
