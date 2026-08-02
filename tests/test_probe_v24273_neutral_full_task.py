from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import object_sha256  # noqa: E402
from deepwide_agent.v24273_two_wave_task_runtime import run_v24273_task  # noqa: E402
from scripts import probe_v24273_neutral_full_task as target  # noqa: E402
from test_v24272_two_wave_retrieval import Clock, FakeSearch  # noqa: E402
from test_v24273_two_wave_task_runtime import FakeModel, PLAN, TABLE  # noqa: E402


def projected():
    model = FakeModel([PLAN, TABLE])
    search = FakeSearch()
    result = run_v24273_task(
        target.NEUTRAL_TASK,
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
        monotonic=Clock(),
    )
    return target._content_free_projection(
        result,
        model_counters=target._counter_snapshot(model, target.MODEL_COUNTERS),
        search_counters=target._counter_snapshot(search, target.SEARCH_COUNTERS),
        wall_seconds=1.0,
        now=1,
    )


class ProbeV24273NeutralFullTaskTests(unittest.TestCase):
    def test_synthetic_full_projection_validates_and_authorizes_nothing(self):
        value = projected()
        target.validate_projection(value)
        self.assertFalse(any(value["authorization"].values()))
        self.assertFalse(value["source_policy"]["official_evaluator_called"])

    def test_projection_excludes_input_queries_urls_pages_prediction_and_hash(self):
        encoded = json.dumps(projected(), ensure_ascii=False)
        for forbidden in (
            target.NEUTRAL_TASK["opaque_id"],
            target.NEUTRAL_TASK["question"],
            "visible one",
            "source-0",
            "usable evidence",
            "Example | 1",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_resealed_counter_source_or_authority_tamper_fails(self):
        value = projected()
        for mutation in ("counter", "source", "authority"):
            altered = copy.deepcopy(value)
            if mutation == "counter":
                altered["search_counters"]["fetch_calls"] += 1
            elif mutation == "source":
                altered["source_policy"][
                    "benchmark_manifest_mapping_gold_prediction_or_evaluator_read"
                ] = True
            else:
                altered["authorization"]["dev_benchmark_launch"] = True
            unsigned = dict(altered)
            unsigned.pop("result_payload_sha256")
            altered["result_payload_sha256"] = object_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "probe|projection|accounting"):
                target.validate_projection(altered)


if __name__ == "__main__":
    unittest.main()
