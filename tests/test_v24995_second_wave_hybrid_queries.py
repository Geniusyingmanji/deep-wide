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

from deepwide_agent import v24995_second_wave_hybrid_queries as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Use web search and the official IANA Root Zone Database public page to "
    "return one table for <DOMAIN>.ch</DOMAIN>. "
    "Column names: Domain, Type, TLD Manager. The values must come from the "
    "same official IANA table record."
)
COMPLETED = [
    "long provider semantic anchor",
    "long provider semantic anchor official source",
    "long provider semantic anchor official list index",
    "long provider semantic anchor official database",
]


class SecondWaveHybridQueryTests(unittest.TestCase):
    def build(self, **kwargs):
        values = {
            "question": QUESTION,
            "completed_queries": COMPLETED,
            "provider_unique_query_count": 1,
        }
        values.update(kwargs)
        return target.build_second_wave_hybrid_queries(**values)

    def test_preserves_first_wave_and_replaces_only_second_wave(self) -> None:
        value = self.build()
        receipt = value["content_free_receipt"]
        self.assertEqual(value["queries"][:2], COMPLETED[:2])
        self.assertNotEqual(value["queries"][2:], COMPLETED[2:])
        self.assertIn(".ch", value["queries"][2])
        self.assertIn("Type", value["queries"][2])
        self.assertIn("IANA Root Zone Database", value["queries"][3])
        self.assertTrue(receipt["strategy_applied"])
        self.assertTrue(receipt["first_two_completed_queries_preserved"])
        self.assertEqual(receipt["shared_prefix_query_count"], 2)
        self.assertEqual(receipt["replaced_second_wave_query_count"], 2)
        self.assertEqual(receipt["selected_authority_ordinal"], 1)

    def test_one_or_two_provider_queries_both_preserve_completed_prefix(self) -> None:
        for count in (1, 2):
            with self.subTest(count=count):
                value = self.build(provider_unique_query_count=count)
                self.assertEqual(value["queries"][:2], COMPLETED[:2])
                self.assertTrue(value["content_free_receipt"]["strategy_applied"])

    def test_missing_facets_and_invalid_provider_fail_closed(self) -> None:
        missing = self.build(question="Return one table. Column names: Domain, Type.")
        self.assertEqual(missing["queries"], COMPLETED)
        self.assertFalse(missing["content_free_receipt"]["strategy_applied"])
        invalid = self.build(
            provider_unique_query_count=0,
            provider_query_vector_valid=False,
        )
        self.assertEqual(invalid["queries"], COMPLETED)
        self.assertFalse(invalid["content_free_receipt"]["strategy_applied"])

    def test_incomplete_or_duplicate_output_fails_closed(self) -> None:
        incomplete = self.build(completed_queries=COMPLETED[:3])
        self.assertEqual(incomplete["queries"], COMPLETED[:3])
        self.assertFalse(incomplete["content_free_receipt"]["strategy_applied"])
        generated = self.build()["queries"][2]
        collision = self.build(
            completed_queries=[COMPLETED[0], generated, COMPLETED[2], COMPLETED[3]]
        )
        self.assertEqual(
            collision["queries"],
            [COMPLETED[0], generated, COMPLETED[2], COMPLETED[3]],
        )
        self.assertFalse(collision["content_free_receipt"]["strategy_applied"])

    def test_receipt_is_content_free_and_credit_zero(self) -> None:
        receipt = self.build()["content_free_receipt"]
        serialized = str(receipt)
        for forbidden in (".ch", "IANA Root Zone Database", "TLD Manager"):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(receipt["entropy_or_information_gain_assigns_signed_credit"])
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_replay_resealed_tamper_and_unknown_field_fail_closed(self) -> None:
        value = self.build()
        self.assertEqual(
            target.validate_result(
                value,
                question=QUESTION,
                completed_queries=COMPLETED,
                provider_unique_query_count=1,
            ),
            value,
        )
        tampered = copy.deepcopy(value)
        tampered["queries"][0] = "changed first wave"
        tampered.pop("artifact_payload_sha256")
        import hashlib, json

        tampered["artifact_payload_sha256"] = hashlib.sha256(
            json.dumps(
                tampered,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        with self.assertRaises(ValueError):
            target.validate_result(
                tampered,
                question=QUESTION,
                completed_queries=COMPLETED,
                provider_unique_query_count=1,
            )

        receipt = copy.deepcopy(value["content_free_receipt"])
        receipt["unexpected"] = True
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            target.validate_receipt(receipt)

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v24995_second_wave_hybrid_queries.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
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


if __name__ == "__main__":
    unittest.main()
