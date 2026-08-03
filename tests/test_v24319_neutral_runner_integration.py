from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24319_neutral_runner_integration as target  # noqa: E402


class V24319NeutralRunnerIntegrationTests(unittest.TestCase):
    def test_protocol_binds_parents_and_grants_no_benchmark_launch(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        target.validate_protocol(ROOT, value)
        self.assertEqual(value["real_local_subprocess_children"], 11)
        self.assertTrue(value["deadline_stops_must_be_complete_success_envelopes"])
        self.assertFalse(value["authorization"]["paired_dev64_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_real_subprocess_probe_has_exact_taxonomy_and_zero_external_effect(self) -> None:
        if not (ROOT / target.PROTOCOL).is_file():
            self.skipTest("official probe runs only after protocol publication")
        value = target.execute_probe(ROOT, now=1)
        target.validate_probe(ROOT, value)
        self.assertEqual(
            {name: value["modes"][name]["failure_taxonomy"] for name in target.MODES},
            target.EXPECTED_TAXONOMY,
        )
        self.assertGreater(value["modes"]["slot_reject"]["pre_provider_rejections"], 0)
        self.assertFalse(value["authorization"]["paired_dev64_launch"])

    def test_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        altered = copy.deepcopy(value)
        altered["expected_parent_taxonomy"]["timeout"] = "success"
        altered.pop("protocol_payload_sha256")
        altered["protocol_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
