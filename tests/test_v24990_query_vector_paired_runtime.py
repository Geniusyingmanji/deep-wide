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


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v24990_query_vector_paired_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24984_robust_late_page_projection import (  # noqa: E402
    build_projection,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
)
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    validate_receipt as validate_fetch_receipt,
)


QUESTION = (
    "Use web search and the official Example Public Registry public page to "
    "return one table for <ENTITY>Alpha</ENTITY>. "
    "Column names: Entity, Value. Preserve exact spelling."
)


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=240,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class InnerModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
        self.requests += 1
        self.attempts += 1
        if json_mode:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["wrong"],
                    "queries": ["one very long provider query"],
                }
            )
        else:
            value = "999" if "999" in user else "111"
            text = f"| Entity | Value |\n|---|---|\n| Alpha | {value} |"
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class SyntheticRobustSearch(RobustLatePageBoundSearchClient):
    def __init__(self, question: str, value: str) -> None:
        self.calls = self.failures = self.tool_calls = 0
        self.fetch_calls = self.fetch_failures = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self._question = question
        self._value = value
        self._prefixes: dict[str, str] = {}
        self._receipts: list[dict] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        output = []
        for query in values:
            token = hashlib.sha256(query.encode()).hexdigest()[:12]
            sources = [
                {
                    "url": f"https://official-{self._value}.example/{token}/{index}",
                    "fetch_url": f"https://official-{self._value}.example/{token}/{index}",
                    "title": f"Source {index}",
                }
                for index in range(3)
            ]
            output.append(
                {
                    "query": query,
                    "answer": "",
                    "results": sources,
                    "error": None,
                    "provider": "synthetic",
                }
            )
        return output

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        output = []
        for item in values:
            raw = (
                "archive boilerplate\n" * 350
                + f"Entity | Value\nAlpha | {self._value}\n"
            )
            projected = build_projection(
                self._question,
                {"title": "Official", "url": item["url"], "text": raw},
            )
            self._prefixes[item["url"]] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            output.append(
                {
                    "query": item.get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": "Official",
                            "url": item["url"],
                            "fetch_url": item["url"],
                            "raw_content": projected["projection"],
                            "content": "",
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-fetch",
                }
            )
        return output

    def parent_prefix_for(self, url):
        return self._prefixes.get(url, "")

    def late_page_projection_receipt(self):
        summed = (
            "projection_failure_count",
            "input_content_characters",
            "input_characters_beyond_parent_prefix",
            "discovered_record_count",
            "admissible_record_count",
            "admissible_bound_observation_count",
            "retained_record_count",
            "retained_bound_observation_count",
            "compact_prefix_characters",
            "raw_prefix_characters_retained",
            "output_characters",
            "positive_signed_credit_count",
        )
        value = {
            "artifact_version": 1,
            "role": "v24981_content_free_late_page_fetch_receipt",
            "policy_id": "v24981_hard_deadline_late_page_bound_fetch_v1",
            "fetch_calls_snapshot": self.fetch_calls,
            "fetch_failures_snapshot": self.fetch_failures,
            "helper_result_count": len(self._receipts),
            "projected_page_count": len(self._receipts),
            "mechanism_engaged_page_count": sum(
                row["mechanism_engaged"] for row in self._receipts
            ),
            "exact_parent_prefix_handoff_page_count": sum(
                row["exact_parent_prefix_handoff"] for row in self._receipts
            ),
            "candidate_evidence_changed_page_count": sum(
                row["candidate_evidence_changed"] for row in self._receipts
            ),
            **{
                name: sum(int(row[name]) for row in self._receipts)
                for name in summed
            },
            "maximum_network_response_bytes_per_fetch": 3_000_000,
            "parent_page_character_cap": 5_000,
            "visible_question_read_from_environment_file_or_benchmark_metadata": False,
            "question_url_title_page_record_value_prediction_answer_hash_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_fetch_receipt(value)


class FailingSyntheticRobustSearch(SyntheticRobustSearch):
    def search_many(self, queries, **kwargs):
        del kwargs
        list(queries)
        self.calls += 1
        self.failures += 1
        raise RuntimeError("synthetic retrieval failure")


class QueryVectorPairedRuntimeTests(unittest.TestCase):
    def _run(self, *, question: str = QUESTION, values=("111", "999")):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = InnerModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                target.CONTROL_ARM: SyntheticRobustSearch(question, values[0]),
                target.CANDIDATE_ARM: SyntheticRobustSearch(question, values[1]),
            }
            result = target.run_paired_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": question,
                },
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        return inner, searches, target.validate_result(result)

    def test_one_plan_two_equal_retrieval_arms_and_two_syntheses(self) -> None:
        inner, searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["short_query_strategy_applied"])
        self.assertTrue(receipt["query_vectors_differ"])
        self.assertEqual(receipt["model_logical_call_count"], 3)
        self.assertEqual(inner.requests, 3)
        for arm in target.ARMS:
            metric = receipt["arm_metrics"][arm]
            self.assertEqual(metric["planned_queries"], 4)
            self.assertEqual(metric["executed_queries"], 4)
            self.assertEqual(metric["fetch_attempts"], 10)
            self.assertEqual(metric["usable_pages"], 10)
            self.assertGreater(metric["query_local_results"], 0)
            self.assertGreater(metric["retained_records"], 0)
            self.assertTrue(metric["model_success"])
            self.assertEqual(searches[arm].calls, 2)
            self.assertEqual(searches[arm].fetch_calls, 10)
        self.assertEqual(len(set(result["evidence_characters"].values())), 1)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])

    def test_missing_facets_uses_identical_query_vectors(self) -> None:
        question = "Return one table. Column names: Entity, Value."
        _inner, _searches, result = self._run(
            question=question, values=("111", "111")
        )
        receipt = result["content_free_receipt"]
        self.assertFalse(receipt["short_query_strategy_applied"])
        self.assertFalse(receipt["query_vectors_differ"])
        self.assertFalse(result["prediction_changed"])

    def test_tamper_fails_closed(self) -> None:
        _inner, _searches, result = self._run()
        tampered = copy.deepcopy(result)
        tampered["content_free_receipt"]["arm_metrics"][target.CANDIDATE_ARM][
            "fetch_attempts"
        ] = 11
        with self.assertRaises(ValueError):
            target.validate_result(tampered)

        unknown = copy.deepcopy(result["content_free_receipt"])
        unknown["unexpected_field"] = 1
        unknown.pop("receipt_payload_sha256")
        unknown["receipt_payload_sha256"] = payload_sha256(unknown)
        with self.assertRaises(ValueError):
            target.validate_receipt(unknown)

    def test_invalid_arm_order_and_shared_client_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            model = DeadlineAwareGlobalModelSlotLimiter(
                InnerModel(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            shared = SyntheticRobustSearch(QUESTION, "999")
            with self.assertRaisesRegex(ValueError, "distinct robust search"):
                target.run_paired_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": QUESTION,
                    },
                    model=model,
                    searches={arm: shared for arm in target.ARMS},
                    limits=limits(),
                )

            distinct = {
                target.CONTROL_ARM: SyntheticRobustSearch(QUESTION, "111"),
                target.CANDIDATE_ARM: SyntheticRobustSearch(QUESTION, "999"),
            }
            distinct[target.CONTROL_ARM].calls = 1
            with self.assertRaisesRegex(ValueError, "pristine"):
                target.run_paired_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": QUESTION,
                    },
                    model=model,
                    searches=distinct,
                    limits=limits(),
                )

    def test_receipt_discloses_nonproduction_total_budget(self) -> None:
        _inner, _searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertTrue(
            receipt["external_gate_total_retrieval_budget_doubles_production"]
        )
        self.assertFalse(receipt["production_runtime_or_exact220_authorized"])
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])
        self.assertFalse(
            receipt["entropy_or_information_gain_assigns_signed_credit"]
        )

    def test_partial_retrieval_failure_preserves_effect_accounting(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            model = DeadlineAwareGlobalModelSlotLimiter(
                InnerModel(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            result = target.run_paired_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": QUESTION,
                },
                model=model,
                searches={
                    target.CONTROL_ARM: FailingSyntheticRobustSearch(
                        QUESTION, "111"
                    ),
                    target.CANDIDATE_ARM: SyntheticRobustSearch(QUESTION, "999"),
                },
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        checked = target.validate_result(result)
        receipt = checked["content_free_receipt"]
        failed = receipt["arm_metrics"][target.CONTROL_ARM]
        candidate = receipt["arm_metrics"][target.CANDIDATE_ARM]
        self.assertEqual(failed["executed_queries"], 2)
        self.assertEqual(failed["fetch_attempts"], 0)
        self.assertFalse(failed["synthesis_attempted"])
        self.assertEqual(
            receipt["actual_first_synthesis_arm"], target.CANDIDATE_ARM
        )
        self.assertTrue(candidate["synthesis_attempted"])
        self.assertEqual(receipt["model_logical_call_count"], 2)

    def test_module_has_no_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v24990_query_vector_paired_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "deepwidebench",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )


if __name__ == "__main__":
    unittest.main()
