#!/usr/bin/env python3
"""Run one shared-prefix V2.42.65 paired task under the global GPT limiter."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import AnthropicSearchClient  # noqa: E402
from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
)
from deepwide_agent.v24265_paired_normalizer_runtime import (  # noqa: E402
    run_paired_task,
    validate_paired_result,
)
from scripts.run_v24257_score_first_task import (  # noqa: E402
    _atomic_new,
    _ordinary_under,
    _read_object,
)


def _progress(path: Path, value: dict) -> None:
    if (
        value.get("role") != "v24265_paired_safe_progress"
        or value.get(
            "contains_question_query_url_page_prediction_answer_or_opaque_id"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise ValueError("unsafe V2.42.65 progress payload")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            import json

            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--model-slot-directory", required=True)
    parser.add_argument("--model-slot-receipt", required=True)
    parser.add_argument("--model-slot-cap", type=int, required=True)
    parser.add_argument("--model-slot-pool-id", required=True)
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
    parser.add_argument("--wall-seconds", type=float, default=600)
    parser.add_argument("--model-calls", type=int, default=3)
    parser.add_argument("--search-queries", type=int, default=8)
    parser.add_argument("--fetch-targets", type=int, default=16)
    parser.add_argument("--search-results-per-query", type=int, default=3)
    parser.add_argument("--evidence-chars", type=int, default=100_000)
    parser.add_argument("--page-chars", type=int, default=5_000)
    args = parser.parse_args()

    task_path = _ordinary_under(Path(args.task), ROOT / "outputs")
    result_path = _ordinary_under(Path(args.result), ROOT / "outputs")
    progress_path = _ordinary_under(Path(args.progress), ROOT / "outputs")
    receipt_path = _ordinary_under(
        Path(args.model_slot_receipt), ROOT / "outputs"
    )
    slot_directory = Path(args.model_slot_directory)
    if (
        not task_path.is_file()
        or result_path.exists()
        or result_path.is_symlink()
        or receipt_path.exists()
        or receipt_path.is_symlink()
    ):
        raise RuntimeError("V2.42.65 child execution surface drifted")
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
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is unavailable")
    inner = ResponsesClient(
        args.proxy_url,
        args.model,
        reasoning_effort=args.reasoning_effort,
        service_tier=args.service_tier,
        timeout=args.model_timeout,
        max_retries=args.model_max_retries,
    )
    model = GlobalModelSlotLimiter(
        inner,
        slot_directory=slot_directory,
        output_root=ROOT / "outputs",
        slot_cap=args.model_slot_cap,
        pool_id=args.model_slot_pool_id,
    )
    if args.model_slot_pool_id != POOL_ID:
        raise RuntimeError("V2.42.65 model slot pool identity drifted")
    search = AnthropicSearchClient(
        key,
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
    try:
        result = run_paired_task(
            task,
            model=model,
            search=search,
            limits=limits,
            progress=lambda value: _progress(progress_path, dict(value)),
        )
        validate_paired_result(result)
    except BaseException:
        _atomic_new(receipt_path, model.receipt())
        raise
    _atomic_new(receipt_path, model.receipt())
    _atomic_new(result_path, result)


if __name__ == "__main__":
    main()
