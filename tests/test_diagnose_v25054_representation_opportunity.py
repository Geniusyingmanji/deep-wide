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

from scripts import diagnose_v25054_representation_opportunity as target  # noqa: E402


class V25054RepresentationOpportunityTests(unittest.TestCase):
    def test_actual_frozen_content_free_evidence_supports_integration_design(self) -> None:
        value = target.build_diagnosis(now=1)
        opportunity = value["v25030_production_opportunity"]
        self.assertEqual(opportunity["projected_pages"], 1534)
        self.assertEqual(opportunity["characters_beyond_5k_prefix"], 23595703)
        self.assertEqual(opportunity["old_identity_required_projector_exposed_pages"], 0)
        self.assertTrue(
            value["decision"][
                "page_self_identity_production_integration_design_supported"
            ]
        )
        self.assertFalse(
            value["decision"]["new_exact220_launch_authorized_by_diagnosis_alone"]
        )

    def test_resealed_aggregate_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for mutation in ("pages", "launch"):
            changed = copy.deepcopy(value)
            if mutation == "pages":
                changed["v25030_production_opportunity"]["projected_pages"] += 1
            else:
                changed["decision"]["new_exact220_launch_authorized_by_diagnosis_alone"] = True
            unsigned = copy.deepcopy(changed)
            unsigned.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.payload_sha256(unsigned)
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)

    def test_publication_is_create_exclusive_and_rejects_symlink(self) -> None:
        value = target.build_diagnosis(now=1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "diagnosis.json"
            target.publish_exclusive(output, value)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(output, value)

            symlink = root / "symlink.json"
            symlink.symlink_to(output)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(symlink, value)


if __name__ == "__main__":
    unittest.main()
