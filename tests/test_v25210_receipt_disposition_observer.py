from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25180_quote_aware_production_runtime as quote  # noqa: E402
from deepwide_agent import v25210_receipt_disposition_observer as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25135_sparse_production_runtime import (  # noqa: E402
    FailingProductionModel,
    SparseProductionRuntimeTests,
)
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    EscapedProductionModel,
    NO_GAIN_CONTENT,
    V25180QuoteAwareProductionRuntimeTests,
)


class V25210ReceiptDispositionObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sparse_helper = SparseProductionRuntimeTests(methodName="runTest")
        _inner, _searches, sparse_no_gain = sparse_helper._run(field_page=False)
        _inner, _searches, sparse_gain = sparse_helper._run(field_page=True)
        _inner, _searches, sparse_fallback = sparse_helper._run(
            field_page=True, inner=FailingProductionModel()
        )
        cls.sparse_receipts = [
            copy.deepcopy(value["content_free_receipt"])
            for value in (sparse_no_gain, sparse_gain, sparse_fallback)
        ]

        quote_helper = V25180QuoteAwareProductionRuntimeTests(methodName="runTest")
        _inner, _searches, quote_inactive = quote_helper._run(
            quote, content=NO_GAIN_CONTENT
        )
        _inner, _searches, quote_active = quote_helper._run(
            quote,
            content=NO_GAIN_CONTENT,
            inner=EscapedProductionModel(),
        )
        cls.quote_receipts = [
            copy.deepcopy(value["content_free_receipt"])
            for value in (quote_inactive, quote_active)
        ]

    @staticmethod
    def _reseal(value: dict) -> dict:
        changed = copy.deepcopy(value)
        changed.pop("receipt_payload_sha256", None)
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        return changed

    def test_valid_sparse_states_have_exact_frozen_parity(self) -> None:
        for receipt in self.sparse_receipts:
            with self.subTest(kind=receipt["production_provider_output_valid"]):
                observation = target.observe_sparse_receipt(receipt)
                self.assertEqual(observation["violation_codes"], [])
                self.assertIsNone(observation["primary_violation_code"])
                self.assertTrue(observation["frozen_validator_expected_to_accept"])
                self.assertEqual(sparse.validate_receipt(receipt), receipt)

    def test_valid_quote_states_have_exact_frozen_parity(self) -> None:
        for receipt in self.quote_receipts:
            with self.subTest(applied=receipt["quote_aware_repair_applied_count"]):
                observation = target.observe_quote_receipt(receipt)
                self.assertEqual(observation["violation_codes"], [])
                self.assertIsNone(observation["primary_violation_code"])
                self.assertTrue(observation["frozen_validator_expected_to_accept"])
                self.assertEqual(quote.validate_receipt(receipt), receipt)

    def test_sparse_mutations_are_finite_and_frozen_rejected(self) -> None:
        base = self.sparse_receipts[0]
        cases = {
            "provider_forward_accounting": {
                "provider_forward_count": base["provider_forward_count"] + 1
            },
            "verified_gain_contract": {
                "verified_source_identity_field_gain": True
            },
            "production_fallback_complement": {
                "production_fallback_used": base["production_provider_output_valid"]
            },
            "fixed_budget_caps": {"physical_fetch_cap": 15},
            "policy_false_flag": {
                "entropy_or_information_gain_assigns_signed_credit": True
            },
        }
        for expected, updates in cases.items():
            changed = copy.deepcopy(base)
            changed.update(updates)
            changed = self._reseal(changed)
            with self.subTest(expected=expected):
                observation = target.observe_sparse_receipt(changed)
                self.assertIn(expected, observation["violation_codes"])
                self.assertFalse(observation["frozen_validator_expected_to_accept"])
                with self.assertRaisesRegex(
                    ValueError, "V2.51.35 sparse production receipt drifted"
                ):
                    sparse.validate_receipt(changed)

    def test_quote_mutations_are_finite_and_frozen_rejected(self) -> None:
        inactive, active = self.quote_receipts
        cases = {
            "observer_entry_count": (inactive, {"raw_normalizer_observer_entry_count": 0}),
            "repair_attempt_contract": (inactive, {"quote_aware_repair_attempt_count": 1}),
            "export_completion_contract": (active, {"public_export_attempt_count": 0}),
            "production_fallback_complement": (
                inactive,
                {
                    "parent_production_fallback_used": inactive[
                        "parent_production_provider_output_valid"
                    ]
                },
            ),
            "policy_false_flag": (
                inactive,
                {"entropy_or_information_gain_assigns_signed_credit": True},
            ),
        }
        for expected, (base, updates) in cases.items():
            changed = copy.deepcopy(base)
            changed.update(updates)
            changed = self._reseal(changed)
            with self.subTest(expected=expected):
                observation = target.observe_quote_receipt(changed)
                self.assertIn(expected, observation["violation_codes"])
                self.assertFalse(observation["frozen_validator_expected_to_accept"])
                with self.assertRaisesRegex(
                    ValueError, "V2.51.80 quote-aware receipt drifted"
                ):
                    quote.validate_receipt(changed)

    def test_nested_receipt_tamper_is_classified_without_value_disclosure(self) -> None:
        active = copy.deepcopy(self.quote_receipts[1])
        active["quote_aware_repair_receipt"]["internal_entity_cell_count"] += 1
        active = self._reseal(active)
        observation = target.observe_quote_receipt(active)
        self.assertIn("nested_repair_contract", observation["violation_codes"])
        self.assertNotIn("country", json.dumps(observation, ensure_ascii=False))
        with self.assertRaises(ValueError):
            quote.validate_receipt(active)

    def test_primary_code_is_first_and_observation_tamper_fails(self) -> None:
        changed = copy.deepcopy(self.sparse_receipts[0])
        changed["provider_forward_count"] += 1
        changed["entropy_or_information_gain_assigns_signed_credit"] = True
        changed = self._reseal(changed)
        observation = target.observe_receipt_invariants(
            changed, receipt_kind=target.SPARSE_KIND
        )
        self.assertEqual(
            observation["primary_violation_code"],
            observation["violation_codes"][0],
        )
        tampered = copy.deepcopy(observation)
        tampered["primary_violation_code"] = "policy_false_flag"
        tampered.pop("receipt_payload_sha256")
        tampered["receipt_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_observation(tampered)

    def test_nonmapping_and_unknown_kind_fail_closed(self) -> None:
        with self.assertRaises(TypeError):
            target.observe_sparse_receipt(None)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            target.observe_quote_receipt(None)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            target.observe_receipt_invariants({}, receipt_kind="unknown")

    def test_representative_single_field_mutations_match_frozen_acceptance(self) -> None:
        representatives = (None, False, True, -1, 0, 1, 2, "", "x", [], {})
        groups = (
            (
                "sparse",
                self.sparse_receipts,
                target.observe_sparse_receipt,
                sparse.validate_receipt,
                set(target.SPARSE_VIOLATION_CODES),
            ),
            (
                "quote",
                self.quote_receipts,
                target.observe_quote_receipt,
                quote.validate_receipt,
                set(target.QUOTE_VIOLATION_CODES),
            ),
        )
        observed = 0
        for kind, receipts, observer, validator, allowed_codes in groups:
            for receipt_index, receipt in enumerate(receipts):
                for field in receipt:
                    if field == "receipt_payload_sha256":
                        continue
                    for replacement in representatives:
                        if (
                            type(receipt[field]) is type(replacement)
                            and receipt[field] == replacement
                        ):
                            continue
                        changed = copy.deepcopy(receipt)
                        changed[field] = copy.deepcopy(replacement)
                        changed = self._reseal(changed)
                        observation = observer(changed)
                        try:
                            validator(changed)
                        except BaseException:
                            frozen_accepts = False
                        else:
                            frozen_accepts = True
                        with self.subTest(
                            kind=kind,
                            receipt_index=receipt_index,
                            field=field,
                            replacement_type=type(replacement).__name__,
                        ):
                            self.assertEqual(
                                observation["frozen_validator_expected_to_accept"],
                                frozen_accepts,
                            )
                            self.assertTrue(
                                set(observation["violation_codes"]).issubset(
                                    allowed_codes
                                )
                            )
                        observed += 1
        self.assertEqual(observed, 2_411)

    def test_module_is_pure_label_blind_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v25210_receipt_disposition_observer.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
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
                    "open",
                    "read_text",
                    "write_text",
                }
            )
        )
        for forbidden in ("run_official_eval_local", "target/main", "ghp_", "tvly-dev-"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
