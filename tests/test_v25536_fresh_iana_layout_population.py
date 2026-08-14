from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25509_fresh_multirow_uncertainty_population as prior9  # noqa: E402
from deepwide_agent import v25516_fresh_evidence_coverage_population as prior16  # noqa: E402
from deepwide_agent import v25523_fresh_source_bound_population as prior23  # noqa: E402
from deepwide_agent import v25527_independent_iana_shape_study as research  # noqa: E402
from deepwide_agent import v25536_fresh_iana_layout_population as target  # noqa: E402


class V25536FreshIanaLayoutPopulationTests(unittest.TestCase):
    def test_pairs_match_pushed_selection_snapshot_exactly(self) -> None:
        snapshot = json.loads(
            (ROOT / target.SELECTION_SNAPSHOT).read_text(encoding="utf-8")
        )
        pairs = target.pair_vector()
        flattened = [identity for pair in pairs for identity in pair]
        self.assertEqual(
            pairs, [tuple(pair) for pair in snapshot["selection"]["pairs"]]
        )
        self.assertEqual(flattened, snapshot["selection"]["selected_identities"])
        self.assertEqual(len(pairs), 20)
        self.assertEqual(len(set(flattened)), 40)
        self.assertEqual(flattened[0], ".bridgestone")
        self.assertEqual(flattened[-1], ".cbre")
        self.assertEqual(
            target.payload_sha256(pairs), target.EXPECTED_PAIR_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(flattened),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )

    def test_identity_question_and_opaque_vectors_are_disjoint_from_prior_blocks(self) -> None:
        tasks = target.task_vector()
        prior_pairs = [*prior9.PAIRS, *prior16.PAIRS, *prior23.PAIRS]
        prior_rows = {identity for pair in prior_pairs for identity in pair}
        prior_rows.update(research.STUDY_IDENTITIES)
        prior_tasks = [
            *prior9.task_vector(),
            *prior16.task_vector(),
            *prior23.task_vector(),
        ]
        self.assertFalse(
            {identity for pair in target.PAIRS for identity in pair} & prior_rows
        )
        self.assertFalse(
            {task["question"] for task in tasks}
            & {task["question"] for task in prior_tasks}
        )
        self.assertFalse(
            {task["opaque_id"] for task in tasks}
            & {task["opaque_id"] for task in prior_tasks}
        )

    def test_task_vector_contains_only_visible_pair_and_schema(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 20)
        for task, pair in zip(tasks, target.PAIRS, strict=True):
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertEqual(task["question"].count("<DOMAIN>"), 2)
            self.assertIn(pair[0], task["question"])
            self.assertIn(pair[1], task["question"])
            for forbidden in (
                "https://",
                "iana",
                "delegation",
                "sponsoring organisation",
                "parenthetical",
                "coverage",
            ):
                self.assertNotIn(forbidden, task["question"].casefold())
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_source_policy_and_atomic_layout_gate_are_strict(self) -> None:
        policy = target.source_policy()
        gate = target.mechanism_gate()
        self.assertEqual(
            policy["runtime_boundary"],
            ["opaque_id", "question", "same_forward_public_pages"],
        )
        self.assertTrue(
            policy[
                "all_prior_tld_populations_and_v25527_research_identities_excluded"
            ]
        )
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertEqual(gate["minimum_iana_layout_complete_page_tasks"], 2)
        self.assertEqual(gate["minimum_applied_coordinate_count_total"], 4)
        self.assertEqual(gate["minimum_treatment_changed_tasks"], 2)
        self.assertEqual(
            gate["minimum_treatment_changed_coordinate_count_total"], 4
        )
        self.assertEqual(gate["candidate_additional_fetches_beyond_parent"], 0)
        self.assertEqual(gate["positive_signed_credit_count"], 0)

    def test_tamper_or_privileged_shape_fails(self) -> None:
        tasks = target.task_vector()
        for kind in ("drop", "hint", "metadata"):
            changed = copy.deepcopy(tasks)
            if kind == "drop":
                changed.pop()
            elif kind == "hint":
                changed[0]["question"] += " IANA delegation layout"
            else:
                changed[0]["category"] = "forbidden"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_task_vector(changed)

    def test_module_is_pure_and_authorizes_no_effect(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any(
                name == blocked or name.startswith(blocked + ".")
                for blocked in (
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "httpx",
                )
                for name in imports
            )
        )
        self.assertFalse(
            target.source_policy()[
                "network_model_search_fetch_evaluator_or_benchmark_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
