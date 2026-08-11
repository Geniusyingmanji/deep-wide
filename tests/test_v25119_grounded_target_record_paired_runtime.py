from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25119_grounded_target_record_paired_runtime as target,
)
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24984_robust_late_page_projection import (  # noqa: E402
    build_projection,
)
from test_v24990_query_vector_paired_runtime import (  # noqa: E402
    SyntheticRobustSearch,
)


QUESTION = (
    "A country has capital New Delhi and currency INR. Resolve the country, "
    "then use the visible IANA Root Zone Database authority to return one table. "
    "Columns exactly: Domain | Type | TLD Manager. Preserve exact spelling."
)
OPAQUE_TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": QUESTION,
}


def limits(**changes: int) -> ScoreFirstLimits:
    values = {
        "wall_seconds": 240,
        "model_calls": 3,
        "search_queries": 4,
        "fetch_targets": 10,
        "search_results_per_query": 3,
        "evidence_chars": 60_000,
        "page_chars": 5_000,
    }
    values.update(changes)
    return ScoreFirstLimits(**values)


def lead(url: str, title: str = "Noise") -> dict[str, str]:
    return {"url": url, "fetch_url": url, "title": title}


class GroundedAttributionModel:
    def __init__(
        self,
        *,
        grounded_output: str = "valid",
        alternate_unexposed: bool = False,
    ) -> None:
        self.grounded_output = grounded_output
        self.alternate_unexposed = alternate_unexposed
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = self.synthesis_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
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
                    "columns": ["provider column must be ignored"],
                    "queries": [
                        "capital New Delhi currency INR country",
                        "New Delhi INR official source",
                        "country domain type",
                        "country TLD manager",
                    ],
                }
            )
        elif self.logical_calls == 2:
            if self.grounded_output == "valid":
                text = json.dumps(
                    {
                        "pivots": ["India"],
                        "row_targets": [".in"],
                        "authority_terms": ["IANA Root Zone Database"],
                        "queries": [
                            "India .in Domain Type IANA",
                            "India .in TLD Manager IANA",
                        ],
                    }
                )
            else:
                text = "not-json"
        else:
            self.synthesis_calls += 1
            if "999" in user:
                value = "999"
            elif self.alternate_unexposed:
                value = "111" if self.synthesis_calls == 1 else "222"
            else:
                value = "111"
            text = (
                "| Domain | Type | TLD Manager |\n"
                "|---|---|---|\n"
                f"| .in | country-code | {value} |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class GroundedFrontierSearch(SyntheticRobustSearch):
    def __init__(self, question: str, phase: str, *, field_page: bool = True) -> None:
        super().__init__(question, "unused")
        self._phase = phase
        self._field_page = field_page

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        if self._phase == target.FIRST_PHASE:
            return [
                {
                    "query": query,
                    "answer": "",
                    "results": [
                        lead(
                            f"https://public.example/country-{query_index}-{item_index}",
                            "Country profile",
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
                                    "https://www.iana.org/domains/root/db/records/in.html",
                                    "IN record detail",
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
            if self._phase == target.FIRST_PHASE and "country-0-0" in url:
                raw = (
                    "India is the country whose capital is New Delhi and currency is "
                    "INR. Its country-code top-level domain is .in."
                )
            elif self._phase == target.FIRST_PHASE:
                raw = "Public country background material."
            elif "iana.org/domains/root/db/records/in.html" in url:
                raw = (
                    "Domain | Type | TLD Manager\n.in | country-code | 999\n"
                    if self._field_page
                    else "A narrow registry entry for .in with the requested fields omitted."
                )
            else:
                raw = "Stable control material 111."
            projected = build_projection(
                self._question,
                {"title": "Official record", "url": url, "text": raw},
            )
            self._prefixes[url] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            output.append(
                {
                    "query": item.get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": "Official record",
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


class FailingFirstWaveSearch(GroundedFrontierSearch):
    def search_many(self, queries, **kwargs):
        del kwargs
        list(queries)
        self.calls += 1
        self.failures += 1
        raise RuntimeError("synthetic first-wave failure")


class GroundedTargetRecordPairedRuntimeTests(unittest.TestCase):
    def _run(
        self,
        *,
        grounded_output: str = "valid",
        field_page: bool = True,
        alternate_unexposed: bool = False,
        fail_first: bool = False,
    ):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = GroundedAttributionModel(
                grounded_output=grounded_output,
                alternate_unexposed=alternate_unexposed,
            )
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            first_type = FailingFirstWaveSearch if fail_first else GroundedFrontierSearch
            searches = {
                target.FIRST_PHASE: first_type(
                    QUESTION, target.FIRST_PHASE, field_page=field_page
                ),
                target.SECOND_PHASE: GroundedFrontierSearch(
                    QUESTION, target.SECOND_PHASE, field_page=field_page
                ),
            }
            result = target.run_paired_task(
                OPAQUE_TASK,
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=target.ARMS,
            )
        return inner, searches, target.validate_result(result)

    def test_grounded_field_page_gain_and_prediction_change_are_attributable(self) -> None:
        inner, searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertTrue(receipt["grounded_plan_strategy_applied"])
        self.assertTrue(receipt["selection_strategy_eligible"])
        self.assertTrue(receipt["selection_changed"])
        self.assertGreater(receipt["target_field_page_gain"], 0)
        self.assertGreater(receipt["target_field_pair_gain"], 0)
        self.assertTrue(receipt["retrieval_mechanism_engaged"])
        self.assertTrue(receipt["prediction_changed"])
        self.assertTrue(receipt["attributable_prediction_change"])
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 14)
        self.assertEqual(searches[target.FIRST_PHASE].calls, 1)
        self.assertEqual(searches[target.FIRST_PHASE].fetch_calls, 6)
        self.assertEqual(searches[target.SECOND_PHASE].calls, 1)
        self.assertEqual(searches[target.SECOND_PHASE].fetch_calls, 5)
        for arm in target.ARMS:
            metric = receipt["arm_metrics"][arm]
            self.assertEqual(metric["effective_model_logical_call_count"], 3)
            self.assertEqual(metric["executed_query_count"], 4)
            self.assertLessEqual(metric["logical_fetch_count"], 10)
            self.assertTrue(metric["model_success"])
        self.assertEqual(
            receipt["control_evidence_characters"],
            receipt["candidate_evidence_characters"],
        )
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])

    def test_invalid_grounded_output_is_exact_legacy_selection_handoff(self) -> None:
        inner, _searches, result = self._run(grounded_output="invalid")
        plan = result["grounded_plan_receipt"]
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertTrue(plan["model_call_attempted"])
        self.assertFalse(plan["model_output_strictly_valid"])
        self.assertTrue(plan["exact_legacy_second_wave_handoff"])
        self.assertFalse(receipt["grounded_plan_strategy_applied"])
        self.assertFalse(receipt["selection_changed"])
        self.assertFalse(receipt["retrieval_mechanism_engaged"])
        self.assertFalse(receipt["attributable_prediction_change"])
        self.assertEqual(
            result["predictions"][target.CONTROL_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )

    def test_selection_change_without_field_page_gain_gets_zero_credit(self) -> None:
        _inner, _searches, result = self._run(
            field_page=False,
            alternate_unexposed=True,
        )
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["selection_changed"])
        self.assertEqual(receipt["target_field_page_gain"], 0)
        self.assertTrue(receipt["prediction_changed"])
        self.assertFalse(receipt["retrieval_mechanism_engaged"])
        self.assertFalse(receipt["attributable_prediction_change"])

    def test_first_wave_failure_stops_grounded_plan_and_synthesis_without_retry(self) -> None:
        inner, searches, result = self._run(fail_first=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 1)
        self.assertEqual(inner.synthesis_calls, 0)
        self.assertFalse(receipt["shared_first_wave_completed"])
        self.assertFalse(receipt["grounded_plan_model_call_attempted"])
        self.assertFalse(receipt["shared_second_wave_completed"])
        self.assertEqual(receipt["first_synthesis_arm"], "none")
        self.assertEqual(receipt["physical_model_logical_call_count"], 1)
        self.assertEqual(searches[target.FIRST_PHASE].calls, 1)
        self.assertEqual(searches[target.SECOND_PHASE].calls, 0)
        self.assertFalse(any(result["model_success"].values()))

    def test_shared_client_budget_drift_and_privileged_task_fail_before_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = GroundedAttributionModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            shared = GroundedFrontierSearch(QUESTION, target.FIRST_PHASE)
            with self.assertRaisesRegex(ValueError, "distinct robust search"):
                target.run_paired_task(
                    OPAQUE_TASK,
                    model=model,
                    searches={phase: shared for phase in target.PHASES},
                    limits=limits(),
                )
            distinct = {
                target.FIRST_PHASE: GroundedFrontierSearch(
                    QUESTION, target.FIRST_PHASE
                ),
                target.SECOND_PHASE: GroundedFrontierSearch(
                    QUESTION, target.SECOND_PHASE
                ),
            }
            with self.assertRaisesRegex(ValueError, "budget drifted"):
                target.run_paired_task(
                    OPAQUE_TASK,
                    model=model,
                    searches=distinct,
                    limits=limits(model_calls=2),
                )
            with self.assertRaisesRegex(ValueError, "privileged"):
                target.run_paired_task(
                    {**OPAQUE_TASK, "category": "forbidden"},
                    model=model,
                    searches=distinct,
                    limits=limits(),
                )
        self.assertEqual(inner.requests, 0)

    def test_resealed_receipt_or_result_metadata_tamper_fails_closed(self) -> None:
        _inner, _searches, result = self._run()
        for kind in (
            "launch",
            "physical_effect",
            "arm_fetch",
            "model_cost",
            "wave_fetch",
        ):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if kind == "launch":
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            elif kind == "physical_effect":
                changed["physical_effects"][target.SECOND_PHASE][
                    "fetch_requests"
                ] -= 1
            elif kind == "arm_fetch":
                receipt["arm_metrics"][target.CANDIDATE_ARM][
                    "logical_fetch_count"
                ] -= 1
            elif kind == "model_cost":
                changed["cost"]["model"]["requests"] -= 1
            else:
                wave = changed["physical_wave_receipts"][target.SECOND_PHASE]
                wave["physical_union_fetch_count"] -= 1
                wave.pop("receipt_payload_sha256")
                wave["receipt_payload_sha256"] = payload_sha256(wave)
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

        extra = copy.deepcopy(result)
        extra["question_type"] = "forbidden"
        extra.pop("result_payload_sha256")
        extra["result_payload_sha256"] = payload_sha256(extra)
        with self.assertRaises(ValueError):
            target.validate_result(extra)

    def test_receipt_is_content_free_and_runtime_ast_is_label_blind(self) -> None:
        _inner, _searches, result = self._run()
        encoded = json.dumps(result["content_free_receipt"], ensure_ascii=False)
        for forbidden in (
            "India",
            "New Delhi",
            ".in",
            "IANA",
            "https://",
            "111",
            "999",
            OPAQUE_TASK["opaque_id"],
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            result["content_free_receipt"]
            ["entropy_or_information_gain_assigns_signed_credit"]
        )

        source_path = (
            ROOT
            / "src/deepwide_agent/v25119_grounded_target_record_paired_runtime.py"
        )
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in ("os", "pathlib", "subprocess", "requests", "socket"):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
