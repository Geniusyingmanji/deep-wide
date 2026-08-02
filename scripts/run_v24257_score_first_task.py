#!/usr/bin/env python3
"""Run one V2.42.57 task in a child process.

The parent executor supplies one exact visible-task JSON file and one pristine
result path.  Safe progress receipts contain counts only; they never contain a
question, query, URL, page, prediction, answer, credential, or evaluator data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import AnthropicSearchClient  # noqa: E402
from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    run_score_first_task,
    validate_score_first_result,
    validate_visible_task,
)


def _ordinary_under(path: Path, root: Path) -> Path:
    target = path.resolve(strict=False)
    base = root.resolve()
    if not target.is_relative_to(base):
        raise ValueError("V2.42.57 task path escaped its allowed root")
    if path.is_symlink() or target.is_symlink():
        raise ValueError("V2.42.57 task path may not be a symlink")
    return target


def _read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _atomic_new(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _atomic_progress(path: Path, value: dict) -> None:
    if value.get("role") != "v24257_score_first_safe_progress":
        raise ValueError("unsafe progress role")
    if value.get("contains_question_query_url_page_prediction_or_answer") is not False:
        raise ValueError("unsafe progress payload")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--proxy-url", default="http://127.0.0.1:9878/responses")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--service-tier", default="priority")
    parser.add_argument("--model-timeout", type=int, default=180)
    parser.add_argument("--model-max-retries", type=int, default=2)
    parser.add_argument("--search-model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--search-timeout", type=int, default=90)
    parser.add_argument("--search-max-retries", type=int, default=2)
    parser.add_argument("--search-workers", type=int, default=4)
    parser.add_argument("--fetch-workers", type=int, default=8)
    parser.add_argument("--fetch-timeout", type=int, default=20)
    parser.add_argument("--wall-seconds", type=float, default=900)
    parser.add_argument("--model-calls", type=int, default=3)
    parser.add_argument("--search-queries", type=int, default=12)
    parser.add_argument("--fetch-targets", type=int, default=24)
    parser.add_argument("--search-results-per-query", type=int, default=4)
    parser.add_argument("--evidence-chars", type=int, default=120_000)
    parser.add_argument("--page-chars", type=int, default=6_000)
    args = parser.parse_args()

    task_path = _ordinary_under(Path(args.task), ROOT / "outputs")
    result_path = _ordinary_under(Path(args.result), ROOT / "outputs")
    progress_path = _ordinary_under(Path(args.progress), ROOT / "outputs")
    if not task_path.is_file():
        raise FileNotFoundError("V2.42.57 task input is absent")
    if result_path.exists() or result_path.is_symlink():
        raise FileExistsError("V2.42.57 result already exists")
    task = validate_visible_task(_read_object(task_path))
    limits = ScoreFirstLimits(
        wall_seconds=args.wall_seconds,
        model_calls=args.model_calls,
        search_queries=args.search_queries,
        fetch_targets=args.fetch_targets,
        search_results_per_query=args.search_results_per_query,
        evidence_chars=args.evidence_chars,
        page_chars=args.page_chars,
    )
    limits.validate()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        raise RuntimeError("ANTHROPIC_API_KEY is unavailable")
    model = ResponsesClient(
        args.proxy_url,
        args.model,
        reasoning_effort=args.reasoning_effort,
        service_tier=args.service_tier,
        timeout=args.model_timeout,
        max_retries=args.model_max_retries,
    )
    search = AnthropicSearchClient(
        anthropic_key,
        model=args.search_model,
        timeout=args.search_timeout,
        max_retries=args.search_max_retries,
        max_workers=args.search_workers,
        max_uses=1,
        max_output_tokens=1_000,
        fetch_pages=False,
        fetch_workers=args.fetch_workers,
        fetch_timeout=args.fetch_timeout,
        max_page_chars=args.page_chars,
    )
    result = run_score_first_task(
        task,
        model=model,
        search=search,
        limits=limits,
        progress=lambda value: _atomic_progress(progress_path, dict(value)),
    )
    validate_score_first_result(result)
    _atomic_new(result_path, result)


if __name__ == "__main__":
    main()
