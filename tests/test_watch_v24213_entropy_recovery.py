from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.watch_v24213_entropy_recovery import (  # noqa: E402
    _search_parent_state,
    run_cycle,
)


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}


def search_state() -> dict:
    value = {
        "role": "v24210_selected_search_component_watcher_state",
        "protocol": {
            "path": "results/v24210_selected_search_component_preregistration_v1_20260731.json",
            "sha256": "dc5a64d036aac52e9ec76fdc952645678aff9408e18887f425686ba2660c6f23",
        },
        "scope_parent_safe_state_envelope_opened": True,
        "search_quality_safe_state_envelope_opened": True,
        "entropy_controller_published_or_implemented": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
        "status": "waiting_for_scope_and_search_quality_terminal",
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


class WatchV24213EntropyRecoveryTests(unittest.TestCase):
    def test_exact_upstream_field_is_accepted_and_wrong_name_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "outputs/v24210_selected_search_component_watcher_state_v1_20260731.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(search_state()))
            value, terminal = _search_parent_state(root)
            self.assertFalse(terminal)
            self.assertEqual(
                value["status"], "waiting_for_scope_and_search_quality_terminal"
            )
            wrong = copy.deepcopy(value)
            wrong.pop("state_payload_sha256")
            wrong[
                "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing"
            ] = wrong.pop(
                "mapping_gold_category_question_type_evaluator_score_or_reward_read"
            )
            wrong["state_payload_sha256"] = payload_sha256(wrong)
            path.write_text(json.dumps(wrong))
            with self.assertRaisesRegex(RuntimeError, "safe envelope drifted"):
                _search_parent_state(root)

    def test_missing_activation_opens_no_parent_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            failed_activation = root / "results/v24212_selected_entropy_component_activation_v1_20260731.json"
            failed_state = root / "outputs/v24212_selected_entropy_component_watcher_state_v1_20260731.json"
            failed_activation.parent.mkdir(parents=True)
            failed_state.parent.mkdir(parents=True)
            failed_activation.write_text("{}")
            failed_state.write_text("{}")
            with mock.patch(
                "scripts.watch_v24213_entropy_recovery.ROOT", root
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery._activation",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery._search_parent_state"
            ) as search, mock.patch(
                "scripts.watch_v24213_entropy_recovery._gate2a_state"
            ) as gate:
                value = run_cycle(root, now=1)
        search.assert_not_called()
        gate.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")

    def test_dual_preterminal_opens_no_selected_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            failed_activation = root / "results/v24212_selected_entropy_component_activation_v1_20260731.json"
            failed_state = root / "outputs/v24212_selected_entropy_component_watcher_state_v1_20260731.json"
            failed_activation.parent.mkdir(parents=True)
            failed_state.parent.mkdir(parents=True)
            failed_activation.write_text("{}")
            failed_state.write_text("{}")
            with mock.patch(
                "scripts.watch_v24213_entropy_recovery.ROOT", root
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery._search_parent_state",
                return_value=({"status": "waiting_search"}, False),
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery._gate2a_state",
                return_value=({"status": "waiting_gate"}, False),
            ), mock.patch(
                "scripts.watch_v24213_entropy_recovery.load_selected_inputs"
            ) as loader:
                value = run_cycle(root, now=1)
        loader.assert_not_called()
        self.assertEqual(
            value["status"], "waiting_for_search_parent_and_gate2a_terminal"
        )
        self.assertFalse(value["selected_work_order_opened"])
        self.assertFalse(value["shared_api_lease_acquired"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_bootstrap_requires_isolated_flags_and_no_reexec(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/watch_v24213_entropy_recovery.py"
        ).read_text()
        self.assertIn("V2.42.13 watcher requires python -I -B", source)
        self.assertNotIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
