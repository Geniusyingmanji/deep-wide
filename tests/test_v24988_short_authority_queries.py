from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v24988_short_authority_queries as target  # noqa: E402


QUESTION = (
    "Use web search and the official IANA Root Zone Database public page to "
    "return one table for <DOMAIN>.ad</DOMAIN>. "
    "Column names: Domain, Type, TLD Manager. Preserve exact spelling."
)


class ShortAuthorityQueryTests(unittest.TestCase):
    def test_builds_four_short_complementary_queries(self) -> None:
        value = target.build_short_queries(QUESTION, ["one very long planner query"])
        receipt = value["content_free_receipt"]
        self.assertTrue(receipt["strategy_applied"])
        self.assertEqual(receipt["output_query_count"], 4)
        self.assertEqual(len(set(value["queries"])), 4)
        self.assertTrue(all(len(query) <= target.QUERY_CHARACTER_CAP for query in value["queries"]))
        self.assertTrue(all(".ad" in query for query in value["queries"][:2]))
        self.assertTrue(any("Type" in query and "TLD Manager" in query for query in value["queries"]))
        self.assertTrue(any("official list" in query for query in value["queries"]))

    def test_missing_explicit_facets_fails_closed_to_planner_queries(self) -> None:
        planner = ["one", "two"]
        value = target.build_short_queries(
            "Return a table. Column names: Name, Value.", planner
        )
        self.assertFalse(value["content_free_receipt"]["strategy_applied"])
        self.assertEqual(value["queries"], planner)

    def test_fallback_preserves_parent_query_character_envelope(self) -> None:
        query = "q" * target.PROVIDER_QUERY_CHARACTER_CAP
        value = target.build_short_queries(
            "Return a table. Column names: Name, Value.", [query]
        )
        self.assertFalse(value["content_free_receipt"]["strategy_applied"])
        self.assertEqual(value["queries"], [query])
        self.assertEqual(
            value["content_free_receipt"]["maximum_output_query_characters"],
            target.PROVIDER_QUERY_CHARACTER_CAP,
        )

    def test_provider_count_matches_parent_normalization(self) -> None:
        planner = ["  .query ;  ", ".query ;", 7, 7, ""]
        value = target.build_short_queries(
            "Return a table. Column names: Name, Value.", planner
        )
        self.assertEqual(value["queries"], [".query ;", "7"])
        self.assertEqual(
            value["content_free_receipt"]["provider_unique_query_count"], 2
        )

    def test_absent_provider_query_vector_cannot_activate_strategy(self) -> None:
        value = target.build_short_queries(
            QUESTION, [], provider_query_vector_valid=False
        )
        receipt = value["content_free_receipt"]
        self.assertFalse(receipt["provider_query_vector_valid"])
        self.assertFalse(receipt["strategy_applied"])
        self.assertEqual(value["queries"], [])

    def test_empty_provider_query_vector_cannot_activate_strategy(self) -> None:
        value = target.build_short_queries(QUESTION, [])
        receipt = value["content_free_receipt"]
        self.assertTrue(receipt["provider_query_vector_valid"])
        self.assertEqual(receipt["provider_unique_query_count"], 0)
        self.assertFalse(receipt["strategy_applied"])
        self.assertEqual(value["queries"], [])

    def test_receipt_is_content_free_and_credit_zero(self) -> None:
        value = target.build_short_queries(QUESTION, ["planner"])
        encoded = json.dumps(value["content_free_receipt"], ensure_ascii=False)
        for forbidden in (".ad", "IANA", "Domain", "Type", "TLD Manager", "planner"):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["content_free_receipt"]["entropy_or_information_gain_assigns_signed_credit"]
        )

    def test_replay_and_tamper_fail_closed(self) -> None:
        value = target.build_short_queries(QUESTION, ["planner"])
        self.assertEqual(
            target.validate_result(value, question=QUESTION, planner_queries=["planner"]),
            value,
        )
        tampered = copy.deepcopy(value)
        tampered["queries"][0] = "changed"
        with self.assertRaises(ValueError):
            target.validate_result(
                tampered, question=QUESTION, planner_queries=["planner"]
            )

    def test_module_has_no_io_or_privileged_import(self) -> None:
        tree = ast.parse((ROOT / "src/deepwide_agent/v24988_short_authority_queries.py").read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in ("os", "pathlib", "subprocess", "requests", "deepwidebench"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for name in imports))


if __name__ == "__main__":
    unittest.main()
