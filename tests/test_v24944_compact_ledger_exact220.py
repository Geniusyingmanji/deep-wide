from __future__ import annotations
import copy,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for path in (ROOT,ROOT/"src"):
    if str(path) not in sys.path: sys.path.insert(0,str(path))
from deepwide_agent import v24942_compact_schema_bound_record_ledger as projector  # noqa: E402
from deepwide_agent import v24944_compact_ledger_exact220_contract as contract  # noqa: E402
from scripts import control_v24944_compact_ledger_exact220 as control  # noqa: E402
from scripts import run_v24944_compact_ledger_exact220_task as child  # noqa: E402
from scripts import finalize_v24944_compact_ledger_exact220 as finalizer  # noqa: E402

QUESTION="From the page include Cohort C01 only.\nColumn names: Country | Cohort | ISO3 | Population [POP] @2021\nOutput format: table only. Cohort C01."
def batches():
    return [{"results":[{"title":"Official","url":"https://example.invalid/data","content":"Country | Cohort | ISO3 | Population\nAlpha | C01 | ALP | 991\nBeta | X01 | BET | 881"}]}]
class V24944Tests(unittest.TestCase):
    def tearDown(self): child._VISIBLE_QUESTION=None;child._LAST_RECEIPT=None
    def test_single_change_and_caps(self):
        self.assertEqual(contract._single_change()["to"],projector.POLICY_ID);self.assertEqual((contract.SELECTED_COUNT,contract.EXECUTOR_CONCURRENCY,contract.MODEL_SLOT_CAP),(220,20,8));self.assertEqual(contract.LIMITS["search_queries"],4)
    def test_task_vector_label_blind(self):
        tasks=contract.task_vector(ROOT);self.assertEqual(len(tasks),220);self.assertTrue(all(set(x)=={"opaque_id","question"} for x in tasks))
    def test_external_go_chain(self):
        evidence=contract._evidence(ROOT);self.assertTrue(evidence["fresh_representation_only_external_go_valid"]);self.assertEqual(evidence["external_exact_gain"],11)
    def test_projection_and_receipt(self):
        child._VISIBLE_QUESTION=QUESTION;limits=type("L",(),{"page_chars":5000,"evidence_chars":30000})();text=child.compact_ledger_evidence_projection([],batches(),limits);self.assertIn("Alpha",text);r=child._LAST_RECEIPT["candidate_receipt"];self.assertGreater(r["admissible_bound_observation_count"],0)
    def test_receipt_tamper(self):
        child._VISIBLE_QUESTION=QUESTION;limits=type("L",(),{"page_chars":5000,"evidence_chars":30000})();child.compact_ledger_evidence_projection([],batches(),limits);bad=copy.deepcopy(child._LAST_RECEIPT);bad["candidate_receipt"]["positive_signed_credit_count"]=1
        with self.assertRaises(ValueError):child.validate_runtime_receipt(bad)
    def test_zero_credit(self):
        child._VISIBLE_QUESTION=QUESTION;limits=type("L",(),{"page_chars":5000,"evidence_chars":30000})();child.compact_ledger_evidence_projection([],batches(),limits);r=child._LAST_RECEIPT["candidate_receipt"];self.assertEqual(r["positive_signed_credit_count"],0);self.assertEqual(r["unbound_observation_positive_credit_count"],0)
    def test_watchers(self):self.assertEqual([x["pid"] for x in contract.protected_watcher_snapshot()],[795336,3061652,2808901,2889939])
    def test_runtime_semantic_audit(self):control.configure();self.assertEqual(control.base._runtime_findings(),([],[],[]))
    def test_source_policy_is_label_blind(self):
        self.assertTrue(contract._single_change()["same_forward_page_bytes_only"])
        self.assertFalse(contract._single_change()["entropy_or_information_gain_assigns_credit_or_routes"])
    def test_create_only(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"outputs") as d:
            p=Path(d)/"x.json";control.base.publish_new(p,{})
            with self.assertRaises(FileExistsError):control.base.publish_new(p,{})
    def test_finalizer_namespace(self):
        finalizer.configure();self.assertIn("v24944_compact_ledger",str(finalizer.parent.parent.base.FINAL_RESULT))
if __name__=="__main__":unittest.main()
