from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24874_keyless_coverage_bundle import (  # noqa: E402
    BUNDLE_NAME,
    EFFECT_NAME,
    validate_bundle,
)
from deepwide_agent.v24875_keyless_coverage_child_runtime import (  # noqa: E402
    TERMINAL_NAME,
    run_child_bundle,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24873_keyless_fixed_coverage_runtime import (  # noqa: E402
    FullSourceThinSearch,
    LowSourceThinSearch,
)
from test_v24874_keyless_coverage_bundle import (  # noqa: E402
    PreProviderFailureThinSearch,
    PreResponseFailureThinSearch,
    RetryThinSearch,
)


class _MeteredMixin:
    provider_attempts_per_wave = 1
    response_statuses_per_wave: tuple[int, ...] = (200,)
    transport_failures_per_wave = 0

    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        self._increment("hosted_search_attempts", self.provider_attempts_per_wave)
        self._increment("transport_failures", self.transport_failures_per_wave)
        with self._lock:
            for status in self.response_statuses_per_wave:
                self.status_counts[status] = self.status_counts.get(status, 0) + 1
        return output

    def fetch_urls(self, requests_):
        values = list(requests_)
        output = super().fetch_urls(values)
        self._increment("hard_fetch_helper_calls", len(values))
        return output


class MeteredFullSearch(_MeteredMixin, FullSourceThinSearch):
    pass


class MeteredLowSearch(_MeteredMixin, LowSourceThinSearch):
    pass


class MeteredRetrySearch(_MeteredMixin, RetryThinSearch):
    provider_attempts_per_wave = 2
    response_statuses_per_wave = (500, 200)


class MeteredPreResponseFailureSearch(
    _MeteredMixin, PreResponseFailureThinSearch
):
    provider_attempts_per_wave = 1
    response_statuses_per_wave = ()
    transport_failures_per_wave = 1


class MeteredPreProviderFailureSearch(
    _MeteredMixin, PreProviderFailureThinSearch
):
    provider_attempts_per_wave = 0
    response_statuses_per_wave = ()


class V24875KeylessCoverageChildRuntimeTests(unittest.TestCase):
    def clients(self, output: Path, search_cls):
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
        return clock, inner, model, search

    def run_case(self, search_cls):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output = Path(temporary.name)
        directory = output / "task"
        directory.mkdir()
        clock, inner, model, search = self.clients(output, search_cls)
        value = run_child_bundle(
            output_root=output,
            directory=directory,
            task=core_test.task(),
            model=model,
            search=search,
            limits=core_test.limits(),
            expected_model_slot_cap=2,
            monotonic=clock,
        )
        return temporary, output, directory, inner, search, value

    def test_low_source_bundle_commits_actual_two_fetches(self) -> None:
        temporary, output, directory, _inner, _search, _value = self.run_case(
            MeteredLowSearch
        )
        self.addCleanup(temporary.cleanup)
        validate_bundle(
            output_root=output, directory=directory, expected_model_slot_cap=2
        )
        effect = json.loads((directory / EFFECT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(effect["actual_fetches"], 2)
        self.assertEqual(effect["provider_attempts"], 2)
        self.assertEqual(effect["parent_response_calls"], 2)

    def test_retry_bundle_commits_four_responses(self) -> None:
        temporary, output, directory, _inner, _search, _value = self.run_case(
            MeteredRetrySearch
        )
        self.addCleanup(temporary.cleanup)
        validate_bundle(
            output_root=output, directory=directory, expected_model_slot_cap=2
        )
        effect = json.loads((directory / EFFECT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(effect["provider_attempts"], 4)
        self.assertEqual(effect["parent_response_calls"], 4)
        self.assertEqual(effect["status_5xx"], 2)
        self.assertEqual(effect["status_2xx"], 2)

    def test_pre_provider_failure_preserves_committed_parent_prediction(self) -> None:
        temporary, output, directory, _inner, _search, _value = self.run_case(
            MeteredPreProviderFailureSearch
        )
        self.addCleanup(temporary.cleanup)
        validate_bundle(
            output_root=output, directory=directory, expected_model_slot_cap=2
        )
        effect = json.loads((directory / EFFECT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(effect["provider_attempts"], 0)
        self.assertEqual(effect["parent_response_calls"], 0)
        self.assertEqual(effect["parent_failed_query_rows"], 4)
        self.assertTrue((directory / BUNDLE_NAME).is_file())

    def test_pre_response_transport_failure_preserves_committed_parent(self) -> None:
        temporary, output, directory, _inner, _search, _value = self.run_case(
            MeteredPreResponseFailureSearch
        )
        self.addCleanup(temporary.cleanup)
        validate_bundle(
            output_root=output, directory=directory, expected_model_slot_cap=2
        )
        effect = json.loads((directory / EFFECT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(effect["provider_attempts"], 2)
        self.assertEqual(effect["transport_failures"], 2)
        self.assertEqual(effect["parent_response_calls"], 0)

    def test_privileged_input_fails_before_effect_and_without_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            clock, inner, model, search = self.clients(output, MeteredFullSearch)
            with self.assertRaises(ValueError):
                run_child_bundle(
                    output_root=output,
                    directory=directory,
                    task={**core_test.task(), "question_type": "forbidden"},
                    model=model,
                    search=search,
                    limits=core_test.limits(),
                    expected_model_slot_cap=2,
                    monotonic=clock,
                )
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.calls, 0)
            self.assertFalse((directory / BUNDLE_NAME).exists())
            terminal = validate_child_receipt(
                json.loads((directory / TERMINAL_NAME).read_text(encoding="utf-8"))
            )
            self.assertEqual(terminal["stage"], "child_exception")

    def test_nonpristine_surface_fails_before_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            (directory / "result.json").write_text("{}\n", encoding="utf-8")
            clock, inner, model, search = self.clients(output, MeteredFullSearch)
            with self.assertRaises(FileExistsError):
                run_child_bundle(
                    output_root=output, directory=directory, task=core_test.task(),
                    model=model, search=search, limits=core_test.limits(),
                    expected_model_slot_cap=2, monotonic=clock,
                )
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.calls, 0)


if __name__ == "__main__":
    unittest.main()
