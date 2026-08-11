from __future__ import annotations

import contextlib
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25049_page_self_identified_record as representation  # noqa: E402
from deepwide_agent import v25051_cran_shared_length_contract as contract  # noqa: E402
from deepwide_agent.native_search import html_to_document  # noqa: E402
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25051_cran_shared_length as runner  # noqa: E402


def html(project: str = "RNifti") -> str:
    return (
        "<html><head><title>CRAN: Package " + project + "</title></head><body>"
        "<h2>CRAN: Package " + project + "</h2>"
        "<p>" + ("Ordinary package documentation. " * 80) + "</p>"
        "<table>"
        "<tr><td>Version:</td><td>1.8.0</td></tr>"
        "<tr><td>Published:</td><td>2026-08-01</td></tr>"
        "<tr><td>License:</td><td>GPL-2</td></tr>"
        "</table></body></html>"
    )


class V25051CranSharedLengthTests(unittest.TestCase):
    def _prepared(self, count: int = contract.TASK_COUNT) -> list[dict]:
        values = []
        for index in range(count):
            project = contract.PROJECTS[index]
            endpoint = contract.endpoint_vector()[index]
            title, text, _links = html_to_document(html(project), endpoint)
            page = {"title": title, "url": endpoint, "text": text}
            rendered = representation.build_representation(
                contract.task_vector()[index]["question"],
                page,
                page_character_cap=contract.EVIDENCE_CHAR_CAP,
            )
            control_chars = len(rendered["control_evidence"])
            candidate_chars = len(rendered["candidate_evidence"])
            self.assertTrue(
                0 < control_chars == candidate_chars < contract.EVIDENCE_CHAR_CAP
            )
            values.append(
                {
                    "index": index,
                    "opaque_id": contract.task_vector()[index]["opaque_id"],
                    "question": contract.task_vector()[index]["question"],
                    "project": project,
                    "endpoint": endpoint,
                    "raw_response_sha256": hashlib.sha256(
                        html(project).encode()
                    ).hexdigest(),
                    "raw_response_bytes": len(html(project).encode()),
                    "decoded_page_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "decoded_page_characters": len(text),
                    "control_evidence": rendered["control_evidence"],
                    "candidate_evidence": rendered["candidate_evidence"],
                    "receipt": rendered["page_self_record_receipt"],
                    "record": representation.extract_record(
                        contract.task_vector()[index]["question"], page
                    ),
                    "fetch_attempts": 1,
                    "fetch_successes": 1,
                    "http_status": 200,
                    "elapsed_seconds": 0.01,
                    "paired_evidence_chars": control_chars,
                    "ready": True,
                }
            )
        return values

    def _task_row(self, *, changed: bool = True) -> dict:
        item = self._prepared(1)[0]
        control = (
            "| Package | Version | Published | License |\n"
            "| --- | --- | --- | --- |\n"
            "| RNifti | Unknown | Unknown | Unknown |"
        )
        candidate = (
            "| Package | Version | Published | License |\n"
            "| --- | --- | --- | --- |\n"
            "| RNifti | 1.8.0 | 2026-08-01 | GPL-2 |"
            if changed else control
        )
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
            "role": "v25051_cran_shared_length_task_result",
            "protocol_id": contract.PROTOCOL_ID,
            "opaque_id": item["opaque_id"],
            "runtime_input_keys": [
                "opaque_id", "question", "same_forward_public_cran_html_bytes"
            ],
            "terminal": True,
            "completed": True,
            "failure_as_zero": False,
            "fetch_attempts": 1,
            "fetch_successes": 1,
            "http_status": 200,
            "representation_receipt": item["receipt"],
            "evidence_chars": {
                arm: item["paired_evidence_chars"] for arm in contract.ARMS
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
            "same_exact_public_response_and_decoded_page_for_both_arms": True,
            "control_is_raw_decoded_page_prefix_up_to_cap": True,
            "candidate_is_page_self_identified_record_then_same_length_raw_prefix": True,
            "task_local_evidence_lengths_positive_equal_and_at_most_cap": True,
            "same_prompt_model_output_cap_attempt_count_and_deadline": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_credit_or_routes": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
            "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential": False,
        }
        return contract.seal(value, "result_payload_sha256")

    def test_population_is_fresh_disjoint_fixed_and_question_hides_identity(self) -> None:
        self.assertEqual(len(contract.PROJECTS), 20)
        self.assertEqual(len(set(contract.PROJECTS)), 20)
        self.assertFalse(set(contract.PROJECTS) & set(contract.PREDECESSOR_PROJECTS))
        self.assertTrue(
            all(set(row) == {"opaque_id", "question"} for row in contract.task_vector())
        )
        for project, task in zip(
            contract.PROJECTS, contract.task_vector(), strict=True
        ):
            self.assertNotIn(project.casefold(), task["question"].casefold())
            self.assertEqual(
                tuple(extract_robust_visible_columns(task["question"])),
                contract.COLUMNS,
            )

    def test_short_production_html_uses_equal_actual_length_and_engages(self) -> None:
        item = self._prepared(1)[0]
        self.assertLess(item["paired_evidence_chars"], contract.EVIDENCE_CHAR_CAP)
        self.assertEqual(
            len(item["control_evidence"]), len(item["candidate_evidence"])
        )
        self.assertNotEqual(item["control_evidence"], item["candidate_evidence"])
        self.assertTrue(item["receipt"]["mechanism_engaged"])
        self.assertEqual(item["receipt"]["retained_bound_observation_count"], 3)

    def test_readiness_go_accepts_twenty_equal_positive_lengths_below_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            runner, "ROOT", Path(temporary)
        ):
            value = runner.validate_readiness(
                runner.build_readiness(self._prepared(), now=1)
            )
        self.assertTrue(value["passed"])
        self.assertEqual(value["parser_ready_tasks"], 20)
        self.assertEqual(value["paired_positive_bounded_evidence_tasks"], 20)
        self.assertLess(
            value["shared_evidence_characters_per_arm"],
            contract.TASK_COUNT * contract.EVIDENCE_CHAR_CAP,
        )

    def test_readiness_no_go_disables_model_forward(self) -> None:
        prepared = self._prepared()
        prepared[-1] = {
            "index": 19,
            "opaque_id": contract.task_vector()[19]["opaque_id"],
            "fetch_attempts": 1,
            "fetch_successes": 0,
            "http_status": 503,
            "elapsed_seconds": 0.01,
            "paired_evidence_chars": 0,
            "ready": False,
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            runner, "ROOT", Path(temporary)
        ):
            value = runner.validate_readiness(
                runner.build_readiness(prepared, now=1)
            )
        self.assertFalse(value["passed"])
        self.assertFalse(value["authorization"]["paired_model_forward"])

    def test_resealed_readiness_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            runner, "ROOT", Path(temporary)
        ):
            value = runner.build_readiness(self._prepared(), now=1)
        for mutation in ("authorization", "length", "checks"):
            changed = copy.deepcopy(value)
            if mutation == "authorization":
                changed["authorization"]["paired_model_forward"] = False
            elif mutation == "length":
                changed["shared_evidence_characters_per_arm"] = 0
            else:
                changed["checks"][
                    "all_tasks_have_paired_positive_bounded_evidence"
                ] = False
            changed = contract.seal(changed, "readiness_payload_sha256")
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                runner.validate_readiness(changed)

    def test_protocol_exact_schema_and_single_control_plane_change(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(
            value["execution"]["only_control_plane_change_from_v25050"],
            "shared_positive_task_local_evidence_length_at_most_cap",
        )
        with (
            mock.patch.object(
                contract, "dependency_manifest", return_value=value["source_manifest"]
            ),
            mock.patch.object(contract, "sha256", return_value="0" * 64),
            mock.patch.object(
                contract, "watcher_snapshot", return_value=value["protected_watchers"]
            ),
        ):
            self.assertEqual(contract.validate_protocol(ROOT, value), value)
            changed = copy.deepcopy(value)
            changed["unexpected_metadata"] = True
            changed = contract.seal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                contract.validate_protocol(ROOT, changed)

    def test_failed_readiness_barrier_makes_zero_model_calls_and_no_output_root(self) -> None:
        prepared = self._prepared()
        prepared[-1] = {
            "index": 19,
            "opaque_id": contract.task_vector()[19]["opaque_id"],
            "fetch_attempts": 1,
            "fetch_successes": 0,
            "http_status": 500,
            "elapsed_seconds": 0.01,
            "paired_evidence_chars": 0,
            "ready": False,
        }
        protocol = {"protected_watchers": []}
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
                    runner,
                    "acquire_deepwide_api_lease",
                    return_value=contextlib.nullcontext(),
                ),
                mock.patch.object(contract, "watcher_snapshot", return_value=[]),
                mock.patch.object(
                    runner, "_fetch_exact", side_effect=lambda index: prepared[index]
                ),
                mock.patch.object(runner, "_synthesize") as synthesize,
            ):
                value = runner.run_forward()
            self.assertFalse(value["passed"])
            synthesize.assert_not_called()
            self.assertFalse((root / contract.OUTPUT_ROOT).exists())
            self.assertTrue((root / contract.PARSER_READINESS).is_file())

    def test_task_row_exact_schema_usage_and_length_tamper_rejection(self) -> None:
        value = self._task_row()
        self.assertEqual(runner.validate_task_row(value), value)
        mutations = []
        changed = copy.deepcopy(value)
        changed["unexpected_metadata"] = True
        mutations.append(changed)
        changed = copy.deepcopy(value)
        changed["evidence_chars"][contract.CANDIDATE_ARM] += 1
        mutations.append(changed)
        changed = copy.deepcopy(value)
        changed["model_usage"][contract.CONTROL_ARM]["total_tokens"] = -1
        mutations.append(changed)
        for changed in mutations:
            changed = contract.seal(changed, "result_payload_sha256")
            with self.assertRaises(RuntimeError):
                runner.validate_task_row(changed)

    def test_unexpected_task_exception_is_terminal_failure_as_zero(self) -> None:
        with mock.patch.object(runner, "_synthesize", side_effect=RuntimeError("boom")):
            value = runner._row_from_prepared(self._prepared(1)[0])
        checked = runner.validate_task_row(value)
        self.assertFalse(checked["completed"])
        self.assertTrue(checked["failure_as_zero"])
        self.assertEqual(
            checked["predictions"],
            {arm: contract.FALLBACK_TABLE for arm in contract.ARMS},
        )

    def test_strict_normalizer_rejects_extra_rows(self) -> None:
        value = (
            "preamble\n| Package | Version | Published | License |\n"
            "| --- | --- | --- | --- |\n| RNifti | 1.8.0 | 2026-08-01 | GPL-2 |"
        )
        normalized = runner.normalize_prediction(value)
        self.assertTrue(normalized.startswith("| Package |"))
        with self.assertRaises(ValueError):
            runner.normalize_prediction(normalized + "\n| extra | row | is | forbidden |")

    def test_mechanism_gate_requires_six_changes_and_equal_bounded_totals(self) -> None:
        total = sum(item["paired_evidence_chars"] for item in self._prepared())
        value = {
            "terminal_tasks": 20,
            "completed_tasks": 20,
            "fallback_tasks": 0,
            "identity_bound_records": 20,
            "bound_target_fields": 60,
            "paired_positive_bounded_evidence_tasks": 20,
            "prediction_changed_tasks": 5,
            "evidence_chars": {arm: total for arm in contract.ARMS},
        }
        for arm in contract.ARMS:
            value[f"{arm}_model_successes"] = 20
            value[f"{arm}_model_attempts"] = 20
        self.assertFalse(runner.mechanism_decision(value)["mechanism_gate_passed"])
        value["prediction_changed_tasks"] = 6
        self.assertTrue(runner.mechanism_decision(value)["mechanism_gate_passed"])
        value["evidence_chars"][contract.CANDIDATE_ARM] += 1
        self.assertFalse(runner.mechanism_decision(value)["mechanism_gate_passed"])

    def test_snapshot_requires_hashes_identity_and_exact_values(self) -> None:
        prepared = self._prepared()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            freeze_path = root / contract.PREDICTION_FREEZE
            freeze_path.parent.mkdir(parents=True)
            freeze_path.write_text("{}\n", encoding="utf-8")
            freeze_hash = contract.sha256(freeze_path)
            values = [
                {
                    "index": index,
                    "opaque_id": item["opaque_id"],
                    "project": item["project"],
                    "endpoint_sha256": hashlib.sha256(
                        item["endpoint"].encode()
                    ).hexdigest(),
                    "raw_response_sha256": item["raw_response_sha256"],
                    "raw_response_bytes": item["raw_response_bytes"],
                    "decoded_page_sha256": item["decoded_page_sha256"],
                    "decoded_page_characters": item["decoded_page_characters"],
                    "http_status": 200,
                    "record": item["record"],
                    "prediction_freeze_sha256": freeze_hash,
                    "published_after_prediction_freeze": True,
                }
                for index, item in enumerate(prepared)
            ]
            with mock.patch.object(runner, "ROOT", root):
                self.assertEqual(len(runner.validate_snapshot_rows(values)), 20)
                changed = copy.deepcopy(values)
                changed[0]["record"]["Package"] = "different-package"
                with self.assertRaises(RuntimeError):
                    runner.validate_snapshot_rows(changed)

    def test_forward_dependency_closure_is_label_blind_and_evaluator_free(self) -> None:
        unexpected = []
        evaluator = []
        for relative in contract.forward_dependency_closure(ROOT):
            for finding in semantic_audit._accesses(ROOT / relative, ROOT):
                if not finding.endswith("clients.py:565:score"):
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
        self.assertIn(
            "scripts/run_v25050_cran_html_representation.py", manifest
        )
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
