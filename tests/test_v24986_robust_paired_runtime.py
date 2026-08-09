from __future__ import annotations

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

from deepwide_agent import v24986_robust_paired_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24980_late_page_bound_projection import build_projection  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    LatePageBoundSearchClient,
    validate_receipt,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Return exactly one Markdown table. Column names: Entity, Value. "
    "Preserve exact spelling."
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
                    "queries": ["visible planned query"],
                }
            )
        else:
            value = "999" if "999" in user else "Unknown"
            # Equal-width but wrong headers are recoverable without changing
            # either non-empty factual cell.
            text = f"Name | Amount\n--- | ---\nLate Entity | {value}\n"
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class SyntheticSearch(LatePageBoundSearchClient):
    def __init__(self, question: str) -> None:
        self.calls = self.failures = self.tool_calls = 0
        self.fetch_calls = self.fetch_failures = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self._question = question
        self._prefixes: dict[str, str] = {}
        self._receipts: list[dict] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += len(values)
        output = []
        for query_index, query in enumerate(values):
            sources = [
                {
                    "url": f"https://official{query_index}.example/data/{source_index}",
                    "fetch_url": f"https://official{query_index}.example/data/{source_index}",
                    "title": f"Source {source_index}",
                }
                for source_index in range(1, 4)
            ]
            output.append(
                {
                    "query": query,
                    "answer": "",
                    "results": [],
                    "error": "hosted search returned no query-local URL citation",
                    "provider": "synthetic",
                    "hosted_search_trace": {"actions": [{"sources": sources}]},
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
                + "Entity | Value\nLate Entity | 999\n"
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
        counts = {
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
        }
        value = {
            "artifact_version": 1,
            "role": "v24981_content_free_late_page_fetch_receipt",
            "policy_id": "v24981_hard_deadline_late_page_bound_fetch_v1",
            "fetch_calls_snapshot": self.fetch_calls,
            "fetch_failures_snapshot": self.fetch_failures,
            "helper_result_count": len(self._receipts),
            "projected_page_count": len(self._receipts),
            "mechanism_engaged_page_count": sum(
                receipt["mechanism_engaged"] for receipt in self._receipts
            ),
            "exact_parent_prefix_handoff_page_count": sum(
                receipt["exact_parent_prefix_handoff"] for receipt in self._receipts
            ),
            "candidate_evidence_changed_page_count": sum(
                receipt["candidate_evidence_changed"] for receipt in self._receipts
            ),
            **{
                name: sum(int(receipt[name]) for receipt in self._receipts)
                for name in counts
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
        return validate_receipt(value)


class RobustPairedRuntimeTests(unittest.TestCase):
    def test_query_completion_is_fixed_visible_only_and_unique(self) -> None:
        queries = target.complete_visible_queries(
            "Research the visible public directory.", ["visible query"], limit=4
        )
        self.assertEqual(len(queries), 4)
        self.assertEqual(len({value.casefold() for value in queries}), 4)
        self.assertEqual(queries[0], "visible query")
        self.assertTrue(all("visible query" in value for value in queries))

    def test_robust_plan_stops_at_sentence_boundary(self) -> None:
        plan = target.validated_robust_plan(
            {"queries": ["one"]},
            QUESTION,
            ScoreFirstLimits(search_queries=4),
        )
        self.assertEqual(plan["columns"], ["Entity", "Value"])
        self.assertEqual(len(plan["queries"]), 4)
        self.assertEqual(plan["provider_unique_query_count"], 1)

    def test_full_chain_uses_four_queries_three_models_and_normalizer(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            model = DeadlineAwareGlobalModelSlotLimiter(
                InnerModel(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                search=SyntheticSearch(QUESTION),
                limits=ScoreFirstLimits(
                    wall_seconds=240,
                    model_calls=3,
                    search_queries=4,
                    fetch_targets=10,
                    search_results_per_query=3,
                    evidence_chars=60_000,
                    page_chars=5_000,
                ),
            )
        checked = target.validate_result(result)
        receipt = checked["content_free_receipt"]
        robust = checked["robust_runtime_receipt"]
        self.assertEqual(receipt["planned_query_count"], 4)
        self.assertEqual(receipt["executed_query_count"], 4)
        self.assertEqual(receipt["model_logical_call_count"], 3)
        self.assertTrue(all(checked["model_success"].values()))
        self.assertEqual(robust["provider_unique_query_count"], 1)
        self.assertEqual(robust["deterministically_added_query_count"], 3)
        self.assertEqual(robust["normalizer_recovery_count"], 2)
        for prediction in checked["predictions"].values():
            self.assertIn("| Entity | Value |", prediction)
            self.assertIn("| Late Entity |", prediction)

    def test_runtime_receipt_emits_no_content(self) -> None:
        receipt = target._runtime_receipt(
            {
                "provider_unique_query_count": 1,
                "first_synthesis_arm": target.CONTROL_ARM,
                "completed_query_count": 4,
                "deterministically_added_query_count": 3,
                "robust_visible_schema_column_count": 2,
                "normalizer_attempt_count": 2,
                "exact_table_count": 0,
                "normalizer_recovery_count": 2,
                "normalizer_unrecoverable_count": 0,
            }
        )
        encoded = json.dumps(receipt)
        for forbidden in ("Entity", "Value", "visible query", "Late Entity"):
            self.assertNotIn(forbidden, encoded)

    def test_explicit_arm_order_is_validated_and_applied(self) -> None:
        with self.assertRaisesRegex(ValueError, "arm order"):
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
                target.run_paired_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": QUESTION,
                    },
                    model=model,
                    search=SyntheticSearch(QUESTION),
                    limits=ScoreFirstLimits(
                        wall_seconds=240,
                        model_calls=3,
                        search_queries=4,
                        fetch_targets=10,
                        evidence_chars=60_000,
                        page_chars=5_000,
                    ),
                    arm_order=[target.CONTROL_ARM, target.CONTROL_ARM],
                )


if __name__ == "__main__":
    unittest.main()
