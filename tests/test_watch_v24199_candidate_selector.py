from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24199_candidate_selector import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
        "selector_protocol": {"path": "results/selector.json", "sha256": "s" * 64},
        "parent": {"protocol": {"sha256": "c" * 64}},
        "inheritance_contract": {"slot_manifest": {}},
    },
}
SELECTOR = {"sha256": "s" * 64, "value": {"selector_payload_sha256": "x" * 64}}


class WatchV24199CandidateSelectorTests(unittest.TestCase):
    def _run(self, root: Path, *, activation=None):
        with mock.patch(
            "scripts.watch_v24199_candidate_selector.ROOT", root
        ), mock.patch(
            "scripts.watch_v24199_candidate_selector.validate_protocol",
            return_value=VERIFIED,
        ), mock.patch(
            "scripts.watch_v24199_candidate_selector.validate_selector",
            return_value=SELECTOR,
        ), mock.patch(
            "scripts.watch_v24199_candidate_selector._activation",
            return_value=activation,
        ):
            return run_cycle(root, now=1)

    def test_missing_activation_opens_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = self._run(Path(directory))
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["quality_status_envelopes_opened"])
        self.assertFalse(value["capacity_pair_opened"])
        self.assertFalse(value["candidate_slot_selected"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_activated_pre_capacity_does_not_open_quality_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = self._run(Path(directory), activation={"sha256": "a" * 64})
        self.assertEqual(value["status"], "waiting_for_capacity_freeze")
        self.assertFalse(value["quality_status_envelopes_opened"])
        self.assertFalse(value["candidate_publication_opened"])
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called"])

    def test_terminal_vector_missing_slot_waits_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for raw in (
                "results/v24196_capacity_ladder_report_v1_20260731.json",
                "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json",
            ):
                path = root / raw
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            slot = {
                "feature_vector": {
                    "schema77": False,
                    "search_yield": False,
                    "markdown": False,
                    "scope_open": False,
                    "entropy_credit": False,
                },
                "candidate_publication_path": "results/missing/publication.json",
                "candidate_handoff_path": "results/missing/handoff.json",
            }
            verified = {
                **VERIFIED,
                "value": {
                    **VERIFIED["value"],
                    "inheritance_contract": {"slot_manifest": {"slot": slot}},
                },
            }
            with mock.patch(
                "scripts.watch_v24199_candidate_selector.ROOT", root
            ), mock.patch(
                "scripts.watch_v24199_candidate_selector.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.watch_v24199_candidate_selector.validate_selector",
                return_value=SELECTOR,
            ), mock.patch(
                "scripts.watch_v24199_candidate_selector._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24199_candidate_selector.load_capacity_pair",
                return_value=(
                    {"selected": 4, "workers": 2, "shards": 2},
                    {},
                    {"report_sha256": "r" * 64, "freeze_sha256": "f" * 64},
                ),
            ), mock.patch(
                "scripts.watch_v24199_candidate_selector._quality_states",
                return_value=({}, {}),
            ), mock.patch(
                "scripts.watch_v24199_candidate_selector.derive_terminal_vector",
                return_value=(slot["feature_vector"], {"all": "go"}),
            ), mock.patch(
                "scripts.watch_v24199_candidate_selector.slot_for_vector",
                return_value="slot",
            ):
                value = run_cycle(root, now=1)
        self.assertEqual(value["status"], "waiting_for_integrated_candidate_slot")
        self.assertEqual(value["reason"], "selected_slot_publication_absent_no_fallback")
        self.assertTrue(value["candidate_slot_selected"])
        self.assertFalse(value["candidate_built_merged_or_frozen_by_selector"])
        self.assertFalse(value["terminal_receipt_created"])

    def test_bootstrap_validates_in_place_without_reexec(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/watch_v24199_candidate_selector.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("os.execve", source)
        self.assertIn("V2.41.99 watcher requires python -I -B", source)
        self.assertIn("V2.41.99 control bytes drifted", source)


if __name__ == "__main__":
    unittest.main()
