from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    build_v24259_fallback_result,
)
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402
from scripts.run_v24259_score_first_smoke import aggregate_results  # noqa: E402


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "表格中的列名依次为：名称、年份。",
}


def protocol() -> dict:
    return {
        "protocol_id": "v24259_deterministic_normalizer_smoke16_v1",
        "task_contract": {"selected_count": 16},
        "gate_contract": {
            "minimum_model_generated_tables": 15,
            "maximum_fallback_tables": 1,
            "maximum_hard_deadline_fallbacks": 1,
            "maximum_p95_wall_seconds": 600,
            "maximum_mean_system_tokens": 750_000,
            "maximum_mean_fetch_calls": 200,
        },
    }


def result(kind: str) -> dict:
    value = build_v24259_fallback_result(
        TASK,
        completion_kind=(
            kind if "fallback" in kind else "worker_failure_fallback"
        ),
        elapsed_seconds=10,
    )
    value["completion_kind"] = kind
    if kind in {"normalized_primary", "normalized_repaired"}:
        value["normalization"]["events"] = [
            {
                "stage": "synthesis",
                "status": "normalized",
                "mode": "positional_header",
                "candidate_group_count": 1,
                "input_column_count": 2,
                "output_column_count": 2,
                "input_row_count": 1,
                "output_row_count": 1,
                "dropped_row_count": 0,
                "filled_empty_cell_count": 0,
            }
        ]
    return value


class RunV24259ScoreFirstSmokeTests(unittest.TestCase):
    def test_normalized_primary_counts_as_model_generated(self) -> None:
        rows = [result("normalized_primary") for _ in range(15)] + [
            result("worker_failure_fallback")
        ]
        value = aggregate_results(protocol(), rows)
        self.assertEqual(value["engineering_gate"], "go")
        self.assertEqual(value["model_generated_tables"], 15)
        self.assertEqual(value["normalization_modes"], {"positional_header": 15})
        unsigned = dict(value)
        self.assertEqual(
            unsigned.pop("result_payload_sha256"), payload_sha256(unsigned)
        )

    def test_two_fallbacks_still_fail_closed(self) -> None:
        rows = [result("normalized_primary") for _ in range(14)] + [
            result("best_effort_fallback"),
            result("worker_failure_fallback"),
        ]
        value = aggregate_results(protocol(), rows)
        self.assertEqual(value["engineering_gate"], "no_go")
        self.assertIn("fallback_table_count_above_gate", value["findings"])


if __name__ == "__main__":
    unittest.main()
