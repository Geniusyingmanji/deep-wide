from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24327_neutral_transport_smoke as target  # noqa: E402


def fake_parent() -> dict:
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=12.0,
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


def fake_envelope() -> dict:
    receipt = {
        "effect_accounting_complete": True,
        "prefix_status": "frozen",
        "prefix_bundle": {"producer_execution_count": 1},
        "candidate_identity_handoff": True,
        "proposed_cell_changes": 0,
        "admitted_cell_changes": 0,
        "credited_conditional_entropy_reduction_nats": 0,
        "logical_model_admissions": 3,
        "provider_model_requests": 3,
        "provider_model_attempts": 3,
        "pre_provider_model_rejections": 0,
        "core_logical_queries": 4,
        "core_search_provider_effects": 1,
        "reserve_search_provider_effects": 0,
        "core_fetch_targets": 7,
        "reserve_fetch_targets": 3,
        "core_network_fetch_effects": 7,
        "reserve_network_fetch_effects": 3,
        "core_usable_pages": 6,
        "reserve_usable_pages": 2,
        "repeated_plan_model_effects_by_branches": 0,
        "repeated_core_search_effects_by_branches": 0,
        "repeated_core_fetch_effects_by_branches": 0,
    }
    return {
        "result": {
            "status": "completed",
            "completion_kind": "identity_no_reserve",
            "shared_prefix_revision_receipt": receipt,
            "cost": {
                "model": {
                    "requests": 3,
                    "attempts": 3,
                    "total_tokens": 1234,
                },
                "search": {
                    "calls": 1,
                    "failures": 0,
                    "fetch_calls": 10,
                    "fetch_failures": 2,
                    "total_tokens": 567,
                },
            },
        },
        "model_slot_receipt": {
            "slot_cap": 2,
            "acquisitions": 3,
            "slot_timeouts": 0,
        },
        "transport_health": {
            "hosted_search_attempts": 1,
            "hosted_search_deadline_failures": 0,
            "hard_fetch_helper_calls": 10,
            "hard_fetch_deadline_failures": 1,
            "fetch_deadline_rejections": 0,
            "fetch_helper_failures": 1,
            "deadline_exhausted": False,
        },
    }


class V24327NeutralTransportSmokeTests(unittest.TestCase):
    def test_protocol_is_sealed_content_free_and_launch_false(self) -> None:
        value = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=value)
        self.assertFalse(value["authorization"]["neutral_transport_smoke_launch"])
        self.assertFalse(value["authorization"]["benchmark_launch"])
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertNotIn(target.neutral_task()["question"], encoded)
        self.assertNotIn(target.neutral_task()["opaque_id"], encoded)

    def test_projection_and_decision_are_content_free_and_gate_mechanical(self) -> None:
        projected = target._project(fake_parent(), fake_envelope(), wall_seconds=12.0)
        target.validate_projection(projected)
        checks = target._checks(projected, target.GATES)
        self.assertTrue(all(checks.values()), checks)
        encoded = json.dumps(projected, ensure_ascii=False)
        for forbidden in (
            target.neutral_task()["opaque_id"],
            target.neutral_task()["question"],
            "http://",
            "https://",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_projection_resealed_content_injection_fails_closed(self) -> None:
        projected = target._project(fake_parent(), fake_envelope(), wall_seconds=12.0)
        projected["leaked"] = "https://example.invalid/private"
        projected.pop("probe_payload_sha256")
        projected["probe_payload_sha256"] = payload_sha256(projected)
        with self.assertRaises(RuntimeError):
            target.validate_projection(projected)

    def test_preaudit_fails_closed_on_port_or_lease(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        with (
            patch.object(target, "validate_protocol", return_value=protocol),
            patch.object(target, "_run_test", return_value=True),
            patch.object(target, "sha256", return_value="a" * 64),
            patch.object(target, "_port_listening", return_value=False),
            patch.object(
                target,
                "lease_observation",
                return_value={"active": False},
            ),
        ):
            with self.assertRaises(RuntimeError):
                target.build_preaudit(ROOT, now=0)
        with (
            patch.object(target, "validate_protocol", return_value=protocol),
            patch.object(target, "_run_test", return_value=True),
            patch.object(target, "sha256", return_value="a" * 64),
            patch.object(target, "_port_listening", return_value=True),
            patch.object(
                target,
                "lease_observation",
                return_value={"active": True},
            ),
        ):
            with self.assertRaises(RuntimeError):
                target.build_preaudit(ROOT, now=0)

    def test_activation_and_execution_start_are_no_effect_artifacts(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        preaudit = {
            "protected_watchers": target.protected_watcher_snapshot(),
        }
        with (
            patch.object(target, "validate_protocol", return_value=protocol),
            patch.object(target, "validate_preaudit", return_value=preaudit),
            patch.object(target, "sha256", return_value="a" * 64),
            patch.object(
                target,
                "lease_observation",
                return_value={"active": False},
            ),
            patch.object(target, "_port_listening", return_value=True),
            patch.object(target, "validate_activation", side_effect=lambda root, value: value),
        ):
            activation = target.build_activation(ROOT, now=0)
        self.assertFalse(
            activation["network_model_search_fetch_evaluator_or_api_called"]
        )
        self.assertTrue(activation["launch_authorized"])


if __name__ == "__main__":
    unittest.main()
