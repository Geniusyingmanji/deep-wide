from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import preregister_v24290_neutral_low_coverage as target  # noqa: E402


class V24290NeutralPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_protocol(ROOT, now=1, require_pristine=False)

    def test_protocol_freezes_fault_injection_gates_and_no_benchmark(self) -> None:
        target.validate_protocol(ROOT, value=self.value)
        self.assertEqual(self.value["gates"]["required_rescue_triggered"], True)
        self.assertEqual(self.value["gates"]["maximum_hosted_search_requests_added_by_rescue"], 0)
        self.assertFalse(self.value["authorization"]["benchmark_launch"])
        self.assertFalse(self.value["authorization"]["dev64_launch"])
        self.assertEqual(self.value["fault_injection"]["claim_scope"], "mechanism_robustness_not_natural_frequency_or_benchmark_quality")

    def test_resealed_gate_or_authorization_tamper_is_rejected(self) -> None:
        for mutation in ("gate", "launch"):
            altered = copy.deepcopy(self.value)
            if mutation == "gate":
                altered["gates"]["maximum_hosted_search_requests_added_by_rescue"] = 1
            else:
                altered["authorization"]["dev64_launch"] = True
            altered["protocol_payload_sha256"] = target.payload_sha256(
                {key: value for key, value in altered.items() if key != "protocol_payload_sha256"}
            )
            with self.assertRaisesRegex(RuntimeError, "protocol drifted"):
                target.validate_protocol(ROOT, value=altered)


if __name__ == "__main__":
    unittest.main()
