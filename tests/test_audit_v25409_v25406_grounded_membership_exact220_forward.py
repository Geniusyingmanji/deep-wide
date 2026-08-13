from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25406_grounded_membership_exact220_contract as contract  # noqa: E402
from scripts import audit_v25409_v25406_grounded_membership_exact220_forward as audit  # noqa: E402


class V25409V25406ForwardAuditAdapterTests(unittest.TestCase):
    def test_frozen_finalizer_remains_protocol_bound(self) -> None:
        self.assertEqual(
            contract.sha256(ROOT / contract.FINALIZER),
            audit.FROZEN_FINALIZER_SHA256,
        )
        protocol = audit._read(contract.PROTOCOL)
        self.assertEqual(
            protocol["dependency_manifest"][str(contract.FINALIZER)],
            audit.FROZEN_FINALIZER_SHA256,
        )

    def test_adapter_targets_only_v25406_future_surfaces(self) -> None:
        self.assertEqual(
            audit._future_surfaces(),
            (
                contract.FORWARD_AUDIT,
                contract.EVALUATOR_PROTOCOL,
                contract.RESULT,
                contract.POSTAUDIT,
                audit.frozen.EVALUATOR_ROOT,
            ),
        )

    def test_inherited_root_is_temporarily_bound_and_restored(self) -> None:
        audit.configure_postforward()
        inherited = audit.frozen.base.EVALUATOR_ROOT

        def observed() -> dict[str, object]:
            self.assertEqual(
                audit.frozen.base.EVALUATOR_ROOT,
                audit.frozen.EVALUATOR_ROOT,
            )
            return {"audit_valid": True}

        with mock.patch.object(
            audit.frozen, "_build_native_forward_audit", side_effect=observed
        ):
            value, returned = audit._native_with_v25406_evaluator_root()
        self.assertEqual(value, {"audit_valid": True})
        self.assertEqual(returned, inherited)
        self.assertEqual(audit.frozen.base.EVALUATOR_ROOT, inherited)

    def test_bottom_shell_is_bound_to_v25406(self) -> None:
        audit.configure_postforward()
        bottom = audit.frozen.base.base
        self.assertIs(bottom.contract, contract)
        self.assertIs(bottom._forward_barrier, audit.frozen._forward_barrier)
        self.assertIn(str(audit.ADAPTER), bottom.CONTROL_FILES)
        self.assertIn(str(audit.ADAPTER_TEST), bottom.CONTROL_FILES)
        self.assertEqual(bottom.FORWARD_AUDIT, contract.FORWARD_AUDIT)
        self.assertEqual(bottom.EVALUATOR_PROTOCOL, contract.EVALUATOR_PROTOCOL)
        self.assertEqual(bottom.FINAL_RESULT, contract.RESULT)
        self.assertEqual(bottom.POSTAUDIT, contract.POSTAUDIT)

    def test_postforward_commands_delegate_after_binding(self) -> None:
        sentinel = {"ok": True}
        with mock.patch.object(
            audit.frozen.base.base,
            "build_evaluator_protocol",
            return_value=sentinel,
        ), mock.patch.object(
            audit.frozen.base.base,
            "validate_evaluator_protocol",
            return_value=sentinel,
        ):
            self.assertIs(audit.build_evaluator_protocol(), sentinel)
        with mock.patch.object(
            audit.frozen.base.base, "evaluate", return_value=sentinel
        ):
            self.assertIs(audit.evaluate(), sentinel)
        with mock.patch.object(
            audit.frozen.base.base,
            "build_postresult_audit",
            return_value=sentinel,
        ), mock.patch.object(
            audit.frozen.base.base,
            "validate_postresult_audit",
            return_value=sentinel,
        ):
            self.assertIs(audit.build_postresult_audit(), sentinel)


if __name__ == "__main__":
    unittest.main()
