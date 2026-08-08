from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24886_revision_envelope_passthrough as frozen  # noqa: E402
from deepwide_agent import v24897_revision_parser_totality as target  # noqa: E402


PLAIN = "```markdown\n| Name | Code | Note |\n| --- | --- | --- |\n| Alpha | plain | Stable |\n```"
FULLWIDTH_PIPE = "```markdown\n| Name | Code | Note |\n| --- | --- | --- |\n| Alpha | left｜right | Stable |\n```"


class V24897RevisionParserTotalityTests(unittest.TestCase):
    def test_plain_parent_retains_frozen_candidate_semantics(self) -> None:
        observed = target.apply_full_evidence_revision(
            baseline=PLAIN, proposed="", pages=()
        )
        expected = frozen.apply_full_evidence_revision(
            baseline=PLAIN, proposed="", pages=()
        )
        self.assertEqual(observed["candidate_table"], expected["candidate_table"])
        self.assertTrue(target.revision_envelope_eligible(PLAIN))

    def test_fullwidth_pipe_parent_is_identity_only(self) -> None:
        self.assertFalse(target.revision_envelope_eligible(FULLWIDTH_PIPE))
        value = target.apply_full_evidence_revision(
            baseline=FULLWIDTH_PIPE, proposed="", pages=()
        )
        self.assertEqual(value["candidate_table"], FULLWIDTH_PIPE)
        self.assertEqual(value["receipt"]["baseline_row_count"], 1)
        self.assertEqual(value["receipt"]["table_column_count"], 3)
        self.assertEqual(value["receipt"]["baseline_rows_deleted"], 0)
        self.assertEqual(value["receipt"]["support_checks"], 0)

    def test_parser_incompatible_parent_rejects_nonidentity_effects(self) -> None:
        with self.assertRaises(ValueError):
            target.apply_full_evidence_revision(
                baseline=FULLWIDTH_PIPE, proposed=PLAIN, pages=()
            )

    def test_resealed_receipt_tamper_fails(self) -> None:
        receipt = target.apply_full_evidence_revision(
            baseline=FULLWIDTH_PIPE, proposed="", pages=()
        )["receipt"]
        altered = copy.deepcopy(receipt)
        altered["final_row_count"] += 1
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = frozen.frozen.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_receipt(altered)


if __name__ == "__main__":
    unittest.main()
