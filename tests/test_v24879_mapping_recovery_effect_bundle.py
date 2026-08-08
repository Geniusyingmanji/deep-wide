from __future__ import annotations

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
from deepwide_agent.v24280_task_union_single_shot import MAPPING_FAILURE  # noqa: E402
from deepwide_agent import v24874_keyless_coverage_bundle as frozen  # noqa: E402
from deepwide_agent import v24879_mapping_recovery_effect_bundle as target  # noqa: E402
from test_v24874_keyless_coverage_bundle import (  # noqa: E402
    FullSourceThinSearch,
    V24874KeylessCoverageBundleTests,
)
from test_v24862_same_task_coverage_runtime import SyntheticThinSearch  # noqa: E402


class MappingRecoveryThinSearch(SyntheticThinSearch):
    """No query-local citations, but action sources recover the task union."""

    def search_many(self, queries, **_kwargs):
        self.search_invocations += 1
        values = list(queries)
        self._increment("calls")
        self._increment("failures", len(values))
        self._increment("tool_calls")
        batches = [
            {
                "query": query,
                "answer": "",
                "results": [],
                "error": MAPPING_FAILURE,
                "provider": "synthetic",
            }
            for query in values
        ]
        if batches:
            batches[0]["hosted_search_trace"] = {
                "response_id": f"r{self.search_invocations}",
                "search_call_ids": [f"s{self.search_invocations}"],
                "actions": [
                    {
                        "id": f"s{self.search_invocations}",
                        "sources": [
                            {
                                "url": (
                                    f"https://source-{self.search_invocations}-"
                                    f"{index}.example/record"
                                ),
                                "title": "synthetic",
                            }
                            for index in range(1, 7)
                        ],
                    }
                ],
            }
        return batches


class V24879MappingRecoveryEffectBundleTests(unittest.TestCase):
    def fixture(self, output: Path):
        helper = V24874KeylessCoverageBundleTests()
        outcome, statuses, failures, timeouts = helper.outcome(
            output, MappingRecoveryThinSearch
        )
        return outcome, statuses, failures, timeouts

    def test_mapping_recovered_rows_are_valid(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            outcome, statuses, failures, timeouts = self.fixture(output)
            target.write_bundle(
                output_root=output,
                directory=directory,
                outcome=outcome,
                status_counts=statuses,
                transport_failures=failures,
                hard_total_wall_timeouts=timeouts,
                expected_model_slot_cap=2,
            )
            effect = json.loads(
                (directory / target.EFFECT_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(effect["parent_failed_query_rows"], 4)
            self.assertEqual(effect["unrecoverable_search_failures"], 0)
            target.validate_bundle(
                output_root=output,
                directory=directory,
                expected_model_slot_cap=2,
            )

    def test_frozen_validator_still_rejects_mapping_recovery_case(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            outcome, statuses, failures, timeouts = self.fixture(output)
            with self.assertRaises(ValueError):
                frozen.write_bundle(
                    output_root=output,
                    directory=directory,
                    outcome=outcome,
                    status_counts=statuses,
                    transport_failures=failures,
                    hard_total_wall_timeouts=timeouts,
                    expected_model_slot_cap=2,
                )

    def test_unrecoverable_cannot_exceed_failed_rows(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            helper = V24874KeylessCoverageBundleTests()
            helper.write_case(output, FullSourceThinSearch)
            directory = output / "task"
            envelope = json.loads(
                (directory / target.RESULT_NAME).read_text(encoding="utf-8")
            )
            effect = json.loads(
                (directory / target.EFFECT_NAME).read_text(encoding="utf-8")
            )
            effect["unrecoverable_search_failures"] = 1
            effect.pop("receipt_payload_sha256")
            effect["receipt_payload_sha256"] = payload_sha256(effect)
            with self.assertRaises(ValueError):
                target.validate_effect_receipt(effect, envelope=envelope)

    def test_all_other_effect_tamper_stays_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            helper = V24874KeylessCoverageBundleTests()
            helper.write_case(output, FullSourceThinSearch)
            directory = output / "task"
            envelope = json.loads(
                (directory / target.RESULT_NAME).read_text(encoding="utf-8")
            )
            base = json.loads(
                (directory / target.EFFECT_NAME).read_text(encoding="utf-8")
            )
            for field in (
                "actual_fetches",
                "provider_attempts",
                "parent_response_calls",
                "usable_pages",
            ):
                with self.subTest(field=field):
                    effect = copy.deepcopy(base)
                    effect[field] += 1
                    effect.pop("receipt_payload_sha256")
                    effect["receipt_payload_sha256"] = payload_sha256(effect)
                    with self.assertRaises(ValueError):
                        target.validate_effect_receipt(effect, envelope=envelope)

    def test_isolation_keeps_frozen_validator_identity(self) -> None:
        target.validate_isolation()
        self.assertIsNot(target.validate_effect_receipt, frozen.validate_effect_receipt)


if __name__ == "__main__":
    unittest.main()
