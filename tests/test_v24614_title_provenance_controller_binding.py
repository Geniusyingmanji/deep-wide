from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24614_title_provenance_controller_binding as target  # noqa: E402
from scripts import v24604_content_free_title_funnel_external_gate as controller  # noqa: E402
from test_v24607_proof_carrying_title_provenance import populate, validate  # noqa: E402


class V24614TitleProvenanceControllerBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        populate(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_import_time_runtime_binding_is_exact(self) -> None:
        self.assertTrue(target.invariant_valid())
        self.assertIs(target.runtime_proof.parent_proof, target.protocol_proof)
        self.assertIs(
            target.runtime_bounded.run_timed_subprocess.__globals__["proof"],
            target.runtime_proof,
        )
        self.assertIs(
            target.runtime_bounded.run_timed_subprocess.__globals__["total"],
            target.runtime_total,
        )

    def test_protocol_view_rebinds_controller_only(self) -> None:
        before = (controller.proof, controller.total, controller.bounded)
        with target.controller_bindings(controller, protocol_compatibility=True):
            self.assertIs(controller.proof, target.protocol_proof)
            self.assertIs(controller.total, target.protocol_total)
            self.assertIs(controller.bounded, target.protocol_bounded)
            self.assertTrue(target.invariant_valid())
        self.assertEqual((controller.proof, controller.total, controller.bounded), before)
        self.assertTrue(target.invariant_valid())

    def test_runtime_view_rebinds_controller_only(self) -> None:
        before = (controller.proof, controller.total, controller.bounded)
        with target.controller_bindings(controller, protocol_compatibility=False):
            self.assertIs(controller.proof, target.runtime_proof)
            self.assertIs(controller.total, target.runtime_total)
            self.assertIs(controller.bounded, target.runtime_bounded)
            self.assertTrue(target.invariant_valid())
        self.assertEqual((controller.proof, controller.total, controller.bounded), before)

    def test_protocol_view_cannot_change_real_parent_validator(self) -> None:
        parent = target.runtime_proof.parent_proof
        validator = target.runtime_proof.validate_proof_carrying_title_provenance_bundle
        with target.controller_bindings(controller, protocol_compatibility=True):
            capability = validate(self.root)
            self.assertIsInstance(
                capability,
                target.runtime_proof.ValidatedProofCarryingContentFreeTitleProvenance,
            )
            self.assertIs(target.runtime_proof.parent_proof, parent)
            self.assertIs(
                target.runtime_proof.validate_proof_carrying_title_provenance_bundle,
                validator,
            )

    def test_nested_views_restore_lifo_without_cross_contamination(self) -> None:
        dummy = SimpleNamespace(
            proof="original-proof",
            total="original-total",
            bounded="original-bounded",
            collector_repair="original-collector",
        )
        with target.controller_bindings(dummy, protocol_compatibility=True):
            self.assertIs(dummy.proof, target.protocol_proof)
            with target.controller_bindings(dummy, protocol_compatibility=False):
                self.assertIs(dummy.proof, target.runtime_proof)
                self.assertTrue(target.invariant_valid())
            self.assertIs(dummy.proof, target.protocol_proof)
        self.assertEqual(dummy.proof, "original-proof")
        self.assertEqual(dummy.total, "original-total")
        self.assertEqual(dummy.bounded, "original-bounded")
        self.assertEqual(dummy.collector_repair, "original-collector")

    def test_binding_vectors_are_complete_and_distinct(self) -> None:
        protocol = target.binding_vector(protocol_compatibility=True)
        runtime = target.binding_vector(protocol_compatibility=False)
        self.assertEqual(set(protocol), {"proof", "total", "bounded", "collector_repair"})
        self.assertEqual(set(runtime), set(protocol))
        self.assertTrue(all(protocol[name] is not runtime[name] for name in protocol))

    def test_runtime_source_is_label_blind_and_secret_free(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        path = Path("src/deepwide_agent/v24614_title_provenance_controller_binding.py")
        accesses, imports = audit.ast_findings(path)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertIsNone(audit.SECRET.search((ROOT / path).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
