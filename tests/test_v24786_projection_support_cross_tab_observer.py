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

from deepwide_agent import (  # noqa: E402
    v24786_projection_support_cross_tab_observer as observer,
)
from deepwide_agent.v24365_entity_segment_projection import (  # noqa: E402
    build_target_segment_catalog,
)
from deepwide_agent.v24743_generic_record_binding import _render_table  # noqa: E402


def page(host: str, content: str) -> dict[str, object]:
    return {"host": host, "content": content, "fetch_integrity": True}


def table(value: str = "Unknown", country: str = "Unknown") -> str:
    return _render_table(
        ["Organization", "Founded", "Country"],
        [["Alpha Observatory", value, country]],
    )


def targets(value: str = "Unknown", country: str = "Unknown") -> list[dict]:
    return [
        {
            "row_key": "Alpha Observatory",
            "column": "Founded",
            "old_value": value,
        },
        {
            "row_key": "Alpha Observatory",
            "column": "Country",
            "old_value": country,
        },
    ]


class V24786ProjectionSupportCrossTabObserverTests(unittest.TestCase):
    def build(
        self,
        pages: list[dict],
        *,
        baseline: str | None = None,
        candidate: str | None = None,
        cells: list[dict] | None = None,
    ) -> dict:
        before_pages = copy.deepcopy(pages)
        catalog = build_target_segment_catalog(cells or targets(), pages, [])
        before_catalog = copy.deepcopy(catalog)
        value = observer.build_projection_support_cross_tab(
            catalog,
            baseline or table(),
            candidate or baseline or table(),
        )
        self.assertEqual(pages, before_pages)
        self.assertEqual(catalog, before_catalog)
        return value

    def test_single_source_unknown_group_is_jointly_quarantined(self) -> None:
        value = self.build(
            [page("one.example", "Alpha Observatory was founded in 1999.")]
        )
        self.assertEqual(value["projection_group_count"], 1)
        self.assertEqual(value["unknown_single_source_projection_group_count"], 1)
        self.assertEqual(value["unknown_two_or_more_source_projection_group_count"], 0)
        self.assertEqual(value["projection_backed_support_group_count"], 0)
        self.assertEqual(value["strict_joint_safe_change_group_count"], 0)
        self.assertEqual(
            value["catalog_quarantine_disposition_counts"][
                "quarantine_insufficient_independence"
            ],
            1,
        )
        row = value["projection_group_cross_tab"][0]
        self.assertEqual(row["baseline_state"], "unknown")
        self.assertEqual(row["projection_source_multiplicity"], "one")
        self.assertEqual(
            row["catalog_disposition"],
            "quarantine_insufficient_independence",
        )
        self.assertEqual(row["proposal_disposition"], "catalog_blocked")
        self.assertEqual(row["candidate_change"], "unchanged")

    def test_two_source_unknown_proposal_and_change_close_strict_joint(self) -> None:
        value = self.build(
            [
                page("one.example", "Alpha Observatory was founded in 1999."),
                page(
                    "two.example.net",
                    "Alpha Observatory was established in 1999.",
                ),
            ],
            candidate=table("1999"),
        )
        self.assertEqual(value["projection_group_count"], 1)
        self.assertEqual(value["unknown_two_or_more_source_projection_group_count"], 1)
        self.assertEqual(value["projection_backed_support_group_count"], 1)
        self.assertEqual(value["unconflicted_unknown_proposal_group_count"], 1)
        self.assertEqual(value["changed_target_count"], 1)
        self.assertEqual(value["strict_joint_safe_change_group_count"], 1)
        row = value["projection_group_cross_tab"][0]
        self.assertEqual(row["catalog_disposition"], "eligible_support")
        self.assertEqual(
            row["proposal_disposition"],
            "unconflicted_projection_backed_unknown_proposal",
        )
        self.assertEqual(
            row["candidate_change"], "changed_to_this_projection_value"
        )
        self.assertTrue(
            value["task_local_joint"]["has_strict_joint_safe_change_group"]
        )

    def test_conflicting_projection_values_do_not_become_safe_proposal(self) -> None:
        value = self.build(
            [
                page("one.example", "Alpha Observatory was founded in 1999."),
                page(
                    "two.example.net",
                    "Alpha Observatory was established in 1999.",
                ),
                page("three.example.edu", "Alpha Observatory was founded in 2001."),
            ]
        )
        self.assertEqual(value["projection_group_count"], 2)
        self.assertEqual(value["unconflicted_unknown_proposal_group_count"], 0)
        self.assertEqual(value["strict_joint_safe_change_group_count"], 0)
        rows = value["projection_group_cross_tab"]
        self.assertTrue(
            any(
                row["catalog_disposition"] == "eligible_support"
                and row["proposal_disposition"] == "projection_value_conflict"
                for row in rows
            )
        )
        self.assertTrue(
            any(
                row["catalog_disposition"]
                == "quarantine_insufficient_independence"
                and row["proposal_disposition"] == "catalog_blocked"
                for row in rows
            )
        )

    def test_zero_projection_targets_remain_in_target_denominator(self) -> None:
        value = self.build([])
        self.assertEqual(value["target_count"], 2)
        self.assertEqual(value["zero_projection_target_count"], 2)
        self.assertEqual(value["projection_group_count"], 0)
        self.assertEqual(value["projection_group_cross_tab"], [])
        self.assertEqual(len(value["target_cross_tab"]), 1)
        row = value["target_cross_tab"][0]
        self.assertEqual(row["baseline_state"], "unknown")
        self.assertEqual(row["projected_value_group_count"], "zero")
        self.assertEqual(row["count"], 2)

    def test_known_target_is_not_relabelled_as_unknown_proposal(self) -> None:
        baseline = table("1998")
        value = self.build(
            [
                page("one.example", "Alpha Observatory was founded in 1999."),
                page("two.example.net", "Alpha Observatory was founded in 1999."),
                page("three.example.edu", "Alpha Observatory was founded in 1999."),
            ],
            baseline=baseline,
            candidate=baseline,
            cells=targets("1998"),
        )
        self.assertEqual(value["unknown_projection_group_count"], 0)
        self.assertEqual(value["unconflicted_unknown_proposal_group_count"], 0)
        self.assertEqual(
            value["projection_group_cross_tab"][0]["proposal_disposition"],
            "not_unknown",
        )

    def test_candidate_nonunknown_mutation_fails_closed(self) -> None:
        baseline = table("1998")
        catalog = build_target_segment_catalog(
            targets("1998"),
            [page("one.example", "Alpha Observatory was founded in 1999.")],
            [],
        )
        with self.assertRaises(ValueError):
            observer.build_projection_support_cross_tab(
                catalog, baseline, table("1999")
            )

    def test_receipt_contains_fixed_counts_not_private_literals(self) -> None:
        private_entity = "Unique Private Observatory Zeta"
        cells = [
            {
                "row_key": private_entity,
                "column": "Founded",
                "old_value": "Unknown",
            }
        ]
        baseline = _render_table(
            ["Organization", "Founded"], [[private_entity, "Unknown"]]
        )
        catalog = build_target_segment_catalog(
            cells,
            [page("private-source.example", f"{private_entity} was founded in 1987.")],
            [],
        )
        value = observer.build_projection_support_cross_tab(
            catalog, baseline, baseline
        )
        encoded = json.dumps(value, ensure_ascii=False).casefold()
        for literal in (
            private_entity.casefold(),
            "private-source.example",
            "founded",
            "1987",
            baseline.casefold(),
        ):
            self.assertNotIn(literal, encoded)
        self.assertFalse(value["positive_entropy_or_task_credit_assigned"])
        self.assertFalse(
            value["cross_task_or_cross_group_margins_used_as_joint"]
        )

    def test_resealed_joint_or_authority_tamper_fails(self) -> None:
        value = self.build(
            [
                page("one.example", "Alpha Observatory was founded in 1999."),
                page("two.example.net", "Alpha Observatory was founded in 1999."),
            ],
            candidate=table("1999"),
        )
        mutations = (
            lambda item: item.__setitem__("strict_joint_safe_change_group_count", 0),
            lambda item: item.__setitem__("unknown_projection_group_count", 0),
            lambda item: item["catalog_quarantine_disposition_counts"].__setitem__(
                "quarantine_insufficient_independence", 1
            ),
            lambda item: item["task_local_joint"].__setitem__(
                "has_strict_joint_safe_change_group", False
            ),
            lambda item: item.__setitem__(
                "benchmark_launch_or_evaluator_authorized", True
            ),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                altered = copy.deepcopy(value)
                mutate(altered)
                altered.pop("receipt_sha256")
                altered["receipt_sha256"] = observer.payload_sha256(altered)
                with self.assertRaises(ValueError):
                    observer.validate_receipt(altered)

    def test_module_has_no_external_or_privileged_capability(self) -> None:
        tree = ast.parse(Path(observer.__file__).read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertTrue(
            imported.isdisjoint(
                {
                    "os",
                    "pathlib",
                    "requests",
                    "socket",
                    "subprocess",
                    "httpx",
                }
            )
        )
        privileged = {
            "answer",
            "answer_key",
            "category",
            "evaluator",
            "gold",
            "ground_truth",
            "mapping",
            "question_type",
            "reward",
            "score",
            "split",
            "task_category",
        }
        accesses = []
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            if isinstance(key, str) and key.casefold() in privileged:
                accesses.append((node.lineno, key))
        self.assertEqual(accesses, [])


if __name__ == "__main__":
    unittest.main()
