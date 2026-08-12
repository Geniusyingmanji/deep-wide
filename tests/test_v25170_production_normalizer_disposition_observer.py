from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24986_robust_paired_runtime as frozen  # noqa: E402
from deepwide_agent import v25170_production_normalizer_disposition_observer as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


COLUMNS = ("Package", "Version", "License", "NeedsCompilation")


class V25170ProductionNormalizerObserverTests(unittest.TestCase):
    def _observe(
        self, text: str, *, columns=COLUMNS, truncated: bool = False
    ) -> dict:
        return target.observe_production_normalization(
            text,
            columns=columns,
            provider_output_truncated=truncated,
        )

    def test_exact_and_normalized_acceptance_match_frozen_parent(self) -> None:
        exact = (
            "```markdown\n"
            "| Package | Version | License | NeedsCompilation |\n"
            "| --- | --- | --- | --- |\n"
            "| alpha | 1.2.3 | MIT | no |\n"
            "```"
        )
        normalized = (
            "| Name | Release | Terms | Compiles |\n"
            "| --- | --- | --- | --- |\n"
            "| alpha | 1.2.3 | MIT | no |"
        )
        for text, reason in (
            (exact, "exact_table_accepted"),
            (normalized, "normalized_table_accepted"),
        ):
            with self.subTest(reason=reason):
                value = self._observe(text)
                parent, _status = frozen._normalize_synthesis(
                    text, COLUMNS, "visible English question"
                )
                self.assertIsNotNone(parent)
                self.assertEqual(value["disposition_counts"][reason], 1)
                self.assertTrue(value["frozen_synthesis_contract_accepted"])

    def test_all_reject_dispositions_are_mutually_exclusive_and_parent_rejects(self) -> None:
        cases = {
            "invalid_required_columns_reject": (
                "plain prose",
                ("Package", "Package"),
            ),
            "no_pipe_group_reject": ("plain prose", COLUMNS),
            "no_separator_row_reject": (
                "| Package | Version | License | NeedsCompilation |\n"
                "| alpha | 1.2.3 | MIT | no |",
                COLUMNS,
            ),
            "no_bindable_header_reject": (
                "| Other | Thing |\n| --- | --- |\n| alpha | beta |",
                COLUMNS,
            ),
            "separator_width_mismatch_reject": (
                "| Package | Version | License | NeedsCompilation |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| alpha | 1.2.3 | MIT | no |",
                COLUMNS,
            ),
            "missing_data_rows_reject": (
                "| Package | Version | License | NeedsCompilation |\n"
                "| --- | --- | --- | --- |",
                COLUMNS,
            ),
            "malformed_row_or_escaped_pipe_reject": (
                "| Package | Version | License | NeedsCompilation |\n"
                "| --- | --- | --- | --- |\n"
                "| alpha | 1.2.3 | MIT\\|Apache | no |",
                COLUMNS,
            ),
        }
        for reason, (text, columns) in cases.items():
            with self.subTest(reason=reason):
                value = self._observe(text, columns=columns)
                parent, _status = frozen._normalize_synthesis(
                    text, columns, "visible English question"
                )
                self.assertIsNone(parent)
                self.assertEqual(value["disposition_counts"][reason], 1)
                self.assertEqual(sum(value["disposition_counts"].values()), 1)
                self.assertFalse(value["frozen_synthesis_contract_accepted"])

    def test_output_truncation_is_observed_without_changing_disposition(self) -> None:
        text = "plain prose"
        control = self._observe(text, truncated=False)
        candidate = self._observe(text, truncated=True)
        self.assertEqual(control["disposition_counts"], candidate["disposition_counts"])
        self.assertFalse(control["provider_output_truncated"])
        self.assertTrue(candidate["provider_output_truncated"])

    def test_semantically_different_same_structure_has_same_observation(self) -> None:
        first = self._observe("alpha prose without a table")
        second = self._observe("beta words with no markdown structure")
        self.assertEqual(first, second)
        encoded = json.dumps(first, ensure_ascii=False)
        for forbidden in ("alpha", "beta", "Package", "https://"):
            self.assertNotIn(forbidden, encoded)

    def test_tamper_count_credit_launch_or_behavior_fails_closed(self) -> None:
        value = self._observe("plain prose")
        for kind in ("count", "credit", "launch", "behavior"):
            changed = copy.deepcopy(value)
            if kind == "count":
                changed["pipe_group_count"] = 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "launch":
                changed["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed[
                    "observer_changes_response_fallback_prediction_candidate_routing_or_budget"
                ] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_observation(changed)

    def test_module_is_pure_label_blind_and_effect_free(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25170_production_normalizer_disposition_observer.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: list[str] = []
        privileged: list[str] = []
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value
                in {
                    "category",
                    "question_type",
                    "task_category",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }
            ):
                privileged.append(str(node.slice.value))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        self.assertTrue(
            {name.split(".")[0] for name in imports}.isdisjoint(
                {
                    "os",
                    "pathlib",
                    "socket",
                    "subprocess",
                    "requests",
                    "httpx",
                    "openai",
                }
            )
        )
        self.assertEqual(privileged, [])
        self.assertTrue(
            calls.isdisjoint(
                {"complete", "search_many", "fetch_urls", "create_connection"}
            )
        )


if __name__ == "__main__":
    unittest.main()
