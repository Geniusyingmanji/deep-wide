from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24978_pypi_release_file_compactor as compact  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


PROJECT = "release-file-demo"
RAW = ("raw long pypi prefix\n" * 2000)[:16_000]


def page(*, name: str = PROJECT, version: str = "2.0", requires_python=">=3.10"):
    return {
        "url": f"https://pypi.org/pypi/{PROJECT}/json",
        "text": json.dumps(
            {
                "info": {
                    "name": name,
                    "version": version,
                    "requires_python": requires_python,
                },
                "noise": "x" * 20_000,
                "releases": {
                    version: [
                        {"upload_time_iso_8601": "2026-08-03T12:00:00Z", "size": 200},
                        {"upload_time": "2026-08-01T10:00:00", "size": 450},
                    ]
                },
            }
        ),
    }


class V24978PyPIReleaseFileCompactorTests(unittest.TestCase):
    def build(self, source=None):
        return compact.build_compact_evidence(
            [source or page()], RAW, project=PROJECT, total_chars=len(RAW)
        )

    def test_extracts_current_version_late_file_fields(self) -> None:
        record = compact.extract_record(page(), project=PROJECT)
        self.assertEqual(
            record,
            {
                "latest_version": "2.0",
                "requires_python": ">=3.10",
                "release_file_count": "2",
                "first_upload_date": "2026-08-01",
                "largest_file_size_bytes": "450",
            },
        )

    def test_compact_record_changes_evidence_under_same_cap(self) -> None:
        result = self.build()
        self.assertEqual(len(result["evidence"]), len(RAW))
        self.assertNotEqual(result["evidence"], RAW)
        self.assertIn("Current-version file count: 2", result["evidence"])
        self.assertIn("Current-version largest file size (bytes): 450", result["evidence"])
        compact.validate_receipt(result["receipt"], total_chars=len(RAW))

    def test_missing_requires_python_is_explicit_unknown(self) -> None:
        record = compact.extract_record(page(requires_python=None), project=PROJECT)
        self.assertEqual(record["requires_python"], compact.UNKNOWN)
        self.assertEqual(self.build(page(requires_python=None))["receipt"]["unknown_field_count"], 1)

    def test_wrong_url_or_primary_identity_fails_closed(self) -> None:
        wrong_url = page()
        wrong_url["url"] = "https://pypi.org/pypi/other/json"
        with self.assertRaises(ValueError):
            self.build(wrong_url)
        with self.assertRaises(ValueError):
            self.build(page(name="other"))

    def test_missing_empty_or_malformed_current_release_fails_closed(self) -> None:
        for mutation in ("missing", "empty", "bad_size", "bad_date"):
            source = page()
            value = json.loads(source["text"])
            if mutation == "missing":
                value["releases"].pop("2.0")
            elif mutation == "empty":
                value["releases"]["2.0"] = []
            elif mutation == "bad_size":
                value["releases"]["2.0"][0]["size"] = True
            else:
                value["releases"]["2.0"][0]["upload_time_iso_8601"] = "not-a-date"
            source["text"] = json.dumps(value)
            with self.assertRaises(ValueError, msg=mutation):
                self.build(source)

    def test_page_vector_budget_and_receipt_tamper_fail(self) -> None:
        with self.assertRaises(ValueError):
            compact.build_compact_evidence([], RAW, project=PROJECT, total_chars=len(RAW))
        result = self.build()
        changed = copy.deepcopy(result["receipt"])
        changed["unique_bound_field_count"] = 4
        with self.assertRaises(ValueError):
            compact.validate_receipt(changed, total_chars=len(RAW))

    def test_receipt_is_counts_only(self) -> None:
        encoded = json.dumps(self.build()["receipt"], sort_keys=True)
        for forbidden in (PROJECT, "2.0", "2026-08-01", "450", "https://"):
            self.assertNotIn(forbidden, encoded)

    def test_source_is_pure_label_blind_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v24978_pypi_release_file_compactor.py"
        imports = []
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        forbidden = ("requests", "socket", "subprocess", "urllib.request", "evaluator")
        self.assertFalse(any(any(token in name for token in forbidden) for name in imports))
        self.assertEqual(semantic_audit._accesses(path, ROOT), [])
        self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])


if __name__ == "__main__":
    unittest.main()
