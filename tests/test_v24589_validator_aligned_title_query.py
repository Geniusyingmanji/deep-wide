from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24523_conservative_alias_title_projection as validator  # noqa: E402
from deepwide_agent import v24529_alias_seeded_target_acquisition as acquisition  # noqa: E402
from deepwide_agent import v24547_alias_surface_observability as surface  # noqa: E402
from deepwide_agent import v24589_validator_aligned_title_query as target  # noqa: E402


class V24589ValidatorAlignedTitleQueryTests(unittest.TestCase):
    def test_full_and_core_queries_match_frozen_validator_surfaces(self) -> None:
        row = "Oxford Brookes University"
        full, second, mode = target._surface_vector(row)
        queries = target.validator_aligned_query_vector(
            row, "Founding year", "1865"
        )
        candidates = {
            " ".join(tokens)
            for _candidate_mode, tokens in validator._candidate_aliases(
                validator._canonical_tokens(row)
            )
        }
        self.assertEqual(mode, "distinctive_core")
        self.assertIn(full, candidates)
        self.assertIn(second, candidates)
        self.assertIn(f'"{full}"', queries[0])
        self.assertIn(f'"{second}"', queries[1])
        self.assertIn('"1865"', queries[0])
        self.assertIn('"1865"', queries[1])

    def test_query_does_not_force_preferred_initialism_with_full_surface(self) -> None:
        row = "Oxford Brookes University"
        queries = target.validator_aligned_query_vector(row, "Founding year")
        self.assertEqual(acquisition.primary_alias_surface(row), "obu")
        self.assertNotIn('"obu"', queries[0].casefold())
        self.assertNotIn('"obu"', queries[1].casefold())
        self.assertEqual(len(queries), 2)

    def test_initialism_is_used_only_when_distinctive_core_is_absent(self) -> None:
        row = "EPHEC University College"
        full, second, mode = target._surface_vector(row)
        queries = target.validator_aligned_query_vector(row, "Founding year")
        self.assertEqual(mode, "initialism")
        self.assertEqual(second, "euc")
        self.assertIn(f'"{full}"', queries[0])
        self.assertIn('"euc"', queries[1])

    def test_full_fallback_still_produces_two_distinct_queries(self) -> None:
        with patch.object(
            target.validator,
            "_candidate_aliases",
            return_value=((target.validator.ALIAS_MODES[0], ("longname",)),),
        ):
            full, second, mode = target._surface_vector("Longname")
            queries = target.validator_aligned_query_vector(
                "Longname", "Founding year"
            )
        self.assertEqual((full, second, mode), ("longname", "longname", "full_fallback"))
        self.assertEqual(len(set(queries)), 2)

    def test_context_is_observed_by_surface_policy_and_restores(self) -> None:
        original = acquisition.alias_seeded_query_vector
        with target.ValidatorAlignedTitleQuery() as aligned:
            with surface.AliasSurfaceObservability() as observed:
                queries = surface.targeted._query_vector(
                    "Oxford Brookes University", "Founding year", "1865"
                )
                discovery = surface.neutral._discovery_query_vector(
                    "University of Hertfordshire", "Founding year"
                )
            surface.validate_receipt(observed.content_free_receipt())
        self.assertIs(acquisition.alias_seeded_query_vector, original)
        self.assertEqual(len(queries), 2)
        self.assertEqual(len(discovery), 2)
        receipt = target.validate_receipt(aligned.content_free_receipt())
        self.assertEqual(receipt["query_vector_calls"], 2)
        self.assertEqual(receipt["targeted_query_vector_calls"], 1)
        self.assertEqual(receipt["discovery_query_vector_calls"], 1)
        self.assertEqual(receipt["logical_query_count"], 4)
        self.assertEqual(receipt["full_surface_first_query_calls"], 2)
        self.assertEqual(receipt["distinctive_core_second_query_calls"], 2)

    def test_visible_input_validation_and_query_cap_are_total(self) -> None:
        for row, column in (("", "Founding year"), ("Alpha University", "")):
            with self.assertRaises(ValueError):
                target.validator_aligned_query_vector(row, column)
        queries = target.validator_aligned_query_vector(
            "University of Applied Sciences and Arts Northwestern Switzerland",
            "Founding year",
            "1900",
        )
        self.assertEqual(len(queries), 2)
        self.assertTrue(all(0 < len(item) <= 1_200 for item in queries))

    def test_receipt_tamper_and_binding_drift_fail_closed(self) -> None:
        with target.ValidatorAlignedTitleQuery() as aligned:
            acquisition.alias_seeded_query_vector(
                "Oxford Brookes University", "Founding year"
            )
        receipt = aligned.content_free_receipt()
        for name, value in (
            ("bindings_restored", False),
            ("logical_query_count", 3),
            (
                "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit",
                True,
            ),
        ):
            changed = copy.deepcopy(receipt)
            changed[name] = value
            with self.assertRaises(ValueError):
                target.validate_receipt(changed)
        with patch.object(
            acquisition, "alias_seeded_query_vector", lambda *_args, **_kwargs: []
        ):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                target.ValidatorAlignedTitleQuery().__enter__()

    def test_policy_is_label_blind_and_has_no_external_effect(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24589_validator_aligned_title_query.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        receipt = target.ValidatorAlignedTitleQuery().content_free_receipt()
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(
            receipt[
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy"
            ]
        )
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
