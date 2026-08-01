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

from scripts.audit_v24234_provider_cost_meter import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24234ProviderCostMeterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["build_only_provider_cost_meter_available"])
        self.assertFalse(value["claims"]["runtime_provider_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_parent_receipt_payload_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "4630d2056aa7508d5b6a55257dfb4f3f7c75a6dafeff4b08c5ab05644a383cf3",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "fceafc658823913bbf200bfffd8e050f59490266052260499cd1998539874260",
        )
        self.assertEqual(
            parent["v24233_control_manifest_sha256"],
            "77d73a9a02c7aa9ebc04f87c3b3f499cc4d356393420fac62229c3a4664dbaca",
        )
        self.assertEqual(parent["v24233_control_files_rehashed"], 4)
        self.assertTrue(parent["v24233_build_only_parent_validated"])

    def test_replay_covers_all_providers_and_fallback_semantics(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        self.assertEqual(replay["provider_count"], 7)
        self.assertEqual(len(replay["provider_rows"]), 7)
        self.assertEqual(
            set(replay["provider_kinds"]),
            {
                "azure_responses_model",
                "azure_responses_web_search",
                "anthropic_server_web_search",
                "tavily_search_api",
                "native_http_fetch",
                "local_orchestrator",
                "local_other_tool",
            },
        )
        for field in (
            "all_provider_contracts_and_v24233_settlements_replayed",
            "model_logical_call_and_http_attempt_mapping_replayed",
            "hosted_search_http_attempt_and_provider_action_mapping_replayed",
            "tavily_and_fetch_token_usage_not_applicable_replayed",
            "transport_failure_has_no_synthetic_response_replayed",
            "failed_local_effect_remains_chargeable_replayed",
            "missing_applicable_usage_uses_only_dimension_local_reservation_fallback",
            "observed_lower_bound_above_reservation_rejected",
        ):
            self.assertTrue(replay[field], field)
        for field in (
            "missing_applicable_usage_treated_as_zero",
            "provider_response_authenticity_independently_verified",
            "local_counter_and_clock_independently_attested",
            "schema_resealing_without_secret_cryptographically_excluded",
            "runtime_provider_wrapper_integrated",
            "real_model_search_fetch_or_orchestrator_execution_observed",
            "synthetic_benchmark_rows_or_real_evaluator_payload_read",
        ):
            self.assertFalse(replay[field], field)

    def test_scientific_scope_discloses_measurement_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "typed_provider_cost_contract_available",
            "usage_observed_unavailable_and_not_applicable_distinguished",
            "missing_applicable_usage_not_treated_as_zero",
            "missing_usage_settles_against_already_debited_reservation",
            "observed_cost_lower_bound_preserved",
            "observed_cost_above_reservation_rejected",
            "provider_response_hash_and_byte_count_schema_available",
            "transport_failure_cannot_claim_response_bytes_or_hash",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "provider_response_authenticity_independently_verified",
            "local_counter_and_clock_independently_attested",
            "schema_resealing_without_secret_cryptographically_excluded",
            "declared_reservation_is_conservative_independently_verified",
            "provider_limits_enforce_reservation_independently_verified",
            "external_effect_occurrence_or_order_independently_verified",
            "runtime_provider_wrapper_integrated",
            "real_model_search_fetch_or_orchestrator_execution_observed",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_active_forward_and_static_capability_audits_are_clean(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(guard["module_absent_from_guarded_forward_entrypoints"])
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(static["disallowed_import_count"], 0)
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertFalse(
            static[
                "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability"
            ]
        )

    def test_static_audit_rejects_expansive_capabilities_and_privilege(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('TOKEN')\n",
            "import pathlib\ndef x(): return pathlib.Path('x').read_text()\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "from deepwide_agent.runtime import DeepWideRuntime\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)

    def test_publish_is_exclusive_nofollow_and_fsyncs_file_and_parent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            target = root / "results" / "receipt.json"
            target.parent.mkdir()
            with (
                mock.patch(
                    "scripts.audit_v24234_provider_cost_meter.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24234_provider_cost_meter.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24234_provider_cost_meter.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24234_provider_cost_meter.os.fsync",
                    wraps=os.fsync,
                ) as fsync_mock,
            ):
                publish_new(target, self.value)
                self.assertGreaterEqual(fsync_mock.call_count, 2)
                first_flags = open_mock.call_args_list[0].args[1]
                self.assertTrue(first_flags & os.O_EXCL)
                self.assertTrue(first_flags & os.O_NOFOLLOW)
                with self.assertRaises(FileExistsError):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
