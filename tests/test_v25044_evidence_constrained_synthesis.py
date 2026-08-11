from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src",):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25044_evidence_constrained_synthesis as target  # noqa: E402


QUESTION = "Return one row for package alpha with columns Package, Version, Date."
COLUMNS = ("Package", "Version", "Date")
EVIDENCE = "[PAGE 1]\nalpha version 2.0 date 2026-08-01\n[PAGE 2]\nbeta version 9.0"


class V25044EvidenceConstrainedSynthesisTests(unittest.TestCase):
    def test_two_arms_preserve_evidence_bytes_and_common_visible_contract(self) -> None:
        prompts = {
            arm: target.synthesis_prompt(
                arm, question=QUESTION, columns=COLUMNS, evidence=EVIDENCE
            )
            for arm in target.ARMS
        }
        for system, user, receipt in prompts.values():
            self.assertTrue(system)
            self.assertIn(QUESTION, user)
            self.assertIn(EVIDENCE, user)
            self.assertEqual(receipt["evidence_characters"], len(EVIDENCE))
            self.assertFalse(
                receipt[
                    "evidence_bytes_parsed_ranked_truncated_reordered_or_modified"
                ]
            )
        self.assertNotEqual(prompts[target.CONTROL_ARM][0], prompts[target.CANDIDATE_ARM][0])

    def test_candidate_requires_identity_field_record_binding_and_unknown(self) -> None:
        _system, user, receipt = target.synthesis_prompt(
            target.CANDIDATE_ARM,
            question=QUESTION,
            columns=COLUMNS,
            evidence=EVIDENCE,
        )
        self.assertIn("exact requested row identity", user)
        self.assertIn("same current/latest record", user)
        self.assertIn("write Unknown", user)
        self.assertTrue(receipt["candidate_requires_exact_row_identity_field_value_binding"])
        self.assertTrue(receipt["candidate_requires_same_record_current_latest_coherence"])
        self.assertTrue(receipt["candidate_conflict_or_ambiguity_projects_unknown"])

    def test_control_does_not_claim_candidate_treatment(self) -> None:
        _system, user, receipt = target.synthesis_prompt(
            target.CONTROL_ARM,
            question=QUESTION,
            columns=COLUMNS,
            evidence=EVIDENCE,
        )
        self.assertNotIn(target.CANDIDATE_RULES, user)
        self.assertFalse(receipt["candidate_treatment_applied"])
        self.assertFalse(receipt["candidate_forbids_general_knowledge_completion"])

    def test_no_hard_cap_or_entropy_authority(self) -> None:
        for arm in target.ARMS:
            _system, _user, receipt = target.synthesis_prompt(
                arm, question=QUESTION, columns=COLUMNS, evidence=EVIDENCE
            )
            self.assertFalse(
                receipt["query_fetch_model_output_token_context_or_wall_cap_changed"]
            )
            self.assertFalse(
                receipt["entropy_or_information_gain_assigns_credit_or_routes"]
            )
            self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])

    def test_invalid_or_injected_schema_fails_closed(self) -> None:
        for columns in (("A", "a"), ("A|B",), (), ("A\nB",)):
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                target.synthesis_prompt(
                    target.CANDIDATE_ARM,
                    question=QUESTION,
                    columns=columns,
                    evidence=EVIDENCE,
                )
        with self.assertRaises(ValueError):
            target.synthesis_prompt(
                "unknown", question=QUESTION, columns=COLUMNS, evidence=EVIDENCE
            )

    def test_nested_tamper_fails_closed(self) -> None:
        _system, _user, receipt = target.synthesis_prompt(
            target.CANDIDATE_ARM,
            question=QUESTION,
            columns=COLUMNS,
            evidence=EVIDENCE,
        )
        changed = copy.deepcopy(receipt)
        changed["candidate_forbids_general_knowledge_completion"] = False
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_receipt(changed)


if __name__ == "__main__":
    unittest.main()
