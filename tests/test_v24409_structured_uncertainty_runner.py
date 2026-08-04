from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    child_receipt,
    parent_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    build_directory_observation,
)
from deepwide_agent.v24409_structured_uncertainty_runner import (  # noqa: E402
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_envelope,
    run_and_persist_structured_uncertainty_task,
    run_v24409_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import Clock, slots  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    IdentityModel,
    SEED,
    TASK,
)
from test_v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    DeadlineUncertaintySearch,
)


class StructuredDeadlineSearch(DeadlineUncertaintySearch):
    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations == 3:
            content = (
                "Alpha\nFounded | 2025\nWebsite | example\n\n"
                "Beta\nFounded | 2024\nWebsite | example"
            )
            for batch in batches:
                for result in batch["results"]:
                    result["raw_content"] = content
        return batches


def clients(output: Path, clock: Clock, *, deadline: float = 300):
    model = build_deadline_model(
        url="http://unused.invalid/responses",
        model_name="synthetic",
        reasoning_effort="low",
        service_tier="",
        static_timeout_seconds=180,
        max_retries=2,
        slot_directory=slots(output),
        output_root=output,
        slot_cap=2,
        pool_id=POOL_ID,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.01,
        monotonic=clock,
        sleeper=clock.sleep,
        inner=IdentityModel(),
    )
    return model, StructuredDeadlineSearch(clock, deadline=deadline)


def writer(directory: Path):
    def write(name: str, value) -> None:
        path = directory / name
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")

    return write


class V24409StructuredUncertaintyRunnerTests(unittest.TestCase):
    def make_directory(self) -> Path:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def run_case(self):
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock)
        outcome = run_v24409_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search, directory

    def test_structured_recovery_keeps_parent_effect_equations_closed(self) -> None:
        outcome, model, search, _ = self.run_case()
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_single_shot_receipt=outcome.search_single_shot_receipt,
            expected_cap=2,
        )
        receipt = outcome.result["structured_recovery_receipt"]
        self.assertEqual(receipt["additional_model_requests"], 0)
        self.assertEqual(receipt["additional_logical_queries"], 0)
        self.assertEqual(receipt["additional_fetch_calls"], 0)
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.fetch_invocations, 3)
        self.assertEqual(outcome.transport_health["hard_fetch_helper_calls"], 10)
        self.assertEqual(receipt["recovered_safe_change_count"], 1)
        self.assertGreater(receipt["recovered_epistemic_credit_total_nats"], 0)

    def test_independent_receipt_and_recovery_tamper_are_rejected(self) -> None:
        outcome, _, _, _ = self.run_case()
        envelope = build_envelope(outcome)
        transport = copy.deepcopy(outcome.transport_health)
        transport["hard_fetch_helper_calls"] += 1
        with self.assertRaises(ValueError):
            validate_observed_bundle(
                envelope,
                model_slot_receipt=outcome.model_slot_receipt,
                transport_health=transport,
                search_single_shot_receipt=outcome.search_single_shot_receipt,
                expected_cap=2,
            )
        altered = copy.deepcopy(envelope)
        altered["result"]["structured_recovery_receipt"][
            "additional_fetch_calls"
        ] = 1
        result = altered["result"]
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_envelope(altered)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock)
        with self.assertRaises(ValueError):
            run_v24409_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_success_persistence_and_content_free_observation(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock)
        outcome = run_and_persist_structured_uncertainty_task(
            TASK,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=writer(directory),
        )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
            self.assertTrue((directory / name).is_file())
        self.assertFalse((directory / FAILURE_NAME).exists())
        terminal = child_receipt(
            stage="result_envelope_written",
            exception_type=None,
            model_receipt_written=True,
            transport_receipt_written=True,
            result_envelope_written=True,
        )
        (directory / "child_terminal_receipt.json").write_text(
            json.dumps(terminal), encoding="utf-8"
        )
        parent = parent_receipt(
            return_code=0,
            timed_out=False,
            elapsed_seconds=4.0,
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
        observation = build_directory_observation(
            1, parent, directory=directory, expected_model_cap=2
        )
        self.assertEqual(observation["parent_taxonomy"], "success")
        self.assertEqual(
            observation["model_acquisitions"],
            outcome.model_slot_receipt["acquisitions"],
        )
        self.assertFalse(
            observation[
                "contains_task_question_prompt_response_prediction_query_url_page_or_credential"
            ]
        )

    def test_recovery_failure_persists_complete_partial_effect_receipts(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock)
        with patch(
            "deepwide_agent.v24409_structured_uncertainty_runner.recover_structured_uncertainty",
            side_effect=RuntimeError("private structured detail"),
        ):
            with self.assertRaises(RuntimeError):
                run_and_persist_structured_uncertainty_task(
                    TASK,
                    model_factory=lambda: model,
                    search_factory=lambda: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    writer=writer(directory),
                )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, FAILURE_NAME):
            self.assertTrue((directory / name).is_file())
        self.assertFalse((directory / RESULT_NAME).exists())
        snapshot = json.loads((directory / FAILURE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(snapshot["failure_stage"], "runtime")
        self.assertNotIn("private structured detail", json.dumps(snapshot))
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.fetch_invocations, 3)

    def test_mid_serialization_failure_binds_only_durable_receipts(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock)
        ordinary = writer(directory)

        def fail_after_model(name: str, value) -> None:
            if name == TRANSPORT_NAME:
                raise OSError("private serialization detail")
            ordinary(name, value)

        with self.assertRaises(OSError):
            run_and_persist_structured_uncertainty_task(
                TASK,
                model_factory=lambda: model,
                search_factory=lambda: search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
                expected_model_cap=2,
                writer=fail_after_model,
            )
        self.assertTrue((directory / MODEL_NAME).is_file())
        self.assertFalse((directory / TRANSPORT_NAME).exists())
        snapshot = json.loads((directory / FAILURE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(snapshot["failure_stage"], "artifact_serialization")
        self.assertTrue(snapshot["model_receipt_present"])
        self.assertFalse(snapshot["transport_receipt_present"])


if __name__ == "__main__":
    unittest.main()
