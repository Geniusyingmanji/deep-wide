#!/usr/bin/env python3
"""Run one V2.42.75 task through the audited V2.42.73 two-wave runtime."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
)
from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    TwoWavePolicy,
)
from deepwide_agent.v24273_two_wave_task_runtime import (  # noqa: E402
    run_v24273_task,
    validate_v24273_result,
)
from deepwide_agent.v24275_hard_deadline_fetch import (  # noqa: E402
    HardDeadlineNativeSearchClient,
    validate_transport_health,
)
from deepwide_agent.v24275_forward_contract import (  # noqa: E402
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    SEARCH,
    TWO_WAVE_POLICY,
)


def _ordinary_under(path: Path, root: Path) -> Path:
    target = path.resolve(strict=False)
    base = root.resolve()
    if not target.is_relative_to(base) or path.is_symlink() or target.is_symlink():
        raise ValueError("V2.42.75 child path escaped outputs or is a symlink")
    return target


def _read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.42.75 child expected a JSON object")
    return value


def _atomic_new(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
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


def _atomic_progress(path: Path, value: dict) -> None:
    if (
        value.get("role") != "v24257_score_first_safe_progress"
        or value.get("contains_question_query_url_page_prediction_or_answer")
        is not False
        or value.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        raise ValueError("V2.42.75 unsafe child progress")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def transport_health(search: HardDeadlineNativeSearchClient) -> dict[str, int]:
    return validate_transport_health({
        "hard_fetch_helper_calls": int(search.hard_fetch_helper_calls),
        "hard_fetch_deadline_failures": int(search.hard_fetch_deadline_failures),
        "fetch_helper_failures": int(search.fetch_helper_failures),
    })


def validate_frozen_configuration(args: Any, slot_directory: Path) -> None:
    """Reject any child-side budget/provider/controller drift before effects."""

    expected = {
        "proxy_url": MODEL["proxy_url"],
        "model": MODEL["name"],
        "reasoning_effort": MODEL["reasoning_effort"],
        "service_tier": MODEL["service_tier"],
        "model_timeout": MODEL["timeout_seconds"],
        "model_max_retries": MODEL["max_retries"],
        "search_batch_size": SEARCH["batch_size"],
        "search_workers": SEARCH["workers"],
        "search_context_size": SEARCH["context_size"],
        "search_output_tokens": SEARCH["max_output_tokens"],
        "search_timeout": SEARCH["timeout_seconds"],
        "search_max_retries": SEARCH["max_retries"],
        "fetch_workers": SEARCH["fetch_workers"],
        "fetch_timeout": SEARCH["fetch_timeout_seconds"],
        "model_slot_pool_id": MODEL_SLOT_POOL_ID,
        "model_slot_cap": MODEL_SLOT_CAP,
        **LIMITS,
        **TWO_WAVE_POLICY,
    }
    actual = {name: getattr(args, name) for name in expected}
    if (
        actual != expected
        or args.model_slot_pool_id != POOL_ID
        or slot_directory.is_symlink()
        or not slot_directory.is_dir()
        or slot_directory.resolve(strict=False)
        != (ROOT / MODEL_SLOT_DIRECTORY).resolve(strict=False)
    ):
        raise RuntimeError("V2.42.75 child execution surface drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--model-slot-directory", required=True)
    parser.add_argument("--model-slot-receipt", required=True)
    parser.add_argument("--transport-health", required=True)
    parser.add_argument("--model-slot-cap", type=int, required=True)
    parser.add_argument("--model-slot-pool-id", required=True)
    parser.add_argument("--proxy-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", required=True)
    parser.add_argument("--service-tier", required=True)
    parser.add_argument("--model-timeout", type=int, required=True)
    parser.add_argument("--model-max-retries", type=int, required=True)
    parser.add_argument("--search-batch-size", type=int, required=True)
    parser.add_argument("--search-workers", type=int, required=True)
    parser.add_argument("--search-context-size", required=True)
    parser.add_argument("--search-output-tokens", type=int, required=True)
    parser.add_argument("--search-timeout", type=int, required=True)
    parser.add_argument("--search-max-retries", type=int, required=True)
    parser.add_argument("--fetch-workers", type=int, required=True)
    parser.add_argument("--fetch-timeout", type=int, required=True)
    parser.add_argument("--wall-seconds", type=float, required=True)
    parser.add_argument("--model-calls", type=int, required=True)
    parser.add_argument("--search-queries", type=int, required=True)
    parser.add_argument("--fetch-targets", type=int, required=True)
    parser.add_argument("--search-results-per-query", type=int, required=True)
    parser.add_argument("--evidence-chars", type=int, required=True)
    parser.add_argument("--page-chars", type=int, required=True)
    parser.add_argument("--plan-output-tokens", type=int, required=True)
    parser.add_argument("--synthesis-output-tokens", type=int, required=True)
    parser.add_argument("--repair-output-tokens", type=int, required=True)
    parser.add_argument("--wave1-queries", type=int, required=True)
    parser.add_argument("--wave1-fetches", type=int, required=True)
    parser.add_argument("--wave2-queries", type=int, required=True)
    parser.add_argument("--wave2-fetches", type=int, required=True)
    parser.add_argument("--minimum-usable-pages", type=int, required=True)
    parser.add_argument("--minimum-novel-pages", type=int, required=True)
    parser.add_argument("--minimum-unique-hosts", type=int, required=True)
    parser.add_argument("--content-chars-per-column", type=int, required=True)
    parser.add_argument("--maximum-wave1-seconds", type=float, required=True)
    parser.add_argument("--latency-loss-per-second", type=float, required=True)
    parser.add_argument("--information-gain-weight", type=float, required=True)
    parser.add_argument("--minimum-net-value", type=float, required=True)
    parser.add_argument("--beta-prior-alpha", type=float, required=True)
    parser.add_argument("--beta-prior-beta", type=float, required=True)
    args = parser.parse_args()

    task_path = _ordinary_under(Path(args.task), ROOT / "outputs")
    result_path = _ordinary_under(Path(args.result), ROOT / "outputs")
    progress_path = _ordinary_under(Path(args.progress), ROOT / "outputs")
    receipt_path = _ordinary_under(
        Path(args.model_slot_receipt), ROOT / "outputs"
    )
    transport_path = _ordinary_under(Path(args.transport_health), ROOT / "outputs")
    slot_directory = Path(args.model_slot_directory)
    expected_task_root = (ROOT / "outputs/v24275_two_wave_dev64_v2_20260802/tasks").resolve()
    task_directory = task_path.parent
    if (
        not task_path.is_file()
        or not task_directory.is_relative_to(expected_task_root)
        or not task_directory.name.startswith("task_")
        or task_path.name != "visible_task.json"
        or result_path.parent != task_directory
        or result_path.name != "result.json"
        or progress_path.parent != task_directory
        or progress_path.name != "safe_progress.json"
        or receipt_path.parent != task_directory
        or receipt_path.name != "model_slot_receipt.json"
        or transport_path.parent != task_directory
        or transport_path.name != "transport_health.json"
        or result_path.exists()
        or result_path.is_symlink()
        or progress_path.exists()
        or progress_path.is_symlink()
        or receipt_path.exists()
        or receipt_path.is_symlink()
        or transport_path.exists()
        or transport_path.is_symlink()
    ):
        raise RuntimeError("V2.42.75 child execution surface drifted")
    validate_frozen_configuration(args, slot_directory)

    task = validate_visible_task(_read_object(task_path))
    limits = ScoreFirstLimits(
        wall_seconds=args.wall_seconds,
        model_calls=args.model_calls,
        search_queries=args.search_queries,
        fetch_targets=args.fetch_targets,
        search_results_per_query=args.search_results_per_query,
        evidence_chars=args.evidence_chars,
        page_chars=args.page_chars,
        plan_output_tokens=args.plan_output_tokens,
        synthesis_output_tokens=args.synthesis_output_tokens,
        repair_output_tokens=args.repair_output_tokens,
    )
    limits.validate()
    policy = TwoWavePolicy(
        wave1_queries=args.wave1_queries,
        wave1_fetches=args.wave1_fetches,
        wave2_queries=args.wave2_queries,
        wave2_fetches=args.wave2_fetches,
        minimum_usable_pages=args.minimum_usable_pages,
        minimum_novel_pages=args.minimum_novel_pages,
        minimum_unique_hosts=args.minimum_unique_hosts,
        content_chars_per_column=args.content_chars_per_column,
        maximum_wave1_seconds=args.maximum_wave1_seconds,
        latency_loss_per_second=args.latency_loss_per_second,
        information_gain_weight=args.information_gain_weight,
        minimum_net_value=args.minimum_net_value,
        beta_prior_alpha=args.beta_prior_alpha,
        beta_prior_beta=args.beta_prior_beta,
    )
    policy.validate()
    if limits.__dict__ != LIMITS or policy.__dict__ != TWO_WAVE_POLICY:
        raise RuntimeError("V2.42.75 retrieval policy drifted")

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
    search = HardDeadlineNativeSearchClient(
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
        hard_fetch_deadline_seconds=SEARCH["hard_fetch_deadline_seconds"],
    )
    try:
        result = run_v24273_task(
            task,
            model=model,
            search=search,
            limits=limits,
            policy=policy,
            progress=lambda value: _atomic_progress(progress_path, dict(value)),
        )
        validate_v24273_result(result)
    except BaseException:
        _atomic_new(receipt_path, model.receipt())
        _atomic_new(transport_path, transport_health(search))
        raise
    _atomic_new(receipt_path, model.receipt())
    health = transport_health(search)
    _atomic_new(transport_path, health)
    envelope = {
        "artifact_version": 1,
        "role": "v24275_two_wave_task_envelope",
        "result": result,
        "transport_health": health,
    }
    from deepwide_agent.v24275_forward_contract import payload_sha256

    envelope["envelope_payload_sha256"] = payload_sha256(envelope)
    _atomic_new(result_path, envelope)


if __name__ == "__main__":
    main()
