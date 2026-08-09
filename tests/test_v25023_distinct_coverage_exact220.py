from __future__ import annotations

import ast
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as parent  # noqa: E402
from deepwide_agent import v25023_distinct_coverage_exact220_contract as contract  # noqa: E402
from scripts import control_v25023_distinct_coverage_exact220 as control  # noqa: E402
from scripts import finalize_v25023_distinct_coverage_exact220 as finalizer  # noqa: E402
from scripts import run_v25023_distinct_coverage_exact220 as runner  # noqa: E402
from scripts import run_v25023_distinct_coverage_exact220_task as child  # noqa: E402


def metrics(**changes):
    value = {
        "whole_table_successes": 9,
        "quality_composite": 0.45724897824812605,
        "entity_acc": 0.7136363636363636,
        "f1_by_row": 0.2297391933902937,
        "f1_by_item": 0.400228047737325,
        "column_f1": 0.48539230822852186,
        "evaluator_invalid_or_not_run": 10,
        "fallback_tables": 0,
    }
    value.update(changes)
    return value


def direct(**changes):
    value = {
        "status_429": 0,
        "transport_failures": 0,
        "slot_timeouts": 0,
        "rate_aware": {"provider_gate_timeouts": 0},
    }
    value.update(changes)
    return value


class DistinctCoverageExact220Tests(unittest.TestCase):
    def test_parent_budget_capacity_and_policies_are_equal(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.rate_policy(), parent.rate_policy())
        self.assertEqual(contract.pacing_policy(), parent.pacing_policy())
        self.assertEqual(
            (
                contract.SELECTED_COUNT,
                contract.EXECUTOR_CONCURRENCY,
                contract.MODEL_SLOT_CAP,
                contract.TAVILY_KEY_SLOT_CAP,
            ),
            (220, 20, 8, 12),
        )

    def test_task_vector_is_complete_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_treatment_policy_is_matched_and_entropy_free(self) -> None:
        policy = contract.treatment_policy()
        self.assertTrue(policy["control_second_wave_exactly_replays_v24857"])
        self.assertTrue(policy["candidate_second_wave_fetch_count_equals_control"])
        self.assertTrue(policy["non_multi_identity_selection_exact_handoff"])
        self.assertTrue(policy["projector_nonadmission_exact_parent_5k_handoff"])
        self.assertFalse(policy["additional_query_fetch_model_token_context_byte_wall_or_network_cap"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_credit_or_routes"])

    def test_visible_question_exposure_is_counts_only_and_zero(self) -> None:
        tasks = contract.exposure_task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        value = contract.mechanism_exposure(tasks)
        self.assertEqual(
            value["visible_identity_count_distribution"], {"0": 220}
        )
        self.assertEqual(value["strict_multi_identity_task_count"], 0)
        self.assertEqual(value["line_list_block_count"], 35)
        self.assertEqual(value["formatting_context_line_list_block_count"], 35)
        self.assertEqual(value["nonformatting_context_line_list_block_count"], 0)
        self.assertFalse(value["exposure_gate_passed"])
        self.assertFalse(value["opaque_id_question_text_identity_or_list_item_emitted"])

    def test_exposure_audit_roundtrip_is_no_go(self) -> None:
        value = contract.build_exposure_audit(
            ROOT, now=123, require_clean=False
        )
        self.assertEqual(contract.validate_exposure_audit(ROOT, value), value)
        self.assertEqual(value["status"], "no_go_zero_natural_exposure")
        self.assertFalse(value["passed"])
        self.assertFalse(value["authorization"]["protocol_generation"])

    def test_resealed_exposure_tamper_and_protocol_generation_fail_closed(self) -> None:
        value = contract.build_exposure_audit(ROOT, now=123, require_clean=False)
        changed = copy.deepcopy(value)
        changed["exposure"]["strict_multi_identity_task_count"] = 1
        changed["exposure"]["exposure_gate_passed"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            contract.validate_exposure_audit(ROOT, changed)
        original_read = contract._read
        with mock.patch.object(
            contract,
            "_read",
            side_effect=lambda path: (
                value
                if path == ROOT / contract.EXPOSURE_AUDIT
                else original_read(path)
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "zero natural mechanism exposure"):
                contract.build_protocol(
                    ROOT, now=123, require_clean=False, require_pristine=False
                )

    def test_all_four_protected_watchers_are_bound(self) -> None:
        self.assertEqual(
            [row["pid"] for row in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_control_audits_all_treatment_sources_and_exact_count(self) -> None:
        original = (control.base.contract, control.base.RUNTIME_SOURCES, control.base.TEST_SUITES, control.base.EXPECTED_TESTS)
        try:
            control.configure()
            self.assertEqual(control.base.EXPECTED_TESTS, 148)
            for path in (
                contract.SELECTION_SOURCE,
                contract.RETRIEVAL_SOURCE,
                contract.SEARCH_SOURCE,
                contract.TASK_INTEGRATION_SOURCE,
                contract.PROJECTOR_SOURCE,
                contract.FETCH_SOURCE,
                contract.FETCH_HELPER,
            ):
                self.assertIn(path, control.base.RUNTIME_SOURCES)
        finally:
            (
                control.base.contract,
                control.base.RUNTIME_SOURCES,
                control.base.TEST_SUITES,
                control.base.EXPECTED_TESTS,
            ) = original

    def test_runner_sidecar_aggregates_are_content_free_at_zero_tasks(self) -> None:
        with mock.patch.object(contract, "SELECTED_COUNT", 0):
            distinct = runner._distinct_totals(ROOT)
            projection = runner._projection_totals(ROOT)
        self.assertEqual(distinct["invalid_or_missing_receipts"], 0)
        self.assertTrue(distinct["control_exactly_replays_frozen_v24857_lead_prefix"])
        self.assertFalse(distinct["mapping_gold_category_question_type_split_evaluator_score_reward_read"])
        self.assertEqual(projection["positive_signed_credit_count"], 0)
        self.assertFalse(projection["mapping_gold_category_question_type_split_evaluator_score_reward_read"])

    def test_child_visible_task_rejects_privileged_keys(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            directory = Path(raw)
            (directory / "visible_task.json").write_text(
                '{"opaque_id":"task_0123456789abcdef01234567","question":"q","category":"x"}',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                child._visible_question(directory)

    def test_quality_gate_requires_every_strict_condition(self) -> None:
        prior = metrics()
        current = metrics(whole_table_successes=10, quality_composite=0.46)
        checks = finalizer.quality_checks(
            current, prior, direct(), postresult_audit_valid=True
        )
        self.assertTrue(all(checks.values()))
        degraded = metrics(
            whole_table_successes=10,
            quality_composite=0.46,
            f1_by_item=prior["f1_by_item"] - 0.001,
        )
        checks = finalizer.quality_checks(
            degraded, prior, direct(), postresult_audit_valid=True
        )
        self.assertFalse(checks["item_f1_nonregression"])
        self.assertFalse(all(checks.values()))

    def test_quality_gate_rejects_exact_tie_or_transport_regression(self) -> None:
        prior = metrics()
        tie = metrics(quality_composite=0.46)
        checks = finalizer.quality_checks(
            tie, prior, direct(), postresult_audit_valid=True
        )
        self.assertFalse(checks["whole_table_exact_strict_gain_over_v24857"])
        gain = metrics(whole_table_successes=10, quality_composite=0.46)
        checks = finalizer.quality_checks(
            gain,
            prior,
            direct(status_429=1),
            postresult_audit_valid=True,
        )
        self.assertFalse(checks["provider_429_nonincrease"])

    def test_forward_runtime_sources_have_no_evaluator_import(self) -> None:
        for relative in (
            contract.RUNNER,
            contract.CHILD,
            contract.SELECTION_SOURCE,
            contract.RETRIEVAL_SOURCE,
            contract.SEARCH_SOURCE,
            contract.TASK_INTEGRATION_SOURCE,
            contract.PROJECTOR_SOURCE,
            contract.FETCH_SOURCE,
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(
                any("evaluator" in name or "finalize" in name for name in imports)
            )


if __name__ == "__main__":
    unittest.main()
