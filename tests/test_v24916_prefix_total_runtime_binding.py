from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24913_cap_bound_long_page_fetch import (  # noqa: E402
    CapBoundLongPageSearchClient,
)
from deepwide_agent.v24916_prefix_total_runtime_binding import (  # noqa: E402
    bind_child_algorithm,
    project_evidence,
    validate_binding_contract,
)
from scripts import run_v24916_prefix_total_long_page_task as child  # noqa: E402


def contract() -> types.ModuleType:
    value = types.ModuleType("frozen_contract")
    value.OUTPUT_ROOT = Path("outputs/frozen")
    value.TASK_ROOT = value.OUTPUT_ROOT / "tasks"
    value.MODEL_SLOT_DIRECTORY = value.OUTPUT_ROOT / "slots"
    value.LIMITS = {
        "wall_seconds": 240,
        "model_calls": 3,
        "search_queries": 4,
        "fetch_targets": 10,
        "search_results_per_query": 3,
        "evidence_chars": 60_000,
        "page_chars": 12_000,
        "plan_output_tokens": 4_000,
        "synthesis_output_tokens": 30_000,
        "repair_output_tokens": 12_000,
    }
    value.MODEL = {"name": "gpt-5.6-sol"}
    value.SEARCH = {"provider": "keyless"}
    value.TWO_WAVE_POLICY = {"information_gain_weight": 0.0}
    value.MODEL_SLOT_CAP = 8
    value.EXECUTOR_CONCURRENCY = 20
    return value


class Limits:
    page_chars = 12_000
    evidence_chars = 60_000


class V24916PrefixTotalRuntimeBindingTests(unittest.TestCase):
    def test_binding_preserves_12k_fetch_class(self) -> None:
        algorithm = types.ModuleType("algorithm")
        bind_child_algorithm(algorithm, contract())
        self.assertIs(
            algorithm.ThinSameResponseCitationTitleBackfillSearchClient,
            CapBoundLongPageSearchClient,
        )

    def test_binding_rejects_legacy_cap(self) -> None:
        value = contract()
        value.LIMITS["page_chars"] = 5_000
        with self.assertRaises(ValueError):
            validate_binding_contract(value)

    def test_projection_totalizes_overflow_without_extra_effect(self) -> None:
        content = (("Entity Value " + "x" * 40) + "\n\n") * 200
        evidence, receipt = project_evidence(
            "Return one table. Columns: Entity, Value",
            [],
            [
                {
                    "results": [
                        {
                            "title": "Official",
                            "url": "https://official.example/data",
                            "raw_content": content,
                        }
                    ]
                }
            ],
            Limits(),
        )
        self.assertTrue(receipt["structural_cap_totality_fallback_applied"])
        self.assertIn(content[:5_000], evidence)
        self.assertFalse(receipt["additional_search_fetch_model_call_or_wall_cap"])

    def test_child_requires_frozen_contract(self) -> None:
        previous = child._CONTRACT
        child._CONTRACT = None
        try:
            with self.assertRaises(RuntimeError):
                child.main()
        finally:
            child._CONTRACT = previous


if __name__ == "__main__":
    unittest.main()
