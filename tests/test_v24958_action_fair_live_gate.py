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

from scripts import v24958_action_fair_live_gate as gate  # noqa: E402


def source(label: str) -> dict[str, str]:
    return {
        "type": "url", "title": "",
        "url": f"https://{label}.example/record",
        "fetch_url": f"https://{label}.example/record",
    }


def batches() -> list[dict]:
    return [
        {
            "query": "discarded",
            "answer": "discarded",
            "results": [source("local")],
            "error": None,
            "hosted_search_trace": {
                "actions": [
                    {"sources": [source(f"a{i}") for i in range(1, 7)]},
                    {"sources": [source("b1"), source("b2")]},
                    {"sources": [source("c1")]},
                ]
            },
        }
    ]


def passing_row() -> dict[str, int | float | bool]:
    return {
        "terminal": True,
        "completed": True,
        "logical_query_rows": 4,
        "search_provider_attempts": 2,
        "search_provider_response_calls": 2,
        "search_http_2xx": 2,
        "transport_failures": 0,
        "hosted_search_deadline_failures": 0,
        "raw_action_group_count": 4,
        "raw_action_source_count": 24,
        "matched_selection": True,
        "control_selected_leads": 10,
        "candidate_selected_leads": 10,
        "selection_changed": True,
        "control_action_group_coverage": 2,
        "candidate_action_group_coverage": 4,
        "action_group_coverage_gain": 2,
        "action_group_coverage_gain_task": True,
        "control_usable_pages": 8,
        "candidate_usable_pages": 8,
        "control_usable_chars": 30000,
        "candidate_usable_chars": 30000,
        "control_selected_unique_hosts": 8,
        "candidate_selected_unique_hosts": 8,
        "physical_union_fetches": 15,
        "hard_fetch_helper_calls": 15,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "fetch_deadline_rejections": 0,
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "wall_seconds": 20.0,
    }


class V24958ActionFairLiveGateTests(unittest.TestCase):
    def test_protocol_freezes_production_shaped_shared_prefix(self) -> None:
        value = gate.build_protocol(
            now=1, require_clean=False, require_pristine=False,
            require_watchers=False,
        )
        self.assertEqual(value["schedule"]["task_count"], 20)
        self.assertEqual(value["schedule"]["executor_concurrency"], 20)
        self.assertEqual(value["schedule"]["wave_fetch_caps"], [6, 4])
        self.assertEqual(value["schedule"]["fetch_cap_per_arm"], 10)
        self.assertTrue(value["schedule"]["shared_response_replay"])
        self.assertTrue(value["schedule"]["task_local_shared_fetch_union"])
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_query_population_is_fixed_fresh_neutral_shape(self) -> None:
        vector = gate.query_vector()
        self.assertEqual(len(vector), 20)
        self.assertTrue(all(len(row) == 4 for row in vector))
        self.assertTrue(
            all("official documentation" in query.casefold() for row in vector for query in row)
        )

    def test_shared_response_selection_changes_prefix_and_matches_cost(self) -> None:
        value = gate.select_wave_prefixes(batches(), cap=6)
        control = [item["url"] for item in value[gate.CONTROL]]
        candidate = [item["url"] for item in value[gate.CANDIDATE]]
        self.assertEqual(len(control), len(candidate))
        self.assertEqual(len(control), 6)
        self.assertNotEqual(control, candidate)
        self.assertEqual(len(value["control_action_groups"]), 1)
        self.assertEqual(len(value["candidate_action_groups"]), 3)
        self.assertTrue(value["source_set_equal"])

    def test_prior_wave_urls_are_skipped_without_losing_cap_when_capacity_exists(self) -> None:
        first = gate.select_wave_prefixes(batches(), cap=6)
        control_prior = {item["url"] for item in first[gate.CONTROL]}
        candidate_prior = {item["url"] for item in first[gate.CANDIDATE]}
        second_raw = copy.deepcopy(batches())
        second_raw[0]["hosted_search_trace"]["actions"].append(
            {"sources": [source(f"z{i}") for i in range(1, 7)]}
        )
        second = gate.select_wave_prefixes(
            second_raw, cap=4, prior_control=control_prior,
            prior_candidate=candidate_prior,
        )
        self.assertEqual(len(second[gate.CONTROL]), 4)
        self.assertEqual(len(second[gate.CANDIDATE]), 4)
        self.assertFalse(
            control_prior & {item["url"] for item in second[gate.CONTROL]}
        )
        self.assertFalse(
            candidate_prior & {item["url"] for item in second[gate.CANDIDATE]}
        )

    def test_aggregate_gate_is_content_free_and_fail_closed(self) -> None:
        aggregate = gate._aggregate([passing_row() for _ in range(20)], 30.0)
        self.assertTrue(gate.decision(aggregate)["action_fair_live_gate_go"])
        self.assertFalse(
            aggregate[
                "contains_query_url_host_title_page_answer_provider_payload_selection_or_per_task_row"
            ]
        )
        aggregate["candidate_usable_pages"] = aggregate["control_usable_pages"] - 1
        decision = gate.decision(aggregate)
        self.assertFalse(decision["action_fair_live_gate_go"])
        self.assertIn("candidate_usable_pages_noninferior", decision["failed_checks"])

    def test_source_has_no_evaluator_or_credential_capability(self) -> None:
        source_text = (ROOT / "scripts/v24958_action_fair_live_gate.py").read_text(
            encoding="utf-8"
        )
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
        self.assertIsNone(gate.SECRET.search(source_text))


if __name__ == "__main__":
    unittest.main()
