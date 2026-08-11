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
from deepwide_agent import v25052_cran_fixed_denominator_contract as contract  # noqa: E402
from deepwide_agent.native_search import html_to_document  # noqa: E402
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25052_cran_fixed_denominator as runner  # noqa: E402


def html(project: str = "sapflow") -> str:
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


class V25052CranFixedDenominatorTests(unittest.TestCase):
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
                        "http_status": 200,
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
            self.assertTrue(
                0 < chars == len(rendered["candidate_evidence"])
                < contract.EVIDENCE_CHAR_CAP
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
            "| sapflow | 1.8.0 | 2026-08-01 | GPL-2 |"
        )
        return table, {
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "elapsed_milliseconds": 10,
            "provider_attempts": 1,
        }

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

    def test_preparation_validator_accepts_two_content_free_failures(self) -> None:
        values = runner._validate_prepared(self._prepared(failures=2))
        self.assertEqual(sum(row["ready"] for row in values), 18)
        self.assertEqual(
            set(values[-1]),
            {
                "index", "opaque_id", "fetch_attempts", "fetch_successes",
                "http_status", "elapsed_seconds", "paired_evidence_chars",
                "preparation_terminal", "ready",
            },
        )

    def test_readiness_go_at_eighteen_and_no_go_at_seventeen(self) -> None:
        for failures, passed in ((2, True), (3, False)):
            with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
                runner, "ROOT", Path(temporary)
            ):
                value = runner.validate_readiness(
                    runner.build_readiness(self._prepared(failures=failures), now=1)
                )
            with self.subTest(failures=failures):
                self.assertIs(value["passed"], passed)
                self.assertEqual(value["ready_tasks"], 20 - failures)
                self.assertIs(
                    value["authorization"]["fixed_denominator_paired_forward"],
                    passed,
                )

    def test_resealed_readiness_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            runner, "ROOT", Path(temporary)
        ):
            value = runner.build_readiness(self._prepared(failures=2), now=1)
        for mutation in ("ready", "authorization", "checks"):
            changed = copy.deepcopy(value)
            if mutation == "ready":
                changed["ready_tasks"] = 17
            elif mutation == "authorization":
                changed["authorization"]["fixed_denominator_paired_forward"] = False
            else:
                changed["checks"]["minimum_ready_tasks_met"] = False
            changed = contract.seal(changed, "readiness_payload_sha256")
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                runner.validate_readiness(changed)

    def test_protocol_freezes_fixed_denominator_and_exact_schema(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(value["execution"]["minimum_ready_tasks"], 18)
        self.assertEqual(value["execution"]["model_calls_per_unready_arm"], 0)
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

    def test_unready_task_has_zero_model_calls_and_paired_fallback(self) -> None:
        item = self._prepared(failures=1)[-1]
        with mock.patch.object(runner, "_synthesize") as synthesize:
            value = runner._row_from_prepared(item)
        synthesize.assert_not_called()
        checked = runner.validate_task_row(value)
        self.assertTrue(checked["preparation_failure_as_zero"])
        self.assertTrue(checked["failure_as_zero"])
        self.assertEqual(checked["model_attempts"], {arm: 0 for arm in contract.ARMS})
        self.assertEqual(
            checked["predictions"],
            {arm: contract.FALLBACK_TABLE for arm in contract.ARMS},
        )

    def test_ready_success_row_is_distinct_from_preparation_failure(self) -> None:
        item = self._prepared()[0]
        with mock.patch.object(runner, "_synthesize", side_effect=self._success_response):
            value = runner._row_from_prepared(item)
        checked = runner.validate_task_row(value)
        self.assertTrue(checked["preparation_ready"])
        self.assertTrue(checked["completed"])
        self.assertFalse(checked["failure_as_zero"])
        self.assertEqual(checked["model_attempts"], {arm: 1 for arm in contract.ARMS})

    def test_ready_model_failure_is_not_preparation_failure(self) -> None:
        item = self._prepared()[0]
        with mock.patch.object(runner, "_synthesize", side_effect=RuntimeError("boom")):
            value = runner._row_from_prepared(item)
        checked = runner.validate_task_row(value)
        self.assertTrue(checked["preparation_ready"])
        self.assertFalse(checked["preparation_failure_as_zero"])
        self.assertTrue(checked["failure_as_zero"])
        self.assertEqual(
            checked["predictions"],
            {arm: contract.FALLBACK_TABLE for arm in contract.ARMS},
        )

    def test_task_row_resealed_state_tamper_is_rejected(self) -> None:
        item = self._prepared()[0]
        with mock.patch.object(runner, "_synthesize", side_effect=self._success_response):
            value = runner._row_from_prepared(item)
        mutations = []
        changed = copy.deepcopy(value)
        changed["preparation_ready"] = False
        changed["preparation_failure_as_zero"] = True
        mutations.append(changed)
        changed = copy.deepcopy(value)
        changed["evidence_chars"][contract.CANDIDATE_ARM] += 1
        mutations.append(changed)
        changed = copy.deepcopy(value)
        changed["model_attempts"][contract.CONTROL_ARM] = 0
        mutations.append(changed)
        for changed in mutations:
            changed = contract.seal(changed, "result_payload_sha256")
            with self.assertRaises(RuntimeError):
                runner.validate_task_row(changed)

    def test_mechanism_gate_requires_only_preparation_fallbacks_and_six_changes(self) -> None:
        value = {
            "terminal_tasks": 20,
            "terminal_arm_predictions": 40,
            "ready_tasks": 18,
            "preparation_failure_tasks": 2,
            "completed_tasks": 18,
            "fallback_tasks": 2,
            "identity_bound_records": 18,
            "bound_target_fields": 54,
            "prediction_changed_tasks": 5,
            "evidence_chars": {arm: 40_000 for arm in contract.ARMS},
        }
        for arm in contract.ARMS:
            value[f"{arm}_model_successes"] = 18
            value[f"{arm}_model_attempts"] = 18
        self.assertFalse(runner.mechanism_decision(value)["mechanism_gate_passed"])
        value["prediction_changed_tasks"] = 6
        self.assertTrue(runner.mechanism_decision(value)["mechanism_gate_passed"])
        value["fallback_tasks"] = 3
        self.assertFalse(runner.mechanism_decision(value)["mechanism_gate_passed"])

    def test_below_readiness_threshold_makes_zero_model_calls_and_no_output_root(self) -> None:
        prepared = self._prepared(failures=3)
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

    def test_strict_normalizer_rejects_extra_rows(self) -> None:
        value = (
            "preamble\n| Package | Version | Published | License |\n"
            "| --- | --- | --- | --- |\n| sapflow | 1.8.0 | 2026-08-01 | GPL-2 |"
        )
        normalized = runner.normalize_prediction(value)
        self.assertTrue(normalized.startswith("| Package |"))
        with self.assertRaises(ValueError):
            runner.normalize_prediction(normalized + "\n| extra | row | is | forbidden |")

    def test_snapshot_supports_ready_records_and_content_free_failures(self) -> None:
        prepared = self._prepared(failures=2)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            freeze_path = root / contract.PREDICTION_FREEZE
            freeze_path.parent.mkdir(parents=True)
            freeze_path.write_text("{}\n", encoding="utf-8")
            freeze_hash = contract.sha256(freeze_path)
            values = []
            for index, item in enumerate(prepared):
                ready = item["ready"]
                values.append(
                    {
                        "index": index,
                        "opaque_id": item["opaque_id"],
                        "project": contract.PROJECTS[index],
                        "preparation_ready": ready,
                        "endpoint_sha256": hashlib.sha256(
                            contract.endpoint_vector()[index].encode()
                        ).hexdigest(),
                        "raw_response_sha256": item.get("raw_response_sha256"),
                        "raw_response_bytes": item.get("raw_response_bytes"),
                        "decoded_page_sha256": item.get("decoded_page_sha256"),
                        "decoded_page_characters": item.get("decoded_page_characters"),
                        "http_status": item["http_status"],
                        "record": item.get("record") if ready else None,
                        "prediction_freeze_sha256": freeze_hash,
                        "published_after_prediction_freeze": True,
                    }
                )
            with mock.patch.object(runner, "ROOT", root):
                self.assertEqual(len(runner.validate_snapshot_rows(values)), 20)
                changed = copy.deepcopy(values)
                changed[-1]["record"] = {column: "x" for column in contract.COLUMNS}
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
        self.assertIn("scripts/run_v25050_cran_html_representation.py", manifest)
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
