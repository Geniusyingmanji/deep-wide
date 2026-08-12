from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25215_offline_candidate_discovery as discovery  # noqa: E402
from deepwide_agent import v25217_single_snapshot_transport as transport  # noqa: E402
from deepwide_agent import v25218_snapshot_hard_deadline_controller as controller  # noqa: E402
from scripts import audit_v25213_population_selection as selector  # noqa: E402
from scripts import design_v25214_candidate_preselection_protocol as sampling  # noqa: E402
from scripts import run_v25219_snapshot_population as target  # noqa: E402


PARENT = "a" * 40
START = "b" * 64


def snapshots() -> dict[str, bytes]:
    crates = json.dumps(
        {
            "crates": [
                {"id": f"crate-{index}", "max_version": "1", "description": "x"}
                for index in range(64)
            ]
        }
    ).encode()
    cran = "\n\n".join(
        f"Package: Pkg{index}\nVersion: 1\nLicense: MIT\nSuggests: dep"
        for index in range(64)
    ).encode()
    crossref = json.dumps(
        {
            "message": {
                "items": [
                    {
                        "DOI": f"10.1234/item{index}",
                        "title": ["T"],
                        "publisher": "P",
                        "container-title": ["C"],
                    }
                    for index in range(64)
                ]
            }
        }
    ).encode()
    pypi = "".join(
        f'<a href="/simple/proj{index:04d}/">proj{index:04d}</a>'
        for index in range(64)
    ).encode()
    return dict(zip(discovery.STRATA, (crates, cran, crossref, pypi), strict=True))


def success_batch(bodies=None):
    bodies = snapshots() if bodies is None else bodies
    children = {}
    for stratum, body in bodies.items():
        nested = transport._receipt(
            stratum=stratum,
            provider_attempt_count=1,
            outcome="success",
            failure_code=None,
            http_status=200,
            elapsed_seconds=0.01,
            response_bytes=len(body),
            response_sha256=hashlib.sha256(body).hexdigest(),
        )
        children[stratum] = controller._child_row(
            started=True,
            message_received=True,
            kind="success",
            exit_code=0,
            transport_receipt=nested,
        )
    receipt = controller._receipt(
        hard_deadline_seconds=180.0,
        elapsed_seconds=0.1,
        terminal_outcome="success",
        failure_code=None,
        children=children,
    )
    return bodies, receipt


def failed_batch():
    _bodies, receipt = success_batch()
    changed = copy.deepcopy(receipt)
    stratum = discovery.STRATA[0]
    changed["children"][stratum] = controller._child_row(
        started=True,
        message_received=False,
        kind="hard_deadline",
        exit_code=-15,
        transport_receipt=None,
    )
    changed["terminal_outcome"] = "failure"
    changed["failure_code"] = "hard_deadline"
    changed["successful_transport_count"] = 3
    changed["transport_response_bytes_total"] -= receipt["children"][stratum][
        "transport_receipt"
    ]["response_bytes"]
    changed.pop("receipt_payload_sha256")
    changed["receipt_payload_sha256"] = controller.payload_sha256(changed)
    return {}, controller.validate_receipt(changed)


def history_success(candidates, *, parent_commit, now):
    ordered = [
        identity
        for stratum in selector.RISK_STRATA
        for identity in candidates[stratum]
    ]
    value = {
        "artifact_version": 1,
        "role": selector.ROLE,
        "created_at_unix": now,
        "parent_commit": parent_commit,
        "risk_strata": list(selector.RISK_STRATA),
        "tasks_per_stratum": 16,
        "identity_count": 64,
        "unique_identity_count": 64,
        "stratum_identity_counts": {stratum: 16 for stratum in selector.RISK_STRATA},
        "ordered_identity_vector_sha256": selector.payload_sha256(ordered),
        "identity_history_introduction_hit_total": 0,
        "identity_history_zero_hit_count": 64,
        "stratum_identity_history_zero_hit_counts": {stratum: 16 for stratum in selector.RISK_STRATA},
        "selection_uses_local_repository_history_only": True,
        "candidate_preselection_provenance_attested_by_selector": False,
        "identity_plaintext_item_hash_or_stratum_identity_mapping_persisted": False,
        "endpoint_page_value_question_prediction_or_evidence_persisted": False,
        "risk_stratum_passed_as_hidden_runtime_input_or_router_signal": False,
        "identity_is_future_visible_task_input_not_hidden_mapping": True,
        "selection_script_network_model_search_fetch_or_evaluator_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "prior_external_or_deepwidebench_population_reuse": False,
        "population_frozen_or_external_protocol_authorized": False,
        "retry_resume_replacement_selective_rerun_or_revaluation_authorized": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "findings": [],
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = selector.payload_sha256(value)
    return selector.validate_audit(value)


class V25219SnapshotPopulationRunnerTests(unittest.TestCase):
    def test_success_freezes_exact_64_visible_tasks_without_hidden_stratum(self) -> None:
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=success_batch,
            history_builder=history_success,
            now=1,
        )
        self.assertEqual(value["status"], "go")
        self.assertEqual(len(value["task_vector"]), 64)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in value["task_vector"]))
        self.assertNotIn("stratum", json.dumps(value["task_vector"]))
        self.assertTrue(value["authorization"]["fresh_disjoint_reliability_protocol_design"])
        self.assertTrue(value["batch_body_receipt_bytes_and_sha256_binding_passed"])
        self.assertTrue(value["public_snapshot_network_or_api_called"])
        self.assertFalse(
            value["model_hosted_search_tavily_evaluator_or_benchmark_called"]
        )

    def test_body_length_or_sha_mismatch_fails_before_any_parse(self) -> None:
        original_bodies, receipt = success_batch()
        stratum = discovery.STRATA[0]
        for kind in ("length", "same_length_sha"):
            bodies = copy.deepcopy(original_bodies)
            if kind == "length":
                bodies[stratum] += b"x"
            else:
                first = b"x" if bodies[stratum][:1] != b"x" else b"y"
                bodies[stratum] = first + bodies[stratum][1:]
            def batch(): return bodies, receipt
            value = target.build_result(
                execution_start_sha256=START,
                parent_commit=PARENT,
                batch_runner=batch,
                history_builder=history_success,
                now=1,
            )
            with self.subTest(kind=kind):
                self.assertEqual(value["failure_stage"], "snapshot_transport")
                self.assertFalse(
                    value["batch_body_receipt_bytes_and_sha256_binding_passed"]
                )
                self.assertEqual(value["parser_observations"], {})
                self.assertEqual(value["task_vector"], [])

    def test_transport_failure_is_whole_batch_no_go(self) -> None:
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=failed_batch,
            history_builder=history_success,
            now=1,
        )
        self.assertEqual(value["status"], "no_go")
        self.assertEqual(value["failure_stage"], "snapshot_transport")
        self.assertEqual(value["task_vector"], [])

    def test_parser_coverage_failure_is_no_go_without_candidate_values(self) -> None:
        bodies, receipt = success_batch()
        bodies[discovery.STRATA[0]] = b'{"crates":[]}'
        _bodies, receipt = success_batch(bodies)
        def batch(): return bodies, receipt
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=batch,
            history_builder=history_success,
            now=1,
        )
        self.assertEqual(value["failure_stage"], "snapshot_parse_or_coverage")
        self.assertEqual(value["task_vector"], [])
        self.assertNotIn("crate-0", json.dumps(value))

    def test_history_failure_is_no_go_without_selected_identities(self) -> None:
        def fail(*args, **kwargs): raise RuntimeError("private identity overlap")
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=success_batch,
            history_builder=fail,
            now=1,
        )
        self.assertEqual(value["failure_stage"], "deterministic_selection_or_history")
        self.assertEqual(value["task_vector"], [])
        self.assertNotIn("private identity overlap", json.dumps(value))

    def test_unsafe_identity_makes_whole_population_no_go(self) -> None:
        bodies, receipt = success_batch()
        parsed = json.loads(bodies[discovery.STRATA[0]])
        parsed["crates"][0]["id"] = "</task>"
        bodies[discovery.STRATA[0]] = json.dumps(parsed).encode()
        _bodies, receipt = success_batch(bodies)
        def batch(): return bodies, receipt
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=batch,
            history_builder=history_success,
            now=1,
        )
        self.assertEqual(value["status"], "no_go")
        self.assertEqual(value["task_vector"], [])

    def test_unselected_unsafe_candidate_does_not_poison_safe_oversample(self) -> None:
        bodies = snapshots()
        parsed = json.loads(bodies[discovery.STRATA[0]])
        parsed["crates"].append(
            {"id": "</task>", "max_version": "1", "description": "x"}
        )
        bodies[discovery.STRATA[0]] = json.dumps(parsed).encode()
        _bodies, receipt = success_batch(bodies)
        def batch(): return bodies, receipt
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=batch,
            history_builder=history_success,
            now=1,
        )
        self.assertEqual(value["status"], "go")
        self.assertNotIn("</task>", json.dumps(value))

    def test_local_sampling_and_selection_validator_match_frozen_parents(self) -> None:
        bodies = snapshots()
        candidate_pools = {}
        snapshot_hashes = {}
        for stratum in discovery.STRATA:
            candidates, observed = discovery.discover_candidates(
                bodies[stratum], stratum=stratum
            )
            candidate_pools[stratum] = candidates
            snapshot_hashes[stratum] = observed["snapshot_sha256"]
        expected = sampling.select_candidates(
            candidate_pools, snapshot_hashes=snapshot_hashes
        )
        observed = target._select_candidates(
            candidate_pools, snapshot_hashes=snapshot_hashes
        )
        self.assertEqual(observed, expected)
        parent_audit = history_success(observed, parent_commit=PARENT, now=1)
        self.assertEqual(
            target.validate_selection_audit(parent_audit),
            selector.validate_audit(parent_audit),
        )

    def test_watcher_and_shared_lease_execution_barriers_fail_closed(self) -> None:
        self.assertTrue(target._protected_watchers_match())
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            original_root = target.ROOT
            original_lease = target.LEASE_PATH
            try:
                target.ROOT = Path(temporary)
                target.LEASE_PATH = Path("lease.lock")
                first = target._acquire_api_lease()
                with self.assertRaises(RuntimeError):
                    target._acquire_api_lease()
                first.close()
                second = target._acquire_api_lease()
                second.close()
                os.unlink(Path(temporary) / "lease.lock")
                os.symlink("missing", Path(temporary) / "lease.lock")
                with self.assertRaises(RuntimeError):
                    target._acquire_api_lease()
            finally:
                target.ROOT = original_root
                target.LEASE_PATH = original_lease

    def test_task_vector_tamper_or_hidden_key_fails_closed(self) -> None:
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=success_batch,
            history_builder=history_success,
            now=1,
        )
        for kind in (
            "hidden",
            "question",
            "plausible_identity",
            "opaque_id",
            "hash",
            "top_level_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "hidden":
                changed["task_vector"][0]["stratum"] = "hidden"
            elif kind == "question":
                changed["task_vector"][0]["question"] = "bad"
            elif kind == "plausible_identity":
                changed["task_vector"][0]["question"] = changed["task_vector"][0][
                    "question"
                ].replace('crate named "', 'crate named "other-')
            elif kind == "opaque_id":
                changed["task_vector"][0]["opaque_id"] = "task_" + "f" * 24
            elif kind == "top_level_hidden":
                changed["candidate_pool"] = ["private"]
            else:
                changed["task_vector_sha256"] = "0" * 64
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_result_authority_or_credit_tamper_fails_closed(self) -> None:
        value = target.build_result(
            execution_start_sha256=START,
            parent_commit=PARENT,
            batch_runner=success_batch,
            history_builder=history_success,
            now=1,
        )
        for field in (
            "raw_snapshot_candidate_pool_stratum_identity_map_or_item_hash_persisted",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "model_hosted_search_tavily_evaluator_or_benchmark_called",
        ):
            changed = copy.deepcopy(value)
            changed[field] = True
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                target.validate_result(changed)
        changed = copy.deepcopy(value)
        changed["parent_receipt_effect_disclosure"][
            "does_not_deny_public_snapshot_http_get_or_public_api_effect"
        ] = False
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(changed)

    def test_attempt_claim_is_exact_and_tamper_evident(self) -> None:
        manifest = {"scripts/example.py": "d" * 64}
        claim = target.build_attempt_claim(
            execution_start_path=Path(
                "results/v25219_snapshot_population_execution_start_v1_20260812.json"
            ),
            execution_start_sha256=START,
            history_parent_commit=PARENT,
            source_manifest=manifest,
            now=1,
        )
        self.assertTrue(
            claim["claim_created_before_public_snapshot_network_or_api_call"]
        )
        self.assertFalse(
            claim["retry_refetch_backfill_replacement_or_second_batch_authorized"]
        )
        for kind in ("second_batch", "hidden", "hash"):
            changed = copy.deepcopy(claim)
            if kind == "second_batch":
                changed[
                    "retry_refetch_backfill_replacement_or_second_batch_authorized"
                ] = True
            elif kind == "hidden":
                changed["hidden_authority"] = True
            else:
                changed["source_manifest"]["scripts/example.py"] = "e" * 64
            changed.pop("claim_payload_sha256")
            changed["claim_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_attempt_claim(
                    changed, expected_source_manifest=manifest
                )

    def test_execution_start_must_be_the_only_change_in_one_pushed_commit(self) -> None:
        start = {"history_parent_commit": "a" * 40}
        head = "b" * 40
        target_head = head

        def valid_git(*args):
            if args[0] == "rev-list":
                return f"{head} {'a' * 40}"
            if args[0] == "diff-tree":
                return str(target.EXECUTION_START)
            raise AssertionError(args)

        self.assertTrue(
            target.execution_start_commit_boundary(
                start,
                current_head=head,
                current_target=target_head,
                git=valid_git,
            )
        )
        for kind in ("unpushed", "extra_file", "extra_parent"):
            def changed_git(*args):
                if args[0] == "rev-list":
                    suffix = f" {'c' * 40}" if kind == "extra_parent" else ""
                    return f"{head} {'a' * 40}{suffix}"
                if args[0] == "diff-tree":
                    suffix = "\nplan.md" if kind == "extra_file" else ""
                    return str(target.EXECUTION_START) + suffix
                raise AssertionError(args)

            with self.subTest(kind=kind):
                self.assertFalse(
                    target.execution_start_commit_boundary(
                        start,
                        current_head=head,
                        current_target=("c" * 40 if kind == "unpushed" else head),
                        git=changed_git,
                    )
                )
        preaudit = {"git": {"head": "0" * 40}}
        preaudit_commit = "a" * 40

        def valid_preaudit_git(*args):
            if args[0] == "rev-list":
                return f"{preaudit_commit} {'0' * 40}"
            if args[0] == "diff-tree":
                return str(target.PREAUDIT)
            raise AssertionError(args)

        self.assertTrue(
            target.preactivation_commit_boundary(
                preaudit,
                preactivation_commit=preaudit_commit,
                git=valid_preaudit_git,
            )
        )
        for changed in ("plan.md", str(target.PREAUDIT) + "\nplan.md"):
            def invalid_preaudit_git(*args):
                if args[0] == "rev-list":
                    return f"{preaudit_commit} {'0' * 40}"
                if args[0] == "diff-tree":
                    return changed
                raise AssertionError(args)

            with self.subTest(preaudit_changed=changed):
                self.assertFalse(
                    target.preactivation_commit_boundary(
                        preaudit,
                        preactivation_commit=preaudit_commit,
                        git=invalid_preaudit_git,
                    )
                )


if __name__ == "__main__":
    unittest.main()
