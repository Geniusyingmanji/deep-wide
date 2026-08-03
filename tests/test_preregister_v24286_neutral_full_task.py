from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import preregister_v24286_neutral_full_task as target  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


class PreregisterV24286NeutralFullTaskTests(unittest.TestCase):
    def test_protocol_freezes_one_neutral_probe_and_no_benchmark_authority(self):
        value = target.build_protocol(ROOT, now=1, require_pristine=False)
        target.validate_protocol(ROOT, value=value)
        self.assertEqual(value["task_contract"]["task_count"], 1)
        self.assertTrue(value["authorization"]["one_neutral_provider_probe"])
        self.assertFalse(value["authorization"]["exact220_launch"])
        self.assertEqual(value["gates"]["maximum_wall_seconds"], 35.0)

    def test_resealed_gate_authority_or_manifest_tamper_fails(self):
        for mutation in ("gate", "authority", "manifest"):
            altered = copy.deepcopy(
                target.build_protocol(ROOT, now=1, require_pristine=False)
            )
            if mutation == "gate":
                altered["gates"]["maximum_wall_seconds"] = 350.0
            elif mutation == "authority":
                altered["authorization"]["exact220_launch"] = True
            else:
                key = next(iter(altered["surface_manifest"]))
                altered["surface_manifest"][key] = "0" * 64
                altered["surface_manifest_sha256"] = payload_sha256(
                    altered["surface_manifest"]
                )
            unsigned = dict(altered)
            unsigned.pop("protocol_payload_sha256")
            altered["protocol_payload_sha256"] = payload_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "preregistration drifted"):
                target.validate_protocol(ROOT, value=altered)


if __name__ == "__main__":
    unittest.main()
