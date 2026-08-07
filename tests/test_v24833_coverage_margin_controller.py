from __future__ import annotations

import ast
import copy
import dataclasses
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24272_two_wave_entropy_voc import FirstWaveObservation  # noqa: E402
from deepwide_agent.v24833_coverage_margin_controller import (  # noqa: E402
    POLICY_VALUES,
    build_synthetic_gate,
    coverage_margin_policy,
    decide_coverage_margin,
    payload_sha256,
    validate_receipt,
)


def observation(**changes):
    values = {
        "queries_executed": 2,
        "sources_discovered": 6,
        "fetches_attempted": 6,
        "usable_pages": 6,
        "novel_pages": 6,
        "unique_hosts": 3,
        "content_chars": 12_000,
        "required_column_count": 4,
        "explicit_row_target": 0,
        "search_seconds": 10.0,
        "fetch_seconds": 10.0,
        "unrecoverable_search_failures": 0,
    }
    values.update(changes)
    return FirstWaveObservation(**values)


class V24833CoverageMarginControllerTests(unittest.TestCase):
    def test_policy_is_frozen_and_entropy_zero_weight(self) -> None:
        self.assertEqual(dataclasses.asdict(coverage_margin_policy()), POLICY_VALUES)
        self.assertEqual(POLICY_VALUES["minimum_usable_pages"], 6)
        self.assertEqual(POLICY_VALUES["minimum_novel_pages"], 6)
        self.assertEqual(POLICY_VALUES["maximum_wave1_seconds"], 60.0)
        self.assertEqual(POLICY_VALUES["information_gain_weight"], 0.0)

    def test_complete_margin_can_stop_early(self) -> None:
        value = decide_coverage_margin(observation())
        self.assertEqual(value["decision"], "stop")
        self.assertEqual(value["reason"], "first_wave_sufficient")
        self.assertTrue(value["coverage_margin"]["early_stop_authorized"])

    def test_one_unusable_or_duplicate_page_expands(self) -> None:
        for changed in (
            {"usable_pages": 5, "novel_pages": 5},
            {"novel_pages": 5},
            {"unique_hosts": 1},
            {"content_chars": 4_799},
        ):
            value = decide_coverage_margin(observation(**changed))
            self.assertEqual(value["decision"], "expand")
            self.assertFalse(value["coverage_margin"]["early_stop_authorized"])

    def test_sixty_second_ceiling_stops_incomplete_prefix(self) -> None:
        value = decide_coverage_margin(
            observation(
                usable_pages=2,
                novel_pages=2,
                unique_hosts=1,
                content_chars=1_000,
                search_seconds=30.0,
                fetch_seconds=30.0,
            )
        )
        self.assertEqual(value["decision"], "stop")
        self.assertEqual(value["reason"], "latency_ceiling")
        self.assertFalse(value["coverage_margin"]["inside_safety_ceiling"])

    def test_synthetic_grid_proves_safety_invariants(self) -> None:
        gate = build_synthetic_gate()
        self.assertGreater(gate["counts"]["observations"], 1_000)
        self.assertGreater(gate["counts"]["early_stops"], 0)
        self.assertGreater(gate["counts"]["in_budget_incomplete_expands"], 0)
        self.assertEqual(gate["counts"]["unsafe_early_stops"], 0)
        self.assertEqual(gate["counts"]["in_budget_incomplete_stops"], 0)
        self.assertEqual(gate["counts"]["entropy_nonzero"], 0)

    def test_resealed_tamper_fails_replay(self) -> None:
        value = decide_coverage_margin(observation())
        for mutation in ("decision", "margin", "history"):
            altered = copy.deepcopy(value)
            if mutation == "decision":
                altered["decision"] = "expand"
            elif mutation == "margin":
                altered["coverage_margin"]["full_fetch_yield"] = False
            else:
                altered["historical_benchmark_metric_or_stratum_read"] = True
            altered.pop("receipt_sha256")
            altered["receipt_sha256"] = payload_sha256(altered)
            with self.assertRaises(ValueError):
                validate_receipt(altered)

    def test_ast_has_no_io_or_dynamic_execution_surface(self) -> None:
        path = SRC / "deepwide_agent/v24833_coverage_margin_controller.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "subprocess", "requests", "socket", "urllib"}
            )
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"})
        )


if __name__ == "__main__":
    unittest.main()
