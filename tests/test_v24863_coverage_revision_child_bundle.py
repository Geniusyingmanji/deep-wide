from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import empty_receipt  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    empty_rate_aware_receipt,
)
from deepwide_agent.v24856_pacing_aware_admission import (  # noqa: E402
    object_sha256,
)
from deepwide_agent.v24862_same_task_coverage_runtime import (  # noqa: E402
    run_v24862_task,
)
from deepwide_agent.v24863_coverage_revision_child_bundle import (  # noqa: E402
    BUNDLE_NAME,
    COVERAGE_NAME,
    DATA_NAMES,
    PARENT_MODEL_NAME,
    validate_bundle,
    write_bundle,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24862_same_task_coverage_runtime import SyntheticThinSearch  # noqa: E402


def pacing_receipt() -> dict[str, object]:
    value = {
        "artifact_version": 1,
        "role": "v24856_pacing_aware_admission_receipt",
        "policy_id": "v24856_same_pass_max_provider_wait_pacing_aware_admission_v1",
        "base_controller_policy_id": "v24272_label_blind_two_wave_entropy_voc_build_only_v1",
        "provider_wait_metric": "same_task_max_provider_gate_wait_delta",
        "provider_start_reservations_before": 0,
        "provider_start_reservations_at_admission": 0,
        "provider_max_wait_seconds_before": 0.0,
        "provider_max_wait_seconds_at_admission": 0.0,
        "observed_provider_max_wait_delta_seconds": 0.0,
        "maximum_provider_wait_credit_seconds": 30.0,
        "credited_provider_wait_seconds": 0.0,
        "raw_wave1_elapsed_seconds": 0.0,
        "base_wave1_ceiling_seconds": 30.0,
        "effective_wave1_ceiling_seconds": 30.0,
        "legacy_decision": "expand",
        "legacy_reason": "positive_entropy_voc",
        "pacing_aware_decision": "expand",
        "pacing_aware_reason": "positive_entropy_voc",
        "decision_changed": False,
        "absolute_task_deadline_changed": False,
        "cleanup_reserve_changed": False,
        "query_fetch_model_token_or_context_cap_changed": False,
        "search_pacing_cooldown_or_attempt_cap_changed": False,
        "raw_first_wave_elapsed_rewritten": False,
        "same_pass_content_free_transport_telemetry_only": True,
        "question_query_url_page_prediction_answer_or_credential_read_or_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "historical_correctness_429_or_latency_cohort_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = object_sha256(value)
    return value


class V24863CoverageRevisionChildBundleTests(unittest.TestCase):
    def build_outcome(self, output: Path):
        clock = core_test.Clock(100.0)
        inner = core_test.SyntheticModel(
            [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
        )
        model = build_deadline_model(
            url="http://unused.invalid/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=core_test.make_slots(output),
            output_root=output,
            slot_cap=2,
            pool_id="v24263_score_first_global_model_slots_v1",
            absolute_deadline=220.0,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=inner,
        )
        search = SyntheticThinSearch(clock, deadline=220.0)
        outcome = run_v24862_task(
            core_test.task(),
            arm="baseline",
            model=model,
            search=search,
            limits=core_test.limits(),
            two_wave_policy=TwoWavePolicy(),
            monotonic=clock,
        )
        direct = empty_receipt(2)
        direct.update(
            {
                "successful_queries": 4,
                "provider_attempts": 4,
                "slot_acquisitions": 4,
                "status_2xx": 4,
            }
        )
        direct["receipt_payload_sha256"] = payload_sha256(
            {key: item for key, item in direct.items() if key != "receipt_payload_sha256"}
        )
        rate = empty_rate_aware_receipt()
        rate.update({"provider_start_reservations": 4})
        rate["receipt_payload_sha256"] = payload_sha256(
            {key: item for key, item in rate.items() if key != "receipt_payload_sha256"}
        )
        return outcome, direct, rate, pacing_receipt()

    def test_bundle_commit_marker_is_written_last_and_validates(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            outcome, direct, rate, pacing = self.build_outcome(output)
            bundle = write_bundle(
                output_root=output,
                directory=task_directory,
                outcome=outcome,
                direct_receipt=direct,
                rate_receipt=rate,
                pacing_receipt=pacing,
                expected_model_slot_cap=2,
                expected_tavily_key_slot_cap=2,
            )
            self.assertTrue((task_directory / BUNDLE_NAME).is_file())
            self.assertEqual(set(bundle["artifact_manifest"]), set(DATA_NAMES))
            self.assertEqual(
                validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                ),
                bundle,
            )

    def test_missing_external_receipt_fails_even_if_envelope_has_copy(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            outcome, direct, rate, pacing = self.build_outcome(output)
            write_bundle(
                output_root=output,
                directory=task_directory,
                outcome=outcome,
                direct_receipt=direct,
                rate_receipt=rate,
                pacing_receipt=pacing,
                expected_model_slot_cap=2,
                expected_tavily_key_slot_cap=2,
            )
            (task_directory / PARENT_MODEL_NAME).unlink()
            with self.assertRaises(ValueError):
                validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                )

    def test_resealed_external_copy_tamper_fails_manifest_and_copy_binding(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            outcome, direct, rate, pacing = self.build_outcome(output)
            write_bundle(
                output_root=output,
                directory=task_directory,
                outcome=outcome,
                direct_receipt=direct,
                rate_receipt=rate,
                pacing_receipt=pacing,
                expected_model_slot_cap=2,
                expected_tavily_key_slot_cap=2,
            )
            path = task_directory / COVERAGE_NAME
            value = json.loads(path.read_text(encoding="utf-8"))
            value["revision_seconds"] += 1
            value.pop("receipt_payload_sha256")
            value["receipt_payload_sha256"] = payload_sha256(value)
            path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                )

    def test_interrupted_write_never_creates_bundle_commit_marker(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            outcome, direct, rate, pacing = self.build_outcome(output)
            calls = 0

            def interrupt(path: Path, value):
                nonlocal calls
                calls += 1
                if calls == 4:
                    raise OSError("synthetic")
                from deepwide_agent.v24863_coverage_revision_child_bundle import _atomic_new

                _atomic_new(path, value)

            with self.assertRaises(OSError):
                write_bundle(
                    output_root=output,
                    directory=task_directory,
                    outcome=outcome,
                    direct_receipt=direct,
                    rate_receipt=rate,
                    pacing_receipt=pacing,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                    writer=interrupt,
                )
            self.assertFalse((task_directory / BUNDLE_NAME).exists())


if __name__ == "__main__":
    unittest.main()
