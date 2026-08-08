from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    STATUS_BUCKETS,
    empty_receipt,
)
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    empty_rate_aware_receipt,
)
from deepwide_agent.v24862_same_task_coverage_runtime import (  # noqa: E402
    run_v24862_task,
)
from deepwide_agent import v24863_coverage_revision_child_bundle as frozen  # noqa: E402
from deepwide_agent import v24867_response_aware_coverage_bundle as repaired  # noqa: E402
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24862_same_task_coverage_runtime import SyntheticThinSearch  # noqa: E402
from test_v24863_coverage_revision_child_bundle import pacing_receipt  # noqa: E402


def _reseal(value: dict[str, object]) -> dict[str, object]:
    value = copy.deepcopy(value)
    value.pop("receipt_payload_sha256", None)
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


class ScenarioSearch(SyntheticThinSearch):
    """Synthetic search whose counters retain their production semantics."""

    def __init__(self, *args, scenario: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scenario = scenario
        self.direct_successes = 0
        self.direct_failures = 0
        self.direct_attempts = 0
        self.direct_2xx = 0
        self.direct_429 = 0

    def search_many(self, queries, **kwargs):
        values = list(queries)
        if self.scenario == "pre_provider_failure":
            self.search_invocations += 1
            self._increment("failures", len(values))
            self.direct_failures += len(values)
            return [
                {
                    "query": query,
                    "answer": "",
                    "results": [],
                    "error": "synthetic pre-provider failure",
                    "provider": "synthetic",
                }
                for query in values
            ]
        if self.scenario == "retry":
            output = super().search_many(values, **kwargs)
            # One retryable HTTP response precedes the two terminal 2xx
            # responses in each two-query wave.
            self._increment("calls")
            self.direct_successes += len(values)
            self.direct_attempts += len(values) + 1
            self.direct_2xx += len(values)
            self.direct_429 += 1
            return output
        raise AssertionError(self.scenario)

    def direct_search_receipt(self):
        value = empty_receipt(2)
        value.update(
            {
                "successful_queries": self.direct_successes,
                "failed_queries": self.direct_failures,
                "provider_attempts": self.direct_attempts,
                "slot_acquisitions": self.direct_attempts,
                "status_2xx": self.direct_2xx,
                "status_429": self.direct_429,
                "retryable_responses": self.direct_429,
            }
        )
        return _reseal(value)

    def rate_aware_search_receipt(self):
        value = empty_rate_aware_receipt()
        value.update(
            {
                "provider_start_reservations": self.direct_attempts,
                "provider_429_responses": self.direct_429,
                "provider_cooldown_activations": self.direct_429,
            }
        )
        return _reseal(value)


class V24867ResponseAwareCoverageBundleTests(unittest.TestCase):
    def build_outcome(self, output: Path, scenario: str):
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
            pool_id="v24263_score_first_global_model_slots_v1",
            absolute_deadline=220.0,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=inner,
        )
        search = ScenarioSearch(clock, deadline=220.0, scenario=scenario)
        outcome = run_v24862_task(
            core_test.task(),
            arm="baseline",
            model=model,
            search=search,
            limits=core_test.limits(),
            two_wave_policy=TwoWavePolicy(),
            monotonic=clock,
        )
        parent = outcome.result["parent_result"]
        total = parent["two_wave_retrieval"]["receipt"]["total"]
        if scenario == "pre_provider_failure":
            self.assertEqual(total["queries_executed"], 4)
            self.assertEqual(total["fetches_attempted"], 0)
            self.assertEqual(parent["cost"]["search"]["calls"], 0)
            self.assertEqual(parent["cost"]["search"]["failures"], 4)
        elif scenario == "retry":
            self.assertEqual(total["queries_executed"], 4)
            self.assertEqual(parent["cost"]["search"]["calls"], 6)
            self.assertEqual(parent["cost"]["search"]["failures"], 0)
        return outcome, search

    def write_case(
        self,
        output: Path,
        *,
        scenario: str,
    ) -> tuple[Path, dict[str, object]]:
        task_directory = output / "task"
        task_directory.mkdir()
        outcome, search = self.build_outcome(output, scenario)
        bundle = repaired.write_bundle(
            output_root=output,
            directory=task_directory,
            outcome=outcome,
            direct_receipt=search.direct_search_receipt(),
            rate_receipt=search.rate_aware_search_receipt(),
            pacing_receipt=pacing_receipt(),
            expected_model_slot_cap=2,
            expected_tavily_key_slot_cap=2,
        )
        return task_directory, bundle

    def test_pre_provider_failures_preserve_completed_parent_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory, bundle = self.write_case(
                output,
                scenario="pre_provider_failure",
            )
            self.assertEqual(
                repaired.validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                ),
                bundle,
            )
            with self.assertRaises(ValueError):
                frozen.validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                )

    def test_retry_responses_can_exceed_logical_queries(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory, bundle = self.write_case(
                output,
                scenario="retry",
            )
            self.assertEqual(
                repaired.validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                ),
                bundle,
            )
            with self.assertRaises(ValueError):
                frozen.validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                )

    def test_resealed_status_counter_tamper_fails_cross_binding(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory, _bundle = self.write_case(
                output,
                scenario="retry",
            )
            path = task_directory / repaired.DIRECT_NAME
            value = json.loads(path.read_text(encoding="utf-8"))
            value["status_2xx"] = 3
            value = _reseal(value)
            path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
            bundle_path = task_directory / repaired.BUNDLE_NAME
            manifest = json.loads(bundle_path.read_text(encoding="utf-8"))
            import hashlib

            manifest["artifact_manifest"][repaired.DIRECT_NAME] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            manifest.pop("receipt_payload_sha256")
            manifest["receipt_payload_sha256"] = payload_sha256(manifest)
            bundle_path.write_text(
                json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                repaired.validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                )

    def test_success_without_2xx_response_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory, _bundle = self.write_case(
                output,
                scenario="retry",
            )
            direct_path = task_directory / repaired.DIRECT_NAME
            direct = json.loads(direct_path.read_text(encoding="utf-8"))
            direct["status_2xx"] = 0
            direct["status_other"] = 4
            direct = _reseal(direct)
            direct_path.write_text(
                json.dumps(direct, sort_keys=True) + "\n", encoding="utf-8"
            )
            bundle_path = task_directory / repaired.BUNDLE_NAME
            manifest = json.loads(bundle_path.read_text(encoding="utf-8"))
            import hashlib

            manifest["artifact_manifest"][repaired.DIRECT_NAME] = hashlib.sha256(
                direct_path.read_bytes()
            ).hexdigest()
            manifest.pop("receipt_payload_sha256")
            manifest["receipt_payload_sha256"] = payload_sha256(manifest)
            bundle_path.write_text(
                json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                repaired.validate_bundle(
                    output_root=output,
                    directory=task_directory,
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                )

    def test_isolated_successor_does_not_patch_frozen_module(self) -> None:
        repaired.validate_isolation()
        self.assertIs(
            frozen._validate_values.__globals__["_runtime_binding"],
            frozen._runtime_binding,
        )

    def test_source_has_no_effect_or_privileged_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24867_response_aware_coverage_bundle.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name for name in imports))
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)
        self.assertNotIn("os.environ", source)


if __name__ == "__main__":
    unittest.main()
