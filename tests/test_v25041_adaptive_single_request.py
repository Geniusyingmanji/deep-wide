from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25041_adaptive_single_request as target  # noqa: E402


SEEDS = (
    "Rust 1.80 official documentation language and compiler changes",
    "Rust 1.80 official release notes library features",
)


def action(query: str, *titles: str, queries: list[str] | None = None) -> dict:
    return {
        "type": "web_search_call",
        "id": "call",
        "status": "completed",
        "action": {
            "type": "search",
            "query": query,
            "queries": queries or [],
            "sources": [
                {
                    "type": "url",
                    "url": f"https://example.org/{index}-{len(query)}",
                    "title": title,
                }
                for index, title in enumerate(titles)
            ],
        },
    }


def positive_payload() -> dict:
    return {
        "output": [
            action(SEEDS[0], "Rust stabilizes LazyCell in standard library"),
            action(SEEDS[1], "Cargo adds manifest lint table"),
            action("Rust 1.80 LazyCell stabilization details", "detail"),
            action("Rust 1.80 Cargo manifest lint details", "detail"),
        ]
    }


class V25041AdaptiveSingleRequestTests(unittest.TestCase):
    def test_request_contains_only_seed_queries_and_freezes_two_phase_contract(self) -> None:
        body = target.build_adaptive_request_body(
            model="gpt-5.6-sol",
            seed_queries=SEEDS,
            search_context_size="medium",
            reasoning_effort="low",
            service_tier="priority",
        )
        target.validate_adaptive_request_body(body, expected_seed_queries=SEEDS)
        combined = "\n".join(item["content"] for item in body["input"])
        self.assertEqual(combined.count(SEEDS[0]), 1)
        self.assertEqual(combined.count(SEEDS[1]), 1)
        self.assertEqual(body["tool_choice"], "required")
        self.assertEqual(body["include"], ["web_search_call.action.sources"])

    def test_positive_trace_requires_order_anchor_and_title_novelty(self) -> None:
        value = target.analyze_adaptive_trace(positive_payload(), SEEDS)
        self.assertTrue(value["receipt"]["trace_capability_passed"])
        self.assertEqual(value["receipt"]["followup_query_count"], 2)
        self.assertEqual(value["receipt"]["followups_with_seed_anchor"], 2)
        self.assertEqual(
            value["receipt"]["followups_with_seed_title_novel_token"], 2
        )
        self.assertEqual(len(value["followup_queries"]), 2)

    def test_followup_before_second_seed_fails_closed(self) -> None:
        payload = positive_payload()
        payload["output"][1], payload["output"][2] = (
            payload["output"][2],
            payload["output"][1],
        )
        value = target.analyze_adaptive_trace(payload, SEEDS)
        self.assertFalse(value["receipt"]["trace_capability_passed"])
        self.assertFalse(value["receipt"]["seed_exact_first_order"])

    def test_seed_rewrite_fails_exact_order_check(self) -> None:
        payload = positive_payload()
        payload["output"][0]["action"]["query"] = SEEDS[0] + " overview"
        value = target.analyze_adaptive_trace(payload, SEEDS)
        self.assertFalse(value["receipt"]["trace_capability_passed"])
        self.assertFalse(value["receipt"]["seed_exact_first_order"])

    def test_generic_followups_without_title_novelty_fail(self) -> None:
        payload = positive_payload()
        payload["output"][2]["action"]["query"] = "Rust 1.80 official details"
        payload["output"][3]["action"]["query"] = "Rust 1.80 documentation overview"
        value = target.analyze_adaptive_trace(payload, SEEDS)
        self.assertFalse(value["receipt"]["trace_capability_passed"])
        self.assertEqual(
            value["receipt"]["followups_with_seed_title_novel_token"], 0
        )

    def test_mixed_seed_and_followup_action_fails(self) -> None:
        payload = {
            "output": [
                action(SEEDS[0], "Rust stabilizes LazyCell"),
                action(
                    SEEDS[1],
                    "Cargo adds manifest lint table",
                    queries=["Rust 1.80 Cargo manifest lint details"],
                ),
                action("Rust 1.80 LazyCell stabilization details", "detail"),
            ]
        }
        value = target.analyze_adaptive_trace(payload, SEEDS)
        self.assertFalse(value["receipt"]["trace_capability_passed"])
        self.assertEqual(value["receipt"]["mixed_seed_followup_action_count"], 1)

    def test_fifth_distinct_query_fails_exact_four_gate(self) -> None:
        payload = positive_payload()
        payload["output"].append(action("Rust 1.80 fifth query", "detail"))
        value = target.analyze_adaptive_trace(payload, SEEDS)
        self.assertFalse(value["receipt"]["trace_capability_passed"])
        self.assertEqual(value["receipt"]["distinct_action_query_count"], 5)

    def test_module_has_no_privileged_or_effect_capability(self) -> None:
        source = (ROOT / "src/deepwide_agent/v25041_adaptive_single_request.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertFalse(imports & {"os", "subprocess", "requests", "pathlib"})
        for marker in (
            "question_type",
            "ground_truth",
            "answer_key",
            "results.csv",
            "tvly-dev-",
            "ghp_",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
