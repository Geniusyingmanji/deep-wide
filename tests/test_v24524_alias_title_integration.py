from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
)
from deepwide_agent.v24524_alias_title_integration import (  # noqa: E402
    run_v24524_task,
    validate_alias_title_receipt,
    validate_cross_artifacts,
    validate_result,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import (  # noqa: E402
    clients as parent_clients,
)
from test_v24503_record_bound_reserve_integration import (  # noqa: E402
    RecordReserveSearch,
)


BASELINE = """```markdown
| University | Founding year |
| --- | --- |
| University of Southern Queensland | Unknown |
| Beta College | Unknown |
```"""
TASK = {
    "opaque_id": "task_abcdefabcdefabcdefabcdef",
    "question": (
        "Use public web sources to return one Markdown table about University "
        "of Southern Queensland and Beta College. The column names are: "
        "University, Founding year. Return one table only."
    ),
}


class AliasReserveSearch(RecordReserveSearch):
    def __init__(self, *args, alias_mode: str, **kwargs):
        super().__init__(*args, record_mode="none", **kwargs)
        self.alias_mode = alias_mode

    def _request(self, queries):  # type: ignore[override]
        payload = super()._request(queries)
        if self.request_invocations == 3:
            if self.alias_mode == "duplicate_source":
                urls = [
                    "https://same.example/record-one",
                    "https://same.example/record-two",
                ]
            else:
                urls = [
                    "https://usq-one.example/record",
                    "https://usq-two.example/record",
                ]
            payload["output"][0]["action"]["sources"][:] = [
                {
                    "type": "web_source",
                    "url": url,
                    "title": f"USQ institutional history {index}",
                }
                for index, url in enumerate(urls, start=1)
            ]
        return payload

    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations == 3:
            ordinal = 0
            for batch in batches:
                for result in batch["results"]:
                    year = (
                        "1967"
                        if self.alias_mode != "conflict" or ordinal == 0
                        else "1990"
                    )
                    result["raw_content"] = f"Founded | {year}"
                    ordinal += 1
        return batches


def clients(output: Path, clock: AdvancingClock, *, mode: str):
    model, old_search = parent_clients(output, clock, third=False)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    model.inner.baseline = BASELINE
    search = AliasReserveSearch(clock, deadline=300, alias_mode=mode)
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del old_search
    return model, search


def execute(mode: str):
    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    clock = AdvancingClock()
    model, search = clients(Path(temporary.name), clock, mode=mode)
    outcome = run_v24524_task(
        TASK,
        model=model,
        search=search,
        partition_seed_sha256=SEED,
        limits=limits(),
        monotonic=clock,
    )
    return temporary, outcome, model, search


class V24524AliasTitleIntegrationTests(unittest.TestCase):
    fixture: dict[str, tuple]

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = {
            mode: execute(mode)
            for mode in ("support", "conflict", "duplicate_source")
        }

    @classmethod
    def tearDownClass(cls) -> None:
        for temporary, *_ in cls.fixture.values():
            temporary.cleanup()

    def test_two_alias_sources_fill_unknown_cell_and_gain_decision_credit(self) -> None:
        _, outcome, _, _ = self.fixture["support"]
        receipt = outcome.alias_title_result["alias_title_receipt"]
        self.assertEqual(receipt["unique_alias_anchor_page_count"], 2)
        self.assertEqual(receipt["alias_projection_count"], 2)
        self.assertEqual(receipt["alias_observation_count"], 2)
        self.assertEqual(receipt["added_observation_count"], 2)
        self.assertEqual(receipt["safe_change_improvement_count"], 1)
        self.assertEqual(receipt["safe_change_regression_count"], 0)
        self.assertGreater(receipt["positive_information_gain_gain_nats"], 0)
        self.assertGreater(receipt["epistemic_credit_gain_nats"], 0)
        self.assertGreater(receipt["decision_credit_gain_nats"], 0)
        self.assertIn(
            "| University of Southern Queensland | 1967 |",
            outcome.alias_title_result["candidate_prediction"],
        )

    def test_conflicting_alias_sources_receive_no_decision_credit(self) -> None:
        _, outcome, _, _ = self.fixture["conflict"]
        receipt = outcome.alias_title_result["alias_title_receipt"]
        self.assertEqual(receipt["added_observation_count"], 2)
        self.assertEqual(receipt["safe_change_improvement_count"], 0)
        self.assertEqual(receipt["decision_credit_gain_nats"], 0)
        self.assertNotIn(
            "| University of Southern Queensland | 1967 |",
            outcome.alias_title_result["candidate_prediction"],
        )

    def test_duplicate_source_alias_pages_are_rejected_before_credit(self) -> None:
        from deepwide_agent import v24524_alias_title_integration as target

        _, outcome, _, _ = self.fixture["support"]
        projection = copy.deepcopy(
            outcome.alias_title_result["alias_title_projection"]
        )
        pages = copy.deepcopy(projection["pages"])
        self.assertEqual(len(pages), 2)
        pages[0]["host"] = "a.same.example"
        pages[1]["host"] = "b.same.example"
        projection = target.alias.build_conservative_alias_title_projection(
            BASELINE,
            pages,
            selected_identities={("universityofsouthernqueensland", "foundingyear")},
        )
        observations, removed_alias, removed_parent = (
            target._ambiguity_filtered_observations(
                projection,
                BASELINE,
                [],
            )
        )
        # Projection canonicalization collapses the two pages to one
        # registrable-source observation; the page count still makes that
        # source-row ambiguous and therefore rejects the observation.
        self.assertEqual(projection["alias_projection_count"], 1)
        self.assertEqual(removed_alias, 1)
        self.assertEqual(removed_parent, 0)
        self.assertEqual(observations, [])

    def test_alias_recovery_adds_no_external_effect(self) -> None:
        for mode, (_, outcome, model, search) in self.fixture.items():
            with self.subTest(mode=mode):
                receipt = outcome.alias_title_result["alias_title_receipt"]
                effect = outcome.effect_equivalence_receipt
                self.assertFalse(effect["external_effect_detected"])
                self.assertEqual(receipt["additional_model_requests"], 0)
                self.assertEqual(receipt["additional_logical_queries"], 0)
                self.assertEqual(receipt["additional_search_batches"], 0)
                self.assertEqual(receipt["additional_provider_search_calls"], 0)
                self.assertEqual(receipt["additional_fetch_calls"], 0)
                self.assertEqual(model.acquisitions, 2)
                self.assertEqual(search.request_invocations, 3)
                self.assertEqual(search.fetch_invocations, 3)

    def test_result_receipt_and_cross_artifacts_validate(self) -> None:
        for mode, (_, outcome, _, _) in self.fixture.items():
            with self.subTest(mode=mode):
                validate_result(outcome.alias_title_result)
                validate_alias_title_receipt(
                    outcome.alias_title_result["alias_title_receipt"]
                )
                validate_cross_artifacts(
                    outcome.parent.record_bound_result,
                    outcome.alias_title_result,
                    model_before=outcome.model_slot_receipt_before_alias_projection,
                    transport_before=outcome.transport_health_before_alias_projection,
                    search_before=outcome.search_single_shot_receipt_before_alias_projection,
                    model_after=outcome.model_slot_receipt,
                    transport_after=outcome.transport_health,
                    search_after=outcome.search_single_shot_receipt,
                    effect_equivalence_receipt=outcome.effect_equivalence_receipt,
                    expected_model_cap=2,
                )

    def test_result_receipt_parent_and_effect_tamper_fail_closed(self) -> None:
        _, outcome, _, _ = self.fixture["support"]
        result = copy.deepcopy(outcome.alias_title_result)
        result["alias_title_projection"]["alias_title_projections"][0][
            "value"
        ] = "1990"
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        with self.assertRaises(ValueError):
            validate_result(result)
        receipt = copy.deepcopy(outcome.alias_title_result["alias_title_receipt"])
        receipt["decision_credit_gain_nats"] = 0
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            validate_alias_title_receipt(receipt)
        effect = copy.deepcopy(outcome.effect_equivalence_receipt)
        effect["external_effect_detected"] = True
        effect.pop("receipt_sha256")
        effect["receipt_sha256"] = payload_sha256(effect)
        with self.assertRaises(ValueError):
            validate_cross_artifacts(
                outcome.parent.record_bound_result,
                outcome.alias_title_result,
                model_before=outcome.model_slot_receipt_before_alias_projection,
                transport_before=outcome.transport_health_before_alias_projection,
                search_before=outcome.search_single_shot_receipt_before_alias_projection,
                model_after=outcome.model_slot_receipt,
                transport_after=outcome.transport_health,
                search_after=outcome.search_single_shot_receipt,
                effect_equivalence_receipt=effect,
                expected_model_cap=2,
            )

    def test_public_receipt_contains_no_private_content(self) -> None:
        _, outcome, _, _ = self.fixture["support"]
        encoded = json.dumps(
            outcome.alias_title_result["alias_title_receipt"],
            ensure_ascii=False,
            sort_keys=True,
        )
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "usq-one.example",
            "1967",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24524_alias_title_integration.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
