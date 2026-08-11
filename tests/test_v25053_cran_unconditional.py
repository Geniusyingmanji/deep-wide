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
from deepwide_agent import v25053_cran_unconditional_denominator_contract as contract  # noqa: E402
from deepwide_agent.native_search import html_to_document  # noqa: E402
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25053_cran_unconditional as runner  # noqa: E402


def html(project: str = "admiralophtha") -> str:
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


class V25053CranUnconditionalTests(unittest.TestCase):
    def _prepared(self, failures: int = 0) -> list[dict]:
        values = []
        for index in range(contract.TASK_COUNT):
            if index >= contract.TASK_COUNT - failures:
                values.append(
                    {
                        "index": index,
                        "opaque_id": contract.task_vector()[index]["opaque_id"],
                        "fetch_attempts": 1,
                        "fetch_successes": 0,
                        "http_status": 404,
                        "elapsed_seconds": 0.01,
                        "paired_evidence_chars": 0,
                        "preparation_terminal": True,
                        "ready": False,
                    }
                )
                continue
            project = contract.PROJECTS[index]
            endpoint = contract.endpoint_vector()[index]
            title, text, _links = html_to_document(html(project), endpoint)
            page = {"title": title, "url": endpoint, "text": text}
            rendered = representation.build_representation(
                contract.task_vector()[index]["question"],
                page,
                page_character_cap=contract.EVIDENCE_CHAR_CAP,
            )
            chars = len(rendered["control_evidence"])
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
                    "paired_evidence_chars": chars,
                    "preparation_terminal": True,
                    "ready": True,
                }
            )
        return values

    def _success_response(self, _question: str, _evidence: str, *, deadline: float):
        del deadline
        table = (
            "| Package | Version | Published | License |\n"
            "| --- | --- | --- | --- |\n"
            "| admiralophtha | 1.8.0 | 2026-08-01 | GPL-2 |"
        )
        return table, {
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "elapsed_milliseconds": 10,
            "provider_attempts": 1,
        }

    def test_population_is_fresh_disjoint_fixed_and_visible_only(self) -> None:
        self.assertEqual(len(contract.PROJECTS), 20)
        self.assertEqual(len(set(contract.PROJECTS)), 20)
        self.assertFalse(set(contract.PROJECTS) & set(contract.PREDECESSOR_PROJECTS))
        for project, task in zip(
            contract.PROJECTS, contract.task_vector(), strict=True
        ):
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(project.casefold(), task["question"].casefold())
            self.assertEqual(
                tuple(extract_robust_visible_columns(task["question"])),
                contract.COLUMNS,
            )

    def test_readiness_passes_for_zero_fifteen_and_twenty_ready(self) -> None:
        for failures in (20, 5, 0):
            with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
                runner, "ROOT", Path(temporary)
            ):
                value = runner.validate_readiness(
                    runner.build_readiness(self._prepared(failures=failures), now=1)
                )
            with self.subTest(failures=failures):
                self.assertTrue(value["passed"])
                self.assertEqual(value["ready_tasks"], 20 - failures)
                self.assertTrue(
                    value["authorization"]["unconditional_fixed_denominator_forward"]
                )

    def test_readiness_rejects_nonterminal_preparation_and_resealed_count_tamper(self) -> None:
        prepared = self._prepared(failures=20)
        prepared[-1]["preparation_terminal"] = False
        with self.assertRaises(RuntimeError):
            runner.build_readiness(prepared, now=1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            runner, "ROOT", Path(temporary)
        ):
            value = runner.build_readiness(self._prepared(failures=5), now=1)
        changed = copy.deepcopy(value)
        changed["ready_tasks"] = 14
        changed = contract.seal(changed, "readiness_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_readiness(changed)

    def test_protocol_removes_batch_threshold_and_exact_schema(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertIsNone(value["execution"]["ready_count_activation_threshold"])
        self.assertEqual(
            value["execution"]["control_plane_change_from_v25052"],
            "remove_batch_ready_activation_threshold",
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

    def test_unready_task_freezes_paired_fallback_without_model_call(self) -> None:
        item = self._prepared(failures=1)[-1]
        with mock.patch.object(runner, "_synthesize") as synthesize:
            value = runner._row_from_prepared(item)
        synthesize.assert_not_called()
        checked = runner.validate_task_row(value)
        self.assertTrue(checked["preparation_failure_as_zero"])
        self.assertEqual(checked["model_attempts"], {arm: 0 for arm in contract.ARMS})
        self.assertEqual(
            checked["predictions"],
            {arm: contract.FALLBACK_TABLE for arm in contract.ARMS},
        )

    def test_ready_task_uses_successor_synthesis_binding(self) -> None:
        item = self._prepared()[0]
        with mock.patch.object(runner, "_synthesize", side_effect=self._success_response):
            value = runner._row_from_prepared(item)
        checked = runner.validate_task_row(value)
        self.assertTrue(checked["completed"])
        self.assertEqual(checked["model_attempts"], {arm: 1 for arm in contract.ARMS})

    def test_task_row_role_and_resealed_tamper_fail_closed(self) -> None:
        item = self._prepared()[0]
        with mock.patch.object(runner, "_synthesize", side_effect=self._success_response):
            value = runner._row_from_prepared(item)
        self.assertEqual(value["role"], "v25053_cran_unconditional_task_result")
        changed = copy.deepcopy(value)
        changed["evidence_chars"][contract.CANDIDATE_ARM] += 1
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(changed)

    def test_mechanism_gate_is_postforward_and_requires_fifteen_ready(self) -> None:
        value = {
            "terminal_tasks": 20,
            "terminal_arm_predictions": 40,
            "ready_tasks": 14,
            "preparation_failure_tasks": 6,
            "completed_tasks": 14,
            "fallback_tasks": 6,
            "identity_bound_records": 14,
            "bound_target_fields": 42,
            "prediction_changed_tasks": 6,
            "evidence_chars": {arm: 30_000 for arm in contract.ARMS},
        }
        for arm in contract.ARMS:
            value[f"{arm}_model_successes"] = 14
            value[f"{arm}_model_attempts"] = 14
        self.assertFalse(runner.mechanism_decision(value)["mechanism_gate_passed"])
        value.update(
            {
                "ready_tasks": 15,
                "preparation_failure_tasks": 5,
                "completed_tasks": 15,
                "fallback_tasks": 5,
                "identity_bound_records": 15,
                "bound_target_fields": 45,
            }
        )
        for arm in contract.ARMS:
            value[f"{arm}_model_successes"] = 15
            value[f"{arm}_model_attempts"] = 15
        self.assertTrue(runner.mechanism_decision(value)["mechanism_gate_passed"])

    def test_full_local_forward_with_five_failures_freezes_forty_predictions(self) -> None:
        prepared = self._prepared(failures=5)
        protocol = {"protected_watchers": []}
        start = {"execution_start_payload_sha256": "x"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            start_path = root / contract.EXECUTION_START
            start_path.parent.mkdir(parents=True)
            start_path.write_text("{}\n", encoding="utf-8")
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
                mock.patch.object(
                    runner, "_synthesize", side_effect=self._success_response
                ),
            ):
                value = runner.run_forward()
            self.assertEqual(value["task_count"], 20)
            self.assertEqual(value["aggregate"]["terminal_arm_predictions"], 40)
            self.assertEqual(value["aggregate"]["ready_tasks"], 15)
            self.assertEqual(value["aggregate"]["fallback_tasks"], 5)
            self.assertTrue((root / contract.FORWARD_RESULT).is_file())

    def test_strict_normalizer_rejects_extra_rows(self) -> None:
        value = (
            "preamble\n| Package | Version | Published | License |\n"
            "| --- | --- | --- | --- |\n"
            "| admiralophtha | 1.8.0 | 2026-08-01 | GPL-2 |"
        )
        normalized = runner.normalize_prediction(value)
        self.assertTrue(normalized.startswith("| Package |"))
        with self.assertRaises(ValueError):
            runner.normalize_prediction(normalized + "\n| extra | row | is | forbidden |")

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

    def test_dependency_manifest_includes_successor_and_transitive_parent(self) -> None:
        manifest = contract.dependency_manifest(ROOT, tracked=False)
        self.assertIn(str(contract.CONTROL), manifest)
        self.assertIn(str(contract.TEST), manifest)
        self.assertIn("scripts/run_v25052_cran_fixed_denominator.py", manifest)
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
