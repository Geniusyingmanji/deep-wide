from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24227_credit_commit_reveal import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24227CreditCommitRevealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_order_binding_residue_and_claim_limits(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "prediction_committed_before_outer_root_exists",
            "launch_receipt_and_reservation_replayed",
            "valid_complete_sequence_replayed",
            "exact_parent_hash_bindings_replayed",
            "pair_before_launch_rejected",
            "reveal_before_pair_rejected",
            "resealed_wrong_campaign_pair_rejected",
            "uncommitted_outer_residue_rejected",
            "create_exclusive_stage_publication_replayed",
            "post_prediction_synthetic_outer_target_contribution_validated",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(
            replay["outer_target_used_for_runtime_routing_or_same_forward_pass"]
        )
        self.assertFalse(replay["physical_time_or_external_precomputation_claimed"])
        self.assertFalse(replay["native_launch_challenge_bound_inside_v24226_pair"])
        self.assertFalse(replay["synthetic_benchmark_rows_or_real_evaluator_payload_read"])

    def test_static_audit_allows_narrow_store_but_rejects_extra_capabilities(self) -> None:
        for source in (
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "import os\ndef x(): return os.getenv('TOKEN')\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "from pathlib import Path\ndef x(): return Path('x').read_text()\n",
            "def x(v): return getattr(v, 'secret')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_audit_is_build_only_sealed_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["build_only_commit_reveal_store_available"])
        self.assertFalse(value["claims"]["formal_gate2b_evaluator_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_active_forward_and_historical_gate_are_untouched(self) -> None:
        active = self.value["active_forward_guard"]
        historical = self.value["historical_gate_guard"]
        self.assertTrue(active["module_absent_from_guarded_forward_entrypoints"])
        self.assertTrue(all(count == 0 for count in active["module_name_hit_count_by_file"].values()))
        self.assertTrue(all(count == 0 for count in historical["module_name_hit_count_by_file"].values()))
        self.assertTrue(historical["historical_synthetic_gate_preserved_for_regression_only"])
        self.assertFalse(historical["historical_gate_authorizes_formal_gate2b_after_v24227"])

    def test_scientific_scope_discloses_unproven_boundaries(self) -> None:
        scope = self.value["scientific_scope"]
        self.assertTrue(scope["repository_local_commit_launch_reserve_pair_reveal_order_enforced"])
        self.assertTrue(scope["post_prediction_outer_target_available_only_to_reveal_validation"])
        self.assertFalse(scope["trusted_physical_clock_used"])
        self.assertFalse(scope["external_target_precomputation_excluded"])
        self.assertFalse(scope["hostile_concurrent_filesystem_mutation_excluded"])
        self.assertFalse(scope["independent_append_only_or_transparency_service_used"])
        self.assertFalse(scope["store_api_execution_independently_attested"])
        self.assertFalse(
            scope[
                "offline_self_consistent_chain_fabrication_cryptographically_excluded"
            ]
        )
        self.assertTrue(scope["local_file_and_directory_fsync_implemented"])
        self.assertFalse(scope["pair_native_launch_challenge_binding_present"])
        self.assertFalse(scope["real_independent_outer_target_data_observed"])
        self.assertFalse(scope["formal_gate2b_evaluated"])

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)

    def test_failed_canonical_publish_leaves_poison_and_blocks_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            output = Path("results/receipt.json")
            target = root / output

            def fail_after_partial(
                value: object, handle: object, **kwargs: object
            ) -> None:
                handle.write("{")  # type: ignore[attr-defined]
                raise OSError("synthetic audit write failure")

            with (
                mock.patch(
                    "scripts.audit_v24227_credit_commit_reveal.ROOT", root
                ),
                mock.patch(
                    "scripts.audit_v24227_credit_commit_reveal.OUTPUT", output
                ),
                mock.patch(
                    "scripts.audit_v24227_credit_commit_reveal.json.dump",
                    side_effect=fail_after_partial,
                ),
            ):
                with self.assertRaisesRegex(
                    OSError, "synthetic audit write failure"
                ):
                    publish_new(target, self.value)
            self.assertTrue(target.exists())
            with self.assertRaises(FileExistsError):
                with (
                    mock.patch(
                        "scripts.audit_v24227_credit_commit_reveal.ROOT", root
                    ),
                    mock.patch(
                        "scripts.audit_v24227_credit_commit_reveal.OUTPUT", output
                    ),
                ):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
