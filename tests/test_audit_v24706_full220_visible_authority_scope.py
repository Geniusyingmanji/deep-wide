from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24706_full220_visible_authority_scope as audit  # noqa: E402


class V24706AuthorityScopeAuditTests(unittest.TestCase):
    def test_real_scope_has_one_worldbank_task(self) -> None:
        value = audit.build_audit(now=0)
        audit.validate_audit(value)
        self.assertEqual(value["coverage"]["adapter_route_eligible_task_count"], 1)
        self.assertEqual(
            value["coverage"]["authority_namespace_task_counts"], {"world_bank": 1}
        )

    def test_namespace_bridge_is_no_go_before_forward(self) -> None:
        decision = audit.build_audit(now=0)["decision"]
        self.assertEqual(decision["status"], "deepwidebench_transfer_no_go_before_forward")
        self.assertFalse(decision["new_benchmark_forward_or_evaluator_warranted"])

    def test_only_generic_candidate_design_is_authorized(self) -> None:
        authorization = audit.build_audit(now=0)["authorization"]
        self.assertTrue(authorization["generic_target_value_candidate_design"])
        self.assertFalse(authorization["namespace_adapter_runtime_implementation"])
        self.assertFalse(authorization["fresh_dev64_protocol_or_launch"])
        self.assertFalse(authorization["exact220"])

    def test_resealed_launch_tamper_fails_closed(self) -> None:
        value = audit.build_audit(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["fresh_dev64_protocol_or_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(ValueError):
            audit.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
