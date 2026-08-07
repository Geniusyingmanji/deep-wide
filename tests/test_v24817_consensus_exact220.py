from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24817_consensus_exact220_contract as contract  # noqa: E402
from scripts import control_v24817_consensus_exact220 as control  # noqa: E402


class V24817ConsensusExact220Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Replaying the three complete protocol/manifest chains is intentional
        # but expensive.  Do it once per isolated test process, then reuse only
        # the already validated in-memory bundle.
        cls.bundle = contract.source_bundle(ROOT)

    def test_three_frozen_sources_are_exact_and_task_aligned(self):
        bundle = self.bundle
        self.assertEqual(len(bundle["task_vector"]), 220)
        self.assertEqual(len(bundle["sources"]), 3)
        self.assertTrue(all(len(source["rows"]) == 220 for source in bundle["sources"]))

    def test_source_bundle_excludes_evaluator_results_and_scores(self):
        bundle = self.bundle
        for source in bundle["sources"]:
            self.assertNotIn("result", source)
            self.assertNotIn("score", source)
            self.assertNotIn("evaluator", source)
            self.assertEqual(
                set(source) - {"rows"},
                {"name", "protocol_sha256", "forward_result_sha256", "prediction_freeze_sha256", "runtime_predictions_sha256"},
            )

    def test_task_boundary_is_visible_only(self):
        tasks = self.bundle["task_vector"]
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_generator_ast_has_no_privileged_signal_access(self):
        fields, imports, secrets = control._ast_findings()
        self.assertEqual(fields, [])
        self.assertEqual(imports, [])
        self.assertEqual(secrets, [])

    def test_future_surface_is_fresh_before_generation(self):
        self.assertTrue(control._future_pristine())


if __name__ == "__main__": unittest.main()
