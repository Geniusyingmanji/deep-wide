from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24723_fresh_indicator_population as target  # noqa: E402


class V24723FreshIndicatorPopulationTests(unittest.TestCase):
    def test_actual_pre_outcome_source_selects_exact_two_fresh_targets(self) -> None:
        value = target.build_design(now=0)
        target.validate_design(value)
        self.assertEqual(
            [item["target_key"] for item in value["selection"]["selected_targets"]],
            ["IT.NET.USER.ZS@2022", "SP.DYN.LE00.IN@2022"],
        )
        self.assertFalse(
            value["selection"]["network_or_transport_outcome_used_for_selection"]
        )
        self.assertFalse(value["authorization"]["transport_launch"])

    def test_consumed_or_dynamic_target_source_fails_closed(self) -> None:
        source = b'TARGETS = (("A", "AG.SRF.TOTL.K2", "2022"),)\n'
        with self.assertRaises(ValueError):
            target.select_targets(source)
        with self.assertRaises(ValueError):
            target.select_targets(b"TARGETS = tuple()\n")

    def test_resealed_selection_or_authorization_tamper_fails(self) -> None:
        value = target.build_design(now=0)
        for path, replacement in (
            (("selection", "selected_count"), 3),
            (("authorization", "transport_launch"), True),
        ):
            tampered = copy.deepcopy(value)
            tampered[path[0]][path[1]] = replacement
            tampered.pop("design_payload_sha256")
            tampered["design_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_design(tampered)


if __name__ == "__main__":
    unittest.main()
