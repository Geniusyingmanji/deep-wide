#!/usr/bin/env python3
"""Run one V2.49.23 task from a frozen shared public-page prefix."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
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

from deepwide_agent import v24846_atomic_table_header_30k_profile as parent  # noqa: E402
from deepwide_agent import v24921_target_value_coverage_projector as candidate  # noqa: E402
from deepwide_agent import v24923_target_value_external_contract as contract  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to((ROOT / contract.OUTPUT_ROOT).resolve())
    ):
        raise RuntimeError("V2.49.23 child expected ordinary in-root object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.23 child expected JSON object")
    return value


def _new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _prompt(question: str, evidence: str) -> str:
    return (
        "Return exactly one Markdown table and no prose. Preserve the exact requested "
        "column order and the twelve requested country rows in their visible order. "
        "Read values only from the supplied frozen official World Bank pages. Preserve "
        "the numeric decimal spelling shown in those pages; use Unknown only when a "
        "requested value is absent.\n\nVISIBLE TASK:\n"
        + question
        + "\n\nFROZEN OFFICIAL PAGES:\n"
        + evidence
    )


def _extract_text(response: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if (
                isinstance(content, dict)
                and content.get("type") in {"output_text", "text"}
                and isinstance(content.get("text"), str)
                and content["text"].strip()
            ):
                chunks.append(content["text"].strip())
    direct = response.get("output_text")
    if not chunks and isinstance(direct, str) and direct.strip():
        chunks.append(direct.strip())
    if not chunks:
        raise ValueError("V2.49.23 synthesis response contained no text")
    return "\n".join(chunks)


@contextmanager
def _model_slot():
    directory = ROOT / contract.MODEL_SLOT_DIRECTORY
    deadline = time.monotonic() + contract.TASK_WALL_SECONDS
    handles = []
    try:
        while time.monotonic() < deadline:
            for index in range(contract.MODEL_SLOT_CAP):
                handle = (directory / f"slot_{index:02d}.lock").open(
                    "a+", encoding="utf-8"
                )
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
        raise TimeoutError("V2.49.23 model slot deadline exhausted")
    finally:
        for handle in handles:
            if not handle.closed:
                handle.close()


def _synthesize(question: str, evidence: str) -> tuple[str, dict[str, int]]:
    payload = {
        "model": contract.MODEL["name"],
        "input": _prompt(question, evidence),
        "reasoning": {"effort": contract.MODEL["reasoning_effort"]},
        "service_tier": contract.MODEL["service_tier"],
        "max_output_tokens": contract.MODEL["max_output_tokens"],
        "store": False,
    }
    started = time.monotonic()
    with _model_slot():
        response = requests.post(
            contract.MODEL["proxy_url"],
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=contract.MODEL["timeout_seconds"],
        )
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise ValueError("V2.49.23 synthesis response drifted")
    usage = value.get("usage") if isinstance(value.get("usage"), dict) else {}
    return _extract_text(value), {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
        "provider_attempts": 1,
    }


def build_projections(
    question: str, pages: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    values = {
        "parent_30k": parent.build_projection(question, pages),
        "target_value_30k": candidate.build_projection(question, pages),
    }
    parent_receipt = values["parent_30k"]["content_free_receipt"]
    candidate_receipt = values["target_value_30k"]["content_free_receipt"]
    return {
        "parent_30k": {
            "projection": str(values["parent_30k"]["projection"]),
            "receipt": parent_receipt,
        },
        "target_value_30k": {
            "projection": str(values["target_value_30k"]["projection"]),
            "receipt": candidate_receipt,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--pages", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    task_path = Path(args.task)
    pages_path = Path(args.pages)
    result_path = Path(args.result)
    output = (ROOT / contract.OUTPUT_ROOT).resolve()
    for path in (task_path, pages_path, result_path):
        if path.is_symlink() or not path.resolve(strict=False).is_relative_to(output):
            raise RuntimeError("V2.49.23 child path escaped output root")
    task = _read(task_path)
    if set(task) != {"opaque_id", "question"}:
        raise RuntimeError("V2.49.23 runtime input drifted")
    contract.parse_visible_countries(str(task["question"]))
    page_bundle = _read(pages_path)
    pages = page_bundle.get("pages")
    if not isinstance(pages, list) or len(pages) != len(contract.TARGETS):
        raise RuntimeError("V2.49.23 frozen page vector drifted")
    projections = build_projections(str(task["question"]), pages)
    predictions: dict[str, str] = {}
    usage: dict[str, dict[str, int]] = {}
    for arm in contract.ARMS:
        predictions[arm], usage[arm] = _synthesize(
            str(task["question"]), projections[arm]["projection"]
        )
    projection_receipts = {
        arm: dict(projections[arm]["receipt"]) for arm in contract.ARMS
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24923_target_value_external_task_result",
        "opaque_id": task["opaque_id"],
        "status": "completed",
        "runtime_input_keys": ["opaque_id", "question"],
        "frozen_pages_sha256": contract.sha256(pages_path),
        "predictions": predictions,
        "prediction_sha256": {
            arm: contract.payload_sha256(predictions[arm]) for arm in contract.ARMS
        },
        "projection_sha256": {
            arm: contract.payload_sha256(projections[arm]["projection"])
            for arm in contract.ARMS
        },
        "projection_equal": projections["parent_30k"]["projection"]
        == projections["target_value_30k"]["projection"],
        "projection_receipts": projection_receipts,
        "model_usage": usage,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "same_frozen_pages_model_prompt_output_cap_and_attempt_count": True,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    _new(result_path, value)


if __name__ == "__main__":
    main()
