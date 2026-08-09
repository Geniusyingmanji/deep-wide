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

from deepwide_agent import v25015_distinct_identity_child_selection as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = """Use web search and the official Acme Package Index public page to return one Markdown table.
<PACKAGES>
1. AlphaKit
2. BetaCore
3. GammaTools
4. DeltaLib
</PACKAGES>
Column names: Package, Version, Published, License. Return one table only."""


def source(url: str) -> dict[str, str]:
    return {"url": url, "fetch_url": url, "title": "ignored search citation"}


def second_wave(*urls: str) -> list[dict[str, object]]:
    values = urls or ("https://search.example/kept",)
    return [
        {
            "query": "same completed query",
            "answer": "discarded",
            "results": [source(url) for url in values],
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
                {"url": "noise-one/", "text": "noise"},
                {"url": "AlphaKit/index.html", "text": "alpha first"},
                {"url": "AlphaKit/details.html", "text": "alpha duplicate"},
                {"url": "BetaCore/index.html", "text": "beta"},
                {"url": "GammaTools/index.html", "text": "gamma"},
                {"url": "DeltaLib/index.html", "text": "delta"},
            ],
        )
    ]


class DistinctIdentityChildSelectionTests(unittest.TestCase):
    def select(self, *, first=None, second=None, cap: int = 4, exclude=()):
        return target.select_distinct_identity_child_prefixes(
            pages() if first is None else first,
            second_wave() if second is None else second,
            question=QUESTION,
            cap=cap,
            exclude_urls=exclude,
        )

    def test_candidate_maximizes_distinct_identity_not_link_count(self) -> None:
        value = self.select(cap=3)
        control = [item["url"] for item in value["control_visible_links"]]
        candidate = [item["url"] for item in value["candidate_visible_links"]]
        self.assertEqual(
            control,
            [
                "https://packages.acme.example/web/packages/noise-one",
                "https://packages.acme.example/web/packages/AlphaKit/index.html",
            ],
        )
        self.assertEqual(
            candidate,
            [
                "https://packages.acme.example/web/packages/AlphaKit/index.html",
                "https://packages.acme.example/web/packages/BetaCore/index.html",
            ],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["control_new_distinct_identity_count"], 1)
        self.assertEqual(receipt["candidate_new_distinct_identity_count"], 2)
        self.assertEqual(receipt["new_distinct_identity_gain"], 1)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_search_prefix_identity_is_prior_coverage_and_not_reselected(self) -> None:
        alpha = "https://packages.acme.example/web/packages/AlphaKit/index.html"
        value = self.select(second=second_wave(alpha), cap=3)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["prior_covered_distinct_identity_count"], 1)
        candidate = [item["url"] for item in value["candidate_visible_links"]]
        self.assertEqual(
            candidate,
            [
                "https://packages.acme.example/web/packages/BetaCore/index.html",
                "https://packages.acme.example/web/packages/GammaTools/index.html",
            ],
        )
        self.assertEqual(sum(item["url"] == alpha for item in value["candidate"]), 1)
        self.assertEqual(receipt["candidate_new_distinct_identity_count"], 2)

    def test_duplicate_identity_links_cannot_crowd_out_another_identity(self) -> None:
        raw = pages()
        raw[0]["results"][0]["page_links"] = [
            {"url": "AlphaKit/one.html", "text": "a1"},
            {"url": "AlphaKit/two.html", "text": "a2"},
            {"url": "AlphaKit/three.html", "text": "a3"},
            {"url": "BetaCore/index.html", "text": "b"},
        ]
        value = self.select(first=raw, cap=3)
        self.assertEqual(
            [item["url"] for item in value["candidate_visible_links"]],
            [
                "https://packages.acme.example/web/packages/AlphaKit/one.html",
                "https://packages.acme.example/web/packages/BetaCore/index.html",
            ],
        )
        self.assertEqual(
            value["content_free_receipt"]["candidate_new_distinct_identity_count"],
            2,
        )

    def test_duplicate_url_can_gain_later_valid_attestation_without_reordering(self) -> None:
        beta = "https://packages.acme.example/web/packages/BetaCore/index.html"
        first = [
            page(
                "https://unrelated.example/catalog/",
                [{"url": beta, "text": "first unbound occurrence"}],
            ),
            page(
                "https://packages.acme.example/web/packages/",
                [
                    {"url": "noise/", "text": "noise"},
                    {"url": beta, "text": "later valid attestation"},
                ],
            ),
        ]
        value = self.select(first=first, cap=2)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["unique_visible_link_count_before_exclusion"], 2)
        self.assertEqual(receipt["attested_unique_identity_child_link_count"], 1)
        self.assertEqual(value["candidate_visible_links"][0]["url"], beta)

    def test_ambiguous_identity_url_receives_no_coverage_credit(self) -> None:
        question = QUESTION.replace(
            "1. AlphaKit\n2. BetaCore\n3. GammaTools\n4. DeltaLib",
            "1. Alpha\n2. Alpha Kit\n3. GammaTools\n4. DeltaLib",
        )
        first = [
            page(
                "https://packages.acme.example/web/packages/",
                [
                    {"url": "Alpha-Kit/index.html", "text": "ambiguous"},
                    {"url": "GammaTools/index.html", "text": "unique"},
                    {"url": "noise/", "text": "noise"},
                ],
            )
        ]
        value = target.select_distinct_identity_child_prefixes(
            first,
            second_wave(),
            question=question,
            cap=2,
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["ambiguous_identity_child_link_count"], 1)
        self.assertEqual(receipt["attested_unique_identity_child_link_count"], 1)
        self.assertIn(
            "https://packages.acme.example/web/packages/GammaTools/index.html",
            [item["url"] for item in value["candidate_visible_links"]],
        )

    def test_body_title_and_anchor_text_cannot_change_ranking(self) -> None:
        reference = self.select()
        changed = copy.deepcopy(pages())
        changed[0]["results"][0]["title"] = "AlphaKit Acme " * 100
        changed[0]["results"][0]["raw_content"] = "BetaCore " * 1000
        for link in changed[0]["results"][0]["page_links"]:
            link["text"] = "GammaTools official Acme " * 100
        observed = self.select(first=changed)
        self.assertEqual(reference["control"], observed["control"])
        self.assertEqual(reference["candidate"], observed["candidate"])

    def test_cross_origin_unbound_parent_private_and_invalid_links_do_not_promote(self) -> None:
        first = [
            page(
                "https://packages.acme.example/web/index.html",
                [
                    {"url": "https://elsewhere.example/web/BetaCore/", "text": "cross"},
                    {"url": "../other/GammaTools/", "text": "sibling"},
                    {"url": "http://127.0.0.1/DeltaLib", "text": "private"},
                    {"url": "javascript:alert(1)", "text": "invalid"},
                ],
            ),
            page(
                "https://unrelated.example/web/packages/",
                [{"url": "BetaCore/index.html", "text": "unbound"}],
            ),
        ]
        value = self.select(first=first)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["attested_unique_identity_child_link_count"], 0)
        self.assertEqual(value["control"], value["candidate"])
        self.assertFalse(receipt["strategy_eligible"])
        self.assertEqual(receipt["rejected_private_or_credential_link_count"], 1)
        self.assertEqual(receipt["rejected_invalid_or_non_http_link_count"], 1)

    def test_full_prefix_or_no_distinct_gain_is_exact_handoff(self) -> None:
        full = self.select(
            second=second_wave(
                "https://search.example/one",
                "https://search.example/two",
                "https://search.example/three",
            ),
            cap=3,
        )
        self.assertEqual(full["control"], full["candidate"])
        self.assertEqual(full["control_visible_links"], [])

        already_distinct = pages()
        already_distinct[0]["results"][0]["page_links"] = [
            {"url": "AlphaKit/index.html", "text": "a"},
            {"url": "BetaCore/index.html", "text": "b"},
        ]
        handoff = self.select(first=already_distinct, cap=3)
        self.assertEqual(handoff["control"], handoff["candidate"])
        self.assertEqual(
            handoff["content_free_receipt"]["new_distinct_identity_gain"], 0
        )

    def test_receipt_is_content_free_replay_bound_and_credit_zero(self) -> None:
        value = self.select()
        receipt_text = str(value["content_free_receipt"])
        for forbidden in (
            "AlphaKit",
            "BetaCore",
            "Acme",
            "packages.acme.example",
            "https://",
        ):
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
                cap=4,
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
                cap=4,
            )
        resealed = copy.deepcopy(value["content_free_receipt"])
        resealed["candidate_new_distinct_identity_count"] = 0
        resealed["new_distinct_identity_gain"] = 0
        resealed.pop("receipt_payload_sha256")
        resealed["receipt_payload_sha256"] = payload_sha256(resealed)
        with self.assertRaises(ValueError):
            target.validate_receipt(resealed)

    def test_single_identity_question_is_rejected_before_selection(self) -> None:
        single = QUESTION.replace(
            "<PACKAGES>\n1. AlphaKit\n2. BetaCore\n3. GammaTools\n4. DeltaLib\n</PACKAGES>",
            "<PACKAGE>AlphaKit</PACKAGE>",
        )
        with self.assertRaises(ValueError):
            target.select_distinct_identity_child_prefixes(
                pages(), second_wave(), question=single, cap=4
            )

        short_identity = QUESTION.replace("2. BetaCore", "2. R")
        with self.assertRaises(ValueError):
            target.select_distinct_identity_child_prefixes(
                pages(), second_wave(), question=short_identity, cap=4
            )

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25015_distinct_identity_child_selection.py"
        source = path.read_text(encoding="utf-8")
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
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
