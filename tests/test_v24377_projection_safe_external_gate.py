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
from deepwide_agent.v24372_batch_stratified_verifier_runner import (  # noqa: E402
    build_envelope,
    run_v24372_task,
)
from scripts import v24377_projection_safe_external_gate as target  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import Clock  # noqa: E402
from test_v24367_target_segment_verifier_runtime import SEED, TASK  # noqa: E402
from test_v24372_batch_stratified_verifier_runner import clients  # noqa: E402
from test_v24374_batch_stratified_external_gate import (  # noqa: E402
    task_projection as frozen_task_projection,
)


def task_projection(ordinal: int, **kwargs: object) -> dict:
    value = frozen_task_projection(ordinal, **kwargs)
    value["checks"] = target._task_checks(value)
    value["passed"] = all(value["checks"].values())
    target.validate_task_projection(value)
    return value


def passing_tasks() -> list[dict]:
    values = [task_projection(index) for index in range(1, target.SELECTED + 1)]
    values[0] = task_projection(
        1,
        parent_before=1,
        legacy_after=0,
        target_after=1,
        recovered=1,
        status="verified_candidate",
    )
    return values


def public_result(aggregate: dict) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24377_target_segment_external_result",
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


def write_json(root: Path, relative: Path, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


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


class V24377ProjectionSafeExternalGateTests(unittest.TestCase):
    def test_protocol_freezes_fifth_disjoint_128_entity_vector(self) -> None:
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
            for question in (
                *target.prior_gate.prior_gate.prior_gate.control.task_source.QUESTIONS,
                *target.prior_gate.prior_gate.prior_gate.QUESTIONS,
                *target.prior_gate.prior_gate.QUESTIONS,
                *target.prior_gate.QUESTIONS,
            )
            for entity in target._question_entity_vector(question)
        }
        self.assertEqual(len(current), 128)
        self.assertEqual(len(prior), 480)
        self.assertTrue(current.isdisjoint(prior))
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(protocol["discovery_partition"]["proposal_source_cap"], 8)
        self.assertEqual(protocol["discovery_partition"]["verifier_source_cap"], 2)
        self.assertEqual(
            protocol["mechanism"]["projection_recovery_policy"],
            target.PROJECTION_RECOVERY_POLICY_ID,
        )
        self.assertTrue(
            protocol["mechanism"][
                "projection_preflight_uses_real_synthetic_envelope_shape"
            ]
        )
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)

        tampered = copy.deepcopy(protocol)
        tampered["authorization"]["hidden_launch"] = True
        tampered.pop("protocol_payload_sha256")
        tampered["protocol_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, value=tampered)

        extra_top = copy.deepcopy(protocol)
        extra_top["hidden_surface"] = False
        extra_top.pop("protocol_payload_sha256")
        extra_top["protocol_payload_sha256"] = payload_sha256(extra_top)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, value=extra_top)

    def test_real_synthetic_envelope_projects_full_recovered_shape(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = Clock()
        model, search = clients(Path(temporary.name), clock, deadline=300)
        outcome = run_v24372_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        projection = target._task_projection(
            1, successful_parent(), build_envelope(outcome)
        )
        self.assertTrue(projection["passed"])
        self.assertEqual(projection["logical_query_count"], 4)
        self.assertEqual(projection["selected_batch_host_counts"], [5, 5])
        self.assertEqual(projection["proposal_batch_host_counts"], [4, 4])
        self.assertEqual(projection["verifier_batch_host_counts"], [1, 1])
        self.assertEqual(projection["model_requests"], 3)
        self.assertEqual(projection["total_fetch_calls"], 10)

    def test_one_net_recovered_verified_cell_is_mechanism_go(self) -> None:
        aggregate = target.aggregate_tasks(passing_tasks(), 120.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["target_segment_recovered_cells"], 1)
        self.assertEqual(aggregate["target_segment_net_cell_gain"], 1)
        self.assertEqual(aggregate["selected_verified_candidate_changes"], 1)
        self.assertGreater(aggregate["utility_aligned_entropy_credit_nats"], 0)

    def test_negative_net_gain_is_valid_diagnostic_but_no_go(self) -> None:
        values = [task_projection(index) for index in range(1, 17)]
        values[0] = task_projection(
            1,
            parent_before=1,
            legacy_after=1,
            target_after=0,
            recovered=0,
            reverted_legacy=1,
            status="independent_conflict",
        )
        aggregate = target.aggregate_tasks(values, 120.0)
        self.assertEqual(aggregate["target_segment_net_cell_gain"], -1)
        self.assertFalse(aggregate["passed"])
        self.assertFalse(aggregate["checks"]["target_segment_net_cell_gain"])

    def test_status_and_entropy_conservation_fail_closed(self) -> None:
        task = passing_tasks()[0]
        altered = copy.deepcopy(task)
        altered["selected_independent_conflict_changes"] = 1
        altered["checks"] = target._task_checks(altered)
        altered["passed"] = all(altered["checks"].values())
        with self.assertRaises(RuntimeError):
            target.validate_task_projection(altered)

        aggregate = target.aggregate_tasks(passing_tasks(), 120.0)
        altered_aggregate = copy.deepcopy(aggregate)
        altered_aggregate["selected_proposal_entropy_nats"] = 0.0
        altered_aggregate["checks"] = target._aggregate_checks(altered_aggregate)
        altered_aggregate["passed"] = all(
            altered_aggregate["checks"].values()
        )
        with self.assertRaises(RuntimeError):
            target.validate_aggregate(altered_aggregate)

    def test_public_result_rejects_content_and_resealed_count_tamper(self) -> None:
        result = public_result(target.aggregate_tasks(passing_tasks(), 120.0))
        target.validate_public_result(result)
        leaked = copy.deepcopy(result)
        leaked["private_text"] = "non-url private content"
        leaked.pop("result_payload_sha256")
        leaked["result_payload_sha256"] = payload_sha256(leaked)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(leaked)

        tampered = copy.deepcopy(result)
        tampered["aggregate"]["target_segment_recovered_cells"] = 2
        tampered["aggregate"]["checks"] = target._aggregate_checks(
            tampered["aggregate"]
        )
        tampered["aggregate"]["passed"] = all(
            tampered["aggregate"]["checks"].values()
        )
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(tampered)

    def test_decision_and_postaudit_recompute_from_frozen_result(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary)
            for relative in (
                target.PROTOCOL,
                target.PREAUDIT,
                target.ACTIVATION,
                target.EXECUTION_START,
            ):
                write_json(root, relative, {})
            watchers = [{"pid": 1, "start_ticks": 2}]
            write_json(root, target.EXECUTION_START, {"protected_watchers": watchers})
            write_json(
                root,
                target.RESULT,
                public_result(target.aggregate_tasks(passing_tasks(), 120.0)),
            )
            decision = target.build_decision(root, now=0)
            write_json(root, target.DECISION, decision)
            target.validate_decision(root)
            self.assertEqual(decision["status"], "fresh_target_segment_external_go")

            changed = copy.deepcopy(decision)
            changed["observed"]["target_segment_net_cell_gain"] = 0
            changed.pop("decision_payload_sha256")
            changed["decision_payload_sha256"] = payload_sha256(changed)
            with self.assertRaises(RuntimeError):
                target.validate_decision(root, value=changed)

            with patch.object(
                target, "lease_observation", return_value={"active": False}
            ), patch.object(
                target, "protected_watcher_snapshot", return_value=watchers
            ):
                audit = target.build_postaudit(root, now=0)
                write_json(root, target.POSTAUDIT, audit)
                target.validate_postaudit(root)
            self.assertTrue(audit["audit_valid"])

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

    def test_preaudit_rejects_unavailable_proxy(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        with patch.object(
            target, "validate_protocol", return_value=protocol
        ), patch.object(
            target,
            "_run_tests",
            return_value={name: True for name in target.TEST_FILES},
        ), patch.object(target, "_future", return_value=True), patch.object(
            target, "_port_listening", return_value=False
        ), patch.object(
            target, "lease_observation", return_value={"active": False}
        ), patch.object(
            target, "protected_watcher_snapshot", return_value=[]
        ), patch.object(
            target, "_parent", return_value={"closure": {"protected_watchers": []}}
        ), patch.object(target, "sha256", return_value="a" * 64), patch.object(
            target, "_git", side_effect=lambda root, *args: ""
        ):
            with self.assertRaises(RuntimeError):
                target.build_preaudit(ROOT, now=0)


if __name__ == "__main__":
    unittest.main()
