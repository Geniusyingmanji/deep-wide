#!/usr/bin/env python3
"""Run the official DeepWideSearch evaluator with the local Azure Responses proxy.

This script intentionally keeps the official evaluator logic intact and only
patches its LLM backend. It evaluates existing prediction JSONL files, so it
does not call Tavily or rerun search.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import random
import re
import sys
import time
import types
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests


DEFAULT_PROXY_URL = os.environ.get("AZURE_RESPONSES_URL", "http://127.0.0.1:9877/responses")
DEFAULT_MODEL = os.environ.get("AZURE_RESPONSES_MODEL", "gpt-5.6-sol")
DEFAULT_REASONING_EFFORT = os.environ.get("AZURE_REASONING_EFFORT", "low")
OFFICIAL_ROOT = Path("external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch")
EVALUATOR_RUN_CONFIG_VERSION = 2


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
        max_retries: int = 12,
    ):
        self.url = url
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.calls = 0
        self.attempts = 0

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
        last_status: int | None = None
        for attempt in range(1, self.max_retries + 1):
            self.attempts += 1
            response = requests.post(
                self.url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            last_status = response.status_code
            if response.status_code in {408, 409, 429} or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = max(1.0, min(float(retry_after), 120.0))
                except ValueError:
                    delay = min(2**attempt + random.random(), 90.0)
                print(
                    json.dumps(
                        {
                            "event": "judge_retry",
                            "status": response.status_code,
                            "attempt": attempt,
                            "delay_seconds": round(delay, 3),
                        }
                    ),
                    flush=True,
                )
                time.sleep(delay)
                continue
            response.raise_for_status()
            obj = response.json()
            text = self._extract_text(obj)
            if obj.get("status") not in {None, "completed"} and not text:
                raise RuntimeError(
                    f"judge response not completed: {obj.get('status')} {obj.get('error')}"
                )
            if not text:
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 30))
                    continue
                raise RuntimeError("judge response was empty")
            self.calls += 1
            return LocalLLMResponse(content=text)
        raise RuntimeError(
            f"judge request exhausted {self.max_retries} retries "
            f"(last_status={last_status})"
        )


def install_my_utils_shim() -> None:
    if "my_utils" in sys.modules:
        return
    module = types.ModuleType("my_utils")

    def request_api(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("my_utils.request_api is not available in local evaluator mode")

    module.request_api = request_api  # type: ignore[attr-defined]
    sys.modules["my_utils"] = module


def install_datasets_shim() -> None:
    """Allow the released local-file loader without the optional HF package."""
    if "datasets" in sys.modules:
        return
    try:
        __import__("datasets")
        return
    except ModuleNotFoundError:
        pass
    module = types.ModuleType("datasets")

    def load_dataset(*args: Any, **kwargs: Any) -> None:
        del args, kwargs
        raise RuntimeError(
            "Hugging Face datasets is unavailable in local evaluator mode"
        )

    module.load_dataset = load_dataset  # type: ignore[attr-defined]
    sys.modules["datasets"] = module


def install_pandarallel_shim() -> None:
    """Shim the released evaluator's unused import-time initializer."""
    if "pandarallel" in sys.modules:
        return
    try:
        __import__("pandarallel")
        return
    except ModuleNotFoundError:
        pass
    module = types.ModuleType("pandarallel")

    class PandarallelShim:
        @staticmethod
        def initialize(**kwargs: Any) -> None:
            del kwargs

    module.pandarallel = PandarallelShim()  # type: ignore[attr-defined]
    sys.modules["pandarallel"] = module


def install_ipdb_shim() -> None:
    """Satisfy the released evaluator's unused debug-only import."""
    if "ipdb" in sys.modules:
        return
    try:
        __import__("ipdb")
        return
    except ModuleNotFoundError:
        pass
    module = types.ModuleType("ipdb")

    def set_trace() -> None:
        raise RuntimeError("official evaluator attempted to enter an ipdb breakpoint")

    module.set_trace = set_trace  # type: ignore[attr-defined]
    sys.modules["ipdb"] = module


def install_dateparser_shim() -> None:
    """Provide evaluator-only parsing for the benchmark's documented dates."""
    if "dateparser" in sys.modules:
        return
    try:
        __import__("dateparser")
        return
    except ModuleNotFoundError:
        pass
    from dateutil import parser as dateutil_parser

    module = types.ModuleType("dateparser")

    def parse(value: Any, settings: dict[str, Any] | None = None) -> datetime | None:
        del settings
        text = str(value or "").strip()
        if not text or text.casefold() in {"/", "n/a", "null", "none", "不适用"}:
            return None
        unknown_day = re.fullmatch(r"-,\s*((?:18|19|20)\d{2})", text)
        if unknown_day:
            return datetime(int(unknown_day.group(1)), 1, 1)
        chinese = re.fullmatch(
            r"((?:18|19|20)\d{2})年(?:\s*(\d{1,2})月)?(?:\s*(\d{1,2})日)?",
            text,
        )
        if chinese:
            return datetime(
                int(chinese.group(1)),
                int(chinese.group(2) or 1),
                int(chinese.group(3) or 1),
            )
        try:
            return dateutil_parser.parse(text, default=datetime(2000, 1, 1))
        except (ValueError, TypeError, OverflowError):
            return None

    module.parse = parse  # type: ignore[attr-defined]
    sys.modules["dateparser"] = module


def install_number_near_compat(metric_utils: Any) -> None:
    """Default an omitted released-schema number tolerance to 5%."""
    current = metric_utils.metric_function_registry["number_near"]
    if getattr(current, "_deepwide_default_criterion", False):
        return

    def number_near_with_default(
        response: str,
        target: str,
        criterion: float | None,
    ) -> tuple[float, str]:
        return current(response, target, 0.05 if criterion is None else criterion)

    number_near_with_default._deepwide_default_criterion = True  # type: ignore[attr-defined]
    metric_utils.metric_function_registry["number_near"] = number_near_with_default


def _chinese_integer(text: str) -> int | None:
    digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    chars = [char for char in text if char in digits or char in units]
    if not chars:
        return None
    if not any(char in units for char in chars):
        return int("".join(str(digits[char]) for char in chars))
    total = 0
    section = 0
    number = 0
    for char in chars:
        if char in digits:
            number = digits[char]
        elif char == "万":
            total += (section + number) * units[char]
            section = 0
            number = 0
        else:
            section += (number or 1) * units[char]
            number = 0
    return total + section + number


def install_extract_number_compat(metric_utils: Any) -> None:
    """Extend the released numeric preprocessor to Chinese ordinals."""
    current = metric_utils.preprocess_function_registry["extract_number"]
    if getattr(current, "_deepwide_chinese_numerals", False):
        return

    def extract_number_with_chinese(content: str) -> str:
        upstream = current(content)
        if upstream != "NULL":
            return upstream
        match = re.search(r"[零〇一二两三四五六七八九十百千万]+", str(content))
        parsed = _chinese_integer(match.group(0)) if match else None
        return str(parsed) if parsed is not None else upstream

    extract_number_with_chinese._deepwide_chinese_numerals = True  # type: ignore[attr-defined]
    metric_utils.preprocess_function_registry["extract_number"] = extract_number_with_chinese


def validate_metric_row(row: dict[str, Any]) -> None:
    bounded = (
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
    )
    invalid = {
        name: row.get(name)
        for name in bounded
        if not isinstance(row.get(name), (int, float))
        or not 0.0 <= float(row[name]) <= 1.0
    }
    if invalid:
        raise RuntimeError(f"official evaluator returned out-of-range metrics: {invalid}")


def import_official_modules(judge: LocalResponsesJudge) -> dict[str, Any]:
    root = OFFICIAL_ROOT.resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    install_my_utils_shim()
    install_datasets_shim()
    install_pandarallel_shim()
    install_ipdb_shim()
    install_dateparser_shim()

    from eval.evaluation import evaluation as official_eval
    from eval.evaluation import metric_utils
    from eval.evaluation.data_loader import WideSearchQuery, WideSearchResponse
    from eval.utils import llm as official_llm
    from eval.utils.utils import norm_column

    official_llm.llm_completion = judge
    metric_utils.llm_completion = judge
    official_eval.llm_completion = judge

    # Evaluator compatibility workaround: a small number of released tasks use
    # ``number_near`` without a ``criterion`` field.  Upstream forwards None to
    # ``number_near`` and then attempts ``float * None``.  Keep the official
    # evaluator source untouched and apply its conventional 5% tolerance only
    # when the schema omitted a value entirely.
    install_number_near_compat(metric_utils)
    # Released schemas also apply extract_number to Chinese ordinal keys such
    # as 第一章.  Upstream maps every such key to NULL, causing a Cartesian merge
    # and impossible F1 values above one.  Preserve Arabic behavior and add the
    # missing Chinese numeral case locally.
    install_extract_number_compat(metric_utils)
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    except (AttributeError, OSError):
        return
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    _atomic_text(
        path,
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
    )


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    rows = read_jsonl(path)
    rows.append(row)
    write_jsonl_atomic(path, rows)


def _manifest_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def evaluator_source_manifest(root: Path = OFFICIAL_ROOT) -> dict[str, Any]:
    resolved = root.resolve()
    paths = sorted(path for path in (resolved / "eval").rglob("*.py") if path.is_file())
    adapter = Path(__file__).resolve()
    rows = [
        {
            "path": str(path.relative_to(resolved)),
            "sha256": sha256_file(path),
        }
        for path in paths
    ]
    rows.append({"path": "local_adapter/run_official_eval_local.py", "sha256": sha256_file(adapter)})
    return {
        "file_count": len(rows),
        "manifest_sha256": _manifest_digest(rows),
    }


def answer_corpus_manifest(answer_root: Path) -> dict[str, Any]:
    resolved = answer_root.resolve()
    paths = sorted(path for path in resolved.glob("*.csv") if path.is_file())
    rows = [
        {"path": path.name, "sha256": sha256_file(path)} for path in paths
    ]
    return {
        "file_count": len(rows),
        "manifest_sha256": _manifest_digest(rows),
    }


def build_eval_run_contract(
    *,
    predictions_path: Path,
    query_path: Path,
    answer_root: Path,
    predictions: list[dict[str, Any]],
    proxy_url: str,
    model: str,
    reasoning_effort: str,
    judge_max_output_tokens: int,
    judge_timeout: int,
    judge_max_retries: int,
    requested_instance_ids: list[str],
    limit: int,
    official_root: Path = OFFICIAL_ROOT,
) -> dict[str, Any]:
    instance_ids: list[str] = []
    for row in predictions:
        instance_id = row.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            raise ValueError("selected prediction lacks instance_id")
        instance_ids.append(instance_id)
    if len(instance_ids) != len(set(instance_ids)):
        raise ValueError("selected predictions contain duplicate instance_id")
    resolved_predictions = predictions_path.resolve()
    resolved_query = query_path.resolve()
    resolved_answers = answer_root.resolve()
    if not resolved_predictions.is_file() or not resolved_query.is_file():
        raise FileNotFoundError("evaluator prediction/query input is missing")
    if not resolved_answers.is_dir():
        raise FileNotFoundError(resolved_answers)
    selection_protocol = {
        "requested_instance_ids": list(requested_instance_ids),
        "limit": limit,
    }
    return {
        "artifact_version": EVALUATOR_RUN_CONFIG_VERSION,
        "role": "deepwide_official_evaluator_crash_recovery_contract",
        "predictions": {
            "path": str(resolved_predictions),
            "sha256": sha256_file(resolved_predictions),
        },
        "query_data": {
            "path": str(resolved_query),
            "sha256": sha256_file(resolved_query),
        },
        "answers": {
            "root": str(resolved_answers),
            **answer_corpus_manifest(resolved_answers),
        },
        "selected_prediction_count": len(instance_ids),
        "selected_instance_order_sha256": hashlib.sha256(
            json.dumps(instance_ids, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "selection_protocol_sha256": hashlib.sha256(
            json.dumps(
                selection_protocol, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
        "evaluator_source": evaluator_source_manifest(official_root),
        "judge": {
            "proxy_url": proxy_url,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "max_output_tokens": judge_max_output_tokens,
            "timeout_seconds": judge_timeout,
            "max_retries": judge_max_retries,
        },
        "recovery_policy": {
            "explicit_resume_required": True,
            "committed_success_or_error_is_terminal": True,
            "committed_rows_must_be_exact_prediction_prefix": True,
            "canonical_result_file_atomic_replace_per_task": True,
            "selective_error_retry_allowed": False,
        },
        "credentials": "environment-only; not persisted",
    }


def validate_committed_eval_rows(
    rows: list[dict[str, Any]], selected_instance_ids: list[str]
) -> None:
    if len(rows) > len(selected_instance_ids):
        raise RuntimeError("committed evaluator rows exceed selected predictions")
    committed_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("committed evaluator row is not an object")
        instance_id = row.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            raise RuntimeError("committed evaluator row lacks instance_id")
        committed_ids.append(instance_id)
        error = row.get("error")
        if error is None:
            validate_metric_row(row)
        elif not isinstance(error, str) or not error:
            raise RuntimeError("committed evaluator error is malformed")
        elapsed = row.get("elapsed_seconds")
        if (
            not isinstance(elapsed, (int, float))
            or isinstance(elapsed, bool)
            or float(elapsed) < 0
        ):
            raise RuntimeError("committed evaluator elapsed time is invalid")
    if len(committed_ids) != len(set(committed_ids)):
        raise RuntimeError("committed evaluator rows contain duplicate instance_id")
    if committed_ids != selected_instance_ids[: len(committed_ids)]:
        raise RuntimeError("committed evaluator rows are not the exact prediction prefix")


def initialize_or_resume_eval_output(
    out_dir: Path,
    *,
    contract: dict[str, Any],
    selected_instance_ids: list[str],
    resume: bool,
) -> list[dict[str, Any]]:
    config_path = out_dir / "run_config.json"
    result_path = out_dir / "official_eval_results.jsonl"
    if resume:
        if not out_dir.is_dir() or not config_path.is_file():
            raise RuntimeError("evaluator resume requires an existing run contract")
        stored = json.loads(config_path.read_text(encoding="utf-8"))
        if stored != contract:
            raise RuntimeError("evaluator resume contract does not match live inputs")
        rows = read_jsonl(result_path)
        validate_committed_eval_rows(rows, selected_instance_ids)
        return rows
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError("fresh evaluator output directory is not empty")
    out_dir.mkdir(parents=True, exist_ok=True)
    _atomic_text(
        config_path, json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    )
    if result_path.exists():
        raise FileExistsError("fresh evaluator result already exists")
    return []


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
    latest: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    for row in rows:
        instance_id = row.get("instance_id")
        if instance_id is None:
            anonymous.append(row)
        else:
            latest[str(instance_id)] = row
    current_rows = list(latest.values()) + anonymous
    valid_rows = [row for row in current_rows if not row.get("error")]
    error_count = len(current_rows) - len(valid_rows)
    summary: dict[str, Any] = {
        "n": len(current_rows),
        "valid_n": len(valid_rows),
        "errors": error_count,
        "complete": bool(current_rows) and error_count == 0,
        "judge_calls_current_process": judge_calls,
    }
    if valid_rows:
        for name in metric_names:
            vals = [float(row.get(name, 0.0) or 0.0) for row in valid_rows]
            summary[name] = sum(vals) / len(vals)
    else:
        for name in metric_names:
            summary[name] = 0.0
    return summary


def write_summary(out_dir: Path, rows: list[dict[str, Any]], judge_calls: int) -> None:
    summary = build_summary(rows, judge_calls)
    _atomic_text(
        out_dir / "summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    )


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
    parser.add_argument("--judge-max-retries", type=int, default=12)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    predictions_path = Path(args.predictions)
    query_path = Path(args.query_path)
    answer_root = Path(args.answer_root)
    predictions = read_jsonl(predictions_path)
    if args.instance_id:
        wanted = set(args.instance_id)
        predictions = [row for row in predictions if row.get("instance_id") in wanted]
    if args.limit > 0:
        predictions = predictions[: args.limit]
    selected_instance_ids = [str(row.get("instance_id", "")) for row in predictions]
    contract = build_eval_run_contract(
        predictions_path=predictions_path,
        query_path=query_path,
        answer_root=answer_root,
        predictions=predictions,
        proxy_url=args.proxy_url,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        judge_max_output_tokens=args.judge_max_output_tokens,
        judge_timeout=args.judge_timeout,
        judge_max_retries=args.judge_max_retries,
        requested_instance_ids=args.instance_id,
        limit=args.limit,
    )
    result_rows = initialize_or_resume_eval_output(
        out_dir,
        contract=contract,
        selected_instance_ids=selected_instance_ids,
        resume=args.resume,
    )

    judge = LocalResponsesJudge(
        url=args.proxy_url,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.judge_max_output_tokens,
        timeout=args.judge_timeout,
        max_retries=args.judge_max_retries,
    )
    official = import_official_modules(judge)
    queries = load_query_map(query_path, answer_root, official["norm_column"], official["WideSearchQuery"])

    result_path = out_dir / "official_eval_results.jsonl"
    done = {str(row["instance_id"]) for row in result_rows}

    print(
        json.dumps(
            {
                "event": "eval_start",
                "selected": len(predictions),
                "resume_committed": len(done),
                "committed_errors": sum(bool(row.get("error")) for row in result_rows),
                "crash_only_resume": args.resume,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
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
            if str(getattr(eval_result, "msg", "")).startswith("evaluator error:"):
                raise RuntimeError("official evaluator reported an internal error")
            row = dataclasses.asdict(eval_result)
            row["error"] = None
            validate_metric_row(row)
        except Exception as exc:  # noqa: BLE001 - keep long eval resumable
            row = {"instance_id": instance_id, "error": f"{type(exc).__name__}: {exc}"}
        row["elapsed_seconds"] = round(time.time() - start, 3)
        row["judge_calls_current_process"] = judge.calls
        result_rows.append(row)
        write_jsonl_atomic(result_path, result_rows)
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
