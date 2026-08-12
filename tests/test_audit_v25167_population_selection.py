from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v25167_population_selection as target  # noqa: E402


class V25167PopulationSelectionAuditTests(unittest.TestCase):
    def _zero_hit(self) -> list[mock.Mock]:
        return [
            mock.Mock(stdout="parent\n"),
            *[mock.Mock(stdout="") for _ in range(20)],
        ]

    def test_aggregate_only_zero_hit_freeze_has_no_runtime_authority(self) -> None:
        with mock.patch.object(
            target.parent.subprocess, "run", side_effect=self._zero_hit()
        ):
            value = target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["identity_history_zero_hit_count"], 20)
        self.assertTrue(value["selection_uses_repository_history_only"])
        self.assertFalse(value["vertical_binding_policy_change"])
        self.assertFalse(
            value[
                "external_protocol_activation_evaluator_or_deepwidebench_authorized"
            ]
        )
        self.assertFalse(
            value[
                "v25141_v25145_v25149_v25153_v25157_v25160_population_reuse"
            ]
        )
        self.assertNotIn("identity-0", json.dumps(value))

    def test_nonzero_history_hit_fails_closed(self) -> None:
        completed = [
            mock.Mock(stdout="parent\n"),
            mock.Mock(stdout="commit\n"),
            *[mock.Mock(stdout="") for _ in range(19)],
        ]
        with mock.patch.object(
            target.parent.subprocess, "run", side_effect=completed
        ), self.assertRaises(RuntimeError):
            target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )

    def test_resealed_authority_content_reuse_or_policy_tamper_fails(self) -> None:
        with mock.patch.object(
            target.parent.subprocess, "run", side_effect=self._zero_hit()
        ):
            value = target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        for name in (
            "identity_plaintext_or_item_hash_persisted",
            "clue_to_identity_mapping_persisted",
            "network_endpoint_page_value_model_or_evaluator_access",
            "v25141_v25145_v25149_v25153_v25157_v25160_population_reuse",
            "vertical_binding_policy_change",
            "external_protocol_activation_evaluator_or_deepwidebench_authorized",
            "entropy_or_information_gain_assigns_signed_credit",
        ):
            changed = copy.deepcopy(value)
            changed[name] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
