from __future__ import annotations

import copy
import re
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
from deepwide_agent import v25457_date_bounded_official_rfc_xml_shared_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import limits  # noqa: E402
from test_v25446_key_anchored_metadata_shared_effect_external import (  # noqa: E402
    RfcModel,
    RfcSearch,
)


QUESTION = (
    "Use public web sources and the official RFC Editor database to return "
    "exactly one Markdown table and no prose for the four visible document "
    "identities <RFCS>RFC 9080; RFC 9081; RFC 9082; RFC 9083</RFCS>. "
    "Columns exactly: RFC | Title | Authors | Status | Stream | Published."
)
TASK = {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION}


def prefix(number: int) -> str:
    return (
        f'<rfc number="{number}" category="std" submissionType="IETF">'
        "<front>"
        f"<title>Official\u00a0Title {number}</title>"
        f'<seriesInfo name="RFC" value="{number}" stream="IETF"/>'
        f'<author asciiFullname="Author {number}" fullname="作者 {number}"/>'
        '<date month="08" year="2026"/>'
        "<abstract><t>truncated"
    )


class PrefixRfcSearch(RfcSearch):
    def __init__(self, question: str, phase: str, *, redirect: bool = False) -> None:
        super().__init__(question, phase)
        self.redirect = redirect

    def fetch_urls(self, requests_):
        values = list(requests_)
        if values and all(str(item.get("url", "")).endswith(".xml") for item in values):
            self.fetch_calls += len(values)
            output = []
            for item in values:
                requested = str(item["url"])
                number = int(re.search(r"rfc([0-9]+)\.xml$", requested).group(1))
                self._prefixes[requested] = prefix(number)
                final = requested + "?redirected=1" if self.redirect else requested
                output.append(
                    {
                        "query": item.get("query", ""),
                        "answer": "",
                        "results": [
                            {
                                "title": f"RFC {number}",
                                "url": final,
                                "fetch_url": requested,
                                "requested_url": requested,
                                "raw_content": prefix(number),
                                "content": "",
                            }
                        ],
                        "error": None,
                        "provider": "synthetic-date-bounded-xml",
                    }
                )
            return output
        return super().fetch_urls(values)


def run_runtime(*, redirect: bool = False):
    model = RfcModel()
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        output = Path(raw)
        slots = output / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=output,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        outer = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                PrefixRfcSearch(QUESTION, phase, redirect=redirect),
                budget,
                phase=phase,
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            TASK,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return (
        model,
        target.validate_result(result),
        target.validate_stage_receipt(stage),
        cap.validate_budget_receipt(budget.receipt()),
    )


class V25457DateBoundedOfficialRfcXmlSharedRuntimeTests(unittest.TestCase):
    def test_one_parent_then_date_bounded_xml_candidate(self) -> None:
        model, result, stage, budget = run_runtime()
        receipt = result["official_rfc_xml_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(budget["fetch_rejected_count"], 0)
        self.assertGreaterEqual(receipt["official_xml_valid_record_count"], 3)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("Official Title 9080", result["prediction"])
        self.assertIn("Author 9080", result["prediction"])
        self.assertFalse(stage["failure_present"])

    def test_shared_base_and_parent_key_candidate_not_composed(self) -> None:
        _model, result, _stage, _budget = run_runtime()
        parent = target.parent_runtime.parent.validate_result(
            result["private_parent_result"]
        )
        self.assertEqual(
            result["predictions"][target.BASE_ARM],
            parent["predictions"][target.parent_runtime.parent.BASE_ARM],
        )
        self.assertTrue(
            result["official_rfc_xml_receipt"][
                "parent_key_anchored_candidate_not_composed"
            ]
        )

    def test_redirected_pages_preserve_base(self) -> None:
        _model, result, _stage, budget = run_runtime(redirect=True)
        receipt = result["official_rfc_xml_receipt"]
        self.assertEqual(receipt["official_xml_exact_nonredirected_page_count"], 0)
        self.assertEqual(receipt["official_xml_valid_record_count"], 0)
        self.assertFalse(result["prediction_changed"])
        self.assertEqual(budget["fetch_rejected_count"], 0)

    def test_parent_runtime_globals_are_not_mutated(self) -> None:
        contract = target.integration_contract()
        self.assertTrue(contract["candidate_module_bound_in_private_namespace"])
        self.assertTrue(contract["parent_runtime_global_candidate_unchanged"])
        self.assertTrue(contract["date_bounded_official_xml_candidate_applied"])

    def test_resealed_result_stage_receipt_or_credit_tamper_fails(self) -> None:
        _model, result, stage, _budget = run_runtime()
        for kind in ("result", "receipt", "stage", "credit"):
            if kind == "stage":
                changed_stage = copy.deepcopy(stage)
                changed_stage["candidate_fetch_accounted_in_same_outer_budget"] = False
                changed_stage.pop("receipt_payload_sha256")
                changed_stage["receipt_payload_sha256"] = target.payload_sha256(
                    changed_stage
                )
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(changed_stage)
                continue
            changed = copy.deepcopy(result)
            if kind == "result":
                changed["prediction"] = changed["predictions"][target.BASE_ARM]
            elif kind == "receipt":
                changed["official_rfc_xml_receipt"]["final_fetch_count"] += 1
            else:
                changed["official_rfc_xml_receipt"][
                    "positive_signed_credit_count"
                ] = 1
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_privileged_input_rejected_before_effect(self) -> None:
        task = {**TASK, "category": "forbidden"}
        budget = cap.PhysicalEffectBudget()
        with self.assertRaises(ValueError):
            target.run_task(
                task,
                model=object(),
                searches={},
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        self.assertEqual(budget.receipt()["fetch_admitted_count"], 0)

    def test_contract_preserves_caps_and_forbids_launch(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(contract["maximum_candidate_additional_fetches"], 4)
        self.assertEqual(contract["candidate_additional_queries"], 0)
        self.assertEqual(contract["candidate_additional_model_calls"], 0)
        self.assertEqual(contract["maximum_physical_fetches"], 14)
        self.assertFalse(contract["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
