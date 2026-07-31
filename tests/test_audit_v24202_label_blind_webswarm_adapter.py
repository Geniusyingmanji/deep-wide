from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_v24202_label_blind_webswarm_adapter import (
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24202LabelBlindWebSwarmAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_audit_replays_modes_rejections_and_tamper_guards(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        self.assertEqual(replay["adapter_payload_replay_count"], 27)
        self.assertEqual(replay["child_envelope_replay_count"], 1)
        self.assertEqual(replay["total_synthetic_replay_count"], 28)
        self.assertEqual(replay["fallback_mode_count"], 4)
        self.assertEqual(
            replay["fallback_modes_observed"],
            ["atom", "deep", "entity_collect", "wide"],
        )
        self.assertEqual(replay["privileged_key_rejection_count"], 12)
        for field in (
            "stale_planner_context_rejected",
            "search_answer_only_provenance_rejected",
            "contradicted_provenance_rejected",
            "batch_cap_enforced",
            "root_scope_tamper_rejected",
            "inactive_child_provenance_rejected",
            "child_cap_tamper_rejected",
            "exact_contract_duplicate_removed",
            "distinct_objective_on_same_evidence_preserved",
            "deterministic_replay",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(replay["content_values_emitted"])

    def test_static_audit_rejects_io_network_and_dynamic_code(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('X')\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_receipt_seal_and_false_authorizations(self) -> None:
        unsigned = dict(self.value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(self.value["label_blind"])
        self.assertTrue(self.value["build_only"])
        self.assertTrue(self.value["audit_valid"])
        for section in ("source_policy", "authorization", "claims"):
            for key, value in self.value[section].items():
                if key.endswith("_only"):
                    continue
                if key in {
                    "synthetic_visible_input_and_content_free_provenance_only",
                }:
                    continue
                self.assertFalse(value, f"{section}.{key}")

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)


if __name__ == "__main__":
    unittest.main()
