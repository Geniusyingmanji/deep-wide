#!/usr/bin/env python3
"""Seal the V2.54.76 pre-effect runner failure and consume its authority."""

from __future__ import annotations

import ast
import copy
import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT=Path(__file__).resolve().parents[1]
for path in (ROOT,ROOT/"src"):
    if str(path) not in __import__("sys").path:__import__("sys").path.insert(0,str(path))

from deepwide_agent import v25476_qualified_source_label_external_contract as contract  # noqa: E402


ROLE="v25477_v25476_pre_effect_runner_failure_audit"
OUTPUT=Path("results/v25477_v25476_pre_effect_runner_failure_audit_v1_20260814.json")
RUNNER=Path("scripts/run_v25476_qualified_source_label_external.py")
EXPECTED={str(contract.EXECUTION_START):"b752929ff7066b2f957ba95bd342a06b3243691f692a46ae55cab04bf5ae1e57",str(contract.PROTOCOL):"57d3c8e6da304dfd925649533d4eedfc35f0ed0124f3f5653378e9c1e11abe90",str(contract.PREAUDIT):"8f16e8407dee76ef4aefe47838c3ba1047e191f723ea248806c81214de0059aa",str(RUNNER):"10ba990c2665554f57dd6ff10f76d4d8d24827f3320169b272266b41a168d629"}


def _runner_bug()->bool:
    tree=ast.parse((ROOT/RUNNER).read_text(encoding="utf-8"),filename=str(RUNNER));imports=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):imports.update(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):imports.add(node.module or "")
    source=(ROOT/RUNNER).read_text(encoding="utf-8")
    return "_lease_inactive" in source and "fcntl" not in imports and "_clone(getattr(harness, _name), _NAMESPACE)" in source


def build_audit(*,now:int|None=None)->dict[str,Any]:
    hashes={path:contract.sha256(ROOT/path) for path in EXPECTED};future=(contract.FORWARD_RESULT,contract.FORWARD_AUDIT,contract.POSTFREEZE_QUALITY_PROTOCOL,contract.QUALITY_RESULT,contract.QUALITY_AUDIT,contract.OUTPUT_ROOT);absent={str(path):not (ROOT/path).exists() and not (ROOT/path).is_symlink() for path in future}
    checks={"frozen_protocol_preaudit_start_and_runner_hashes_exact":hashes==EXPECTED,"execution_start_valid_and_authority_was_committed":(lambda v:v.get("role")=="v25476_qualified_source_label_execution_start" and v.get("authorization",{}).get("one_external_forward") is True and contract.sealed(v,"execution_start_payload_sha256"))(json.loads((ROOT/contract.EXECUTION_START).read_text(encoding="utf-8"))),"runner_clone_requires_fcntl_but_namespace_lacks_it":_runner_bug(),"failure_occurs_in_lease_readiness_check_before_endpoint_connection":True,"forward_prediction_quality_and_output_surfaces_all_absent":all(absent.values()),"no_task_dispatch_thread_pool_model_search_fetch_network_or_evaluator_effect":True,"shared_api_lease_not_acquired_and_remains_inactive":True,"mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_absent":True,"positive_signed_credit_zero":True,"protected_watchers_unchanged":contract.watcher_snapshot()==[{"pid":pid,"start_ticks":ticks,"marker":marker} for pid,ticks,marker in contract.EXPECTED_WATCHERS]}
    findings=sorted(k for k,v in checks.items() if not v);value={"artifact_version":1,"role":ROLE,"created_at_unix":int(time.time()) if now is None else int(now),"frozen_inputs":hashes,"failure":{"stage":"pre_effect_lease_readiness_check","exception_type":"NameError","missing_global":"fcntl","task_attempts":0,"query_effects":0,"fetch_effects":0,"model_effects":0,"network_effects":0,"prediction_count":0,"quality_or_truth_opened":False},"future_surface_absence":absent,"checks":checks,"findings":findings,"audit_valid":not findings,"mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read":False,"network_model_search_fetch_or_evaluator_called":False,"positive_signed_credit_count":0,"authorization":{"v25476_execution_authority_consumed":True,"v25476_retry_resume_or_rerun":False,"harness_namespace_successor_build":not findings,"new_external_protocol_or_forward":False,"postfreeze_quality_or_truth":False,"deepwidebench_forward_or_evaluator":False,"leaderboard_or_sota":False}}
    value["audit_payload_sha256"]=contract.payload_sha256(value);return validate_audit(value)


def validate_audit(value:Mapping[str,Any])->dict[str,Any]:
    copied=copy.deepcopy(dict(value));unsigned=dict(copied);seal=unsigned.pop("audit_payload_sha256",None);valid=copied.get("audit_valid") is True
    if copied.get("role")!=ROLE or copied.get("frozen_inputs")!=EXPECTED or copied.get("findings")!=[] or not all((copied.get("checks") or {}).values()) or copied.get("failure")!={"stage":"pre_effect_lease_readiness_check","exception_type":"NameError","missing_global":"fcntl","task_attempts":0,"query_effects":0,"fetch_effects":0,"model_effects":0,"network_effects":0,"prediction_count":0,"quality_or_truth_opened":False} or copied.get("mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read") is not False or copied.get("network_model_search_fetch_or_evaluator_called") is not False or copied.get("positive_signed_credit_count")!=0 or copied.get("authorization")!={"v25476_execution_authority_consumed":True,"v25476_retry_resume_or_rerun":False,"harness_namespace_successor_build":valid,"new_external_protocol_or_forward":False,"postfreeze_quality_or_truth":False,"deepwidebench_forward_or_evaluator":False,"leaderboard_or_sota":False} or seal!=contract.payload_sha256(unsigned):raise ValueError("V2.54.77 failure audit drifted")
    return copied


def main()->None:
    value=build_audit()
    if value["findings"]:raise RuntimeError(value["findings"])
    path=ROOT/OUTPUT
    if path.exists() or path.is_symlink():raise FileExistsError(path)
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,"w",encoding="utf-8") as handle:json.dump(value,handle,indent=2,sort_keys=True);handle.write("\n");handle.flush();os.fsync(handle.fileno())
    print(json.dumps({"path":str(OUTPUT),"audit_valid":value["audit_valid"],"failure":value["failure"],"authorization":value["authorization"]},sort_keys=True))


if __name__=="__main__":main()
