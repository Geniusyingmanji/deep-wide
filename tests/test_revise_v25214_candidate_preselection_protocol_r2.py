from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import revise_v25214_candidate_preselection_protocol_r2 as target  # noqa: E402


class V25214CandidatePreselectionProtocolR2Tests(unittest.TestCase):
    def test_parent_v1_hash_is_exact(self) -> None:
        self.assertEqual(
            target.base.base.sha256(target.PARENT), target.EXPECTED_PARENT_SHA256
        )

    def test_only_crates_predicate_and_append_only_metadata_change(self) -> None:
        parent = target.v1.validate_design(
            __import__("json").loads(
                target.base.base._ordinary(target.PARENT).read_text(encoding="utf-8")
            )
        )
        revised = target.build_revision(now=1)
        self.assertEqual(
            revised["source_specs"]["single_authority_exact_record"][
                "selection_predicate"
            ],
            target.CORRECTED_CRATES_PREDICATE,
        )
        for stratum in target.v1.SAMPLING_STRATA[1:]:
            self.assertEqual(revised["source_specs"][stratum], parent["source_specs"][stratum])
        self.assertEqual(revised["authorization"], parent["authorization"])

    def test_resealed_parent_predicate_authority_or_credit_tamper_fails(self) -> None:
        value = target.build_revision(now=1)
        for kind in ("parent", "predicate", "authority", "credit"):
            changed = copy.deepcopy(value)
            if kind == "parent":
                changed["parent_design"]["sha256"] = "0" * 64
            elif kind == "predicate":
                changed["source_specs"]["single_authority_exact_record"][
                    "selection_predicate"
                ] = "non_yanked"
            elif kind == "authority":
                changed["authorization"]["public_index_snapshot_network_access"] = True
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_revision(changed)


if __name__ == "__main__":
    unittest.main()
