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

from deepwide_agent import (  # noqa: E402
    v24998_identity_authority_action_selection as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Use web search and the official Acme Public Registry public page to "
    "return one table for <ENTITY>.ch</ENTITY>. Column names: Entity, Value."
)


def source(url: str, title: str = "") -> dict[str, str]:
    return {"type": "url", "title": title, "url": url, "fetch_url": url}


def batches() -> list[dict[str, object]]:
    return [
        {
            "query": "discarded query",
            "answer": "discarded narrative",
            "results": [source("https://local.example/first")],
            "error": None,
            "hosted_search_trace": {
                "actions": [
                    {
                        "sources": [
                            source("https://noise.example/a"),
                            source("https://example.org/unrelated"),
                            source("https://registry.acme.example/records/ch.html"),
                            source("https://example.org/records/champion.html"),
                            source("https://example.org/records/ch.html"),
                        ]
                    }
                ]
            },
        }
    ]


class IdentityAuthorityActionSelectionTests(unittest.TestCase):
    def test_promotes_only_jointly_bound_action_url_after_local_prefix(self) -> None:
        value = target.select_matched_prefixes(batches(), question=QUESTION, cap=3)
        control = [item["url"] for item in value["control"]]
        candidate = [item["url"] for item in value["candidate"]]
        self.assertEqual(control[0], "https://local.example/first")
        self.assertEqual(candidate[0], "https://local.example/first")
        self.assertNotIn("https://registry.acme.example/records/ch.html", control)
        self.assertIn("https://registry.acme.example/records/ch.html", candidate)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["identity_authority_bound_action_url_count"], 1)
        self.assertEqual(receipt["bound_action_url_gain"], 1)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_host_tld_identity_substring_and_authority_only_do_not_bind(self) -> None:
        self.assertFalse(
            target.identity_authority_bound(
                "https://unrelated.ch/registry/acme", question=QUESTION
            )
        )
        self.assertFalse(
            target.identity_authority_bound(
                "https://registry.acme.example/unrelated", question=QUESTION
            )
        )
        self.assertFalse(
            target.identity_authority_bound(
                "https://example.org/records/champion.html", question=QUESTION
            )
        )
        self.assertTrue(
            target.identity_authority_bound(
                "https://registry.acme.example/records/ch.html", question=QUESTION
            )
        )

    def test_query_local_citations_are_never_displaced(self) -> None:
        raw = batches()
        raw[0]["results"] = [
            source("https://local.example/one"),
            source("https://local.example/two"),
            source("https://local.example/three"),
        ]
        value = target.select_matched_prefixes(raw, question=QUESTION, cap=2)
        self.assertEqual(value["control"], value["candidate"])
        self.assertEqual(
            [item["url"] for item in value["candidate"]],
            ["https://local.example/one", "https://local.example/two"],
        )
        self.assertFalse(value["content_free_receipt"]["mechanism_engaged"])

    def test_prior_url_exclusion_precedes_matched_selection(self) -> None:
        value = target.select_matched_prefixes(
            batches(),
            question=QUESTION,
            cap=3,
            exclude_urls={"https://local.example/first"},
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["excluded_prior_url_count"], 1)
        self.assertEqual(len(value["control"]), len(value["candidate"]))
        self.assertNotIn(
            "https://local.example/first",
            {item["url"] for item in value["control"] + value["candidate"]},
        )

    def test_missing_visible_facets_is_identity_handoff(self) -> None:
        value = target.select_matched_prefixes(
            batches(), question="Return one table. Column names: A, B.", cap=3
        )
        self.assertEqual(value["control"], value["candidate"])
        receipt = value["content_free_receipt"]
        self.assertFalse(receipt["strategy_eligible"])
        self.assertFalse(receipt["mechanism_engaged"])

    def test_receipt_is_content_free_credit_zero_and_replay_bound(self) -> None:
        value = target.select_matched_prefixes(batches(), question=QUESTION, cap=3)
        receipt_text = str(value["content_free_receipt"])
        for forbidden in (".ch", "Acme", "registry.acme.example"):
            self.assertNotIn(forbidden, receipt_text)
        self.assertFalse(
            value["content_free_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        self.assertEqual(
            target.validate_result(value, raw=batches(), question=QUESTION, cap=3),
            value,
        )
        tampered = copy.deepcopy(value)
        tampered["candidate"][0]["url"] = "https://changed.example/"
        with self.assertRaises(ValueError):
            target.validate_result(tampered, raw=batches(), question=QUESTION, cap=3)

        resealed = copy.deepcopy(value["content_free_receipt"])
        resealed["candidate_bound_action_url_count"] = 0
        resealed["bound_action_url_gain"] = 0
        resealed.pop("receipt_payload_sha256")
        resealed["receipt_payload_sha256"] = payload_sha256(resealed)
        with self.assertRaises(ValueError):
            target.validate_receipt(resealed)

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v24998_identity_authority_action_selection.py"
        source_text = path.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in ("os", "pathlib", "subprocess", "requests", "deepwidebench"):
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
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
