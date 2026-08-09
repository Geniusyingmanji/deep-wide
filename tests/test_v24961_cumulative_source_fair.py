from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24961_cumulative_source_fair as target  # noqa: E402


def source(host: str, suffix: str) -> dict[str, str]:
    return {
        "type": "url", "title": "",
        "url": f"https://{host}/{suffix}",
        "fetch_url": f"https://{host}/{suffix}",
    }


def wave(actions: list[list[dict[str, str]]]) -> list[dict]:
    return [{
        "query": "discarded", "answer": "discarded", "results": [], "error": None,
        "hosted_search_trace": {"actions": [{"sources": values} for values in actions]},
    }]


class V24961CumulativeSourceFairTests(unittest.TestCase):
    def test_reproduces_v24960_local_false_failure_and_accepts_cumulative_gain(self) -> None:
        first = target.compare_cumulative_prefixes(
            wave([
                [
                    source("alpha.example", "a1"),
                    source("alpha.example", "a2"),
                    source("alpha.example", "a3"),
                ],
                [source("beta.example", "b1")],
                [source("gamma.example", "g1")],
            ]),
            cap=3,
        )
        self.assertEqual(
            first["candidate_cumulative_sources"],
            {"alpha.example", "beta.example", "gamma.example"},
        )
        self.assertEqual(first["control_cumulative_sources"], {"alpha.example"})
        second = target.compare_cumulative_prefixes(
            wave([
                [
                    source("alpha.example", "a4"),
                    source("beta.example", "b2"),
                    source("gamma.example", "g2"),
                ],
                [source("alpha.example", "a5")],
                [source("delta.example", "d1")],
            ]),
            cap=3,
            prior_control_urls={item["url"] for item in first["stable"]},
            prior_candidate_urls={item["url"] for item in first["candidate"]},
            prior_control_sources=first["control_cumulative_sources"],
            prior_candidate_sources=first["candidate_cumulative_sources"],
        )
        receipt = second["receipt"]
        self.assertLess(
            receipt["candidate_current_registrable_source_count"],
            receipt["stable_current_registrable_source_count"],
        )
        self.assertGreaterEqual(
            receipt["candidate_cumulative_registrable_source_count"],
            receipt["stable_cumulative_registrable_source_count"],
        )
        self.assertEqual(target.validate_receipt(receipt), receipt)

    def test_cumulative_regression_still_fails_closed(self) -> None:
        raw = wave([[source("alpha.example", "a1")]])
        with self.assertRaises(RuntimeError):
            target.compare_cumulative_prefixes(
                raw,
                cap=1,
                prior_control_sources={"alpha.example", "beta.example"},
                prior_candidate_sources=set(),
            )

    def test_matched_cost_and_no_prior_matches_single_wave_behavior(self) -> None:
        raw = wave([
            [source("alpha.example", "a1"), source("alpha.example", "a2")],
            [source("beta.example", "b1")],
            [source("gamma.example", "g1")],
        ])
        value = target.compare_cumulative_prefixes(raw, cap=3)
        self.assertEqual(len(value["stable"]), len(value["candidate"]))
        self.assertEqual(value["receipt"]["candidate_cumulative_registrable_source_count"], 3)
        self.assertGreaterEqual(
            value["receipt"]["candidate_cumulative_registrable_source_count"],
            value["receipt"]["stable_cumulative_registrable_source_count"],
        )

    def test_source_has_no_evaluator_or_privileged_runtime_capability(self) -> None:
        source_text = (
            ROOT / "src/deepwide_agent/v24961_cumulative_source_fair.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertNotIn("os.environ", source_text)
        for forbidden in ("answer_key", "ground_truth", "benchmark_question_type"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
