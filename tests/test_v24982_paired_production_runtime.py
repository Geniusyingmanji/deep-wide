from __future__ import annotations

import copy
import json
import tempfile
import time
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24982_paired_production_runtime as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from deepwide_agent.v24980_late_page_bound_projection import build_projection  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import LatePageBoundSearchClient  # noqa: E402


class FakeSearch:
    def __init__(self) -> None:
        self.prefix = {"https://official.example/data": "raw-prefix-padding"}

    def parent_prefix_for(self, url: str) -> str:
        return self.prefix.get(url, "")


class InnerModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
        self.requests += 1
        self.attempts += 1
        if json_mode:
            text = json.dumps({
                "language": "English",
                "columns": ["Entity", "Value"],
                "row_target_hint": "",
                "queries": ["q1", "q2", "q3", "q4"],
            })
        else:
            text = (
                "```markdown\n| Entity | Value |\n|---|---|\n"
                + ("| Late Entity | 999 |" if "999" in user else "| Late Entity | Unknown |")
                + "\n```"
            )
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class SyntheticProductionSearch(LatePageBoundSearchClient):
    def __init__(self, *, question: str) -> None:
        # Keep the real production class identity while avoiding construction
        # of network helpers in this end-to-end accounting test.
        self.calls = self.failures = self.tool_calls = 0
        self.fetch_calls = self.fetch_failures = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self._question = question
        self._prefixes = {}
        self._receipts = []

    def search_many(self, queries, **kwargs):
        del kwargs
        self.calls += 1
        sources = [
            {
                "url": f"https://official.example/data/{index}",
                "fetch_url": f"https://official.example/data/{index}",
                "title": f"Source {index}",
            }
            for index in range(1, 6)
        ]
        return [
            {
                "query": query,
                "answer": "",
                "results": [],
                "error": "hosted search returned no query-local URL citation",
                "provider": "synthetic",
                "hosted_search_trace": {"actions": [{"sources": sources}]},
            }
            for query in queries
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        output = []
        for item in values:
            url = item["url"]
            raw = (
                "archive boilerplate\n" * 350
                + "| Entity | Value |\n|---|---|\n| Late Entity | 999 |\n"
            )
            projected = build_projection(
                self._question, {"title": "Official", "url": url, "text": raw}
            )
            self._prefixes[url] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            output.append({
                "query": item.get("query", ""),
                "answer": "",
                "results": [{
                    "title": "Official", "url": url, "fetch_url": url,
                    "raw_content": projected["projection"], "content": "",
                }],
                "error": None,
                "provider": "synthetic-fetch",
            })
        return output

    def parent_prefix_for(self, url):
        return self._prefixes.get(url, "")

    def late_page_projection_receipt(self):
        from deepwide_agent.v24981_late_page_bound_fetch import validate_receipt
        from deepwide_agent.v24263_global_model_limiter import payload_sha256

        counts = {
            "projection_failure_count", "input_content_characters",
            "input_characters_beyond_parent_prefix", "discovered_record_count",
            "admissible_record_count", "admissible_bound_observation_count",
            "retained_record_count", "retained_bound_observation_count",
            "compact_prefix_characters", "raw_prefix_characters_retained",
            "output_characters", "positive_signed_credit_count",
        }
        value = {
            "artifact_version": 1,
            "role": "v24981_content_free_late_page_fetch_receipt",
            "policy_id": "v24981_hard_deadline_late_page_bound_fetch_v1",
            "fetch_calls_snapshot": self.fetch_calls,
            "fetch_failures_snapshot": self.fetch_failures,
            "helper_result_count": len(self._receipts),
            "projected_page_count": len(self._receipts),
            "mechanism_engaged_page_count": sum(r["mechanism_engaged"] for r in self._receipts),
            "exact_parent_prefix_handoff_page_count": sum(r["exact_parent_prefix_handoff"] for r in self._receipts),
            "candidate_evidence_changed_page_count": sum(r["candidate_evidence_changed"] for r in self._receipts),
            **{name: sum(int(r[name]) for r in self._receipts) for name in counts},
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


class V24982PairedProductionRuntimeTests(unittest.TestCase):
    def test_evidence_arms_share_order_and_differ_only_in_page_text(self) -> None:
        pages = [
            {
                "title": "Official",
                "url": "https://official.example/data",
                "content": "compact-candidate",
            }
        ]
        limits = ScoreFirstLimits(
            wall_seconds=240,
            model_calls=3,
            search_queries=4,
            fetch_targets=10,
            search_results_per_query=3,
            evidence_chars=60_000,
            page_chars=5_000,
        )
        control = target._evidence(
            pages, search=FakeSearch(), limits=limits, arm=target.CONTROL_ARM
        )
        candidate = target._evidence(
            pages, search=FakeSearch(), limits=limits, arm=target.CANDIDATE_ARM
        )
        self.assertIn("raw-prefix-padding", control)
        self.assertNotIn("compact-candidate", control)
        self.assertIn("compact-candidate", candidate)
        self.assertEqual(
            control.split("content=", 1)[0], candidate.split("content=", 1)[0]
        )

    def test_missing_shadow_prefix_fails_closed(self) -> None:
        limits = ScoreFirstLimits(
            wall_seconds=240, model_calls=3, search_queries=4,
            fetch_targets=10, evidence_chars=60_000, page_chars=5_000,
        )
        with self.assertRaises(RuntimeError):
            target._evidence(
                [{"title": "x", "url": "https://missing.example", "content": "y"}],
                search=FakeSearch(), limits=limits, arm=target.CONTROL_ARM,
            )

    def test_receipt_accepts_exact_budget_and_rejects_expansion(self) -> None:
        value = target._receipt(
            {
                "planned_query_count": 4,
                "executed_query_count": 4,
                "fetch_attempt_count": 10,
                "usable_page_count": 10,
                "model_logical_call_count": 3,
                "model_provider_request_count": 3,
                "model_provider_attempt_count": 3,
                "control_evidence_characters": 50_000,
                "candidate_evidence_characters": 50_000,
                "candidate_changed_page_count": 4,
                "mechanism_engaged_page_count": 4,
                "prediction_changed": True,
                "both_arms_model_success": True,
            }
        )
        self.assertEqual(target.validate_receipt(value), value)
        tampered = copy.deepcopy(value)
        tampered["fetch_attempt_count"] = 11
        with self.assertRaises(ValueError):
            target.validate_receipt(tampered)

    def test_fixed_controller_has_zero_entropy_weight(self) -> None:
        from deepwide_agent.v24799_fixed_full_budget_control import POLICY_VALUES

        self.assertEqual(POLICY_VALUES["information_gain_weight"], 0.0)
        self.assertEqual(POLICY_VALUES["latency_loss_per_second"], 0.0)

    def test_arm_order_is_deterministic_and_balanced_surface(self) -> None:
        left = target._arm_order("task_000000000000000000000000")
        right = target._arm_order("task_000000000000000000000000")
        self.assertEqual(left, right)
        self.assertEqual(set(left), set(target.ARMS))

    def test_fallback_preserves_visible_columns(self) -> None:
        value = target._fallback(["Entity", "Value"])
        self.assertIn("| Entity | Value |", value)
        self.assertIn("| Unknown | Unknown |", value)

    def test_full_production_shaped_chain_conserves_three_model_calls(self) -> None:
        question = "Return one table. Column names: Entity, Value"
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
            search = SyntheticProductionSearch(question=question)
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": question},
                model=model,
                search=search,
                limits=ScoreFirstLimits(
                    wall_seconds=240, model_calls=3, search_queries=4,
                    fetch_targets=10, search_results_per_query=3,
                    evidence_chars=60_000, page_chars=5_000,
                ),
            )
        checked = target.validate_result(result)
        receipt = checked["content_free_receipt"]
        self.assertEqual(receipt["model_logical_call_count"], 3)
        self.assertEqual(receipt["model_provider_request_count"], 3)
        self.assertEqual(receipt["executed_query_count"], 4)
        self.assertLessEqual(receipt["fetch_attempt_count"], 10)
        self.assertGreater(receipt["mechanism_engaged_page_count"], 0)
        self.assertTrue(checked["model_success"][target.CONTROL_ARM])
        self.assertTrue(checked["model_success"][target.CANDIDATE_ARM])
        self.assertTrue(checked["prediction_changed"])


if __name__ == "__main__":
    unittest.main()
