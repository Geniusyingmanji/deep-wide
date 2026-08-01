from __future__ import annotations

import copy
import hashlib
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24252_candidate_runner_package import (  # noqa: E402
    build_candidate_runner_package_contract,
)
from deepwide_agent.v24253_candidate_runtime_integration import (  # noqa: E402
    CandidateDev64Identity,
    build_candidate_runtime_integration_contract,
)
from deepwide_agent.v24254_candidate_dev64_launcher import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARM_EXECUTION_IMPLEMENTED,
    ARM_ORDER,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREATE_EXCLUSIVE_PAIR_PREPARATION_IMPLEMENTED,
    DEV64_LAUNCH_AUTHORIZED,
    EVALUATOR_EXECUTION_IMPLEMENTED,
    EXACT220_LAUNCH_AUTHORIZED,
    EXACT_VISIBLE_DEV64_INPUT_SNAPSHOT_IMPLEMENTED,
    FAILURE_AS_ZERO_AGGREGATE_IMPLEMENTED,
    FAILURE_AS_ZERO_CONTRACT_FROZEN,
    LAUNCH_ACTIVATION_IMPLEMENTED,
    LEASE_ACQUISITION_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    MAPPING_OR_EVALUATOR_OPEN_AUTHORIZED,
    NO_RESUME_OR_SELECTIVE_RERUN_CONTRACT_FROZEN,
    PRODUCTION_LAUNCHER_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SINGLE_CONTIGUOUS_SHARED_LEASE_CONTRACT_FROZEN,
    TWO_ARM_TERMINAL_BEFORE_EVALUATOR_CONTRACT_FROZEN,
    TWO_DISJOINT_PRISTINE_ARM_ROOTS_IMPLEMENTED,
    CandidateDev64LauncherPackage,
    CandidateDev64LauncherPoisoned,
    build_candidate_dev64_launcher_contract,
    snapshot_visible_dev64_inputs,
    validate_candidate_dev64_launcher_contract,
    validate_visible_dev64_input_snapshot,
)
from tests import test_v24253_candidate_runtime_integration as parent_fixture  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V24254CandidateDev64LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = parent_fixture.V24253CandidateRuntimeIntegrationTests(
            methodName="runTest"
        )
        self.parent.setUp()
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.base = Path(self.temporary.name).resolve()
        self.manifest = self.base / "visible_dev64.jsonl"
        self.ids = self.base / "visible_dev64.ids"
        rows = [
            {
                "opaque_id": f"task_{index:024x}",
                "question": f"Visible synthetic question {index}",
            }
            for index in range(64)
        ]
        self.manifest.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                for row in rows
            ),
            encoding="utf-8",
        )
        self.ids.write_text(
            "".join(row["opaque_id"] + "\n" for row in rows),
            encoding="utf-8",
        )
        frozen = self.parent.frozen()
        package_contract = build_candidate_runner_package_contract(
            source_root=ROOT / "src",
            frozen=frozen,
            journal_namespace_sha256=hashlib.sha256(
                b"v24254-journal"
            ).hexdigest(),
        )
        identity = CandidateDev64Identity(
            selected_count=64,
            opaque_id_file_sha256=sha256(self.ids),
            runtime_manifest_sha256=sha256(self.manifest),
        )
        self.integration = build_candidate_runtime_integration_contract(
            repository_root=ROOT,
            package_contract=package_contract,
            runtime_config=self.parent.runtime_config(),
            launch_limits=self.parent.limits(),
            dev64_identity=identity,
        )
        self.contract = build_candidate_dev64_launcher_contract(
            repository_root=ROOT,
            runtime_integration_contract=self.integration,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()
        self.parent.tearDown()

    def launcher_root(self) -> Path:
        return Path(tempfile.mkdtemp(dir=self.base)).resolve()

    def initialize(self) -> CandidateDev64LauncherPackage:
        return CandidateDev64LauncherPackage.initialize(
            root=self.launcher_root(),
            repository_root=ROOT,
            contract=self.contract,
            runtime_manifest_path=self.manifest,
            opaque_id_file_path=self.ids,
        )

    def test_scope_and_authorization_constants_are_exact(self) -> None:
        for value in (
            PRODUCTION_LAUNCHER_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            DEV64_LAUNCH_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            MAPPING_OR_EVALUATOR_OPEN_AUTHORIZED,
            EXACT220_LAUNCH_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            LAUNCH_ACTIVATION_IMPLEMENTED,
            LEASE_ACQUISITION_IMPLEMENTED,
            ARM_EXECUTION_IMPLEMENTED,
            EVALUATOR_EXECUTION_IMPLEMENTED,
            FAILURE_AS_ZERO_AGGREGATE_IMPLEMENTED,
        ):
            self.assertFalse(value)
        for value in (
            CREATE_EXCLUSIVE_PAIR_PREPARATION_IMPLEMENTED,
            EXACT_VISIBLE_DEV64_INPUT_SNAPSHOT_IMPLEMENTED,
            TWO_DISJOINT_PRISTINE_ARM_ROOTS_IMPLEMENTED,
            SINGLE_CONTIGUOUS_SHARED_LEASE_CONTRACT_FROZEN,
            TWO_ARM_TERMINAL_BEFORE_EVALUATOR_CONTRACT_FROZEN,
            FAILURE_AS_ZERO_CONTRACT_FROZEN,
            NO_RESUME_OR_SELECTIVE_RERUN_CONTRACT_FROZEN,
        ):
            self.assertTrue(value)

    def test_contract_binds_parent_runtime_source_inputs_arms_and_barriers(self) -> None:
        validate_candidate_dev64_launcher_contract(self.contract)
        self.assertEqual(
            self.contract["runtime_integration_contract_sha256"],
            self.integration["integration_contract_sha256"],
        )
        self.assertEqual(self.contract["arm_order"], list(ARM_ORDER))
        control = self.contract["arm_execution_contracts"]["legacy_control"]
        candidate = self.contract["arm_execution_contracts"]["candidate_runtime"]
        self.assertEqual(
            control["package_contract_sha256"],
            candidate["package_contract_sha256"],
        )
        self.assertFalse(
            control["v24253_checkpoint_and_page_postcondition_wrapper_enabled"]
        )
        self.assertTrue(
            candidate["v24253_checkpoint_and_page_postcondition_wrapper_enabled"]
        )
        lease = self.contract["shared_lease_contract"]
        self.assertTrue(
            lease["one_contiguous_lease_spans_both_forwards_and_evaluators"]
        )
        self.assertFalse(lease["lease_acquire_authorized"])
        barrier = self.contract["terminal_and_evaluator_barrier_contract"]
        self.assertEqual(barrier["both_arms_exact_terminal_count_required"], 64)
        self.assertTrue(barrier["failure_as_zero"])
        self.assertFalse(
            barrier["mapping_path_open_hash_or_read_before_barrier_allowed"]
        )
        decision = self.contract["engineering_gate_decision_contract"]
        self.assertTrue(decision["thresholds_frozen_before_pair_materialization"])
        self.assertEqual(decision["each_quality_component_min_delta"], -0.005)
        self.assertEqual(decision["system_total_token_ratio_max"], 1.05)
        self.assertTrue(decision["go_authorizes_only_future_activation_design"])
        self.assertFalse(decision["go_authorizes_exact220_launch"])
        priority = self.contract["upstream_priority_contract"]
        self.assertTrue(priority["existing_v24216_to_v24220_chain_has_priority"])
        self.assertEqual(len(priority["v24216_frozen_receipts"]), 3)
        self.assertFalse(priority["activation_receipt_materialized"])

    def test_visible_input_snapshot_returns_only_hashes_and_schema(self) -> None:
        value = snapshot_visible_dev64_inputs(
            runtime_manifest_path=self.manifest,
            opaque_id_file_path=self.ids,
            expected_identity=self.contract["dev64_identity"],
        )
        validate_visible_dev64_input_snapshot(value)
        encoded = json.dumps(value, sort_keys=True)
        self.assertNotIn("Visible synthetic question", encoded)
        self.assertNotRegex(encoded, r"task_[0-9a-f]{24}")
        self.assertEqual(value["selected_count"], 64)
        self.assertTrue(value["manifest_and_id_order_identical"])
        self.assertFalse(value["questions_persisted_or_emitted"])

    def test_initialize_prepares_exact_disjoint_pristine_roots_without_effect(self) -> None:
        package = self.initialize()
        status = package.preflight()
        self.assertEqual(status["prepared_pristine_package_root_count"], 2)
        self.assertEqual(status["prepared_pristine_output_root_count"], 2)
        self.assertFalse(status["shared_api_lease_acquired"])
        self.assertFalse(status["provider_model_search_fetch_or_evaluator_called"])
        roots: list[Path] = []
        for arm in ARM_ORDER:
            arm_roots = package.arm_roots(arm)
            self.assertEqual(list(arm_roots["package"].iterdir()), [])
            self.assertEqual(list(arm_roots["output"].iterdir()), [])
            roots.extend((arm_roots["package"], arm_roots["output"]))
        self.assertEqual(len({path.resolve() for path in roots}), 4)
        persisted = "".join(
            path.read_text(encoding="utf-8")
            for path in (
                package.initial_path,
                package.lease_intent_path,
                package.ready_path,
            )
        )
        self.assertNotIn("Visible synthetic question", persisted)
        self.assertNotRegex(persisted, r"task_[0-9a-f]{24}")

    def test_open_revalidates_exact_same_prepared_package(self) -> None:
        package = self.initialize()
        reopened = CandidateDev64LauncherPackage.open(
            root=package.root,
            repository_root=ROOT,
            contract=self.contract,
            runtime_manifest_path=self.manifest,
            opaque_id_file_path=self.ids,
        )
        self.assertEqual(reopened.preflight(), package.preflight())

    def test_public_surface_has_no_launch_lease_evaluator_or_resume_method(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(
                CandidateDev64LauncherPackage, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        }
        self.assertEqual(methods, {"arm_roots", "preflight"})
        source = inspect.getsource(CandidateDev64LauncherPackage)
        for forbidden in (
            "subprocess",
            "acquire_deepwide_api_lease",
            "run_task",
            "evaluate_package_gate",
            "evaluator_mapping",
        ):
            self.assertNotIn(forbidden, source)

    def test_manifest_rejects_extra_privileged_field_and_order_mismatch(self) -> None:
        original = self.manifest.read_text(encoding="utf-8")
        rows = [json.loads(line) for line in original.splitlines()]
        rows[0]["question_type"] = "forbidden"
        self.manifest.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "schema"):
            snapshot_visible_dev64_inputs(
                runtime_manifest_path=self.manifest,
                opaque_id_file_path=self.ids,
                expected_identity=self.contract["dev64_identity"],
            )
        self.manifest.write_text(original, encoding="utf-8")
        id_rows = self.ids.read_text(encoding="utf-8").splitlines()
        id_rows[0], id_rows[1] = id_rows[1], id_rows[0]
        self.ids.write_text("\n".join(id_rows) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "identity"):
            snapshot_visible_dev64_inputs(
                runtime_manifest_path=self.manifest,
                opaque_id_file_path=self.ids,
                expected_identity=self.contract["dev64_identity"],
            )

    def test_manifest_rejects_duplicate_json_keys(self) -> None:
        original = self.manifest.read_text(encoding="utf-8")
        lines = self.manifest.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        lines[0] = (
            '{"opaque_id":'
            + json.dumps(first["opaque_id"])
            + ',"question":"first","question":"second"}'
        )
        self.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON keys"):
            snapshot_visible_dev64_inputs(
                runtime_manifest_path=self.manifest,
                opaque_id_file_path=self.ids,
                expected_identity=self.contract["dev64_identity"],
            )
        self.manifest.write_text(original, encoding="utf-8")

    def test_input_source_contract_and_receipt_tamper_fail_closed(self) -> None:
        package = self.initialize()
        original_ids = self.ids.read_text(encoding="utf-8")
        self.ids.write_text(original_ids.replace("task_", "task_f", 1), encoding="utf-8")
        with self.assertRaises(CandidateDev64LauncherPoisoned):
            package.preflight()
        self.ids.write_text(original_ids, encoding="utf-8")

        package._contract["dev64_launch_authorized"] = True
        with self.assertRaises(CandidateDev64LauncherPoisoned):
            package.preflight()
        package._contract = copy.deepcopy(self.contract)

        ready = json.loads(package.ready_path.read_text(encoding="utf-8"))
        ready["lease_acquired"] = True
        package.ready_path.write_text(json.dumps(ready), encoding="utf-8")
        with self.assertRaises(CandidateDev64LauncherPoisoned):
            package.preflight()

    def test_source_drift_fails_before_pair_preparation(self) -> None:
        root = self.launcher_root()
        with mock.patch(
            "deepwide_agent.v24254_candidate_dev64_launcher."
            "build_candidate_dev64_launcher_source_manifest",
            return_value={"drifted": True},
        ):
            with self.assertRaises(CandidateDev64LauncherPoisoned):
                CandidateDev64LauncherPackage.initialize(
                    root=root,
                    repository_root=ROOT,
                    contract=self.contract,
                    runtime_manifest_path=self.manifest,
                    opaque_id_file_path=self.ids,
                )
        self.assertEqual(list(root.iterdir()), [])

    def test_nonpristine_overlap_residue_symlink_and_hardlink_fail_closed(self) -> None:
        nonpristine = self.launcher_root()
        (nonpristine / "residue").mkdir()
        with self.assertRaises(FileExistsError):
            CandidateDev64LauncherPackage.initialize(
                root=nonpristine,
                repository_root=ROOT,
                contract=self.contract,
                runtime_manifest_path=self.manifest,
                opaque_id_file_path=self.ids,
            )
        with self.assertRaisesRegex(ValueError, "overlaps"):
            CandidateDev64LauncherPackage.initialize(
                root=self.base,
                repository_root=ROOT,
                contract=self.contract,
                runtime_manifest_path=self.manifest,
                opaque_id_file_path=self.ids,
            )

        package = self.initialize()
        (package.records_root / "unexpected").mkdir()
        with self.assertRaises(CandidateDev64LauncherPoisoned):
            package.preflight()

        package = self.initialize()
        output = package.arm_roots("legacy_control")["output"]
        output.rmdir()
        output.symlink_to(package.arm_roots("candidate_runtime")["output"])
        with self.assertRaises(CandidateDev64LauncherPoisoned):
            package.preflight()

        package = self.initialize()
        second = package.root / "hardlinked_ready.json"
        second.hardlink_to(package.ready_path)
        with self.assertRaises(CandidateDev64LauncherPoisoned):
            package.preflight()

    def test_create_exclusive_initialization_cannot_repeat(self) -> None:
        package = self.initialize()
        with self.assertRaises(FileExistsError):
            CandidateDev64LauncherPackage.initialize(
                root=package.root,
                repository_root=ROOT,
                contract=self.contract,
                runtime_manifest_path=self.manifest,
                opaque_id_file_path=self.ids,
            )

    def test_contract_rejects_activation_barrier_or_parent_binding_drift(self) -> None:
        cases = []
        activated = copy.deepcopy(self.contract)
        activated["launch_activation_implemented"] = True
        cases.append(activated)
        mapping = copy.deepcopy(self.contract)
        mapping["terminal_and_evaluator_barrier_contract"][
            "mapping_path_open_hash_or_read_before_barrier_allowed"
        ] = True
        cases.append(mapping)
        parent = copy.deepcopy(self.contract)
        parent["parent_runtime_audit"]["audit_valid"] = False
        cases.append(parent)
        priority = copy.deepcopy(self.contract)
        priority["upstream_priority_contract"][
            "existing_v24216_to_v24220_chain_has_priority"
        ] = False
        cases.append(priority)
        threshold = copy.deepcopy(self.contract)
        threshold["engineering_gate_decision_contract"][
            "system_total_token_ratio_max"
        ] = 1.2
        cases.append(threshold)
        for value in cases:
            value["launcher_contract_sha256"] = self.contract[
                "launcher_contract_sha256"
            ]
            with self.subTest():
                with self.assertRaisesRegex(ValueError, "contract"):
                    validate_candidate_dev64_launcher_contract(value)


if __name__ == "__main__":
    unittest.main()
