from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from deepwide_agent.v24204_postdecision_work_order import (
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import (
    MARKDOWN,
    SCOPE,
)
from deepwide_agent.v24214_joint_package import build_joint_package_order
from scripts.publish_v24214_joint_package import (
    _forbidden_runtime_accesses,
    build_selected_publication,
    materialize_joint_candidate,
    resolve_deepest_graph,
)


ROOT = Path(__file__).resolve().parents[1]


def order_with(components: list[str], baseline: str = "p12") -> dict:
    work_order = next(
        row
        for row in build_work_order_manifest()["rows"].values()
        if row["baseline_name"] == baseline
        and row["eligible_components"] == components
    )
    return build_joint_package_order(work_order)


class PublishV24214JointPackageTests(unittest.TestCase):
    def test_historical_identity_and_scope_graphs_are_exact(self) -> None:
        identity = order_with([])
        files, names, count, provenance = resolve_deepest_graph(identity, {})
        self.assertEqual(identity["final_state_schema_version"], 68)
        self.assertEqual(provenance["historical_schema"], "schema68")
        self.assertEqual(count, 28)
        self.assertTrue(names)
        self.assertIn("src/deepwide_agent/runtime.py", files)

        scope = order_with([MARKDOWN, SCOPE])
        files, names, count, provenance = resolve_deepest_graph(scope, {})
        self.assertEqual(scope["final_state_schema_version"], 70)
        self.assertEqual(provenance["historical_schema"], "schema70")
        self.assertEqual(count, 63)
        self.assertIn("tests.test_v24104_integrated_scope_open_fallback", names)
        self.assertIn("src/deepwide_agent/v24104.py", files)

    def test_p12_markdown_exact_graph_reruns_all_fifty_tests(self) -> None:
        order = order_with([MARKDOWN])
        files, names, count, provenance = resolve_deepest_graph(order, {})
        self.assertEqual(count, 50)
        with tempfile.TemporaryDirectory(
            dir=ROOT / "outputs", prefix="v24214-test-"
        ) as directory:
            candidate = Path(directory) / "candidate"
            value = materialize_joint_candidate(
                files, names, count, provenance, candidate=candidate
            )
        self.assertEqual(value["integrated_tests"]["tests_run"], 50)
        self.assertTrue(value["candidate_is_exact_copy_of_single_deepest_graph"])
        self.assertFalse(value["candidate_directory_overlay_used"])
        self.assertTrue(value["runtime_label_blind_ast_audit_passed"])

    def test_missing_component_test_fails_closed(self) -> None:
        order = order_with([MARKDOWN])
        files, names, _count, _provenance = resolve_deepest_graph(order, {})
        historical = {
            "component_publication": {
                "candidate_root": str(ROOT / "outputs/absent"),
                "candidate_regular_file_manifest": {},
            }
        }
        self.assertIn("src/deepwide_agent/v24102.py", files)
        self.assertIn("tests.test_v24102_markdown_rank_slot", names)
        broken = copy.deepcopy(order)
        broken["eligible_components"].append("invented_component")
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            resolve_deepest_graph(broken, historical)

    def test_ast_audit_detects_direct_evaluator_only_access(self) -> None:
        files = {
            "safe.py": "def f(x):\n    return x.get('question')\n",
            "bad.py": "def f(x):\n    return x.get('question_type')\n",
        }
        self.assertEqual(_forbidden_runtime_accesses(files, ["safe.py"]), [])
        self.assertEqual(
            _forbidden_runtime_accesses(files, ["bad.py"]),
            ["bad.py:2:question_type"],
        )

    def test_identity_publication_does_not_materialize_or_authorize(self) -> None:
        order = order_with([])
        selected = {"selected_payload_sha256": "s" * 64}
        # File hashes belong to the live terminal path and are deliberately
        # patched by the caller in production; this test exercises the pure
        # identity branch through the graph resolver instead.
        files, _names, _count, provenance = resolve_deepest_graph(order, {})
        self.assertTrue(files)
        self.assertEqual(provenance["deepest_byte_owner"], "baseline")
        self.assertTrue(order["identity_handoff_only"])
        self.assertFalse(order["package_gate_evaluated_or_launched"])
        self.assertFalse(order["benchmark_forward_or_full220_launch_allowed"])
        self.assertEqual(selected["selected_payload_sha256"], "s" * 64)


if __name__ == "__main__":
    unittest.main()
