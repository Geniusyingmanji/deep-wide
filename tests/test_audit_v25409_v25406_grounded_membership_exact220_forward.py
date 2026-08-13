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
        audit.frozen.configure()
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


if __name__ == "__main__":
    unittest.main()
