from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24468_total_wall_transport as transport  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24628_backfill_search_integration import (  # noqa: E402
    build_bounded_same_response_title_backfill_search,
)
from deepwide_agent.v24629_backfill_runner_integration import (  # noqa: E402
    build_envelope,
    run_v24629_task,
    validate_envelope,
)


class InnerModel:
    def __init__(self) -> None:
        self.values = [
            json.dumps(
                {"columns": ["Name", "Date"], "queries": ["one", "two", "three", "four"]}
            ),
            "| Name | Date |\n| --- | --- |\n| Alpha | 2026 |",
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
        return types.SimpleNamespace(text=self.values.pop(0))


def hosted_response() -> dict:
    sources = [
        {"type": "web_source", "url": f"https://s{i}.example.invalid/page", "title": ""}
        for i in range(1, 7)
    ]
    annotations = [
        {
            "type": "url_citation",
            "url": source["url"],
            "title": f"Source {index}",
            "start_index": index - 1,
            "end_index": index,
        }
        for index, source in enumerate(sources, start=1)
    ]
    return {
        "kind": "response",
        "status_code": 200,
        "retry_after": "",
        "payload_is_object": True,
        "payload": {
            "id": "synthetic",
            "output": [
                {
                    "type": "web_search_call",
                    "id": "search",
                    "status": "completed",
                    "action": {"type": "search", "sources": sources},
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "unmapped",
                            "annotations": annotations,
                        }
                    ],
                },
            ],
            "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
        },
    }


class V24629BackfillRunnerIntegrationTests(unittest.TestCase):
    def test_complete_runtime_binds_backfill_receipt(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            slots = output / "slots"
            slots.mkdir()
            for index in range(1, 3):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            deadline = time.monotonic() + 120
            model = build_deadline_model(
                url="http://127.0.0.1:9/responses",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=30,
                max_retries=1,
                slot_directory=slots,
                output_root=output,
                slot_cap=2,
                pool_id=POOL_ID,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=5,
                minimum_attempt_seconds=0.01,
                inner=InnerModel(),
            )
            search = build_bounded_same_response_title_backfill_search(
                url="http://127.0.0.1:9/responses",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=30,
                max_retries=1,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=5,
                minimum_attempt_seconds=0.01,
                fetch_pages=False,
            )

            def fake_fetch(instance, requests_):
                values = list(requests_)
                instance._increment("fetch_calls", len(values))
                instance._increment("hard_fetch_helper_calls", len(values))
                return [
                    {
                        "query": item["query"],
                        "results": [
                            {
                                "url": item["url"],
                                "requested_url": item["url"],
                                "title": item["title"],
                                "raw_content": "Public source page " + "x" * 1500,
                            }
                        ],
                    }
                    for item in values
                ]

            search.fetch_urls = types.MethodType(fake_fetch, search)
            with patch.object(
                transport, "run_total_wall_post", return_value=hosted_response()
            ):
                outcome = run_v24629_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": "Return one table. The column names are: Name, Date.",
                    },
                    arm="baseline",
                    model=model,
                    search=search,
                    limits=ScoreFirstLimits(
                        wall_seconds=90,
                        model_calls=3,
                        search_queries=4,
                        fetch_targets=10,
                        search_results_per_query=3,
                        evidence_chars=60_000,
                        page_chars=5_000,
                    ),
                    two_wave_policy=TwoWavePolicy(),
                    monotonic=time.monotonic,
                )
            envelope = build_envelope(outcome, arm="baseline")
            validate_envelope(envelope)
            backfill = envelope["citation_title_backfill_receipt"]
            self.assertGreater(backfill["backfilled_action_source_count"], 0)
            self.assertEqual(
                backfill["multi_query_payload_count"],
                envelope["search_single_shot_receipt"]["multi_query_chunks"],
            )

    def test_privileged_input_fails_before_effect(self) -> None:
        with self.assertRaises(ValueError):
            # Validation happens before either client is dereferenced.
            run_v24629_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": "Return one table.",
                    "question_type": "forbidden",
                },
                arm="baseline",
                model=None,
                search=None,
                limits=ScoreFirstLimits(),
                two_wave_policy=TwoWavePolicy(),
                monotonic=time.monotonic,
            )

    def test_envelope_tamper_fails_closed(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "wrong",
        }
        with self.assertRaises(ValueError):
            validate_envelope(copy.deepcopy(value))


if __name__ == "__main__":
    unittest.main()
