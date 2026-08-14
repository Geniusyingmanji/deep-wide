from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25472_qualified_source_label_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import GroundedFrontierSearch, limits  # noqa: E402


QUESTION = (
    "Identify the jurisdiction whose capital is Kabul and whose official currency has "
    "ISO 4217 code AFN. Then use public web search and the official IANA Root Zone "
    "Database to return exactly one Markdown table and no prose. Columns exactly: "
    "Domain | Type | TLD Manager. Return exactly one row."
)
TASK = {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION}


class QualifiedModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0
        self.systems: list[str] = []
        self.users: list[str] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens, json_mode
        self.logical_calls += 1; self.requests += 1; self.attempts += 1
        self.input_tokens += 10; self.output_tokens += 5; self.total_tokens += 15
        self.systems.append(str(system)); self.users.append(str(user))
        if self.logical_calls == 1:
            text = json.dumps({"language":"English","columns":["ignored"],"queries":["Kabul AFN country","Kabul AFN jurisdiction","IANA AF domain","AF manager"]})
        elif self.logical_calls == 2:
            text = json.dumps({"pivots":["Afghanistan"],"row_targets":[".af"],"authority_terms":["IANA Root Zone Database"],"queries":["IANA .af record",".af TLD type"],"records":[]})
        else:
            text = "| Domain | Type | TLD Manager |\n|---|---|---|\n| .af | Unknown | Old Manager |"
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class QualifiedSearch(GroundedFrontierSearch):
    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        if self._phase == target.PHASES[0] or not output:
            return output
        url = "https://www.iana.org/domains/root/db/af.html"
        first = output[0].get("results") if isinstance(output[0], dict) else None
        if isinstance(first, list) and first:
            first[0].update({"url":url,"fetch_url":url,"title":".af record"})
        for batch in output:
            trace = batch.get("hosted_search_trace") if isinstance(batch,dict) else None
            if isinstance(trace,dict):
                for action in trace.get("actions") or []:
                    for source in action.get("sources") or []:
                        if "iana.org" in str(source.get("url") or ""):
                            source.update({"url":url,"fetch_url":url,"title":".af record"})
        return output

    def fetch_urls(self, requests_):
        values=list(requests_); output=super().fetch_urls(values)
        if self._phase == target.PHASES[0]: return output
        url="https://www.iana.org/domains/root/db/af.html"
        request=next((item for item in values if str(item.get("url") or "")==url),None)
        if request is None:return output
        content="TLD Type | country-code"
        self._prefixes[url]=content
        result={"title":".af record","url":url,"fetch_url":url,"requested_url":url,"raw_content":content,"content":""}
        if output and output[0].get("results"):output[0]["results"][0]=result
        else:output.insert(0,{"query":request.get("query", ""),"answer":"","results":[result],"error":None,"provider":"synthetic-fetch"})
        return output


def run_runtime(*, task: dict[str,str] | None = None, runtime=target):
    model=QualifiedModel()
    with tempfile.TemporaryDirectory(dir=ROOT/"outputs") as raw:
        output=Path(raw);slots=output/"slots";slots.mkdir()
        for i in range(1,5):(slots/f"slot_{i:02d}.lock").write_text("{}\n")
        bounded=DeadlineAwareGlobalModelSlotLimiter(model,slot_directory=slots,output_root=output,slot_cap=4,absolute_deadline=time.monotonic()+240)
        budget=cap.PhysicalEffectBudget()
        searches={phase:cap.HardCappedSearchClient(QualifiedSearch(QUESTION,phase),budget,phase=phase) for phase in runtime.PHASES}
        result,stage=runtime.run_task(TASK if task is None else task,model=cap.HardCappedModelLimiter(bounded,budget),searches=searches,limits=limits(),budget=budget,monotonic=time.monotonic)
    return model,runtime.validate_result(result),runtime.validate_stage_receipt(stage),cap.validate_budget_receipt(budget.receipt())


class V25472QualifiedSourceLabelRuntimeTests(unittest.TestCase):
    def test_one_parent_forward_applies_qualified_source_field(self) -> None:
        model,result,stage,budget=run_runtime()
        self.assertEqual(model.logical_calls,3);self.assertEqual(budget["query_admitted_count"],4);self.assertLessEqual(budget["fetch_admitted_count"],14);self.assertEqual(budget["model_admitted_count"],3)
        self.assertTrue(result["prediction_changed"]);self.assertIn("| .af | country-code | Old Manager |",result["prediction"]);self.assertFalse(stage["failure_present"])
        self.assertEqual(result["row_key_bound_source_receipt"]["additional_fetch_calls"],0)

    def test_parent_provider_request_bytes_are_unchanged(self) -> None:
        candidate,*_=run_runtime();control,*_=run_runtime(runtime=target.parent_runtime)
        self.assertEqual(candidate.systems,control.systems);self.assertEqual(candidate.users,control.users);self.assertEqual(candidate.logical_calls,control.logical_calls)

    def test_private_namespace_does_not_mutate_parent_candidate(self) -> None:
        contract=target.integration_contract();self.assertTrue(contract["candidate_module_bound_in_private_namespace"]);self.assertTrue(contract["parent_module_global_candidate_unchanged"]);self.assertEqual(contract["additional_candidate_provider_effects"],0)

    def test_privileged_input_rejected_before_any_effect(self) -> None:
        with self.assertRaises(ValueError):run_runtime(task={**TASK,"category":"forbidden"})

    def test_result_stage_application_and_credit_tamper_fail_closed(self) -> None:
        _model,result,stage,_budget=run_runtime()
        for kind in ("application","credit","stage"):
            if kind=="stage":
                changed=copy.deepcopy(stage);changed["query_fetch_model_token_context_and_wall_caps_unchanged"]=False;changed.pop("receipt_payload_sha256");changed["receipt_payload_sha256"]=target.payload_sha256(changed)
                with self.subTest(kind=kind),self.assertRaises(ValueError):target.validate_stage_receipt(changed)
                continue
            changed=copy.deepcopy(result)
            if kind=="application":changed["private_source_application"]["candidate_prediction"] += "x"
            else:changed["row_key_bound_source_receipt"]["positive_signed_credit_count"]=1
            changed.pop("result_payload_sha256");changed["result_payload_sha256"]=target.payload_sha256(changed)
            with self.subTest(kind=kind),self.assertRaises(ValueError):target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_new_effect_capability(self) -> None:
        source=Path(target.__file__).read_text(encoding="utf-8");tree=ast.parse(source);imports=[];privileged=[];forbidden={"category","question_type","task_category","split","ground_truth","gold","answer_key","score","reward"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            elif isinstance(node,ast.Subscript) and isinstance(node.slice,ast.Constant) and node.slice.value in forbidden:privileged.append(str(node.slice.value))
        self.assertEqual(privileged,[]);self.assertFalse(any(name==bad or name.startswith(bad+".") for bad in ("os","pathlib","subprocess","socket","requests","httpx") for name in imports))


if __name__ == "__main__":unittest.main()
