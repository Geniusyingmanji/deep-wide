from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24929_unicode_total_neutral_contract as contract  # noqa: E402
from scripts import control_v24931_unicode_total_neutral_activation as activation  # noqa: E402
from scripts import run_v24929_unicode_total_neutral_gate as parent_runner  # noqa: E402
from scripts import run_v24931_unicode_total_neutral_gate as launcher  # noqa: E402


class V24931UnicodeTotalNeutralActivationTests(unittest.TestCase):
    def test_activation_binds_role_adapter_only(self) -> None:
        with (
            patch.object(activation.parent, "_active_conflicts", return_value=[]),
            patch.object(activation, "_tracked", return_value=True),
        ):
            value = activation.build_activation(now=1)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["binding"]["authorization_role_adapter_only"])
        self.assertFalse(
            value["binding"][
                "algorithm_task_vector_prompt_model_search_fetch_or_budget_changed"
            ]
        )

    def test_launcher_returns_frozen_protocol_and_corrected_start(self) -> None:
        with (
            patch.object(activation.parent, "_active_conflicts", return_value=[]),
            patch.object(activation, "_tracked", return_value=True),
        ):
            activation_value = activation.build_activation(now=1)
        inherited_read = launcher.control._read

        def staged_read(path: Path) -> dict:
            if path == ROOT / activation.ACTIVATION:
                return activation_value
            return inherited_read(path)

        with patch.object(launcher.control, "_read", side_effect=staged_read):
            protocol, start = launcher._validate_authorization()
        self.assertEqual(protocol["protocol_id"], contract.PROTOCOL_ID)
        self.assertEqual(start["role"], "v24930_corrected_unicode_total_neutral_execution_start")

    def test_launcher_only_replaces_authorization_reader(self) -> None:
        original = parent_runner._validate_authorization
        try:
            with patch.object(parent_runner, "main", return_value=None) as called:
                launcher.main()
                called.assert_called_once_with()
                self.assertIs(parent_runner._validate_authorization, launcher._validate_authorization)
        finally:
            parent_runner._validate_authorization = original

    def test_resealed_algorithm_change_tamper_is_rejected(self) -> None:
        with (
            patch.object(activation.parent, "_active_conflicts", return_value=[]),
            patch.object(activation, "_tracked", return_value=True),
        ):
            value = activation.build_activation(now=1)
        tampered = copy.deepcopy(value)
        tampered["binding"][
            "algorithm_task_vector_prompt_model_search_fetch_or_budget_changed"
        ] = True
        tampered.pop("activation_payload_sha256")
        tampered["activation_payload_sha256"] = contract.payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            activation.validate_activation(tampered)


if __name__ == "__main__":
    unittest.main()
