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

from deepwide_agent import v25002_page_visible_link_paired_runtime as parent  # noqa: E402
from deepwide_agent import v25004_identity_bound_detail_fields as projection  # noqa: E402
from deepwide_agent import v25006_detail_field_link_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    validate_receipt as validate_fetch_receipt,
)
from deepwide_agent.v25005_detail_field_fetch import (  # noqa: E402
    DetailFieldLatePageBoundSearchClient,
)


QUESTION = (
    "Use web search and the official Acme Package Index public page to return "
    "exactly one Markdown table. Include one row for <PACKAGE>AlphaKit</PACKAGE>. "
    "Column names: Package, Version, Published, License."
)


class SyntheticModel:
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
                    "columns": ["ignored"],
                    "queries": ["one long legacy provider query"],
                }
            )
        else:
            version = "9.9.9" if "9.9.9" in user else "Unknown"
            published = "2026-08-01" if "2026-08-01" in user else "Unknown"
            license_value = "Apache-2.0" if "Apache-2.0" in user else "Unknown"
            text = (
                "| Package | Version | Published | License |\n"
                "|---|---|---|---|\n"
                f"| AlphaKit | {version} | {published} | {license_value} |"
            )
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class SyntheticDetailFieldSearch(DetailFieldLatePageBoundSearchClient):
    def __init__(self, question: str, phase: str) -> None:
        self.calls = self.failures = self.tool_calls = 0
        self.fetch_calls = self.fetch_failures = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self._question = question
        self._phase = phase
        self._prefixes: dict[str, str] = {}
        self._receipts: list[dict] = []

    @staticmethod
    def _lead(url: str) -> dict[str, str]:
        return {"url": url, "fetch_url": url, "title": "Synthetic"}

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        if self._phase == target.FIRST_PHASE:
            sources = [
                self._lead(f"https://packages.acme.example/index-{index}")
                for index in range(6)
            ]
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
                "results": [self._lead("https://search.example/kept")],
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
            bound = "/web/packages/AlphaKit/" in url
            raw = (
                "Acme: Package AlphaKit\n"
                "AlphaKit synthetic detail\n"
                "Version: | 9.9.9\n"
                "Published: | 2026-08-01\n"
                "License: | Apache-2.0\n"
                + "Additional public detail line.\n" * 30
                if bound
                else "UNBOUND INDEX OR DETAIL MATERIAL\n" * 30
            )
            projected = projection.build_projection(
                self._question,
                {"title": "Acme: Package AlphaKit" if bound else "Index", "url": url, "text": raw},
            )
            self._prefixes[url] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            links = []
            if self._phase == target.FIRST_PHASE:
                links = [
                    {"url": "https://noise.example/one", "text": "Noise one"},
                    {"url": "https://noise.example/two", "text": "Noise two"},
                    {"url": "https://noise.example/three", "text": "Noise three"},
                    {
                        "url": "https://packages.acme.example/web/packages/AlphaKit/index.html",
                        "text": "AlphaKit",
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
                            "page_links": links,
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
            "projection_failure_count", "input_content_characters",
            "input_characters_beyond_parent_prefix", "discovered_record_count",
            "admissible_record_count", "admissible_bound_observation_count",
            "retained_record_count", "retained_bound_observation_count",
            "compact_prefix_characters", "raw_prefix_characters_retained",
            "output_characters", "positive_signed_credit_count",
        )
        value = {
            "artifact_version": 1,
            "role": "v24981_content_free_late_page_fetch_receipt",
            "policy_id": "v24981_hard_deadline_late_page_bound_fetch_v1",
            "fetch_calls_snapshot": self.fetch_calls,
            "fetch_failures_snapshot": self.fetch_failures,
            "helper_result_count": len(self._receipts),
            "projected_page_count": len(self._receipts),
            "mechanism_engaged_page_count": sum(row["mechanism_engaged"] for row in self._receipts),
            "exact_parent_prefix_handoff_page_count": sum(row["exact_parent_prefix_handoff"] for row in self._receipts),
            "candidate_evidence_changed_page_count": sum(row["candidate_evidence_changed"] for row in self._receipts),
            **{name: sum(int(row[name]) for row in self._receipts) for name in summed},
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


class DetailFieldLinkRuntimeBindingTests(unittest.TestCase):
    def test_production_shaped_link_detail_record_and_prediction_gain(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = SyntheticModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: SyntheticDetailFieldSearch(QUESTION, phase)
                for phase in target.PHASES
            }
            before = parent.RobustLatePageBoundSearchClient
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                searches=searches,
                limits=ScoreFirstLimits(
                    wall_seconds=240,
                    model_calls=3,
                    search_queries=4,
                    fetch_targets=10,
                    search_results_per_query=3,
                    evidence_chars=60_000,
                    page_chars=5_000,
                ),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
            self.assertIs(parent.RobustLatePageBoundSearchClient, before)
        receipt = result["content_free_receipt"]
        control = receipt["arm_metrics"][target.CONTROL_ARM]
        candidate = receipt["arm_metrics"][target.CANDIDATE_ARM]
        self.assertTrue(receipt["selection_changed"])
        self.assertEqual(receipt["bound_visible_link_gain"], 1)
        self.assertEqual(receipt["candidate_target_bound_projected_page_gain"], 1)
        self.assertEqual(receipt["candidate_target_bound_record_gain"], 1)
        self.assertTrue(receipt["target_bound_record_mechanism_engaged"])
        self.assertEqual(control["second_wave_target_bound_records"], 0)
        self.assertEqual(candidate["second_wave_target_bound_records"], 1)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("Unknown", result["predictions"][target.CONTROL_ARM])
        self.assertIn("9.9.9", result["predictions"][target.CANDIDATE_ARM])
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 14)
        self.assertEqual(inner.requests, 3)

    def test_binding_is_subclass_based_without_parent_mutation(self) -> None:
        before = parent.RobustLatePageBoundSearchClient
        target.validate_binding()
        self.assertIs(parent.RobustLatePageBoundSearchClient, before)
        self.assertTrue(
            issubclass(DetailFieldLatePageBoundSearchClient, before)
        )
        self.assertIs(target.validate_result, target.validate_result)

    def test_wrapper_exports_exact_parent_algorithm_surface(self) -> None:
        self.assertEqual(target.ARMS, parent.ARMS)
        self.assertEqual(target.PHASES, parent.PHASES)
        self.assertEqual(target.ROLE, parent.ROLE)
        self.assertEqual(target.RECEIPT_ROLE, parent.RECEIPT_ROLE)
        source = (
            ROOT / "src/deepwide_agent/v25006_detail_field_link_runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn("parent.run_paired_task", source)
        self.assertNotIn("parent.RobustLatePageBoundSearchClient =", source)
        self.assertNotIn("threading", source)

    def test_rejects_non_detail_clients_before_parent_effects(self) -> None:
        with self.assertRaisesRegex(ValueError, "two distinct detail-field"):
            target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": "x"},
                model=object(),
                searches={},
                limits=object(),
            )

    def test_module_has_no_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25006_detail_field_link_runtime.py"
        source_text = path.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os", "pathlib", "socket", "subprocess", "requests", "deepwidebench"
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden in (
            "answer_key", "benchmark_question_type", "results.csv", "ground_truth"
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
