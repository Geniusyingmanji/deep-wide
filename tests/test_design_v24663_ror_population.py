from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24663_ror_population as design  # noqa: E402


class V24663PopulationTests(unittest.TestCase):
    def test_historical_vector_adds_all_v24651_entities(self):
        visible, canonical = design.historical_entities()
        self.assertEqual(len(visible), 4_528)
        self.assertEqual(len(canonical), 4_528)
        self.assertTrue({e for g in design.V24651 for e in g}.issubset(visible))

    def test_fixed_immutable_tree_and_slice(self):
        self.assertEqual(design.COMMIT, "aab1443afefefa8460e69ab01bccceff0a8544d4")
        self.assertEqual(design.VERSION, "v2.11")
        self.assertEqual((design.SLICE_START, design.SLICE_STOP), (0, 3_482))
        self.assertEqual(design.SELECTED_COUNT, 48)

    def test_parent_grants_design_not_launch(self):
        value = {
            "role": "v24662_strict_support_closure_build_audit",
            "audit_valid": True,
            "findings": [],
            "authorization": {
                "fresh_disjoint_external_population_and_protocol_design": True,
                "fresh_external_activation_or_launch": False,
                "exact220": False,
            },
            "mechanism": {"v24659_v24660_design_only_precursor_superseded": True},
        }
        value["audit_payload_sha256"] = design.payload_sha256(value)
        with patch.object(design, "_read", return_value=value):
            self.assertTrue(design._parent_valid())

    def test_selection_rejects_historical_canonical(self):
        historical = {"alpha org"}
        entry = {"path": "012345678.json", "sha": "a" * 40}
        raw = b"{}"
        value = {
            "status": "active",
            "id": "https://ror.org/012345678",
            "names": [{"value": "Alpha Org", "types": ["ror_display"]}],
            "locations": [{"geonames_details": {"country_code": "US"}}],
        }
        candidate = design.prior._record_candidate(
            entry, raw, value, historical_canonical=historical,
            canonical=lambda value: value.casefold(),
        )
        self.assertIsNone(candidate)


if __name__ == "__main__":
    unittest.main()
