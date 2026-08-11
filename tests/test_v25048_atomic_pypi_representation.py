from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25047_pypi_current_record_representation as representation  # noqa: E402
from deepwide_agent import v25048_atomic_pypi_representation_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25048_atomic_pypi_representation as runner  # noqa: E402


def raw(project: str = "gunicorn") -> str:
    return json.dumps(
        {
            "info": {
                "name": project,
                "version": "23.0.0",
                "requires_python": ">=3.9",
            },
            "releases": {
                "22.0.0": [{"upload_time": "2025-01-01T00:00:00"}],
                "23.0.0": [
                    {"upload_time_iso_8601": "2026-07-03T01:00:00Z"},
                    {"upload_time": "2026-07-02T01:00:00"},
                ],
            },
        },
        sort_keys=True,
    )


class V25048AtomicPyPIRepresentationTests(unittest.TestCase):
    def _prepared(self, count: int = contract.TASK_COUNT) -> list[dict]:
        rows = []
        for index in range(count):
            project = contract.PROJECTS[index]
            raw_json = raw(project)
            rendered = representation.build_representations(
                raw_json,
                visible_project=project,
                total_chars=contract.EVIDENCE_CHARS,
            )
            rows.append(
                {
                    "index": index,
                    "opaque_id": contract.task_vector()[index]["opaque_id"],
                    "question": contract.task_vector()[index]["question"],
                    "project": project,
                    "endpoint": contract.endpoint_vector()[index],
                    "raw_response_sha256": hashlib.sha256(raw_json.encode()).hexdigest(),
                    "raw_response_bytes": len(raw_json.encode()),
                    "control_evidence": rendered["control_evidence"],
                    "candidate_evidence": rendered["candidate_evidence"],
                    "receipt": rendered["content_free_receipt"],
                    "record": representation.parse_current_record(
                        raw_json, visible_project=project
                    ),
                    "fetch_attempts": 1,
                    "fetch_successes": 1,
                    "http_status": 200,
                    "elapsed_seconds": 0.01,
                    "ready": True,
                }
            )
        return rows

    def _task_row(self, *, changed: bool = True) -> dict:
        item = self._prepared(1)[0]
        control = (
            "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
            "| --- | --- | --- | --- |\n| gunicorn | 23.0.0 | Unknown | >=3.9 |"
        )
        candidate = control.replace("Unknown", "2026-07-02") if changed else control
        predictions = {
            contract.CONTROL_ARM: control,
            contract.CANDIDATE_ARM: candidate,
        }
        usage = {
            arm: {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "elapsed_milliseconds": 10,
                "provider_attempts": 1,
            }
            for arm in contract.ARMS
        }
        value = {
            "artifact_version": 1,
            "role": "v25048_atomic_pypi_task_result",
            "protocol_id": contract.PROTOCOL_ID,
            "opaque_id": item["opaque_id"],
            "runtime_input_keys": [
                "opaque_id", "question", "same_forward_public_pypi_bytes"
            ],
            "terminal": True,
            "completed": True,
            "failure_as_zero": False,
            "fetch_attempts": 1,
            "fetch_successes": 1,
            "http_status": 200,
            "representation_receipt": item["receipt"],
            "evidence_chars": {
                arm: contract.EVIDENCE_CHARS for arm in contract.ARMS
            },
            "model_success": {arm: True for arm in contract.ARMS},
            "model_attempts": {arm: 1 for arm in contract.ARMS},
            "model_usage": usage,
            "predictions": predictions,
            "prediction_sha256": {
                arm: contract.payload_sha256(predictions[arm])
                for arm in contract.ARMS
            },
            "prediction_changed": changed,
            "wall_seconds": 0.1,
            "same_exact_public_response_bytes_for_both_arms": True,
            "control_is_fixed_raw_json_prefix": True,
            "candidate_is_identity_bound_current_record_then_same_raw_prefix": True,
            "same_evidence_chars_prompt_model_output_cap_attempt_count_and_deadline": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_credit_or_routes": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
            "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential": False,
        }
        return contract.seal(value, "result_payload_sha256")

    def test_population_is_fixed_visible_only_and_arm_balanced(self) -> None:
        self.assertEqual(len(contract.PROJECTS), 20)
        self.assertEqual(len(set(contract.PROJECTS)), 20)
        self.assertTrue(
            all(set(row) == {"opaque_id", "question"} for row in contract.task_vector())
        )
        orders = contract.arm_order_vector()
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in orders), 10)
        self.assertTrue(all(set(order) == set(contract.ARMS) for order in orders))

    def test_protocol_freezes_atomic_barrier_equal_budget_and_no_evaluator(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(value["gates"]["readiness"]["parser_ready_tasks"], 20)
        self.assertEqual(value["gates"]["readiness"]["bound_fields"], 80)
        self.assertEqual(value["gates"]["readiness"]["model_calls_before_go"], 0)
        self.assertEqual(value["execution"]["evidence_chars_per_arm"], 12_000)
        self.assertFalse(value["authorization"]["deepwidebench_dev64_exact220_or_sota"])
        self.assertFalse((ROOT / contract.EVALUATOR).exists())

    def test_readiness_go_recomputes_exact_counts_and_authorization(self) -> None:
        value = runner.validate_readiness(runner.build_readiness(self._prepared(), now=1))
        self.assertTrue(value["passed"])
        self.assertEqual(value["parser_ready_tasks"], 20)
        self.assertEqual(value["bound_fields"], 80)
        self.assertTrue(value["authorization"]["paired_model_forward"])

    def test_readiness_no_go_disables_model_forward(self) -> None:
        prepared = self._prepared()
        prepared[0] = {
            "index": 0,
            "opaque_id": contract.task_vector()[0]["opaque_id"],
            "fetch_attempts": 1,
            "fetch_successes": 0,
            "http_status": 503,
            "elapsed_seconds": 0.01,
            "ready": False,
        }
        value = runner.validate_readiness(runner.build_readiness(prepared, now=1))
        self.assertFalse(value["passed"])
        self.assertFalse(value["authorization"]["paired_model_forward"])
        self.assertIn("all_exact_fetches_complete", value["findings"])

    def test_readiness_resealed_pass_or_authorization_tamper_is_rejected(self) -> None:
        value = runner.build_readiness(self._prepared(), now=1)
        for mutation in ("passed", "authorization", "checks"):
            changed = copy.deepcopy(value)
            if mutation == "passed":
                changed["passed"] = False
            elif mutation == "authorization":
                changed["authorization"]["paired_model_forward"] = False
            else:
                changed["checks"]["all_fields_bound"] = False
            changed = contract.seal(changed, "readiness_payload_sha256")
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                runner.validate_readiness(changed)

    def test_failed_readiness_barrier_makes_zero_model_calls_and_no_output_root(self) -> None:
        prepared = self._prepared()
        prepared[-1] = {
            "index": 19,
            "opaque_id": contract.task_vector()[19]["opaque_id"],
            "fetch_attempts": 1,
            "fetch_successes": 0,
            "http_status": 500,
            "elapsed_seconds": 0.01,
            "ready": False,
        }
        protocol = {
            "population": {},
            "protected_watchers": [],
        }
        start = {"execution_start_payload_sha256": "x"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(runner, "_clean_pushed"),
                mock.patch.object(runner, "_read", return_value={}),
                mock.patch.object(contract, "validate_protocol", return_value=protocol),
                mock.patch.object(runner, "_validate_start", return_value=start),
                mock.patch.object(runner, "_lease_inactive", return_value=True),
                mock.patch.object(
                    runner, "acquire_deepwide_api_lease", return_value=contextlib.nullcontext()
                ),
                mock.patch.object(contract, "watcher_snapshot", return_value=[]),
                mock.patch.object(runner, "_fetch_exact", side_effect=prepared),
                mock.patch.object(runner, "_synthesize") as synthesize,
            ):
                value = runner.run_forward()
            self.assertFalse(value["passed"])
            synthesize.assert_not_called()
            self.assertFalse((root / contract.OUTPUT_ROOT).exists())
            self.assertTrue((root / contract.PARSER_READINESS).is_file())

    def test_task_row_exact_schema_and_nested_tamper_rejection(self) -> None:
        value = self._task_row()
        self.assertEqual(runner.validate_task_row(value), value)
        changed = copy.deepcopy(value)
        changed["unexpected_metadata"] = True
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(changed)
        changed = copy.deepcopy(value)
        changed["representation_receipt"]["bound_field_count"] = 3
        changed["representation_receipt"].pop("receipt_payload_sha256")
        changed["representation_receipt"]["receipt_payload_sha256"] = (
            representation.payload_sha256(changed["representation_receipt"])
        )
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises((RuntimeError, ValueError)):
            runner.validate_task_row(changed)

    def test_strict_normalizer_accepts_one_exact_table_and_rejects_extra_rows(self) -> None:
        value = (
            "preamble\n| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
            "| --- | --- | --- | --- |\n| gunicorn | 23.0.0 | 2026-07-02 | >=3.9 |"
        )
        normalized = runner.normalize_prediction(value)
        self.assertTrue(normalized.startswith("| Package |"))
        with self.assertRaises(ValueError):
            runner.normalize_prediction(normalized + "\n| extra | row | is | forbidden |")

    def test_mechanism_gate_requires_eight_natural_prediction_changes(self) -> None:
        expected = contract.gates()["mechanism"]
        value = {
            "terminal_tasks": 20,
            "completed_tasks": 20,
            "fallback_tasks": 0,
            "admitted_records": 20,
            "bound_fields": 80,
            "prediction_changed_tasks": 7,
            "evidence_chars": {
                arm: expected["evidence_chars_per_arm"] for arm in contract.ARMS
            },
        }
        for arm in contract.ARMS:
            value[f"{arm}_model_successes"] = 20
            value[f"{arm}_model_attempts"] = 20
        self.assertFalse(runner.mechanism_decision(value)["mechanism_gate_passed"])
        value["prediction_changed_tasks"] = 8
        self.assertTrue(runner.mechanism_decision(value)["mechanism_gate_passed"])

    def test_snapshot_requires_postprediction_freeze_hash_and_exact_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            freeze_path = root / contract.PREDICTION_FREEZE
            freeze_path.parent.mkdir(parents=True)
            freeze_path.write_text("{}\n", encoding="utf-8")
            freeze_hash = contract.sha256(freeze_path)
            values = []
            for index, item in enumerate(self._prepared()):
                values.append(
                    {
                        "index": index,
                        "opaque_id": item["opaque_id"],
                        "project": item["project"],
                        "endpoint_sha256": hashlib.sha256(
                            item["endpoint"].encode()
                        ).hexdigest(),
                        "raw_response_sha256": item["raw_response_sha256"],
                        "raw_response_bytes": item["raw_response_bytes"],
                        "http_status": 200,
                        "record": item["record"],
                        "prediction_freeze_sha256": freeze_hash,
                        "published_after_prediction_freeze": True,
                    }
                )
            with mock.patch.object(runner, "ROOT", root):
                self.assertEqual(len(runner.validate_snapshot_rows(values)), 20)
                changed = copy.deepcopy(values)
                changed[0]["prediction_freeze_sha256"] = "0" * 64
                with self.assertRaises(RuntimeError):
                    runner.validate_snapshot_rows(changed)

    def test_forward_dependency_closure_is_label_blind_and_evaluator_free(self) -> None:
        closure = contract.forward_dependency_closure(ROOT)
        self.assertIn(contract.SOURCE, closure)
        self.assertIn(contract.RUNNER, closure)
        unexpected = []
        evaluator = []
        for relative in closure:
            for finding in semantic_audit._accesses(ROOT / relative, ROOT):
                if not (
                    finding.startswith("src/deepwide_agent/clients.py:")
                    and finding.endswith(":score")
                ):
                    unexpected.append(finding)
            evaluator.extend(
                semantic_audit._evaluator_capabilities(ROOT / relative, ROOT)
            )
        self.assertEqual(unexpected, [])
        self.assertEqual(evaluator, [])

    def test_dependency_manifest_includes_control_test_and_transitive_sources(self) -> None:
        manifest = contract.dependency_manifest(ROOT, tracked=False)
        self.assertIn(str(contract.CONTROL), manifest)
        self.assertIn(str(contract.TEST), manifest)
        self.assertEqual(
            set(manifest),
            {
                *(str(path) for path in contract.forward_dependency_closure(ROOT)),
                str(contract.CONTROL),
                str(contract.TEST),
            },
        )


if __name__ == "__main__":
    unittest.main()
