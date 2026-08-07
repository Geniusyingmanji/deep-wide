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

from deepwide_agent import v24781_projection_conversion_funnel as target  # noqa: E402
from deepwide_agent.v24365_entity_segment_projection import (  # noqa: E402
    build_target_segment_catalog,
)


def page(host: str, content: str) -> dict[str, object]:
    return {"host": host, "content": content, "fetch_integrity": True}


def cell(entity: str, column: str = "Founding year", old: str = "Unknown") -> dict:
    return {"row_key": entity, "column": column, "old_value": old}


class V24781ProjectionConversionFunnelTests(unittest.TestCase):
    def receipt(self, targets: list[dict], pages: list[dict], reserve=None) -> dict:
        catalog = build_target_segment_catalog(targets, pages, reserve or [])
        frozen = copy.deepcopy(catalog)
        value = target.build_projection_conversion_funnel(catalog)
        self.assertEqual(catalog, frozen)
        return value

    def test_pair_reason_partition_covers_strict_projection_stages(self) -> None:
        cases = (
            (
                "unsupported_column_kind",
                [cell("Alpha Observatory", "Favorite color")],
                [page("one.example", "Alpha Observatory has blue branding.")],
            ),
            (
                "exact_entity_anchor_absent",
                [cell("Alpha Observatory")],
                [page("one.example", "Another institute was founded in 1999.")],
            ),
            (
                "explicit_relation_absent",
                [cell("Alpha Observatory")],
                [page("one.example", "Alpha Observatory remains active today.")],
            ),
            (
                "relation_token_without_parsable_value",
                [cell("Alpha Observatory")],
                [page("one.example", "Alpha Observatory was founded in an unknown era.")],
            ),
            (
                "parsable_relation_not_bound",
                [cell("Alpha Observatory")],
                [page("one.example", "Founded Alpha Observatory in 1999.")],
            ),
            (
                "projection_emitted",
                [cell("Alpha Observatory")],
                [page("one.example", "Alpha Observatory was founded in 1999.")],
            ),
        )
        for expected, cells, pages in cases:
            with self.subTest(reason=expected):
                receipt = self.receipt(cells, pages)
                self.assertEqual(receipt["page_target_pair_count"], 1)
                self.assertEqual(receipt["reason_counts"][expected], 1)
                self.assertEqual(sum(receipt["reason_counts"].values()), 1)
                self.assertTrue(receipt["reason_partition_exact"])

    def test_two_sources_close_one_unknown_proposal(self) -> None:
        cells = [cell("Alpha Observatory")]
        pages = [
            page("one.example", "Alpha Observatory was founded in 1999."),
            page("two.example.net", "Alpha Observatory was established in 1999."),
        ]
        receipt = self.receipt(cells, pages)
        self.assertEqual(receipt["semantic_projection_count"], 2)
        self.assertEqual(receipt["distinct_target_value_projection_count"], 1)
        self.assertEqual(receipt["projection_single_source_group_count"], 0)
        self.assertEqual(receipt["projection_two_or_more_source_group_count"], 1)
        self.assertEqual(receipt["catalog_eligible_support_set_count"], 1)
        self.assertEqual(receipt["projection_backed_eligible_support_set_count"], 1)
        self.assertEqual(
            receipt["unconflicted_projection_backed_unknown_proposal_count"], 1
        )

    def test_single_source_and_same_registrable_domain_do_not_close_support(self) -> None:
        cells = [cell("Alpha Observatory")]
        for pages in (
            [page("one.example.org", "Alpha Observatory was founded in 1999.")],
            [
                page("one.example.org", "Alpha Observatory was founded in 1999."),
                page("two.example.org", "Alpha Observatory was established in 1999."),
            ],
        ):
            with self.subTest(pages=len(pages)):
                receipt = self.receipt(cells, pages)
                self.assertEqual(receipt["projection_single_source_group_count"], 1)
                self.assertEqual(receipt["projection_two_or_more_source_group_count"], 0)
                self.assertEqual(receipt["catalog_eligible_support_set_count"], 0)
                self.assertEqual(
                    receipt["unconflicted_projection_backed_unknown_proposal_count"],
                    0,
                )

    def test_conflicting_projection_values_abstain_after_one_supported_value(self) -> None:
        cells = [cell("Alpha Observatory")]
        pages = [
            page("one.example", "Alpha Observatory was founded in 1999."),
            page("two.example.net", "Alpha Observatory was established in 1999."),
            page("three.example.edu", "Alpha Observatory was founded in 2001."),
        ]
        receipt = self.receipt(cells, pages)
        self.assertEqual(receipt["distinct_target_value_projection_count"], 2)
        self.assertEqual(receipt["projection_single_source_group_count"], 1)
        self.assertEqual(receipt["projection_two_or_more_source_group_count"], 1)
        self.assertEqual(receipt["projection_conflicting_target_binding_count"], 1)
        self.assertEqual(receipt["projection_backed_eligible_support_set_count"], 1)
        self.assertEqual(
            receipt["unconflicted_projection_backed_unknown_proposal_count"], 0
        )

    def test_nonunknown_target_never_counts_as_unknown_proposal(self) -> None:
        cells = [cell("Alpha Observatory", old="1998")]
        pages = [
            page("one.example", "Alpha Observatory was founded in 1999."),
            page("two.example.net", "Alpha Observatory was founded in 1999."),
            page("three.example.edu", "Alpha Observatory was founded in 1999."),
        ]
        receipt = self.receipt(cells, pages)
        self.assertEqual(receipt["baseline_unknown_target_count"], 0)
        self.assertEqual(receipt["catalog_eligible_support_set_count"], 1)
        self.assertEqual(receipt["projection_backed_eligible_support_set_count"], 0)
        self.assertEqual(
            receipt["unconflicted_projection_backed_unknown_proposal_count"], 0
        )

    def test_mixed_pages_and_targets_preserve_exact_denominators(self) -> None:
        cells = [
            cell("Alpha Observatory"),
            cell("Beta Laboratory", "Country"),
        ]
        core = [
            page(
                "one.example",
                "Alpha Observatory was founded in 1999. Beta Laboratory is located in Canada.",
            )
        ]
        reserve = [
            page(
                "two.example.net",
                "Alpha Observatory was established in 1999. Beta Laboratory is based in Canada.",
            )
        ]
        receipt = self.receipt(cells, core, reserve)
        self.assertEqual(receipt["target_count"], 2)
        self.assertEqual(receipt["core_page_count"], 1)
        self.assertEqual(receipt["reserve_page_count"], 1)
        self.assertEqual(receipt["input_page_count"], 2)
        self.assertEqual(receipt["page_target_pair_count"], 4)
        self.assertEqual(sum(receipt["reason_counts"].values()), 4)
        self.assertEqual(receipt["projection_two_or_more_source_group_count"], 2)
        self.assertEqual(
            receipt["unconflicted_projection_backed_unknown_proposal_count"], 2
        )

    def test_receipt_contains_counts_only_and_no_input_literals(self) -> None:
        cells = [cell("Unique Private Entity Zeta")]
        pages = [
            page(
                "private-source.example",
                "Unique Private Entity Zeta was founded in 1987.",
            )
        ]
        receipt = self.receipt(cells, pages)
        encoded = json.dumps(receipt, ensure_ascii=False).casefold()
        for literal in (
            "unique private entity zeta",
            "private-source.example",
            "1987",
        ):
            self.assertNotIn(literal, encoded)
        self.assertTrue(
            receipt[
                "counts_only_no_task_question_identity_field_value_query_url_host_page_prediction_or_private_content_hash"
            ]
        )
        self.assertFalse(receipt["positive_entropy_or_task_credit_assigned"])

    def test_resealed_count_partition_or_authority_tamper_fails(self) -> None:
        receipt = self.receipt(
            [cell("Alpha Observatory")],
            [page("one.example", "Alpha Observatory was founded in 1999.")],
        )
        mutations = (
            lambda value: value.__setitem__("semantic_projection_count", 0),
            lambda value: value["reason_counts"].__setitem__(
                "projection_emitted", 0
            ),
            lambda value: value.__setitem__(
                "benchmark_launch_or_evaluator_authorized", True
            ),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                altered = copy.deepcopy(receipt)
                mutate(altered)
                altered.pop("receipt_sha256")
                altered["receipt_sha256"] = target.payload_sha256(altered)
                with self.assertRaises(ValueError):
                    target.validate_receipt(altered)

    def test_module_has_no_external_or_privileged_capability(self) -> None:
        tree = ast.parse(Path(target.__file__).read_text(encoding="utf-8"))
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
                {"os", "pathlib", "requests", "socket", "subprocess", "httpx"}
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
