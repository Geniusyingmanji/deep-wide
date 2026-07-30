from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.preregister_v24188_parent_closure import (
    CONTROL_FILES,
    DEFAULT_PROTOCOL,
    DEFAULT_RESULT,
    build_protocol,
    payload_sha,
    validate_protocol,
)


class PreregisterV24188ParentClosureTests(unittest.TestCase):
    def test_protocol_explicitly_corrects_only_overbroad_wording(self) -> None:
        root = Path(__file__).parents[1]
        with patch(
            "scripts.preregister_v24188_parent_closure._v24187_inputs",
            return_value={},
        ):
            value = build_protocol(
                root, created_at_unix=1, require_pristine_result=False
            )
        self.assertTrue(
            value["correction_contract"][
                "v24187_parent_control_manifest_live_replay_is_not_implemented"
            ]
        )
        self.assertTrue(
            value["correction_contract"][
                "v24188_supersedes_only_the_overbroad_control_bytes_wording"
            ]
        )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        self.assertEqual(
            value["control_surface"]["manifest_sha256"],
            payload_sha(value["control_surface"]["manifest"]),
        )
        self.assertFalse(value["authorization"]["v24187_source_or_protocol_modification"])
        self.assertFalse(
            value["authorization"]["benchmark_model_search_fetch_evaluator_or_api_call"]
        )

    def test_live_protocol_rebuilds_when_published(self) -> None:
        root = Path(__file__).parents[1]
        path = root / DEFAULT_PROTOCOL
        if not path.exists():
            self.skipTest("protocol not published yet")
        self.assertEqual(
            validate_protocol(root, path)["value"]["role"],
            "v24188_parent_control_closure_preregistration",
        )

    def test_result_pristine_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in CONTROL_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            result = root / DEFAULT_RESULT
            result.parent.mkdir(parents=True, exist_ok=True)
            result.write_text("{}", encoding="utf-8")
            with patch(
                "scripts.preregister_v24188_parent_closure._v24187_inputs",
                return_value={},
            ), self.assertRaises(FileExistsError):
                build_protocol(root, created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
