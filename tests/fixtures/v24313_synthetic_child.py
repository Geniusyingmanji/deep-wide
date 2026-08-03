#!/usr/bin/env python3
"""Network-free real child for the V2.43.13 runner integration gate."""

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

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
)
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    validate_v24310_result,
)
from deepwide_agent.v24313_runner_integration import (  # noqa: E402
    build_deadline_model,
    run_v24313_task,
    validate_deadline_model_receipt,
)


def _new(path: Path, value: dict) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


class Model:
    def __init__(self) -> None:
        self.values = [
            json.dumps(
                {
                    "columns": ["Name", "Date"],
                    "queries": ["one", "two", "three", "four"],
                }
            ),
            "```markdown\n| Name | Date |\n| --- | --- |\n| A | 2026 |\n```",
            "```markdown\n| Name | Date |\n| --- | --- |\n| A | 2026 |\n```",
        ]
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.deadline_failures = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        return SimpleNamespace(text=self.values.pop(0))


class Search:
    batch_size = 8
    max_workers = 1
    fetch_workers = 8
    fetch_timeout = 20
    fetch_pages = False

    def __init__(self) -> None:
        self.calls = self.failures = self.tool_calls = 0
        self.fetch_calls = self.fetch_failures = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.search_invocations = 0

    def search_many(self, queries, **_kwargs):
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "url": f"https://synthetic-{self.search_invocations}-{index}.example/page",
                        "title": "synthetic",
                        "content": "synthetic",
                    }
                    for index in range(3)
                ],
            }
            for query in queries
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        return [
            {
                "query": item["query"],
                "results": [
                    {
                        "url": item["url"],
                        "title": "synthetic",
                        "raw_content": "synthetic evidence " + "x" * 2000,
                    }
                ],
            }
            for item in values
        ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--model-receipt", required=True)
    parser.add_argument("--transport", required=True)
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--slots", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    directory = Path(args.result).parent.resolve()
    task = validate_visible_task(
        json.loads(Path(args.task).read_text(encoding="utf-8"))
    )

    def action() -> None:
        limits = ScoreFirstLimits(
            wall_seconds=120,
            model_calls=3,
            search_queries=4,
            fetch_targets=10,
            search_results_per_query=3,
            evidence_chars=60_000,
            page_chars=5_000,
        )
        model = build_deadline_model(
            url="http://invalid.local",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=Path(args.slots),
            output_root=Path(args.output_root),
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=time.monotonic() + 1.5,
            cleanup_reserve_seconds=0.2,
            minimum_attempt_seconds=0.01,
            inner=Model(),
        )
        result = run_v24313_task(
            task,
            arm=args.arm,
            model=model,
            search=Search(),
            limits=limits,
            two_wave_policy=TwoWavePolicy(),
            reserve_policy=StagedReservePolicy()
            if args.arm == "candidate"
            else None,
        )
        validate_v24310_result(result, args.arm)
        receipt = model.receipt()
        validate_deadline_model_receipt(
            receipt,
            expected_cap=2,
            expected_acquisitions=result["cost"]["model"]["requests"],
        )
        transport = {
            "hard_fetch_helper_calls": 0,
            "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 0,
        }
        envelope = {
            "artifact_version": 1,
            "role": "v24313_synthetic_task_envelope",
            "arm": args.arm,
            "completion_kind": result["completion_kind"],
            "model_effects": result[RECEIPT_FIELD]["total_effects_admitted"],
            "fourth_model_effect": result[RECEIPT_FIELD]["fourth_model_effect"],
            "slot_acquisitions": receipt["acquisitions"],
            "slot_timeouts": receipt["slot_timeouts"],
            "provider_deadline_failures": receipt["provider_deadline_failures"],
            "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        _new(Path(args.model_receipt), receipt)
        _new(Path(args.transport), transport)
        _new(Path(args.result), envelope)

    run_child_with_terminal_receipt(
        output_root=Path(args.output_root),
        directory=directory,
        action=action,
        result_name=Path(args.result).name,
        model_receipt_name=Path(args.model_receipt).name,
        transport_receipt_name=Path(args.transport).name,
        terminal_name=Path(args.terminal).name,
    )


if __name__ == "__main__":
    main()
