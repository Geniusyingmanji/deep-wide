from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24959_source_fair_discovery as target  # noqa: E402


def source(host: str, suffix: str) -> dict[str, str]:
    return {
        "type": "url",
        "title": "",
        "url": f"https://{host}/{suffix}",
        "fetch_url": f"https://{host}/{suffix}",
    }


def batches() -> list[dict]:
    return [
        {
            "query": "discarded",
            "answer": "discarded",
            "results": [source("news.alpha.example", "local")],
            "error": None,
            "hosted_search_trace": {
                "actions": [
                    {
                        "sources": [
                            source("docs.alpha.example", f"a{i}")
                            for i in range(1, 6)
                        ]
                    },
                    {"sources": [source("www.beta.example", "b1")]},
                    {"sources": [source("gamma.example", "c1")]},
                    {"sources": [source("delta.example", "d1")]},
                ]
            },
        }
    ]


class V24959SourceFairDiscoveryTests(unittest.TestCase):
    def test_same_url_set_and_every_prefix_has_non_decreasing_source_coverage(self) -> None:
        ordered, observation, private = target.order_source_fair_leads(batches())
        stable = list(observation["stable_urls"])
        candidate = [item["url"] for item in ordered]
        self.assertEqual(set(stable), set(candidate))
        source_by_url = private["source_by_url"]
        for cap in range(1, len(stable) + 1):
            stable_sources = {
                source_by_url[url] for url in stable[:cap] if source_by_url[url]
            }
            candidate_sources = {
                source_by_url[url] for url in candidate[:cap] if source_by_url[url]
            }
            self.assertGreaterEqual(len(candidate_sources), len(stable_sources))
        self.assertEqual(observation["registrable_source_count"], 4)
        self.assertEqual(observation["independent_source_phase_url_count"], 4)

    def test_prefix_moves_independent_sources_ahead_of_same_source_duplicates(self) -> None:
        value = target.compare_prefixes(batches(), cap=4)
        stable_hosts = [item["url"].split("//", 1)[1].split("/", 1)[0] for item in value["stable"]]
        candidate_hosts = [item["url"].split("//", 1)[1].split("/", 1)[0] for item in value["candidate"]]
        self.assertEqual(stable_hosts[:2], ["news.alpha.example", "docs.alpha.example"])
        self.assertEqual(
            candidate_hosts,
            ["news.alpha.example", "www.beta.example", "gamma.example", "delta.example"],
        )
        receipt = value["receipt"]
        self.assertEqual(receipt["stable_prefix_registrable_source_count"], 1)
        self.assertEqual(receipt["candidate_prefix_registrable_source_count"], 4)
        self.assertEqual(receipt["registrable_source_coverage_gain"], 3)
        self.assertEqual(receipt["selection_changed"], 1)

    def test_prior_wave_sources_are_deferred_in_second_wave(self) -> None:
        first = target.compare_prefixes(batches(), cap=2)
        prior_sources = set(first["candidate_sources"])
        raw = copy.deepcopy(batches())
        raw[0]["hosted_search_trace"]["actions"].append(
            {"sources": [source("epsilon.example", "e1")]}
        )
        second = target.compare_prefixes(
            raw,
            cap=2,
            prior_control_urls={item["url"] for item in first["stable"]},
            prior_candidate_urls={item["url"] for item in first["candidate"]},
            prior_candidate_sources=prior_sources,
        )
        candidate_sources = set(second["candidate_sources"])
        self.assertEqual(len(candidate_sources), 2)
        self.assertFalse(candidate_sources & prior_sources)
        self.assertTrue(candidate_sources <= {"gamma.example", "delta.example", "epsilon.example"})
        self.assertEqual(
            second["receipt"]["stable_prefix_url_count"],
            second["receipt"]["candidate_prefix_url_count"],
        )

    def test_unattributable_host_is_preserved_but_deferred(self) -> None:
        raw = batches()
        raw[0]["results"].insert(0, source("localhost", "private-shape"))
        ordered, observation, _private = target.order_source_fair_leads(raw)
        urls = [item["url"] for item in ordered]
        self.assertIn("https://localhost/private-shape", urls)
        self.assertEqual(observation["unattributable_url_count"], 1)
        self.assertGreater(
            urls.index("https://localhost/private-shape"),
            urls.index("https://delta.example/d1"),
        )

    def test_empty_input_is_total_and_receipt_is_content_free(self) -> None:
        value = target.compare_prefixes([], cap=6)
        self.assertEqual(value["stable"], [])
        self.assertEqual(value["candidate"], [])
        receipt = value["receipt"]
        self.assertEqual(target.validate_receipt(receipt), receipt)
        self.assertEqual(receipt["input_unique_url_count"], 0)
        self.assertFalse(
            receipt[
                "query_text_provider_narrative_snippet_page_content_or_score_used_for_ordering"
            ]
        )

    def test_source_has_no_evaluator_or_privileged_runtime_capability(self) -> None:
        source_text = (
            ROOT / "src/deepwide_agent/v24959_source_fair_discovery.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any("evaluator" in name or "finalize" in name for name in imports)
        )
        self.assertNotIn("os.environ", source_text)
        for forbidden in ("answer_key", "ground_truth", "benchmark_question_type"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
