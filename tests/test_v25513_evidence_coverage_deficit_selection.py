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

from deepwide_agent import v25513_evidence_coverage_deficit_selection as target  # noqa: E402


COLUMNS = ("Package", "Version", "Status")
BASE = (
    "```markdown\n"
    "| Package | Version | Status |\n"
    "| --- | --- | --- |\n"
    "| alpha | 1.0 | Stable |\n"
    "| beta | 2.0 | Pending |\n"
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


def page(identity: str, content: str, *, suffix: str = "summary"):
    return {
        "url": f"https://registry.example/packages/{identity}/{suffix}",
        "title": f"{identity} package record",
        "content": f"{identity} package record\n{content}",
    }


LINKS = batches(
    {"url": "alpha/detail", "text": "alpha package metadata"},
    {"url": "beta/detail", "text": "beta package metadata"},
)


class V25513EvidenceCoverageDeficitSelectionTests(unittest.TestCase):
    def test_nonunknown_rows_schedule_larger_source_coverage_deficit(self) -> None:
        pages = [page("alpha", "Version: 1.0\nStatus: Stable")]
        value = target.build_selection(
            BASE, columns=COLUMNS, fetch_batches=LINKS, pages=pages
        )
        candidates = value["private_candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["row_identity"], "beta")
        self.assertEqual(candidates[0]["evidence_deficit_count"], 2)
        self.assertEqual(candidates[1]["row_identity"], "alpha")
        self.assertEqual(candidates[1]["covered_nonkey_cell_count"], 2)
        self.assertEqual(value["requests"][0]["title"], "beta")
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["coverage_probe_unique_coordinate_count"], 2)
        self.assertEqual(receipt["positive_evidence_deficit_candidate_count"], 1)
        self.assertEqual(
            target.validate_selection(
                value,
                base_prediction=BASE,
                columns=COLUMNS,
                fetch_batches=LINKS,
                pages=pages,
            ),
            value,
        )

    def test_equal_deficit_uses_stable_table_order_not_link_order(self) -> None:
        reverse = batches(
            {"url": "beta/detail", "text": "beta"},
            {"url": "alpha/detail", "text": "alpha"},
        )
        value = target.build_selection(
            BASE, columns=COLUMNS, fetch_batches=reverse, pages=[]
        )
        self.assertEqual(value["requests"][0]["title"], "alpha")
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["maximum_evidence_deficit_tie_count"], 2)
        self.assertEqual(receipt["stable_row_order_tiebreak_count"], 1)

    def test_complete_unique_coverage_yields_no_request(self) -> None:
        pages = [
            page("alpha", "Version: 1.0\nStatus: Stable"),
            page("beta", "Version: 2.0\nStatus: Pending"),
        ]
        value = target.build_selection(
            BASE, columns=COLUMNS, fetch_batches=LINKS, pages=pages
        )
        self.assertEqual(value["requests"], [])
        self.assertEqual(
            value["content_free_receipt"][
                "positive_evidence_deficit_candidate_count"
            ],
            0,
        )

    def test_ambiguous_same_coordinate_is_uncovered_not_voted(self) -> None:
        pages = [
            page("alpha", "Version: 1.0", suffix="summary-a"),
            page("alpha", "Version: 1.0", suffix="summary-b"),
        ]
        value = target.build_selection(
            BASE, columns=COLUMNS, fetch_batches=LINKS, pages=pages
        )
        alpha = next(
            item for item in value["private_candidates"]
            if item["row_identity"] == "alpha"
        )
        self.assertEqual(alpha["covered_nonkey_cell_count"], 0)
        self.assertEqual(alpha["evidence_deficit_count"], 2)

    def test_parent_per_row_link_ambiguity_remains_fail_closed(self) -> None:
        ambiguous = batches(
            {"url": "alpha/detail", "text": "alpha"},
            {"url": "alpha/other", "text": "alpha"},
            {"url": "beta/detail", "text": "other record"},
        )
        value = target.build_selection(
            BASE, columns=COLUMNS, fetch_batches=ambiguous, pages=[]
        )
        self.assertEqual(value["private_candidates"], [])
        self.assertEqual(value["requests"], [])

    def test_tamper_of_deficit_candidate_or_credit_fails(self) -> None:
        value = target.build_selection(
            BASE, columns=COLUMNS, fetch_batches=LINKS, pages=[]
        )
        for kind in ("deficit", "candidate", "credit"):
            changed = copy.deepcopy(value)
            if kind == "deficit":
                changed["private_candidates"][0]["evidence_deficit_count"] = 0
            elif kind == "candidate":
                changed["requests"][0]["title"] = "beta"
                changed["requests"][0]["member_label"] = "beta"
            else:
                changed["content_free_receipt"]["positive_signed_credit_count"] = 1
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_selection(changed)

    def test_pure_module_is_label_blind_and_has_no_external_capability(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(
            contract["scheduling_signal"],
            "row_local_missing_unique_source_bound_coordinate_count",
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
                for bad in (
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
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)


if __name__ == "__main__":
    unittest.main()
