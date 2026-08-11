from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25048_atomic_pypi_representation_contract as contract  # noqa: E402
from scripts import audit_v25048_persisted_snapshot as audit  # noqa: E402


class V25048PersistedSnapshotAuditTests(unittest.TestCase):
    def _rows(self, freeze_sha256: str) -> list[dict]:
        values = []
        for index, project in enumerate(contract.PROJECTS):
            record = json.loads(
                json.dumps(
                    {
                        "Package": project,
                        "Latest version": "1.0.0",
                        "Latest release date (YYYY-MM-DD)": "2026-08-01",
                        "Requires-Python": ">=3.9",
                    },
                    sort_keys=True,
                )
            )
            values.append(
                {
                    "index": index,
                    "opaque_id": contract.task_vector()[index]["opaque_id"],
                    "project": project,
                    "endpoint_sha256": hashlib.sha256(
                        contract.endpoint_vector()[index].encode()
                    ).hexdigest(),
                    "raw_response_sha256": "1" * 64,
                    "raw_response_bytes": 100,
                    "http_status": 200,
                    "record": record,
                    "prediction_freeze_sha256": freeze_sha256,
                    "published_after_prediction_freeze": True,
                }
            )
        return values

    def test_sorted_nested_keys_are_order_independent_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            freeze = root / contract.PREDICTION_FREEZE
            freeze.parent.mkdir(parents=True)
            freeze.write_text("{}\n", encoding="utf-8")
            rows = self._rows(contract.sha256(freeze))
            with mock.patch.object(audit, "ROOT", root):
                self.assertEqual(len(audit.validate_rows(rows)), 20)

    def test_extra_record_key_or_freeze_hash_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            freeze = root / contract.PREDICTION_FREEZE
            freeze.parent.mkdir(parents=True)
            freeze.write_text("{}\n", encoding="utf-8")
            rows = self._rows(contract.sha256(freeze))
            with mock.patch.object(audit, "ROOT", root):
                for mutation in ("extra", "freeze"):
                    changed = copy.deepcopy(rows)
                    if mutation == "extra":
                        changed[0]["record"]["extra"] = "forbidden"
                    else:
                        changed[0]["prediction_freeze_sha256"] = "0" * 64
                    with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                        audit.validate_rows(changed)


if __name__ == "__main__":
    unittest.main()
