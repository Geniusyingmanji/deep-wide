from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.owic import FEATURE_KEYS  # noqa: E402
from deepwide_agent.v24121_continuation import object_sha256  # noqa: E402
from deepwide_agent.v24123_release import (  # noqa: E402
    CAPTURE_DESIGN_ID,
    EXPECTED_CANDIDATE_STATE_SCHEMA_VERSION,
    REPLICATE_IDS,
    aggregate_replicate_contributions,
    attach_v24122_terminal_evaluator,
    contribution_record,
)
from deepwide_agent.v24224_credit_source_adapter import (  # noqa: E402
    CREDIT_TRAINING_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    adapt_v24123_source_graph,
    validate_adapter_result,
)


def digest(value: object) -> str:
    return object_sha256(value)


def reseal(value: dict[str, object], key: str) -> None:
    unsigned = copy.deepcopy(value)
    unsigned.pop(key, None)
    value[key] = object_sha256(unsigned)


def artifact_sha256(value: object) -> str:
    return hashlib.sha256(
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    ).hexdigest()


def terminal_receipt(
    role: str,
    replicate: int,
    *,
    manifest_sha256: str,
    terminal_state: dict[str, object],
    status: str = "completed",
) -> dict[str, object]:
    observation = {
        "logical_search_queries": 1,
        "search_provider_calls": 1,
        "search_tool_calls": 1,
        "search_fetch_calls": 1,
        "search_fetch_failures": 0,
        "search_input_tokens": 1,
        "search_output_tokens": 2,
        "search_total_tokens": 3,
        "wall_milliseconds": 250,
    }
    continuation = {
        "model_calls": 1,
        "model_attempts": 1,
        "input_tokens": 2,
        "output_tokens": 3,
        "total_tokens": 5,
        "search_calls": 0,
        "search_failures": 0,
        "search_tool_calls": 0,
        "search_fetch_calls": 0,
        "search_fetch_failures": 0,
        "search_input_tokens": 0,
        "search_output_tokens": 0,
        "search_total_tokens": 0,
        "system_total_tokens": 5,
        "wall_seconds": 0.5,
    }
    total = dict(continuation)
    total.update(
        {
            "search_calls": 1,
            "search_tool_calls": 1,
            "search_fetch_calls": 1,
            "search_input_tokens": 1,
            "search_output_tokens": 2,
            "search_total_tokens": 3,
            "system_total_tokens": 8,
            "wall_seconds": 0.75,
        }
    )
    value: dict[str, object] = {
        "schema_version": 1,
        "role": "v24122_true_continuation_terminal_receipt",
        "branch_role": role,
        "source_checkpoint_sha256": digest("checkpoint"),
        "shadow_projection_sha256": digest("shadow"),
        "continuation_policy_sha256": digest("continuation"),
        "job_manifest_sha256": manifest_sha256,
        "action_observation_sha256": digest(["observation", replicate]),
        "branch_adapter_receipt_sha256": digest(["adapter", replicate]),
        "replicate_id": replicate,
        "provider_seed_supported": False,
        "provider_seed": None,
        "terminal_status": status,
        "failure_type": None if status == "completed" else "RuntimeError",
        "prediction_sha256": (
            digest(terminal_state["prediction"])
            if status == "completed"
            else None
        ),
        "terminal_state_sha256": object_sha256(terminal_state),
        "suffix_cost": {"total_tokens": 5},
        "process_model_delta": {"calls": 1},
        "process_search_delta": {"calls": 1},
        "cost_accounting_complete": True,
        "evaluator_read": False,
        "model_projection_used_as_label": False,
        "parent_v24121_terminal_receipt_sha256": digest(
            ["parent", replicate, role]
        ),
        "action_observation_cost": observation,
        "continuation_cost": continuation,
        "total_experiment_cost": total,
        "continuation_wall_measured": True,
        "all_cost_segments_complete": True,
    }
    value["receipt_payload_sha256"] = object_sha256(value)
    return value


def build_fixture(
    *,
    signed_gains: tuple[float, float, float] = (0.4, -0.2, 0.1),
    failed_action_replicate: int | None = None,
) -> dict[str, object]:
    bundle_identity: dict[str, object] = {
        "task_cluster_ref_sha256": digest("cluster"),
        "trajectory_ref_sha256": digest("trajectory"),
        "partition_role": "development_fit",
        "context": "anchor",
        "action": "resolve_anchor",
        "source_checkpoint_sha256": digest("checkpoint"),
        "shadow_projection_sha256": digest("shadow"),
        "visible_question_sha256": digest("visible-question"),
        "target_manifest_sha256": digest("target-manifest"),
        "continuation_policy_sha256": digest("continuation"),
    }
    bundle_sha = object_sha256(bundle_identity)
    bundle: dict[str, object] = {
        **bundle_identity,
        "bundle_sha256": bundle_sha,
        "opaque_id": "task_" + "1" * 24,
        "checkpoint_path": "checkpoints/checkpoint.json",
        "target_binding": {"kind": "anchor", "target_required": False},
        "target_binding_sha256": object_sha256(
            {"kind": "anchor", "target_required": False}
        ),
        "pre_action_features": {key: 0.0 for key in FEATURE_KEYS},
        "pre_action_features_sha256": object_sha256(
            {key: 0.0 for key in FEATURE_KEYS}
        ),
        "replicate_ids": list(REPLICATE_IDS),
        "branch_order_by_replicate": {
            str(replicate): ["no_op", "action"]
            for replicate in REPLICATE_IDS
        },
        "provider_seed_supported": False,
        "provider_seed": None,
        "eligible": True,
        "mapping_gold_category_evaluator_or_score_read": False,
    }
    manifest: dict[str, object] = {
        "artifact_version": 1,
        "role": "v24123_true_continuation_job_manifest",
        "label_blind": True,
        "capture_design_id": CAPTURE_DESIGN_ID,
        "target_manifest_sha256": digest("target-manifest"),
        "continuation_policy_sha256": digest("continuation"),
        "candidate_pipeline_version": "v2.41.0-test",
        "candidate_state_schema_version": EXPECTED_CANDIDATE_STATE_SCHEMA_VERSION,
        "candidate_runtime_config_sha256": digest("runtime-config"),
        "replicate_ids": list(REPLICATE_IDS),
        "provider_seed_supported": False,
        "provider_seed": None,
        "phase_order": [
            "development_fit_and_calibration",
            "freeze_audit_predictions",
            "development_audit",
        ],
        "bundles": [bundle],
        "excluded_targets": [],
        "eligible_bundle_count": 1,
        "excluded_target_count": 0,
        "task_cluster_is_statistical_unit": True,
        "subject_level_fallback_allowed": False,
        "mapping_gold_category_evaluator_or_score_read": False,
        "controller_or_training_authorized": False,
    }
    manifest["manifest_sha256"] = object_sha256(manifest)

    terminal_states: list[dict[str, object]] = []
    terminal_receipts: list[dict[str, object]] = []
    for replicate in REPLICATE_IDS:
        no_op_state = {
            "prediction": f"no-op-{replicate}",
            "shadow_risk_snapshots": [],
        }
        action_state = {
            "prediction": f"action-{replicate}",
            "shadow_risk_snapshots": [],
        }
        action_failed = failed_action_replicate == replicate
        for role, state, status in (
            ("no_op", no_op_state, "completed"),
            ("action", action_state, "failed" if action_failed else "completed"),
        ):
            terminal_states.append(
                {
                    "replicate_id": replicate,
                    "branch_role": role,
                    "terminal_state": state,
                }
            )
            terminal_receipts.append(
                terminal_receipt(
                    role,
                    replicate,
                    manifest_sha256=str(manifest["manifest_sha256"]),
                    terminal_state=state,
                    status=status,
                )
            )

    freeze: dict[str, object] = {
        "artifact_version": 1,
        "role": "v24123_bundle_prediction_freeze",
        "bundle_sha256": bundle_sha,
        "job_manifest_sha256": manifest["manifest_sha256"],
        "replicate_action_observation_sha256s": [
            digest(["observation", replicate]) for replicate in REPLICATE_IDS
        ],
        "replicate_branch_adapter_receipt_sha256s": [
            digest(["adapter", replicate]) for replicate in REPLICATE_IDS
        ],
        "terminal_receipt_sha256s": [
            value["receipt_payload_sha256"] for value in terminal_receipts
        ],
        "prediction_values_emitted": False,
        "evaluator_read": False,
        "created_at_unix": 1,
    }
    freeze["seal_sha256"] = object_sha256(freeze)
    freeze_sha = artifact_sha256(freeze)
    provenance: dict[str, object] = {
        "artifact_version": 1,
        "role": "v24123_post_prediction_freeze_evaluator_provenance",
        "bundle_sha256": bundle_sha,
        "prediction_freeze_sha256": freeze_sha,
        "all_six_predictions_frozen_before_evaluator_material_read": True,
        "live_provenance": {"closure": digest("evaluator-closure")},
        "mapping_gold_category_evaluator_or_score_read_scope": (
            "post_terminal_evaluator_join_only"
        ),
    }
    provenance["receipt_sha256"] = object_sha256(provenance)
    evaluated: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    states_by_key = {
        (row["replicate_id"], row["branch_role"]): row["terminal_state"]
        for row in terminal_states
    }
    terminals_by_key = {
        (row["replicate_id"], row["branch_role"]): row
        for row in terminal_receipts
    }
    for replicate, gain in zip(REPLICATE_IDS, signed_gains):
        no_op_loss = 0.6
        action_loss = 1.0 if failed_action_replicate == replicate else 0.6 - gain
        pair: dict[str, dict[str, object]] = {}
        for role, loss in (("no_op", no_op_loss), ("action", action_loss)):
            terminal = terminals_by_key[(replicate, role)]
            valid = terminal["terminal_status"] == "completed"
            metrics = (
                {
                    "score": 1.0 - loss,
                    "entity_acc": 1.0 - loss,
                    "f1_by_row": 1.0 - loss,
                    "f1_by_item": 1.0 - loss,
                    "column_f1": 1.0 - loss,
                }
                if valid
                else None
            )
            receipt = attach_v24122_terminal_evaluator(
                terminal,
                evaluator_protocol_sha256=digest("evaluator-protocol"),
                evaluator_artifact_sha256=(
                    digest(["evaluator-result", replicate, role])
                    if valid
                    else None
                ),
                evaluator_valid=valid,
                metrics=metrics,
                prediction_freeze_sha256=freeze_sha,
                evaluator_provenance_receipt_sha256=str(
                    provenance["receipt_sha256"]
                ),
                official_prediction_sha256=(
                    digest(["official-prediction", replicate, role])
                    if valid
                    else None
                ),
                evaluator_attempted=valid,
                evaluator_returncode=0 if valid else None,
                evaluator_run_config_sha256=(
                    digest(["run-config", replicate, role]) if valid else None
                ),
                evaluator_result_sha256=(
                    digest(["evaluator-result", replicate, role])
                    if valid
                    else None
                ),
            )
            evaluated.append(receipt)
            pair[role] = receipt
        records.append(
            contribution_record(
                pair["no_op"],
                pair["action"],
                no_op_terminal_state=states_by_key[(replicate, "no_op")],
                action_terminal_state=states_by_key[(replicate, "action")],
            )
        )
    aggregate = aggregate_replicate_contributions(records)
    aggregate.pop("aggregate_sha256")
    aggregate.update(
        {
            "bundle_sha256": bundle_sha,
            "task_cluster_ref_sha256": bundle["task_cluster_ref_sha256"],
            "partition_role": bundle["partition_role"],
            "context": bundle["context"],
            "action": bundle["action"],
            "job_manifest_sha256": manifest["manifest_sha256"],
            "replicate_action_observation_sha256s": [
                value["action_observation_sha256"] for value in records
            ],
            "replicate_branch_adapter_receipt_sha256s": [
                value["branch_adapter_receipt_sha256"] for value in records
            ],
        }
    )
    aggregate["aggregate_sha256"] = object_sha256(aggregate)
    return {
        "job_manifest": manifest,
        "bundle_sha256": bundle_sha,
        "evaluated_terminal_receipts": evaluated,
        "prediction_freeze": freeze,
        "evaluator_provenance_receipt": provenance,
        "terminal_state_records": terminal_states,
        "contribution_records": records,
        "replicate_aggregate": aggregate,
    }


def adapt(fixture: dict[str, object]) -> dict[str, object]:
    return adapt_v24123_source_graph(**fixture)  # type: ignore[arg-type]


class V24224CreditSourceAdapterTests(unittest.TestCase):
    def test_valid_six_receipt_graph_derives_verified_sign(self) -> None:
        result = adapt(build_fixture())
        validate_adapter_result(result)
        source = result["source_receipt"]
        verified = result["verified_contribution"]
        self.assertEqual(
            verified["replicate_signed_terminal_contributions"],
            [0.4, -0.2, 0.1],
        )
        self.assertEqual(verified["mean_signed_terminal_contribution"], 0.1)
        self.assertTrue(source["prediction_freeze_artifact_validated"])
        self.assertTrue(
            source["post_freeze_evaluator_provenance_binding_validated"]
        )
        self.assertFalse(
            source["evaluator_live_provenance_independently_replayed"]
        )
        self.assertFalse(
            result["semantic_or_distributional_ood_independently_assessed"]
        )
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(CREDIT_TRAINING_AUTHORIZED)

    def test_receipt_state_contribution_and_aggregate_tamper_fail_closed(self) -> None:
        cases = []
        receipt = build_fixture()
        receipt["evaluated_terminal_receipts"][0]["terminal_task_loss"] = 0.1
        cases.append(receipt)
        state = build_fixture()
        state["terminal_state_records"][0]["terminal_state"]["prediction"] = "x"
        cases.append(state)
        contribution = build_fixture()
        contribution["contribution_records"][0]["signed_task_contribution"] = -0.4
        reseal(contribution["contribution_records"][0], "record_sha256")
        cases.append(contribution)
        aggregate = build_fixture()
        aggregate["replicate_aggregate"]["mean_signed_task_contribution"] = -0.1
        reseal(aggregate["replicate_aggregate"], "aggregate_sha256")
        cases.append(aggregate)
        for fixture in cases:
            with self.subTest(kind=len(cases)):
                with self.assertRaises(ValueError):
                    adapt(fixture)

    def test_manifest_bundle_replicate_protocol_and_freeze_mismatch_fail(self) -> None:
        mutations = []
        manifest = build_fixture()
        manifest["job_manifest"]["unexpected"] = True
        mutations.append(manifest)
        bundle = build_fixture()
        bundle["bundle_sha256"] = digest("absent-bundle")
        mutations.append(bundle)
        replicate = build_fixture()
        replicate["evaluated_terminal_receipts"][0]["replicate_id"] = 2
        reseal(
            replicate["evaluated_terminal_receipts"][0],
            "receipt_payload_sha256",
        )
        mutations.append(replicate)
        protocol = build_fixture()
        protocol["evaluated_terminal_receipts"][0][
            "evaluator_protocol_sha256"
        ] = digest("other-protocol")
        reseal(
            protocol["evaluated_terminal_receipts"][0],
            "receipt_payload_sha256",
        )
        mutations.append(protocol)
        freeze = build_fixture()
        freeze["prediction_freeze"]["terminal_receipt_sha256s"].reverse()
        reseal(freeze["prediction_freeze"], "seal_sha256")
        mutations.append(freeze)
        provenance = build_fixture()
        provenance["evaluator_provenance_receipt"][
            "prediction_freeze_sha256"
        ] = digest("other-freeze")
        reseal(
            provenance["evaluator_provenance_receipt"], "receipt_sha256"
        )
        mutations.append(provenance)
        for fixture in mutations:
            with self.subTest(kind=len(mutations)):
                with self.assertRaises(ValueError):
                    adapt(fixture)

    def test_exact_schema_rejects_resealed_manifest_and_bundle_extras(self) -> None:
        manifest = build_fixture()
        manifest["job_manifest"]["unexpected"] = False
        reseal(manifest["job_manifest"], "manifest_sha256")
        bundle = build_fixture()
        bundle["job_manifest"]["bundles"][0]["unexpected"] = False
        reseal(bundle["job_manifest"], "manifest_sha256")
        for fixture in (manifest, bundle):
            with self.assertRaisesRegex(ValueError, "schema|ineligible"):
                adapt(fixture)

    def test_missing_or_duplicate_receipt_fails(self) -> None:
        missing = build_fixture()
        missing["evaluated_terminal_receipts"].pop()
        duplicate = build_fixture()
        duplicate["evaluated_terminal_receipts"][-1] = copy.deepcopy(
            duplicate["evaluated_terminal_receipts"][0]
        )
        for fixture in (missing, duplicate):
            with self.assertRaises(ValueError):
                adapt(fixture)

    def test_terminal_state_evaluator_metadata_is_rejected_even_if_resealed(self) -> None:
        fixture = build_fixture()
        state = fixture["terminal_state_records"][0]["terminal_state"]
        state["question_type"] = "hidden-label"
        state_sha = object_sha256(state)
        receipt = fixture["evaluated_terminal_receipts"][0]
        receipt["terminal_state_sha256"] = state_sha
        parent = copy.deepcopy(receipt)
        parent_hash = parent.pop("parent_v24122_terminal_receipt_sha256")
        for key in (
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
        ):
            parent.pop(key, None)
        parent["role"] = "v24122_true_continuation_terminal_receipt"
        parent["evaluator_read"] = False
        reseal(parent, "receipt_payload_sha256")
        receipt["parent_v24122_terminal_receipt_sha256"] = parent[
            "receipt_payload_sha256"
        ]
        freeze = fixture["prediction_freeze"]
        freeze["terminal_receipt_sha256s"][0] = parent[
            "receipt_payload_sha256"
        ]
        reseal(freeze, "seal_sha256")
        freeze_sha = artifact_sha256(freeze)
        provenance = fixture["evaluator_provenance_receipt"]
        provenance["prediction_freeze_sha256"] = freeze_sha
        reseal(provenance, "receipt_sha256")
        for value in fixture["evaluated_terminal_receipts"]:
            value["prediction_freeze_sha256"] = freeze_sha
            value["evaluator_provenance_receipt_sha256"] = provenance[
                "receipt_sha256"
            ]
            reseal(value, "receipt_payload_sha256")
        # The exact V2.41.23 receipt remains mechanically valid, but V2.42.24
        # refuses evaluator-only keys in state content it explicitly opens.
        with self.assertRaisesRegex(ValueError, "evaluator-only metadata"):
            adapt(fixture)

    def test_resealed_contribution_sign_flip_is_rejected(self) -> None:
        fixture = build_fixture()
        record = fixture["contribution_records"][0]
        record["signed_task_contribution"] = -record[
            "signed_task_contribution"
        ]
        reseal(record, "record_sha256")
        aggregate = aggregate_replicate_contributions(
            fixture["contribution_records"]
        )
        aggregate.pop("aggregate_sha256")
        supplied = fixture["replicate_aggregate"]
        for key in (
            "bundle_sha256",
            "task_cluster_ref_sha256",
            "partition_role",
            "context",
            "action",
            "job_manifest_sha256",
            "replicate_action_observation_sha256s",
            "replicate_branch_adapter_receipt_sha256s",
        ):
            aggregate[key] = supplied[key]
        aggregate["aggregate_sha256"] = object_sha256(aggregate)
        fixture["replicate_aggregate"] = aggregate
        with self.assertRaisesRegex(ValueError, "receipt-graph replay"):
            adapt(fixture)

    def test_failed_branch_uses_conservative_unit_loss(self) -> None:
        fixture = build_fixture(
            signed_gains=(0.4, -0.4, 0.1), failed_action_replicate=1
        )
        result = adapt(fixture)
        self.assertEqual(
            result["verified_contribution"][
                "replicate_signed_terminal_contributions"
            ],
            [0.4, -0.4, 0.1],
        )
        failed = next(
            value
            for value in fixture["evaluated_terminal_receipts"]
            if value["replicate_id"] == 1 and value["branch_role"] == "action"
        )
        self.assertEqual(failed["terminal_task_loss"], 1.0)
        self.assertFalse(failed["evaluator_valid"])


if __name__ == "__main__":
    unittest.main()
