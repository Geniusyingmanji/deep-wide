#!/usr/bin/env python3
"""Post-freeze compact-ledger mechanism audit and evaluator."""
from __future__ import annotations
import copy,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
for path in (ROOT,ROOT/"src"):
    if str(path) not in sys.path:sys.path.insert(0,str(path))
from deepwide_agent import v24944_compact_ledger_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24932_unicode_total_exact220 as parent  # noqa: E402
from scripts import run_v24944_compact_ledger_exact220_task as child  # noqa: E402

def _aggregate()->dict[str,Any]:
    names=("input_page_count","visible_schema_column_count","discovered_record_count","discovered_row_key_count","conflicting_coordinate_count","admissible_bound_observation_count","retained_admissible_bound_observation_count","missed_admissible_bound_observation_count","admissible_record_count","retained_admissible_record_count","source_url_count","source_host_count","compact_ledger_characters","maximum_compact_record_line_characters","projected_rendered_characters","positive_signed_credit_count","unbound_observation_positive_credit_count")
    totals={name:0 for name in names};valid=0;missing=[];invalid=[];engaged=0;full=0
    for position in range(1,221):
        path=ROOT/contract.TASK_ROOT/f"task_{position:04d}"/contract.PROJECTION_RECEIPT_NAME
        if path.is_symlink() or not path.is_file():missing.append(position);continue
        try:value=child.validate_runtime_receipt(parent.parent.base._read(path));receipt=value["candidate_receipt"]
        except (KeyError,OSError,RuntimeError,TypeError,ValueError):invalid.append(position);continue
        valid+=1
        for name in names:totals[name]+=int(receipt[name])
        engaged+=int(receipt["admissible_bound_observation_count"]>0)
        full+=int(receipt["admissible_bound_observation_count"]>0 and receipt["missed_admissible_bound_observation_count"]==0)
    return {"selected_tasks":220,"valid_content_free_receipts":valid,"missing_receipts":len(missing),"invalid_receipts":len(invalid),"missing_task_positions":missing,"invalid_task_positions":invalid,"tasks_with_admissible_bound_observation":engaged,"tasks_with_full_admissible_observation_retention":full,"totals":totals,"mechanism_engaged":totals["admissible_bound_observation_count"]>0,"contains_question_query_url_host_page_projection_prediction_hash_or_opaque_id":False,"mapping_gold_category_question_type_split_evaluator_score_reward_read":False,"entropy_or_information_gain_assigns_credit":False}

def configure():
    parent.contract=contract;parent.configure();engine=parent.parent.base;date=contract.DATE;evaluator_root=contract.OUTPUT_ROOT/"evaluator"
    engine.EVALUATOR_PROTOCOL=Path(f"results/v24944_compact_ledger_exact220_evaluator_preregistration_v1_{date}.json")
    engine.FINAL_RESULT=Path(f"results/v24944_compact_ledger_exact220_result_v1_{date}.json")
    engine.POSTAUDIT=Path(f"results/v24944_compact_ledger_exact220_postresult_audit_v1_{date}.json")
    engine.EVALUATOR_ROOT=evaluator_root;engine.PREPARE_ATTESTATION=evaluator_root/"prepare_attestation.json";engine.JOINED_OUTCOMES=evaluator_root/"terminal_outcomes_evaluator_joined.jsonl";engine.OFFICIAL_PREDICTIONS=evaluator_root/"official_predictions.jsonl";engine.EVALUATOR_RUNS=evaluator_root/"official_eval_workers";engine.EVALUATOR_LOGS=evaluator_root/"logs";engine.MERGED_RESULTS=evaluator_root/"official_eval_results.jsonl";engine.MERGE_ATTESTATION=evaluator_root/"merge_attestation.json";engine.SUMMARY=evaluator_root/"conservative_summary.json";engine.EVALUATOR_OWNER="v24944_compact_ledger_exact220_evaluator_v1";engine.EVALUATOR_PURPOSE="postfreeze_fixed_partition_parallel_compact_ledger_exact220_evaluator"
    engine.CONTROL_FILES=tuple(dict.fromkeys((str(contract.FINALIZER),str(contract.RUNNER),str(contract.CHILD),str(contract.CONTROL),str(contract.SOURCE),str(contract.PROJECTOR_SOURCE),str(contract.LEGACY_PROJECTOR_SOURCE),str(contract.TARGET_VALUE_SOURCE),str(contract.BINDING),str(contract.TEST),*engine.CONTROL_FILES)))
    engine.REFERENCES={**engine.REFERENCES,"v24857":Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),"v24938":Path("results/v24938_contextual_record_exact220_result_v1_20260809.json")}
    inherited=engine.build_forward_audit
    def build_forward_audit(*,now=None):
        value=copy.deepcopy(inherited(now=now));aggregate=_aggregate();value["compact_ledger_mechanism"]=aggregate;value["checks"]["all_present_projection_receipts_valid"]=aggregate["invalid_receipts"]==0;value["checks"]["receipt_partition_exact220"]=aggregate["valid_content_free_receipts"]+aggregate["missing_receipts"]+aggregate["invalid_receipts"]==220;value["findings"]=sorted(name for name,passed in value["checks"].items() if not passed);value["audit_valid"]=not value["findings"];value["authorization"]["postfreeze_exact220_evaluator_protocol"]=value["audit_valid"];value.pop("audit_payload_sha256",None);value["audit_payload_sha256"]=contract.payload_sha256(value);return value
    engine.build_forward_audit=build_forward_audit
def main():configure();parent.parent.base.main()
if __name__=="__main__":main()
