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
from scripts import diagnose_v24382_active_verifier_query as target  # noqa: E402


class V24382ActiveVerifierQueryDiagnosisTests(unittest.TestCase):
    def test_frozen_no_go_yields_active_query_contract(self) -> None:
        value = target.build(ROOT, now=0)
        target.validate(ROOT, value=value)
        self.assertTrue(
            value["diagnosis"][
                "candidate_conditioned_source_selection_but_not_search"
            ]
        )
        self.assertEqual(
            value["diagnosis"]["root_cause"],
            "candidate_target_unavailable_when_verifier_source_pool_was_searched",
        )
        self.assertEqual(
            value["successor_contract"]["maximum_total_hosted_search_batches"],
            3,
        )
        self.assertEqual(value["successor_contract"]["total_fetch_cap"], 10)
        self.assertFalse(value["authorization"]["external_probe_launch"])

    def test_resealed_observation_and_authorization_tamper_fail(self) -> None:
        for field in ("observation", "authorization", "contract"):
            with self.subTest(field=field):
                value = copy.deepcopy(target.build(ROOT, now=0))
                if field == "observation":
                    value["observed_no_go"][
                        "verifier_semantic_projection_count"
                    ] = 1
                elif field == "authorization":
                    value["authorization"]["external_probe_launch"] = True
                else:
                    value["successor_contract"]["total_fetch_cap"] = 11
                value.pop("diagnosis_payload_sha256")
                value["diagnosis_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate(ROOT, value=value)


if __name__ == "__main__":
    unittest.main()
