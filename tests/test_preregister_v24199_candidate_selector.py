from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24199_candidate_selector import payload_sha256
from scripts.preregister_v24199_candidate_selector import (
    CONTROL_FILES,
    DECISION_FIELDS,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24199CandidateSelectorTests(unittest.TestCase):
    def test_protocol_freezes_bijective_inheritance_without_build_or_launch(self) -> None:
        with mock.patch(
            "scripts.preregister_v24199_candidate_selector.protected_processes",
            return_value={},
        ):
            selector, value = build_protocol(
                ROOT, created_at_unix=1, require_pristine=False
            )
        contract = value["inheritance_contract"]
        self.assertEqual(contract["slot_count"], 24)
        self.assertTrue(contract["one_legal_vector_maps_to_exactly_one_slot"])
        self.assertTrue(contract["missing_integrated_candidate_waits_without_fallback"])
        self.assertFalse(
            contract["score_rank_last_go_or_best_observed_selection_allowed"]
        )
        self.assertFalse(
            value["authorization"]["candidate_code_build_merge_or_freeze_generation"]
        )
        self.assertFalse(value["authorization"]["shared_api_lease_acquire"])
        self.assertFalse(
            value["authorization"]["benchmark_forward_or_full220_launch"]
        )
        self.assertEqual(
            selector["candidate_set_manifest_sha256"],
            contract["slot_manifest_sha256"],
        )
        self.assertEqual(
            selector["candidate_inheritance_rule_sha256"],
            contract["inheritance_rule_sha256"],
        )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        self.assertEqual(
            value["decision_contract_sha256"],
            payload_sha256({key: value[key] for key in DECISION_FIELDS}),
        )

    def test_parent_drift_fails_closed(self) -> None:
        with mock.patch(
            "scripts.preregister_v24199_candidate_selector.PARENT_PROTOCOL_SHA256",
            "0" * 64,
        ), self.assertRaisesRegex(RuntimeError, "drifted"):
            build_protocol(ROOT, created_at_unix=1, require_pristine=False)

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            publish_new(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                publish_new(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
