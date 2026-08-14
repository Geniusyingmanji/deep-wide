from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25468_outcome_blind_row_key_source_population as target  # noqa: E402


class V25468OutcomeBlindRowKeySourcePopulationAuditTests(unittest.TestCase):
    def test_parent_and_historical_terminal_barriers_are_exact(self) -> None:
        build = target._build_barrier()
        role, terminal = target._historical_terminal_barrier()
        self.assertTrue(build["audit_valid"])
        self.assertEqual(role, target.EXPECTED_HISTORICAL_ROLE)
        self.assertEqual(terminal, target.EXPECTED_HISTORICAL_TERMINAL_TASKS)
        for path, expected in target.FIXED_HASHES.items():
            observed = (
                target._sha256(target._blob(path))
                if path
                in {
                    target.BUILD_AUDIT,
                    target.HISTORICAL_POPULATION,
                    target.HISTORICAL_FORWARD,
                }
                else target.base.sha256(path)
            )
            self.assertEqual(observed, expected)

    def test_population_audit_authorizes_only_protocol_design(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        authorization = value["authorization"]
        self.assertTrue(authorization["fresh_external_protocol_design"])
        self.assertFalse(authorization["external_forward"])
        self.assertFalse(authorization["postfreeze_truth_or_quality"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])
        self.assertEqual(value["selection"]["selected_overlap_count"], 0)

    def test_resealed_selection_check_or_authorization_tamper_fails(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        for kind in ("selection", "check", "authorization"):
            changed = copy.deepcopy(value)
            if kind == "selection":
                changed["selection"]["selected_overlap_count"] = 1
            elif kind == "check":
                changed["checks"][
                    "historical_score_metric_quality_prediction_or_per_task_outcome_never_read"
                ] = False
            else:
                changed["authorization"]["external_forward"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_nonzero_historical_overlap_fails_audit(self) -> None:
        first = target.population.CANDIDATE_BLOCKS[0][0]
        with mock.patch.object(
            target.population,
            "CONSUMED_PUBLIC_CLUES",
            (*target.population.CONSUMED_PUBLIC_CLUES[:-1], first),
        ):
            with self.assertRaises(RuntimeError):
                target.build_audit(now=1, tracked=False)


if __name__ == "__main__":
    unittest.main()
