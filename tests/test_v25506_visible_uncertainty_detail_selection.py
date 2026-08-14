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

from deepwide_agent import v25506_visible_uncertainty_detail_selection as target  # noqa: E402


COLUMNS = ("Package", "Version", "Status")
BASE = (
    "```markdown\n"
    "| Package | Version | Status |\n"
    "| --- | --- | --- |\n"
    "| alpha | 1.0 | Unknown |\n"
    "| beta | Unknown | Unknown |\n"
    "```"
)


def batches(*links: dict[str, str]):
    base = "https://registry.example/packages/"
    return [
        {
            "results": [
                {
                    "url": base,
                    "requested_url": base,
                    "fetch_url": base,
                    "title": "Package index",
                    "raw_content": "visible index",
                    "page_links": list(links),
                }
            ]
        }
    ]


class V25506VisibleUncertaintyDetailSelectionTests(unittest.TestCase):
    def test_multiple_rows_selects_highest_visible_unknown_count(self) -> None:
        fetched = batches(
            {"url": "alpha/metadata", "text": "alpha package metadata"},
            {"url": "beta/metadata", "text": "beta package metadata"},
        )
        value = target.build_selection(BASE, columns=COLUMNS, fetch_batches=fetched)
        self.assertEqual(
            value["requests"],
            [
                {
                    "url": "https://registry.example/packages/beta/metadata",
                    "query": target.REQUEST_QUERY,
                    "title": "beta",
                    "member_label": "beta",
                }
            ],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["candidate_row_count"], 2)
        self.assertEqual(receipt["candidate_unknown_cell_count_total"], 3)
        self.assertEqual(receipt["maximum_unknown_cell_count"], 2)
        self.assertEqual(receipt["logical_request_count"], 1)
        self.assertEqual(
            target.validate_selection(
                value,
                base_prediction=BASE,
                columns=COLUMNS,
                fetch_batches=fetched,
            ),
            value,
        )

    def test_equal_priority_uses_stable_parent_table_order(self) -> None:
        equal = BASE.replace("| beta | Unknown | Unknown |", "| beta | 1.0 | Unknown |")
        fetched = batches(
            {"url": "beta/metadata", "text": "beta"},
            {"url": "alpha/metadata", "text": "alpha"},
        )
        value = target.build_selection(equal, columns=COLUMNS, fetch_batches=fetched)
        self.assertEqual(value["requests"][0]["title"], "alpha")
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["maximum_unknown_tie_count"], 2)
        self.assertEqual(receipt["stable_row_order_tiebreak_count"], 1)

    def test_no_visible_unknown_yields_no_request(self) -> None:
        complete = BASE.replace("Unknown", "Stable")
        fetched = batches(
            {"url": "alpha/metadata", "text": "alpha"},
            {"url": "beta/metadata", "text": "beta"},
        )
        value = target.build_selection(
            complete, columns=COLUMNS, fetch_batches=fetched
        )
        self.assertEqual(value["requests"], [])
        self.assertEqual(
            value["content_free_receipt"]["positive_uncertainty_candidate_count"],
            0,
        )

    def test_parent_per_row_ambiguity_and_identity_rules_remain_fail_closed(self) -> None:
        fetched = batches(
            {"url": "alpha/metadata", "text": "alpha"},
            {"url": "alpha/details", "text": "alpha"},
            {"url": "beta/metadata", "text": "other record"},
        )
        value = target.build_selection(BASE, columns=COLUMNS, fetch_batches=fetched)
        self.assertEqual(value["requests"], [])
        self.assertEqual(value["private_candidates"], [])

    def test_tamper_of_priority_candidate_or_credit_fails(self) -> None:
        fetched = batches(
            {"url": "alpha/metadata", "text": "alpha"},
            {"url": "beta/metadata", "text": "beta"},
        )
        value = target.build_selection(BASE, columns=COLUMNS, fetch_batches=fetched)
        for kind in ("priority", "candidate", "credit"):
            changed = copy.deepcopy(value)
            if kind == "priority":
                changed["requests"][0]["title"] = "alpha"
                changed["requests"][0]["member_label"] = "alpha"
            elif kind == "candidate":
                changed["private_candidates"][0]["unknown_cell_count"] = 0
            else:
                changed["content_free_receipt"]["positive_signed_credit_count"] = 1
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_selection(changed)

    def test_pure_module_is_label_blind_and_has_no_external_capability(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(
            contract["scheduling_signal"], "visible_unknown_nonkey_cell_count"
        )
        self.assertFalse(
            contract[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden = {
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
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        self.assertFalse(
            any(
                name == bad or name.startswith(bad + ".")
                for bad in ("os", "pathlib", "subprocess", "socket", "requests", "httpx")
                for name in imports
            )
        )
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)


if __name__ == "__main__":
    unittest.main()
