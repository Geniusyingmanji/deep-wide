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

from deepwide_agent import v25491_visible_row_key_detail_selection as target  # noqa: E402


COLUMNS = ("Package", "Version", "Status")
BASE = (
    "```markdown\n"
    "| Package | Version | Status |\n"
    "| --- | --- | --- |\n"
    "| alpha | 1.0 | Unknown |\n"
    "```"
)


def batches(*links: dict[str, str], base: str = "https://registry.example/packages/"):
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


class V25491VisibleRowKeyDetailSelectionTests(unittest.TestCase):
    def test_unique_same_origin_path_and_anchor_binding_selects_one_link(self) -> None:
        fetched = batches(
            {"url": "alpha/metadata", "text": "alpha package metadata"},
            {"url": "unrelated", "text": "other record"},
        )
        value = target.build_selection(
            BASE, columns=COLUMNS, fetch_batches=fetched
        )
        self.assertEqual(
            value["requests"],
            [
                {
                    "url": "https://registry.example/packages/alpha/metadata",
                    "query": target.REQUEST_QUERY,
                    "title": "alpha",
                    "member_label": "alpha",
                }
            ],
        )
        self.assertEqual(value["content_free_receipt"]["logical_request_count"], 1)
        self.assertEqual(
            target.validate_selection(
                value,
                base_prediction=BASE,
                columns=COLUMNS,
                fetch_batches=fetched,
            ),
            value,
        )

    def test_anchor_path_cross_origin_and_already_fetched_mismatches_fail_closed(self) -> None:
        fixtures = {
            "anchor": batches({"url": "alpha/metadata", "text": "beta"}),
            "path": batches({"url": "beta/metadata", "text": "alpha"}),
            "origin": batches(
                {"url": "https://other.example/packages/alpha", "text": "alpha"}
            ),
            "already_fetched": [
                {
                    "results": [
                        {
                            "url": "https://registry.example/packages/alpha/metadata",
                            "requested_url": "https://registry.example/packages/",
                            "fetch_url": "https://registry.example/packages/",
                            "page_links": [
                                {"url": "alpha/metadata", "text": "alpha"}
                            ],
                        }
                    ]
                }
            ],
        }
        for name, fetched in fixtures.items():
            with self.subTest(name=name):
                value = target.build_selection(
                    BASE, columns=COLUMNS, fetch_batches=fetched
                )
                self.assertEqual(value["requests"], [])

    def test_two_urls_for_one_row_or_two_global_rows_are_ambiguous(self) -> None:
        same_row = batches(
            {"url": "alpha/metadata", "text": "alpha"},
            {"url": "alpha/details", "text": "alpha"},
        )
        value = target.build_selection(BASE, columns=COLUMNS, fetch_batches=same_row)
        self.assertEqual(value["requests"], [])
        self.assertEqual(value["content_free_receipt"]["ambiguous_row_link_count"], 2)

        two_row_base = BASE.replace(
            "| alpha | 1.0 | Unknown |",
            "| alpha | 1.0 | Unknown |\n| beta | 1.0 | Unknown |",
        )
        two_rows = batches(
            {"url": "alpha/metadata", "text": "alpha"},
            {"url": "beta/metadata", "text": "beta"},
        )
        value = target.build_selection(
            two_row_base, columns=COLUMNS, fetch_batches=two_rows
        )
        self.assertEqual(value["requests"], [])
        self.assertEqual(
            value["content_free_receipt"]["global_multi_candidate_handoff_count"],
            1,
        )

    def test_duplicate_occurrence_of_same_url_is_deduplicated_without_ranking(self) -> None:
        fetched = batches(
            {"url": "alpha/metadata", "text": "alpha"},
            {"url": "alpha/metadata", "text": "alpha package"},
        )
        value = target.build_selection(BASE, columns=COLUMNS, fetch_batches=fetched)
        self.assertEqual(len(value["requests"]), 1)
        self.assertEqual(
            value["content_free_receipt"]["duplicate_valid_occurrence_count"], 1
        )

    def test_private_invalid_or_non_child_links_are_rejected(self) -> None:
        fetched = batches(
            {"url": "http://127.0.0.1/alpha", "text": "alpha"},
            {"url": "javascript:alert(1)", "text": "alpha"},
            {"url": "../alpha", "text": "alpha"},
        )
        value = target.build_selection(BASE, columns=COLUMNS, fetch_batches=fetched)
        self.assertEqual(value["requests"], [])
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["rejected_private_or_credential_link_count"], 1)
        self.assertEqual(receipt["rejected_invalid_or_non_http_link_count"], 1)

    def test_receipt_or_candidate_tamper_fails(self) -> None:
        fetched = batches({"url": "alpha/metadata", "text": "alpha"})
        value = target.build_selection(BASE, columns=COLUMNS, fetch_batches=fetched)
        for kind in ("candidate", "credit"):
            changed = copy.deepcopy(value)
            if kind == "candidate":
                changed["private_candidates"][0]["row_identity"] = "beta"
            else:
                changed["content_free_receipt"]["positive_signed_credit_count"] = 1
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_selection(changed)

    def test_pure_module_is_label_blind_and_has_no_external_capability(self) -> None:
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
