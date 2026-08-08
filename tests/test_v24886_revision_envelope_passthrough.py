from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24859_full_evidence_coverage_revision as frozen  # noqa: E402
from deepwide_agent import v24886_revision_envelope_passthrough as target  # noqa: E402


def table(rows: int) -> str:
    return (
        "| Name | Date |\n| --- | --- |\n"
        + "\n".join(f"| R{index:04d} | {2000 + index} |" for index in range(rows))
    )


class V24886RevisionEnvelopePassthroughTests(unittest.TestCase):
    def test_512_projects_to_frozen_byte_semantics(self) -> None:
        baseline = table(512)
        observed = target.apply_full_evidence_revision(
            baseline=baseline, proposed="", pages=()
        )
        expected = frozen.apply_full_evidence_revision(
            baseline=baseline, proposed="", pages=()
        )
        self.assertEqual(observed["candidate_table"], expected["candidate_table"])
        projected = copy.deepcopy(observed["receipt"])
        projected["role"] = frozen.ROLE
        projected["policy_id"] = frozen.POLICY_ID
        projected.pop("receipt_payload_sha256")
        projected["receipt_payload_sha256"] = frozen.payload_sha256(projected)
        self.assertEqual(projected, expected["receipt"])

    def test_513_and_700_are_exact_identity_without_deletion(self) -> None:
        for rows in (513, 700):
            with self.subTest(rows=rows):
                baseline = table(rows)
                value = target.apply_full_evidence_revision(
                    baseline=baseline, proposed="", pages=()
                )
                self.assertEqual(value["candidate_table"], baseline)
                receipt = value["receipt"]
                self.assertEqual(receipt["baseline_row_count"], rows)
                self.assertEqual(receipt["final_row_count"], rows)
                self.assertEqual(receipt["baseline_rows_deleted"], 0)
                self.assertEqual(receipt["support_checks"], 0)
                self.assertTrue(receipt["candidate_identity_handoff"])

    def test_over_envelope_is_identity_only(self) -> None:
        baseline = table(513)
        with self.assertRaises(ValueError):
            target.apply_full_evidence_revision(
                baseline=baseline, proposed=baseline, pages=()
            )
        with self.assertRaises(ValueError):
            target.apply_full_evidence_revision(
                baseline=baseline,
                proposed="",
                pages=[{"evidence_id": "E0001"}],
            )

    def test_duplicate_and_empty_identity_are_not_size_passthrough(self) -> None:
        duplicate = "| Name | Date |\n| --- | --- |\n| A | 1 |\n| a | 2 |"
        self.assertTrue(target.revision_envelope_eligible(duplicate))
        with self.assertRaises(ValueError):
            target.revision_envelope_eligible("| Name | Date |\n| --- | --- |")

    def test_resealed_tamper_fails_conservation(self) -> None:
        receipt = target.apply_full_evidence_revision(
            baseline=table(513), proposed="", pages=()
        )["receipt"]
        altered = copy.deepcopy(receipt)
        altered["final_row_count"] -= 1
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = frozen.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_receipt(altered)
        altered = copy.deepcopy(receipt)
        altered["support_checks"] = False
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = frozen.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_receipt(altered)
        altered = copy.deepcopy(receipt)
        altered["table_column_count"] = "2"
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = frozen.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_receipt(altered)

    def test_receipt_is_content_free_and_label_blind(self) -> None:
        receipt = target.apply_full_evidence_revision(
            baseline=table(513), proposed="", pages=()
        )["receipt"]
        encoded = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("R0001", encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )

    def test_source_has_no_privileged_effect_capability(self) -> None:
        source = ROOT / "src/deepwide_agent/v24886_revision_envelope_passthrough.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and not node.level
        }
        imports.update(
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        self.assertTrue(imports.isdisjoint({"os", "pathlib", "subprocess", "requests"}))


if __name__ == "__main__":
    unittest.main()
