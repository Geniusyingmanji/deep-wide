from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v25064_three_run_strategy as target  # noqa: E402


class V25064ThreeRunStrategyAuditTests(unittest.TestCase):
    def synthetic(self) -> dict:
        with mock.patch.object(target, "_git") as git, mock.patch.object(
            target, "_tracked", return_value=True
        ), mock.patch.object(target, "_watchers") as watchers:
            git.side_effect = lambda *args: (
                "frozen-head"
                if args == ("rev-parse", "HEAD") or args == ("rev-parse", "target/main")
                else ""
            )
            watchers.return_value = {
                str(pid): {
                    "present": True,
                    "start_ticks": ticks,
                    "matches_frozen_identity": True,
                }
                for pid, ticks in target.PROTECTED_WATCHERS.items()
            }
            return target.build_audit(now=1)

    def test_clean_aggregate_only_audit_passes(self) -> None:
        value = self.synthetic()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(all(value["checks"].values()))

    def test_authority_stays_build_only(self) -> None:
        authorization = self.synthetic()["authorization"]
        self.assertTrue(authorization["source_record_binding_build_design"])
        self.assertFalse(authorization["fresh_external_protocol_publication"])
        self.assertFalse(authorization["fresh_external_launch"])
        self.assertFalse(authorization["new_exact220_launch"])

    def test_resealed_watcher_or_authority_tamper_fails(self) -> None:
        for mutation in ("watcher", "launch", "finding"):
            changed = copy.deepcopy(self.synthetic())
            if mutation == "watcher":
                changed["protected_watchers"]["795336"][
                    "matches_frozen_identity"
                ] = False
            elif mutation == "launch":
                changed["authorization"]["new_exact220_launch"] = True
            else:
                changed["findings"] = ["must-fail"]
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_publication_is_create_exclusive(self) -> None:
        value = self.synthetic()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit.json"
            target.publish_exclusive(path, value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, value)


if __name__ == "__main__":
    unittest.main()
