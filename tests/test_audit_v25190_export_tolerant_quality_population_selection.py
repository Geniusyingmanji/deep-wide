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
    audit_v25190_export_tolerant_quality_population_selection as target,
)


class V25190PopulationSelectionTests(unittest.TestCase):
    @staticmethod
    def _zero_hit() -> list[mock.Mock]:
        return [mock.Mock(stdout="parent\n"), *[mock.Mock(stdout="") for _ in range(20)]]

    def test_fresh_enriched_population_discloses_scope_and_nonreuse(self):
        with mock.patch.object(
            target.base.subprocess, "run", side_effect=self._zero_hit()
        ):
            value = target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["preselection_enriched_for_license_literal_pipe"])
        self.assertFalse(value["preselection_is_unconditional_natural_population"])
        self.assertFalse(value["v25187_population_reuse"])
        self.assertFalse(
            value["external_forward_evaluator_deepwidebench_or_sota_authorized"]
        )
        self.assertNotIn("identity-0", json.dumps(value))

    def test_history_overlap_fails_closed(self):
        completed = [
            mock.Mock(stdout="parent\n"),
            mock.Mock(stdout="commit\n"),
            *[mock.Mock(stdout="") for _ in range(19)],
        ]
        with mock.patch.object(
            target.base.subprocess, "run", side_effect=completed
        ), self.assertRaises(RuntimeError):
            target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )

    def test_resealed_reuse_scope_credit_or_authority_tamper_fails(self):
        with mock.patch.object(
            target.base.subprocess, "run", side_effect=self._zero_hit()
        ):
            value = target.build_audit(
                [f"identity-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        for name in (
            "v25187_population_reuse",
            "preselection_is_unconditional_natural_population",
            "external_forward_evaluator_deepwidebench_or_sota_authorized",
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
