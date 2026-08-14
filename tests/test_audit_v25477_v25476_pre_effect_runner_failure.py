from __future__ import annotations
import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for path in (ROOT,ROOT/"src"):
    if str(path) not in sys.path:sys.path.insert(0,str(path))
from scripts import audit_v25477_v25476_pre_effect_runner_failure as target  # noqa: E402
class V25477FailureAuditTests(unittest.TestCase):
    def test_runner_bug_is_reproducible_statically(self)->None:self.assertTrue(target._runner_bug())
    def test_failure_audit_consumes_authority_without_effect(self)->None:
        value=target.build_audit(now=1);self.assertEqual(target.validate_audit(value),value);self.assertTrue(value["audit_valid"]);self.assertEqual(value["failure"]["task_attempts"],0);self.assertTrue(value["authorization"]["v25476_execution_authority_consumed"]);self.assertFalse(value["authorization"]["v25476_retry_resume_or_rerun"])
    def test_all_forward_and_quality_surfaces_are_absent(self)->None:self.assertTrue(all(target.build_audit(now=1)["future_surface_absence"].values()))
    def test_resealed_effect_retry_or_credit_tamper_fails(self)->None:
        value=target.build_audit(now=1)
        for kind in ("effect","retry","credit"):
            changed=copy.deepcopy(value)
            if kind=="effect":changed["failure"]["model_effects"]=1
            elif kind=="retry":changed["authorization"]["v25476_retry_resume_or_rerun"]=True
            else:changed["positive_signed_credit_count"]=1
            changed.pop("audit_payload_sha256");changed["audit_payload_sha256"]=target.contract.payload_sha256(changed)
            with self.subTest(kind=kind),self.assertRaises(ValueError):target.validate_audit(changed)
if __name__=="__main__":unittest.main()
