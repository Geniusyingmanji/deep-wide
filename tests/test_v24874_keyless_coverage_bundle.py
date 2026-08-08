from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    payload_sha256,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24861_coverage_revision_exact_task import (  # noqa: E402
    IntegratedCoverageRevisionTaskOutcome,
)
from deepwide_agent.v24873_keyless_fixed_coverage_runtime import (  # noqa: E402
    run_v24873_task,
)
from deepwide_agent import v24874_keyless_coverage_bundle as bundle  # noqa: E402
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24862_same_task_coverage_runtime import SyntheticThinSearch  # noqa: E402
from test_v24873_keyless_fixed_coverage_runtime import (  # noqa: E402
    FullSourceThinSearch,
    LowSourceThinSearch,
)


class RetryThinSearch(FullSourceThinSearch):
    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        # One retryable HTTP response before the successful response for each
        # two-query wave. Logical query and page semantics are unchanged.
        self._increment("calls")
        return output


class PreResponseFailureThinSearch(SyntheticThinSearch):
    def search_many(self, queries, **_kwargs):
        values = list(queries)
        self.search_invocations += 1
        self._increment("failures", len(values))
        return [
            {
                "query": query,
                "answer": "",
                "results": [],
                "error": "synthetic pre-response transport failure",
                "provider": "synthetic",
            }
            for query in values
        ]


class PreProviderFailureThinSearch(PreResponseFailureThinSearch):
    """Logical rows fail before any provider attempt or HTTP response."""


class V24874KeylessCoverageBundleTests(unittest.TestCase):
    def outcome(self, output: Path, search_cls):
        clock = core_test.Clock(100.0)
        inner = core_test.SyntheticModel(
            [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
        )
        model = build_deadline_model(
            url="http://unused.invalid/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=core_test.make_slots(output),
            output_root=output,
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=220.0,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=inner,
        )
        search = search_cls(clock, deadline=220.0)
        outcome = run_v24873_task(
            core_test.task(),
            arm="baseline",
            model=model,
            search=search,
            limits=core_test.limits(),
            monotonic=clock,
        )
        parent = outcome.result["parent_result"]
        retrieval = parent["two_wave_retrieval"]
        total = retrieval["receipt"]["total"]
        calls = int(parent["cost"]["search"]["calls"])
        fetches = int(total["fetches_attempted"])
        transport_failures = 0
        hard_timeouts = 0
        if search_cls is PreResponseFailureThinSearch:
            attempts = 2
            transport_failures = 2
            statuses = {}
        elif search_cls is PreProviderFailureThinSearch:
            attempts = 0
            statuses = {}
        elif search_cls is RetryThinSearch:
            attempts = 4
            statuses = {200: 2, 500: 2}
        else:
            attempts = calls
            statuses = {200: calls}
        self.assertEqual(calls, sum(statuses.values()))
        transport = {
            "hosted_search_attempts": attempts,
            "hosted_search_deadline_failures": 0,
            "hard_fetch_helper_calls": fetches,
            "hard_fetch_deadline_failures": 0,
            "fetch_deadline_rejections": 0,
            "fetch_helper_failures": 0,
            "deadline_exhausted": False,
        }
        adjusted = IntegratedCoverageRevisionTaskOutcome(
            copy.deepcopy(outcome.result),
            copy.deepcopy(outcome.parent_model_slot_receipt),
            copy.deepcopy(outcome.model_slot_receipt),
            transport,
            copy.deepcopy(outcome.search_single_shot_receipt),
            copy.deepcopy(outcome.citation_title_backfill_receipt),
            copy.deepcopy(outcome.coverage_revision_receipt),
        )
        return adjusted, statuses, transport_failures, hard_timeouts

    def write_case(self, output: Path, search_cls):
        directory = output / "task"
        directory.mkdir()
        outcome, statuses, failures, timeouts = self.outcome(output, search_cls)
        receipt = bundle.write_bundle(
            output_root=output,
            directory=directory,
            outcome=outcome,
            status_counts=statuses,
            transport_failures=failures,
            hard_total_wall_timeouts=timeouts,
            expected_model_slot_cap=2,
        )
        return directory, receipt

    def effect(self, directory: Path):
        return json.loads(
            (directory / bundle.EFFECT_NAME).read_text(encoding="utf-8")
        )

    def test_low_source_two_fetches_is_valid_below_ten_fetch_cap(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, receipt = self.write_case(output, LowSourceThinSearch)
            effect = self.effect(directory)
            self.assertEqual(effect["admitted_logical_queries"], 4)
            self.assertEqual(effect["executed_logical_queries"], 4)
            self.assertEqual(effect["parent_response_calls"], 2)
            self.assertEqual(effect["actual_fetches"], 2)
            self.assertEqual(effect["fetch_cap"], 10)
            self.assertFalse(effect["fetch_cap_equal_actual_fetches_required"])
            self.assertEqual(
                bundle.validate_bundle(
                    output_root=output,
                    directory=directory,
                    expected_model_slot_cap=2,
                ),
                receipt,
            )

    def test_full_source_ten_fetches_is_valid(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _receipt = self.write_case(output, FullSourceThinSearch)
            effect = self.effect(directory)
            self.assertEqual(effect["executed_logical_queries"], 4)
            self.assertEqual(effect["actual_fetches"], 10)
            self.assertEqual(effect["usable_pages"], 10)
            self.assertEqual(effect["hard_fetch_helper_calls"], 10)

    def test_retry_responses_can_equal_four_logical_queries_coincidentally(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _receipt = self.write_case(output, RetryThinSearch)
            effect = self.effect(directory)
            self.assertEqual(effect["executed_logical_queries"], 4)
            self.assertEqual(effect["parent_response_calls"], 4)
            self.assertEqual(effect["provider_attempts"], 4)
            self.assertEqual(effect["status_2xx"], 2)
            self.assertEqual(effect["status_5xx"], 2)
            self.assertFalse(effect["logical_queries_equal_http_responses_required"])

    def test_pre_response_failure_preserves_completed_parent_prediction(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _receipt = self.write_case(
                output, PreResponseFailureThinSearch
            )
            effect = self.effect(directory)
            self.assertEqual(effect["executed_logical_queries"], 4)
            self.assertEqual(effect["parent_response_calls"], 0)
            self.assertEqual(effect["provider_attempts"], 2)
            self.assertEqual(effect["transport_failures"], 2)
            self.assertEqual(effect["parent_failed_query_rows"], 4)
            self.assertEqual(effect["actual_fetches"], 0)
            self.assertTrue((directory / bundle.RESULT_NAME).is_file())
            self.assertTrue((directory / bundle.BUNDLE_NAME).is_file())

    def test_pre_provider_failure_with_zero_attempts_is_valid(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _receipt = self.write_case(
                output, PreProviderFailureThinSearch
            )
            effect = self.effect(directory)
            self.assertEqual(effect["executed_logical_queries"], 4)
            self.assertEqual(effect["provider_attempts"], 0)
            self.assertEqual(effect["parent_response_calls"], 0)
            self.assertEqual(effect["transport_failures"], 0)
            self.assertEqual(effect["parent_failed_query_rows"], 4)
            self.assertEqual(effect["unrecoverable_search_failures"], 4)

    def test_usable_pages_without_2xx_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _receipt = self.write_case(output, FullSourceThinSearch)
            effect_path = directory / bundle.EFFECT_NAME
            effect = json.loads(effect_path.read_text(encoding="utf-8"))
            effect["status_other"] = effect["status_2xx"]
            effect["status_2xx"] = 0
            effect.pop("receipt_payload_sha256")
            effect["receipt_payload_sha256"] = payload_sha256(effect)
            effect_path.write_text(
                json.dumps(effect, sort_keys=True) + "\n", encoding="utf-8"
            )
            marker_path = directory / bundle.BUNDLE_NAME
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["artifact_manifest"][bundle.EFFECT_NAME] = hashlib.sha256(
                effect_path.read_bytes()
            ).hexdigest()
            marker.pop("receipt_payload_sha256")
            marker["receipt_payload_sha256"] = payload_sha256(marker)
            marker_path.write_text(
                json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                bundle.validate_bundle(
                    output_root=output,
                    directory=directory,
                    expected_model_slot_cap=2,
                )

    def test_resealed_effect_tamper_and_manifest_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _receipt = self.write_case(output, LowSourceThinSearch)
            effect_path = directory / bundle.EFFECT_NAME
            effect = json.loads(effect_path.read_text(encoding="utf-8"))
            effect["actual_fetches"] = 3
            effect.pop("receipt_payload_sha256")
            effect["receipt_payload_sha256"] = payload_sha256(effect)
            effect_path.write_text(
                json.dumps(effect, sort_keys=True) + "\n", encoding="utf-8"
            )
            marker_path = directory / bundle.BUNDLE_NAME
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["artifact_manifest"][bundle.EFFECT_NAME] = hashlib.sha256(
                effect_path.read_bytes()
            ).hexdigest()
            marker.pop("receipt_payload_sha256")
            marker["receipt_payload_sha256"] = payload_sha256(marker)
            marker_path.write_text(
                json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                bundle.validate_bundle(
                    output_root=output,
                    directory=directory,
                    expected_model_slot_cap=2,
                )

    def test_missing_external_effect_receipt_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _receipt = self.write_case(output, FullSourceThinSearch)
            (directory / bundle.EFFECT_NAME).unlink()
            with self.assertRaises(ValueError):
                bundle.validate_bundle(
                    output_root=output,
                    directory=directory,
                    expected_model_slot_cap=2,
                )

    def test_interrupted_write_never_creates_commit_marker(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            outcome, statuses, failures, timeouts = self.outcome(
                output, FullSourceThinSearch
            )
            calls = 0

            def interrupt(path: Path, value):
                nonlocal calls
                calls += 1
                if calls == 5:
                    raise OSError("synthetic")
                bundle._atomic_new(path, value)

            with self.assertRaises(OSError):
                bundle.write_bundle(
                    output_root=output,
                    directory=directory,
                    outcome=outcome,
                    status_counts=statuses,
                    transport_failures=failures,
                    hard_total_wall_timeouts=timeouts,
                    expected_model_slot_cap=2,
                    writer=interrupt,
                )
            self.assertFalse((directory / bundle.BUNDLE_NAME).exists())

    def test_source_has_no_effect_or_evaluator_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24874_keyless_coverage_bundle.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)
        self.assertNotIn("os.environ", source)


if __name__ == "__main__":
    unittest.main()
