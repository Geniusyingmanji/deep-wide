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

from scripts import diagnose_v24605_v24604_title_provenance as target  # noqa: E402


class V24605V24604TitleProvenanceDiagnosisTests(unittest.TestCase):
    def test_public_selection_boundary_is_exactly_empty(self) -> None:
        observed = target.build_diagnosis(now=0)["observed_selection_boundary"]
        self.assertEqual(observed["visible_input_lead_count"], 783)
        self.assertEqual(observed["empty_title_lead_count"], 783)
        self.assertEqual(observed["nonempty_title_lead_count"], 0)

    def test_synthetic_chain_preserves_action_and_citation_titles(self) -> None:
        fidelity = target.build_diagnosis(now=0)["synthetic_transport_fidelity"]
        self.assertTrue(fidelity["synthetic_action_title_preserved_to_union"])
        self.assertTrue(fidelity["synthetic_citation_title_preserved_to_union"])
        self.assertTrue(
            fidelity["synthetic_union_titles_preserved_by_lead_projection"]
        )
        self.assertEqual(fidelity["concrete_request_owner"], "HardTotalWallNativeSearchClient")
        self.assertEqual(fidelity["concrete_chunk_owner"], "TaskUnionSingleShotMixin")

    def test_diagnosis_does_not_overattribute_root_cause(self) -> None:
        conclusions = target.build_diagnosis(now=0)["conclusions"]
        for name in (
            "v24604_proves_concrete_adapter_deleted_nonempty_provider_titles",
            "v24604_proves_real_provider_action_sources_omitted_titles",
            "v24604_proves_query_local_citations_omitted_titles",
            "v24604_observed_fetch_request_titles",
            "v24604_observed_fetched_page_titles",
            "direct_parser_or_validator_change_is_evidence_supported",
        ):
            self.assertFalse(conclusions[name])
        self.assertTrue(
            conclusions["next_successor_must_observe_title_provenance_boundaries"]
        )

    def test_authorization_is_observer_design_only(self) -> None:
        authorization = target.build_diagnosis(now=0)["authorization"]
        self.assertTrue(authorization["content_free_title_provenance_observer_design"])
        self.assertFalse(
            authorization["search_parser_title_validator_or_evidence_rule_change"]
        )
        self.assertFalse(authorization["fresh_external_protocol_design"])
        self.assertFalse(authorization["fresh_external_activation_or_launch"])
        self.assertFalse(authorization["paired_dev64_or_exact220"])

    def test_source_policy_is_label_blind_and_effect_free(self) -> None:
        source = target.build_diagnosis(now=0)["source_policy"]
        self.assertTrue(source["synthetic_payload_only"])
        self.assertFalse(source["prior_private_execution_directory_opened"])
        self.assertFalse(
            source[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(source["network_model_search_fetch_process_or_evaluator_called"])

    def test_resealed_overclaim_fails_closed(self) -> None:
        changed = copy.deepcopy(target.build_diagnosis(now=0))
        changed["conclusions"][
            "v24604_proves_real_provider_action_sources_omitted_titles"
        ] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
