from __future__ import annotations

import concurrent.futures
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24567_strict_reachability_conversion_external_gate as runtime  # noqa: E402
from scripts import v24585_nested_collector_projection_repair as target  # noqa: E402
from test_v24583_prededup_preservation_external_gate import positive_capability  # noqa: E402


class V24585NestedCollectorProjectionRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.capability = positive_capability(Path(cls.temporary.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_binding_captures_unbound_v24580_projector(self) -> None:
        self.assertTrue(target.binding_valid())
        self.assertIs(target.FROZEN_TASK_PROJECTION, target.total.task_projection)
        self.assertIsNone(getattr(target.FROZEN_TASK_PROJECTION, "__self__", None))

    def test_nested_runtime_global_rebinding_cannot_change_collector_target(self) -> None:
        before = runtime._ORIGINAL_TASK_PROJECTION
        with target.capability_collection() as collector:
            bound = target.total.task_projection
            self.assertIs(getattr(bound, "__self__", None), collector)
            runtime._ORIGINAL_TASK_PROJECTION = bound
            try:
                row = target.total.task_projection(1, self.capability)
            finally:
                runtime._ORIGINAL_TASK_PROJECTION = before
        self.assertEqual(row["status"], "validated_capability")
        self.assertGreater(row["prededup_preservation_preserved_candidate_count"], 0)

    def test_real_eight_way_collector_projects_and_aggregates_without_recursion(self) -> None:
        barrier = threading.Barrier(8)

        def project(ordinal: int) -> dict:
            barrier.wait(timeout=10)
            return target.total.task_projection(ordinal, self.capability)

        with target.capability_collection():
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                rows = list(pool.map(project, range(1, 9)))
            aggregate = target.aggregate_projections(rows, selected=8)
        self.assertEqual(aggregate["selected"], 8)
        self.assertEqual(aggregate["success_tasks"], 8)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 0)
        self.assertEqual(aggregate["prededup_preservation_activity_tasks"], 8)
        self.assertEqual(aggregate["prededup_preserved_candidate_tasks"], 8)
        self.assertEqual(
            aggregate["prededup_and_title_replacement_cooccurrence_tasks"], 8
        )

    def test_public_failure_row_and_capability_mix_is_total(self) -> None:
        with target.capability_collection():
            first = target.total.task_projection(1, self.capability)
            failure = target.total.failure_projection(2)
            aggregate = target.aggregate_projections(
                [first, failure], selected=2
            )
        self.assertEqual(aggregate["success_tasks"], 1)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 1)
        self.assertTrue(
            aggregate[
                "all_prededup_preservation_failure_rows_are_content_free_zero_projections"
            ]
        )

    def test_duplicate_aggregate_and_nested_collector_fail_closed(self) -> None:
        with target.capability_collection():
            row = target.total.task_projection(1, self.capability)
            target.aggregate_projections([row], selected=1)
            with self.assertRaisesRegex(RuntimeError, "already consumed"):
                target.aggregate_projections([row], selected=1)
            with self.assertRaisesRegex(RuntimeError, "already active"):
                target.capability_collection().__enter__()

    def test_dynamic_projector_drift_fails_before_collection(self) -> None:
        with patch.object(target.total, "task_projection", lambda *_args, **_kwargs: {}):
            with self.assertRaisesRegex(RuntimeError, "binding surface drifted"):
                with target.capability_collection():
                    pass

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/v24585_nested_collector_projection_repair.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
