from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.publish_v24213_entropy_recovery import (  # noqa: E402
    build_recovery_publication,
)


class PublishV24213EntropyRecoveryTests(unittest.TestCase):
    def test_recovery_wraps_base_publication_without_reusing_failed_state(self) -> None:
        base = {
            "artifact_version": 1,
            "role": "v24212_selected_entropy_component_publication",
            "label_blind": True,
            "publication_payload_sha256": "",
        }
        base["publication_payload_sha256"] = payload_sha256(
            {key: value for key, value in base.items() if key != "publication_payload_sha256"}
        )
        with mock.patch(
            "scripts.publish_v24213_entropy_recovery.build_selected_publication",
            return_value=base,
        ):
            value = build_recovery_publication({}, None, {}, {}, {}, {})
        self.assertEqual(
            value["role"],
            "v24213_selected_entropy_component_recovery_publication",
        )
        self.assertFalse(
            value[
                "v24212_activation_state_or_candidate_reused_overwritten_or_resumed"
            ]
        )
        self.assertEqual(
            value["recovery_delta"],
            "validate_v24210_frozen_false_field_under_its_exact_registered_name",
        )


if __name__ == "__main__":
    unittest.main()
