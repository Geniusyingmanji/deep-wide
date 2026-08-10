from __future__ import annotations

import ast
import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25029_evidence_conditioned_runtime as runtime  # noqa: E402
from deepwide_agent import v25030_evidence_conditioned_exact220_contract as contract  # noqa: E402
from scripts import control_v25030_evidence_conditioned_exact220 as control  # noqa: E402
from scripts import finalize_v25030_evidence_conditioned_exact220 as finalizer  # noqa: E402
from scripts import run_v25030_evidence_conditioned_exact220 as runner  # noqa: E402


class V25030EvidenceConditionedExact220Tests(unittest.TestCase):
    def test_exact_v24857_visible_task_vector(self) -> None:
        tasks = contract.task_vector(ROOT)
        parent = contract._parent_task_contract(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(
            contract.payload_sha256([row["opaque_id"] for row in tasks]),
            parent["opaque_id_vector_sha256"],
        )
        self.assertEqual(
            contract.payload_sha256([row["question"] for row in tasks]),
            parent["visible_question_vector_sha256"],
        )
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))

    def test_production_budget_concurrency_and_transport(self) -> None:
        self.assertEqual((contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP), (220, 20, 8))
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["fetch_targets"], 10)
        self.assertEqual(contract.LIMITS["wall_seconds"], 240)
        self.assertIn("keyless", contract.SEARCH["provider"])
        self.assertNotIn("tavily", contract.SEARCH["provider"].casefold())

    def test_runtime_is_v25029_and_entropy_credit_is_disabled(self) -> None:
        self.assertEqual(runtime.POLICY_ID, "v25029_single_arm_evidence_conditioned_resolve_expand_v1")
        source = (ROOT / contract.RUNTIME).read_text(encoding="utf-8")
        self.assertIn('"entropy_or_information_gain_assigns_signed_credit": False', source)

    def test_forward_dependency_closure_covers_indirect_imports(self) -> None:
        closure = set(contract.forward_dependency_closure(ROOT))
        self.assertIn(Path("src/deepwide_agent/clients.py"), closure)
        self.assertIn(Path("src/deepwide_agent/v24984_robust_late_page_projection.py"), closure)
        self.assertIn(contract.RUNNER, closure)
        self.assertGreaterEqual(len(closure), 50)

    def test_runtime_semantic_audit_is_label_blind_and_secret_free(self) -> None:
        self.assertEqual(control._findings(tracked=False), ([], [], [], []))

    def test_protocol_discloses_transport_confound(self) -> None:
        value = contract.build_protocol(
            ROOT, now=1, tracked=False, require_clean=False, require_pristine=False
        )
        self.assertEqual(value["build_audit"], contract._build_audit_binding(ROOT))
        scope = value["treatment_scope"]
        self.assertFalse(scope["v24857_tavily_transport_reused"])
        self.assertTrue(scope["cross_rollout_difference_is_not_a_pure_query_treatment_effect"])
        self.assertFalse(value["source_policy"]["entropy_or_information_gain_assigns_signed_credit_or_routes"])

    def test_resealed_protocol_budget_tamper_fails_closed(self) -> None:
        value = contract.build_protocol(
            ROOT, now=1, tracked=False, require_clean=False, require_pristine=False
        )
        changed = copy.deepcopy(value)
        changed["execution"]["limits"]["fetch_targets"] = 11
        changed.pop("protocol_payload_sha256")
        changed["protocol_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            contract.validate_protocol(ROOT, changed, tracked=False)

    def test_runner_has_no_evaluator_import_or_child_subprocess(self) -> None:
        tree = ast.parse((ROOT / contract.RUNNER).read_text(encoding="utf-8"))
        imports = []
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        self.assertFalse(any("finalize" in item or "evaluator" in item for item in imports))
        self.assertNotIn("Popen", calls)

    def test_runner_projects_setup_failure_without_retry(self) -> None:
        task = contract.task_vector(ROOT)[0]
        original = runner.HardTotalWallResponsesClient

        class BrokenClient:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("synthetic setup failure")

        runner.HardTotalWallResponsesClient = BrokenClient
        try:
            result = runner.run_one_task(task)
        finally:
            runner.HardTotalWallResponsesClient = original
        self.assertEqual(result["opaque_id"], task["opaque_id"])
        self.assertEqual(result["completion_kind"], "best_effort_fallback")
        self.assertTrue(result["unexpected_runtime_exception_projected_without_retry"])
        self.assertEqual(result["content_free_receipt"]["physical_query_count"], 0)

    def test_finalizer_role_projection_keeps_native_files_immutable(self) -> None:
        source = (ROOT / contract.FINALIZER).read_text(encoding="utf-8")
        self.assertIn("_native_forward_barrier", source)
        self.assertNotIn("write_text", source)
        self.assertNotIn("write_bytes", source)
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertIs(finalizer.base._forward_barrier, finalizer._native_forward_barrier)

    def test_create_only_publication_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
