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

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    build_envelope,
    run_v24447_task,
)
from deepwide_agent.v24450_timed_third_source_runner import (  # noqa: E402
    aggregate_stage_timings,
    build_timing_receipt,
    run_timed_observed_subprocess,
    validate_stage_timing_aggregate,
    validate_timing_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


class SequenceClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return float(next(self.values))


def successful_parent(elapsed: float = 7.0) -> dict:
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=elapsed,
        subprocess_exception=False,
        child_terminal_receipt_present=True,
        child_terminal_receipt_valid=True,
        result_envelope_present=True,
        result_envelope_valid=True,
        model_receipt_present=True,
        model_receipt_valid=True,
        transport_receipt_present=True,
        transport_receipt_valid=True,
    )


class SuccessfulPopen:
    def __init__(self, *_args, **_kwargs):
        self.pid = 987654
        self.returncode = 0

    def wait(self, timeout=None):
        del timeout
        return 0


class V24450TimedThirdSourceRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.temporary.name), clock, third=True)
        cls.outcome = run_v24447_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(cls.outcome)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_success_runs_one_validation_then_one_projection(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            artifacts = {
                RESULT_NAME: self.envelope,
                MODEL_NAME: self.outcome.model_slot_receipt,
                TRANSPORT_NAME: self.outcome.transport_health,
                SEARCH_NAME: self.outcome.search_single_shot_receipt,
            }
            for name, value in artifacts.items():
                (directory / name).write_text(
                    json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            (directory / "child_terminal_receipt.json").write_text(
                json.dumps(
                    {
                        "artifact_version": 1,
                        "role": "v24308_content_free_child_terminal_receipt",
                        "stage": "result_envelope_written",
                        "exception_type": None,
                        "model_receipt_written": True,
                        "transport_receipt_written": True,
                        "result_envelope_written": True,
                        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer": False,
                        "mapping_gold_category_question_type_split_evaluator_score_read": False,
                        "network_model_search_fetch_or_evaluator_called_by_receipt_builder": False,
                    }
                ),
                encoding="utf-8",
            )
            child = json.loads(
                (directory / "child_terminal_receipt.json").read_text(encoding="utf-8")
            )
            child["receipt_payload_sha256"] = payload_sha256(child)
            (directory / "child_terminal_receipt.json").write_text(
                json.dumps(child) + "\n", encoding="utf-8"
            )
            value = run_timed_observed_subprocess(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=directory,
                command=["synthetic"],
                environment={},
                timeout_seconds=1,
                expected_model_cap=2,
                monotonic=SequenceClock([0, 5, 6, 8, 9, 12]),
                popen=SuccessfulPopen,
            )
            timing = value.timing_receipt
            self.assertEqual(value.parent_receipt["failure_taxonomy"], "success")
            self.assertTrue(value.mechanism_projection["passed"])
            self.assertEqual(timing["child_wall_seconds"], 5.0)
            self.assertEqual(timing["post_child_validation_wall_seconds"], 2.0)
            self.assertEqual(timing["projection_wall_seconds"], 3.0)
            self.assertEqual(timing["validation_invocations"], 1)
            self.assertEqual(timing["projection_invocations"], 1)

    def test_failure_receipt_projects_zero_without_projection(self) -> None:
        parent = parent_receipt(
            return_code=1,
            timed_out=False,
            elapsed_seconds=4.0,
            subprocess_exception=False,
            child_terminal_receipt_present=False,
            child_terminal_receipt_valid=False,
            result_envelope_present=False,
            result_envelope_valid=False,
            model_receipt_present=False,
            model_receipt_valid=False,
            transport_receipt_present=False,
            transport_receipt_valid=False,
        )
        receipt = build_timing_receipt(
            ordinal=1,
            parent=parent,
            child_wall_seconds=4.0,
            validation_wall_seconds=0,
            projection_wall_seconds=0,
            validation_invocations=0,
            projection_invocations=0,
            validated_capability=False,
            projected_validated_capability=False,
        )
        validate_timing_receipt(receipt)
        self.assertEqual(receipt["projection_invocations"], 0)

    def test_aggregate_reports_work_sum_median_p95_and_max(self) -> None:
        receipts = []
        for ordinal, child, validation, projection in (
            (1, 1, 0.1, 0.01),
            (2, 2, 0.2, 0.02),
            (3, 3, 0.3, 0.03),
            (4, 4, 0.4, 0.04),
        ):
            receipts.append(
                build_timing_receipt(
                    ordinal=ordinal,
                    parent=successful_parent(child),
                    child_wall_seconds=child,
                    validation_wall_seconds=validation,
                    projection_wall_seconds=projection,
                    validation_invocations=1,
                    projection_invocations=1,
                    validated_capability=True,
                    projected_validated_capability=True,
                )
            )
        value = aggregate_stage_timings(receipts, selected=4)
        validate_stage_timing_aggregate(value)
        self.assertEqual(value["child_wall_sum_seconds"], 10.0)
        self.assertEqual(value["child_wall_median_seconds"], 2.5)
        self.assertEqual(value["child_wall_p95_seconds"], 4.0)
        self.assertEqual(value["child_wall_max_seconds"], 4.0)
        self.assertTrue(value["parallel_task_work_sums_are_not_batch_wall_seconds"])

    def test_timing_or_seal_tamper_fails(self) -> None:
        valid = build_timing_receipt(
            ordinal=1,
            parent=successful_parent(),
            child_wall_seconds=7.0,
            validation_wall_seconds=0.2,
            projection_wall_seconds=0.1,
            validation_invocations=1,
            projection_invocations=1,
            validated_capability=True,
            projected_validated_capability=True,
        )
        altered = copy.deepcopy(valid)
        altered["projection_wall_seconds"] += 1
        with self.assertRaises(ValueError):
            validate_timing_receipt(altered)


if __name__ == "__main__":
    unittest.main()
