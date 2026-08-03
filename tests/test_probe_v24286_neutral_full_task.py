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
from deepwide_agent.v24286_visible_schema_runtime import run_v24286_task  # noqa: E402
from scripts import probe_v24286_neutral_full_task as target  # noqa: E402
from test_v24272_two_wave_retrieval import Clock, FakeSearch  # noqa: E402
from test_v24273_two_wave_task_runtime import FakeModel  # noqa: E402


PLAN = json.dumps(
    {
        "language": "English",
        "columns": ["wrong"],
        "queries": ["visible one", "visible two", "visible three", "visible four"],
    }
)
TABLE = """```markdown
| Feature | Python Version | Status |
| --- | --- | --- |
| Example | 3.13 | Stable |
```"""


def projected():
    model = FakeModel([PLAN, TABLE])
    search = FakeSearch()
    result = run_v24286_task(
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
    return target._projection(
        result,
        model_counters=target._counter_snapshot(model, target.MODEL_COUNTERS),
        search_counters=target._counter_snapshot(search, target.SEARCH_COUNTERS),
        wall_seconds=1.0,
        now=1,
    )


class ProbeV24286NeutralFullTaskTests(unittest.TestCase):
    def test_projection_validates_and_authorizes_nothing(self):
        value = projected()
        target.validate_projection(value)
        self.assertFalse(any(value["authorization"].values()))
        self.assertEqual(value["visible_schema"]["column_count"], 3)
        self.assertEqual(value["attributed_timing"]["status"], "complete")

    def test_projection_excludes_content_and_identifiers(self):
        encoded = json.dumps(projected(), ensure_ascii=False)
        for forbidden in (
            target.NEUTRAL_TASK["opaque_id"],
            target.NEUTRAL_TASK["question"],
            "Feature",
            "visible one",
            "source-0",
            "usable evidence",
            "Example",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_resealed_counter_content_or_authority_tamper_fails(self):
        for mutation in ("counter", "content", "authority"):
            altered = copy.deepcopy(projected())
            if mutation == "counter":
                altered["search_counters"]["fetch_calls"] = 11
            elif mutation == "content":
                altered["visible_schema"]["field"] = "Feature"
            else:
                altered["authorization"]["exact220_launch"] = True
            unsigned = dict(altered)
            unsigned.pop("result_payload_sha256")
            altered["result_payload_sha256"] = object_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "projection|accounting|schema"):
                target.validate_projection(altered)


if __name__ == "__main__":
    unittest.main()
