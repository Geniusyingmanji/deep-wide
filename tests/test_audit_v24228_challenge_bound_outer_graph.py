from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24228_challenge_bound_outer_graph import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24228ChallengeBoundOuterGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_every_layer_and_discloses_claim_limits(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "complete_challenge_graph_replayed",
            "launch_challenge_present_in_every_envelope_layer",
            "exact_parent_hash_dag_replayed",
            "legacy_source_graph_replayed_through_v24224",
            "legacy_v24226_pair_revalidated",
            "historical_payload_after_wrapping_possible",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["required_layer_count"], 15)
        for field in (
            "legacy_payloads_challenge_native",
            "keyed_or_asymmetric_signature_present",
            "independent_append_only_attestation_present",
            "external_target_precomputation_excluded",
            "formal_gate2b_evaluation_authorized",
            "synthetic_benchmark_rows_or_real_evaluator_payload_read",
        ):
            self.assertFalse(replay[field], field)

    def test_static_audit_rejects_privileged_and_expansive_capabilities(self) -> None:
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
        self.assertTrue(
            value["claims"][
                "build_only_challenge_bound_compatibility_graph_available"
            ]
        )
        self.assertFalse(value["claims"]["native_challenge_consuming_executor_available"])
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
            historical["historical_gate_authorizes_formal_gate2b_after_v24228"]
        )

    def test_scientific_scope_keeps_compatibility_and_trust_claims_separate(self) -> None:
        scope = self.value["scientific_scope"]
        self.assertTrue(
            scope[
                "launch_challenge_bound_in_request_freeze_executor_evaluator_terminal_contribution_aggregate_and_pair_envelopes"
            ]
        )
        self.assertTrue(scope["exact_parent_hash_dag_validated"])
        self.assertTrue(scope["historical_payload_after_wrapping_possible"])
        self.assertTrue(scope["executor_declares_challenge_consumed_before_execution"])
        for field in (
            "legacy_payloads_challenge_native",
            "executor_challenge_consumption_independently_verified",
            "keyed_or_asymmetric_signature_present",
            "independent_append_only_or_transparency_service_used",
            "store_api_execution_independently_attested",
            "offline_self_consistent_graph_fabrication_cryptographically_excluded",
            "external_target_precomputation_excluded",
            "real_independent_outer_target_data_observed",
            "formal_gate2b_evaluated",
            "benchmark_quality_or_cost_effect_observed",
        ):
            self.assertFalse(scope[field], field)

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
                    "scripts.audit_v24228_challenge_bound_outer_graph.ROOT", root
                ),
                mock.patch(
                    "scripts.audit_v24228_challenge_bound_outer_graph.OUTPUT", output
                ),
                mock.patch(
                    "scripts.audit_v24228_challenge_bound_outer_graph.json.dump",
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
                        "scripts.audit_v24228_challenge_bound_outer_graph.ROOT", root
                    ),
                    mock.patch(
                        "scripts.audit_v24228_challenge_bound_outer_graph.OUTPUT", output
                    ),
                ):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
