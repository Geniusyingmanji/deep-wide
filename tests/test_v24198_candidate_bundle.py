from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24197_parallel_all220 import (  # noqa: E402
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    file_sha256,
    payload_sha256,
)
from deepwide_agent.v24198_candidate_bundle import (  # noqa: E402
    BUNDLE,
    COMPILER_PROTOCOL,
    GO_RECEIPT,
    HANDOFF,
    QUALITY_TERMINAL_RECEIPT,
    SELECTION_PROTOCOL,
    build_bundle,
    build_go_receipt,
    payload_file_sha256,
    validate_handoff,
    validate_published_outputs,
)
from tests import test_v24197_parallel_all220 as v24197_fixtures  # noqa: E402


write_json = v24197_fixtures.write_json


class V24198CandidateBundleTests(unittest.TestCase):
    def fixture(self, root: Path):
        helper = v24197_fixtures.V24197ParallelAll220Tests()
        report, capacity_freeze, report_sha = helper.capacity_pair()
        from deepwide_agent.v24197_parallel_all220 import validate_capacity_pair

        capacity = validate_capacity_pair(
            report,
            capacity_freeze,
            report_sha256=report_sha,
            protocol_sha256="p" * 64,
        )
        candidate_bundle = helper.candidate(
            root, capacity_freeze, workers=capacity["workers"]
        )
        publication = root / "results/candidate_publication.json"
        write_json(publication, {"opaque_candidate_publication": True})
        selector = {
            "artifact_version": 1,
            "role": "v24198_selected_candidate_selector_preregistration",
            "protocol_id": "v24198_predeclared_quality_chain_candidate_selector_v1",
            "created_at_unix": 1,
            "label_blind": True,
            "selection_frozen_before_quality_outcomes": True,
            "candidate_set_manifest_sha256": "c" * 64,
            "candidate_inheritance_rule_sha256": "d" * 64,
            "selection_uses_only_predeclared_quality_gate_statuses": True,
            "selection_requires_entire_quality_chain_terminal": True,
            "selected_candidate_must_have_integrated_canonical_all220_freezes": True,
            "bundle_compiler_has_no_selection_discretion": True,
            "terminal_receipt_path": str(QUALITY_TERMINAL_RECEIPT),
            "handoff_path": str(HANDOFF),
            "benchmark_forward_launch_allowed": False,
            "mapping_gold_category_question_type_evaluator_score_read_by_selector_runtime": False,
            "leaderboard_submission_or_sota_claim": False,
        }
        selector["selector_payload_sha256"] = payload_sha256(selector)
        selector_path = root / SELECTION_PROTOCOL
        write_json(selector_path, selector)
        selector_ref = {
            "path": str(SELECTION_PROTOCOL),
            "sha256": file_sha256(selector_path),
        }
        publication_ref = {
            "path": str(publication.relative_to(root)),
            "sha256": file_sha256(publication),
        }
        method = candidate_bundle["candidate_method_contract_sha256"]
        terminal = {
            "artifact_version": 1,
            "role": "v24198_selected_candidate_terminal_receipt",
            "created_at_unix": 2,
            "label_blind": True,
            "decision": "go",
            "selector_protocol": selector_ref,
            "all_required_quality_gates_terminal": True,
            "candidate_selection_rule_live_replayed": True,
            "selected_candidate_publication": publication_ref,
            "selected_pipeline_version": candidate_bundle["pipeline_version"],
            "selected_state_schema_version": candidate_bundle["state_schema_version"],
            "selected_candidate_method_contract_sha256": method,
            "canonical_all220_integrated_freezes_ready": True,
            "benchmark_forward_launch_allowed": False,
            "mapping_gold_category_question_type_evaluator_score_read_by_bundle_compiler": False,
            "leaderboard_submission_or_sota_claim": False,
        }
        terminal["terminal_receipt_payload_sha256"] = payload_sha256(terminal)
        terminal_path = root / QUALITY_TERMINAL_RECEIPT
        write_json(terminal_path, terminal)
        rows = copy.deepcopy(candidate_bundle["shards"])
        canonical = (
            "configs/full220_v2403_r1_test_s01.ids",
            "configs/full220_v2403_r1_test_s02.ids",
            "configs/full220_v2403_r1_test_s03.ids",
            "configs/full220_v2403_r1_devval_s04.ids",
        )
        for tag, source in zip(EXPECTED_SHARDS, canonical):
            destination = root / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / source).read_bytes())
            rows[tag]["selected_ids"] = {
                "path": source,
                "sha256": file_sha256(destination),
                "count": EXPECTED_COUNTS[tag],
            }
            freeze_path = root / rows[tag]["freeze"]["path"]
            integrated = json.loads(freeze_path.read_text())
            integrated["selected_ids_file"] = source
            integrated["selected_ids_sha256"] = file_sha256(destination)
            integrated["selected_count"] = EXPECTED_COUNTS[tag]
            write_json(freeze_path, integrated)
            rows[tag]["freeze"]["sha256"] = file_sha256(freeze_path)
        compiler_sha = "x" * 64
        handoff = {
            "artifact_version": 1,
            "role": "v24198_selected_candidate_handoff",
            "created_at_unix": 3,
            "label_blind": True,
            "decision": "go",
            "compiler_protocol": {
                "path": str(COMPILER_PROTOCOL),
                "sha256": compiler_sha,
            },
            "selection_protocol": selector_ref,
            "quality_chain_terminal_receipt": {
                "path": str(QUALITY_TERMINAL_RECEIPT),
                "sha256": file_sha256(terminal_path),
            },
            "candidate_publication": publication_ref,
            "selection_was_frozen_before_bundle_compilation": True,
            "candidate_selected_by_predeclared_quality_gates": True,
            "selection_not_made_by_bundle_compiler": True,
            "target_name": candidate_bundle["target_name"],
            "pipeline_version": candidate_bundle["pipeline_version"],
            "state_schema_version": candidate_bundle["state_schema_version"],
            "candidate_method_contract_sha256": method,
            "model": candidate_bundle["model"],
            "shard_order": list(EXPECTED_SHARDS),
            "shards": rows,
            "selected_total": 220,
            "all_output_directories_absent_at_handoff": True,
            "same_pipeline_code_prompt_search_budget_threshold": True,
            "forward_failure_scored_as_zero": True,
            "resume_or_selective_rerun_allowed": False,
            "dev64_is_gate_not_primary_result": True,
            "all220_is_primary_result": True,
            "search_capacity_preflight_required": True,
            "benchmark_forward_launch_allowed": False,
            "separate_executor_activation_required": True,
            "runtime_mapping_gold_category_question_type_evaluator_score_read": False,
            "leaderboard_submission_or_sota_claim": False,
        }
        handoff["handoff_payload_sha256"] = payload_sha256(handoff)
        return handoff, capacity, capacity_freeze, compiler_sha

    def validate(self, root: Path, handoff, capacity_freeze, compiler_sha):
        return validate_handoff(
            root,
            handoff,
            handoff_path=str(HANDOFF),
            handoff_sha256="h" * 64,
            compiler_protocol_sha256=compiler_sha,
            capacity_freeze=capacity_freeze,
        )

    def test_valid_handoff_compiles_launch_false_go_and_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff, capacity, freeze, compiler_sha = self.fixture(root)
            selected = self.validate(root, handoff, freeze, compiler_sha)
            go = build_go_receipt(selected)
            go_path = root / GO_RECEIPT
            write_json(go_path, go)
            bundle = build_bundle(
                selected,
                capacity_freeze_path="results/capacity.json",
                capacity_freeze_sha256="f" * 64,
                go_receipt_path=str(GO_RECEIPT),
                go_receipt_sha256=file_sha256(go_path),
            )
            candidate = validate_published_outputs(
                root,
                bundle=bundle,
                bundle_sha256=payload_file_sha256(bundle),
                capacity=capacity,
                capacity_freeze=freeze,
                capacity_freeze_path="results/capacity.json",
                capacity_freeze_sha256="f" * 64,
            )
        self.assertEqual(candidate["opaque_partition_sha256"], "cace8746d5a817a467e7cb70e715ee599a242cc88ce4474802b9d93a9221082b")
        self.assertFalse(go["benchmark_forward_launch_allowed"])
        self.assertFalse(bundle["full220_launch_allowed"])

    def test_resealed_selector_authority_escalation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff, _capacity, freeze, compiler_sha = self.fixture(root)
            selector_path = root / SELECTION_PROTOCOL
            selector = json.loads(selector_path.read_text())
            selector["selection_frozen_before_quality_outcomes"] = False
            selector["selector_payload_sha256"] = payload_sha256(
                {k: v for k, v in selector.items() if k != "selector_payload_sha256"}
            )
            write_json(selector_path, selector)
            handoff["selection_protocol"]["sha256"] = file_sha256(selector_path)
            terminal_path = root / QUALITY_TERMINAL_RECEIPT
            terminal = json.loads(terminal_path.read_text())
            terminal["selector_protocol"] = handoff["selection_protocol"]
            terminal["terminal_receipt_payload_sha256"] = payload_sha256(
                {k: v for k, v in terminal.items() if k != "terminal_receipt_payload_sha256"}
            )
            write_json(terminal_path, terminal)
            handoff["quality_chain_terminal_receipt"]["sha256"] = file_sha256(terminal_path)
            handoff["handoff_payload_sha256"] = payload_sha256(
                {k: v for k, v in handoff.items() if k != "handoff_payload_sha256"}
            )
            with self.assertRaisesRegex(RuntimeError, "selector protocol"):
                self.validate(root, handoff, freeze, compiler_sha)

    def test_terminal_candidate_or_method_mismatch_is_rejected(self) -> None:
        for field, value in (
            ("selected_pipeline_version", "different"),
            ("selected_candidate_method_contract_sha256", "e" * 64),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                handoff, _capacity, freeze, compiler_sha = self.fixture(root)
                terminal_path = root / QUALITY_TERMINAL_RECEIPT
                terminal = json.loads(terminal_path.read_text())
                terminal[field] = value
                terminal["terminal_receipt_payload_sha256"] = payload_sha256(
                    {k: v for k, v in terminal.items() if k != "terminal_receipt_payload_sha256"}
                )
                write_json(terminal_path, terminal)
                handoff["quality_chain_terminal_receipt"]["sha256"] = file_sha256(terminal_path)
                handoff["handoff_payload_sha256"] = payload_sha256(
                    {k: v for k, v in handoff.items() if k != "handoff_payload_sha256"}
                )
                with self.assertRaisesRegex(RuntimeError, "differs from handoff"):
                    self.validate(root, handoff, freeze, compiler_sha)

    def test_selector_terminal_handoff_timestamp_order_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff, _capacity, freeze, compiler_sha = self.fixture(root)
            handoff["created_at_unix"] = 1
            handoff["handoff_payload_sha256"] = payload_sha256(
                {k: v for k, v in handoff.items() if k != "handoff_payload_sha256"}
            )
            with self.assertRaisesRegex(RuntimeError, "order"):
                self.validate(root, handoff, freeze, compiler_sha)

    def test_noncanonical_ids_or_worker_drift_fails_v24197_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff, capacity, freeze, compiler_sha = self.fixture(root)
            selected = self.validate(root, handoff, freeze, compiler_sha)
            go = build_go_receipt(selected)
            go_path = root / GO_RECEIPT
            write_json(go_path, go)
            tag = EXPECTED_SHARDS[0]
            freeze_path = root / selected["shards"][tag]["freeze"]["path"]
            candidate_freeze = json.loads(freeze_path.read_text())
            candidate_freeze["runtime"]["candidate_model_workers"] += 1
            write_json(freeze_path, candidate_freeze)
            selected["shards"][tag]["freeze"]["sha256"] = file_sha256(freeze_path)
            bundle = build_bundle(
                selected,
                capacity_freeze_path="results/capacity.json",
                capacity_freeze_sha256="f" * 64,
                go_receipt_path=str(GO_RECEIPT),
                go_receipt_sha256=file_sha256(go_path),
            )
            with self.assertRaisesRegex(RuntimeError, "capacity binding"):
                validate_published_outputs(
                    root,
                    bundle=bundle,
                    bundle_sha256=payload_file_sha256(bundle),
                    capacity=capacity,
                    capacity_freeze=freeze,
                    capacity_freeze_path="results/capacity.json",
                    capacity_freeze_sha256="f" * 64,
                )


if __name__ == "__main__":
    unittest.main()
