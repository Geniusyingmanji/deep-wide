from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24468_total_wall_transport as transport  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v24485_execution_scoped_validation_memo as target,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24470_bounded_adaptive_integration import (  # noqa: E402
    run_and_persist_stage_hooked_task,
)
from deepwide_agent.v24476_bounded_nominal_search_integration import (  # noqa: E402
    build_bounded_nominal_hard_total_wall_search,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import slots  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    IdentityModel,
    SEED,
    TASK,
)
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import KNOWN_BASELINE  # noqa: E402
from test_v24476_bounded_nominal_search_integration import hosted_payload  # noqa: E402


MANIFEST = hashlib.sha256(b"v24485-local-validator-manifest").hexdigest()


def run_chain(*, memoized: bool) -> tuple[object, dict[str, dict], float, dict | None]:
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
        output_root = Path(temporary)
        directory = output_root / "task"
        directory.mkdir()
        clock = AdvancingClock()
        deadline = 300.0
        model = build_deadline_model(
            url="http://127.0.0.1:9/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=70,
            max_retries=1,
            slot_directory=slots(output_root),
            output_root=output_root,
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=IdentityModel(baseline=KNOWN_BASELINE),
        )
        model.inner.timeout = 70
        search = build_bounded_nominal_hard_total_wall_search(
            url="http://127.0.0.1:9/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=70,
            max_retries=1,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            stage_callback=lambda _stage: None,
            fetch_pages=False,
            max_workers=1,
            fetch_workers=1,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        search.fetch_invocations = 0

        def fake_fetch(instance, requests_):
            instance.fetch_invocations += 1
            requested = list(requests_)
            instance._increment("fetch_calls", len(requested))
            instance._increment("hard_fetch_helper_calls", len(requested))
            content = (
                "The product was founded in 2025 and later expanded."
                if instance.fetch_invocations >= 3
                else "The product publishes documentation and software."
            )
            return [
                {
                    "query": "synthetic",
                    "results": [
                        {
                            "url": item["url"],
                            "requested_url": item["url"],
                            "title": item["title"],
                            "raw_content": content,
                        }
                    ],
                }
                for item in requested
            ]

        search.fetch_urls = types.MethodType(fake_fetch, search)
        request_count = 0

        def local_post(*, body, **_kwargs):
            nonlocal request_count
            request_count += 1
            del body
            return hosted_payload(request_count, ["synthetic"])

        manager = target.ExecutionValidationMemo() if memoized else None
        started = time.perf_counter()
        with patch.object(transport, "run_total_wall_post", side_effect=local_post):
            if manager is None:
                outcome = run_and_persist_stage_hooked_task(
                    TASK,
                    model_factory=lambda: model,
                    search_factory=lambda: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    directory=directory,
                    writer=lambda name, value: _new_json(directory / name, value),
                    validator_manifest_sha256=MANIFEST,
                    stage_callback=lambda _stage: None,
                )
            else:
                with manager:
                    outcome = run_and_persist_stage_hooked_task(
                        TASK,
                        model_factory=lambda: model,
                        search_factory=lambda: search,
                        partition_seed_sha256=SEED,
                        limits=limits(),
                        monotonic=clock,
                        expected_model_cap=2,
                        directory=directory,
                        writer=lambda name, value: _new_json(directory / name, value),
                        validator_manifest_sha256=MANIFEST,
                        stage_callback=lambda _stage: None,
                    )
        elapsed = time.perf_counter() - started
        artifacts = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in directory.iterdir()
        }
        receipt = manager.content_free_receipt() if manager is not None else None
        return outcome, artifacts, elapsed, receipt


class V24485ExecutionScopedValidationMemoTests(unittest.TestCase):
    def test_memoized_full_chain_is_value_identical_and_fast(self) -> None:
        slow_outcome, slow_artifacts, slow_elapsed, _ = run_chain(memoized=False)
        fast_outcome, fast_artifacts, fast_elapsed, receipt = run_chain(memoized=True)
        self.assertEqual(fast_outcome, slow_outcome)
        self.assertEqual(fast_artifacts, slow_artifacts)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["layer_count"], 8)
        self.assertEqual(receipt["binding_count"], 17)
        self.assertEqual(receipt["total_misses"], 8)
        self.assertGreater(receipt["total_hits"], 100)
        self.assertEqual(receipt["total_mismatches"], 0)
        self.assertTrue(receipt["bindings_restored"])
        self.assertLess(fast_elapsed, 5.0)
        self.assertLess(fast_elapsed, slow_elapsed / 5)

    def test_same_seal_with_tampered_content_is_not_a_hit(self) -> None:
        from test_v24437_narrative_title_uncertainty_recovery import recover

        value, _, _, _ = recover()
        with target.ExecutionValidationMemo() as memo:
            target.v24437.validate_result(value)
            target.v24437.validate_result(value)
            altered = copy.deepcopy(value)
            altered["candidate_prediction"] += "\n"
            # Deliberately retain the old seal.  A seal-only cache would
            # incorrectly accept this value; V2.44.85 must fall through and fail.
            with self.assertRaises(ValueError):
                target.v24437.validate_result(altered)
            resealed = copy.deepcopy(altered)
            resealed.pop("result_sha256")
            resealed["result_sha256"] = payload_sha256(resealed)
            # A different but internally sealed payload also falls through to
            # the frozen validator, whose deterministic replay must reject it.
            with self.assertRaises(ValueError):
                target.v24437.validate_result(resealed)
        receipt = memo.content_free_receipt()
        counts = receipt["layers"]["v24437"]
        self.assertEqual(counts["misses"], 2)
        self.assertEqual(counts["hits"], 1)
        self.assertEqual(counts["mismatches"], 2)

    def test_type_shape_prevents_list_tuple_aliasing(self) -> None:
        original = {"result_sha256": "0" * 64, "value": ["x"]}
        altered = {"result_sha256": "0" * 64, "value": ("x",)}
        self.assertEqual(target._canonical_bytes(original), target._canonical_bytes(altered))
        first = bytearray()
        second = bytearray()
        target._shape(original, first)
        target._shape(altered, second)
        self.assertNotEqual(first, second)

    def test_context_restores_every_binding_after_exception(self) -> None:
        originals = {
            (binding.owner, binding.attribute): getattr(
                binding.owner, binding.attribute
            )
            for binding in target.BINDINGS
        }
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with target.ExecutionValidationMemo():
                raise RuntimeError("synthetic")
        for key, original in originals.items():
            self.assertIs(getattr(key[0], key[1]), original)

    def test_binding_drift_fails_before_any_patch(self) -> None:
        original = target.v24325.validate_result
        with patch.object(target.v24325, "validate_result", lambda _value: None):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                with target.ExecutionValidationMemo():
                    pass
        self.assertIs(target.v24325.validate_result, original)

    def test_contract_is_label_blind_and_design_only(self) -> None:
        contract = target.binding_contract()
        self.assertEqual(contract["layer_count"], 8)
        self.assertEqual(contract["binding_count"], 17)
        self.assertTrue(contract["first_validation_unchanged"])
        self.assertTrue(contract["all_bindings_restored_on_exit"])
        self.assertTrue(
            contract[
                "same_seal_without_exact_bytes_and_type_shape_is_not_a_hit"
            ]
        )
        self.assertFalse(contract["benchmark_launch_or_evaluator_authorized"])
        self.assertFalse(
            contract[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24485_execution_scoped_validation_memo.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
