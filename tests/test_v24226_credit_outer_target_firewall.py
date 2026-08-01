from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24121_continuation import object_sha256  # noqa: E402
from deepwide_agent.v24123_release import (  # noqa: E402
    REPLICATE_IDS,
    aggregate_replicate_contributions,
    attach_v24122_terminal_evaluator,
    contribution_record,
)
from deepwide_agent.v24223_sign_preserving_credit import (  # noqa: E402
    MODULATION_POLICY_SHA256,
    build_amplitude_features,
    modulate_verified_credit,
)
from deepwide_agent.v24224_credit_source_adapter import (  # noqa: E402
    adapt_v24123_source_graph,
)
from deepwide_agent.v24226_credit_outer_target_firewall import (  # noqa: E402
    CREDIT_TRAINING_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_credit_prediction_freeze,
    build_outer_target_diagnostic_aggregate,
    build_outer_target_protocol,
    join_independent_outer_target,
    validate_credit_prediction_freeze,
    validate_independent_outer_target_pair,
    validate_outer_target_diagnostic_aggregate,
    validate_outer_target_protocol,
)
from tests.test_v24224_credit_source_adapter import (  # noqa: E402
    artifact_sha256,
    build_fixture,
    reseal,
)


def digest(character: str) -> str:
    return character * 64


def protocol(*audit_clusters: str) -> dict[str, object]:
    return build_outer_target_protocol(
        selection_protocol_sha256=digest("a"),
        fit_task_cluster_ref_sha256s=[digest("b"), digest("c")],
        calibration_task_cluster_ref_sha256s=[digest("d")],
        audit_task_cluster_ref_sha256s=[digest(value) for value in audit_clusters],
    )


def set_cluster(fixture: dict[str, object], character: str) -> None:
    manifest = fixture["job_manifest"]
    bundle = manifest["bundles"][0]  # type: ignore[index]
    bundle["task_cluster_ref_sha256"] = digest(character)  # type: ignore[index]
    bundle["partition_role"] = "development_audit"  # type: ignore[index]
    identity = {
        key: bundle[key]  # type: ignore[index]
        for key in (
            "task_cluster_ref_sha256",
            "trajectory_ref_sha256",
            "partition_role",
            "context",
            "action",
            "source_checkpoint_sha256",
            "shadow_projection_sha256",
            "visible_question_sha256",
            "target_manifest_sha256",
            "continuation_policy_sha256",
        )
    }
    bundle["bundle_sha256"] = object_sha256(identity)  # type: ignore[index]
    fixture["bundle_sha256"] = bundle["bundle_sha256"]  # type: ignore[index]
    manifest.pop("manifest_sha256")  # type: ignore[union-attr]
    manifest["manifest_sha256"] = object_sha256(manifest)  # type: ignore[index]
    manifest_sha = manifest["manifest_sha256"]  # type: ignore[index]
    old_evaluated = copy.deepcopy(fixture["evaluated_terminal_receipts"])
    parents = [_parent_from_evaluated(row) for row in old_evaluated]
    for parent in parents:
        parent["job_manifest_sha256"] = manifest_sha
        reseal(parent, "receipt_payload_sha256")
    _rebuild_post_terminal_graph(
        fixture,
        parents=parents,
        gains=tuple(
            float(record["signed_task_contribution"])
            for record in fixture["contribution_records"]  # type: ignore[union-attr]
        ),
        evaluator_nonce="cluster-" + character,
        previous_evaluated=old_evaluated,
    )


EVALUATOR_EXTENSION_KEYS = (
    "evaluator_protocol_sha256",
    "evaluator_artifact_sha256",
    "prediction_freeze_sha256",
    "evaluator_provenance_receipt_sha256",
    "official_prediction_sha256",
    "evaluator_attempted",
    "evaluator_returncode",
    "evaluator_run_config_sha256",
    "evaluator_result_sha256",
    "evaluator_joined_post_terminal_only",
    "evaluator_valid",
    "official_metrics",
    "terminal_task_loss",
    "credit_label_definition",
    "official_score_used_as_credit_label",
)


def _parent_from_evaluated(value: dict[str, object]) -> dict[str, object]:
    parent = copy.deepcopy(value)
    parent_hash = parent.pop("parent_v24122_terminal_receipt_sha256")
    for key in EVALUATOR_EXTENSION_KEYS:
        parent.pop(key, None)
    parent["role"] = "v24122_true_continuation_terminal_receipt"
    parent["evaluator_read"] = False
    parent["receipt_payload_sha256"] = parent_hash
    return parent


def _enriched_aggregate(
    fixture: dict[str, object], records: list[dict[str, object]]
) -> dict[str, object]:
    manifest = fixture["job_manifest"]
    bundle = manifest["bundles"][0]  # type: ignore[index]
    aggregate = aggregate_replicate_contributions(records)
    aggregate.pop("aggregate_sha256")
    aggregate.update(
        {
            "bundle_sha256": bundle["bundle_sha256"],  # type: ignore[index]
            "task_cluster_ref_sha256": bundle["task_cluster_ref_sha256"],  # type: ignore[index]
            "partition_role": bundle["partition_role"],  # type: ignore[index]
            "context": bundle["context"],  # type: ignore[index]
            "action": bundle["action"],  # type: ignore[index]
            "job_manifest_sha256": manifest["manifest_sha256"],  # type: ignore[index]
            "replicate_action_observation_sha256s": [
                value["action_observation_sha256"] for value in records
            ],
            "replicate_branch_adapter_receipt_sha256s": [
                value["branch_adapter_receipt_sha256"] for value in records
            ],
        }
    )
    aggregate["aggregate_sha256"] = object_sha256(aggregate)
    return aggregate


def _rebuild_post_terminal_graph(
    fixture: dict[str, object],
    *,
    parents: list[dict[str, object]],
    gains: tuple[float, float, float],
    evaluator_nonce: str,
    previous_evaluated: list[dict[str, object]] | None = None,
) -> None:
    manifest = fixture["job_manifest"]
    bundle = manifest["bundles"][0]  # type: ignore[index]
    manifest_sha = manifest["manifest_sha256"]  # type: ignore[index]
    freeze = copy.deepcopy(fixture["prediction_freeze"])
    freeze["bundle_sha256"] = bundle["bundle_sha256"]
    freeze["job_manifest_sha256"] = manifest_sha
    freeze["replicate_action_observation_sha256s"] = [
        next(
            parent["action_observation_sha256"]
            for parent in parents
            if parent["replicate_id"] == replicate
        )
        for replicate in REPLICATE_IDS
    ]
    freeze["replicate_branch_adapter_receipt_sha256s"] = [
        next(
            parent["branch_adapter_receipt_sha256"]
            for parent in parents
            if parent["replicate_id"] == replicate
        )
        for replicate in REPLICATE_IDS
    ]
    parent_index = {
        (row["replicate_id"], row["branch_role"]): row for row in parents
    }
    freeze["terminal_receipt_sha256s"] = [
        parent_index[(replicate, role)]["receipt_payload_sha256"]
        for replicate in REPLICATE_IDS
        for role in bundle["branch_order_by_replicate"][str(replicate)]
    ]
    reseal(freeze, "seal_sha256")
    freeze_sha = artifact_sha256(freeze)
    provenance = copy.deepcopy(fixture["evaluator_provenance_receipt"])
    provenance["bundle_sha256"] = bundle["bundle_sha256"]
    provenance["prediction_freeze_sha256"] = freeze_sha
    provenance["live_provenance"] = {"closure": object_sha256(evaluator_nonce)}
    reseal(provenance, "receipt_sha256")
    old_index = {
        (row["replicate_id"], row["branch_role"]): row
        for row in (previous_evaluated or fixture["evaluated_terminal_receipts"])
    }
    evaluated: list[dict[str, object]] = []
    states = {
        (row["replicate_id"], row["branch_role"]): row["terminal_state"]
        for row in fixture["terminal_state_records"]
    }
    for replicate, gain in zip(REPLICATE_IDS, gains):
        no_op_loss = 0.6
        action_loss = 0.6 - gain
        for role, loss in (("no_op", no_op_loss), ("action", action_loss)):
            parent = parent_index[(replicate, role)]
            old = old_index[(replicate, role)]
            metrics = {
                "score": 1.0 - loss,
                "entity_acc": 1.0 - loss,
                "f1_by_row": 1.0 - loss,
                "f1_by_item": 1.0 - loss,
                "column_f1": 1.0 - loss,
            }
            evaluator_result = object_sha256(
                ["evaluator", evaluator_nonce, replicate, role]
            )
            evaluated.append(
                attach_v24122_terminal_evaluator(
                    parent,
                    evaluator_protocol_sha256=old["evaluator_protocol_sha256"],
                    evaluator_artifact_sha256=evaluator_result,
                    evaluator_valid=True,
                    metrics=metrics,
                    prediction_freeze_sha256=freeze_sha,
                    evaluator_provenance_receipt_sha256=provenance[
                        "receipt_sha256"
                    ],
                    official_prediction_sha256=object_sha256(
                        ["prediction", evaluator_nonce, replicate, role]
                    ),
                    evaluator_attempted=True,
                    evaluator_returncode=0,
                    evaluator_run_config_sha256=object_sha256(
                        ["run-config", evaluator_nonce, replicate, role]
                    ),
                    evaluator_result_sha256=evaluator_result,
                )
            )
    evaluated_index = {
        (row["replicate_id"], row["branch_role"]): row for row in evaluated
    }
    records = [
        contribution_record(
            evaluated_index[(replicate, "no_op")],
            evaluated_index[(replicate, "action")],
            no_op_terminal_state=states[(replicate, "no_op")],
            action_terminal_state=states[(replicate, "action")],
        )
        for replicate in REPLICATE_IDS
    ]
    fixture["prediction_freeze"] = freeze
    fixture["evaluator_provenance_receipt"] = provenance
    fixture["evaluated_terminal_receipts"] = evaluated
    fixture["contribution_records"] = records
    fixture["replicate_aggregate"] = _enriched_aggregate(fixture, records)


def make_fixture(
    gains: tuple[float, float, float], *, cluster: str = "e"
) -> dict[str, object]:
    fixture = build_fixture(signed_gains=gains)
    set_cluster(fixture, cluster)
    return fixture


def independent_outer(
    inner_fixture: dict[str, object],
    gains: tuple[float, float, float],
    *,
    nonce: str,
) -> dict[str, object]:
    outer = copy.deepcopy(inner_fixture)
    parents = [
        _parent_from_evaluated(row)
        for row in outer["evaluated_terminal_receipts"]  # type: ignore[union-attr]
    ]
    for parent in parents:
        replicate = parent["replicate_id"]
        parent["action_observation_sha256"] = object_sha256(
            ["outer-observation", nonce, replicate]
        )
        parent["branch_adapter_receipt_sha256"] = object_sha256(
            ["outer-adapter", nonce, replicate]
        )
        parent["parent_v24121_terminal_receipt_sha256"] = object_sha256(
            ["outer-parent", nonce, replicate, parent["branch_role"]]
        )
        reseal(parent, "receipt_payload_sha256")
    _rebuild_post_terminal_graph(
        outer,
        parents=parents,
        gains=gains,
        evaluator_nonce="outer-" + nonce,
        previous_evaluated=copy.deepcopy(
            inner_fixture["evaluated_terminal_receipts"]  # type: ignore[arg-type]
        ),
    )
    return outer


def adapt(fixture: dict[str, object]) -> dict[str, object]:
    return adapt_v24123_source_graph(**fixture)  # type: ignore[arg-type]


def components(
    *,
    gains: tuple[float, float, float] = (0.4, -0.2, 0.1),
    nonce: str = "f",
) -> dict[str, object]:
    frozen_protocol = protocol("e")
    inner_fixture = make_fixture(gains)
    inner_result = adapt(inner_fixture)
    amplitude = build_amplitude_features(
        opaque_step_ref_sha256=inner_result["verified_contribution"][  # type: ignore[index]
            "opaque_step_ref_sha256"
        ],
        source_checkpoint_sha256=inner_result["verified_contribution"][  # type: ignore[index]
            "source_checkpoint_sha256"
        ],
        feature_source_sha256=digest("9"),
        entropy_reduction=0.2,
        provenance_role="discovery",
        provenance_strength=0.6,
        cost_fraction=0.1,
    )
    modulation = modulate_verified_credit(
        verified_contribution=inner_result["verified_contribution"],  # type: ignore[arg-type,index]
        amplitude_features=amplitude,
    )
    freeze = build_credit_prediction_freeze(
        protocol=frozen_protocol,
        inner_job_manifest=inner_fixture["job_manifest"],  # type: ignore[arg-type]
        inner_adapter_result=inner_result,
        amplitude_features=amplitude,
        modulation_receipt=modulation,
    )
    outer_fixture = independent_outer(
        inner_fixture, gains, nonce=nonce
    )
    outer_result = adapt(outer_fixture)
    return {
        "protocol": frozen_protocol,
        "inner_fixture": inner_fixture,
        "inner_result": inner_result,
        "amplitude": amplitude,
        "modulation": modulation,
        "freeze": freeze,
        "outer_fixture": outer_fixture,
        "outer_result": outer_result,
    }


def pair(values: dict[str, object]) -> dict[str, object]:
    return join_independent_outer_target(
        protocol=values["protocol"],  # type: ignore[arg-type]
        prediction_freeze=values["freeze"],  # type: ignore[arg-type]
        inner_job_manifest=values["inner_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
        inner_adapter_result=values["inner_result"],  # type: ignore[arg-type]
        amplitude_features=values["amplitude"],  # type: ignore[arg-type]
        modulation_receipt=values["modulation"],  # type: ignore[arg-type]
        outer_job_manifest=values["outer_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
        outer_adapter_result=values["outer_result"],  # type: ignore[arg-type]
    )


class V24226CreditOuterTargetFirewallTests(unittest.TestCase):
    def test_protocol_freezes_disjoint_cluster_splits_and_no_authority(self) -> None:
        value = protocol("e")
        validate_outer_target_protocol(value)
        self.assertTrue(value["task_cluster_sets_pairwise_disjoint"])
        self.assertTrue(value["audit_clusters_unavailable_to_policy_selection"])
        self.assertEqual(value["credit_policy_sha256"], MODULATION_POLICY_SHA256)
        self.assertFalse(value["production_package_authorized"])
        self.assertFalse(value["credit_training_authorized"])
        self.assertFalse(value["gate2b_pass_authorized"])
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(CREDIT_TRAINING_AUTHORIZED)
        self.assertFalse(GATE2B_PASS_AUTHORIZED)

    def test_protocol_rejects_any_cluster_overlap(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            build_outer_target_protocol(
                selection_protocol_sha256=digest("a"),
                fit_task_cluster_ref_sha256s=[digest("b")],
                calibration_task_cluster_ref_sha256s=[digest("c")],
                audit_task_cluster_ref_sha256s=[digest("b")],
            )

    def test_prediction_freeze_accepts_only_audit_cluster_and_excludes_outer(self) -> None:
        values = components()
        freeze = values["freeze"]
        validate_credit_prediction_freeze(
            freeze, protocol=values["protocol"]  # type: ignore[arg-type]
        )
        self.assertTrue(freeze["outer_target_unavailable_to_prediction_builder"])
        self.assertFalse(
            freeze[
                "outer_job_manifest_source_receipt_target_or_contribution_read"
            ]
        )
        self.assertEqual(freeze["partition_role"], "development_audit")

    def test_valid_outer_pair_reuses_contract_but_not_arm_graph(self) -> None:
        values = components()
        result = pair(values)
        validate_independent_outer_target_pair(
            result, protocol=values["protocol"]  # type: ignore[arg-type]
        )
        self.assertEqual(
            result["inner_job_manifest_sha256"],
            result["outer_job_manifest_sha256"],
        )
        self.assertTrue(result["inner_outer_job_manifest_contract_equal"])
        self.assertEqual(result["inner_outer_arm_graph_hash_intersection_count"], 0)
        self.assertTrue(result["inner_outer_arm_graph_hashes_disjoint"])
        self.assertFalse(result["same_source_contribution_used_as_outer_target"])
        self.assertFalse(result["gate2b_pass_authorized"])

    def test_equal_numeric_contribution_is_allowed_when_artifacts_are_independent(self) -> None:
        result = pair(components(gains=(0.4, -0.2, 0.1)))
        self.assertEqual(
            result["inner_source_contribution_diagnostic"],
            result["outer_target_contribution"],
        )
        self.assertTrue(
            result["numeric_contribution_equality_does_not_imply_artifact_reuse"]
        )

    def test_same_source_graph_as_outer_target_is_rejected(self) -> None:
        values = components()
        with self.assertRaisesRegex(ValueError, "arm graphs overlap"):
            join_independent_outer_target(
                protocol=values["protocol"],  # type: ignore[arg-type]
                prediction_freeze=values["freeze"],  # type: ignore[arg-type]
                inner_job_manifest=values["inner_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
                inner_adapter_result=values["inner_result"],  # type: ignore[arg-type]
                amplitude_features=values["amplitude"],  # type: ignore[arg-type]
                modulation_receipt=values["modulation"],  # type: ignore[arg-type]
                outer_job_manifest=values["inner_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
                outer_adapter_result=values["inner_result"],  # type: ignore[arg-type]
            )

    def test_semantically_different_outer_step_is_rejected(self) -> None:
        values = components()
        bad_fixture = copy.deepcopy(values["outer_fixture"])
        bad_fixture["job_manifest"]["bundles"][0]["action"] = "falsify_anchor"  # type: ignore[index]
        with self.assertRaises(ValueError):
            join_independent_outer_target(
                protocol=values["protocol"],  # type: ignore[arg-type]
                prediction_freeze=values["freeze"],  # type: ignore[arg-type]
                inner_job_manifest=values["inner_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
                inner_adapter_result=values["inner_result"],  # type: ignore[arg-type]
                amplitude_features=values["amplitude"],  # type: ignore[arg-type]
                modulation_receipt=values["modulation"],  # type: ignore[arg-type]
                outer_job_manifest=bad_fixture["job_manifest"],  # type: ignore[index,arg-type]
                outer_adapter_result=values["outer_result"],  # type: ignore[arg-type]
            )

    def test_tampered_prediction_freeze_fails_even_when_resealed(self) -> None:
        values = components()
        bad = copy.deepcopy(values["freeze"])
        bad["predicted_credit"] = -bad["predicted_credit"]  # type: ignore[operator]
        reseal(bad, "freeze_sha256")
        with self.assertRaisesRegex(ValueError, "differs from source replay"):
            join_independent_outer_target(
                protocol=values["protocol"],  # type: ignore[arg-type]
                prediction_freeze=bad,
                inner_job_manifest=values["inner_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
                inner_adapter_result=values["inner_result"],  # type: ignore[arg-type]
                amplitude_features=values["amplitude"],  # type: ignore[arg-type]
                modulation_receipt=values["modulation"],  # type: ignore[arg-type]
                outer_job_manifest=values["outer_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
                outer_adapter_result=values["outer_result"],  # type: ignore[arg-type]
            )

    def test_aggregate_is_diagnostic_only_and_cannot_pass_gate2b(self) -> None:
        frozen_protocol = protocol("e", "f", "9")
        pairs = []
        for cluster, gains, nonce in (
            ("e", (0.4, -0.2, 0.1), "6"),
            ("f", (-0.4, -0.2, -0.1), "7"),
            ("9", (0.2, 0.3, 0.4), "8"),
        ):
            values = components(gains=gains, nonce=nonce)
            values["protocol"] = frozen_protocol
            values["inner_fixture"] = make_fixture(gains, cluster=cluster)
            values["inner_result"] = adapt(values["inner_fixture"])  # type: ignore[arg-type]
            verified = values["inner_result"]["verified_contribution"]  # type: ignore[index]
            values["amplitude"] = build_amplitude_features(
                opaque_step_ref_sha256=verified["opaque_step_ref_sha256"],
                source_checkpoint_sha256=verified["source_checkpoint_sha256"],
                feature_source_sha256=digest(nonce),
                entropy_reduction=0.2,
                provenance_role="discovery",
                provenance_strength=0.6,
                cost_fraction=0.1,
            )
            values["modulation"] = modulate_verified_credit(
                verified_contribution=verified,
                amplitude_features=values["amplitude"],  # type: ignore[arg-type]
            )
            values["freeze"] = build_credit_prediction_freeze(
                protocol=frozen_protocol,
                inner_job_manifest=values["inner_fixture"]["job_manifest"],  # type: ignore[index,arg-type]
                inner_adapter_result=values["inner_result"],  # type: ignore[arg-type]
                amplitude_features=values["amplitude"],  # type: ignore[arg-type]
                modulation_receipt=values["modulation"],  # type: ignore[arg-type]
            )
            values["outer_fixture"] = independent_outer(
                values["inner_fixture"], gains, nonce=nonce  # type: ignore[arg-type]
            )
            values["outer_result"] = adapt(values["outer_fixture"])  # type: ignore[arg-type]
            pairs.append(pair(values))
        report = build_outer_target_diagnostic_aggregate(
            protocol=frozen_protocol, pairs=pairs
        )
        validate_outer_target_diagnostic_aggregate(
            report, protocol=frozen_protocol
        )
        self.assertEqual(report["pair_count"], 3)
        self.assertEqual(report["unique_audit_task_cluster_count"], 3)
        self.assertEqual(report["same_source_target_self_evaluation_pair_count"], 0)
        self.assertTrue(report["mechanical_self_confirmation_prevented"])
        self.assertEqual(report["diagnostic_status"], "contract_only_not_evaluable_or_fail")
        self.assertFalse(report["cluster_bootstrap_performed"])
        self.assertFalse(report["stress_family_minima_verified"])
        self.assertFalse(report["gate2b_pass_authorized"])

    def test_duplicate_pair_is_rejected(self) -> None:
        values = components()
        result = pair(values)
        with self.assertRaisesRegex(ValueError, "duplicated"):
            build_outer_target_diagnostic_aggregate(
                protocol=values["protocol"],  # type: ignore[arg-type]
                pairs=[result, result],
            )

    def test_resealed_pair_claiming_same_source_target_is_rejected(self) -> None:
        values = components()
        result = pair(values)
        bad = copy.deepcopy(result)
        bad["same_source_contribution_used_as_outer_target"] = True
        reseal(bad, "pair_sha256")
        with self.assertRaisesRegex(ValueError, "pair contract drifted"):
            validate_independent_outer_target_pair(
                bad, protocol=values["protocol"]  # type: ignore[arg-type]
            )

    def test_exact_schemas_reject_extra_fields(self) -> None:
        values = components()
        result = pair(values)
        for validator, value, kwargs in (
            (validate_outer_target_protocol, values["protocol"], {}),
            (
                validate_credit_prediction_freeze,
                values["freeze"],
                {"protocol": values["protocol"]},
            ),
            (
                validate_independent_outer_target_pair,
                result,
                {"protocol": values["protocol"]},
            ),
        ):
            with self.subTest(validator=validator.__name__):
                with self.assertRaisesRegex(ValueError, "schema is not exact"):
                    validator({**value, "extra": False}, **kwargs)


if __name__ == "__main__":
    unittest.main()
