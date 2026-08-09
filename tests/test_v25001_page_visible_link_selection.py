from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25001_page_visible_link_selection as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Use web search and the official Acme Public Registry public page to "
    "return one table for <ENTITY>Alpha</ENTITY>. "
    "Column names: Entity, Value."
)


def source(url: str) -> dict[str, str]:
    return {"url": url, "fetch_url": url, "title": "search citation"}


def second_wave() -> list[dict[str, object]]:
    return [
        {
            "query": "same completed query",
            "answer": "discarded",
            "results": [source("https://search.example/kept")],
            "error": None,
            "provider": "synthetic",
        }
    ]


def first_wave_pages() -> list[dict[str, object]]:
    return [
        {
            "query": "first",
            "answer": "",
            "results": [
                {
                    "requested_url": "https://index.example/catalog/",
                    "url": "https://index.example/catalog/",
                    "raw_content": "body text must not rank any link",
                    "page_links": [
                        {"url": "noise-one", "text": "Noise one"},
                        {"url": "../noise-two", "text": "Noise two"},
                        {
                            "url": "https://registry.acme.example/records/alpha.html",
                            "text": "Alpha official record",
                        },
                        {"url": "../noise-two#duplicate", "text": "duplicate"},
                        {"url": "https://user:secret@example.org/private", "text": "bad"},
                        {"url": "http://127.0.0.1/admin", "text": "bad"},
                        {"url": "http://localhost/admin", "text": "bad"},
                        {"url": "mailto:alpha@example.org", "text": "bad"},
                        {"url": "", "text": "bad"},
                    ],
                }
            ],
            "error": None,
            "provider": "synthetic-fetch",
        },
        {
            "query": "first-duplicate",
            "answer": "",
            "results": [
                {
                    "requested_url": "https://index.example/catalog/",
                    "url": "https://index.example/catalog/",
                    "raw_content": "a different body also must not rank links",
                    "page_links": [
                        {"url": "../noise-two", "text": "duplicate elsewhere"},
                        {"url": "/catalog/", "text": "source page itself"},
                    ],
                }
            ],
            "error": None,
            "provider": "synthetic-fetch",
        },
    ]


class PageVisibleLinkSelectionTests(unittest.TestCase):
    def select(self, pages=None, raw=None):
        return target.select_page_visible_link_prefixes(
            first_wave_pages() if pages is None else pages,
            second_wave() if raw is None else raw,
            question=QUESTION,
            cap=3,
        )

    def test_relative_resolution_dedup_private_rejection_and_bound_gain(self) -> None:
        value = self.select()
        receipt = value["content_free_receipt"]
        self.assertEqual(
            [item["url"] for item in value["shared_search_prefix"]],
            ["https://search.example/kept"],
        )
        self.assertEqual(
            [item["url"] for item in value["control_visible_links"]],
            [
                "https://index.example/catalog/noise-one",
                "https://index.example/noise-two",
            ],
        )
        self.assertEqual(
            [item["url"] for item in value["candidate_visible_links"]],
            [
                "https://registry.acme.example/records/alpha.html",
                "https://index.example/catalog/noise-one",
            ],
        )
        self.assertEqual(receipt["bound_visible_link_gain"], 1)
        self.assertEqual(receipt["selection_changed"], 1)
        self.assertEqual(receipt["control_total_selected_url_count"], 3)
        self.assertEqual(receipt["candidate_total_selected_url_count"], 3)
        self.assertEqual(receipt["rejected_private_or_credential_link_count"], 3)
        self.assertEqual(receipt["rejected_invalid_or_non_http_link_count"], 2)
        self.assertNotIn(
            "https://index.example/catalog/",
            {item["url"] for item in value["control"] + value["candidate"]},
        )

    def test_completed_search_prefix_and_original_pages_cannot_be_displaced(self) -> None:
        raw = second_wave()
        raw[0]["results"] = [
            source("https://search.example/one"),
            source("https://search.example/two"),
            source("https://search.example/three"),
        ]
        value = self.select(raw=raw)
        self.assertEqual(value["control"], value["candidate"])
        self.assertEqual(value["control_visible_links"], [])
        self.assertEqual(
            [item["url"] for item in value["control"]],
            [
                "https://search.example/one",
                "https://search.example/two",
                "https://search.example/three",
            ],
        )
        self.assertFalse(value["content_free_receipt"]["mechanism_engaged"])

    def test_page_body_title_and_anchor_text_do_not_change_url_ranking(self) -> None:
        pages = first_wave_pages()
        reference = self.select(pages=pages)
        changed = copy.deepcopy(pages)
        for batch in changed:
            for page in batch["results"]:
                page["raw_content"] = (
                    "Alpha Acme registry " * 500
                    + "https://registry.acme.example/records/alpha.html"
                )
                page["title"] = "Alpha Acme authority"
                for link in page["page_links"]:
                    link["text"] = "Alpha Acme authority" * 10
        observed = self.select(pages=changed)
        self.assertEqual(
            [item["url"] for item in reference["control"]],
            [item["url"] for item in observed["control"]],
        )
        self.assertEqual(
            [item["url"] for item in reference["candidate"]],
            [item["url"] for item in observed["candidate"]],
        )

    def test_no_strict_bound_gain_is_exact_identity_handoff(self) -> None:
        pages = first_wave_pages()
        pages[0]["results"][0]["page_links"] = [
            {
                "url": "https://registry.acme.example/records/alpha.html",
                "text": "already first",
            },
            {"url": "noise", "text": "noise"},
        ]
        pages[1]["results"][0]["page_links"] = []
        value = self.select(pages=pages)
        self.assertEqual(value["control"], value["candidate"])
        self.assertEqual(value["content_free_receipt"]["bound_visible_link_gain"], 0)
        self.assertFalse(value["content_free_receipt"]["mechanism_engaged"])

    def test_links_without_valid_attesting_page_url_are_rejected(self) -> None:
        pages = first_wave_pages()
        page = pages[0]["results"][0]
        page["requested_url"] = ""
        page["url"] = ""
        page["fetch_url"] = ""
        pages[1]["results"][0]["page_links"] = []
        value = self.select(pages=pages)
        receipt = value["content_free_receipt"]
        self.assertEqual(value["control_visible_links"], [])
        self.assertEqual(value["candidate_visible_links"], [])
        self.assertEqual(
            receipt["rejected_invalid_or_non_http_link_count"],
            receipt["raw_page_visible_link_count"],
        )

    def test_receipt_is_content_free_credit_zero_and_replay_bound(self) -> None:
        value = self.select()
        receipt_text = str(value["content_free_receipt"])
        for forbidden in ("Alpha", "Acme", "registry.acme.example", "noise-two"):
            self.assertNotIn(forbidden, receipt_text)
        self.assertFalse(
            value["content_free_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        self.assertEqual(
            target.validate_result(
                value,
                first_wave_page_batches=first_wave_pages(),
                second_wave_raw=second_wave(),
                question=QUESTION,
                cap=3,
            ),
            value,
        )
        tampered = copy.deepcopy(value)
        tampered["candidate_visible_links"][0]["url"] = "https://changed.example/"
        with self.assertRaises(ValueError):
            target.validate_result(
                tampered,
                first_wave_page_batches=first_wave_pages(),
                second_wave_raw=second_wave(),
                question=QUESTION,
                cap=3,
            )

        resealed = copy.deepcopy(value["content_free_receipt"])
        resealed["candidate_bound_visible_link_count"] = 0
        resealed.pop("receipt_payload_sha256")
        resealed["receipt_payload_sha256"] = payload_sha256(resealed)
        with self.assertRaises(ValueError):
            target.validate_receipt(resealed)

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25001_page_visible_link_selection.py"
        source_text = path.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "socket",
            "subprocess",
            "requests",
            "deepwidebench",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden in (
            "answer_key",
            "benchmark_question_type",
            "results.csv",
            "ground_truth",
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
