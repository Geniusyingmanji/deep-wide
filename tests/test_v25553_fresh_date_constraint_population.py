from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25541_visible_output_constraint_contract as constraints  # noqa: E402
from deepwide_agent import v25553_fresh_date_constraint_population as target  # noqa: E402


class V25553FreshDateConstraintPopulationTests(unittest.TestCase):
    def test_whole_static_population_is_unique_and_hash_bound(self) -> None:
        identities = target.identity_vector()
        tasks = target.task_vector()
        self.assertEqual(len(identities), 40)
        self.assertEqual(len(set(identities)), 40)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertEqual(
            target.payload_sha256(identities), target.EXPECTED_IDENTITY_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_all_tasks_activate_only_date_and_order_contracts(self) -> None:
        for row in target.task_vector():
            contract = constraints.build_contract(row["question"], target.DATE_COLUMNS)
            self.assertEqual(contract["active_family_count"], 2)
            self.assertEqual(contract["date_format"]["style"], "chinese_ymd_unpadded")
            self.assertIsNone(contract["numeric_scale"])
            self.assertIsNone(contract["temporal_year_range"])
            self.assertIsNone(contract["rank_slots"])
            self.assertEqual(
                contract["explicit_order"],
                {
                    "target_column": "Latest Stable Release Date",
                    "direction": "descending",
                    "value_kind": "date",
                },
            )

    def test_questions_fix_no_stable_unknown_and_unknown_order_semantics(self) -> None:
        for row in target.task_vector():
            question = row["question"]
            self.assertIn("no stable release must use Unknown", question)
            self.assertIn("place Unknown after known dates", question)
            self.assertIn("preserving supplied order among Unknown rows", question)

    def test_task_validation_and_tamper_fail_closed(self) -> None:
        values = target.task_vector()
        self.assertEqual(target.validate_task_vector(values), values)
        for kind in ("question", "opaque", "denominator"):
            changed = copy.deepcopy(values)
            if kind == "question":
                changed[0]["question"] += " altered"
            elif kind == "opaque":
                changed[0]["opaque_id"] = changed[1]["opaque_id"]
            else:
                changed.pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_task_vector(changed)

    def test_policy_and_gates_are_outcome_blind_and_forbid_launch(self) -> None:
        policy = target.source_policy()
        mechanism = target.mechanism_gate()
        quality = target.quality_gate()
        self.assertTrue(policy["selection_reads_repository_history_only"])
        self.assertFalse(
            policy[
                "endpoint_page_version_date_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection"
            ]
        )
        self.assertFalse(
            policy["network_model_search_fetch_evaluator_or_benchmark_authorized"]
        )
        self.assertEqual(mechanism["minimum_date_contract_tasks"], 20)
        self.assertEqual(mechanism["minimum_scale_contract_tasks"], 0)
        self.assertEqual(
            mechanism[
                "candidate_additional_queries_fetches_model_calls_or_sampling_effects"
            ],
            0,
        )
        self.assertTrue(
            quality["official_identity_bound_no_stable_release_is_valid_unknown"]
        )
        self.assertEqual(quality["positive_signed_credit_count"], 0)

    def test_population_module_has_no_io_or_privileged_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden_call in (
            "open(",
            "getenv(",
            "model.complete(",
            "search_many(",
            "fetch_urls(",
        ):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
