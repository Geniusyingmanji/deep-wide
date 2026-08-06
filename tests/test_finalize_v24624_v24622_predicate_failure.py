from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import finalize_v24624_v24622_predicate_failure as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


class V24624V24622PredicateFailureTests(unittest.TestCase):
    def test_control_chain_is_valid_and_public_result_absent(self) -> None:
        chain = target._control_chain()
        self.assertEqual(
            set(chain),
            {
                "build_audit_sha256",
                "protocol_sha256",
                "preactivation_audit_sha256",
                "activation_sha256",
                "execution_start_sha256",
            },
        )
        self.assertTrue(all(len(value) == 64 for value in chain.values()))
        self.assertFalse((ROOT / target.failed.RESULT).exists())

    def test_binding_diagnosis_proves_self_reference_without_calling_predicate(self) -> None:
        value = target.binding_diagnosis()
        self.assertTrue(value["self_referential_binding_proven"])
        self.assertTrue(value["base_mechanism_predicate_is_v24616_predicate"])
        self.assertTrue(value["controller_mechanism_predicate_is_v24616_predicate"])
        self.assertTrue(
            value["predicate_bytecode_references_controller_mechanism_passed"]
        )

    def test_failure_is_terminal_consumed_and_nonretryable(self) -> None:
        value = target.build_failure(now=0)
        self.assertEqual(
            value["status"],
            "terminal_postaggregate_mechanism_predicate_recursion_no_result",
        )
        self.assertTrue(value["external_population_consumed"])
        self.assertEqual(value["external_wave_count"], 1)
        self.assertFalse(value["result_created"])
        self.assertFalse(value["official_evaluator_called"])
        self.assertFalse(
            value["authorization"]["same_population_retry_resume_or_evaluation"]
        )

    def test_failure_distinguishes_recovered_collector_from_predicate(self) -> None:
        value = target.build_failure(now=0)
        self.assertEqual(
            value["failure_class"], "self_referential_mechanism_predicate_binding"
        )
        self.assertTrue(value["all_task_futures_returned"])
        self.assertTrue(value["collector_context_covered_task_and_aggregate_lifetime"])
        self.assertTrue(value["content_free_mechanism_aggregate_completed"])
        self.assertFalse(value["mechanism_gate_evaluation_completed"])
        self.assertFalse(value["collector_absent_failure_recurred"])
        self.assertFalse(
            value["provider_search_or_fetch_latency_established_as_failure_cause"]
        )

    def test_resealed_failure_tamper_fails_closed(self) -> None:
        value = target.build_failure(now=0)
        for field, changed in (
            ("external_population_consumed", False),
            ("result_created", True),
            ("collector_absent_failure_recurred", True),
        ):
            tampered = copy.deepcopy(value)
            tampered[field] = changed
            reseal(tampered, "failure_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_failure(tampered)

    def test_postaudit_requires_inactive_lease_watchers_no_runner_or_temp(self) -> None:
        failure = target.build_failure(now=0)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "failure.json"
            path.write_text("{}\n", encoding="utf-8")
            expected = target.failed._read(target.failed.EXECUTION_START)[
                "protected_watchers"
            ]
            with (
                patch.object(target, "FAILURE", path.relative_to(ROOT)),
                patch.object(target, "validate_failure", return_value=failure),
                patch.object(
                    target.failed.base,
                    "lease_observation",
                    return_value={"active": False},
                ),
                patch.object(target, "_runner_pids", return_value=[]),
                patch.object(target, "_recent_temporary_directories", return_value=[]),
                patch.object(
                    target.failed.base,
                    "protected_watcher_snapshot",
                    return_value=expected,
                ),
            ):
                value = target.build_postaudit(now=0)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])

    def test_runtime_surface_is_label_blind_and_secret_free(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        path = Path("scripts/finalize_v24624_v24622_predicate_failure.py")
        accesses, imports = audit.ast_findings(path)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertIsNone(audit.SECRET.search((ROOT / path).read_text(encoding="utf-8")))

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "failure.json"
            target._publish(path, {})
            with self.assertRaises(FileExistsError):
                target._publish(path, {})


if __name__ == "__main__":
    unittest.main()
