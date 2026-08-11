from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diagnose_v25064_three_run_strategy as target  # noqa: E402


class V25064ThreeRunStrategyDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_fixed_aggregate_scores_and_costs(self) -> None:
        runs = self.value["runs"]
        self.assertEqual(runs["v24857"]["whole_table_successes"], 9)
        self.assertEqual(runs["v25030"]["whole_table_successes"], 7)
        self.assertEqual(runs["v25057"]["whole_table_successes"], 6)
        self.assertEqual(runs["v24857"]["system_total_tokens"], 3_781_060)
        self.assertEqual(runs["v25030"]["system_total_tokens"], 13_973_126)
        self.assertEqual(runs["v25057"]["system_total_tokens"], 14_302_160)

    def test_record_binding_never_naturally_engaged(self) -> None:
        for run in ("v25030", "v25057"):
            counts = self.value["runs"][run]["retrieval"]["record_binding_counts"]
            self.assertEqual(counts["discovered_records"], 0)
            self.assertEqual(counts["admissible_records"], 0)
            self.assertEqual(counts["retained_records"], 0)
        self.assertEqual(
            self.value["runs"]["v25057"]["page_self_projection"][
                "mechanism_exposed_pages"
            ],
            0,
        )

    def test_extra_query_refinement_cost_did_not_establish_quality_gain(self) -> None:
        comparison = self.value["comparisons"]["v25030_minus_v24857"]
        self.assertEqual(comparison["whole_table_success_delta"], -2)
        self.assertLess(comparison["quality_composite_delta"], 0)
        self.assertGreater(comparison["system_total_token_ratio"], 3.0)
        diagnosis = self.value["diagnosis"]
        self.assertFalse(
            diagnosis[
                "evidence_conditioned_query_refinement_established_as_quality_improvement"
            ]
        )

    def test_next_candidate_is_quote_verified_record_binding(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertTrue(
            diagnosis[
                "next_candidate_reallocates_existing_model_call_to_record_proposal_and_deterministic_quote_verification"
            ]
        )
        self.assertTrue(
            diagnosis[
                "next_candidate_must_not_increase_query_fetch_model_context_token_or_wall_caps"
            ]
        )
        self.assertEqual(diagnosis["entropy_or_information_gain_signed_credit"], 0)

    def test_receipt_scanner_never_decodes_unselected_top_level_values(self) -> None:
        raw = json.dumps(
            {
                "first_wave_receipt": {name: 0 for name in target.WAVE_FIELDS},
                "question": {"gold": "must-not-decode"},
                "second_wave_receipt": {name: 0 for name in target.WAVE_FIELDS},
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
                "entropy_or_information_gain_assigns_signed_credit": False,
            }
        )
        original = json.loads
        decoded: list[str] = []

        def observed(value: str, *args, **kwargs):
            decoded.append(value)
            return original(value, *args, **kwargs)

        with mock.patch.object(
            sys.modules[
                "scripts.diagnose_v25063_three_run_output_structure"
            ].json,
            "loads",
            side_effect=observed,
        ):
            selected = target.selected_top_level_fields(raw, target.RECEIPT_FIELDS)
        self.assertEqual(set(selected), set(target.RECEIPT_FIELDS))
        self.assertFalse(any("must-not-decode" in item for item in decoded))

    def test_authority_is_build_only(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["source_record_binding_build_design"])
        self.assertFalse(authorization["fresh_external_protocol_publication"])
        self.assertFalse(authorization["fresh_external_launch"])
        self.assertFalse(authorization["new_exact220_launch"])
        self.assertFalse(authorization["leaderboard_or_sota"])

    def test_resealed_sensitive_or_launch_tamper_fails(self) -> None:
        for mutation in ("sensitive", "launch", "credit", "score"):
            changed = copy.deepcopy(self.value)
            if mutation == "sensitive":
                changed["content_policy"][
                    "task_identifier_materialized_or_cross_run_per_task_joined"
                ] = True
            elif mutation == "launch":
                changed["authorization"]["new_exact220_launch"] = True
            elif mutation == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            else:
                changed["runs"]["v24857"]["whole_table_successes"] = 10
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagnosis.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)

    def test_isolated_cli_imports_repository_scanner(self) -> None:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                "-c",
                (
                    "import runpy; value=runpy.run_path("
                    + repr(str(ROOT / target.SOURCE))
                    + "); assert str(value['ROOT'])=="
                    + repr(str(ROOT))
                ),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
