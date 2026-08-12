from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    revise_v25234_local_package_shadow_population_r2 as target,
)


class V25234R2PopulationDesignCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_revision(now=1)

    def test_parent_design_is_exactly_hash_bound(self) -> None:
        self.assertEqual(
            target.parent.base.sha256(target.PARENT), target.PARENT_SHA256
        )

    def test_only_aggregate_probe_counts_are_corrected(self) -> None:
        correction = self.value["correction"]
        self.assertEqual(correction["old_counts"]["single_hyphen_alpha"], 353)
        self.assertEqual(
            correction["corrected_counts"]["single_hyphen_alpha"], 351
        )
        self.assertEqual(correction["old_counts"]["excluded_other"], 84)
        self.assertEqual(correction["corrected_counts"]["excluded_other"], 86)
        self.assertEqual(correction["misclassified_single_hyphen_package_count"], 2)
        self.assertFalse(
            correction["identity_plaintext_or_item_hash_opened_emitted_or_persisted"]
        )

    def test_all_contracts_and_authority_are_unchanged(self) -> None:
        frozen = target.parent.build_design(now=0)
        self.assertEqual(
            self.value["unchanged_contracts"],
            {
                "source_contract": frozen["source_contract"],
                "morphology_contract": frozen["morphology_contract"],
                "selection_contract": frozen["selection_contract"],
                "task_contract": frozen["task_contract"],
                "future_shadow_gate": frozen["future_shadow_gate"],
            },
        )
        self.assertEqual(self.value["authorization"], frozen["authorization"])
        self.assertFalse(
            self.value["authorization"]
            ["formal_dpkg_query_history_scan_or_population_freeze"]
        )

    def test_resealed_count_launch_or_identity_tamper_fails(self) -> None:
        for kind in ("count", "launch", "identity"):
            changed = copy.deepcopy(self.value)
            if kind == "count":
                changed["correction"]["corrected_counts"][
                    "single_hyphen_alpha"
                ] = 353
            elif kind == "launch":
                changed["authorization"][
                    "formal_dpkg_query_history_scan_or_population_freeze"
                ] = True
            else:
                changed["correction"][
                    "identity_plaintext_or_item_hash_opened_emitted_or_persisted"
                ] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.parent.base.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_revision(changed)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "revision.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
