from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import correct_v24762_v24759_source_provenance as target  # noqa: E402


class V24762V24759SourceProvenanceCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_correction(
            now=0, require_clean=False, require_pristine=False
        )

    def test_network_misstatement_is_corrected_without_changing_counts(self) -> None:
        correction = self.value["correction"]
        self.assertFalse(correction["original_statement_valid"])
        self.assertEqual(
            correction["v24758_population_design"][
                "immutable_ror_record_https_reads_code_path_implied"
            ],
            3_482,
        )
        self.assertEqual(correction["v24758_population_design"]["model_calls"], 0)
        self.assertFalse(correction["capacity_counts_or_minimum_cap_changed"])

    def test_population_is_recertified_and_old_protocol_is_superseded(self) -> None:
        recertification = self.value["recertification"]
        supersession = self.value["supersession"]
        self.assertTrue(
            recertification[
                "v24760_population_recertified_under_corrected_provenance"
            ]
        )
        self.assertTrue(recertification["v24760_private_file_hash_matches_public_design"])
        self.assertFalse(supersession["v24759_original_successor_authorization_valid"])
        self.assertFalse(supersession["v24761_protocol_authorizes_successor_use"])
        self.assertTrue(supersession["v24761_protocol_was_inert_and_never_activated"])

    def test_resealed_launch_tamper_fails(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["authorization"]["activation_or_external_launch"] = True
        altered.pop("correction_payload_sha256")
        altered["correction_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_correction(altered)


if __name__ == "__main__":
    unittest.main()
