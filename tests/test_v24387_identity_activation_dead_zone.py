from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24387_identity_activation_dead_zone as target  # noqa: E402


class V24387IdentityActivationDeadZoneTests(unittest.TestCase):
    def test_frozen_no_go_yields_uncertainty_target_successor(self) -> None:
        value = target.build(ROOT, now=0)
        target.validate(ROOT, value=value)
        self.assertTrue(value["diagnosis"]["proposal_acquisition_succeeded"])
        self.assertTrue(
            value["diagnosis"][
                "eligible_alternative_support_was_zero_for_every_task"
            ]
        )
        self.assertEqual(
            value["diagnosis"]["root_cause"],
            "candidate_revision_requires_preexisting_eligible_alternative_support_after_baseline_consumes_the_same_proposal_evidence",
        )
        self.assertTrue(
            value["successor_contract"][
                "active_target_selection_does_not_require_a_preexisting_candidate_change"
            ]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])

    def test_resealed_observation_contract_and_authorization_tamper_fail(self) -> None:
        for field in ("observation", "contract", "authorization", "source"):
            with self.subTest(field=field):
                value = copy.deepcopy(target.build(ROOT, now=0))
                if field == "observation":
                    value["observed_no_go"]["active_query_tasks"] = 1
                elif field == "contract":
                    value["successor_contract"]["maximum_selected_targets"] = 3
                elif field == "authorization":
                    value["authorization"]["external_probe_launch"] = True
                else:
                    key = next(iter(value["source_manifest"]))
                    value["source_manifest"][key] = "0" * 64
                    value["source_manifest_sha256"] = payload_sha256(
                        value["source_manifest"]
                    )
                value.pop("diagnosis_payload_sha256")
                value["diagnosis_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate(ROOT, value=value)


if __name__ == "__main__":
    unittest.main()
