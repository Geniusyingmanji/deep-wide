from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24739_fresh_resilience_population as target  # noqa: E402


class V24739FreshResiliencePopulationTests(unittest.TestCase):
    def test_fixed_zero_occurrence_candidates_select_exact_first_two(self) -> None:
        value = target.build_design(now=0)
        target.validate_design(value)
        self.assertEqual(
            [row["target_key"] for row in value["selection"]["selected_targets"]],
            ["EG.ELC.ACCS.ZS@2022", "SH.H2O.BASW.ZS@2022"],
        )
        self.assertTrue(
            value["selection"]["all_candidates_absent_from_pre_outcome_tracked_tree"]
        )
        self.assertFalse(value["authorization"]["transport_launch"])

    def test_prior_occurrence_or_invalid_candidate_fails_closed(self) -> None:
        completed = target.subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"tracked.py\n", stderr=b""
        )
        with patch.object(target, "_git", return_value=completed):
            with self.assertRaises(ValueError):
                target.select_targets()
        with self.assertRaises(ValueError):
            target.select_targets((("x", "invalid", "2022"),))

    def test_resealed_selection_or_authorization_tamper_fails(self) -> None:
        value = target.build_design(now=0)
        for path, replacement in (
            (("selection", "selected_count"), 3),
            (("authorization", "transport_launch"), True),
        ):
            tampered = copy.deepcopy(value)
            tampered[path[0]][path[1]] = replacement
            tampered.pop("design_payload_sha256")
            tampered["design_payload_sha256"] = target.seal.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_design(tampered)


if __name__ == "__main__":
    unittest.main()
