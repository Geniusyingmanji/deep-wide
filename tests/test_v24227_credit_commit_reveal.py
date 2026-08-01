from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24223_sign_preserving_credit import object_sha256  # noqa: E402
from deepwide_agent.v24227_credit_commit_reveal import (  # noqa: E402
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    CreditOuterSequenceStore,
    build_commit_reveal_protocol,
    validate_commit_reveal_protocol,
    validate_launch_receipt,
    validate_outer_reservation_receipt,
    validate_prediction_commitment,
    validate_reveal_receipt,
)
from tests.test_v24226_credit_outer_target_firewall import (  # noqa: E402
    components,
    digest,
    pair,
)


def reseal(value: dict[str, object], field: str) -> None:
    value.pop(field, None)
    value[field] = object_sha256(value)


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class V24227CreditCommitRevealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.values = components()
        cls.outer_pair = pair(cls.values)
        cls.namespace = digest("1")
        cls.sequence_protocol = build_commit_reveal_protocol(
            outer_target_protocol=cls.values["protocol"],  # type: ignore[arg-type]
            sequence_namespace_sha256=cls.namespace,
            coordinator_contract_sha256=digest("2"),
            launch_policy_sha256=digest("3"),
        )

    def new_store(self, root: Path) -> CreditOuterSequenceStore:
        return CreditOuterSequenceStore(
            root=root, sequence_namespace_sha256=self.namespace
        )

    def commit(self, store: CreditOuterSequenceStore) -> dict[str, object]:
        return store.commit(
            protocol=self.sequence_protocol,
            prediction_freeze=self.values["freeze"],  # type: ignore[arg-type]
            outer_seed_schedule_sha256=digest("4"),
            outer_execution_contract_sha256=digest("5"),
            outer_evaluator_protocol_sha256=digest("6"),
        )

    def complete(self, root: Path) -> tuple[CreditOuterSequenceStore, dict[str, object]]:
        store = self.new_store(root)
        self.commit(store)
        store.open_launch(launch_request_sha256=digest("7"))
        store.publish_outer_pair(pair=self.outer_pair)
        reveal = store.reveal()
        return store, reveal

    def test_protocol_and_all_stages_are_label_blind_and_authorize_nothing(self) -> None:
        validate_commit_reveal_protocol(
            self.sequence_protocol,
            outer_target_protocol=self.values["protocol"],  # type: ignore[arg-type]
        )
        constants = (
            PRODUCTION_PACKAGE_AUTHORIZED,
            CREDIT_TRAINING_AUTHORIZED,
            GATE2B_PASS_AUTHORIZED,
            OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
        )
        self.assertEqual(constants, (False, False, False, False, False))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self.new_store(root)
            commitment = self.commit(store)
            launch = store.open_launch(launch_request_sha256=digest("7"))
            reservation = store._read_object(store.outer_reservation_path)
            store.publish_outer_pair(pair=self.outer_pair)
            reveal = store.reveal()
            validate_prediction_commitment(
                commitment,
                protocol=self.sequence_protocol,
                prediction_freeze=self.values["freeze"],  # type: ignore[arg-type]
            )
            validate_launch_receipt(
                launch, protocol=self.sequence_protocol, commitment=commitment
            )
            validate_outer_reservation_receipt(
                reservation, protocol=self.sequence_protocol, launch=launch
            )
            validate_reveal_receipt(
                reveal,
                protocol=self.sequence_protocol,
                commitment=commitment,
                launch=launch,
                reservation=reservation,
                pair=self.outer_pair,
            )
            for artifact in (self.sequence_protocol, commitment, launch, reservation, reveal):
                self.assertTrue(artifact["label_blind_control"])
                for field in (
                    "production_package_authorized",
                    "credit_training_authorized",
                    "gate2b_pass_authorized",
                    "outer_campaign_execution_authorized",
                    "benchmark_forward_or_evaluator_authorized",
                ):
                    self.assertFalse(artifact[field], field)
            self.assertTrue(
                reveal[
                    "post_prediction_outer_target_contribution_available_to_reveal_validator"
                ]
            )
            self.assertFalse(
                reveal["outer_target_used_for_runtime_routing_or_same_forward_pass"]
            )

    def test_complete_sequence_binds_exact_files_but_discloses_claim_limits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store, reveal = self.complete(Path(directory))
            self.assertEqual(store.validate_complete_sequence(), reveal)
            self.assertTrue(reveal["repository_commit_launch_reveal_order_enforced"])
            self.assertFalse(reveal["outer_pair_native_launch_challenge_binding_present"])
            self.assertFalse(reveal["external_target_precomputation_excluded"])
            self.assertFalse(reveal["trusted_physical_wall_clock_used"])
            self.assertFalse(
                reveal["physical_wall_clock_creation_order_independently_proven"]
            )
            self.assertFalse(
                reveal["hostile_concurrent_filesystem_mutation_excluded"]
            )
            self.assertFalse(
                reveal["independent_append_only_or_transparency_service_used"]
            )
            self.assertFalse(reveal["store_api_execution_independently_attested"])
            self.assertFalse(
                reveal[
                    "offline_self_consistent_chain_fabrication_cryptographically_excluded"
                ]
            )
            self.assertTrue(reveal["local_file_and_directory_fsync_used"])
            self.assertFalse(reveal["semantic_or_distributional_ood_independently_assessed"])
            self.assertFalse(reveal["formal_gate2b_evaluation_authorized"])
            self.assertEqual(
                set(store.directory.iterdir()),
                {
                    store.protocol_path,
                    store.commitment_path,
                    store.launch_path,
                    store.outer_directory,
                    store.reveal_path,
                },
            )
            self.assertEqual(
                set(store.outer_directory.iterdir()),
                {store.outer_reservation_path, store.outer_pair_path},
            )

    def test_stage_skips_and_duplicate_publications_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.new_store(Path(directory))
            with self.assertRaises((FileNotFoundError, ValueError)):
                store.open_launch(launch_request_sha256=digest("7"))
            self.commit(store)
            with self.assertRaises((FileNotFoundError, ValueError)):
                store.publish_outer_pair(pair=self.outer_pair)
            store.open_launch(launch_request_sha256=digest("7"))
            with self.assertRaises((FileNotFoundError, ValueError)):
                store.reveal()
            with self.assertRaises((FileExistsError, ValueError)):
                store.open_launch(launch_request_sha256=digest("7"))
            store.publish_outer_pair(pair=self.outer_pair)
            with self.assertRaises(FileExistsError):
                store.publish_outer_pair(pair=self.outer_pair)
            store.reveal()
            with self.assertRaises(FileExistsError):
                store.reveal()
            with self.assertRaises(FileExistsError):
                self.commit(store)

    def test_failed_stage_write_leaves_append_only_poison_and_blocks_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.new_store(Path(directory))
            def fail_after_partial(value: object, handle: object, **kwargs: object) -> None:
                handle.write("{")  # type: ignore[attr-defined]
                raise OSError("synthetic write failure")

            with mock.patch(
                "deepwide_agent.v24227_credit_commit_reveal.json.dump",
                side_effect=fail_after_partial,
            ):
                with self.assertRaisesRegex(OSError, "synthetic write failure"):
                    self.commit(store)
            self.assertTrue(store.protocol_path.exists())
            with self.assertRaises(FileExistsError):
                self.commit(store)
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                store.open_launch(launch_request_sha256=digest("7"))

    def test_preexisting_namespace_and_residue_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self.new_store(root)
            store.directory.mkdir()
            with self.assertRaises(FileExistsError):
                self.commit(store)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self.new_store(root)
            self.commit(store)
            (store.directory / "residue").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "residue"):
                store.open_launch(launch_request_sha256=digest("7"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self.new_store(root)
            self.commit(store)
            store.open_launch(launch_request_sha256=digest("7"))
            (store.outer_directory / "residue").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "residue"):
                store.publish_outer_pair(pair=self.outer_pair)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_roots_stage_files_and_outer_root_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            real = base / "real"
            real.mkdir()
            alias = base / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "ordinary directory"):
                self.new_store(alias)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external"
            external.mkdir()
            store = self.new_store(root)
            store.directory.symlink_to(external, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                self.commit(store)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self.new_store(root)
            self.commit(store)
            external = root / "external.json"
            shutil.copyfile(store.commitment_path, external)
            store.commitment_path.unlink()
            store.commitment_path.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "ordinary stage file"):
                store.open_launch(launch_request_sha256=digest("7"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self.new_store(root)
            self.commit(store)
            store.open_launch(launch_request_sha256=digest("7"))
            store.outer_reservation_path.unlink()
            store.outer_directory.rmdir()
            external = root / "external-outer"
            external.mkdir()
            store.outer_directory.symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "nonordinary"):
                store.publish_outer_pair(pair=self.outer_pair)

    def test_wrong_campaign_pair_and_resealed_manifest_drift_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.new_store(Path(directory))
            self.commit(store)
            store.open_launch(launch_request_sha256=digest("7"))
            wrong = copy.deepcopy(self.outer_pair)
            wrong["semantic_bundle_sha256"] = digest("8")
            reseal(wrong, "pair_sha256")
            with self.assertRaisesRegex(ValueError, "committed campaign"):
                store.publish_outer_pair(pair=wrong)

    def test_commit_rejects_prediction_from_a_different_outer_protocol(self) -> None:
        different = copy.deepcopy(self.values["protocol"])
        different["selection_protocol_sha256"] = digest("8")
        reseal(different, "protocol_sha256")
        sequence = build_commit_reveal_protocol(
            outer_target_protocol=different,
            sequence_namespace_sha256=self.namespace,
            coordinator_contract_sha256=digest("2"),
            launch_policy_sha256=digest("3"),
        )
        with tempfile.TemporaryDirectory() as directory:
            store = self.new_store(Path(directory))
            with self.assertRaisesRegex(ValueError, "prediction binding"):
                store.commit(
                    protocol=sequence,
                    prediction_freeze=self.values["freeze"],  # type: ignore[arg-type]
                    outer_seed_schedule_sha256=digest("4"),
                    outer_execution_contract_sha256=digest("5"),
                    outer_evaluator_protocol_sha256=digest("6"),
                )

    @unittest.skipUnless(hasattr(os, "link"), "hard links unavailable")
    def test_hardlinked_stage_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self.new_store(root)
            self.commit(store)
            os.link(store.commitment_path, root / "second-link.json")
            with self.assertRaisesRegex(ValueError, "ordinary stage file"):
                store.open_launch(launch_request_sha256=digest("7"))

    def test_reveal_validator_rechecks_pair_to_commitment_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store, reveal = self.complete(Path(directory))
            protocol = store._read_object(store.protocol_path)
            commitment = store._read_object(store.commitment_path)
            launch = store._read_object(store.launch_path)
            reservation = store._read_object(store.outer_reservation_path)
            wrong_pair = copy.deepcopy(self.outer_pair)
            wrong_pair["semantic_bundle_sha256"] = digest("8")
            reseal(wrong_pair, "pair_sha256")
            wrong_reveal = copy.deepcopy(reveal)
            wrong_reveal["outer_pair_sha256"] = wrong_pair["pair_sha256"]
            wrong_reveal["semantic_bundle_sha256"] = digest("8")
            reseal(wrong_reveal, "reveal_sha256")
            with self.assertRaisesRegex(ValueError, "committed campaign"):
                validate_reveal_receipt(
                    wrong_reveal,
                    protocol=protocol,
                    commitment=commitment,
                    launch=launch,
                    reservation=reservation,
                    pair=wrong_pair,
                )

    def test_reveal_cannot_be_validated_without_complete_predecessor_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, reveal = self.complete(Path(directory))
            with self.assertRaisesRegex(ValueError, "complete predecessor chain"):
                validate_reveal_receipt(reveal)

    def test_resealed_stage_tampering_and_extra_residue_are_detected(self) -> None:
        mutations = {
            "protocol": ("coordinator_contract_sha256", digest("8"), "protocol_sha256"),
            "commitment": ("predicted_credit", 0.123, "commitment_sha256"),
            "launch": ("launch_challenge_sha256", digest("8"), "launch_receipt_sha256"),
            "reservation": ("reservation_nonce_sha256", digest("8"), "reservation_sha256"),
            "pair": ("outer_target_contribution", -0.123, "pair_sha256"),
            "reveal": ("formal_gate2b_evaluation_authorized", True, "reveal_sha256"),
        }
        for name, (field, replacement, seal) in mutations.items():
            with self.subTest(stage=name), tempfile.TemporaryDirectory() as directory:
                store, _ = self.complete(Path(directory))
                paths = {
                    "protocol": store.protocol_path,
                    "commitment": store.commitment_path,
                    "launch": store.launch_path,
                    "reservation": store.outer_reservation_path,
                    "pair": store.outer_pair_path,
                    "reveal": store.reveal_path,
                }
                value = store._read_object(paths[name])
                value[field] = replacement
                reseal(value, seal)
                write_json(paths[name], value)
                with self.assertRaises((ValueError, KeyError)):
                    store.validate_complete_sequence()
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.complete(Path(directory))
            (store.outer_directory / "late-residue").write_text(
                "x", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "residue"):
                store.validate_complete_sequence()

    def test_exact_schemas_reject_privileged_or_unknown_fields(self) -> None:
        for field in (
            "category",
            "question_type",
            "ground_truth",
            "evaluator_score",
            "reward",
        ):
            with self.subTest(field=field):
                value = copy.deepcopy(self.sequence_protocol)
                value[field] = "forbidden"
                reseal(value, "protocol_sha256")
                with self.assertRaisesRegex(ValueError, "schema is not exact"):
                    validate_commit_reveal_protocol(value)

    def test_stage_reader_rejects_duplicate_keys_and_nonstandard_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stage.json"
            path.write_text('{"a":1,"a":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate key"):
                CreditOuterSequenceStore._read_object(path)
            path.write_text('{"a":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonstandard NaN"):
                CreditOuterSequenceStore._read_object(path)


if __name__ == "__main__":
    unittest.main()
