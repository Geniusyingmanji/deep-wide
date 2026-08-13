from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25308_worldbank_population_postfreeze as target  # noqa: E402


class V25308WorldBankPopulationPostfreezeTests(unittest.TestCase):
    def test_fixed_inputs_and_commit_boundaries_are_exact(self) -> None:
        self.assertEqual(
            target._fixed(),
            {str(path): digest for path, digest in target.EXPECTED_FIXED.items()},
        )
        self.assertEqual(target._changed_paths(target.START_COMMIT), [str(target.runner.EXECUTION_START)])
        self.assertEqual(len(target._changed_paths(target.FREEZE_COMMIT)), 52)

    def test_raw_replay_reconstructs_exact_population(self) -> None:
        replay = target._replay()
        self.assertTrue(replay["response_binding_valid"])
        self.assertTrue(replay["private_population_valid"])
        self.assertEqual(len(replay["target_keys"]), 24)
        self.assertEqual(len(replay["response_vector"]), 48)
        self.assertEqual(len(replay["replayed_population"]["target_keys"]), 4)
        self.assertEqual(len(replay["replayed_population"]["entities"]), 144)
        self.assertEqual(len(replay["replayed_population"]["tasks"]), 12)

    def test_audit_authorizes_protocol_design_only(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["external_monotone_fill_mechanism_protocol_design"])
        self.assertFalse(value["authorization"]["external_monotone_fill_forward_or_postfreeze_evaluator"])
        self.assertFalse(value["authorization"]["v25305_retry_resume_refetch_backfill_replacement_or_second_population_freeze"])

    def test_resealed_population_effect_authority_or_hidden_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("population", "effect", "authority", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "population":
                changed["population"]["entity_count"] = 143
            elif kind == "effect":
                changed["effect_accounting"]["target_provider_attempt_count"] = 47
            elif kind == "authority":
                changed["authorization"]["external_monotone_fill_forward_or_postfreeze_evaluator"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runner.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_network_model_or_evaluator_call(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "requests.",
            "urlopen(",
            "invoke_helper(",
            "execute_freeze(",
            "run_official_eval_local",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
