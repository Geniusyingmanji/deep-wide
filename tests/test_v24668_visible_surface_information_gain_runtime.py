from __future__ import annotations

import copy
import json
import math
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24637_objective_alignment_runtime import payload_sha256  # noqa: E402
from deepwide_agent.v24668_visible_surface_information_gain_runtime import (  # noqa: E402
    run_v24668_task,
    select_visible_surface_information_gain_leads,
    validate_result,
)
from test_v24655_unknown_cell_targeted_runtime import (  # noqa: E402
    Model,
    Search,
    TASK,
    limits,
    revision,
    table,
)


def reseal(value: dict) -> None:
    value["receipt"].pop("receipt_sha256", None)
    value["receipt"]["receipt_sha256"] = payload_sha256(value["receipt"])
    value.pop("result_sha256", None)
    value["result_sha256"] = payload_sha256(value)


def batches() -> list[dict]:
    return [
        {
            "query": '"Alpha Phone" "Release Date"',
            "results": [
                {
                    "title": "Generic product database",
                    "url": "https://first.example/record",
                },
                {
                    "title": "Alpha Phone official release",
                    "url": "https://aligned.example/record",
                },
                {
                    "title": "Release archive",
                    "url": "https://archive.example/alpha-phone/history",
                },
                {
                    "title": "Other page",
                    "url": "https://other.example/record",
                },
            ],
        }
    ]


class V24668InformationGainRuntimeTests(unittest.TestCase):
    def test_one_target_concentrates_four_fetches_and_keeps_strict_gate(self) -> None:
        baseline = table(alpha_date="Unknown", beta_maker="Unknown")
        model = Model(
            values=[Model().values[0], baseline, revision(beta_maker="Unknown")]
        )
        search = Search()
        result = run_v24668_task(
            TASK,
            model=model,
            search=search,
            limits=limits(),
            monotonic=time.monotonic,
        )
        validate_result(result)
        receipt = result["receipt"]
        self.assertEqual([len(vector) for vector in search.search_vectors], [2, 1])
        self.assertEqual([len(vector) for vector in search.fetch_vectors], [6, 4])
        self.assertEqual(receipt["selected_unknown_target_count"], 1)
        self.assertEqual(receipt["targeted_fetch_targets"], 4)
        self.assertEqual(receipt["admitted_cell_change_count"], 1)
        self.assertFalse(receipt["support_threshold_relaxed"])
        self.assertFalse(receipt["positive_decision_credit_assigned"])

    def test_aligned_sources_rank_before_earlier_generic_leads(self) -> None:
        selected, eligible, diagnostic = select_visible_surface_information_gain_leads(
            batches(),
            row_key="Alpha Phone",
            excluded_sources=set(),
            excluded_urls=set(),
            limit=2,
        )
        self.assertEqual(len(eligible), 4)
        self.assertIn("Alpha Phone", selected[0]["title"])
        self.assertIn("alpha-phone", selected[1]["url"])
        self.assertEqual(diagnostic["visible_surface_aligned_source_count"], 2)
        self.assertEqual(diagnostic["visible_surface_selected_aligned_lead_count"], 2)
        self.assertAlmostEqual(
            diagnostic["visible_surface_localization_information_gain_nats"],
            math.log(2),
            places=11,
        )

    def test_later_aligned_representative_replaces_same_source_first(self) -> None:
        raw = batches()
        raw[0]["results"] = [
            {
                "title": "Generic page",
                "url": "https://www.example.edu/generic",
            },
            {
                "title": "Alpha Phone official release",
                "url": "https://records.example.edu/alpha-phone",
            },
            {
                "title": "Other",
                "url": "https://independent.example/record",
            },
        ]
        selected, eligible, diagnostic = select_visible_surface_information_gain_leads(
            raw,
            row_key="Alpha Phone",
            excluded_sources=set(),
            excluded_urls=set(),
            limit=2,
        )
        self.assertEqual(eligible, {"example.edu", "independent.example"})
        self.assertEqual(selected[0]["url"], "https://records.example.edu/alpha-phone")
        self.assertEqual(
            diagnostic["visible_surface_source_representative_replacement_count"], 1
        )

    def test_query_only_match_cannot_self_prove_alignment_or_credit(self) -> None:
        raw = [
            {
                "query": '"Alpha Phone" "Release Date"',
                "results": [
                    {
                        "title": "Generic database",
                        "url": "https://generic.example/record",
                    }
                ],
            }
        ]
        selected, eligible, diagnostic = select_visible_surface_information_gain_leads(
            raw,
            row_key="Alpha Phone",
            excluded_sources=set(),
            excluded_urls=set(),
            limit=4,
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(eligible, {"generic.example"})
        self.assertEqual(diagnostic["visible_surface_aligned_source_count"], 0)
        self.assertEqual(diagnostic["epistemic_action_credit_nats"], 0.0)

    def test_unresolved_declared_id_still_fails_closed(self) -> None:
        proposal = json.loads(revision())
        proposal["cell_evidence"][0]["evidence_ids"] = ["R9999"]
        result = run_v24668_task(
            TASK,
            model=Model(
                values=[Model().values[0], Model().values[1], json.dumps(proposal)]
            ),
            search=Search(),
            limits=limits(),
            monotonic=time.monotonic,
        )
        self.assertEqual(
            result["predictions"]["baseline"],
            result["predictions"]["unknown_cell_targeted"],
        )
        self.assertEqual(result["receipt"]["admitted_cell_change_count"], 0)

    def test_resealed_decision_credit_or_target_cap_tamper_fails(self) -> None:
        result = run_v24668_task(
            TASK,
            model=Model(),
            search=Search(),
            limits=limits(),
            monotonic=time.monotonic,
        )
        for field, value in (
            ("positive_decision_credit_assigned", True),
            ("selected_unknown_target_cap", 2),
        ):
            changed = copy.deepcopy(result)
            changed["receipt"][field] = value
            reseal(changed)
            with self.assertRaises(ValueError):
                validate_result(changed)

    def test_entropy_credit_is_action_level_not_outer_utility(self) -> None:
        selected, _eligible, diagnostic = select_visible_surface_information_gain_leads(
            batches(),
            row_key="Alpha Phone",
            excluded_sources=set(),
            excluded_urls=set(),
            limit=1,
        )
        self.assertEqual(len(selected), 1)
        self.assertGreater(diagnostic["epistemic_action_credit_nats"], 0)
        result = run_v24668_task(
            TASK,
            model=Model(),
            search=Search(),
            limits=limits(),
            monotonic=time.monotonic,
        )
        self.assertFalse(result["receipt"]["positive_decision_credit_assigned"])
        self.assertFalse(result["receipt"]["postfreeze_outer_utility_observed"])

    def test_runtime_source_is_label_blind_and_has_no_capability_imports(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        path = Path(
            "src/deepwide_agent/v24668_visible_surface_information_gain_runtime.py"
        )
        accesses, imports = audit.ast_findings(path)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        source = (ROOT / path).read_text(encoding="utf-8")
        for marker in ("evaluation/", "ground_truth", "answer_key", "results.csv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
