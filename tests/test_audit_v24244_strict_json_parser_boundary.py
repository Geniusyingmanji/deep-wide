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

from scripts.audit_v24244_strict_json_parser_boundary import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24244StrictJsonParserBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_runtime_parser_boundary"])
        self.assertTrue(value["audit_valid"])
        authorization = value["authorization"]
        self.assertTrue(authorization["pure_ephemeral_parser_capability"])
        for field, enabled in authorization.items():
            if field == "pure_ephemeral_parser_capability":
                continue
            self.assertFalse(enabled, field)
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "a15825d8343511b27e508ae011a5579dff71d3687cfff44ea602b84e66fcaffa",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "6400bc8ed8d1fb7a61beacb76d2f90e1b6973d764de2ea0e93755db23b94e062",
        )
        self.assertEqual(
            parent["v24243_control_manifest_sha256"],
            "f26af43875ed51cc6de5b1441fef78fc9f7c4091b2629996227ed3e964a31280",
        )
        self.assertEqual(parent["v24243_control_files_rehashed"], 4)
        self.assertTrue(parent["v24243_candidate_parent_validated"])

    def test_fake_replay_parses_after_settlement_and_never_repairs(self) -> None:
        replay = self.value["fake_parser_replay"]
        self.assertTrue(
            replay["local_tempdir_virtual_time_and_ephemeral_synthetic_value_only"]
        )
        self.assertFalse(replay["network_socket_model_search_fetch_or_api_called"])
        self.assertTrue(replay["durable_parent_settled_before_parse"])
        self.assertEqual(replay["parsed_top_level_member_count"], 2)
        self.assertTrue(replay["duplicate_privileged_and_nonfinite_cases_rejected"])
        self.assertTrue(replay["parse_rejection_created_no_new_journal_event"])
        self.assertFalse(replay["internal_repair_provider_effect_called"])
        self.assertFalse(replay["raw_provider_or_parsed_string_in_receipt"])
        self.assertFalse(
            replay[
                "ephemeral_text_to_parent_response_binding_independently_verified"
            ]
        )

    def test_scope_separates_strict_parser_from_unproven_integration(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "post_durable_settlement_parse_boundary_implemented",
            "exact_object_or_whole_fence_only_implemented",
            "duplicate_key_rejection_implemented",
            "nonfinite_number_rejection_implemented",
            "structural_budget_implemented",
            "nested_privileged_metadata_rejection_implemented",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "internal_repair_provider_effect_implemented",
            "search_or_page_parser_integration_implemented",
            "ephemeral_text_to_parent_response_binding_independently_verified",
            "schema_resealing_without_secret_cryptographically_excluded",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_active_forward_and_static_capability_audits_are_exact(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_guarded_clients_and_forward_entrypoints"]
        )
        self.assertTrue(
            all(
                count == 0
                for count in guard["module_name_hit_count_by_file"].values()
            )
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(static["json_load_call_site_count"], 1)
        self.assertEqual(static["scheduler_receipt_validation_call_site_count"], 1)
        self.assertEqual(static["repair_or_provider_effect_call_site_count"], 0)
        self.assertFalse(
            static[
                "direct_network_environment_file_process_subprocess_or_dynamic_code_capability"
            ]
        )

    def test_static_audit_rejects_expansive_capabilities(self) -> None:
        for source in (
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "import os\ndef x(): return os.environ.get('TOKEN')\n",
            "from deepwide_agent.runtime import DeepWideRuntime\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(callback): return callback({})\n",
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
                    "scripts.audit_v24244_strict_json_parser_boundary.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24244_strict_json_parser_boundary.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24244_strict_json_parser_boundary.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24244_strict_json_parser_boundary.os.fsync",
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
