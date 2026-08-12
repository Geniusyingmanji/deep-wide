from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v25213_population_selection as target  # noqa: E402


class V25213PopulationSelectionAuditTests(unittest.TestCase):
    @staticmethod
    def _candidates() -> dict[str, list[str]]:
        return {
            stratum: [f"fresh-{index}-{stratum}" for index in range(16)]
            for stratum in target.RISK_STRATA
        }

    @staticmethod
    def _zero_hit() -> list[mock.Mock]:
        return [
            mock.Mock(stdout="parent\n"),
            *[mock.Mock(stdout="") for _ in range(target.TASK_COUNT)],
        ]

    def test_aggregate_only_zero_hit_selection_has_exact_strata(self) -> None:
        candidates = self._candidates()
        with mock.patch.object(
            target.subprocess, "run", side_effect=self._zero_hit()
        ):
            value = target.build_audit(candidates, parent_commit="parent", now=1)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["identity_count"], 64)
        self.assertEqual(
            value["stratum_identity_counts"],
            {stratum: 16 for stratum in target.RISK_STRATA},
        )
        self.assertEqual(
            value["stratum_identity_history_zero_hit_counts"],
            {stratum: 16 for stratum in target.RISK_STRATA},
        )
        encoded = json.dumps(value, sort_keys=True)
        for rows in candidates.values():
            for identity in rows:
                self.assertNotIn(identity.casefold(), encoded)
        self.assertFalse(
            value["candidate_preselection_provenance_attested_by_selector"]
        )
        self.assertFalse(value["population_frozen_or_external_protocol_authorized"])

    def test_wrong_strata_count_or_cross_stratum_duplicate_fails_before_git(self) -> None:
        cases: list[dict[str, list[str]]] = []
        missing = self._candidates()
        missing.pop(target.RISK_STRATA[0])
        cases.append(missing)
        short = self._candidates()
        short[target.RISK_STRATA[0]].pop()
        cases.append(short)
        duplicate = self._candidates()
        duplicate[target.RISK_STRATA[1]][0] = duplicate[target.RISK_STRATA[0]][0]
        cases.append(duplicate)
        for candidates in cases:
            with self.subTest(case=len(cases)), mock.patch.object(
                target.subprocess, "run"
            ) as called, self.assertRaises(RuntimeError):
                target.build_audit(candidates, parent_commit="parent", now=1)
            called.assert_not_called()

    def test_nonzero_history_hit_fails_closed_without_identity_output(self) -> None:
        completed = self._zero_hit()
        completed[17] = mock.Mock(stdout="commit\n")
        with mock.patch.object(
            target.subprocess, "run", side_effect=completed
        ), self.assertRaises(RuntimeError):
            target.build_audit(
                self._candidates(), parent_commit="parent", now=1
            )

    def test_git_scan_is_parent_bound_literal_and_repository_scoped(self) -> None:
        calls: list[list[str]] = []

        def completed(command, **kwargs):
            calls.append(command)
            return mock.Mock(stdout="parent\n" if command[1] == "rev-parse" else "")

        with mock.patch.object(target.subprocess, "run", side_effect=completed):
            target.build_audit(self._candidates(), parent_commit="parent", now=1)
        self.assertEqual(len(calls), 65)
        for command in calls[1:]:
            self.assertEqual(command[:4], ["git", "log", "parent", "-i"])
            self.assertEqual(command[4], "-S")
            self.assertEqual(command[-7:], ["--", *target.HISTORY_PATHS])

    def test_candidate_parser_preserves_stratum_counts_but_not_mapping(self) -> None:
        candidates = self._candidates()
        raw = [
            f"{stratum}={identity}"
            for stratum in target.RISK_STRATA
            for identity in candidates[stratum]
        ]
        self.assertEqual(target._parse_candidates(raw), candidates)
        with self.assertRaises(RuntimeError):
            target._parse_candidates(["unknown=value"])

    def test_resealed_content_authority_history_or_credit_tamper_fails(self) -> None:
        with mock.patch.object(
            target.subprocess, "run", side_effect=self._zero_hit()
        ):
            value = target.build_audit(
                self._candidates(), parent_commit="parent", now=1
            )
        for name in (
            "identity_plaintext_item_hash_or_stratum_identity_mapping_persisted",
            "endpoint_page_value_question_prediction_or_evidence_persisted",
            "risk_stratum_passed_as_hidden_runtime_input_or_router_signal",
            "selection_script_network_model_search_fetch_or_evaluator_called",
            "prior_external_or_deepwidebench_population_reuse",
            "population_frozen_or_external_protocol_authorized",
            "entropy_or_information_gain_assigns_signed_credit",
        ):
            changed = copy.deepcopy(value)
            changed[name] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                target.validate_audit(changed)
        changed = copy.deepcopy(value)
        changed["stratum_identity_history_zero_hit_counts"][target.RISK_STRATA[0]] -= 1
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
