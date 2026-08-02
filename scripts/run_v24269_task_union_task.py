#!/usr/bin/env python3
"""Run one V2.42.69 task-local source-union successor task."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
)
from deepwide_agent.v24269_task_union_discovery import (  # noqa: E402
    run_v24269_task,
    validate_v24269_result,
)
from scripts.run_v24257_score_first_task import (  # noqa: E402
    _atomic_new,
    _atomic_progress,
    _ordinary_under,
    _read_object,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--model-slot-directory", required=True)
    parser.add_argument("--model-slot-receipt", required=True)
    parser.add_argument("--model-slot-cap", type=int, default=2)
    parser.add_argument("--model-slot-pool-id", default=POOL_ID)
    parser.add_argument("--proxy-url", default="http://127.0.0.1:9878/responses")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--service-tier", default="priority")
    parser.add_argument("--model-timeout", type=int, default=180)
    parser.add_argument("--model-max-retries", type=int, default=2)
    parser.add_argument("--search-batch-size", type=int, default=8)
    parser.add_argument("--search-workers", type=int, default=1)
    parser.add_argument("--search-context-size", default="medium")
    parser.add_argument("--search-output-tokens", type=int, default=7000)
    parser.add_argument("--search-timeout", type=int, default=180)
    parser.add_argument("--search-max-retries", type=int, default=2)
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
    receipt_path = _ordinary_under(Path(args.model_slot_receipt), ROOT / "outputs")
    slot_directory = Path(args.model_slot_directory)
    if (
        not task_path.is_file()
        or result_path.exists()
        or result_path.is_symlink()
        or receipt_path.exists()
        or receipt_path.is_symlink()
    ):
        raise RuntimeError("V2.42.69 child execution surface drifted")
    if (
        args.proxy_url != "http://127.0.0.1:9878/responses"
        or args.model != "gpt-5.6-sol"
        or args.search_batch_size != 8
        or args.search_workers != 1
        or args.search_context_size not in {"low", "medium", "high"}
        or args.model_slot_pool_id != POOL_ID
    ):
        raise RuntimeError("V2.42.69 frozen provider shape drifted")

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
    if (
        limits.search_queries != 8
        or limits.fetch_targets != 16
        or limits.search_results_per_query != 3
    ):
        raise RuntimeError("V2.42.69 retrieval cap drifted")

    inner_model = ResponsesClient(
        args.proxy_url,
        args.model,
        reasoning_effort=args.reasoning_effort,
        service_tier=args.service_tier,
        timeout=args.model_timeout,
        max_retries=args.model_max_retries,
    )
    model = GlobalModelSlotLimiter(
        inner_model,
        slot_directory=slot_directory,
        output_root=ROOT / "outputs",
        slot_cap=args.model_slot_cap,
        pool_id=args.model_slot_pool_id,
    )
    search = AzureNativeSearchClient(
        args.proxy_url,
        args.model,
        reasoning_effort=args.reasoning_effort,
        service_tier=args.service_tier,
        timeout=args.search_timeout,
        max_retries=args.search_max_retries,
        max_workers=args.search_workers,
        batch_size=args.search_batch_size,
        search_context_size=args.search_context_size,
        max_output_tokens=args.search_output_tokens,
        fetch_pages=False,
        fetch_workers=args.fetch_workers,
        fetch_timeout=args.fetch_timeout,
        max_page_chars=args.page_chars,
    )
    try:
        result = run_v24269_task(
            task,
            model=model,
            search=search,
            limits=limits,
            progress=lambda value: _atomic_progress(progress_path, dict(value)),
        )
        validate_v24269_result(result)
    except BaseException:
        _atomic_new(receipt_path, model.receipt())
        raise
    _atomic_new(receipt_path, model.receipt())
    _atomic_new(result_path, result)


if __name__ == "__main__":
    main()
