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
from deepwide_agent.v24384_active_verifier_query_runner import (  # noqa: E402
    build_envelope,
    run_v24384_task,
)
from scripts import v24386_active_verifier_external_gate as target  # noqa: E402
from test_v24384_active_verifier_query_runner import (  # noqa: E402
    Clock,
    DeadlineSearch,
    SEED,
    TASK,
    clients,
    limits,
)
from test_v24383_active_verifier_query_runtime import IdentityModel  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from test_v24343_semantic_active_runner import slots  # noqa: E402


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
        "role": "v24386_active_verifier_external_result",
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


class V24386ActiveVerifierExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = Clock()
        model, search = clients(Path(cls.temporary.name), clock, deadline=300)
        outcome = run_v24384_task(
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

    def test_protocol_freezes_seventh_disjoint_128_entity_vector(self) -> None:
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
            )
            for question in population.QUESTIONS
            for entity in target._question_entity_vector(question)
        }
        self.assertEqual(len(current), 128)
        self.assertEqual(len(prior), 736)
        self.assertTrue(current.isdisjoint(prior))
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(
            protocol["mechanism"]["active_verifier_runtime_policy"],
            target.ACTIVE_VERIFIER_RUNTIME_POLICY_ID,
        )
        self.assertEqual(protocol["budget"]["maximum_hosted_search_batches"], 3)
        self.assertEqual(protocol["budget"]["maximum_logical_search_queries"], 6)
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)

    def test_real_v24384_envelope_projects_active_query_shape(self) -> None:
        projection = self.projection
        self.assertTrue(projection["passed"])
        self.assertEqual(projection["proposal_search_batch_count"], 2)
        self.assertEqual(projection["active_verifier_search_batch_count"], 1)
        self.assertEqual(projection["total_search_batch_count"], 3)
        self.assertEqual(projection["total_logical_query_count"], 6)
        self.assertEqual(projection["proposal_source_count"], 8)
        self.assertEqual(projection["active_selected_source_count"], 2)
        self.assertEqual(projection["model_requests"], 3)
        self.assertEqual(projection["total_fetch_calls"], 10)
        self.assertEqual(
            projection["candidate_changed_cells_after_active_verifier"], 2
        )
        self.assertGreater(projection["utility_aligned_entropy_credit_nats"], 0)

    def test_identity_envelope_projects_without_active_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            clock = Clock()
            deadline = 300
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
            search = DeadlineSearch(clock, deadline=deadline)
            outcome = run_v24384_task(
                TASK,
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
            value = target._task_projection(
                1, successful_parent(), build_envelope(outcome)
            )
        self.assertTrue(value["passed"])
        self.assertEqual(value["active_verifier_logical_query_count"], 0)
        self.assertEqual(value["active_verifier_search_batch_count"], 0)
        self.assertEqual(value["active_selected_source_count"], 0)
        self.assertEqual(value["total_search_batch_count"], 2)
        self.assertEqual(value["total_logical_query_count"], 4)
        self.assertEqual(value["total_fetch_calls"], 8)

    def test_resealed_protocol_nested_tamper_fails_closed(self) -> None:
        for field in ("task_contract", "mechanism", "budget", "authorization"):
            with self.subTest(field=field):
                value = target.build_protocol(
                    ROOT, now=0, require_pristine=False
                )
                value[field]["unexpected"] = True
                value.pop("protocol_payload_sha256")
                value["protocol_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_protocol(ROOT, value=value)

    def test_verified_retention_and_entropy_credit_are_mechanism_go(self) -> None:
        aggregate = target.aggregate_tasks(passing_tasks(self.projection), 120.0)
        self.assertTrue(aggregate["passed"])
        self.assertGreater(aggregate["active_query_tasks"], 0)
        self.assertGreater(aggregate["selected_verified_candidate_changes"], 0)
        self.assertGreater(
            aggregate["candidate_changed_cells_after_active_verifier"], 0
        )
        self.assertGreater(aggregate["utility_aligned_entropy_credit_nats"], 0)

    def test_proposal_entropy_without_verified_retention_is_no_go(self) -> None:
        values = passing_tasks(self.projection)
        for item in values:
            before = item["candidate_changed_cells_before_active_verifier"]
            item["candidate_changed_cells_after_active_verifier"] = 0
            item["active_verifier_admitted_cells"] = 0
            item["active_verifier_reverted_cells"] = before
            for name in target.projection.STATUS_NAMES:
                item[f"{name}_records"] = 0
                item[f"selected_{name}_changes"] = 0
            item["no_independent_candidate_support_records"] = item[
                "verification_record_count"
            ]
            item["selected_no_independent_candidate_support_changes"] = item[
                "selected_exactly_bound_candidate_changes"
            ]
            item["utility_aligned_entropy_credit_nats"] = 0.0
            item["checks"] = target._task_checks(item)
            item["passed"] = all(item["checks"].values())
            target.validate_task_projection(item)
        aggregate = target.aggregate_tasks(values, 120.0)
        self.assertFalse(aggregate["passed"])
        self.assertFalse(
            aggregate["checks"]["selected_verified_candidate_changes"]
        )
        self.assertFalse(
            aggregate["checks"]["active_retained_candidate_changed_cells"]
        )
        self.assertFalse(aggregate["checks"]["utility_aligned_entropy"])

    def test_local_projection_failure_is_valid_failure_as_zero(self) -> None:
        values = passing_tasks(self.projection)
        values[0] = target._local_failure(1)
        aggregate = target.aggregate_tasks(values, 120.0)
        self.assertFalse(aggregate["passed"])
        self.assertEqual(aggregate["selected"], 16)
        self.assertEqual(aggregate["terminal_success_tasks"], 15)
        self.assertEqual(aggregate["structurally_passed_tasks"], 15)
        self.assertEqual(aggregate["deadline_exhausted_tasks"], 1)

    def test_envelope_projection_and_public_result_tamper_fail_closed(self) -> None:
        altered = copy.deepcopy(self.envelope)
        altered["result"]["private_replay_state"]["active_target_state"][
            "active_queries"
        ][0] += " tamper"
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
