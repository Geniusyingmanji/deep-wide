from __future__ import annotations

import ast
import copy
import sys
import tempfile
import threading
import time
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
    v25200_post_effect_tolerant_vertical_receipt as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25158_vertical_key_value_candidate_runtime import (  # noqa: E402
    CandidateModel,
    GenericRecordSearch,
    TASK,
    V25158VerticalKeyValueCandidateTests,
    limits,
)


class V25200PostEffectTolerantVerticalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        helper = V25158VerticalKeyValueCandidateTests(methodName="runTest")
        _inner, result = helper._run(
            "Public background without requested fields."
        )
        cls.inactive = copy.deepcopy(result["content_free_receipt"])

    @staticmethod
    def _reseal(value: dict) -> dict:
        changed = copy.deepcopy(value)
        changed.pop("receipt_payload_sha256", None)
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        return changed

    def _safe_post_effect(self) -> dict:
        changed = copy.deepcopy(self.inactive)
        changed["parent_post_effect_failure_present"] = True
        return self._reseal(changed)

    def test_frozen_validator_rejects_exact_safe_parent_post_effect_state(self) -> None:
        value = self._safe_post_effect()
        with self.assertRaisesRegex(
            ValueError,
            "V2.51.58 vertical key-value candidate receipt drifted",
        ):
            target._FROZEN_VALIDATE(value)
        observation = target.observe_compatibility_state(value)
        self.assertTrue(observation["exact_safe_post_effect_state"])
        self.assertEqual(
            observation["frozen_violation_codes"], ["inactive_dynamic_zero"]
        )
        self.assertEqual(observation["safe_state_code"], target.SAFE_STATE_CODE)

    def test_compatibility_returns_original_receipt_bytes_unchanged(self) -> None:
        value = self._safe_post_effect()
        token = target.begin_task()
        try:
            checked = target.validate_receipt(value)
            self.assertEqual(checked, value)
            self.assertTrue(target.compatibility_applied())
        finally:
            target.end_task(token)

    def test_existing_valid_active_and_inactive_states_remain_frozen_valid(self) -> None:
        helper = V25158VerticalKeyValueCandidateTests(methodName="runTest")
        _inner, active_result = helper._run(
            "Domain: | .in\n\nType= | country-code\nTLD Manager: | 999"
        )
        for receipt in (self.inactive, active_result["content_free_receipt"]):
            with self.subTest(active=receipt["candidate_revision_entry_count"]):
                token = target.begin_task()
                try:
                    self.assertEqual(target.validate_receipt(receipt), receipt)
                    self.assertFalse(target.compatibility_applied())
                finally:
                    target.end_task(token)

    def test_nearby_unsafe_states_remain_rejected(self) -> None:
        safe = self._safe_post_effect()
        cases = {
            "prediction-not-preserved": {
                "production_prediction_preserved_on_failure": False
            },
            "prediction-changed": {
                "final_prediction_changed_from_production": True
            },
            "provider-failure": {"provider_failure_present": True},
            "projection-failure": {"projection_failure_present": True},
            "revision-failure": {"parent_revision_failure_present": True},
            "selector-built": {"selector_prompt_built": True},
            "production-conditioned": {"production_table_conditioned": True},
            "strict-json": {"selection_response_strict_json": True},
            "projection-valid": {"candidate_projection_valid": True},
            "nonzero-page": {"verified_incremental_page_count": 1},
            "nonzero-candidate": {"available_candidate_count": 1},
            "bad-context": {"context_cap_preserved": False},
            "bad-evidence": {"only_verified_incremental_evidence_supplied": False},
            "signed-credit": {
                "entropy_or_information_gain_assigns_signed_credit": True
            },
        }
        for name, updates in cases.items():
            changed = copy.deepcopy(safe)
            changed.update(updates)
            changed = self._reseal(changed)
            with self.subTest(name=name):
                observation = target.observe_compatibility_state(changed)
                self.assertFalse(observation["exact_safe_post_effect_state"])
                with self.assertRaises(ValueError):
                    target.validate_receipt(changed)

    def test_unsealed_state_and_nonmapping_remain_rejected(self) -> None:
        changed = self._safe_post_effect()
        changed["parent_result_payload_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            target.validate_receipt(changed)
        with self.assertRaises((TypeError, ValueError)):
            target.validate_receipt(None)  # type: ignore[arg-type]

    def test_install_is_idempotent_and_preserves_parent_result_validation(self) -> None:
        target.install_compatibility()
        target.install_compatibility()
        value = self._safe_post_effect()
        token = target.begin_task()
        try:
            self.assertEqual(parent.validate_receipt(value), value)
            self.assertTrue(target.compatibility_applied())
        finally:
            target.end_task(token)

    def test_real_parent_post_effect_fallback_is_terminal_without_candidate_entry(self) -> None:
        target.install_compatibility()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = CandidateModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(
                    TASK["question"],
                    phase,
                    content="Public background without requested fields.",
                )
                for phase in parent.PHASES
            }
            original = parent.sparse_parent.parent.validate_result

            def fail_after_effect(value):
                checked = original(value)
                if checked["content_free_receipt"][
                    "physical_model_logical_call_count"
                ]:
                    raise RuntimeError("synthetic post-effect failure")
                return checked

            parent.sparse_parent.parent.validate_result = fail_after_effect
            token = target.begin_task()
            try:
                result = parent.run_task(
                    TASK, model=model, searches=searches, limits=limits()
                )
                checked = parent.validate_result(result)
                self.assertTrue(target.compatibility_applied())
            finally:
                target.end_task(token)
                parent.sparse_parent.parent.validate_result = original
        receipt = checked["content_free_receipt"]
        sparse = checked["parent_result"]["content_free_receipt"]
        self.assertEqual(receipt["candidate_revision_entry_count"], 0)
        self.assertTrue(receipt["parent_post_effect_failure_present"])
        self.assertTrue(receipt["production_prediction_preserved_on_failure"])
        self.assertFalse(receipt["final_prediction_changed_from_production"])
        self.assertEqual(checked["prediction"], checked["production_prediction"])
        self.assertEqual(sparse["provider_forward_count"], inner.logical_calls)

    def test_task_contexts_are_thread_isolated(self) -> None:
        target.install_compatibility()
        barrier = threading.Barrier(2)
        values: list[tuple[str, bool]] = []

        def worker(name: str, receipt: dict) -> None:
            token = target.begin_task()
            try:
                barrier.wait(timeout=5)
                parent.validate_receipt(receipt)
                values.append((name, target.compatibility_applied()))
            finally:
                target.end_task(token)

        threads = [
            threading.Thread(
                target=worker, args=("normal", copy.deepcopy(self.inactive))
            ),
            threading.Thread(
                target=worker, args=("safe", self._safe_post_effect())
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(dict(values), {"normal": False, "safe": True})

    def test_observation_is_content_free_and_tamper_fails_closed(self) -> None:
        observation = target.observe_compatibility_state(
            self._safe_post_effect()
        )
        encoded = str(observation)
        for forbidden in ("Domain", ".in", "Unknown", "exact_quote"):
            self.assertNotIn(forbidden, encoded)
        changed = copy.deepcopy(observation)
        changed[
            "compatibility_can_change_receipt_prediction_routing_effect_budget_or_credit"
        ] = True
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_observation(changed)

    def test_module_is_label_blind_and_effect_free(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25200_post_effect_tolerant_vertical_receipt.py"
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
                {"complete", "search_many", "fetch_urls", "create_connection"}
            )
        )


if __name__ == "__main__":
    unittest.main()
