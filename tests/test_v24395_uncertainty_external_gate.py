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

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    build_envelope,
    run_v24391_task,
)
from scripts import v24395_uncertainty_external_gate as target  # noqa: E402
from test_v24343_semantic_active_runner import Clock  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24391_uncertainty_active_evidence_runner import clients  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402


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


def public_result(aggregate: dict) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24395_uncertainty_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": target.SELECTED,
        "executor_count": target.EXECUTOR_COUNT,
        "model_slot_cap": target.MODEL_SLOT_CAP,
        "aggregate": aggregate,
        "passed": aggregate["passed"],
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


class V24395UncertaintyExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = Clock()
        model, search = clients(Path(cls.temporary.name), clock, deadline=300)
        outcome = run_v24391_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(outcome)
        cls.projection = target._task_projection(
            1, successful_parent(), cls.envelope
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_protocol_freezes_eighth_disjoint_128_entity_vector(self) -> None:
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
            )
            for question in population.QUESTIONS
            for entity in target._question_entity_vector(question)
        }
        self.assertEqual(len(current), 128)
        self.assertEqual(len(prior), 864)
        self.assertTrue(current.isdisjoint(prior))
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(
            protocol["mechanism"]["uncertainty_runtime_policy"],
            target.UNCERTAINTY_RUNTIME_POLICY_ID,
        )
        self.assertEqual(protocol["budget"]["maximum_hosted_search_batches"], 3)
        self.assertEqual(protocol["budget"]["maximum_logical_search_queries"], 5)
        self.assertEqual(
            protocol["revoked_predecessor"], target._revoked_predecessor(ROOT)
        )
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)

    def test_real_v24391_envelope_projects_candidate_independent_credit(self) -> None:
        projection = self.projection
        self.assertTrue(projection["passed"])
        self.assertEqual(projection["proposal_search_batch_count"], 2)
        self.assertEqual(projection["active_search_batch_count"], 1)
        self.assertEqual(projection["total_search_batch_count"], 3)
        self.assertEqual(projection["total_logical_query_count"], 5)
        self.assertEqual(projection["proposal_source_count"], 8)
        self.assertEqual(projection["active_selected_source_count"], 2)
        self.assertEqual(projection["model_requests"], 2)
        self.assertEqual(projection["total_fetch_calls"], 10)
        self.assertEqual(projection["safe_change_count"], 1)
        self.assertGreater(projection["epistemic_credit_total_nats"], 0)
        self.assertGreater(projection["decision_credit_total_nats"], 0)

    def test_candidate_independent_credit_is_mechanism_go(self) -> None:
        aggregate = target.aggregate_tasks(passing_tasks(self.projection), 120.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["active_query_tasks"], 16)
        self.assertGreater(aggregate["positive_epistemic_tasks"], 0)
        self.assertGreater(aggregate["safe_change_tasks"], 0)
        self.assertGreater(aggregate["epistemic_credit_total_nats"], 0)

    def test_no_observations_is_structurally_valid_but_mechanism_no_go(self) -> None:
        values = passing_tasks(self.projection)
        for item in values:
            item["active_observation_count"] = 0
            item["active_independent_source_count"] = 0
            item["safe_change_count"] = 0
            item["unresolved_count"] = 1
            item["candidate_changed_cell_count"] = 0
            item["positive_epistemic_target_count"] = 0
            item["source_credit_record_count"] = 0
            item["positive_information_gain_total_nats"] = 0.0
            item["epistemic_credit_total_nats"] = 0.0
            item["decision_credit_total_nats"] = 0.0
            item["checks"] = target._task_checks(item)
            item["passed"] = all(item["checks"].values())
            target.validate_task_projection(item)
        aggregate = target.aggregate_tasks(values, 120.0)
        self.assertFalse(aggregate["passed"])
        self.assertEqual(aggregate["structurally_passed_tasks"], 16)
        self.assertFalse(aggregate["checks"]["active_observation_tasks"])
        self.assertFalse(aggregate["checks"]["positive_epistemic_tasks"])
        self.assertFalse(aggregate["checks"]["safe_change_tasks"])

    def test_local_projection_failure_is_failure_as_zero(self) -> None:
        values = passing_tasks(self.projection)
        values[0] = target._local_failure(1)
        aggregate = target.aggregate_tasks(values, 120.0)
        self.assertFalse(aggregate["passed"])
        self.assertEqual(aggregate["selected"], 16)
        self.assertEqual(aggregate["terminal_success_tasks"], 15)
        self.assertEqual(aggregate["structurally_passed_tasks"], 15)
        self.assertEqual(aggregate["deadline_exhausted_tasks"], 1)

    def test_resealed_protocol_nested_tamper_fails_closed(self) -> None:
        for field in ("task_contract", "mechanism", "budget", "authorization"):
            with self.subTest(field=field):
                value = target.build_protocol(ROOT, now=0, require_pristine=False)
                value[field]["unexpected"] = True
                value.pop("protocol_payload_sha256")
                value["protocol_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_protocol(ROOT, value=value)

    def test_envelope_projection_and_public_result_tamper_fail_closed(self) -> None:
        altered = copy.deepcopy(self.envelope)
        altered["result"]["private_replay_state"]["active_observations"][0][
            "value"
        ] = "2030"
        result = altered["result"]
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            target._task_projection(1, successful_parent(), altered)

        aggregate = target.aggregate_tasks(passing_tasks(self.projection), 120.0)
        leaked = public_result(aggregate)
        leaked["private_text"] = "private content"
        leaked.pop("result_payload_sha256")
        leaked["result_payload_sha256"] = payload_sha256(leaked)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(leaked)

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
