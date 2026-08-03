from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24308_neutral_child_exit_observability as target  # noqa: E402


class V24308NeutralChildExitObservabilityTests(unittest.TestCase):
    def test_v1_is_explicitly_invalidated_before_v2(self) -> None:
        value = target.build_v1_invalidation(ROOT, now=1)
        target.validate_v1_invalidation(ROOT, value)
        self.assertEqual(value["status"], "invalid_do_not_use")
        self.assertFalse(value["authorization"]["future_runner_integration_design"])

    def test_every_real_subprocess_mode_is_distinct_and_zero_effect(self) -> None:
        receipts = {}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            for mode in target.MODES:
                directory = base / mode
                directory.mkdir()
                receipts[mode] = target.run_mode(
                    ROOT, mode, directory, timeout_seconds=0.15
                )
        value = target.project(receipts, now=1)
        self.assertEqual(value["observed_taxonomy"], target.EXPECTED)
        self.assertFalse(any(value["effect_ledger"].values()))
        self.assertFalse(value["authorization"]["benchmark_dev64"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_protocol_binds_parent_and_has_no_benchmark_authority(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        target.validate_protocol(ROOT, value)
        self.assertEqual(value["modes"], list(target.MODES))
        self.assertEqual(value["network_model_search_fetch_or_evaluator_calls"], 0)
        self.assertFalse(value["authorization"]["benchmark_dev64"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_resealed_protocol_parent_tamper_fails_closed(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        altered = copy.deepcopy(value)
        altered["parent"]["path"] = "results/not_the_frozen_parent.json"
        altered.pop("protocol_payload_sha256")
        altered["protocol_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "protocol drifted"):
            target.validate_protocol(ROOT, altered)

    def test_probe_directory_cannot_escape_outputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            with self.assertRaisesRegex(RuntimeError, "escaped outputs"):
                target.run_mode(
                    ROOT,
                    "success",
                    Path(temporary),
                    timeout_seconds=0.15,
                )


if __name__ == "__main__":
    unittest.main()
