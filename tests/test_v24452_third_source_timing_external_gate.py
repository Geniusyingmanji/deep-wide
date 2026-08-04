from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    child_receipt,
    parent_receipt,
)
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24397_failure_observability import (  # noqa: E402
    aggregate_observations,
    build_task_observation,
)
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    build_envelope,
    run_v24447_task,
)
from deepwide_agent.v24448_serialized_third_source_envelope import (  # noqa: E402
    validate_serialized_observed_bundle,
)
from deepwide_agent.v24450_timed_third_source_runner import (  # noqa: E402
    aggregate_stage_timings,
    build_timing_receipt,
)
from scripts import v24452_third_source_timing_external_gate as target  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


def successful_parent(elapsed: float = 10.0) -> dict:
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=elapsed,
        subprocess_exception=False,
        child_terminal_receipt_present=True,
        child_terminal_receipt_valid=True,
        result_envelope_present=True,
        result_envelope_valid=True,
        model_receipt_present=True,
        model_receipt_valid=True,
        transport_receipt_present=True,
        transport_receipt_valid=True,
    )


class V24452ThirdSourceTimingExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.temporary.name), clock, third=True)
        cls.outcome = run_v24447_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.capability = validate_serialized_observed_bundle(
            json.loads(
                json.dumps(build_envelope(cls.outcome), ensure_ascii=False, sort_keys=True)
            ),
            model_slot_receipt=cls.outcome.model_slot_receipt,
            transport_health=cls.outcome.transport_health,
            search_single_shot_receipt=cls.outcome.search_single_shot_receipt,
            expected_cap=2,
        )
        mechanisms = []
        observations = []
        timings = []
        child = child_receipt(
            stage="result_envelope_written",
            exception_type=None,
            model_receipt_written=True,
            transport_receipt_written=True,
            result_envelope_written=True,
        )
        for ordinal in range(1, target.SELECTED + 1):
            mechanisms.append(target.projection.task_projection(ordinal, cls.capability))
            parent = successful_parent(float(ordinal))
            observations.append(
                build_task_observation(
                    ordinal,
                    parent,
                    child=child,
                    failure_snapshot=None,
                    model_receipt=cls.outcome.model_slot_receipt,
                    transport_health=cls.outcome.transport_health,
                    search_receipt=cls.outcome.search_single_shot_receipt,
                    expected_model_cap=2,
                )
            )
            timings.append(
                build_timing_receipt(
                    ordinal=ordinal,
                    parent=parent,
                    child_wall_seconds=float(ordinal),
                    validation_wall_seconds=0.2,
                    projection_wall_seconds=0.01,
                    validation_invocations=1,
                    projection_invocations=1,
                    validated_capability=True,
                    projected_validated_capability=True,
                )
            )
        cls.mechanism = target.projection.aggregate_tasks(mechanisms, target.GATES)
        cls.observation = aggregate_observations(
            observations, selected=target.SELECTED
        )
        cls.timing = aggregate_stage_timings(timings, selected=target.SELECTED)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def public_result(self) -> dict:
        diagnostic = target._diagnostic_complete(
            self.mechanism, self.observation, self.timing
        )
        value = {
            "artifact_version": 1,
            "role": "v24452_third_source_external_result",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 0,
            "selected": target.SELECTED,
            "executor_count": target.EXECUTOR_COUNT,
            "model_slot_cap": target.MODEL_SLOT_CAP,
            "batch_wall_seconds": 100.0,
            "mechanism_aggregate": copy.deepcopy(self.mechanism),
            "observation_aggregate": copy.deepcopy(self.observation),
            "stage_timing_aggregate": copy.deepcopy(self.timing),
            "mechanism_failure_as_zero_rows": 0,
            "mechanism_passed": True,
            "reliability_passed": True,
            "latency_passed": True,
            "diagnostic_complete": diagnostic,
            "passed": diagnostic,
            "temporary_execution_directory_remaining": False,
            "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "provenance": {
                "protocol_sha256": "a" * 64,
                "preactivation_audit_sha256": "b" * 64,
                "activation_sha256": "c" * 64,
                "execution_start_sha256": "d" * 64,
                "surface_manifest_sha256": "e" * 64,
            },
        }
        value["result_payload_sha256"] = payload_sha256(value)
        return value

    def test_protocol_freezes_sixteenth_disjoint_population(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        current = {
            entity
            for question in target.QUESTIONS
            for entity in target.parent._question_entity_vector(question)
        }
        self.assertEqual(len(current), 128)
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(protocol["task_contract"]["prior_external_entity_count"], 1888)
        encoded = json.dumps(protocol, ensure_ascii=False)
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)
        self.assertEqual(protocol["mechanism"]["additional_fetch_cap"], 1)
        self.assertEqual(protocol["mechanism"]["additional_model_requests"], 0)
        self.assertEqual(protocol["provider"]["executor_count"], 8)
        self.assertEqual(protocol["provider"]["model_slot_cap"], 2)

    def test_public_result_requires_mechanism_latency_and_diagnostic_go(self) -> None:
        value = self.public_result()
        target.validate_public_result(value)
        self.assertTrue(value["passed"])
        self.assertEqual(
            value["mechanism_aggregate"]["third_source_safe_change_tasks"], 16
        )
        self.assertGreater(
            value["mechanism_aggregate"][
                "third_source_decision_credit_total_nats"
            ],
            0,
        )
        self.assertEqual(value["stage_timing_aggregate"]["validation_invocations"], 16)

    def test_public_result_rejects_content_or_resealed_state_drift(self) -> None:
        valid = self.public_result()
        leaked = {**valid, "private_url": "https://example.test/private"}
        leaked.pop("result_payload_sha256")
        leaked["result_payload_sha256"] = payload_sha256(leaked)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(leaked)
        drifted = copy.deepcopy(valid)
        drifted["passed"] = False
        drifted.pop("result_payload_sha256")
        drifted["result_payload_sha256"] = payload_sha256(drifted)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(drifted)

    def test_diagnostic_routes_separate_runtime_yield_decision_and_latency(self) -> None:
        base = copy.deepcopy(self.mechanism)
        self.assertEqual(
            target._diagnostic_route(base, False, True, True),
            "runtime_validation_or_observability_repair",
        )
        no_lead = copy.deepcopy(base)
        no_lead["third_source_total_candidates"] = 0
        self.assertEqual(
            target._diagnostic_route(no_lead, True, True, True),
            "frozen_lead_coverage_successor",
        )
        no_page = copy.deepcopy(base)
        no_page["third_source_total_usable_pages"] = 0
        self.assertEqual(
            target._diagnostic_route(no_page, True, True, True),
            "third_source_fetch_yield_successor",
        )
        no_decision = copy.deepcopy(base)
        no_decision["third_source_safe_change_tasks"] = 0
        self.assertEqual(
            target._diagnostic_route(no_decision, True, True, True),
            "entropy_to_decision_threshold_successor",
        )
        self.assertEqual(
            target._diagnostic_route(base, True, False, True),
            "provider_or_fetch_reliability_successor",
        )
        self.assertEqual(
            target._diagnostic_route(base, True, True, False),
            "latency_stage_capacity_successor",
        )
        self.assertEqual(
            target._diagnostic_route(base, True, True, True),
            "fresh_paired_dev64_design",
        )

    def test_protocol_launch_authorization_tamper_fails_closed(self) -> None:
        value = target.build_protocol(ROOT, now=0, require_pristine=False)
        altered = copy.deepcopy(value)
        altered["authorization"]["external_probe_launch"] = True
        altered.pop("protocol_payload_sha256")
        altered["protocol_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, value=altered)


if __name__ == "__main__":
    unittest.main()
