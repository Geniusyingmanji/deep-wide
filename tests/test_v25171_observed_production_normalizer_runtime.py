from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25165_observed_vertical_key_value_runtime as frozen  # noqa: E402
from deepwide_agent import v25171_observed_production_normalizer_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import TASK  # noqa: E402
from test_v25147_deterministic_quote_candidate_runtime import CandidateModel  # noqa: E402
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)


VERTICAL = "Domain | .in\nType | country-code\nTLD Manager | 999"


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=240,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class MalformedProductionModel(CandidateModel):
    def __init__(self, *, truncated: bool = False) -> None:
        super().__init__()
        self.truncated = truncated

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 2:
            self.prompts.append((str(system), str(user), bool(json_mode)))
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            return ModelResult(
                text="production prose without a markdown table",
                usage={},
                response_id=None,
                attempts=1,
                output_truncated=self.truncated,
            )
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class V25171ObservedProductionNormalizerRuntimeTests(unittest.TestCase):
    @classmethod
    def _without_hashes(cls, value):
        if isinstance(value, dict):
            return {
                key: cls._without_hashes(child)
                for key, child in value.items()
                if not str(key).endswith("sha256")
            }
        if isinstance(value, list):
            return [cls._without_hashes(child) for child in value]
        return value

    @staticmethod
    def _behavior_surface(value):
        parent = value["parent_result"]["parent_result"]
        return {
            "production_prediction": value["production_prediction"],
            "prediction": value["prediction"],
            "prediction_kind": value["prediction_kind"],
            "cost": value["cost"],
            "vertical_candidate_receipt": V25171ObservedProductionNormalizerRuntimeTests._without_hashes(
                value["parent_result"]["content_free_receipt"]
            ),
            "sparse_receipt": parent["content_free_receipt"],
            "failure_types": parent["failure_types"],
        }

    def _run(
        self,
        module,
        *,
        content: str,
        inner=None,
        observer_failure: bool = False,
    ):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = inner or CandidateModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(TASK["question"], phase, content=content)
                for phase in module.PHASES
            }
            patcher = (
                mock.patch.object(
                    target.observer,
                    "observe_production_normalization",
                    side_effect=RuntimeError("synthetic observer failure"),
                )
                if observer_failure
                else mock.patch.object(
                    target.observer,
                    "observe_production_normalization",
                    wraps=target.observer.observe_production_normalization,
                )
            )
            with patcher:
                value = module.run_task(
                    TASK, model=model, searches=searches, limits=limits()
                )
        validator = module.validate_result
        return inner, validator(value)

    def test_valid_production_observation_preserves_full_parent_result(self) -> None:
        baseline_inner, baseline = self._run(frozen, content=VERTICAL)
        inner, result = self._run(target, content=VERTICAL)
        receipt = result["content_free_receipt"]
        observation = receipt["production_normalizer_observation"]
        self.assertEqual(inner.logical_calls, baseline_inner.logical_calls)
        self.assertEqual(
            self._behavior_surface(result["parent_result"]),
            self._behavior_surface(baseline),
        )
        self.assertEqual(result["prediction"], baseline["prediction"])
        self.assertEqual(result["cost"], baseline["cost"])
        self.assertEqual(receipt["production_normalizer_observer_entry_count"], 1)
        self.assertEqual(
            receipt["production_normalizer_observer_completed_count"], 1
        )
        self.assertTrue(observation["frozen_synthesis_contract_accepted"])
        self.assertTrue(receipt["parent_production_provider_output_valid"])

    def test_invalid_production_is_observed_before_unchanged_fallback(self) -> None:
        baseline_inner, baseline = self._run(
            frozen, content=VERTICAL, inner=MalformedProductionModel(truncated=True)
        )
        inner, result = self._run(
            target, content=VERTICAL, inner=MalformedProductionModel(truncated=True)
        )
        receipt = result["content_free_receipt"]
        observation = receipt["production_normalizer_observation"]
        self.assertEqual(inner.logical_calls, baseline_inner.logical_calls)
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(
            self._behavior_surface(result["parent_result"]),
            self._behavior_surface(baseline),
        )
        self.assertEqual(result["prediction_kind"], "fallback")
        self.assertFalse(receipt["parent_production_provider_output_valid"])
        self.assertTrue(receipt["parent_production_fallback_used"])
        self.assertFalse(observation["frozen_synthesis_contract_accepted"])
        self.assertTrue(observation["provider_output_truncated"])
        self.assertEqual(
            observation["disposition_counts"]["no_pipe_group_reject"], 1
        )
        self.assertEqual(
            result["parent_result"]["content_free_receipt"][
                "disposition_observer_entry_count"
            ],
            0,
        )

    def test_no_gain_still_observes_production_but_not_vertical_revision(self) -> None:
        inner, result = self._run(
            target, content="Public background without requested fields."
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["production_normalizer_observer_entry_count"], 1)
        self.assertEqual(
            result["parent_result"]["content_free_receipt"][
                "disposition_observer_entry_count"
            ],
            0,
        )

    def test_observer_failure_isolated_and_parent_result_is_unchanged(self) -> None:
        _baseline_inner, baseline = self._run(frozen, content=VERTICAL)
        inner, result = self._run(
            target, content=VERTICAL, observer_failure=True
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(
            self._behavior_surface(result["parent_result"]),
            self._behavior_surface(baseline),
        )
        self.assertTrue(
            receipt["production_normalizer_observer_failure_present"]
        )
        self.assertEqual(
            receipt["production_normalizer_observer_failure_type"], "RuntimeError"
        )
        self.assertIsNone(receipt["production_normalizer_observation"])

    def test_receipt_is_content_free_and_tamper_fails_closed(self) -> None:
        _inner, result = self._run(
            target, content=VERTICAL, inner=MalformedProductionModel()
        )
        receipt = result["content_free_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False)
        for forbidden in (
            "production prose",
            ".in",
            "999",
            "Domain",
            TASK["opaque_id"],
            "https://",
        ):
            self.assertNotIn(forbidden, encoded)
        for kind in ("count", "parent", "behavior", "credit"):
            changed = copy.deepcopy(result)
            observed = changed["content_free_receipt"]
            if kind == "count":
                observed["production_normalizer_observer_completed_count"] = 0
            elif kind == "parent":
                changed["prediction_kind"] = "model_generated"
            elif kind == "behavior":
                observed[
                    "observer_disposition_changes_response_fallback_prediction_candidate_routing_or_budget"
                ] = True
            else:
                observed["entropy_or_information_gain_assigns_signed_credit"] = True
            observed.pop("receipt_payload_sha256")
            observed["receipt_payload_sha256"] = payload_sha256(observed)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_module_is_label_blind_and_adds_no_effect_surface(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25171_observed_production_normalizer_runtime.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        privileged = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value
            in {
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
        }
        self.assertEqual(privileged, set())
        self.assertFalse(target.__dict__.get("benchmark_launch"))


if __name__ == "__main__":
    unittest.main()
