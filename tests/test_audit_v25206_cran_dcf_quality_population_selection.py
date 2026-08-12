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

from scripts import audit_v25206_cran_dcf_quality_population_selection as target  # noqa: E402


class V25206PopulationSelectionTests(unittest.TestCase):
    @staticmethod
    def _runs(*, hit: bool = False) -> list[mock.Mock]:
        values = [mock.Mock(stdout="parent\n")]
        values.extend(
            mock.Mock(stdout="commit\n" if hit and index == 0 else "")
            for index in range(20)
        )
        return values

    def test_fresh_enriched_population_discloses_scope_and_nonreuse(self) -> None:
        with mock.patch.object(target.base.subprocess, "run", side_effect=self._runs()):
            value = target.build_audit(
                [f"fresh-package-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["identity_history_zero_hit_count"], 20)
        self.assertTrue(
            value[
                "preselection_requires_license_literal_pipe_and_nonempty_needs_compilation"
            ]
        )
        self.assertFalse(value["preselection_is_unconditional_natural_population"])
        self.assertFalse(value["v25203_population_reuse"])
        encoded = json.dumps(value)
        self.assertNotIn("fresh-package-0", encoded)

    def test_history_overlap_fails_closed(self) -> None:
        with mock.patch.object(
            target.base.subprocess, "run", side_effect=self._runs(hit=True)
        ):
            with self.assertRaises(RuntimeError):
                target.build_audit(
                    [f"fresh-package-{index}" for index in range(20)],
                    parent_commit="parent",
                    now=1,
                )

    def test_resealed_reuse_credit_or_authority_tamper_fails(self) -> None:
        with mock.patch.object(target.base.subprocess, "run", side_effect=self._runs()):
            value = target.build_audit(
                [f"fresh-package-{index}" for index in range(20)],
                parent_commit="parent",
                now=1,
            )
        for name in (
            "v25203_population_reuse",
            "entropy_or_information_gain_assigns_signed_credit",
            "external_forward_evaluator_deepwidebench_or_sota_authorized",
        ):
            changed = copy.deepcopy(value)
            changed[name] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
