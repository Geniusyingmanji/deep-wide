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

from scripts import finalize_v24286_neutral_full_task as target  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


class FinalizeV24286NeutralFullTaskTests(unittest.TestCase):
    def test_real_decision_is_engineering_go_without_benchmark_authority(self):
        value = target.build_decision(ROOT, now=1)
        target.validate_decision(value)
        self.assertTrue(value["passed"])
        self.assertTrue(all(value["checks"].values()))
        self.assertFalse(any(value["authorization"].values()))
        self.assertLessEqual(value["observed"]["wall_seconds"], 35.0)

    def test_resealed_check_claim_or_authority_tamper_fails(self):
        for mutation in ("check", "claim", "authority"):
            altered = copy.deepcopy(target.build_decision(ROOT, now=1))
            if mutation == "check":
                altered["checks"]["maximum_wall_seconds"] = False
            elif mutation == "claim":
                altered["claim_scope"] = "sota"
            else:
                altered["authorization"]["exact220_launch"] = True
            unsigned = dict(altered)
            unsigned.pop("decision_payload_sha256")
            altered["decision_payload_sha256"] = payload_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "decision drifted"):
                target.validate_decision(altered)


if __name__ == "__main__":
    unittest.main()
