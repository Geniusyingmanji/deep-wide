from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25047_pypi_current_record_representation as target  # noqa: E402


def raw(
    *,
    name: str = "alpha-package",
    version: str = "2.0.0",
    requires_python: str | None = ">=3.10",
) -> str:
    return json.dumps(
        {
            "info": {
                "name": name,
                "version": version,
                "requires_python": requires_python,
            },
            "releases": {
                "1.0.0": [{"upload_time_iso_8601": "2024-01-01T00:00:00Z"}],
                version: [
                    {"upload_time_iso_8601": "2026-05-03T12:00:00Z"},
                    {"upload_time": "2026-05-02T09:00:00"},
                ],
            },
        },
        sort_keys=True,
    )


class V25047PyPICurrentRecordRepresentationTests(unittest.TestCase):
    def test_current_record_binds_identity_version_date_and_python(self) -> None:
        record = target.parse_current_record(raw(), visible_project="alpha_package")
        self.assertEqual(record["Package"], "alpha-package")
        self.assertEqual(record["Latest version"], "2.0.0")
        self.assertEqual(record["Latest release date (YYYY-MM-DD)"], "2026-05-02")
        self.assertEqual(record["Requires-Python"], ">=3.10")

    def test_missing_requires_python_is_unknown_not_failure(self) -> None:
        record = target.parse_current_record(
            raw(requires_python=None), visible_project="alpha-package"
        )
        self.assertEqual(record["Requires-Python"], "Unknown")

    def test_candidate_and_control_have_equal_exact_character_budget(self) -> None:
        result = target.build_representations(
            raw(), visible_project="alpha-package", total_chars=12_000
        )
        self.assertEqual(len(result["control_evidence"]), 12_000)
        self.assertEqual(len(result["candidate_evidence"]), 12_000)
        self.assertIn("[IDENTITY-BOUND PYPI CURRENT-RELEASE RECORD]", result["candidate_evidence"])
        self.assertNotIn("[IDENTITY-BOUND PYPI CURRENT-RELEASE RECORD]", result["control_evidence"])
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["bound_field_count"], 4)
        self.assertFalse(receipt["contains_project_field_value_raw_page_url_prediction_answer_hash_or_credential"])

    def test_identity_mismatch_or_missing_current_release_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            target.parse_current_record(raw(), visible_project="beta-package")
        value = json.loads(raw())
        value["releases"].pop("2.0.0")
        with self.assertRaises(ValueError):
            target.parse_current_record(
                json.dumps(value), visible_project="alpha-package"
            )

    def test_old_release_date_cannot_be_spliced_into_current_record(self) -> None:
        record = target.parse_current_record(raw(), visible_project="alpha-package")
        self.assertNotEqual(record["Latest release date (YYYY-MM-DD)"], "2024-01-01")

    def test_malformed_or_unsafe_fields_fail_closed(self) -> None:
        for changed in (
            raw(name="alpha|package"),
            raw(version="bad|version"),
            "not json",
        ):
            with self.subTest(changed=changed[:30]), self.assertRaises(ValueError):
                target.parse_current_record(
                    changed, visible_project="alpha-package"
                )

    def test_nested_receipt_tamper_fails_closed(self) -> None:
        result = target.build_representations(
            raw(), visible_project="alpha-package", total_chars=12_000
        )
        changed = copy.deepcopy(result["content_free_receipt"])
        changed["date_bound_to_releases_info_version"] = False
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_receipt(changed)


if __name__ == "__main__":
    unittest.main()
