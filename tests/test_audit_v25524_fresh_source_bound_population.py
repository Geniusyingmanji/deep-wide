from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25524_fresh_source_bound_population as target  # noqa: E402


class V25524FreshSourceBoundPopulationAuditTests(unittest.TestCase):
    def test_build_barrier_hashes_commit_and_namespace_block_are_exact(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertTrue(
            all(
                target.base.sha256(path) == digest
                for path, digest in target.FIXED_HASHES.items()
            )
        )
        history = set(target.base._git("rev-list", "HEAD").splitlines())
        self.assertIn(target.IMPLEMENTATION_COMMIT, history)
        self.assertEqual(
            target._namespace_block(),
            [identity for pair in target.population.PAIRS for identity in pair],
        )

    def test_population_audit_passes_without_external_effect(self) -> None:
        with mock.patch.object(target, "_tracked", return_value=True):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["selection"]["pair_count"], 20)
        self.assertEqual(value["selection"]["row_identity_count"], 40)
        self.assertEqual(
            value["selection"][
                "consumed_v25509_v25516_row_identity_overlap_count"
            ],
            0,
        )
        self.assertFalse(value["authorization"]["external_forward"])

    def test_population_vectors_and_source_bound_gate_are_frozen(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        self.assertEqual(
            value["selection"]["pair_vector_sha256"],
            target.population.EXPECTED_PAIR_VECTOR_SHA256,
        )
        self.assertEqual(
            value["selection"]["task_vector_sha256"],
            target.population.EXPECTED_TASK_VECTOR_SHA256,
        )
        gate = value["mechanism_gate"]
        self.assertEqual(gate["minimum_exact_iana_url_page_tasks"], 3)
        self.assertEqual(gate["minimum_evidence_closed_observation_tasks"], 3)
        self.assertEqual(gate["minimum_material_candidate_tasks"], 2)

    def test_resealed_overlap_launch_or_credit_tamper_fails(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        for kind in ("overlap", "launch", "credit"):
            changed = copy.deepcopy(value)
            if kind == "overlap":
                changed["selection"][
                    "consumed_v25509_v25516_row_identity_overlap_count"
                ] = 1
            elif kind == "launch":
                changed["authorization"]["external_forward"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
