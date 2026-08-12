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

from scripts import (  # noqa: E402
    audit_v25182_quote_aware_population_selection as target,
)


class V25182QuoteAwarePopulationSelectionTests(unittest.TestCase):
    @staticmethod
    def _zero_hit() -> list[mock.Mock]:
        return [
            mock.Mock(stdout="parent\n"),
            *[mock.Mock(stdout="") for _ in range(20)],
        ]

    def test_aggregate_only_zero_hit_freeze_has_no_runtime_authority(self):
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
        self.assertTrue(value["identity_is_visible_task_input_not_hidden_mapping"])
        self.assertFalse(value["prior_external_population_reuse"])
        self.assertFalse(
            value[
                "external_protocol_activation_evaluator_deepwidebench_or_sota_authorized"
            ]
        )
        self.assertNotIn("identity-0", json.dumps(value))

    def test_nonzero_history_hit_fails_closed(self):
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

    def test_resealed_authority_content_reuse_or_credit_tamper_fails(self):
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
            "prior_external_population_reuse",
            "binding_successor_design",
            "vertical_binding_policy_change",
            "external_protocol_activation_evaluator_deepwidebench_or_sota_authorized",
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
