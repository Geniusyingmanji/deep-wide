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
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24361_two_batch_partition_external_gate as control  # noqa: E402
from scripts import v24364_two_verifier_external_gate as target  # noqa: E402


def task_projection(
    ordinal: int,
    *,
    before: int = 0,
    after: int = 0,
    union_hosts: int = 10,
    selected_hosts: int | None = None,
    recursive: int = 0,
    provider_calls: int = 2,
    hidden_pages: int | None = None,
) -> dict:
    selected = min(union_hosts, 10) if selected_hosts is None else selected_hosts
    verifier = min(2, max(0, selected - 2))
    proposal = selected - verifier
    pages = verifier if hidden_pages is None else hidden_pages
    value = {
        "ordinal": ordinal,
        "wall_seconds": 30.0,
        "parent_taxonomy": "success",
        "all_parent_artifacts_valid": True,
        "completion_kind": "paired" if before else "identity_no_reserve",
        "effect_accounting_complete": True,
        "structural_shared_normalization": True,
        "logical_query_count": 4,
        "discovery_batch_count": 2,
        "batch_logical_query_counts": [2, 2],
        "provider_search_call_count": provider_calls,
        "single_shot_multi_query_chunks": 2,
        "recursive_split_requests": recursive,
        "pre_host_dedup_url_lead_count": union_hosts + 2,
        "registrable_host_union_count": union_hosts,
        "registrable_host_duplicate_url_count": 2,
        "selected_source_count": selected,
        "proposal_source_count": proposal,
        "verifier_source_count": verifier,
        "verifier_source_cap": 2,
        "host_union_precedes_partition_fetch_candidate": True,
        "source_partition_disjoint": True,
        "hidden_verifier_prompt_excluded": True,
        "hidden_verifier_no_new_candidate": True,
        "parent_support_ids_reused": True,
        "observed_pages_respect_frozen_partition": True,
        "parent_semantic_catalog_present": True,
        "parent_proposal_page_count": proposal,
        "hidden_verifier_page_count": pages,
        "parent_fetch_calls": proposal,
        "hidden_verifier_fetch_calls": verifier,
        "total_fetch_calls": selected,
        "parent_eligible_support_set_count": 1 if before else 0,
        "candidate_changed_cells_before_hidden_verifier": before,
        "candidate_changed_cells_after_hidden_verifier": after,
        "hidden_verifier_admitted_cells": after,
        "hidden_verifier_reverted_cells": before - after,
        "proposal_conditional_entropy_reduction_nats": 0.25 if before else 0.0,
        "utility_aligned_entropy_credit_nats": 0.25 if after else 0.0,
        "utility_set_count": after,
        "final_candidate_nonidentity": after > 0,
        "model_requests": 3 if before else 2,
        "model_attempts": 3 if before else 2,
        "model_total_tokens": 100,
        "slot_acquisitions": 3 if before else 2,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "slot_total_wait_seconds": 5.0,
        "slot_max_wait_seconds": 2.0,
        "slot_acquisition_counts": [2, 1] if before else [1, 1],
        "search_calls": provider_calls,
        "fetch_failures": verifier - pages,
        "search_total_tokens": 200,
        "hosted_search_attempts": provider_calls,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": selected,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": verifier - pages,
        "deadline_exhausted": False,
        "private_replay_valid": True,
    }
    value["checks"] = target._task_checks(value)
    value["passed"] = all(value["checks"].values())
    target.validate_task_projection(value)
    return value


def public_result(aggregate: dict) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24364_two_verifier_external_result",
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


def passing_result() -> dict:
    tasks = [task_projection(index) for index in range(1, target.SELECTED + 1)]
    tasks[0] = task_projection(1, before=1, after=1)
    return public_result(target.aggregate_tasks(tasks, 120.0))


def write_json(root: Path, relative: Path, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


class V24364TwoVerifierExternalGateTests(unittest.TestCase):
    def test_protocol_is_fresh_content_free_and_freezes_eight_plus_two(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        encoded = json.dumps(protocol, ensure_ascii=False)
        discovery = protocol["discovery_partition"]
        self.assertEqual(len(target.QUESTIONS), target.SELECTED)
        self.assertTrue(
            set(target.QUESTIONS).isdisjoint(control.task_source.QUESTIONS)
        )
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(
            len(
                {
                    entity
                    for question in target.QUESTIONS
                    for entity in target._question_entity_vector(question)
                }
            ),
            128,
        )
        self.assertEqual(discovery["deterministic_batch_query_counts"], [2, 2])
        self.assertEqual(discovery["proposal_source_cap"], 8)
        self.assertEqual(discovery["verifier_source_cap"], 2)
        self.assertEqual(discovery["selected_fetch_source_cap"], 10)
        self.assertFalse(discovery["recursive_query_local_split_allowed"])
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["question"], encoded)
            self.assertNotIn(task["opaque_id"], encoded)

    def test_full_eight_plus_two_with_one_retention_is_go(self) -> None:
        result = passing_result()
        target.validate_public_result(result)
        aggregate = result["aggregate"]
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["full_eight_plus_two_partition_tasks"], 16)
        self.assertEqual(aggregate["selected_source_count"], 160)
        self.assertEqual(aggregate["proposal_sources"], 128)
        self.assertEqual(aggregate["verifier_sources"], 32)
        self.assertEqual(aggregate["hidden_verifier_pages"], 32)
        self.assertEqual(aggregate["utility_aligned_tasks"], 1)

    def test_one_missing_hidden_page_can_retain_with_independent_support(self) -> None:
        tasks = [task_projection(index) for index in range(1, 17)]
        tasks[0] = task_projection(1, before=1, after=1, hidden_pages=1)
        aggregate = target.aggregate_tasks(tasks, 120.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["hidden_verifier_pages"], 31)
        self.assertEqual(aggregate["fetch_helper_failures"], 1)

    def test_candidate_coverage_and_partition_gates_fail_independently(self) -> None:
        cases: list[tuple[list[dict], str]] = []
        cases.append(
            (
                [task_projection(index) for index in range(1, 17)],
                "parent_candidate_tasks",
            )
        )
        low_coverage = [task_projection(index, union_hosts=7) for index in range(1, 17)]
        cases.append((low_coverage, "union_ge_ten_host_tasks"))
        partial = [task_projection(index) for index in range(1, 17)]
        for index in range(1, 6):
            partial[index - 1] = task_projection(index, union_hosts=9)
        cases.append((partial, "full_eight_plus_two_partition_tasks"))
        for tasks, failed in cases:
            with self.subTest(failed=failed):
                aggregate = target.aggregate_tasks(tasks, 120.0)
                self.assertFalse(aggregate["passed"])
                self.assertFalse(aggregate["checks"][failed])

    def test_transport_retry_and_recursive_split_are_distinct(self) -> None:
        retried = [task_projection(index) for index in range(1, 17)]
        retried[0] = task_projection(1, before=1, after=1, provider_calls=4)
        aggregate = target.aggregate_tasks(retried, 120.0)
        self.assertTrue(aggregate["passed"])
        split = task_projection(1, recursive=1)
        self.assertFalse(split["checks"]["recursive_split_absent"])

    def test_task_aggregate_and_public_result_tamper_fail_closed(self) -> None:
        task = task_projection(1)
        task["private_text"] = "secret"
        with self.assertRaises(RuntimeError):
            target.validate_task_projection(task)

        result = passing_result()
        altered = copy.deepcopy(result)
        altered["aggregate"]["verifier_sources"] = 1
        altered["aggregate"]["checks"]["utility_final_alignment"] = True
        altered["aggregate"]["passed"] = True
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(altered)

        leaked = copy.deepcopy(result)
        leaked["private_text"] = "non-url private content"
        leaked.pop("result_payload_sha256")
        leaked["result_payload_sha256"] = payload_sha256(leaked)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(leaked)

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
            write_json(root, target.RESULT, passing_result())
            write_json(
                root,
                target.EXECUTION_START,
                {"protected_watchers": [{"pid": 1, "start_ticks": 2}]},
            )
            decision = target.build_decision(root, now=0)
            write_json(root, target.DECISION, decision)
            target.validate_decision(root)

            changed = copy.deepcopy(decision)
            changed["observed"]["selected"] = 1
            changed.pop("decision_payload_sha256")
            changed["decision_payload_sha256"] = payload_sha256(changed)
            with self.assertRaises(RuntimeError):
                target.validate_decision(root, value=changed)

            extra_authority = copy.deepcopy(decision)
            extra_authority["authorization"]["hidden_launch"] = True
            extra_authority.pop("decision_payload_sha256")
            extra_authority["decision_payload_sha256"] = payload_sha256(
                extra_authority
            )
            with self.assertRaises(RuntimeError):
                target.validate_decision(root, value=extra_authority)

            watchers = [{"pid": 1, "start_ticks": 2}]
            with patch.object(
                target, "lease_observation", return_value={"active": False}
            ), patch.object(target, "protected_watcher_snapshot", return_value=watchers):
                audit = target.build_postaudit(root, now=0)
                write_json(root, target.POSTAUDIT, audit)
                target.validate_postaudit(root)
            self.assertTrue(audit["audit_valid"])

            extra_audit = copy.deepcopy(audit)
            extra_audit["authorization"]["hidden_launch"] = True
            extra_audit.pop("audit_payload_sha256")
            extra_audit["audit_payload_sha256"] = payload_sha256(extra_audit)
            with self.assertRaises(RuntimeError):
                target.validate_postaudit(root, value=extra_audit)

    def test_git_ready_requires_clean_pushed_tracked_start(self) -> None:
        def clean_git(root: Path, *args: str) -> str:
            del root
            if args == ("rev-parse", "HEAD") or args == (
                "rev-parse",
                "target/main",
            ):
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
