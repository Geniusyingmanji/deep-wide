from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24255_finite_depth_dynamic_voc import (  # noqa: E402
    evaluate_voc_policies,
)
from deepwide_agent.v24256_dynamic_voc_calibration import (  # noqa: E402
    CALIBRATION_ROLE,
    FIT_ROLE,
    build_calibration_protocol,
    build_stop_loss_sample,
    build_topology,
    build_transition_sample,
    fit_dynamic_voc_source_package,
    object_sha256,
    reject_privileged_runtime_metadata,
    validate_dynamic_voc_source_package,
    validate_topology,
)


def ref(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class V24256DynamicVocCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ref("state:root")
        self.left = ref("state:left")
        self.right = ref("state:right")
        self.bridge = ref("state:bridge")
        self.terminal = ref("state:terminal")
        self.choose = ref("action:choose")
        self.open_bridge = ref("action:open-bridge")
        self.finish = ref("action:finish")
        self.fit_clusters = [ref(f"fit:{index}") for index in range(4)]
        self.calibration_clusters = [
            ref(f"calibration:{index}") for index in range(4)
        ]
        self.topology = build_topology(
            abstraction_manifest_sha256=ref("abstraction"),
            root_state_ref_sha256=self.root,
            max_depth=2,
            max_budget=2,
            states=[
                {
                    "state_ref_sha256": self.root,
                    "belief_entropy": 0.9,
                    "actions": [
                        {
                            "action_ref_sha256": self.choose,
                            "cost": 1,
                            "allowed_next_state_ref_sha256s": [
                                self.left,
                                self.right,
                            ],
                        },
                        {
                            "action_ref_sha256": self.open_bridge,
                            "cost": 1,
                            "allowed_next_state_ref_sha256s": [
                                self.bridge
                            ],
                        },
                    ],
                },
                {
                    "state_ref_sha256": self.left,
                    "belief_entropy": 0.1,
                    "actions": [],
                },
                {
                    "state_ref_sha256": self.right,
                    "belief_entropy": 0.8,
                    "actions": [],
                },
                {
                    "state_ref_sha256": self.bridge,
                    "belief_entropy": 0.9,
                    "actions": [
                        {
                            "action_ref_sha256": self.finish,
                            "cost": 1,
                            "allowed_next_state_ref_sha256s": [
                                self.terminal
                            ],
                        }
                    ],
                },
                {
                    "state_ref_sha256": self.terminal,
                    "belief_entropy": 0.9,
                    "actions": [],
                },
            ],
        )
        self.protocol = build_calibration_protocol(
            topology=self.topology,
            fit_partition_manifest_sha256=ref("fit-partition"),
            calibration_partition_manifest_sha256=ref(
                "calibration-partition"
            ),
            fit_task_cluster_ref_sha256s=sorted(self.fit_clusters),
            calibration_task_cluster_ref_sha256s=sorted(
                self.calibration_clusters
            ),
            dirichlet_alpha_per_successor=1.0,
            minimum_fit_transition_clusters_per_action=2,
            minimum_calibration_transition_clusters_per_action=2,
            maximum_normalized_multiclass_brier=0.3,
            minimum_fit_stop_clusters_per_state=2,
            minimum_calibration_stop_clusters_per_state=2,
            maximum_stop_loss_mae=0.15,
        )
        self.assertEqual(
            self.topology["belief_entropy_role"],
            "predeclared_diagnostic_feature_not_calibrated_terminal_utility",
        )

    def transition(
        self,
        *,
        partition: str,
        cluster: str,
        action_ref: str,
        next_state: str,
        ordinal: str,
    ) -> dict[str, object]:
        sources = {
            self.choose: self.root,
            self.open_bridge: self.root,
            self.finish: self.bridge,
        }
        return build_transition_sample(
            topology=self.topology,
            protocol=self.protocol,
            partition_role=partition,
            task_cluster_ref_sha256=cluster,
            source_state_ref_sha256=sources[action_ref],
            action_ref_sha256=action_ref,
            next_state_ref_sha256=next_state,
            pre_state_projection_sha256=ref(f"pre:{ordinal}"),
            post_state_projection_sha256=ref(f"post:{ordinal}"),
            action_observation_receipt_sha256=ref(
                f"observation:{ordinal}"
            ),
            state_transition_receipt_sha256=ref(
                f"transition:{ordinal}"
            ),
        )

    def stop(
        self,
        *,
        partition: str,
        cluster: str,
        state_ref: str,
        loss: float,
        ordinal: str,
        valid: bool = True,
    ) -> dict[str, object]:
        return build_stop_loss_sample(
            topology=self.topology,
            protocol=self.protocol,
            partition_role=partition,
            task_cluster_ref_sha256=cluster,
            state_ref_sha256=state_ref,
            state_projection_sha256=ref(f"state-projection:{ordinal}"),
            prediction_freeze_sha256=ref(f"freeze:{ordinal}"),
            terminal_receipt_sha256=ref(f"terminal-receipt:{ordinal}"),
            evaluator_protocol_sha256=ref("evaluator-protocol"),
            evaluator_artifact_sha256=(
                ref(f"evaluator-artifact:{ordinal}") if valid else None
            ),
            terminal_status="completed" if valid else "failed",
            evaluator_valid=valid,
            terminal_loss=loss if valid else 1.0,
        )

    def complete_samples(
        self,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        transitions: list[dict[str, object]] = []
        stops: list[dict[str, object]] = []
        for partition, clusters in (
            (FIT_ROLE, self.fit_clusters),
            (CALIBRATION_ROLE, self.calibration_clusters),
        ):
            for index, cluster in enumerate(clusters):
                prefix = f"{partition}:{index}"
                transitions.extend(
                    [
                        self.transition(
                            partition=partition,
                            cluster=cluster,
                            action_ref=self.choose,
                            next_state=(
                                self.left if index < 3 else self.right
                            ),
                            ordinal=f"{prefix}:choose",
                        ),
                        self.transition(
                            partition=partition,
                            cluster=cluster,
                            action_ref=self.open_bridge,
                            next_state=self.bridge,
                            ordinal=f"{prefix}:bridge",
                        ),
                        self.transition(
                            partition=partition,
                            cluster=cluster,
                            action_ref=self.finish,
                            next_state=self.terminal,
                            ordinal=f"{prefix}:finish",
                        ),
                    ]
                )
                losses = {
                    self.root: 0.6,
                    self.left: 0.58,
                    self.right: 0.3,
                    self.bridge: 0.6,
                    self.terminal: 0.1,
                }
                for state_ref, loss in losses.items():
                    stops.append(
                        self.stop(
                            partition=partition,
                            cluster=cluster,
                            state_ref=state_ref,
                            loss=loss,
                            ordinal=f"{prefix}:stop:{state_ref}",
                        )
                    )
        return transitions, stops

    def test_complete_cross_fit_package_drives_v24255_without_runtime_authority(
        self,
    ) -> None:
        transitions, stops = self.complete_samples()
        package = fit_dynamic_voc_source_package(
            topology=self.topology,
            protocol=self.protocol,
            transition_samples=transitions,
            stop_samples=stops,
        )
        self.assertTrue(package["calibration_complete"])
        self.assertTrue(
            package["v24255_transition_model"][
                "transition_calibration_complete"
            ]
        )
        report = package["calibration_report"]
        self.assertEqual(report["blockers"], [])
        self.assertTrue(
            all(row["gate_passed"] for row in report["action_calibration"])
        )
        self.assertTrue(
            all(
                row["gate_passed"]
                for row in report["state_stop_loss_calibration"]
            )
        )
        choose = next(
            row
            for row in report["action_calibration"]
            if row["action_ref_sha256"] == self.choose
        )
        self.assertEqual(
            [
                row["probability"]
                for row in choose["fitted_transition_probabilities"]
            ],
            [0.666666666667, 0.333333333333],
        )
        receipt = evaluate_voc_policies(
            model=package["v24255_transition_model"],
            expected_transition_model_sha256=package[
                "v24255_transition_model_sha256"
            ],
            requested_depth=2,
            available_budget=2,
        )
        self.assertEqual(
            receipt["policies"]["pure_information_gain"][
                "selected_action_ref_sha256"
            ],
            self.choose,
        )
        self.assertEqual(
            receipt["policies"]["myopic_terminal_loss_voc"][
                "selected_action_ref_sha256"
            ],
            self.choose,
        )
        self.assertEqual(
            receipt["policies"]["finite_depth_dynamic_voc"][
                "selected_action_ref_sha256"
            ],
            self.open_bridge,
        )
        for field in (
            "production_package_authorized",
            "runtime_forward_authorized",
            "credit_training_authorized",
            "benchmark_evaluator_launch_authorized",
            "leaderboard_or_sota_claim_authorized",
        ):
            self.assertFalse(package[field], field)

    def test_missing_support_emits_abstaining_model_not_uniform_ready_fallback(
        self,
    ) -> None:
        transitions, stops = self.complete_samples()
        transitions = [
            sample
            for sample in transitions
            if not (
                sample["partition_role"] == CALIBRATION_ROLE
                and sample["action_ref_sha256"] == self.finish
            )
        ]
        package = fit_dynamic_voc_source_package(
            topology=self.topology,
            protocol=self.protocol,
            transition_samples=transitions,
            stop_samples=stops,
        )
        self.assertFalse(package["calibration_complete"])
        self.assertTrue(
            any(
                blocker.startswith("transition_calibration_support:")
                for blocker in package["calibration_report"]["blockers"]
            )
        )
        model = package["v24255_transition_model"]
        self.assertFalse(model["transition_calibration_complete"])
        receipt = evaluate_voc_policies(
            model=model,
            expected_transition_model_sha256=model[
                "transition_model_sha256"
            ],
            requested_depth=2,
            available_budget=2,
        )
        self.assertTrue(
            all(
                row["decision_kind"] == "abstain"
                for row in receipt["policies"].values()
            )
        )

    def test_calibration_outcomes_gate_but_do_not_refit_parameters(self) -> None:
        transitions, stops = self.complete_samples()
        original = fit_dynamic_voc_source_package(
            topology=self.topology,
            protocol=self.protocol,
            transition_samples=transitions,
            stop_samples=stops,
        )
        altered_transitions = [
            (
                self.transition(
                    partition=CALIBRATION_ROLE,
                    cluster=sample["task_cluster_ref_sha256"],
                    action_ref=self.choose,
                    next_state=self.right,
                    ordinal=f"altered:{index}",
                )
                if sample["partition_role"] == CALIBRATION_ROLE
                and sample["action_ref_sha256"] == self.choose
                else sample
            )
            for index, sample in enumerate(transitions)
        ]
        altered_stops = [
            (
                self.stop(
                    partition=CALIBRATION_ROLE,
                    cluster=sample["task_cluster_ref_sha256"],
                    state_ref=sample["state_ref_sha256"],
                    loss=min(1.0, sample["terminal_loss"] + 0.5),
                    ordinal=f"altered-stop:{index}",
                )
                if sample["partition_role"] == CALIBRATION_ROLE
                else sample
            )
            for index, sample in enumerate(stops)
        ]
        altered = fit_dynamic_voc_source_package(
            topology=self.topology,
            protocol=self.protocol,
            transition_samples=altered_transitions,
            stop_samples=altered_stops,
        )
        def fitted(package: dict[str, object]) -> tuple[object, object]:
            report = package["calibration_report"]
            return (
                [
                    (
                        row["action_ref_sha256"],
                        row["fitted_transition_probabilities"],
                    )
                    for row in report["action_calibration"]
                ],
                [
                    (
                        row["state_ref_sha256"],
                        row["fitted_stop_terminal_loss"],
                    )
                    for row in report["state_stop_loss_calibration"]
                ],
            )
        self.assertEqual(fitted(original), fitted(altered))
        self.assertTrue(original["calibration_complete"])
        self.assertFalse(altered["calibration_complete"])

    def test_replicates_within_one_cluster_do_not_increase_statistical_weight(
        self,
    ) -> None:
        transitions, stops = self.complete_samples()
        baseline = fit_dynamic_voc_source_package(
            topology=self.topology,
            protocol=self.protocol,
            transition_samples=transitions,
            stop_samples=stops,
        )
        duplicated = [
            self.transition(
                partition=FIT_ROLE,
                cluster=self.fit_clusters[0],
                action_ref=self.choose,
                next_state=self.left,
                ordinal=f"duplicate:{index}",
            )
            for index in range(20)
        ]
        duplicated_stops = [
            self.stop(
                partition=FIT_ROLE,
                cluster=self.fit_clusters[0],
                state_ref=self.root,
                loss=0.6,
                ordinal=f"duplicate-stop:{index}",
            )
            for index in range(20)
        ]
        repeated = fit_dynamic_voc_source_package(
            topology=self.topology,
            protocol=self.protocol,
            transition_samples=[*transitions, *duplicated],
            stop_samples=[*stops, *duplicated_stops],
        )
        def row(package: dict[str, object]) -> tuple[object, object, object]:
            report = package["calibration_report"]
            choose = next(
                item
                for item in report["action_calibration"]
                if item["action_ref_sha256"] == self.choose
            )
            root = next(
                item
                for item in report["state_stop_loss_calibration"]
                if item["state_ref_sha256"] == self.root
            )
            return (
                choose["fit_task_cluster_count"],
                choose["fitted_transition_probabilities"],
                root["fitted_stop_terminal_loss"],
            )
        self.assertEqual(row(baseline), row(repeated))

    def test_partition_privilege_and_evaluator_contracts_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            build_calibration_protocol(
                topology=self.topology,
                fit_partition_manifest_sha256=ref("fit-x"),
                calibration_partition_manifest_sha256=ref("cal-x"),
                fit_task_cluster_ref_sha256s=sorted(self.fit_clusters),
                calibration_task_cluster_ref_sha256s=sorted(
                    [*self.calibration_clusters[:-1], self.fit_clusters[0]]
                ),
                dirichlet_alpha_per_successor=1.0,
                minimum_fit_transition_clusters_per_action=2,
                minimum_calibration_transition_clusters_per_action=2,
                maximum_normalized_multiclass_brier=0.3,
                minimum_fit_stop_clusters_per_state=2,
                minimum_calibration_stop_clusters_per_state=2,
                maximum_stop_loss_mae=0.15,
            )
        with self.assertRaisesRegex(ValueError, "partition rejected"):
            build_transition_sample(
                topology=self.topology,
                protocol=self.protocol,
                partition_role="benchmark_test",
                task_cluster_ref_sha256=self.fit_clusters[0],
                source_state_ref_sha256=self.root,
                action_ref_sha256=self.choose,
                next_state_ref_sha256=self.left,
                pre_state_projection_sha256=ref("pre"),
                post_state_projection_sha256=ref("post"),
                action_observation_receipt_sha256=ref("observation"),
                state_transition_receipt_sha256=ref("transition"),
            )
        with self.assertRaisesRegex(ValueError, "binding"):
            build_stop_loss_sample(
                topology=self.topology,
                protocol=self.protocol,
                partition_role=FIT_ROLE,
                task_cluster_ref_sha256=self.fit_clusters[0],
                state_ref_sha256=self.root,
                state_projection_sha256=ref("invalid-state"),
                prediction_freeze_sha256=ref("invalid-freeze"),
                terminal_receipt_sha256=ref("invalid-terminal"),
                evaluator_protocol_sha256=ref("evaluator-protocol"),
                evaluator_artifact_sha256=None,
                terminal_status="failed",
                evaluator_valid=False,
                terminal_loss=0.5,
            )
        for payload in (
            {"category": "hidden"},
            {"outer": [{"question_type": "hidden"}]},
            {"outer": {"ground-truth": "hidden"}},
            {"outer": {"evaluator_payload": {"score": 1}}},
            {"raw_observation": "hidden"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "privileged"):
                    reject_privileged_runtime_metadata(payload)

    def test_topology_and_source_receipt_reuse_fail_closed(self) -> None:
        cycle = copy.deepcopy(self.topology)
        cycle["states"][4]["actions"] = [
            {
                "action_ref_sha256": ref("action:cycle"),
                "cost": 1,
                "allowed_next_state_ref_sha256s": [self.root],
            }
        ]
        cycle["topology_sha256"] = object_sha256(
            {
                key: value
                for key, value in cycle.items()
                if key != "topology_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_topology(cycle)

        transitions, stops = self.complete_samples()
        duplicated = copy.deepcopy(transitions[0])
        duplicated["sample_sha256"] = object_sha256(
            {
                key: value
                for key, value in duplicated.items()
                if key != "sample_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "duplicate sample"):
            fit_dynamic_voc_source_package(
                topology=self.topology,
                protocol=self.protocol,
                transition_samples=[*transitions, duplicated],
                stop_samples=stops,
            )
        reused = copy.deepcopy(transitions[1])
        reused["state_transition_receipt_sha256"] = transitions[0][
            "state_transition_receipt_sha256"
        ]
        reused["sample_sha256"] = object_sha256(
            {
                key: value
                for key, value in reused.items()
                if key != "sample_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "source receipt reuse"):
            fit_dynamic_voc_source_package(
                topology=self.topology,
                protocol=self.protocol,
                transition_samples=[transitions[0], reused],
                stop_samples=[],
            )

    def test_package_replay_and_bool_int_tamper_are_rejected(self) -> None:
        transitions, stops = self.complete_samples()
        package = fit_dynamic_voc_source_package(
            topology=self.topology,
            protocol=self.protocol,
            transition_samples=transitions,
            stop_samples=stops,
        )
        self.assertEqual(
            validate_dynamic_voc_source_package(
                package,
                topology=self.topology,
                protocol=self.protocol,
                transition_samples=transitions,
                stop_samples=stops,
            ),
            package,
        )
        tampered = copy.deepcopy(package)
        tampered["calibration_report"]["fit_task_cluster_count"] = True
        tampered["calibration_report"]["report_sha256"] = object_sha256(
            {
                key: value
                for key, value in tampered["calibration_report"].items()
                if key != "report_sha256"
            }
        )
        tampered["calibration_report_sha256"] = tampered[
            "calibration_report"
        ]["report_sha256"]
        tampered["package_sha256"] = object_sha256(
            {
                key: value
                for key, value in tampered.items()
                if key != "package_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "replay"):
            validate_dynamic_voc_source_package(
                tampered,
                topology=self.topology,
                protocol=self.protocol,
                transition_samples=transitions,
                stop_samples=stops,
            )

        protocol = copy.deepcopy(self.protocol)
        protocol["fit_task_cluster_count"] = True
        protocol["protocol_sha256"] = object_sha256(
            {
                key: value
                for key, value in protocol.items()
                if key != "protocol_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "fit task cluster count"):
            fit_dynamic_voc_source_package(
                topology=self.topology,
                protocol=protocol,
                transition_samples=transitions,
                stop_samples=stops,
            )

        with self.assertRaisesRegex(ValueError, "duplicate sample"):
            validate_dynamic_voc_source_package(
                package,
                topology=self.topology,
                protocol=self.protocol,
                transition_samples=[*transitions, transitions[0]],
                stop_samples=stops,
            )


if __name__ == "__main__":
    unittest.main()
