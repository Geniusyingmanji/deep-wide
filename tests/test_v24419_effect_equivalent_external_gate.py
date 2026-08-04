from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    child_receipt,
    parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import ObservedChildOutcome  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24397_failure_observability import (  # noqa: E402
    aggregate_observations,
    build_task_observation,
)
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    FAILURE_NAME,
    MODEL_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    persist_failure_artifacts,
)
from deepwide_agent.v24415_effect_equivalent_structured_runner import (  # noqa: E402
    build_envelope,
    run_v24415_task,
)
from scripts import v24419_effect_equivalent_external_gate as target  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24409_structured_uncertainty_runner import clients  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402


def successful_parent() -> dict:
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=1.0,
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


def passing_tasks(projection: dict) -> list[dict]:
    output = []
    for ordinal in range(1, target.SELECTED + 1):
        item = copy.deepcopy(projection)
        item["ordinal"] = ordinal
        item["checks"] = target._task_checks(item)
        item["passed"] = all(item["checks"].values())
        target.validate_task_projection(item)
        output.append(item)
    return output


def successful_observations(outcome) -> list[dict]:
    child = child_receipt(
        stage="result_envelope_written",
        exception_type=None,
        model_receipt_written=True,
        transport_receipt_written=True,
        result_envelope_written=True,
    )
    return [
        build_task_observation(
            ordinal,
            successful_parent(),
            child=child,
            failure_snapshot=None,
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=target.MODEL_SLOT_CAP,
        )
        for ordinal in range(1, target.SELECTED + 1)
    ]


def public_result(mechanism: dict, observation: dict) -> dict:
    diagnostic_complete = (
        observation["selected"] == target.SELECTED
        and observation["exact_ordinal_vector"]
        and observation["success_tasks"] + observation["failure_tasks"]
        == target.SELECTED
    )
    value = {
        "artifact_version": 1,
        "role": "v24419_effect_equivalent_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": target.SELECTED,
        "executor_count": target.EXECUTOR_COUNT,
        "model_slot_cap": target.MODEL_SLOT_CAP,
        "mechanism_aggregate": mechanism,
        "observation_aggregate": observation,
        "mechanism_failure_as_zero_rows": observation["failure_tasks"],
        "mechanism_passed": mechanism["passed"],
        "diagnostic_complete": diagnostic_complete,
        "passed": mechanism["passed"] and diagnostic_complete,
        "temporary_execution_directory_remaining": False,
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_revaluation": False,
        "provenance": {
            "protocol_sha256": "a" * 64,
            "preactivation_audit_sha256": "b" * 64,
            "activation_sha256": "c" * 64,
            "execution_start_sha256": "d" * 64,
            "surface_manifest_sha256": "e" * 64,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


class V24419EffectEquivalentExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.temporary.name), clock)
        cls.outcome = run_v24415_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(cls.outcome)
        cls.projection = target._task_projection(
            1, successful_parent(), cls.envelope
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_protocol_freezes_eleventh_disjoint_entity_population(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        encoded = json.dumps(protocol, ensure_ascii=False)
        current = {
            entity
            for question in target.QUESTIONS
            for entity in target._question_entity_vector(question)
        }
        prior = {
            entity
            for population in (
                target.population_1,
                target.population_2,
                target.population_3,
                target.population_4,
                target.population_5,
                target.population_6,
                target.population_7,
                target.population_8,
                target.population_9,
                target.population_10,
            )
            for question in population.QUESTIONS
            for entity in target._question_entity_vector(question)
        }
        self.assertEqual(len(current), 128)
        self.assertEqual(len(prior), 1248)
        self.assertTrue(current.isdisjoint(prior))
        self.assertGreaterEqual(min(map(len, current)), 2)
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(
            protocol["mechanism"]["effect_equivalent_runner_policy"],
            target.EFFECT_EQUIVALENT_RUNNER_POLICY_ID,
        )
        self.assertTrue(
            protocol["mechanism"][
                "zero_additional_model_query_search_batch_or_fetch_effects"
            ]
        )
        self.assertEqual(protocol["parent"]["path"], str(target.PARENT))
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)

    def test_real_envelope_projects_structured_credit_and_zero_effects(self) -> None:
        value = self.projection
        self.assertTrue(value["passed"])
        self.assertEqual(value["total_logical_query_count"], 5)
        self.assertEqual(value["total_search_batch_count"], 3)
        self.assertEqual(value["parent_total_fetch_calls"], 10)
        self.assertEqual(value["legacy_active_observation_count"], 0)
        self.assertEqual(value["novel_structured_observation_count"], 2)
        self.assertEqual(value["recovered_safe_change_count"], 1)
        self.assertGreater(value["recovered_epistemic_credit_total_nats"], 0)
        self.assertTrue(value["effect_equivalence_valid"])
        self.assertTrue(value["model_remaining_seconds_nonincreasing"])
        self.assertTrue(value["model_deadline_state_monotonic"])
        self.assertTrue(value["transport_deadline_state_monotonic"])
        self.assertEqual(value["additional_model_requests"], 0)
        self.assertEqual(value["additional_logical_queries"], 0)
        self.assertEqual(value["additional_fetch_calls"], 0)

    def test_mechanism_go_and_no_go_require_structured_information_gain(self) -> None:
        passing = target.aggregate_tasks(passing_tasks(self.projection), 120.0)
        self.assertTrue(passing["passed"])
        self.assertEqual(passing["novel_structured_observation_tasks"], 16)
        self.assertEqual(passing["safe_change_tasks"], 16)
        self.assertTrue(passing["all_zero_additional_effects"])
        self.assertEqual(passing["effect_equivalent_tasks"], 16)
        self.assertTrue(passing["all_effect_equivalence_attested"])

        failing_rows = passing_tasks(self.projection)
        for item in failing_rows:
            item["legacy_active_observation_count"] = 0
            item["structured_projection_count"] = 0
            item["novel_structured_observation_count"] = 0
            item["combined_active_observation_count"] = 0
            item["recovered_safe_change_count"] = 0
            item["recovered_unresolved_count"] = 1
            item["recovered_positive_epistemic_target_count"] = 0
            item["recovered_source_credit_record_count"] = 0
            item["recovered_positive_information_gain_total_nats"] = 0.0
            item["recovered_epistemic_credit_total_nats"] = 0.0
            item["recovered_decision_credit_total_nats"] = 0.0
            item["checks"] = target._task_checks(item)
            item["passed"] = all(item["checks"].values())
            target.validate_task_projection(item)
        failing = target.aggregate_tasks(failing_rows, 120.0)
        self.assertFalse(failing["passed"])
        self.assertFalse(failing["checks"]["novel_structured_observation_tasks"])
        self.assertFalse(failing["checks"]["positive_epistemic_tasks"])
        self.assertFalse(failing["checks"]["safe_change_tasks"])

    def test_run_one_preserves_nonzero_taxonomy_and_partial_effects(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        directory = output / "task_01"
        slots = output / "slots"
        directory.mkdir()
        slots.mkdir()

        def write(name, value) -> None:
            (directory / name).write_text(
                json.dumps(dict(value), ensure_ascii=False), encoding="utf-8"
            )

        persist_failure_artifacts(
            RuntimeError("private detail"),
            failure_stage="runtime",
            model=type("M", (), {"receipt": lambda _: self.outcome.model_slot_receipt})(),
            search=type(
                "S",
                (),
                {
                    "transport_health": lambda _: self.outcome.transport_health,
                    "single_shot_receipt": lambda _: self.outcome.search_single_shot_receipt,
                },
            )(),
            expected_model_cap=target.MODEL_SLOT_CAP,
            writer=write,
        )
        write(
            "child_terminal_receipt.json",
            child_receipt(
                stage="child_exception",
                exception_type="RuntimeError",
                model_receipt_written=True,
                transport_receipt_written=True,
                result_envelope_written=False,
            ),
        )
        failed_parent = parent_receipt(
            return_code=1,
            timed_out=False,
            elapsed_seconds=12.0,
            subprocess_exception=False,
            child_terminal_receipt_present=True,
            child_terminal_receipt_valid=True,
            result_envelope_present=False,
            result_envelope_valid=False,
            model_receipt_present=True,
            model_receipt_valid=True,
            transport_receipt_present=True,
            transport_receipt_valid=True,
        )
        with patch.object(
            target,
            "run_observed_subprocess",
            return_value=ObservedChildOutcome(1, False, False, failed_parent),
        ):
            value = target._run_one(ROOT, output, slots, directory, 1)
        self.assertEqual(
            value["observation"]["parent_taxonomy"],
            "child_nonzero_with_terminal_receipt",
        )
        self.assertEqual(
            value["observation"]["effect_scope"], "failure_partial_receipts"
        )
        self.assertEqual(value["mechanism"]["parent_taxonomy"], "local_projection_failure")
        for name in (FAILURE_NAME, MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME):
            self.assertTrue((directory / name).is_file())

    def test_public_result_rejects_private_content_and_failure_count_drift(self) -> None:
        mechanism = target.aggregate_tasks(passing_tasks(self.projection), 120.0)
        observation = aggregate_observations(
            successful_observations(self.outcome), selected=target.SELECTED
        )
        valid = public_result(mechanism, observation)
        target.validate_public_result(valid)
        leaked = {**valid, "private_text": "https://example.test Alpha 2025"}
        leaked.pop("result_payload_sha256")
        leaked["result_payload_sha256"] = payload_sha256(leaked)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(leaked)
        drifted = copy.deepcopy(valid)
        drifted["mechanism_failure_as_zero_rows"] = 1
        drifted.pop("result_payload_sha256")
        drifted["result_payload_sha256"] = payload_sha256(drifted)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(drifted)

    def test_decision_authorizes_only_dev64_design_after_full_go(self) -> None:
        observation = aggregate_observations(
            successful_observations(self.outcome), selected=target.SELECTED
        )
        passing = target.aggregate_tasks(passing_tasks(self.projection), 120.0)
        failing_rows = passing_tasks(self.projection)
        for item in failing_rows:
            item["legacy_active_observation_count"] = 0
            item["structured_projection_count"] = 0
            item["novel_structured_observation_count"] = 0
            item["combined_active_observation_count"] = 0
            item["recovered_safe_change_count"] = 0
            item["recovered_unresolved_count"] = 1
            item["recovered_positive_epistemic_target_count"] = 0
            item["recovered_source_credit_record_count"] = 0
            item["recovered_positive_information_gain_total_nats"] = 0.0
            item["recovered_epistemic_credit_total_nats"] = 0.0
            item["recovered_decision_credit_total_nats"] = 0.0
            item["checks"] = target._task_checks(item)
            item["passed"] = all(item["checks"].values())
            target.validate_task_projection(item)
        failing = target.aggregate_tasks(failing_rows, 120.0)
        for mechanism, expected in ((passing, True), (failing, False)):
            with self.subTest(expected=expected):
                result = public_result(mechanism, observation)
                with (
                    patch.object(target, "_read", return_value=result),
                    patch.object(target, "sha256", return_value="a" * 64),
                ):
                    decision = target.build_decision(ROOT, now=0)
                    target.validate_decision(ROOT, value=decision)
                self.assertIs(decision["passed"], expected)
                self.assertIs(
                    decision["authorization"]["fresh_paired_dev64_design"],
                    expected,
                )
                self.assertFalse(decision["authorization"]["fresh_paired_dev64_launch"])
                self.assertFalse(decision["authorization"]["new_exact220"])
                self.assertFalse(decision["authorization"]["evaluator"])

    def test_resealed_protocol_nested_tamper_fails_closed(self) -> None:
        for field in ("task_contract", "mechanism", "budget", "authorization"):
            with self.subTest(field=field):
                value = target.build_protocol(ROOT, now=0, require_pristine=False)
                value[field]["unexpected"] = True
                value.pop("protocol_payload_sha256")
                value["protocol_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_protocol(ROOT, value=value)

    def test_git_ready_requires_clean_pushed_tracked_start(self) -> None:
        def clean_git(root: Path, *args: str) -> str:
            del root
            if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                return "abc"
            if args == ("status", "--porcelain"):
                return ""
            if args[:2] == ("ls-files", "--error-unmatch"):
                return str(target.EXECUTION_START)
            raise AssertionError(args)

        with patch.object(target, "_git", side_effect=clean_git):
            self.assertTrue(target._git_ready(ROOT))
        with patch.object(
            target,
            "_git",
            side_effect=subprocess.CalledProcessError(1, ["git"]),
        ):
            self.assertFalse(target._git_ready(ROOT))


if __name__ == "__main__":
    unittest.main()
