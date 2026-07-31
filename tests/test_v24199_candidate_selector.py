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
)
from deepwide_agent.v24198_candidate_bundle import CANONICAL_ID_FILES  # noqa: E402
from deepwide_agent.v24199_candidate_selector import (  # noqa: E402
    BASELINE_PUBLICATIONS,
    ENTROPY_ROOT_SOURCE,
    QUALITY_SOURCES,
    build_slot_manifest,
    derive_terminal_vector,
    method_contract_from_freeze,
    payload_sha256,
    slot_for_vector,
    validate_candidate_handoff,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class V24199CandidateSelectorTests(unittest.TestCase):
    def quality_states(self, *, values: dict[str, str]):
        states: dict[str, dict] = {}
        for name, spec in QUALITY_SOURCES.items():
            status = values.get(name, "no_go")
            value = {
                "role": spec["role"],
                "status": spec[status]
                if isinstance(spec[status], str)
                else spec[status][0],
            }
            if "protocol_path" in spec:
                value["protocol"] = {
                    "path": spec["protocol_path"],
                    "sha256": spec["protocol_sha256"],
                    "decision_contract_sha256": "d" * 64,
                }
                value.update(
                    terminal=True,
                    replicate_aware_gate2a_evaluated=True,
                    replicate_aware_gate2a_passed=status == "go",
                    controller_design_allowed=status == "go",
                    controller_implementation_or_pilot_launch_allowed=False,
                    training_credit_allowed=False,
                    full220_controller_launch_allowed=False,
                )
            else:
                value["protocol_sha256"] = spec["protocol_sha256"]
                if name in {"schema77", "markdown", "scope_open"}:
                    value.update(
                        test156_or_full220_launch_allowed=False,
                        test156_or_full220_api_called=False,
                        leaderboard_submission_or_sota_claim=False,
                    )
                if name == "schema77":
                    value.update(
                        forward_resume_used=False,
                        selective_rerun_used=False,
                    )
                if name == "search_yield":
                    value.update(
                        benchmark_forward_called=False,
                        resume_or_selective_rerun_used=False,
                        leaderboard_submission_or_sota_claim=False,
                    )
            states[name] = value
        entropy_root = {
            "role": ENTROPY_ROOT_SOURCE["role"],
            "protocol": {
                "path": ENTROPY_ROOT_SOURCE["protocol_path"],
                "sha256": ENTROPY_ROOT_SOURCE["protocol_sha256"],
            },
            "status": "tie_aware_gate2a_pass",
            "terminal": True,
            "tie_aware_gate2a_evaluated": True,
        }
        return states, entropy_root

    def candidate_fixture(self, root: Path):
        slots = build_slot_manifest()
        vector = {
            "schema77": True,
            "search_yield": True,
            "markdown": True,
            "scope_open": True,
            "entropy_credit": True,
        }
        slot_name = slot_for_vector(slots, vector)
        slot = slots[slot_name]
        capacity = {"selected": 4, "workers": 2, "shards": 2}
        capacity_freeze = {
            "endpoint": "http://127.0.0.1:9878/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "service_tier": "priority",
        }
        manifest_path = root / "configs/candidate/manifest.jsonl"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text("{}\n", encoding="utf-8")
        code_path = root / "src/candidate/runtime.py"
        code_path.parent.mkdir(parents=True)
        code_path.write_text("VERSION = 1\n", encoding="utf-8")
        rows = {}
        method_contract = None
        for tag in EXPECTED_SHARDS:
            canonical = CANONICAL_ID_FILES[tag]
            ids_path = root / canonical["path"]
            ids_path.parent.mkdir(parents=True, exist_ok=True)
            ids_path.write_bytes((ROOT / canonical["path"]).read_bytes())
            freeze_path = root / f"configs/candidate/{tag}.json"
            freeze = {
                "pipeline_version": "v2.integrated",
                "state_schema_version": 99,
                "manifest": "configs/candidate/manifest.jsonl",
                "manifest_sha256": file_sha256(manifest_path),
                "selected_ids_file": canonical["path"],
                "selected_ids_sha256": canonical["sha256"],
                "selected_count": EXPECTED_COUNTS[tag],
                "code_sha256": {"src/candidate/runtime.py": file_sha256(code_path)},
                "model": {
                    "proxy_url": capacity_freeze["endpoint"],
                    "name": capacity_freeze["model"],
                    "reasoning_effort": capacity_freeze["reasoning_effort"],
                    "service_tier": capacity_freeze["service_tier"],
                },
                "search": {"provider": "tavily"},
                "runtime": {
                    "candidate_model_workers": capacity["workers"],
                    "row_model_workers": capacity["workers"],
                    "candidate_tokens": 20000,
                },
            }
            write_json(freeze_path, freeze)
            current_method_contract = method_contract_from_freeze(freeze)
            if method_contract is None:
                method_contract = current_method_contract
            self.assertEqual(method_contract, current_method_contract)
            rows[tag] = {
                "freeze": {
                    "path": str(freeze_path.relative_to(root)),
                    "sha256": file_sha256(freeze_path),
                },
                "selected_ids": copy.deepcopy(canonical),
                "output_directory": f"outputs/fresh/{tag}",
            }
        receipts = {}
        for name in slot["required_integrations"]:
            source_path = root / f"results/source/{name}.json"
            write_json(source_path, {"source_implementation": name})
            path = root / f"results/integration/{name}.json"
            receipt = {
                "artifact_version": 1,
                "role": "v24199_candidate_integration_receipt",
                "created_at_unix": 1,
                "label_blind": True,
                "slot_name": slot_name,
                "feature_vector": vector,
                "integration_id": name,
                "baseline_publication": BASELINE_PUBLICATIONS["schema77"],
                "source_implementation_publication": {
                    "path": str(source_path.relative_to(root)),
                    "sha256": file_sha256(source_path),
                },
                "candidate_pipeline_version": "v2.integrated",
                "candidate_state_schema_version": 99,
                "candidate_method_contract_sha256": method_contract,
                "candidate_regular_file_manifest_sha256": "a" * 64,
                "integration_hooks_present": True,
                "integration_tests": {
                    "status": "pass",
                    "tests_run": 1,
                    "tests_failed": 0,
                },
                "merge_conflict": False,
                "candidate_build_performed_by_selector": False,
                "network_model_search_fetch_evaluator_or_api_called": False,
                "benchmark_forward_launch_allowed": False,
                "mapping_gold_category_question_type_evaluator_score_read": False,
            }
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            write_json(path, receipt)
            receipts[name] = {
                "path": str(path.relative_to(root)),
                "sha256": file_sha256(path),
            }
        merge_path = root / "results/integration/merge.json"
        merge = {
            "artifact_version": 1,
            "role": "v24199_candidate_merge_audit",
            "created_at_unix": 1,
            "label_blind": True,
            "slot_name": slot_name,
            "feature_vector": vector,
            "baseline_publication": BASELINE_PUBLICATIONS["schema77"],
            "candidate_pipeline_version": "v2.integrated",
            "candidate_state_schema_version": 99,
            "candidate_method_contract_sha256": method_contract,
            "candidate_regular_file_manifest_sha256": "a" * 64,
            "integration_receipts": receipts,
            "all_required_integrations_present": True,
            "conflict_count": 0,
            "regression_tests": {
                "status": "pass",
                "tests_run": 1,
                "tests_failed": 0,
            },
            "candidate_build_performed_by_selector": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "benchmark_forward_launch_allowed": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
        }
        merge["merge_audit_payload_sha256"] = payload_sha256(merge)
        write_json(merge_path, merge)
        publication = {
            "artifact_version": 1,
            "role": "v24199_integrated_candidate_publication",
            "created_at_unix": 2,
            "label_blind": True,
            "slot_name": slot_name,
            "feature_vector": vector,
            "baseline_publication": BASELINE_PUBLICATIONS["schema77"],
            "included_integrations": slot["required_integrations"],
            "integration_receipts": receipts,
            "merge_audit": {
                "path": str(merge_path.relative_to(root)),
                "sha256": file_sha256(merge_path),
            },
            "all_required_integrations_present": True,
            "merge_conflict": False,
            "candidate_build_performed_by_selector": False,
            "target_name": "integrated_candidate",
            "pipeline_version": "v2.integrated",
            "state_schema_version": 99,
            "candidate_method_contract_sha256": method_contract,
            "candidate_regular_file_manifest_sha256": "a" * 64,
            "canonical_all220_integrated_freezes_ready": True,
            "benchmark_forward_launch_allowed": False,
            "mapping_gold_category_question_type_evaluator_score_read_by_selector_runtime": False,
        }
        publication["publication_payload_sha256"] = payload_sha256(publication)
        publication_path = root / slot["candidate_publication_path"]
        write_json(publication_path, publication)
        handoff = {
            "artifact_version": 1,
            "role": "v24199_integrated_candidate_handoff",
            "created_at_unix": 3,
            "label_blind": True,
            "slot_name": slot_name,
            "feature_vector": vector,
            "selector_protocol": {
                "path": "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json",
                "sha256": "s" * 64,
            },
            "candidate_publication": {
                "path": slot["candidate_publication_path"],
                "sha256": file_sha256(publication_path),
            },
            "included_integrations": slot["required_integrations"],
            "all_required_integrations_present": True,
            "merge_conflict": False,
            "candidate_build_performed_by_selector": False,
            "target_name": publication["target_name"],
            "pipeline_version": publication["pipeline_version"],
            "state_schema_version": publication["state_schema_version"],
            "candidate_method_contract_sha256": publication[
                "candidate_method_contract_sha256"
            ],
            "model": {
                "endpoint": capacity_freeze["endpoint"],
                "name": capacity_freeze["model"],
                "reasoning_effort": capacity_freeze["reasoning_effort"],
                "service_tier": capacity_freeze["service_tier"],
            },
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
        write_json(root / slot["candidate_handoff_path"], handoff)
        return slots, slot_name, slot, capacity, capacity_freeze

    def test_slot_manifest_is_bijective_over_24_legal_vectors(self) -> None:
        slots = build_slot_manifest()
        self.assertEqual(len(slots), 24)
        self.assertEqual(
            len({json.dumps(row["feature_vector"], sort_keys=True) for row in slots.values()}),
            24,
        )
        for name, row in slots.items():
            self.assertEqual(slot_for_vector(slots, row["feature_vector"]), name)

    def test_terminal_vector_uses_status_only_and_enforces_scope_parent(self) -> None:
        states, root = self.quality_states(
            values={name: "go" for name in QUALITY_SOURCES}
        )
        vector, statuses = derive_terminal_vector(states, entropy_root=root)
        self.assertTrue(all(vector.values()))
        self.assertEqual(set(statuses.values()), {"go"})
        states["markdown"]["status"] = QUALITY_SOURCES["markdown"]["no_go"]
        with self.assertRaisesRegex(RuntimeError, "scope-open GO"):
            derive_terminal_vector(states, entropy_root=root)

    def test_registered_entropy_early_terminal_maps_to_no_go(self) -> None:
        states, root = self.quality_states(values={})
        root.update(
            status="waiting_for_true_continuation_audit_terminal",
            source_terminal=True,
            source_status="gate1_no_go_true_continuation_not_launched",
            terminal=True,
            tie_aware_gate2a_evaluated=False,
            tie_aware_gate2a_passed=False,
            controller_design_allowed=False,
        )
        vector, statuses = derive_terminal_vector(states, entropy_root=root)
        self.assertFalse(vector["entropy_credit"])
        self.assertEqual(statuses["entropy_credit"], "no_go")

    def test_unknown_terminal_status_fails_closed(self) -> None:
        states, root = self.quality_states(values={})
        states["search_yield"]["status"] = "complete_unregistered"
        with self.assertRaisesRegex(RuntimeError, "unregistered"):
            derive_terminal_vector(states, entropy_root=root)

    def test_integrated_candidate_and_four_capacity_bound_freezes_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slots, name, slot, capacity, freeze = self.candidate_fixture(root)
            selected = validate_candidate_handoff(
                root,
                slot_name=name,
                slot=slot,
                selector_protocol_sha256="s" * 64,
                capacity=capacity,
                capacity_freeze=freeze,
            )
        self.assertEqual(selected["slot_name"], name)
        self.assertEqual(set(selected["shards"]), set(EXPECTED_SHARDS))

    def test_missing_integration_or_merge_conflict_fails_closed(self) -> None:
        for field, value, message in (
            ("all_required_integrations_present", False, "publication"),
            ("merge_conflict", True, "publication"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _slots, name, slot, capacity, freeze = self.candidate_fixture(root)
                path = root / slot["candidate_publication_path"]
                publication = json.loads(path.read_text())
                publication[field] = value
                publication["publication_payload_sha256"] = payload_sha256(
                    {k: v for k, v in publication.items() if k != "publication_payload_sha256"}
                )
                write_json(path, publication)
                with self.assertRaisesRegex(RuntimeError, message):
                    validate_candidate_handoff(
                        root,
                        slot_name=name,
                        slot=slot,
                        selector_protocol_sha256="s" * 64,
                        capacity=capacity,
                        capacity_freeze=freeze,
                    )


if __name__ == "__main__":
    unittest.main()
