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

from deepwide_agent import v24992_hybrid_authority_queries as target  # noqa: E402


QUESTION = (
    "Use web search and the official IANA Root Zone Database public page to "
    "return exactly one table for <DOMAIN>.bf</DOMAIN>. "
    "Column names: Domain, Type, TLD Manager. The Type and TLD Manager must "
    "come from the same official IANA table record."
)
ANCHOR = "Preserve the full provider semantic anchor exactly"


class HybridAuthorityQueryTests(unittest.TestCase):
    def test_preserves_anchor_and_selects_first_complete_authority(self) -> None:
        value = target.build_hybrid_queries(QUESTION, [f"  {ANCHOR}  "])
        receipt = value["content_free_receipt"]
        self.assertTrue(receipt["strategy_applied"])
        self.assertEqual(value["queries"][0], ANCHOR)
        self.assertEqual(len(value["queries"]), 4)
        self.assertTrue(any("IANA Root Zone Database" in row for row in value["queries"][1:]))
        self.assertFalse(any('"IANA table"' in row for row in value["queries"][1:]))
        self.assertEqual(receipt["selected_authority_ordinal"], 1)
        self.assertGreaterEqual(receipt["explicit_authority_phrase_count"], 2)

    def test_replaces_only_three_non_anchor_slots(self) -> None:
        value = target.build_hybrid_queries(
            QUESTION, [ANCHOR, "legacy two", "legacy three", "legacy four"]
        )
        self.assertEqual(value["queries"][0], ANCHOR)
        self.assertNotIn("legacy two", value["queries"])
        self.assertNotIn("legacy three", value["queries"])
        self.assertNotIn("legacy four", value["queries"])
        self.assertTrue(
            value["content_free_receipt"]["provider_anchor_preserved_in_first_slot"]
        )

    def test_duplicate_hybrid_fails_closed_to_provider_vector(self) -> None:
        duplicate_anchor = '".bf" "IANA Root Zone Database"'
        provider = [duplicate_anchor, "legacy second"]
        value = target.build_hybrid_queries(QUESTION, provider)
        self.assertFalse(value["content_free_receipt"]["strategy_applied"])
        self.assertEqual(value["queries"], provider)

    def test_missing_facets_or_invalid_vector_fails_closed(self) -> None:
        provider = [ANCHOR, "second"]
        missing = target.build_hybrid_queries(
            "Return a table. Column names: Name, Value.", provider
        )
        self.assertFalse(missing["content_free_receipt"]["strategy_applied"])
        self.assertEqual(missing["queries"], provider)
        invalid = target.build_hybrid_queries(
            QUESTION, [], provider_query_vector_valid=False
        )
        self.assertFalse(invalid["content_free_receipt"]["strategy_applied"])
        self.assertEqual(invalid["queries"], [])

    def test_receipt_is_content_free_and_credit_zero(self) -> None:
        value = target.build_hybrid_queries(QUESTION, [ANCHOR])
        encoded = json.dumps(value["content_free_receipt"], ensure_ascii=False)
        for forbidden in (
            ".bf", "IANA", "Domain", "Type", "TLD Manager", ANCHOR
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["content_free_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        self.assertFalse(
            value["content_free_receipt"]["benchmark_launch_or_evaluator_authorized"]
        )

    def test_replay_resealed_tamper_and_unknown_field_fail_closed(self) -> None:
        value = target.build_hybrid_queries(QUESTION, [ANCHOR])
        self.assertEqual(
            target.validate_result(
                value, question=QUESTION, provider_queries=[ANCHOR]
            ),
            value,
        )
        tampered = copy.deepcopy(value)
        tampered["queries"][0] = "changed"
        with self.assertRaises(ValueError):
            target.validate_result(
                tampered, question=QUESTION, provider_queries=[ANCHOR]
            )
        unknown = copy.deepcopy(value["content_free_receipt"])
        unknown["unexpected"] = 1
        unknown.pop("receipt_payload_sha256")
        from deepwide_agent.v24263_global_model_limiter import payload_sha256

        unknown["receipt_payload_sha256"] = payload_sha256(unknown)
        with self.assertRaises(ValueError):
            target.validate_receipt(unknown)

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v24992_hybrid_authority_queries.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os", "pathlib", "subprocess", "requests", "deepwidebench"
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )


if __name__ == "__main__":
    unittest.main()
