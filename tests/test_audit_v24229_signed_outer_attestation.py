from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24229_signed_outer_attestation import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24229SignedOuterAttestationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_cross_verifies_and_rejects_tampering(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "openssl_generated_test_signature_verified_by_pure_module",
            "canonical_domain_separated_statement_replayed",
            "public_key_matches_frozen_protocol",
            "tampered_signature_rejected",
            "wrong_public_key_rejected",
            "signature_proves_only_private_key_possession",
        ):
            self.assertTrue(replay[field], field)
        for field in (
            "private_key_passed_to_production_module",
            "private_key_or_signature_material_persisted_in_audit",
            "independent_signer_identity_verified",
            "independent_trust_domain_verified",
            "append_only_transparency_service_used",
            "trusted_timestamp_verified",
            "statement_truth_independently_verified",
            "launch_before_execution_independently_attested",
            "external_target_precomputation_excluded",
            "formal_gate2b_evaluation_authorized",
            "synthetic_benchmark_rows_or_real_evaluator_payload_read",
        ):
            self.assertFalse(replay[field], field)

    def test_static_audit_rejects_private_key_and_expansive_capabilities(self) -> None:
        for source in (
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "import os\ndef x(): return os.getenv('TOKEN')\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "from pathlib import Path\ndef x(): return Path('x').read_bytes()\n",
            "def x(v): return getattr(v, 'secret')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
            "def x(private_key: bytes): return private_key\n",
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
        self.assertTrue(value["claims"]["build_only_public_signature_verifier_available"])
        self.assertFalse(value["claims"]["independent_trust_domain_established"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_active_forward_and_historical_gate_are_untouched(self) -> None:
        active = self.value["active_forward_guard"]
        historical = self.value["historical_gate_guard"]
        self.assertTrue(active["module_absent_from_guarded_forward_entrypoints"])
        self.assertTrue(
            all(count == 0 for count in active["module_name_hit_count_by_file"].values())
        )
        self.assertTrue(
            all(count == 0 for count in historical["module_name_hit_count_by_file"].values())
        )
        self.assertFalse(
            historical["historical_gate_authorizes_formal_gate2b_after_v24229"]
        )

    def test_scientific_scope_keeps_signature_and_truth_claims_separate(self) -> None:
        scope = self.value["scientific_scope"]
        self.assertTrue(scope["rsa_pss_sha256_detached_signature_verified"])
        self.assertTrue(
            scope["canonical_statement_binds_complete_v24228_compatibility_graph"]
        )
        self.assertTrue(scope["public_key_frozen_before_verification"])
        self.assertTrue(
            scope["signature_proves_only_possession_of_corresponding_private_key"]
        )
        self.assertTrue(scope["historical_payload_after_wrapping_possible"])
        for field in (
            "private_key_accepted_read_hashed_or_persisted_by_production_module",
            "independent_signer_identity_verified",
            "independent_trust_domain_verified",
            "append_only_transparency_service_used",
            "trusted_timestamp_verified",
            "statement_truth_independently_verified",
            "launch_before_execution_independently_attested",
            "external_target_precomputation_excluded",
            "real_independent_outer_target_data_observed",
            "formal_gate2b_evaluated",
            "benchmark_quality_or_cost_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_test_private_key_policy_is_explicit(self) -> None:
        policy = self.value["test_key_policy"]
        self.assertTrue(policy["openssl_subprocess_used_by_test_fixture_only"])
        self.assertTrue(policy["temporary_key_directory_limited_to_repository"])
        self.assertTrue(policy["temporary_private_keys_deleted_after_replay"])
        self.assertFalse(policy["private_key_bytes_read_hashed_logged_or_emitted"])
        self.assertFalse(policy["private_key_or_signature_bytes_in_audit_artifact"])

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
                    "scripts.audit_v24229_signed_outer_attestation.ROOT", root
                ),
                mock.patch(
                    "scripts.audit_v24229_signed_outer_attestation.OUTPUT", output
                ),
                mock.patch(
                    "scripts.audit_v24229_signed_outer_attestation.json.dump",
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
                        "scripts.audit_v24229_signed_outer_attestation.ROOT", root
                    ),
                    mock.patch(
                        "scripts.audit_v24229_signed_outer_attestation.OUTPUT", output
                    ),
                ):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
