#!/usr/bin/env python3
"""Small DeepWideSearch smoke runner.

This is intentionally lightweight:
- no secrets are stored in the repo;
- Tavily keys are read from TAVILY_API_KEYS;
- GPT-5.5 is called through the local Azure Responses proxy;
- evaluation is an approximate local row/item F1 for fast feedback.

The official DeepWideSearch evaluator should still be used for final numbers.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import difflib
import json
import os
import re
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests


AZURE_RESPONSES_URL = os.environ.get("AZURE_RESPONSES_URL", "http://127.0.0.1:9876/responses")
DEFAULT_MODEL = os.environ.get("AZURE_RESPONSES_MODEL", "gpt-5.5")
DEFAULT_REASONING_EFFORT = os.environ.get("AZURE_REASONING_EFFORT", "low")


@dataclasses.dataclass
class ModelResult:
    text: str
    usage: dict[str, Any]
    raw_id: str | None = None


def extract_response_text(obj: dict[str, Any]) -> str:
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


def call_gpt(system: str, user: str, *, model: str = DEFAULT_MODEL, max_output_tokens: int = 4096) -> ModelResult:
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": DEFAULT_REASONING_EFFORT},
    }
    response = requests.post(
        AZURE_RESPONSES_URL,
        headers={"Authorization": "Bearer dummy", "Content-Type": "application/json"},
        json=payload,
        timeout=600,
    )
    response.raise_for_status()
    obj = response.json()
    text = extract_response_text(obj)
    if obj.get("status") != "completed" and not text:
        raise RuntimeError(f"model response not completed: {obj.get('status')} {obj.get('error')}")
    return ModelResult(text=text, usage=obj.get("usage", {}) or {}, raw_id=obj.get("id"))


def get_tavily_keys() -> list[str]:
    raw = os.environ.get("TAVILY_API_KEYS", "")
    keys = [part.strip() for part in re.split(r"[\s,]+", raw) if part.strip()]
    if not keys:
        raise RuntimeError("TAVILY_API_KEYS is not set")
    return keys


class TavilyClient:
    def __init__(self, keys: list[str]):
        self.keys = keys
        self.idx = 0
        self.calls = 0

    def search(self, query: str, *, max_results: int = 8, search_depth: str = "advanced") -> dict[str, Any]:
        last_error: Exception | None = None
        for offset in range(len(self.keys)):
            key = self.keys[(self.idx + offset) % len(self.keys)]
            body = {
                "api_key": key,
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": False,
            }
            try:
                response = requests.post("https://api.tavily.com/search", json=body, timeout=60)
                self.calls += 1
                if response.status_code in {401, 403, 429}:
                    last_error = RuntimeError(f"Tavily status {response.status_code}")
                    continue
                response.raise_for_status()
                self.idx = (self.idx + offset) % len(self.keys)
                return response.json()
            except Exception as exc:  # noqa: BLE001 - rotate keys on API/network failure
                last_error = exc
                continue
        raise RuntimeError(f"all Tavily keys failed; last_error={last_error}")


def load_tasks(query_path: Path) -> list[dict[str, Any]]:
    tasks = []
    with query_path.open(encoding="utf-8") as fh:
        for line in fh:
            item = json.loads(line)
            if isinstance(item.get("evaluation"), str):
                item["evaluation"] = json.loads(item["evaluation"])
            tasks.append(item)
    return tasks


def select_tasks(
    tasks: list[dict[str, Any]],
    answer_root: Path,
    language: str,
    limit: int,
    max_rows: int | None,
    start_index: int = 0,
) -> list[dict[str, Any]]:
    selected = []
    for item in tasks[start_index:]:
        if language and language.lower() not in {"all", "*"} and item.get("language") != language:
            continue
        answer_path = answer_root / f"{item['instance_id']}.csv"
        if not answer_path.exists():
            continue
        if max_rows is not None:
            try:
                rows = len(pd.read_csv(answer_path))
            except Exception:
                continue
            if rows > max_rows:
                continue
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def parse_json_list(text: str) -> list[str]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return [str(x).strip() for x in obj if str(x).strip()]
        if isinstance(obj, dict):
            for key in ("queries", "search_queries"):
                if isinstance(obj.get(key), list):
                    return [str(x).strip() for x in obj[key] if str(x).strip()]
    except json.JSONDecodeError:
        pass
    lines = [re.sub(r"^[-*\d.\s]+", "", line).strip() for line in text.splitlines()]
    return [line for line in lines if line][:6]


def make_search_queries(task: dict[str, Any], model: str, max_output_tokens: int) -> tuple[list[str], dict[str, Any]]:
    system = "You design concise web search queries for a benchmark search agent. Return only JSON."
    user = f"""Task:
{task['question']}

Generate 6 diverse web search queries that can solve the hidden entity identification and the requested table.
Do not use any benchmark metadata or ground truth. Return a JSON array of strings only."""
    result = call_gpt(system, user, model=model, max_output_tokens=max_output_tokens)
    queries = parse_json_list(result.text)
    if not queries:
        queries = [task["question"][:400]]
    return queries[:6], {"text": result.text, "usage": result.usage, "response_id": result.raw_id}


def gather_evidence(tavily: TavilyClient, queries: list[str], max_results: int) -> list[dict[str, str]]:
    seen: set[str] = set()
    evidence: list[dict[str, str]] = []
    for query in queries:
        data = tavily.search(query, max_results=max_results)
        if data.get("answer"):
            evidence.append({"query": query, "title": "Tavily answer", "url": "", "content": str(data["answer"])})
        for result in data.get("results", []) or []:
            url = str(result.get("url", ""))
            key = url or str(result.get("title", "")) + str(result.get("content", ""))
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "query": query,
                    "title": str(result.get("title", "")),
                    "url": url,
                    "content": str(result.get("content", "")),
                }
            )
    return evidence


def merge_evidence(existing: list[dict[str, str]], new_items: list[dict[str, str]]) -> list[dict[str, str]]:
    merged = list(existing)
    seen = {item.get("url") or (item.get("title", "") + item.get("content", "")) for item in merged}
    for item in new_items:
        key = item.get("url") or (item.get("title", "") + item.get("content", ""))
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def format_evidence(evidence: list[dict[str, str]], max_chars: int = 30000) -> str:
    blocks = []
    used = 0
    for idx, ev in enumerate(evidence, start=1):
        block = (
            f"[{idx}] Query: {ev['query']}\n"
            f"Title: {ev['title']}\n"
            f"URL: {ev['url']}\n"
            f"Snippet: {ev['content']}\n"
        )
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n".join(blocks)


def solve_task(
    task: dict[str, Any],
    evidence: list[dict[str, str]],
    model: str,
    max_output_tokens: int,
    evidence_max_chars: int,
) -> tuple[str, dict[str, Any]]:
    system = (
        "You are a careful DeepWideSearch agent. Use the supplied web evidence to answer the task. "
        "Return exactly one Markdown table fenced as ```markdown ... ```. "
        "Do not add prose outside the fenced table. If a cell is unknown, use / or nan as requested. "
        "For wide table tasks, do not omit a plausible row just because some requested attributes are unavailable; "
        "include the row with unknown cells marked as requested."
    )
    user = f"""Question:
{task['question']}

Retrieved evidence:
{format_evidence(evidence, max_chars=evidence_max_chars)}

Now produce the requested final table. Respect the exact requested column order and output language."""
    result = call_gpt(system, user, model=model, max_output_tokens=max_output_tokens)
    return result.text, {"usage": result.usage, "response_id": result.raw_id}


def make_followup_queries(task: dict[str, Any], evidence: list[dict[str, str]], model: str, max_output_tokens: int) -> tuple[list[str], dict[str, Any]]:
    system = "You are a search strategist. Return only JSON."
    user = f"""Task:
{task['question']}

Initial retrieved evidence:
{format_evidence(evidence, max_chars=12000)}

Infer the most likely candidate person/entity from the evidence, then generate 6 follow-up web search queries to fill the requested table.
Queries should include the candidate name when likely, and should target official bios, resumes, interviews, LinkedIn-like pages, company pages, or source pages for the requested columns.
Return a JSON object with keys "candidate" and "queries"."""
    result = call_gpt(system, user, model=model, max_output_tokens=max_output_tokens)
    text = result.text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    candidate = ""
    queries: list[str] = []
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            candidate = str(obj.get("candidate", "")).strip()
            if isinstance(obj.get("queries"), list):
                queries = [str(x).strip() for x in obj["queries"] if str(x).strip()]
    except json.JSONDecodeError:
        queries = parse_json_list(text)
    return queries[:6], {"text": result.text, "candidate": candidate, "usage": result.usage, "response_id": result.raw_id}


def norm_col(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(text)).lower()


def norm_cell(text: Any) -> str:
    s = str(text if text is not None else "")
    s = (
        s.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00a0", " ")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
    )
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = s.strip('"\'`')
    return s


def norm_key_cell(text: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", norm_cell(text))


def soft_equal(a: Any, b: Any) -> bool:
    aa, bb = norm_cell(a), norm_cell(b)
    if aa == bb:
        return True
    if not aa or not bb:
        return False
    return difflib.SequenceMatcher(None, aa, bb).ratio() >= 0.88


def extract_markdown_table(response: str) -> pd.DataFrame | None:
    matches = re.findall(r"```markdown\s*(.*?)```", response, flags=re.DOTALL | re.IGNORECASE)
    if not matches:
        matches = re.findall(r"((?:\|.*\|[ \t]*\n?)+)", response)
    if not matches:
        return None
    table = matches[-1].strip()
    lines = []
    for line in table.splitlines():
        if "|" not in line:
            continue
        if set(line.strip()).issubset(set("|-: ")):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        lines.append("|" + "|".join(parts) + "|")
    if not lines:
        return None
    try:
        return pd.read_csv(StringIO("\n".join(lines)), sep="|").loc[:, lambda df: ~df.columns.str.startswith("Unnamed")]
    except Exception:
        return None


def align_columns(pred: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame | None:
    pred = pred.copy()
    col_map = {}
    pred_norm = {norm_col(col): col for col in pred.columns}
    for req in required_columns:
        nreq = norm_col(req)
        if nreq in pred_norm:
            col_map[pred_norm[nreq]] = req
            continue
        best = None
        best_score = 0.0
        for pnorm, pcol in pred_norm.items():
            score = difflib.SequenceMatcher(None, nreq, pnorm).ratio()
            if score > best_score:
                best = pcol
                best_score = score
        if best is not None and best_score >= 0.82:
            col_map[best] = req
    pred.rename(columns=col_map, inplace=True)
    if not set(required_columns).issubset(set(pred.columns)):
        return None
    return pred[required_columns]


def prf(tp: int, pred_n: int, gold_n: int) -> dict[str, float]:
    precision = tp / pred_n if pred_n else 0.0
    recall = tp / gold_n if gold_n else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_prediction(task: dict[str, Any], answer_root: Path, prediction: str) -> dict[str, Any]:
    required = task["evaluation"]["required"]
    unique = task["evaluation"]["unique_columns"]
    gold = pd.read_csv(answer_root / f"{task['instance_id']}.csv")
    gold.columns = [col.strip() for col in gold.columns]
    gold = align_columns(gold, required)
    pred_raw = extract_markdown_table(prediction)
    if pred_raw is None:
        return {"score": 0.0, "column_f1": 0.0, "row": prf(0, 0, len(gold) if gold is not None else 0), "item": prf(0, 0, 0), "parse_ok": False}
    pred = align_columns(pred_raw, required)
    column_tp = len(set(norm_col(c) for c in pred_raw.columns) & set(norm_col(c) for c in required))
    column_metrics = prf(column_tp, len(pred_raw.columns), len(required))
    if gold is None or pred is None:
        return {"score": 0.0, "column_f1": column_metrics["f1"], "row": prf(0, len(pred_raw), len(gold) if gold is not None else 0), "item": prf(0, 0, 0), "parse_ok": True}

    def key(row: pd.Series) -> tuple[str, ...]:
        return tuple(norm_key_cell(row[col]) for col in unique)

    gold_by_key = {key(row): row for _, row in gold.iterrows()}
    pred_by_key = {key(row): row for _, row in pred.iterrows()}
    row_tp = len(set(gold_by_key) & set(pred_by_key))
    row_metrics = prf(row_tp, len(pred_by_key), len(gold_by_key))

    item_tp = 0
    item_pred = len(pred_by_key) * len(required)
    item_gold = len(gold_by_key) * len(required)
    for k, pred_row in pred_by_key.items():
        gold_row = gold_by_key.get(k)
        if gold_row is None:
            continue
        for col in required:
            if soft_equal(pred_row[col], gold_row[col]):
                item_tp += 1
    item_metrics = prf(item_tp, item_pred, item_gold)

    exact = 0.0
    if len(gold_by_key) == len(pred_by_key) and row_tp == len(gold_by_key) and item_tp == item_gold:
        exact = 1.0
    return {
        "score": exact,
        "column_f1": column_metrics["f1"],
        "row": row_metrics,
        "item": item_metrics,
        "parse_ok": True,
        "pred_rows": len(pred_by_key),
        "gold_rows": len(gold_by_key),
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_summary(metric_rows: list[dict[str, Any]], tavily_calls: int | None = None) -> dict[str, Any]:
    if not metric_rows:
        summary: dict[str, Any] = {
            "n": 0,
            "score": 0.0,
            "row_f1": 0.0,
            "item_f1": 0.0,
            "column_f1": 0.0,
        }
    else:
        summary = {
            "n": len(metric_rows),
            "score": sum(row["score"] for row in metric_rows) / len(metric_rows),
            "row_f1": sum(row["row"]["f1"] for row in metric_rows) / len(metric_rows),
            "item_f1": sum(row["item"]["f1"] for row in metric_rows) / len(metric_rows),
            "column_f1": sum(row["column_f1"] for row in metric_rows) / len(metric_rows),
        }
    if tavily_calls is not None:
        summary["tavily_calls_current_process"] = tavily_calls
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-path", default="external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/data/overall_20250916.jsonl")
    parser.add_argument("--answer-root", default="external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/data/overall_20250916_tables")
    parser.add_argument("--out-dir", default="outputs/deepwide_smoke/latest")
    parser.add_argument("--language", default="en")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--max-rows", type=int, default=8)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--instance-id", default="")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--tavily-results", type=int, default=8)
    parser.add_argument("--query-max-output-tokens", type=int, default=900)
    parser.add_argument("--solve-max-output-tokens", type=int, default=3500)
    parser.add_argument("--evidence-max-chars", type=int, default=20000)
    parser.add_argument("--followup", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--task-sleep", type=float, default=0.0)
    args = parser.parse_args()

    query_path = Path(args.query_path)
    answer_root = Path(args.answer_root)
    out_dir = Path(args.out_dir)
    tasks = load_tasks(query_path)
    max_rows = None if args.max_rows <= 0 else args.max_rows
    if args.instance_id:
        selected = [task for task in tasks if task["instance_id"] == args.instance_id]
    else:
        selected = select_tasks(tasks, answer_root, args.language, args.limit, max_rows, args.start_index)
    if not selected:
        raise RuntimeError("no tasks selected")

    out_dir.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    config["tavily_keys"] = "<redacted>"
    config["selected_count"] = len(selected)
    (out_dir / "run_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dry_run:
        by_lang: dict[str, int] = {}
        by_topic: dict[str, int] = {}
        for task in selected:
            by_lang[task.get("language", "unknown")] = by_lang.get(task.get("language", "unknown"), 0) + 1
            by_topic[task.get("topic", "unknown")] = by_topic.get(task.get("topic", "unknown"), 0) + 1
        print(json.dumps({"selected": len(selected), "by_language": by_lang, "by_topic": by_topic}, ensure_ascii=False, indent=2))
        return

    tavily = TavilyClient(get_tavily_keys())
    predictions_path = out_dir / "predictions.jsonl"
    traces_path = out_dir / "traces.jsonl"
    metrics_jsonl_path = out_dir / "metrics.jsonl"
    metric_rows: list[dict[str, Any]] = read_jsonl(metrics_jsonl_path)
    done = {row.get("instance_id") for row in read_jsonl(predictions_path)} if args.resume else set()

    for idx, task in enumerate(selected, start=1):
        if args.resume and task["instance_id"] in done:
            print(json.dumps({"event": "skip_done", "idx": idx, "instance_id": task["instance_id"]}, ensure_ascii=False), flush=True)
            continue
        start = time.time()
        print(json.dumps({"event": "task_start", "idx": idx, "instance_id": task["instance_id"]}, ensure_ascii=False), flush=True)
        try:
            queries, query_trace = make_search_queries(task, args.model, args.query_max_output_tokens)
            print(json.dumps({"event": "queries_ready", "instance_id": task["instance_id"], "queries": len(queries)}, ensure_ascii=False), flush=True)
            evidence = gather_evidence(tavily, queries, args.tavily_results)
            print(json.dumps({"event": "evidence_ready", "instance_id": task["instance_id"], "evidence_count": len(evidence)}, ensure_ascii=False), flush=True)
            followup_trace = None
            if args.followup:
                followup_queries, followup_trace = make_followup_queries(task, evidence, args.model, args.query_max_output_tokens)
                print(
                    json.dumps(
                        {
                            "event": "followup_queries_ready",
                            "instance_id": task["instance_id"],
                            "candidate": followup_trace.get("candidate") if followup_trace else "",
                            "queries": len(followup_queries),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                followup_evidence = gather_evidence(tavily, followup_queries, args.tavily_results)
                evidence = merge_evidence(evidence, followup_evidence)
                print(json.dumps({"event": "followup_evidence_ready", "instance_id": task["instance_id"], "evidence_count": len(evidence)}, ensure_ascii=False), flush=True)
            prediction, solve_trace = solve_task(
                task,
                evidence,
                args.model,
                args.solve_max_output_tokens,
                args.evidence_max_chars,
            )
            metrics = evaluate_prediction(task, answer_root, prediction)
            error = None
        except Exception as exc:  # noqa: BLE001 - full-run robustness
            prediction = ""
            queries = []
            query_trace = {}
            evidence = []
            followup_trace = None
            solve_trace = {}
            metrics = {
                "score": 0.0,
                "column_f1": 0.0,
                "row": prf(0, 0, 0),
                "item": prf(0, 0, 0),
                "parse_ok": False,
            }
            error = f"{type(exc).__name__}: {exc}"
            print(json.dumps({"event": "task_error", "instance_id": task["instance_id"], "error": error}, ensure_ascii=False), file=sys.stderr, flush=True)
        elapsed = time.time() - start

        prediction_row = {
            "instance_id": task["instance_id"],
            "question": task["question"],
            "rollout_id": 1,
            "prediction": prediction,
            "messages": [
                {"role": "user", "content": task["question"]},
                {"role": "assistant", "content": prediction},
            ],
        }
        metric_row = {"instance_id": task["instance_id"], "error": error, **metrics}
        trace_row = {
            "instance_id": task["instance_id"],
            "error": error,
            "queries": queries,
            "followup": followup_trace,
            "evidence_count": len(evidence),
            "evidence": evidence,
            "query_generation": query_trace,
            "solve": solve_trace,
            "metrics": metrics,
            "elapsed_seconds": elapsed,
        }

        append_jsonl(predictions_path, prediction_row)
        append_jsonl(metrics_jsonl_path, metric_row)
        append_jsonl(traces_path, trace_row)
        metric_rows.append(metric_row)
        (out_dir / "metrics.json").write_text(json.dumps(metric_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = build_summary(metric_rows, tavily.calls)
        (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "idx": idx,
                    "instance_id": task["instance_id"],
                    "score": metrics["score"],
                    "row_f1": metrics["row"]["f1"],
                    "item_f1": metrics["item"]["f1"],
                    "column_f1": metrics["column_f1"],
                    "elapsed_seconds": round(elapsed, 1),
                    "running_n": summary["n"],
                    "running_row_f1": summary["row_f1"],
                    "running_item_f1": summary["item_f1"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if args.task_sleep > 0:
            time.sleep(args.task_sleep)

    summary = build_summary(metric_rows, tavily.calls)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
