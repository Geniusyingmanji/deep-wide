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

from deepwide_agent import v25010_attested_child_detail_selection as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Use web search and the official Acme Package Index public page to return "
    "one table for <PACKAGE>AlphaKit</PACKAGE>. "
    "Column names: Package, Version, Published, License."
)


def source(url: str) -> dict[str, str]:
    return {"url": url, "fetch_url": url, "title": "search citation"}


def second_wave(url: str = "https://search.example/kept") -> list[dict[str, object]]:
    return [
        {
            "query": "same completed query",
            "answer": "discarded",
            "results": [source(url)],
            "error": None,
            "provider": "synthetic",
        }
    ]


def page(
    url: str,
    links: list[dict[str, str]],
    *,
    title: str = "ignored title",
    body: str = "ignored body",
) -> dict[str, object]:
    return {
        "query": "first",
        "answer": "",
        "results": [
            {
                "requested_url": url,
                "fetch_url": url,
                "url": url,
                "title": title,
                "raw_content": body,
                "page_links": links,
            }
        ],
    }


def pages() -> list[dict[str, object]]:
    return [
        page(
            "https://packages.acme.example/web/packages/",
            [
                {"url": "noise-one/", "text": "noise one"},
                {"url": "noise-two/", "text": "noise two"},
                {
                    "url": "AlphaKit/index.html",
                    "text": "AlphaKit detail",
                },
                {
                    "url": "https://elsewhere.example/web/packages/AlphaKit/index.html",
                    "text": "cross origin",
                },
            ],
        )
    ]


class AttestedChildDetailSelectionTests(unittest.TestCase):
    def select(self, *, first=None, second=None, cap: int = 3, exclude=()):
        return target.select_attested_child_detail_prefixes(
            pages() if first is None else first,
            second_wave() if second is None else second,
            question=QUESTION,
            cap=cap,
            exclude_urls=exclude,
        )

    def test_promotes_only_same_origin_authority_attested_identity_child(self) -> None:
        value = self.select()
        control = [item["url"] for item in value["control"]]
        candidate = [item["url"] for item in value["candidate"]]
        detail = "https://packages.acme.example/web/packages/AlphaKit/index.html"
        self.assertNotIn(detail, control)
        self.assertIn(detail, candidate)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["authority_bound_attesting_page_count"], 1)
        self.assertEqual(receipt["same_origin_strict_child_link_count"], 3)
        self.assertEqual(receipt["exact_identity_child_link_count"], 1)
        self.assertEqual(receipt["attested_child_detail_link_count"], 1)
        self.assertEqual(receipt["attested_child_detail_link_gain"], 1)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_cross_origin_sibling_and_unbound_parent_do_not_attest(self) -> None:
        first = [
            page(
                "https://packages.acme.example/web/index.html",
                [
                    {
                        "url": "https://packages.acme.example/other/AlphaKit/index.html",
                        "text": "sibling",
                    },
                    {
                        "url": "https://elsewhere.example/web/AlphaKit/index.html",
                        "text": "cross origin",
                    },
                ],
            ),
            page(
                "https://unrelated.example/web/packages/",
                [{"url": "AlphaKit/index.html", "text": "unbound parent"}],
            ),
        ]
        value = self.select(first=first)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["attested_child_detail_link_count"], 0)
        self.assertEqual(value["control"], value["candidate"])
        self.assertFalse(receipt["strategy_eligible"])

    def test_file_index_uses_parent_directory_as_collection_prefix(self) -> None:
        first = [
            page(
                "https://packages.acme.example/web/packages/available.html",
                [
                    {"url": "AlphaKit/index.html", "text": "detail"},
                    {"url": "../outside/AlphaKit.html", "text": "outside"},
                ],
            )
        ]
        value = self.select(first=first, cap=2)
        self.assertEqual(
            value["content_free_receipt"]["attested_child_detail_link_count"], 1
        )
        self.assertIn(
            "https://packages.acme.example/web/packages/AlphaKit/index.html",
            [item["url"] for item in value["candidate"]],
        )

    def test_duplicate_late_valid_attestation_merges_without_reordering(self) -> None:
        child = "https://packages.acme.example/web/packages/AlphaKit/index.html"
        first = [
            page(
                "https://unrelated.example/catalog/",
                [{"url": child, "text": "first unbound occurrence"}],
            ),
            page(
                "https://packages.acme.example/web/packages/",
                [
                    {"url": "noise/", "text": "noise"},
                    {"url": child, "text": "later valid attestation"},
                ],
            ),
        ]
        value = self.select(first=first, cap=2)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["unique_visible_link_count_before_exclusion"], 2)
        self.assertEqual(receipt["attested_child_detail_link_count"], 1)
        self.assertEqual(value["candidate"][1]["url"], child)

    def test_shared_search_prefix_and_original_pages_are_never_reselected(self) -> None:
        detail = "https://packages.acme.example/web/packages/AlphaKit/index.html"
        first = pages()
        first[0]["results"][0]["page_links"].append(
            {"url": "https://packages.acme.example/web/packages/", "text": "self"}
        )
        value = self.select(first=first, second=second_wave(detail))
        self.assertEqual(value["control"][0]["url"], detail)
        self.assertEqual(value["candidate"][0]["url"], detail)
        self.assertEqual(
            sum(item["url"] == detail for item in value["candidate"]), 1
        )
        self.assertNotIn(
            "https://packages.acme.example/web/packages/",
            [item["url"] for item in value["control_visible_links"]],
        )

    def test_body_title_and_anchor_text_cannot_change_ranking(self) -> None:
        reference = self.select()
        changed = copy.deepcopy(pages())
        changed[0]["results"][0]["title"] = "AlphaKit Acme " * 100
        changed[0]["results"][0]["raw_content"] = "AlphaKit Acme " * 1000
        for link in changed[0]["results"][0]["page_links"]:
            link["text"] = "AlphaKit official Acme detail " * 100
        observed = self.select(first=changed)
        self.assertEqual(reference["control"], observed["control"])
        self.assertEqual(reference["candidate"], observed["candidate"])

    def test_full_prefix_or_no_strict_gain_is_exact_handoff(self) -> None:
        full = second_wave()
        full[0]["results"] = [
            source("https://search.example/one"),
            source("https://search.example/two"),
            source("https://search.example/three"),
        ]
        value = self.select(second=full)
        self.assertEqual(value["control"], value["candidate"])
        self.assertEqual(value["control_visible_links"], [])

        already_first = pages()
        already_first[0]["results"][0]["page_links"] = [
            {"url": "AlphaKit/index.html", "text": "already first"},
            {"url": "noise/", "text": "noise"},
        ]
        handoff = self.select(first=already_first)
        self.assertEqual(handoff["control"], handoff["candidate"])
        self.assertEqual(
            handoff["content_free_receipt"]["attested_child_detail_link_gain"], 0
        )

    def test_receipt_is_content_free_credit_zero_and_replay_bound(self) -> None:
        value = self.select()
        receipt_text = str(value["content_free_receipt"])
        for forbidden in ("AlphaKit", "Acme", "packages.acme.example", "https://"):
            self.assertNotIn(forbidden, receipt_text)
        self.assertFalse(
            value["content_free_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        self.assertEqual(
            target.validate_result(
                value,
                first_wave_page_batches=pages(),
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
                first_wave_page_batches=pages(),
                second_wave_raw=second_wave(),
                question=QUESTION,
                cap=3,
            )
        resealed = copy.deepcopy(value["content_free_receipt"])
        resealed["candidate_attested_child_detail_link_count"] = 0
        resealed["attested_child_detail_link_gain"] = 0
        resealed.pop("receipt_payload_sha256")
        resealed["receipt_payload_sha256"] = payload_sha256(resealed)
        with self.assertRaises(ValueError):
            target.validate_receipt(resealed)

    def test_private_invalid_and_missing_attester_are_rejected(self) -> None:
        first = pages()
        links = first[0]["results"][0]["page_links"]
        links.extend(
            [
                {"url": "http://127.0.0.1/AlphaKit", "text": "private"},
                {"url": "https://user:secret@example.org/AlphaKit", "text": "credential"},
                {"url": "javascript:alert(1)", "text": "invalid"},
                {"url": "http://[bad", "text": "invalid"},
            ]
        )
        first.append(
            {
                "query": "missing",
                "results": [
                    {
                        "requested_url": "",
                        "url": "",
                        "fetch_url": "",
                        "page_links": [{"url": "AlphaKit", "text": "no base"}],
                    }
                ],
            }
        )
        receipt = self.select(first=first)["content_free_receipt"]
        self.assertEqual(receipt["rejected_private_or_credential_link_count"], 2)
        self.assertEqual(receipt["rejected_invalid_or_non_http_link_count"], 3)

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25010_attested_child_detail_selection.py"
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
