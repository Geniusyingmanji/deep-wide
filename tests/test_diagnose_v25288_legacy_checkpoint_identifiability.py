from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25288_legacy_checkpoint_identifiability as target  # noqa: E402


class V25288LegacyCheckpointIdentifiabilityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_fixed_inputs_and_parent_aggregates_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_inputs(),
            {str(path): digest for path, digest in target.FIXED_HASHES.items()},
        )
        _checkpoint, production, _forward, summary = target._parent_barrier()
        self.assertEqual(summary["parent_exit_taxonomy"], {"success": 220})
        self.assertEqual(summary["model_generated_tables"], 220)
        self.assertEqual(summary["fallback_tables"], 0)
        self.assertEqual(
            production["aggregate"]["stage_failure_stage_type_counts"],
            {"sparse_production:ValueError": 11},
        )

    def test_recovery_surface_is_postforward_effect_free_and_not_input_routed(self) -> None:
        reachability = target._source_reachability()
        self.assertTrue(
            reachability["legacy_forward_completes_before_envelope_build"]
        )
        self.assertTrue(
            reachability[
                "checkpoint_revalidates_parent_cross_artifacts_before_recovery_surface"
            ]
        )
        self.assertFalse(
            reachability[
                "recoverable_surface_contains_query_fetch_model_or_network_call"
            ]
        )
        self.assertFalse(
            reachability[
                "recoverable_surface_contains_input_dependent_treatment_branch"
            ]
        )

    def test_diagnosis_is_no_go_without_external_launch(self) -> None:
        self.assertTrue(self.value["diagnosis_valid"])
        self.assertEqual(self.value["findings"], [])
        decision = self.value["decision"]
        self.assertEqual(
            decision["fresh_checkpoint_quality_population_or_forward"],
            "no_go_without_launch",
        )
        self.assertFalse(decision["counterfactual_prediction_change_established"])
        self.assertFalse(decision["quality_delta_can_be_attributed_to_checkpoint"])
        self.assertTrue(
            decision["next_candidate_must_change_normal_path_prediction_under_shared_prefix"]
        )
        self.assertFalse(
            self.value["authorization"]["external_activation_or_launch"]
        )

    def test_v25265_failure_rate_is_not_transferred_to_v25286(self) -> None:
        evidence = self.value["nontransferable_failure_evidence"]
        self.assertEqual(evidence["production_chain_outer_failure_count"], 11)
        self.assertEqual(
            evidence["production_chain_runtime_family"],
            "v25265_sparse_production",
        )
        self.assertEqual(
            evidence["legacy_checkpoint_runtime_family"],
            "v24630_thin_exact220",
        )
        self.assertFalse(
            evidence["production_chain_failure_rate_used_as_v25286_event_rate"]
        )

    def test_resealed_count_stage_credit_authorization_or_decision_tamper_fails(self) -> None:
        for kind in (
            "count",
            "stage",
            "credit",
            "authorization",
            "decision",
            "content",
            "check_hidden",
        ):
            changed = copy.deepcopy(self.value)
            if kind == "count":
                changed["observed_legacy_aggregate"][
                    "observed_v25286_natural_recovery"
                ] = 1
            elif kind == "stage":
                changed["nontransferable_failure_evidence"][
                    "failure_stage_equals_v25286_recoverable_stage"
                ] = True
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            elif kind == "authorization":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "decision":
                changed["decision"][
                    "fresh_checkpoint_quality_population_or_forward"
                ] = "go"
            elif kind == "content":
                changed["content_policy"]["runtime_task_rows_opened"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.seal.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_has_no_network_model_search_or_evaluator_capability(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "import requests",
            "import subprocess",
            "from urllib",
            "urlopen(",
            "socket.",
            "Popen(",
            "HardTotalWallResponsesClient(",
            "AzureNativeSearchClient(",
            "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
