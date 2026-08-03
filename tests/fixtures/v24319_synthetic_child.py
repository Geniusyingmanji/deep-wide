#!/usr/bin/env python3
"""Network-free real child for the V2.43.19 integration matrix."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import run_child_with_terminal_receipt  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import DeadlineAwareNativeSearchClient  # noqa: E402
from deepwide_agent.v24319_runner_integration import build_envelope, run_v24319_task  # noqa: E402


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += float(seconds)


class Model:
    def __init__(self) -> None:
        self.values = [
            json.dumps({"columns": ["Name", "Date"], "queries": ["one", "two", "three", "four"]}),
            "| Name | Date |\n| --- | --- |\n| A | 2026 |",
        ]
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.deadline_failures = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return SimpleNamespace(text=self.values.pop(0))


class Search(DeadlineAwareNativeSearchClient):
    def __init__(self, clock: Clock, *, deadline: float, expire: bool) -> None:
        super().__init__(
            "http://unused.invalid/responses",
            "synthetic",
            timeout=180,
            max_retries=2,
            fetch_pages=False,
            max_workers=1,
            fetch_workers=1,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        self.clock = clock
        self.expire = expire
        self.search_invocations = 0

    def search_many(self, queries, **_kwargs):
        values = list(queries)
        self.search_invocations += 1
        self._increment("calls")
        self._increment("tool_calls")
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "url": f"https://synthetic-{self.search_invocations}-{index}.invalid/page",
                        "title": "synthetic",
                        "content": "untrusted snippet",
                    }
                    for index in range(3)
                ],
            }
            for query in values
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self._increment("fetch_calls", len(values))
        result = [
            {
                "query": item["query"],
                "results": [
                    {
                        "url": item["url"],
                        "title": "synthetic",
                        "raw_content": "public synthetic page " + "x" * 1000,
                    }
                ],
            }
            for item in values
        ]
        if self.expire:
            self.clock.value = 221.0
        return result


def write_new(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--model-receipt", required=True)
    parser.add_argument("--transport", required=True)
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--slots", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    task = validate_visible_task(json.loads(Path(args.task).read_text(encoding="utf-8")))

    def action() -> None:
        if args.mode == "timeout":
            time.sleep(5)
            return
        if args.mode == "nonzero":
            raise RuntimeError("content-free synthetic nonzero")
        clock = Clock()
        deadline = 100.005 if args.mode == "slot_reject" else 300.0
        model = build_deadline_model(
            url="http://unused.invalid/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=Path(args.slots),
            output_root=Path(args.output_root),
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=Model(),
        )
        search = Search(clock, deadline=deadline, expire=args.mode == "cache_defer")
        outcome = run_v24319_task(
            task,
            arm=args.arm,
            model=model,
            search=search,
            limits=ScoreFirstLimits(
                wall_seconds=120,
                model_calls=3,
                search_queries=4,
                fetch_targets=10,
                search_results_per_query=3,
                evidence_chars=60_000,
                page_chars=5_000,
            ),
            two_wave_policy=TwoWavePolicy(),
            reserve_policy=StagedReservePolicy() if args.arm == "candidate" else None,
            monotonic=clock,
        )
        envelope = build_envelope(outcome, arm=args.arm)
        if args.mode != "missing_model":
            write_new(Path(args.model_receipt), outcome.model_slot_receipt)
        if args.mode != "missing_transport":
            write_new(Path(args.transport), outcome.transport_health)
        if args.mode == "invalid_result":
            write_new(Path(args.result), {"invalid": True})
        elif args.mode != "missing_result":
            write_new(Path(args.result), envelope)

    run_child_with_terminal_receipt(
        output_root=Path(args.output_root),
        directory=Path(args.terminal).parent,
        action=action,
        result_name=Path(args.result).name,
        model_receipt_name=Path(args.model_receipt).name,
        transport_receipt_name=Path(args.transport).name,
        terminal_name=Path(args.terminal).name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
