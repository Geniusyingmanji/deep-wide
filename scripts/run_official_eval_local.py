#!/usr/bin/env python3
"""Run the official DeepWideSearch evaluator with the local Azure Responses proxy.

This script intentionally keeps the official evaluator logic intact and only
patches its LLM backend. It evaluates existing prediction JSONL files, so it
does not call Tavily or rerun search.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
import time
import types
from pathlib import Path
from typing import Any

import pandas as pd
import requests


DEFAULT_PROXY_URL = os.environ.get("AZURE_RESPONSES_URL", "http://127.0.0.1:9876/responses")
DEFAULT_MODEL = os.environ.get("AZURE_RESPONSES_MODEL", "gpt-5.5")
DEFAULT_REASONING_EFFORT = os.environ.get("AZURE_REASONING_EFFORT", "low")
OFFICIAL_ROOT = Path("external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch")


@dataclasses.dataclass
class LocalLLMResponse:
    content: str


class LocalResponsesJudge:
    def __init__(
        self,
        url: str,
        model: str,
        reasoning_effort: str,
        max_output_tokens: int,
        timeout: int,
    ):
        self.url = url
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self.calls = 0

    @staticmethod
    def _extract_text(obj: dict[str, Any]) -> str:
        chunks: list[str] = []
        for item in obj.get("output", []) or []:
            if item.get("type") != "message":
                continue
            for content in item.get("content", []) or []:
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text", ""))
        if chunks:
            return "\n".join(chunks).strip()
        return str(obj.get("output_text") or "").strip()

    @staticmethod
    def _normalize_messages(messages: str | list[dict[str, Any]]) -> list[dict[str, str]]:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        normalized: list[dict[str, str]] = []
        has_system = any(msg.get("role") == "system" for msg in messages)
        if not has_system:
            normalized.append(
                {
                    "role": "system",
                    "content": (
                        "You are a strict benchmark evaluator. Follow the user's scoring "
                        "instructions exactly. If JSON is requested, wrap the final JSON in "
                        "a ```json fenced code block. Keep any reasoning concise."
                    ),
                }
            )
        for msg in messages:
            normalized.append({"role": str(msg.get("role", "user")), "content": str(msg.get("content", ""))})
        return normalized

    def __call__(
        self,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model_config_name: str | None = None,
    ) -> LocalLLMResponse:
        del tools, model_config_name
        payload = {
            "model": self.model,
            "input": self._normalize_messages(messages),
            "max_output_tokens": self.max_output_tokens,
            "reasoning": {"effort": self.reasoning_effort},
        }
        response = requests.post(
            self.url,
            headers={"Authorization": "Bearer dummy", "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        self.calls += 1
        response.raise_for_status()
        obj = response.json()
        text = self._extract_text(obj)
        if obj.get("status") not in {None, "completed"} and not text:
            raise RuntimeError(f"judge response not completed: {obj.get('status')} {obj.get('error')}")
        if not text:
            raise RuntimeError("judge response was empty")
        return LocalLLMResponse(content=text)


def install_my_utils_shim() -> None:
    if "my_utils" in sys.modules:
        return
    module = types.ModuleType("my_utils")

    def request_api(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("my_utils.request_api is not available in local evaluator mode")

    module.request_api = request_api  # type: ignore[attr-defined]
    sys.modules["my_utils"] = module


def import_official_modules(judge: LocalResponsesJudge) -> dict[str, Any]:
    root = OFFICIAL_ROOT.resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    install_my_utils_shim()

    from eval.evaluation import evaluation as official_eval
    from eval.evaluation import metric_utils
    from eval.evaluation.data_loader import WideSearchQuery, WideSearchResponse
    from eval.utils import llm as official_llm
    from eval.utils.utils import norm_column

    official_llm.llm_completion = judge
    metric_utils.llm_completion = judge
    official_eval.llm_completion = judge
    return {
        "evaluate_single_query": official_eval.evaluate_single_query,
        "WideSearchQuery": WideSearchQuery,
        "WideSearchResponse": WideSearchResponse,
        "norm_column": norm_column,
    }


def load_query_map(query_path: Path, answer_root: Path, norm_column: Any, query_cls: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    with query_path.open(encoding="utf-8") as fh:
        for line in fh:
            item = json.loads(line)
            evaluation = item["evaluation"]
            if isinstance(evaluation, str):
                evaluation = json.loads(evaluation)
            answer_path = answer_root / f"{item['instance_id']}.csv"
            if not answer_path.exists():
                continue
            answer = pd.read_csv(answer_path)
            answer.columns = [norm_column(str(col).strip()) for col in answer.columns]
            required = evaluation["required"]
            missing = [col for col in required if col not in answer.columns]
            if missing:
                raise RuntimeError(f"{item['instance_id']} answer missing columns: {missing}")
            answer = answer[required]
            out[item["instance_id"]] = query_cls(
                instance_id=item["instance_id"],
                query=item.get("query") or item.get("question", ""),
                entity=item.get("entity", ""),
                language=item.get("language", ""),
                topic=item.get("topic", ""),
                evaluation=evaluation,
                answer=answer,
            )
    return out


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()


def safe_filename(instance_id: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", instance_id)


def build_summary(rows: list[dict[str, Any]], judge_calls: int) -> dict[str, Any]:
    metric_names = [
        "score",
        "entity_acc",
        "precision_by_row",
        "recall_by_row",
        "f1_by_row",
        "precision_by_item",
        "recall_by_item",
        "f1_by_item",
        "column_precision",
        "column_recall",
        "column_f1",
    ]
    summary: dict[str, Any] = {
        "n": len(rows),
        "errors": sum(1 for row in rows if row.get("error")),
        "judge_calls_current_process": judge_calls,
    }
    if rows:
        for name in metric_names:
            vals = [float(row.get(name, 0.0) or 0.0) for row in rows]
            summary[name] = sum(vals) / len(vals)
    else:
        for name in metric_names:
            summary[name] = 0.0
    return summary


def write_summary(out_dir: Path, rows: list[dict[str, Any]], judge_calls: int) -> None:
    summary = build_summary(rows, judge_calls)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", default="outputs/deepwide_full/deepwide_full_20260621_072017/predictions.jsonl")
    parser.add_argument("--query-path", default=str(OFFICIAL_ROOT / "data/overall_20250916.jsonl"))
    parser.add_argument("--answer-root", default=str(OFFICIAL_ROOT / "data/overall_20250916_tables"))
    parser.add_argument("--out-dir", default="outputs/deepwide_official_eval/local_gpt55_latest")
    parser.add_argument("--instance-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0, help="0 means all selected predictions")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--judge-max-output-tokens", type=int, default=8192)
    parser.add_argument("--judge-timeout", type=int, default=600)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    (out_dir / "run_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    judge = LocalResponsesJudge(
        url=args.proxy_url,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.judge_max_output_tokens,
        timeout=args.judge_timeout,
    )
    official = import_official_modules(judge)
    queries = load_query_map(Path(args.query_path), Path(args.answer_root), official["norm_column"], official["WideSearchQuery"])
    predictions = read_jsonl(Path(args.predictions))
    if args.instance_id:
        wanted = set(args.instance_id)
        predictions = [row for row in predictions if row.get("instance_id") in wanted]
    if args.limit > 0:
        predictions = predictions[: args.limit]

    result_path = out_dir / "official_eval_results.jsonl"
    done = {row.get("instance_id") for row in read_jsonl(result_path)} if args.resume else set()
    result_rows = read_jsonl(result_path) if args.resume else []

    print(json.dumps({"event": "eval_start", "selected": len(predictions), "resume_done": len(done)}, ensure_ascii=False), flush=True)
    for idx, pred in enumerate(predictions, start=1):
        instance_id = pred["instance_id"]
        if instance_id in done:
            print(json.dumps({"event": "skip_done", "idx": idx, "instance_id": instance_id}, ensure_ascii=False), flush=True)
            continue
        start = time.time()
        row: dict[str, Any]
        try:
            query = queries[instance_id]
            response = official["WideSearchResponse"](
                instance_id=instance_id,
                response=pred.get("prediction", ""),
                messages=pred.get("messages") or [],
                trial_idx=pred.get("rollout_id", 1),
            )
            detail_path = out_dir / "details" / f"{safe_filename(instance_id)}.csv"
            detail_path.parent.mkdir(parents=True, exist_ok=True)
            eval_result = official["evaluate_single_query"](
                query,
                response,
                str(detail_path),
                args.model,
            )
            row = dataclasses.asdict(eval_result)
            row["error"] = None
        except Exception as exc:  # noqa: BLE001 - keep long eval resumable
            row = {"instance_id": instance_id, "error": f"{type(exc).__name__}: {exc}"}
        row["elapsed_seconds"] = round(time.time() - start, 3)
        row["judge_calls_current_process"] = judge.calls
        append_jsonl(result_path, row)
        result_rows.append(row)
        write_summary(out_dir, result_rows, judge.calls)
        print(
            json.dumps(
                {
                    "event": "eval_done",
                    "idx": idx,
                    "instance_id": instance_id,
                    "score": row.get("score"),
                    "entity_acc": row.get("entity_acc"),
                    "f1_by_row": row.get("f1_by_row"),
                    "f1_by_item": row.get("f1_by_item"),
                    "column_f1": row.get("column_f1"),
                    "error": row.get("error"),
                    "elapsed_seconds": row["elapsed_seconds"],
                    "running_n": len(result_rows),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    write_summary(out_dir, result_rows, judge.calls)
    print("SUMMARY", json.dumps(build_summary(result_rows, judge.calls), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
