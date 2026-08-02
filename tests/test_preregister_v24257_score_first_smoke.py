from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import preregister_v24257_score_first_smoke as target
from scripts.run_v24257_score_first_smoke import payload_sha256


INACTIVE_LEASE = {
    "present": True,
    "active": False,
    "ordinary": True,
    "record_valid": True,
    "owner": None,
    "purpose": None,
    "pid": None,
    "lock_holder_pids": [],
}


class PreregisterV24257ScoreFirstSmokeTests(unittest.TestCase):
    def test_protocol_is_bounded_label_blind_and_content_free(self) -> None:
        with mock.patch.object(
            target, "lease_observation", return_value=INACTIVE_LEASE
        ):
            value = target.build_protocol(
                target.ROOT,
                created_at_unix=1,
                require_pristine=False,
            )

        self.assertTrue(value["label_blind"])
        self.assertEqual(
            value["task_contract"]["runtime_boundary"],
            ["opaque_id", "question"],
        )
        self.assertFalse(
            value["task_contract"][
                "category_question_type_split_mapping_gold_score_used_for_selection"
            ]
        )
        self.assertEqual(value["limits"]["wall_seconds"], 600)
        self.assertEqual(value["limits"]["model_calls"], 3)
        self.assertEqual(value["limits"]["search_queries"], 8)
        self.assertEqual(value["limits"]["fetch_targets"], 16)
        self.assertEqual(value["execution"]["executor_concurrency"], 1)
        self.assertFalse(value["authorization"]["official_evaluator_call"])
        self.assertFalse(value["authorization"]["paired_dev64_or_full220_launch"])
        self.assertEqual(
            set(value["control_surface"]["manifest"]),
            {str(path) for path in target.CONTROL_FILES},
        )
        unsigned = dict(value)
        seal = unsigned.pop("decision_contract_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        encoded = json.dumps(value, sort_keys=True)
        self.assertIsNone(target.OPAQUE_LITERAL.search(encoded))

    def test_active_shared_lease_fails_closed(self) -> None:
        active = dict(INACTIVE_LEASE, active=True, owner="another_owner")
        with mock.patch.object(
            target, "lease_observation", return_value=active
        ), self.assertRaisesRegex(RuntimeError, "lease is active"):
            target.build_protocol(
                target.ROOT,
                created_at_unix=1,
                require_pristine=False,
            )

    def test_missing_control_file_fails_closed(self) -> None:
        controls = (*target.CONTROL_FILES, Path("tests/absent_v24257_control.py"))
        with mock.patch.object(target, "CONTROL_FILES", controls), mock.patch.object(
            target, "lease_observation", return_value=INACTIVE_LEASE
        ), self.assertRaisesRegex(RuntimeError, "expected ordinary file"):
            target.build_protocol(
                target.ROOT,
                created_at_unix=1,
                require_pristine=False,
            )

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = Path("results/protocol.json")
            path = root / relative
            with mock.patch.object(target, "ROOT", root), mock.patch.object(
                target, "OUTPUT", relative
            ):
                target.publish_new(path, {"ok": True})
                with self.assertRaises(FileExistsError):
                    target.publish_new(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
