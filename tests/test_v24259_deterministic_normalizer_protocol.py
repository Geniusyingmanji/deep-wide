from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import activate_v24259_deterministic_normalizer_smoke as activate  # noqa: E402
from scripts import preregister_v24259_deterministic_normalizer_smoke as prereg  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


INACTIVE = {"active": False, "ordinary": True, "record_valid": True}


class V24259ProtocolTests(unittest.TestCase):
    def test_protocol_freezes_one_change_and_same_full_smoke16(self) -> None:
        with mock.patch.object(prereg, "lease_observation", return_value=INACTIVE), mock.patch.object(
            prereg, "process_snapshot", return_value=[]
        ):
            value = prereg.build_protocol(
                ROOT,
                created_at_unix=1,
                require_pristine=False,
            )
        self.assertTrue(value["label_blind"])
        self.assertEqual(value["task_contract"]["selected_count"], 16)
        self.assertFalse(value["task_contract"]["selective_parent_failure_rerun"])
        self.assertEqual(value["limits"]["wall_seconds"], 600)
        self.assertEqual(value["limits"]["model_calls"], 3)
        self.assertTrue(
            value["single_change"][
                "model_prompt_search_provider_budget_selection_and_gate_unchanged"
            ]
        )
        self.assertFalse(value["single_change"]["nonempty_factual_cell_rewrite"])
        self.assertFalse(value["single_change"]["partial_malformed_row_deletion"])
        self.assertFalse(value["authorization"]["official_evaluator_call"])
        self.assertFalse(value["authorization"]["paired_dev64_or_full220_launch"])
        unsigned = dict(value)
        self.assertEqual(unsigned.pop("decision_contract_sha256"), payload_sha256(unsigned))

    def test_active_lease_or_duplicate_runner_fails_closed(self) -> None:
        with mock.patch.object(prereg, "lease_observation", return_value=dict(INACTIVE, active=True)), mock.patch.object(
            prereg, "process_snapshot", return_value=[]
        ), self.assertRaisesRegex(RuntimeError, "boundary is not clean"):
            prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        rows = [{"pid": 1, "argv": ["python", "-I", "-B", prereg.RUNNER_MARKER]}]
        with mock.patch.object(prereg, "lease_observation", return_value=INACTIVE), mock.patch.object(
            prereg, "process_snapshot", return_value=rows
        ), self.assertRaisesRegex(RuntimeError, "boundary is not clean"):
            prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=False)

    def test_activation_authorizes_no_evaluator_or_benchmark(self) -> None:
        protocol = {
            "decision_contract_sha256": "d" * 64,
            "control_surface": {"manifest_sha256": "m" * 64},
            "task_contract": {"selected_opaque_ids_sha256": "s" * 64},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / activate.OUTPUT
            path.parent.mkdir(parents=True)
            path.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(activate, "validate_protocol", return_value=protocol), mock.patch.object(
                activate, "process_snapshot", return_value=[]
            ), mock.patch.object(activate, "lease_observation", return_value=INACTIVE):
                value = activate.build_activation(root, created_at_unix=1)
        self.assertFalse(value["official_evaluator_dev64_full220_or_leaderboard_authorized"])
        self.assertFalse(
            value[
                "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
