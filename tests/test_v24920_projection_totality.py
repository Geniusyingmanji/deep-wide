from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24911_long_page_evidence_packer import payload_sha256  # noqa: E402
from deepwide_agent.v24920_projection_totality import (  # noqa: E402
    TOTAL_OVERFLOW_MESSAGE,
    build_projection_totality,
    validate_receipt,
)
from deepwide_agent.v24920_projection_totality_runtime_binding import (  # noqa: E402
    project_evidence,
)
from deepwide_agent.v24257_score_first_runtime import _lead_requests  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24272_two_wave_retrieval import run_two_wave_retrieval  # noqa: E402
from deepwide_agent.v24273_two_wave_task_runtime import (  # noqa: E402
    TwoWaveCachingSearchClient,
)


QUESTION = "Return one table. Columns: Entity, Value"


def content() -> str:
    return (("Entity Value " + "x" * 40) + "\n\n") * 200


def pages(count: int, *, long_url: bool = False) -> list[dict[str, str]]:
    output = []
    for index in range(count):
        prefix = f"https://source-{index}.example/"
        url = prefix + ("u" * (8_192 - len(prefix)) if long_url else "data")
        output.append({"title": "T" * 500, "url": url, "content": content()})
    return output


class ProductionShapedSearch:
    """Two-wave fake with long final URLs, an empty page, and a duplicate lead."""

    batch_size = 8
    max_workers = 1
    fetch_workers = 8
    fetch_timeout = 20
    fetch_pages = False

    def __init__(self) -> None:
        self.search_invocations = 0
        self.fetch_invocations = 0
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def search_many(self, queries, **kwargs):
        del kwargs
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        results = []
        for index in range(8):
            if self.search_invocations == 2 and index == 0:
                url = "https://lead-0.example/data"
            else:
                url = f"https://lead-{self.search_invocations}-{index}.example/data"
            results.append({"url": url, "title": "lead", "content": "snippet"})
        return [
            {
                "query": "task-local union",
                "answer": "discarded",
                "results": results,
                "error": None,
            }
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_invocations += 1
        self.fetch_calls += len(values)
        batches = []
        for index, item in enumerate(values):
            if self.fetch_invocations == 1 and index == 0:
                self.fetch_failures += 1
                batches.append(
                    {"query": item["query"], "results": [], "error": "empty_extraction"}
                )
                continue
            prefix = f"https://final-{self.fetch_invocations}-{index}.example/"
            final_url = prefix + "u" * (8_192 - len(prefix))
            batches.append(
                {
                    "query": item["query"],
                    "results": [
                        {
                            "requested_url": item["url"],
                            "fetch_url": item["url"],
                            "url": final_url,
                            "title": "T" * 500,
                            "raw_content": content(),
                        }
                    ],
                    "error": None,
                }
            )
        return batches


class V24920ProjectionTotalityTests(unittest.TestCase):
    def test_rendered_total_overflow_falls_back_to_exact_prefix(self) -> None:
        result = build_projection_totality(QUESTION, pages(10, long_url=True))
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["projection_totality_fallback_applied"])
        self.assertEqual(
            receipt["projection_totality_fallback_reason"], "rendered_total_cap"
        )
        self.assertTrue(receipt["fallback_projection_is_exact_stable_5k_prefix"])
        self.assertEqual(receipt["output_active_content_characters"], 50_000)
        self.assertGreater(receipt["projected_rendered_characters"], 60_000)

    def test_per_page_overflow_remains_total(self) -> None:
        result = build_projection_totality(QUESTION, pages(1))
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["projection_totality_fallback_applied"])
        self.assertEqual(receipt["projection_totality_fallback_reason"], "per_page_cap")
        self.assertIn(content()[:5_000], result["projection"])

    def test_nonoverflow_mechanism_remains_active(self) -> None:
        value = {
            "title": "Official",
            "url": "https://official.example/data",
            "content": "boilerplate " * 600 + "\nOmega Republic [OMG]: 999",
        }
        result = build_projection_totality(
            "Return Omega Republic [OMG] Value", [value]
        )
        receipt = result["content_free_receipt"]
        self.assertFalse(receipt["projection_totality_fallback_applied"])
        self.assertTrue(receipt["long_page_mechanism_engaged"])
        self.assertIn("Omega Republic [OMG]: 999", result["projection"])

    def test_runtime_binding_handles_ten_long_redirect_urls(self) -> None:
        batches = [
            {
                "results": [
                    {
                        "title": page["title"],
                        "url": page["url"],
                        "raw_content": page["content"],
                    }
                ]
            }
            for page in pages(10, long_url=True)
        ]
        evidence, receipt = project_evidence(
            QUESTION,
            [],
            batches,
            SimpleNamespace(page_chars=12_000, evidence_chars=60_000),
        )
        self.assertTrue(evidence)
        self.assertEqual(receipt["projection_totality_fallback_reason"], "rendered_total_cap")

    def test_full_two_wave_cache_serve_projection_chain_is_total(self) -> None:
        search = ProductionShapedSearch()
        policy = TwoWavePolicy(
            wave1_queries=2,
            wave1_fetches=6,
            wave2_queries=2,
            wave2_fetches=4,
            minimum_usable_pages=6,
            minimum_novel_pages=6,
            minimum_unique_hosts=6,
            content_chars_per_column=1_000_000_000,
            maximum_wave1_seconds=30.0,
            latency_loss_per_second=0.0,
            information_gain_weight=0.0,
            minimum_net_value=-1.0,
        )
        proxy = TwoWaveCachingSearchClient(
            search,
            required_column_count=2,
            policy=policy,
            monotonic=lambda: 1.0,
        )
        discovery = proxy.search_many(
            ["visible one", "visible two", "visible three", "visible four"],
            max_results=3,
            search_depth="advanced",
            include_raw_content=False,
        )
        leads = _lead_requests(discovery, 10)
        cached = proxy.fetch_urls(leads)
        evidence, receipt = project_evidence(
            QUESTION,
            discovery,
            cached,
            SimpleNamespace(page_chars=12_000, evidence_chars=60_000),
        )
        self.assertTrue(evidence)
        self.assertEqual(search.search_invocations, 2)
        self.assertEqual(search.fetch_invocations, 2)
        self.assertEqual(proxy.cache_serve_invocations, 1)
        self.assertEqual(proxy.network_fetches_after_cache_serve, search.fetch_calls)
        self.assertEqual(proxy.receipt()["status"], "completed")
        self.assertIn(
            receipt["projection_totality_fallback_reason"],
            {"per_page_cap", "rendered_total_cap"},
        )

    def test_unrelated_runtime_error_is_not_swallowed(self) -> None:
        with mock.patch(
            "deepwide_agent.v24920_projection_totality.previous.build_prefix_total_packing",
            side_effect=RuntimeError("unrelated failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unrelated failure"):
                build_projection_totality(QUESTION, pages(1))

    def test_type_and_value_errors_are_not_swallowed(self) -> None:
        for error in (TypeError("bad type"), ValueError("bad value")):
            with self.subTest(error=type(error).__name__), mock.patch(
                "deepwide_agent.v24920_projection_totality.previous.build_prefix_total_packing",
                side_effect=error,
            ):
                with self.assertRaises(type(error)):
                    build_projection_totality(QUESTION, pages(1))

    def test_receipt_resealed_tamper_fails(self) -> None:
        receipt = build_projection_totality(
            QUESTION, pages(10, long_url=True)
        )["content_free_receipt"]
        altered = copy.deepcopy(receipt)
        altered["long_page_mechanism_engaged"] = True
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_receipt(altered)

    def test_exact_error_string_is_frozen(self) -> None:
        self.assertEqual(
            TOTAL_OVERFLOW_MESSAGE,
            "V2.49.11 rendered projection exceeded total cap",
        )


if __name__ == "__main__":
    unittest.main()
