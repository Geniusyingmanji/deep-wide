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

from deepwide_agent import v25026_resolved_schema_reachability as target  # noqa: E402


QUESTION = (
    "Identify the jurisdiction whose capital is Example City. Return a table. "
    "Column names: Domain, Type, TLD Manager."
)


def traces(candidate_page: bool = True):
    queries = {
        target.SHARED_PHASE: ["capital Example City currency", "jurisdiction clue"],
        target.CONTROL_ARM: ["root database country code", "official TLD list"],
        target.CANDIDATE_ARM: [
            "Exampleland country code domain",
            "Exampleland Domain Type TLD Manager",
        ],
    }
    pages = {
        target.SHARED_PHASE: [
            {
                "title": "Exampleland profile",
                "url": "https://public.example/profile",
                "content": "Exampleland has capital Example City.",
            }
        ],
        target.CONTROL_ARM: [
            {
                "title": "Root database",
                "url": "https://authority.example/root",
                "content": "Domain Type TLD Manager generic index",
            }
        ],
        target.CANDIDATE_ARM: [
            {
                "title": "Exampleland domain delegation",
                "url": "https://authority.example/exampleland",
                "content": (
                    "Exampleland Domain delegation. Country-code top-level domain. "
                    "TLD Manager Example Registry."
                    if candidate_page
                    else "unrelated text"
                ),
            }
        ],
    }
    return queries, pages


class ResolvedSchemaReachabilityTests(unittest.TestCase):
    def test_supported_pivot_reaches_candidate_schema_page(self) -> None:
        queries, pages = traces()
        receipt = target.build_receipt(QUESTION, queries, pages)
        self.assertEqual(receipt["candidate_supported_novel_query_token_count"], 1)
        self.assertEqual(receipt["candidate_resolved_schema_page_count"], 1)
        self.assertEqual(receipt["control_resolved_schema_page_count"], 0)
        self.assertTrue(receipt["candidate_resolved_schema_page_strict_advantage"])

    def test_question_visible_token_is_not_a_resolved_pivot(self) -> None:
        queries, pages = traces()
        queries[target.CANDIDATE_ARM] = [
            "Example City country code domain",
            "Example City Domain Type TLD Manager",
        ]
        receipt = target.build_receipt(QUESTION, queries, pages)
        self.assertEqual(receipt["candidate_supported_novel_query_token_count"], 0)
        self.assertEqual(receipt["candidate_resolved_schema_page_count"], 0)

    def test_pivot_page_without_schema_is_not_bound(self) -> None:
        queries, pages = traces(candidate_page=False)
        pages[target.CANDIDATE_ARM][0]["content"] = "Exampleland unrelated text"
        receipt = target.build_receipt(QUESTION, queries, pages)
        self.assertEqual(receipt["candidate_pivot_supported_page_count"], 1)
        self.assertEqual(receipt["candidate_schema_bearing_page_count"], 0)
        self.assertEqual(receipt["candidate_resolved_schema_page_count"], 0)

    def test_missing_or_extra_phase_fails_closed(self) -> None:
        queries, pages = traces()
        del queries[target.CONTROL_ARM]
        with self.assertRaises(ValueError):
            target.build_receipt(QUESTION, queries, pages)

    def test_content_free_receipt_and_resealed_tamper_rejected(self) -> None:
        queries, pages = traces()
        receipt = target.build_receipt(QUESTION, queries, pages)
        serialized = json.dumps(receipt, sort_keys=True)
        for forbidden in ("Exampleland", "Example City", "authority.example"):
            self.assertNotIn(forbidden, serialized)
        changed = copy.deepcopy(receipt)
        changed["candidate_supported_novel_query_token_count"] = 0
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_receipt(changed)

    def test_module_has_no_effect_or_privileged_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25026_resolved_schema_reachability.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in ("os", "pathlib", "socket", "subprocess", "requests", "deepwidebench"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for name in imports))
        for forbidden in ("ground_truth", "answer_key", "results.csv"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
