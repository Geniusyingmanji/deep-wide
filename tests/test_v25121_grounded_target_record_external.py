from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as parser  # noqa: E402
from deepwide_agent import v25119_grounded_target_record_paired_runtime as runtime  # noqa: E402
from deepwide_agent import v25121_grounded_target_record_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24984_robust_late_page_projection import (  # noqa: E402
    build_projection,
)
from scripts import control_v25121_grounded_target_record_external as control  # noqa: E402
from scripts import run_v25121_grounded_target_record_external as runner  # noqa: E402
from test_v24990_query_vector_paired_runtime import (  # noqa: E402
    SyntheticRobustSearch,
)


SYNTHETIC_TARGET = "SyntheticPkg"


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(**contract.LIMITS)


def lead(url: str, title: str = "Noise") -> dict[str, str]:
    return {"url": url, "fetch_url": url, "title": title}


class HiddenPackageModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = self.synthesis_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["ignored"],
                    "queries": [
                        "Python package description clue",
                        "Python library matching public description",
                        "package Version Released PyPI",
                        "package Requires PyPI",
                    ],
                }
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": [SYNTHETIC_TARGET],
                    "row_targets": [SYNTHETIC_TARGET],
                    "authority_terms": ["PyPI"],
                    "queries": [
                        f"{SYNTHETIC_TARGET} Version Released PyPI",
                        f"{SYNTHETIC_TARGET} Requires PyPI",
                    ],
                }
            )
        else:
            self.synthesis_calls += 1
            value = "9.9.9" if "9.9.9" in user else "1.1.1"
            text = (
                "| Package | Version | Released | Requires |\n"
                "|---|---|---|---|\n"
                f"| {SYNTHETIC_TARGET} | {value} | 2026-01-02 | >=3.10 |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class HiddenPackageSearch(SyntheticRobustSearch):
    def __init__(self, question: str, phase: str) -> None:
        super().__init__(question, "unused")
        self.phase = phase

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        if self.phase == runtime.FIRST_PHASE:
            return [
                {
                    "query": query,
                    "answer": "",
                    "results": [
                        lead(
                            f"https://public.example/clue-{query_index}-{item_index}",
                            "Public package description",
                        )
                        for item_index in range(3)
                    ],
                    "error": None,
                    "provider": "synthetic",
                }
                for query_index, query in enumerate(values)
            ]
        return [
            {
                "query": values[0],
                "answer": "",
                "results": [
                    lead("https://noise.example/one"),
                    lead("https://noise.example/two"),
                    lead("https://noise.example/three"),
                ],
                "error": None,
                "provider": "synthetic",
                "hosted_search_trace": {
                    "actions": [
                        {
                            "sources": [
                                lead("https://noise.example/four"),
                                lead(
                                    "https://pypi.org/project/syntheticpkg/",
                                    "SyntheticPkg project record",
                                ),
                            ]
                        }
                    ]
                },
            },
            {
                "query": values[1],
                "answer": "",
                "results": [],
                "error": "hosted search returned no query-local URL citation",
                "provider": "synthetic",
            },
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        output = []
        for item in values:
            url = str(item["url"])
            if self.phase == runtime.FIRST_PHASE and "clue-0-0" in url:
                raw = (
                    "The matching Python package is SyntheticPkg. SyntheticPkg is "
                    "the unique library described by the public clue."
                )
            elif self.phase == runtime.FIRST_PHASE:
                raw = "General Python package background."
            elif "pypi.org/project/syntheticpkg" in url:
                raw = (
                    "Package | Version | Released | Requires\n"
                    "SyntheticPkg | 9.9.9 | 2026-01-02 | >=3.10\n"
                )
            else:
                raw = (
                    "Package | Version | Released | Requires\n"
                    "SyntheticPkg | 1.1.1 | 2026-01-02 | >=3.10\n"
                )
            projected = build_projection(
                self._question,
                {"title": "Public package page", "url": url, "text": raw},
            )
            self._prefixes[url] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            output.append(
                {
                    "query": item.get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": "Public package page",
                            "url": url,
                            "fetch_url": url,
                            "requested_url": url,
                            "raw_content": projected["projection"],
                            "content": "",
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-fetch",
                }
            )
        return output


class V25121GroundedTargetRecordExternalTests(unittest.TestCase):
    def _runtime_row(self, index: int = 0) -> dict:
        task = contract.task_vector()[index]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for slot in range(1, contract.MODEL_SLOT_CAP + 1):
                (slots / f"slot_{slot:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = HiddenPackageModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=root,
                slot_cap=contract.MODEL_SLOT_CAP,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: HiddenPackageSearch(task["question"], phase)
                for phase in runtime.PHASES
            }
            result = runtime.run_paired_task(
                task,
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=contract.arm_order_vector()[index],
            )
            self.assertEqual(inner.logical_calls, 4)
            return runner._from_runtime(
                task,
                contract.arm_order_vector()[index],
                result,
                runner._health(),
            )

    def test_fresh_description_population_exact_schema_and_balanced_order(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len(set(contract.CLUES)), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 4)
        self.assertEqual(
            sum(
                order[0] == contract.CANDIDATE_ARM
                for order in contract.arm_order_vector()
            ),
            10,
        )
        self.assertTrue(
            all(
                parser.extract_exact_visible_columns(task["question"])
                == list(contract.COLUMNS)
                for task in tasks
            )
        )
        self.assertTrue(
            all("<PACKAGE>" not in task["question"] for task in tasks)
        )

    def test_source_policy_and_attribution_gate_are_explicit(self) -> None:
        policy = contract.source_policy()
        gate = contract.mechanism_gate()
        self.assertTrue(
            policy[
                "forward_closure_contains_description_clues_but_no_hidden_target_mapping"
            ]
        )
        self.assertTrue(
            policy[
                "selection_change_needs_actual_target_field_page_gain_for_mechanism_credit"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])
        self.assertEqual(gate["minimum_positive_target_field_page_gain_tasks"], 4)
        self.assertEqual(gate["minimum_retrieval_mechanism_engaged_tasks"], 4)
        self.assertEqual(gate["minimum_attributable_prediction_changed_tasks"], 3)

    def test_real_runtime_row_closes_grounding_selection_and_credit_chain(self) -> None:
        row = runner.validate_task_row(self._runtime_row())
        receipt = row["content_free_receipt"]
        self.assertTrue(row["runtime_completed"])
        self.assertTrue(receipt["grounded_plan_strategy_applied"])
        self.assertTrue(receipt["selection_changed"])
        self.assertGreater(receipt["target_field_page_gain"], 0)
        self.assertTrue(receipt["retrieval_mechanism_engaged"])
        self.assertTrue(receipt["attributable_prediction_change"])
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 14)

    def test_failure_as_zero_is_terminal_and_cannot_pass(self) -> None:
        failure = runner._terminal_outer_failure(
            contract.task_vector()[0],
            contract.arm_order_vector()[0],
            ValueError("x"),
            1.0,
            runner._health(),
        )
        checked = runner.validate_task_row(failure)
        self.assertTrue(checked["failure_as_zero"])
        self.assertFalse(checked["runtime_completed"])

    def test_ideal_aggregate_requires_each_mechanism_stage(self) -> None:
        aggregate = {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "failure_as_zero_tasks": 0,
            "both_arms_model_success_tasks": 20,
            "shared_first_wave_completed_tasks": 20,
            "grounded_plan_attempted_tasks": 20,
            "grounded_plan_strategy_applied_tasks": 8,
            "shared_second_wave_completed_tasks": 20,
            "selection_strategy_eligible_tasks": 6,
            "selection_changed_tasks": 4,
            "positive_target_field_page_gain_tasks": 4,
            "positive_target_field_pair_gain_tasks": 4,
            "retrieval_mechanism_engaged_tasks": 4,
            "prediction_changed_tasks": 3,
            "attributable_prediction_changed_tasks": 3,
            "unattributable_prediction_changed_tasks": 0,
            "physical_queries": 80,
            "physical_fetches": 240,
            "physical_model_logical_calls": 80,
            "model_provider_requests": 80,
            "model_provider_attempts": 80,
            "control_effective_model_logical_calls": 60,
            "candidate_effective_model_logical_calls": 60,
            "control_logical_fetches": 200,
            "candidate_logical_fetches": 200,
            "control_evidence_characters": 1_000,
            "candidate_evidence_characters": 1_000,
            "outer_or_accounting_failure_tasks": 0,
            "terminal_transport_timeout_helper_or_model_hard_failures": 0,
            "query_local_mapping_failure_rows": 0,
            "control_arm_model_failures": 0,
            "candidate_arm_model_failures": 0,
            "system_total_tokens": 1_000,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        for name in (
            "grounded_plan_strategy_applied_tasks",
            "selection_changed_tasks",
            "positive_target_field_page_gain_tasks",
            "retrieval_mechanism_engaged_tasks",
            "attributable_prediction_changed_tasks",
        ):
            changed = copy.deepcopy(aggregate)
            changed[name] = 0
            with self.subTest(name=name):
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_resealed_runtime_or_privileged_tamper_fails(self) -> None:
        row = self._runtime_row()
        for kind in ("runtime", "receipt", "privileged"):
            changed = copy.deepcopy(row)
            if kind == "runtime":
                changed["runtime_result_payload_sha256"] = "0" * 64
            elif kind == "receipt":
                changed["content_free_receipt"]["target_field_page_gain"] = 0
            else:
                changed["category"] = "forbidden"
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises((RuntimeError, ValueError)):
                runner.validate_task_row(changed)

    def test_forward_sources_are_label_blind_and_evaluator_absent(self) -> None:
        forbidden = {
            "category",
            "question_type",
            "ground_truth",
            "answer_key",
            "gold",
            "score",
            "reward",
        }
        accesses: list[str] = []
        closure = contract.forward_dependency_closure(ROOT)
        for relative in closure:
            path = ROOT / relative
            if path.suffix != ".py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(
                    node.slice, ast.Constant
                ):
                    if node.slice.value in forbidden:
                        accesses.append(str(node.slice.value))
        self.assertEqual(accesses, [])
        self.assertFalse((ROOT / contract.EVALUATOR).exists())
        self.assertFalse((ROOT / contract.POSTFREEZE_GOLD).exists())

    def test_build_audit_and_protocol_authorize_only_one_future_forward(self) -> None:
        fake_tests = {
            "expected": control.EXPECTED_TESTS,
            "observed": control.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        fake_semantic = {
            "dependency_closure": [],
            "dependency_closure_sha256": "0" * 64,
            "privileged_runtime_field_accesses": [],
            "allowed_provider_rank_access": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
        }
        fake_freshness = {
            "parent_commit": contract.FRESHNESS_PARENT_COMMIT,
            "clue_count": 20,
            "all_exact_literal_zero_hit": True,
            "rows": [],
            "network_endpoint_page_value_model_or_evaluator_access": False,
        }
        frozen_watchers = [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ]
        with mock.patch.object(control, "_tests", return_value=fake_tests), mock.patch.object(
            control, "_semantic_audit", return_value=fake_semantic
        ), mock.patch.object(
            control, "_history_freshness", return_value=fake_freshness
        ), mock.patch.object(control, "_parent_valid", return_value=True), mock.patch.object(
            control, "_lease_inactive", return_value=True
        ), mock.patch.object(
            control, "_future_pristine", return_value=True
        ), mock.patch.object(contract, "watcher_snapshot", return_value=frozen_watchers):
            value = control.build_audit(now=1, require_clean=False)
        checked = control.validate_build(value)
        self.assertTrue(checked["authorization"]["protocol_generation_after_build_commit_push"])
        self.assertFalse(checked["authorization"]["external_forward"])
        self.assertFalse(checked["authorization"]["evaluator"])


if __name__ == "__main__":
    unittest.main()
