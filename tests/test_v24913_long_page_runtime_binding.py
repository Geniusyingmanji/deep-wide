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
from deepwide_agent.v24913_long_page_runtime_binding import (  # noqa: E402
    bind_child_algorithm,
    project_evidence,
    validate_binding_contract,
)
from scripts import run_v24913_cap_bound_long_page_task as child  # noqa: E402


QUESTION = (
    "Return one table with columns: Country | Target Metric.\n"
    "<COUNTRIES>Omega Republic [OMG]</COUNTRIES>"
)


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


class V24913LongPageRuntimeBindingTests(unittest.TestCase):
    def test_binding_replaces_fetch_class_and_preserves_caps(self) -> None:
        algorithm = types.ModuleType("algorithm")
        bind_child_algorithm(algorithm, contract())
        self.assertIs(
            algorithm.ThinSameResponseCitationTitleBackfillSearchClient,
            CapBoundLongPageSearchClient,
        )
        self.assertEqual(algorithm.LIMITS["page_chars"], 12_000)
        self.assertEqual(algorithm.LIMITS["evidence_chars"], 60_000)

    def test_binding_rejects_legacy_page_cap(self) -> None:
        value = contract()
        value.LIMITS["page_chars"] = 5_000
        with self.assertRaises(ValueError):
            validate_binding_contract(value)

    def test_projection_recovers_late_evidence_and_emits_receipt(self) -> None:
        pages = [
            {
                "results": [
                    {
                        "title": "Official",
                        "url": "https://official.example/data",
                        "raw_content": "boilerplate " * 600
                        + "\nOmega Republic [OMG]: 999",
                    }
                ]
            }
        ]
        evidence, receipt = project_evidence(QUESTION, [], pages, Limits())
        self.assertIn("Omega Republic [OMG]: 999", evidence)
        self.assertTrue(receipt["long_page_mechanism_engaged"])
        self.assertFalse(
            receipt[
                "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential"
            ]
        )

    def test_search_narrative_is_never_forwarded(self) -> None:
        search = [{"answer": "provider narrative", "results": []}]
        evidence, _receipt = project_evidence(
            QUESTION,
            search,
            [{"results": [{"url": "https://official.example", "raw_content": "record"}]}],
            Limits(),
        )
        self.assertNotIn("provider narrative", evidence)

    def test_child_requires_explicit_frozen_contract(self) -> None:
        previous = child._CONTRACT
        child._CONTRACT = None
        try:
            with self.assertRaises(RuntimeError):
                child.main()
        finally:
            child._CONTRACT = previous


if __name__ == "__main__":
    unittest.main()
