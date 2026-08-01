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

from deepwide_agent.v24223_sign_preserving_credit import object_sha256  # noqa: E402
from deepwide_agent.v24227_credit_commit_reveal import (  # noqa: E402
    _build_launch_receipt,
    _build_outer_reservation_receipt,
    _build_prediction_commitment,
    build_commit_reveal_protocol,
)
from deepwide_agent.v24228_challenge_bound_outer_graph import (  # noqa: E402
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
    FORMAL_GATE2B_EVALUATION_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    STORE_API_EXECUTION_INDEPENDENTLY_ATTESTED,
    build_challenge_bound_outer_pair,
    build_challenge_contribution_record,
    build_challenge_evaluated_terminal,
    build_challenge_evaluator_provenance,
    build_challenge_execution_request,
    build_challenge_graph_protocol,
    build_challenge_prediction_freeze,
    build_challenge_replicate_aggregate,
    build_unsigned_executor_declaration,
    validate_challenge_bound_outer_pair,
    validate_challenge_contribution_record,
    validate_challenge_evaluated_terminal,
    validate_challenge_evaluator_provenance,
    validate_challenge_execution_request,
    validate_challenge_graph_protocol,
    validate_challenge_prediction_freeze,
    validate_challenge_replicate_aggregate,
    validate_unsigned_executor_declaration,
)
from tests.test_v24226_credit_outer_target_firewall import (  # noqa: E402
    components,
    digest,
    pair,
)


def reseal(value: dict[str, object], field: str) -> None:
    value.pop(field, None)
    value[field] = object_sha256(value)


class V24228ChallengeBoundOuterGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.values = components()
        cls.legacy_pair = pair(cls.values)
        cls.sequence_protocol = build_commit_reveal_protocol(
            outer_target_protocol=cls.values["protocol"],  # type: ignore[arg-type]
            sequence_namespace_sha256=digest("1"),
            coordinator_contract_sha256=digest("2"),
            launch_policy_sha256=digest("3"),
        )
        cls.commitment = _build_prediction_commitment(
            protocol=cls.sequence_protocol,
            prediction_freeze=cls.values["freeze"],  # type: ignore[arg-type]
            commit_nonce_sha256=digest("4"),
            outer_output_namespace_sha256=digest("5"),
            outer_seed_schedule_sha256=digest("6"),
            outer_execution_contract_sha256=digest("7"),
            outer_evaluator_protocol_sha256=cls.values["outer_fixture"][  # type: ignore[index]
                "evaluated_terminal_receipts"
            ][0]["evaluator_protocol_sha256"],
        )
        cls.launch = _build_launch_receipt(
            protocol=cls.sequence_protocol,
            commitment=cls.commitment,
            launch_request_sha256=digest("9"),
            launch_challenge_sha256=digest("0"),
        )
        cls.reservation = _build_outer_reservation_receipt(
            protocol=cls.sequence_protocol,
            launch=cls.launch,
            reservation_nonce_sha256=digest("a"),
        )
        cls.protocol = build_challenge_graph_protocol(
            sequence_protocol=cls.sequence_protocol,
            graph_namespace_sha256=digest("b"),
            outer_execution_contract_sha256=digest("7"),
            expected_attestor_trust_domain_sha256=digest("c"),
            attestation_policy_sha256=digest("d"),
        )

    def build_graph(self) -> dict[str, object]:
        fixture = self.values["outer_fixture"]
        bundle_sha = fixture["bundle_sha256"]  # type: ignore[index]
        request = build_challenge_execution_request(
            protocol=self.protocol,
            commitment=self.commitment,
            launch=self.launch,
            reservation=self.reservation,
            outer_job_manifest=fixture["job_manifest"],  # type: ignore[index,arg-type]
            outer_bundle_sha256=bundle_sha,
            executor_instance_sha256=digest("e"),
            request_nonce_sha256=digest("f"),
        )
        freeze = build_challenge_prediction_freeze(
            protocol=self.protocol,
            request=request,
            legacy_prediction_freeze=fixture["prediction_freeze"],  # type: ignore[index,arg-type]
        )
        attestation = build_unsigned_executor_declaration(
            protocol=self.protocol,
            request=request,
            challenge_prediction_freeze=freeze,
            execution_trace_sha256=digest("1"),
            execution_result_nonce_sha256=digest("2"),
            attestor_trust_domain_sha256=digest("c"),
        )
        evaluator = build_challenge_evaluator_provenance(
            protocol=self.protocol,
            request=request,
            challenge_prediction_freeze=freeze,
            executor_attestation=attestation,
            legacy_evaluator_provenance=fixture["evaluator_provenance_receipt"],  # type: ignore[index,arg-type]
        )
        terminals = [
            build_challenge_evaluated_terminal(
                protocol=self.protocol,
                request=request,
                challenge_prediction_freeze=freeze,
                executor_attestation=attestation,
                challenge_evaluator_provenance=evaluator,
                legacy_evaluated_terminal_receipt=row,
            )
            for row in fixture["evaluated_terminal_receipts"]  # type: ignore[index,union-attr]
        ]
        terminal_index = {
            (row["replicate_id"], row["branch_role"]): row for row in terminals
        }
        contributions = [
            build_challenge_contribution_record(
                protocol=self.protocol,
                request=request,
                executor_attestation=attestation,
                challenge_evaluator_provenance=evaluator,
                no_op_terminal=terminal_index[(record["replicate_id"], "no_op")],
                action_terminal=terminal_index[(record["replicate_id"], "action")],
                legacy_contribution_record=record,
            )
            for record in fixture["contribution_records"]  # type: ignore[index,union-attr]
        ]
        aggregate = build_challenge_replicate_aggregate(
            protocol=self.protocol,
            request=request,
            executor_attestation=attestation,
            challenge_evaluator_provenance=evaluator,
            challenge_contributions=contributions,
            legacy_replicate_aggregate=fixture["replicate_aggregate"],  # type: ignore[index,arg-type]
        )
        result = build_challenge_bound_outer_pair(
            protocol=self.protocol,
            sequence_protocol=self.sequence_protocol,
            commitment=self.commitment,
            launch=self.launch,
            reservation=self.reservation,
            request=request,
            challenge_prediction_freeze=freeze,
            executor_attestation=attestation,
            challenge_evaluator_provenance=evaluator,
            challenge_terminals=terminals,
            challenge_contributions=contributions,
            challenge_aggregate=aggregate,
            legacy_outer_pair=self.legacy_pair,
            outer_job_manifest=fixture["job_manifest"],  # type: ignore[index,arg-type]
            outer_bundle_sha256=bundle_sha,
            outer_evaluated_terminal_receipts=fixture["evaluated_terminal_receipts"],  # type: ignore[index,arg-type]
            outer_prediction_freeze=fixture["prediction_freeze"],  # type: ignore[index,arg-type]
            outer_evaluator_provenance_receipt=fixture["evaluator_provenance_receipt"],  # type: ignore[index,arg-type]
            outer_terminal_state_records=fixture["terminal_state_records"],  # type: ignore[index,arg-type]
            outer_contribution_records=fixture["contribution_records"],  # type: ignore[index,arg-type]
            outer_replicate_aggregate=fixture["replicate_aggregate"],  # type: ignore[index,arg-type]
            outer_adapter_result=self.values["outer_result"],  # type: ignore[arg-type]
        )
        return {
            "request": request,
            "freeze": freeze,
            "attestation": attestation,
            "evaluator": evaluator,
            "terminals": terminals,
            "contributions": contributions,
            "aggregate": aggregate,
            "pair": result,
        }

    def validate_graph(self, graph: dict[str, object]) -> None:
        validate_challenge_bound_outer_pair(
            graph["pair"],
            protocol=self.protocol,
            sequence_protocol=self.sequence_protocol,
            commitment=self.commitment,
            launch=self.launch,
            reservation=self.reservation,
            request=graph["request"],  # type: ignore[arg-type]
            challenge_prediction_freeze=graph["freeze"],  # type: ignore[arg-type]
            executor_attestation=graph["attestation"],  # type: ignore[arg-type]
            challenge_evaluator_provenance=graph["evaluator"],  # type: ignore[arg-type]
            challenge_terminals=graph["terminals"],  # type: ignore[arg-type]
            challenge_contributions=graph["contributions"],  # type: ignore[arg-type]
            challenge_aggregate=graph["aggregate"],  # type: ignore[arg-type]
        )

    def test_complete_graph_binds_challenge_at_every_layer_and_authorizes_nothing(self) -> None:
        graph = self.build_graph()
        self.validate_graph(graph)
        pair_value = graph["pair"]
        self.assertTrue(pair_value["launch_challenge_bound_in_every_envelope_layer"])
        self.assertFalse(pair_value["challenge_only_at_top_level"])
        for artifact in (
            graph["request"],
            graph["freeze"],
            graph["attestation"],
            graph["evaluator"],
            *graph["terminals"],
            *graph["contributions"],
            graph["aggregate"],
            graph["pair"],
        ):
            self.assertEqual(
                artifact["launch_challenge_sha256"],
                self.launch["launch_challenge_sha256"],
            )
            for field in (
                "production_package_authorized",
                "credit_training_authorized",
                "gate2b_pass_authorized",
                "outer_campaign_execution_authorized",
                "benchmark_forward_or_evaluator_authorized",
            ):
                self.assertFalse(artifact[field], field)
        self.assertEqual(
            (
                PRODUCTION_PACKAGE_AUTHORIZED,
                CREDIT_TRAINING_AUTHORIZED,
                GATE2B_PASS_AUTHORIZED,
                OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
                BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
                FORMAL_GATE2B_EVALUATION_AUTHORIZED,
                EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
                STORE_API_EXECUTION_INDEPENDENTLY_ATTESTED,
            ),
            (False,) * 8,
        )

    def test_compatibility_envelope_discloses_precomputation_and_attestation_limits(self) -> None:
        graph = self.build_graph()
        attestation = graph["attestation"]
        pair_value = graph["pair"]
        self.assertEqual(attestation["signature_scheme"], "none")
        self.assertIsNone(attestation["detached_signature"])
        self.assertTrue(attestation["historical_payload_after_wrapping_possible"])
        self.assertFalse(attestation["executor_challenge_consumption_independently_verified"])
        self.assertFalse(pair_value["legacy_payloads_are_challenge_native"])
        self.assertFalse(pair_value["native_executor_consumed_challenge_independently_proven"])
        self.assertFalse(pair_value["store_api_execution_independently_attested"])
        self.assertFalse(pair_value["external_target_precomputation_excluded"])
        self.assertFalse(pair_value["formal_gate2b_evaluation_authorized"])

    def test_precomputed_graph_cannot_be_rewrapped_under_swapped_challenge(self) -> None:
        graph = self.build_graph()
        swapped_launch = copy.deepcopy(self.launch)
        swapped_launch["launch_challenge_sha256"] = digest("3")
        reseal(swapped_launch, "launch_receipt_sha256")
        with self.assertRaisesRegex(ValueError, "launch binding"):
            validate_challenge_execution_request(
                graph["request"],
                protocol=self.protocol,
                commitment=self.commitment,
                launch=swapped_launch,
                reservation=self.reservation,
            )

    def test_swapped_request_executor_and_namespace_fail_closed(self) -> None:
        graph = self.build_graph()
        request = copy.deepcopy(graph["request"])
        request["executor_instance_sha256"] = digest("4")
        reseal(request, "request_sha256")
        with self.assertRaisesRegex(ValueError, "request binding"):
            validate_unsigned_executor_declaration(
                graph["attestation"],
                protocol=self.protocol,
                request=request,
                challenge_prediction_freeze=graph["freeze"],  # type: ignore[arg-type]
            )
        request = copy.deepcopy(graph["request"])
        request["graph_namespace_sha256"] = digest("5")
        reseal(request, "request_sha256")
        with self.assertRaisesRegex(ValueError, "protocol binding"):
            validate_challenge_execution_request(request, protocol=self.protocol)

    def test_missing_layer_and_challenge_only_at_top_level_fail_closed(self) -> None:
        graph = self.build_graph()
        pair_value = copy.deepcopy(graph["pair"])
        pair_value["challenge_terminal_sha256s"] = pair_value[
            "challenge_terminal_sha256s"
        ][:-1]
        reseal(pair_value, "pair_sha256")
        with self.assertRaisesRegex(ValueError, "challenge terminals"):
            validate_challenge_bound_outer_pair(pair_value, protocol=self.protocol)
        terminal = copy.deepcopy(graph["terminals"][0])
        terminal.pop("launch_challenge_sha256")
        reseal(terminal, "terminal_sha256")
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_challenge_evaluated_terminal(terminal)
        pair_value = copy.deepcopy(graph["pair"])
        pair_value["challenge_only_at_top_level"] = True
        reseal(pair_value, "pair_sha256")
        with self.assertRaisesRegex(ValueError, "pair drifted"):
            validate_challenge_bound_outer_pair(pair_value, protocol=self.protocol)

    def test_resealed_parent_substitution_is_rejected_at_each_downstream_layer(self) -> None:
        graph = self.build_graph()
        terminal = copy.deepcopy(graph["terminals"][0])
        terminal["executor_attestation_sha256"] = digest("6")
        reseal(terminal, "terminal_sha256")
        with self.assertRaisesRegex(ValueError, "parent binding"):
            validate_challenge_evaluated_terminal(
                terminal,
                protocol=self.protocol,
                request=graph["request"],  # type: ignore[arg-type]
                challenge_prediction_freeze=graph["freeze"],  # type: ignore[arg-type]
                executor_attestation=graph["attestation"],  # type: ignore[arg-type]
                challenge_evaluator_provenance=graph["evaluator"],  # type: ignore[arg-type]
            )
        contribution = copy.deepcopy(graph["contributions"][0])
        contribution["signed_terminal_contribution"] *= -1
        reseal(contribution, "contribution_sha256")
        aggregate = copy.deepcopy(graph["aggregate"])
        aggregate["challenge_contribution_sha256s"][0] = contribution[
            "contribution_sha256"
        ]
        reseal(aggregate, "aggregate_sha256")
        with self.assertRaisesRegex(ValueError, "contribution binding"):
            validate_challenge_replicate_aggregate(
                aggregate,
                protocol=self.protocol,
                challenge_contributions=[
                    contribution,
                    *graph["contributions"][1:],
                ],
            )

    def test_wrong_attestor_domain_and_pretend_signature_are_rejected(self) -> None:
        graph = self.build_graph()
        with self.assertRaisesRegex(ValueError, "trust domain"):
            build_unsigned_executor_declaration(
                protocol=self.protocol,
                request=graph["request"],  # type: ignore[arg-type]
                challenge_prediction_freeze=graph["freeze"],  # type: ignore[arg-type]
                execution_trace_sha256=digest("1"),
                execution_result_nonce_sha256=digest("2"),
                attestor_trust_domain_sha256=digest("9"),
            )
        attestation = copy.deepcopy(graph["attestation"])
        attestation["signature_scheme"] = "sha256"
        attestation["detached_signature"] = digest("7")
        reseal(attestation, "attestation_sha256")
        with self.assertRaisesRegex(ValueError, "declaration drifted"):
            validate_unsigned_executor_declaration(attestation, protocol=self.protocol)

    def test_outer_source_replay_rejects_wrapped_but_tampered_legacy_loss(self) -> None:
        graph = self.build_graph()
        fixture = self.values["outer_fixture"]
        terminals = copy.deepcopy(graph["terminals"])
        terminals[0]["terminal_task_loss"] = 0.123
        reseal(terminals[0], "terminal_sha256")
        with self.assertRaisesRegex(ValueError, "wrapper differs"):
            build_challenge_bound_outer_pair(
                protocol=self.protocol,
                sequence_protocol=self.sequence_protocol,
                commitment=self.commitment,
                launch=self.launch,
                reservation=self.reservation,
                request=graph["request"],  # type: ignore[arg-type]
                challenge_prediction_freeze=graph["freeze"],  # type: ignore[arg-type]
                executor_attestation=graph["attestation"],  # type: ignore[arg-type]
                challenge_evaluator_provenance=graph["evaluator"],  # type: ignore[arg-type]
                challenge_terminals=terminals,
                challenge_contributions=graph["contributions"],  # type: ignore[arg-type]
                challenge_aggregate=graph["aggregate"],  # type: ignore[arg-type]
                legacy_outer_pair=self.legacy_pair,
                outer_job_manifest=fixture["job_manifest"],  # type: ignore[index,arg-type]
                outer_bundle_sha256=fixture["bundle_sha256"],  # type: ignore[index]
                outer_evaluated_terminal_receipts=fixture["evaluated_terminal_receipts"],  # type: ignore[index,arg-type]
                outer_prediction_freeze=fixture["prediction_freeze"],  # type: ignore[index,arg-type]
                outer_evaluator_provenance_receipt=fixture["evaluator_provenance_receipt"],  # type: ignore[index,arg-type]
                outer_terminal_state_records=fixture["terminal_state_records"],  # type: ignore[index,arg-type]
                outer_contribution_records=fixture["contribution_records"],  # type: ignore[index,arg-type]
                outer_replicate_aggregate=fixture["replicate_aggregate"],  # type: ignore[index,arg-type]
                outer_adapter_result=self.values["outer_result"],  # type: ignore[arg-type]
            )

    def test_exact_schemas_reject_privileged_or_unknown_fields(self) -> None:
        graph = self.build_graph()
        cases = (
            (validate_challenge_graph_protocol, self.protocol, "protocol_sha256"),
            (validate_challenge_execution_request, graph["request"], "request_sha256"),
            (validate_challenge_prediction_freeze, graph["freeze"], "freeze_sha256"),
            (validate_unsigned_executor_declaration, graph["attestation"], "attestation_sha256"),
            (validate_challenge_evaluator_provenance, graph["evaluator"], "provenance_sha256"),
            (validate_challenge_evaluated_terminal, graph["terminals"][0], "terminal_sha256"),
            (validate_challenge_contribution_record, graph["contributions"][0], "contribution_sha256"),
            (validate_challenge_replicate_aggregate, graph["aggregate"], "aggregate_sha256"),
            (validate_challenge_bound_outer_pair, graph["pair"], "pair_sha256"),
        )
        for validator, original, seal in cases:
            with self.subTest(validator=validator.__name__):
                value = copy.deepcopy(original)
                value["question_type"] = "forbidden"
                reseal(value, seal)
                with self.assertRaisesRegex(ValueError, "schema is not exact"):
                    validator(value)


if __name__ == "__main__":
    unittest.main()
