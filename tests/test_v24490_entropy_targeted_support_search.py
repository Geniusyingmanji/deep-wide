from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24388_uncertainty_credit import (  # noqa: E402
    apply_active_evidence,
)
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
)
from deepwide_agent.v24485_execution_scoped_validation_memo import (  # noqa: E402
    ExecutionValidationMemo,
)
from deepwide_agent.v24490_entropy_targeted_support_search import (  # noqa: E402
    MAXIMUM_TARGETED_LOGICAL_QUERIES,
    MAXIMUM_TARGETED_SOURCES,
    build_target_plan,
    run_v24490_task,
    validate_effect_delta_receipt,
    validate_result,
)
from scripts import audit_v24398_failure_observability_build as audit  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24438_bounded_narrative_effect_runner import (  # noqa: E402
    NarrativeDeadlineSearch,
)
from test_v24447_third_source_entropy_to_decision import (  # noqa: E402
    KNOWN_BASELINE,
    clients as parent_clients,
)


class TargetedSupportSearch(NarrativeDeadlineSearch):
    def __init__(self, *args, targeted_mode: str = "support", overlap=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.targeted_mode = targeted_mode
        self.overlap = overlap
        self.targeted_query_vector: list[str] = []

    def _request(self, queries):  # type: ignore[override]
        payload = super()._request(queries)
        if self.request_invocations == 4:
            self.targeted_query_vector = list(queries)
            sources = payload["output"][0]["action"]["sources"]
            sources[:] = [
                {
                    "type": "web_source",
                    "url": "https://targeted-alpha-three.example/record",
                    "title": "Alpha Founding year 2025 official record",
                },
                {
                    "type": "web_source",
                    "url": "https://targeted-alpha-four.example/record",
                    "title": "Alpha Founding year 2025 historical archive",
                },
                {
                    "type": "web_source",
                    "url": "https://active-alpha-one.example/record"
                    if self.overlap
                    else "https://targeted-alpha-five.example/record",
                    "title": "Alpha Founding year 2025 independent source",
                },
            ]
        return payload

    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations == 4:
            for batch in batches:
                for result in batch["results"]:
                    result["raw_content"] = (
                        "Alpha was founded in 2025 and later expanded."
                        if self.targeted_mode == "support"
                        else "Alpha was founded in 2026 and later expanded."
                    )
        return batches


def clients(output: Path, clock: AdvancingClock, *, mode="support", overlap=False):
    model, old_search = parent_clients(output, clock, third=False)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    model.inner.baseline = KNOWN_BASELINE
    search = TargetedSupportSearch(
        clock, deadline=300, targeted_mode=mode, overlap=overlap
    )
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del old_search
    return model, search


def _reseal_result(value: dict) -> None:
    value.pop("result_sha256", None)
    value["result_sha256"] = payload_sha256(value)


class V24490EntropyTargetedSupportSearchTests(unittest.TestCase):
    fixture: tuple
    temporaries: list[tempfile.TemporaryDirectory] = []

    @classmethod
    def setUpClass(cls) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.temporaries.append(temporary)
        cls.fixture = cls._execute(Path(temporary.name))

    @classmethod
    def tearDownClass(cls) -> None:
        for temporary in reversed(cls.temporaries):
            temporary.cleanup()

    @staticmethod
    def _execute(output: Path, *, mode="support", overlap=False):
        clock = AdvancingClock()
        model, search = clients(
            output, clock, mode=mode, overlap=overlap
        )
        memo = ExecutionValidationMemo()
        with memo:
            outcome = run_v24490_task(
                TASK,
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        memo_receipt = memo.content_free_receipt()
        if (
            memo_receipt["total_misses"] != 8
            or memo_receipt["total_hits"] < 8
            or memo_receipt["total_mismatches"] != 0
            or memo_receipt["bindings_restored"] is not True
        ):
            raise AssertionError(memo_receipt)
        validate_result(outcome.targeted_result)
        validate_effect_delta_receipt(outcome.effect_delta_receipt)
        return outcome, model, search

    def run_case(self, *, mode="support", overlap=False):
        self.assertEqual((mode, overlap), ("support", False))
        return self.fixture

    def test_one_new_source_crosses_unchanged_known_cell_gate(self) -> None:
        outcome, model, search = self.run_case()
        result = outcome.targeted_result
        receipt = result["targeted_support_receipt"]
        plan = result["targeted_private_state"]["target_plan"]
        effect = outcome.effect_delta_receipt
        self.assertEqual(plan["support_deficit"], 1)
        self.assertEqual(plan["current_alternative_support_count"], 2)
        self.assertGreater(plan["current_alternative_posterior_probability"], 0.8)
        self.assertEqual(len(plan["query_vector"]), MAXIMUM_TARGETED_LOGICAL_QUERIES)
        self.assertEqual(search.targeted_query_vector, plan["query_vector"])
        self.assertEqual(receipt["targeted_selected_source_count"], 1)
        self.assertEqual(receipt["safe_change_count_after_targeted_search"], 1)
        self.assertGreater(
            receipt["decision_credit_total_nats_after_targeted_search"], 0
        )
        self.assertIn("| Alpha | 2025 |", result["candidate_prediction"])
        self.assertEqual(effect["additional_search_batches"], 1)
        self.assertEqual(effect["additional_logical_queries"], 2)
        self.assertEqual(effect["additional_fetch_attempts"], 1)
        self.assertEqual(effect["additional_model_acquisitions"], 0)
        self.assertEqual(effect["additional_recursive_split_requests"], 0)
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.request_invocations, 4)
        self.assertEqual(search.fetch_invocations, 4)

    def test_conflicting_targeted_page_preserves_zero_decision_credit(self) -> None:
        outcome, _, _ = self.run_case()
        before = outcome.parent.adaptive_result["adaptive_active_evidence_result"]
        conflicting = apply_active_evidence(
            before["catalog"],
            [
                *before["active_observations"],
                {
                    "row_key": "Alpha",
                    "column": "Founding year",
                    "value": "2026",
                    "source_host": "targeted-conflict.example",
                    "fetch_integrity": True,
                },
            ],
        )
        self.assertEqual(conflicting["receipt"]["safe_change_count"], 0)
        self.assertEqual(
            conflicting["receipt"]["decision_credit_total_nats"], 0
        )
        self.assertEqual(conflicting["final_prediction"], KNOWN_BASELINE)

    def test_overlap_is_excluded_and_fetch_cap_tracks_support_deficit(self) -> None:
        outcome, _, _ = self.run_case()
        private = outcome.targeted_result["targeted_private_state"]
        plan = private["target_plan"]
        overlap = {
            "url": "https://active-alpha-one.example/record",
            "query": "batch-stratified discovery 4",
            "title": "Alpha Founding year 2025 official record",
            "member_label": "",
        }
        selected = __import__(
            "deepwide_agent.v24490_entropy_targeted_support_search",
            fromlist=["_select_targeted_leads", "_used_sources"],
        )
        replayed = selected._select_targeted_leads(
            [overlap, *private["targeted_union_leads"]],
            plan,
            excluded_sources=selected._used_sources(
                outcome.parent.adaptive_result
            ),
        )
        self.assertLessEqual(
            len(replayed), MAXIMUM_TARGETED_SOURCES
        )
        self.assertEqual(len(replayed), plan["support_deficit"])
        self.assertNotIn(
            "active-alpha-one.example",
            {
                item["url"].split("//", 1)[1].split("/", 1)[0]
                for item in replayed
            },
        )

    def test_query_page_credit_and_prediction_tamper_fail_closed(self) -> None:
        outcome, _, _ = self.run_case()
        value = outcome.targeted_result
        cases = (
            (
                "query",
                lambda item: item["targeted_private_state"]["target_plan"][
                    "query_vector"
                ].__setitem__(0, "tampered query"),
            ),
            (
                "page",
                lambda item: item["targeted_private_state"][
                    "targeted_fetch_batches"
                ][0]["results"][0].__setitem__("raw_content", "tampered page"),
            ),
            (
                "credit",
                lambda item: item["targeted_support_receipt"].__setitem__(
                    "decision_credit_total_nats_after_targeted_search", 0
                ),
            ),
            (
                "prediction",
                lambda item: item.__setitem__(
                    "candidate_prediction", KNOWN_BASELINE
                ),
            ),
        )
        with ExecutionValidationMemo():
            validate_result(value)
            for name, alter in cases:
                with self.subTest(name=name):
                    changed = copy.deepcopy(value)
                    alter(changed)
                    _reseal_result(changed)
                    with self.assertRaises(ValueError):
                        validate_result(changed)

    def test_plan_uses_frozen_posterior_not_runtime_labels(self) -> None:
        outcome, _, _ = self.run_case()
        active = outcome.parent.adaptive_result["adaptive_active_evidence_result"]
        plan = build_target_plan(active)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["leading_alternative"], "2025")
        self.assertTrue(
            plan[
                "selection_uses_only_validated_posterior_entropy_and_support_deficit"
            ]
        )

    def test_safe_state_produces_no_further_target_plan(self) -> None:
        outcome, _, _ = self.run_case()
        self.assertIsNone(
            build_target_plan(
                outcome.targeted_result["targeted_active_evidence_result"]
            )
        )

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = AdvancingClock()
        model, search = clients(Path(temporary.name), clock)
        with self.assertRaises(ValueError):
            run_v24490_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_runtime_source_is_label_blind(self) -> None:
        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24490_entropy_targeted_support_search.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
