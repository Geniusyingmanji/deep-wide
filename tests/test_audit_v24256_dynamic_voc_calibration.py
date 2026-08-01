from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24256_dynamic_voc_calibration import (  # noqa: E402
    ROOT,
    audit_python_source,
    audit_v24123_schema,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24256DynamicVocCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_parent_receipts_and_v24123_schema_gap_are_exact(self) -> None:
        parents = self.value["parents"]
        self.assertEqual(
            parents["v24255"]["file_sha256"],
            "f285ba537f0631e69ef8ef6a227b445f106e9fbc1f94f8ca464104176809f447",
        )
        self.assertTrue(parents["v24255"]["build_only_parent_validated"])
        self.assertEqual(
            parents["v24123"]["protocol_sha256"],
            "f78e54b7dd1d8510a4b1afcf1e6d3a9c5c36dc81d8dbda05d39010940b8845ca",
        )
        self.assertFalse(
            parents["v24123"]["real_true_continuation_result_available"]
        )
        gap = parents["v24123_schema_gap"]
        self.assertTrue(
            gap[
                "v24123_aggregate_has_terminal_contribution_and_provenance_hashes"
            ]
        )
        self.assertTrue(
            gap[
                "v24123_training_row_has_pre_action_features_and_myopic_contribution"
            ]
        )
        self.assertTrue(
            gap["v24123_can_supply_myopic_target_without_new_data"]
        )
        self.assertFalse(
            gap["v24123_aggregate_has_successor_state_projection"]
        )
        self.assertFalse(
            gap[
                "v24123_training_row_has_successor_state_or_transition_probability"
            ]
        )
        self.assertFalse(
            gap[
                "v24123_can_supply_dynamic_transition_calibration_without_new_data"
            ]
        )

    def test_synthetic_replay_covers_pass_fail_and_policy_divergence(
        self,
    ) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "content_free_split_calibration_replayed",
            "fit_and_calibration_task_clusters_disjoint",
            "task_cluster_equal_transition_fit_replayed",
            "dirichlet_smoothed_transition_fit_replayed",
            "heldout_normalized_multiclass_brier_gate_replayed",
            "task_cluster_equal_stop_loss_fit_replayed",
            "heldout_stop_loss_mae_gate_replayed",
            "calibration_complete_emits_v24255_ready_model",
            "calibration_incomplete_emits_v24255_all_abstain_model",
            "pure_ig_myopic_and_dynamic_policy_divergence_replayed",
            "nested_privileged_runtime_metadata_rejected",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(
            replay[
                "real_task_state_transition_evaluator_payload_or_api_read"
            ]
        )

    def test_receipt_is_sealed_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"][
                "build_only_dynamic_voc_calibration_primitive_available"
            ]
        )
        self.assertFalse(value["claims"]["real_calibration_dataset_available"])
        self.assertFalse(
            value["claims"]["real_calibrated_dynamic_voc_model_available"]
        )
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_upstream_science_outputs_are_recorded_absent(self) -> None:
        presence = self.value["upstream_science_output_presence_at_audit"]
        self.assertEqual(len(presence), 3)
        self.assertTrue(all(exists is False for exists in presence.values()))

    def test_static_audit_rejects_capability_and_privileged_reads(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('TOKEN')\n",
            "import pathlib\ndef x(): return pathlib.Path('x').read_text()\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(v): return getattr(v, 'secret')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
            "def x(v): return v['raw_observation']\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(
                    RuntimeError, "capability boundary"
                ):
                    audit_python_source(source)

    def test_v24123_schema_audit_rejects_successor_claim(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24123_release.py"
        ).read_text(encoding="utf-8")
        modified = canonical.replace(
            '"task_contribution": float(',
            '"next_state_ref_sha256": "x",\n                "task_contribution": float(',
            1,
        )
        self.assertNotEqual(modified, canonical)
        with self.assertRaisesRegex(RuntimeError, "schema audit"):
            audit_v24123_schema(modified)

    def test_active_forward_guard_has_no_v24256_import(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_guarded_forward_entrypoints"]
        )
        self.assertEqual(guard["file_count"], 8)
        self.assertTrue(
            all(
                count == 0
                for count in guard["module_name_hit_count_by_file"].values()
            )
        )

    def test_control_sources_have_no_credentials_or_concrete_opaque_ids(
        self,
    ) -> None:
        scan = self.value["control_source_forbidden_literal_scan"]
        self.assertEqual(scan["file_count"], 4)
        self.assertEqual(scan["hit_count"], 0)
        self.assertFalse(
            scan["credential_or_concrete_opaque_id_literal_present"]
        )

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)

    def test_publish_is_create_exclusive_nofollow_and_fsyncs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            target = root / "results" / "receipt.json"
            target.parent.mkdir()
            with (
                mock.patch(
                    "scripts.audit_v24256_dynamic_voc_calibration.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24256_dynamic_voc_calibration.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24256_dynamic_voc_calibration.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24256_dynamic_voc_calibration.os.fsync",
                    wraps=os.fsync,
                ) as fsync_mock,
            ):
                publish_new(target, self.value)
                self.assertGreaterEqual(fsync_mock.call_count, 2)
                flags = open_mock.call_args_list[0].args[1]
                self.assertTrue(flags & os.O_EXCL)
                self.assertTrue(flags & os.O_NOFOLLOW)
                with self.assertRaises(FileExistsError):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
