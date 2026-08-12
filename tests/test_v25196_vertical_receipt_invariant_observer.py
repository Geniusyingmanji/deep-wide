from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25158_vertical_key_value_candidate_runtime as parent,
)
from deepwide_agent import (  # noqa: E402
    v25196_vertical_receipt_invariant_observer as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25158_vertical_key_value_candidate_runtime import (  # noqa: E402
    V25158VerticalKeyValueCandidateTests,
    VERTICAL,
)


class V25196VerticalReceiptInvariantObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        helper = V25158VerticalKeyValueCandidateTests(methodName="runTest")
        _inner, result = helper._run(VERTICAL)
        cls.receipt = copy.deepcopy(result["content_free_receipt"])

    def _changed(self, **updates) -> dict:
        value = copy.deepcopy(self.receipt)
        value.update(updates)
        value.pop("receipt_payload_sha256", None)
        value["receipt_payload_sha256"] = payload_sha256(value)
        return value

    def test_valid_receipt_has_zero_violations_and_parent_accepts(self) -> None:
        observation = target.observe_receipt_invariants(self.receipt)
        self.assertEqual(observation["violation_codes"], [])
        self.assertEqual(observation["violation_count"], 0)
        self.assertTrue(observation["frozen_validator_expected_to_accept"])
        self.assertEqual(parent.validate_receipt(self.receipt), self.receipt)

    def test_content_free_success_receipts_from_frozen_gate_have_zero_violations(self) -> None:
        path = (
            ROOT
            / "outputs/v25195_failure_observable_quality_v1_20260812/frozen_task_results.jsonl"
        )
        observed = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if not row["runtime_completed"]:
                continue
            receipts = []

            def walk(value) -> None:
                if isinstance(value, dict):
                    if value.get("role") == parent.RECEIPT_ROLE:
                        receipts.append(value)
                    for child in value.values():
                        walk(child)
                elif isinstance(value, list):
                    for child in value:
                        walk(child)

            walk(row)
            self.assertEqual(len(receipts), 1)
            observation = target.observe_receipt_invariants(receipts[0])
            self.assertEqual(observation["violation_codes"], [])
            observed += 1
        self.assertEqual(observed, 19)

    def test_mutations_are_finitely_classified_and_frozen_parent_rejects(self) -> None:
        cases = {
            "entry_forward_relation": self._changed(
                underlying_provider_forward_count=2
            ),
            "candidate_page_relation": self._changed(
                candidate_source_page_count=
                self.receipt["verified_incremental_page_count"] + 1
            ),
            "vertical_structure_relation": self._changed(
                vertical_identity_bound_block_count=
                self.receipt["vertical_pipe_block_count"] + 1
            ),
            "grammar_accounting": self._changed(
                raw_candidate_observation_count=
                self.receipt["raw_candidate_observation_count"] + 1
            ),
            "candidate_partition_accounting": self._changed(
                verifier_admissible_candidate_count=
                self.receipt["verifier_admissible_candidate_count"] + 1
            ),
            "candidate_cardinality_order": self._changed(
                supplied_candidate_count=
                self.receipt["available_candidate_count"] + 1
            ),
            "parent_revision_entry_parity": self._changed(
                parent_revision_eligible=False
            ),
            "fixed_evidence_or_context_flag": self._changed(
                context_cap_preserved=False
            ),
            "selector_prompt_contract": self._changed(
                production_table_conditioned=False
            ),
            "projection_contract": self._changed(
                selection_response_strict_json=False
            ),
            "prediction_change_contract": self._changed(
                final_prediction_changed_from_production=False
            ),
            "failure_parent_contract": self._changed(
                projection_failure_present=True,
                parent_revision_failure_present=False,
            ),
            "failure_preservation_contract": self._changed(
                parent_post_effect_failure_present=True,
                production_prediction_preserved_on_failure=False,
            ),
            "policy_true_flag": self._changed(
                model_can_only_select_candidate_ids_or_abstain=False
            ),
            "policy_false_flag": self._changed(
                entropy_or_information_gain_assigns_signed_credit=True
            ),
        }
        for expected, value in cases.items():
            with self.subTest(expected=expected):
                observation = target.observe_receipt_invariants(value)
                self.assertIn(expected, observation["violation_codes"])
                self.assertFalse(
                    observation["frozen_validator_expected_to_accept"]
                )
                with self.assertRaises(ValueError):
                    parent.validate_receipt(value)

    def test_unsealed_mutation_reports_payload_seal_without_value_disclosure(self) -> None:
        changed = copy.deepcopy(self.receipt)
        changed["available_candidate_count"] += 1
        observation = target.observe_receipt_invariants(changed)
        self.assertIn("payload_seal", observation["violation_codes"])
        encoded = json.dumps(observation)
        for forbidden in ("Domain", ".in", "999", "exact_quote"):
            self.assertNotIn(forbidden, encoded)

    def test_observation_tamper_fails_closed(self) -> None:
        observation = target.observe_receipt_invariants(self.receipt)
        changed = copy.deepcopy(observation)
        changed["violation_codes"] = ["grammar_accounting"]
        changed["violation_count"] = 1
        changed["frozen_validator_expected_to_accept"] = False
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        target.validate_observation(changed)
        changed["entropy_or_information_gain_assigns_signed_credit"] = True
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_observation(changed)

    def test_module_is_pure_label_blind_and_effect_free(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25196_vertical_receipt_invariant_observer.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        privileged = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        hits = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in privileged
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertEqual(hits, set())
        self.assertTrue(
            calls.isdisjoint(
                {
                    "complete",
                    "search_many",
                    "fetch_urls",
                    "create_connection",
                    "read_text",
                    "write_text",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
