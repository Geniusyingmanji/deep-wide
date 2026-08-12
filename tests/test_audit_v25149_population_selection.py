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

from scripts import audit_v25149_population_selection as target  # noqa: E402


class V25149PopulationSelectionAuditTests(unittest.TestCase):
    def test_aggregate_only_zero_hit_audit(self) -> None:
        completed = [
            mock.Mock(stdout="parent\n"),
            *[mock.Mock(stdout="") for _ in range(20)],
        ]
        with mock.patch.object(
            target.parent.subprocess, "run", side_effect=completed
        ):
            value = target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        self.assertEqual(value["role"], target.ROLE)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["identity_history_zero_hit_count"], 20)
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

    def test_resealed_plaintext_or_mapping_claim_tamper_fails(self) -> None:
        completed = [
            mock.Mock(stdout="parent\n"),
            *[mock.Mock(stdout="") for _ in range(20)],
        ]
        with mock.patch.object(
            target.parent.subprocess, "run", side_effect=completed
        ):
            value = target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        for name in (
            "identity_plaintext_or_item_hash_persisted",
            "clue_to_identity_mapping_persisted",
        ):
            changed = copy.deepcopy(value)
            changed[name] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
