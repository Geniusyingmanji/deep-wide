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

from deepwide_agent import v24929_unicode_total_neutral_contract as contract  # noqa: E402
from scripts import control_v24929_unicode_total_neutral_gate as parent  # noqa: E402
from scripts import control_v24930_unicode_total_neutral_start as corrected  # noqa: E402


class V24930UnicodeTotalNeutralStartTests(unittest.TestCase):
    def test_frozen_parent_empty_list_truthiness_bug_is_reproduced(self) -> None:
        with patch.object(parent, "_active_conflicts", return_value=[]):
            value = parent.build_start()
        self.assertEqual(value["checks"]["conflicting_process_pids"], [])
        self.assertEqual(value["findings"], ["conflicting_process_pids"])

    def test_corrected_empty_conflict_predicate_authorizes(self) -> None:
        with patch.object(parent, "_active_conflicts", return_value=[]):
            value = corrected.build_start(now=1)
        self.assertTrue(value["checks"]["conflicting_process_pids_empty"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["status"], "authorized_not_started")
        self.assertTrue(value["authorization"]["single_fresh_neutral_gate"])

    def test_nonempty_conflict_fails_closed(self) -> None:
        with patch.object(parent, "_active_conflicts", return_value=[12345]):
            value = corrected.build_start(now=1)
        self.assertFalse(value["checks"]["conflicting_process_pids_empty"])
        self.assertIn("conflicting_process_pids_empty", value["findings"])
        self.assertFalse(value["authorization"]["single_fresh_neutral_gate"])

    def test_resealed_algorithm_change_tamper_is_rejected(self) -> None:
        with patch.object(parent, "_active_conflicts", return_value=[]):
            value = corrected.build_start(now=1)
        tampered = copy.deepcopy(value)
        tampered["correction"][
            "algorithm_model_search_fetch_prompt_budget_or_task_vector_changed"
        ] = True
        tampered.pop("execution_start_payload_sha256")
        tampered["execution_start_payload_sha256"] = contract.payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            corrected.validate_start(tampered)


if __name__ == "__main__":
    unittest.main()
