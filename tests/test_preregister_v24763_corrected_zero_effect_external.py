from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24763_corrected_zero_effect_external as target  # noqa: E402


class V24763CorrectedZeroEffectExternalProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_protocol(
            now=0, require_clean=False, require_pristine=False
        )

    def test_correction_and_supersession_are_bound(self) -> None:
        value = self.value
        self.assertTrue(value["parents"]["v24760_population_recertified"])
        self.assertTrue(value["parents"]["v24761_never_activated"])
        self.assertFalse(value["parents"]["v24761_authorizes_successor_use"])
        self.assertEqual(
            value["provenance_correction"][
                "v24758_immutable_ror_record_https_reads_code_path_implied"
            ],
            3_482,
        )
        self.assertTrue(value["source_policy"]["historical_immutable_ror_source_reads_acknowledged"])

    def test_runtime_and_all_scientific_gates_are_frozen_from_v24761(self) -> None:
        old = target._read(ROOT / target.OLD_PROTOCOL)
        for field in (
            "population",
            "task_contract",
            "runtime",
            "forward_health_gate",
            "mechanism_gate_before_private_truth",
            "quality_gate_after_prediction_freeze",
            "entropy_credit_scope",
        ):
            self.assertEqual(self.value[field], old[field])

    def test_manifest_is_evaluator_isolated_and_current(self) -> None:
        manifest = self.value["dependency_manifest"]
        self.assertEqual(manifest, target.dependency_manifest())
        for path in manifest:
            for marker in target.FORBIDDEN_DEPENDENCY_MARKERS:
                self.assertNotIn(marker, path.casefold())

    def test_protocol_is_inert_and_does_not_authorize_runner(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["corrected_protocol_published"])
        self.assertFalse(authorization["runner_or_control_plane_build"])
        self.assertFalse(authorization["preactivation_audit_generation"])
        self.assertFalse(authorization["activation"])
        self.assertFalse(authorization["one_external_forward_launch"])
        self.assertFalse(authorization["quality_surface_open"])
        self.assertFalse(authorization["exact220"])

    def test_resealed_runner_authority_tamper_fails(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["authorization"]["runner_or_control_plane_build"] = True
        altered.pop("protocol_payload_sha256")
        altered["protocol_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(altered)


if __name__ == "__main__":
    unittest.main()
