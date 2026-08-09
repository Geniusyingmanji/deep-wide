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
SRC = ROOT / "src"
TESTS = ROOT / "tests"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25002_page_visible_link_paired_runtime as target,
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
    InnerModel,
    SyntheticRobustSearch,
)


QUESTION = (
    "Use web search and the official Acme Public Registry public page to "
    "return one table for <ENTITY>Alpha</ENTITY>. "
    "Column names: Entity, Value. The Value must come from the same official record."
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


def lead(url: str) -> dict[str, str]:
    return {"url": url, "fetch_url": url, "title": "Synthetic"}


class LinkSelectionModel(InnerModel):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
        self.requests += 1
        self.attempts += 1
        if json_mode:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["ignored"],
                    "queries": ["one long legacy provider query"],
                }
            )
        else:
            value = "999" if "999" in user else "111"
            text = f"| Entity | Value |\n|---|---|\n| Alpha | {value} |"
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class PageVisibleSyntheticSearch(SyntheticRobustSearch):
    def __init__(self, question: str, phase: str) -> None:
        super().__init__(question, "unused")
        self._phase = phase

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        if self._phase == target.FIRST_PHASE:
            sources = [lead(f"https://shared.example/page-{index}") for index in range(6)]
            return [
                {
                    "query": query,
                    "answer": "",
                    "results": copy.deepcopy(sources),
                    "error": None,
                    "provider": "synthetic",
                }
                for query in values
            ]
        return [
            {
                "query": values[0],
                "answer": "",
                "results": [lead("https://search.example/kept")],
                "error": None,
                "provider": "synthetic",
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
            if "registry.acme.example/records/alpha" in url:
                raw = "archive boilerplate\n" * 350 + "Entity | Value\nAlpha | 999\n"
            elif self._phase == target.FIRST_PHASE:
                raw = "SHARED MATERIAL 111\n" * 20
            else:
                raw = "CONTROL MATERIAL 111\n" * 20
            projected = build_projection(
                self._question,
                {"title": "Synthetic", "url": url, "text": raw},
            )
            self._prefixes[url] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            page_links = []
            if self._phase == target.FIRST_PHASE:
                page_links = [
                    {"url": "https://noise.example/one", "text": "Noise one"},
                    {"url": "https://noise.example/two", "text": "Noise two"},
                    {"url": "https://noise.example/three", "text": "Noise three"},
                    {
                        "url": "https://registry.acme.example/records/alpha.html",
                        "text": "Alpha official record",
                    },
                    {"url": "https://user:secret@example.org/private", "text": "bad"},
                ]
            output.append(
                {
                    "query": item.get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": "Synthetic",
                            "url": url,
                            "fetch_url": url,
                            "requested_url": url,
                            "raw_content": projected["projection"],
                            "content": "",
                            "page_links": page_links,
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-fetch",
                }
            )
        return output


class SearchPrefixFullSearch(PageVisibleSyntheticSearch):
    def search_many(self, queries, **kwargs):
        values = list(queries)
        if self._phase == target.FIRST_PHASE:
            return super().search_many(values, **kwargs)
        del kwargs
        self.calls += 1
        return [
            {
                "query": values[0],
                "answer": "",
                "results": [
                    lead("https://search.example/one"),
                    lead("https://search.example/two"),
                    lead("https://search.example/three"),
                    lead("https://search.example/four"),
                ],
                "error": None,
                "provider": "synthetic",
            },
            {
                "query": values[1],
                "answer": "",
                "results": [],
                "error": None,
                "provider": "synthetic",
            },
        ]


class NegativeRecordDeltaSearch(PageVisibleSyntheticSearch):
    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        output = []
        for item in values:
            url = str(item["url"])
            if "noise.example/three" in url:
                raw = "archive boilerplate\n" * 350 + "Entity | Value\nAlpha | 111\n"
            else:
                raw = "UNBOUND OR EMPTY RECORD MATERIAL\n" * 20
            projected = build_projection(
                self._question,
                {"title": "Synthetic", "url": url, "text": raw},
            )
            self._prefixes[url] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            page_links = []
            if self._phase == target.FIRST_PHASE:
                page_links = [
                    {"url": "https://noise.example/one", "text": "Noise one"},
                    {"url": "https://noise.example/two", "text": "Noise two"},
                    {"url": "https://noise.example/three", "text": "Noise three"},
                    {
                        "url": "https://registry.acme.example/records/alpha.html",
                        "text": "Alpha official record",
                    },
                ]
            output.append(
                {
                    "query": item.get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": "Synthetic",
                            "url": url,
                            "fetch_url": url,
                            "requested_url": url,
                            "raw_content": projected["projection"],
                            "content": "",
                            "page_links": page_links,
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-fetch",
                }
            )
        return output


class PageVisibleLinkRuntimeTests(unittest.TestCase):
    def _run(self, *, second_type=PageVisibleSyntheticSearch):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = LinkSelectionModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                target.FIRST_PHASE: PageVisibleSyntheticSearch(
                    QUESTION, target.FIRST_PHASE
                ),
                target.SECOND_PHASE: second_type(QUESTION, target.SECOND_PHASE),
            }
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        return inner, searches, target.validate_result(result)

    def test_search_prefix_plus_visible_links_union_and_record_gain(self) -> None:
        inner, searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["visible_link_strategy_eligible"])
        self.assertTrue(receipt["selection_changed"])
        self.assertTrue(receipt["target_bound_record_mechanism_engaged"])
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertEqual(receipt["physical_fetch_count"], 11)
        self.assertEqual(receipt["model_logical_call_count"], 3)
        self.assertEqual(inner.requests, 3)
        self.assertEqual(searches[target.FIRST_PHASE].fetch_calls, 6)
        self.assertEqual(searches[target.SECOND_PHASE].fetch_calls, 5)
        control = receipt["arm_metrics"][target.CONTROL_ARM]
        candidate = receipt["arm_metrics"][target.CANDIDATE_ARM]
        self.assertEqual(control["logical_fetch_attempts"], 10)
        self.assertEqual(candidate["logical_fetch_attempts"], 10)
        self.assertEqual(control["second_wave_search_prefix_urls"], 1)
        self.assertEqual(candidate["second_wave_search_prefix_urls"], 1)
        self.assertEqual(control["second_wave_visible_link_urls"], 3)
        self.assertEqual(candidate["second_wave_visible_link_urls"], 3)
        self.assertEqual(control["second_wave_bound_visible_links"], 0)
        self.assertEqual(candidate["second_wave_bound_visible_links"], 1)
        self.assertEqual(control["second_wave_target_bound_records"], 0)
        self.assertEqual(candidate["second_wave_target_bound_records"], 1)
        self.assertEqual(len(set(result["evidence_characters"].values())), 1)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])

    def test_full_search_prefix_leaves_no_link_treatment(self) -> None:
        _inner, searches, result = self._run(second_type=SearchPrefixFullSearch)
        receipt = result["content_free_receipt"]
        self.assertFalse(receipt["selection_changed"])
        self.assertEqual(
            receipt["arm_metrics"][target.CONTROL_ARM][
                "second_wave_visible_link_urls"
            ],
            0,
        )
        self.assertEqual(searches[target.SECOND_PHASE].fetch_calls, 4)
        self.assertFalse(result["prediction_changed"])

    def test_negative_record_delta_is_valid_terminal_no_go(self) -> None:
        _inner, _searches, result = self._run(second_type=NegativeRecordDeltaSearch)
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["selection_changed"])
        self.assertEqual(receipt["bound_visible_link_gain"], 1)
        self.assertEqual(receipt["candidate_target_bound_projected_page_gain"], -1)
        self.assertEqual(receipt["candidate_target_bound_record_gain"], -1)
        self.assertFalse(receipt["target_bound_record_mechanism_engaged"])

    def test_resealed_nested_tamper_fails_closed(self) -> None:
        _inner, _searches, result = self._run()
        tampered = copy.deepcopy(result)
        tampered["content_free_receipt"]["arm_metrics"][target.CANDIDATE_ARM][
            "second_wave_target_bound_records"
        ] = 2
        tampered["content_free_receipt"].pop("receipt_payload_sha256")
        tampered["content_free_receipt"]["receipt_payload_sha256"] = payload_sha256(
            tampered["content_free_receipt"]
        )
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_result(tampered)

        nested = copy.deepcopy(result)
        nested["physical_wave_receipts"][target.SECOND_PHASE][
            "physical_union_fetch_count"
        ] = 8
        nested["physical_wave_receipts"][target.SECOND_PHASE].pop(
            "receipt_payload_sha256"
        )
        nested["physical_wave_receipts"][target.SECOND_PHASE][
            "receipt_payload_sha256"
        ] = payload_sha256(nested["physical_wave_receipts"][target.SECOND_PHASE])
        nested.pop("result_payload_sha256")
        nested["result_payload_sha256"] = payload_sha256(nested)
        with self.assertRaises(ValueError):
            target.validate_result(nested)

        jointly_resealed = copy.deepcopy(result)
        selection = jointly_resealed["selection_receipt"]
        selection["candidate_selected_visible_link_count"] = 2
        selection["candidate_total_selected_url_count"] = 3
        selection.pop("receipt_payload_sha256")
        selection["receipt_payload_sha256"] = payload_sha256(selection)
        phase = jointly_resealed["physical_wave_receipts"][target.SECOND_PHASE]
        phase["selection_receipt"] = copy.deepcopy(selection)
        phase["candidate_selected_visible_link_count"] = 2
        phase["candidate_total_selected_url_count"] = 3
        phase.pop("receipt_payload_sha256")
        phase["receipt_payload_sha256"] = payload_sha256(phase)
        jointly_resealed["content_free_receipt"]["arm_metrics"][
            target.CANDIDATE_ARM
        ]["second_wave_visible_link_urls"] = 2
        jointly_resealed["content_free_receipt"]["arm_metrics"][
            target.CANDIDATE_ARM
        ]["logical_fetch_attempts"] = 9
        jointly_resealed["content_free_receipt"].pop("receipt_payload_sha256")
        jointly_resealed["content_free_receipt"][
            "receipt_payload_sha256"
        ] = payload_sha256(jointly_resealed["content_free_receipt"])
        jointly_resealed.pop("result_payload_sha256")
        jointly_resealed["result_payload_sha256"] = payload_sha256(jointly_resealed)
        with self.assertRaises(ValueError):
            target.validate_result(jointly_resealed)

    def test_rejects_extra_task_metadata(self) -> None:
        with self.assertRaises(ValueError):
            target.run_paired_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": QUESTION,
                    "category": "hidden",
                },
                model=object(),
                searches={},
                limits=limits(),
            )

    def test_runtime_has_no_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25002_page_visible_link_paired_runtime.py"
        source_text = path.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in ("os", "pathlib", "subprocess", "requests", "deepwidebench"):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden in (
            "answer_key",
            "benchmark_question_type",
            "results.csv",
            "ground_truth",
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
