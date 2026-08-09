from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25002_page_visible_link_paired_runtime as parent  # noqa: E402
from deepwide_agent import v25004_identity_bound_detail_fields as projection  # noqa: E402
from deepwide_agent import v25011_attested_detail_observed_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    validate_receipt as validate_parent_projection_receipt,
)
from deepwide_agent.v25009_detail_stage_observer_fetch import (  # noqa: E402
    DetailStageObservedSearchClient,
    _observer_receipt,
)


QUESTION = (
    "Use web search and the official Acme Package Index public page to return "
    "exactly one Markdown table. Include one row for <PACKAGE>AlphaKit</PACKAGE>. "
    "Column names: Package, Version, Published, License."
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


def _parent_aggregate(receipts: list[dict], *, fetch_calls: int, fetch_failures: int):
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
        "fetch_calls_snapshot": fetch_calls,
        "fetch_failures_snapshot": fetch_failures,
        "helper_result_count": len(receipts),
        "projected_page_count": len(receipts),
        "mechanism_engaged_page_count": sum(row["mechanism_engaged"] for row in receipts),
        "exact_parent_prefix_handoff_page_count": sum(
            row["exact_parent_prefix_handoff"] for row in receipts
        ),
        "candidate_evidence_changed_page_count": sum(
            row["candidate_evidence_changed"] for row in receipts
        ),
        **{name: sum(int(row[name]) for row in receipts) for name in summed},
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
    return validate_parent_projection_receipt(value)


class SyntheticObservedSearch(DetailStageObservedSearchClient):
    def __init__(self, question: str, phase: str, *, identity: str = "AlphaKit") -> None:
        self.calls = self.failures = self.tool_calls = 0
        self.fetch_calls = self.fetch_failures = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self._question = question
        self._phase = phase
        self._identity = identity
        self._prefixes: dict[str, str] = {}
        self._parent_receipts: list[dict] = []
        self._detail_receipts: list[dict] = []

    @staticmethod
    def _lead(url: str) -> dict[str, str]:
        return {"url": url, "fetch_url": url, "title": "Synthetic"}

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        if self._phase == target.FIRST_PHASE:
            sources = [self._lead("https://packages.acme.example/web/packages/")]
            sources.extend(
                self._lead(f"https://unrelated.example/index-{index}/")
                for index in range(5)
            )
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
            bound = f"/{self._identity}/" in url
            raw = (
                f"Acme: Package {self._identity}\n"
                f"{self._identity} synthetic detail\n"
                "Version: | 9.9.9\n"
                "Published: | 2026-08-01\n"
                "License: | Apache-2.0\n"
                + "Additional public detail line.\n" * 30
                if bound
                else "UNBOUND INDEX OR DETAIL MATERIAL\n" * 30
            )
            projected = projection.build_projection(
                self._question,
                {
                    "title": f"Acme: Package {self._identity}" if bound else "Index",
                    "url": url,
                    "text": raw,
                },
            )
            self._prefixes[url] = raw[:5_000]
            self._parent_receipts.append(projected["content_free_receipt"])
            self._detail_receipts.append(projected["detail_field_receipt"])
            links = []
            if (
                self._phase == target.FIRST_PHASE
                and url == "https://packages.acme.example/web/packages/"
            ):
                links = [
                    {"url": "noise-one/", "text": "Noise one"},
                    {"url": "noise-two/", "text": "Noise two"},
                    {"url": "noise-three/", "text": "Noise three"},
                    {
                        "url": f"{self._identity}/index.html",
                        "text": f"{self._identity} package detail",
                    },
                    {
                        "url": f"https://elsewhere.example/{self._identity}/index.html",
                        "text": "cross origin",
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
        return _parent_aggregate(
            self._parent_receipts,
            fetch_calls=self.fetch_calls,
            fetch_failures=self.fetch_failures,
        )

    def detail_stage_observer_receipt(self):
        return _observer_receipt(
            self._detail_receipts,
            invalid_envelopes=0,
            parent_fetch_calls=self.fetch_calls,
            parent_helper_results=len(self._parent_receipts),
        )


class AttestedDetailObservedRuntimeTests(unittest.TestCase):
    def _run(self, *, identity: str = "AlphaKit"):
        question = QUESTION.replace("AlphaKit", identity)
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
                phase: SyntheticObservedSearch(question, phase, identity=identity)
                for phase in target.PHASES
            }
            result = target.run_paired_task(
                {
                    "opaque_id": "task_" + ("0" if identity == "AlphaKit" else "1") * 24,
                    "question": question,
                },
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        return inner, result

    def test_production_shaped_attested_record_and_prediction_gain(self) -> None:
        inner, envelope = self._run()
        result = envelope["parent_result"]
        receipt = result["content_free_receipt"]
        attested = envelope["attested_selection_receipt"]
        control = receipt["arm_metrics"][target.CONTROL_ARM]
        candidate = receipt["arm_metrics"][target.CANDIDATE_ARM]
        self.assertTrue(attested["selection_changed"])
        self.assertEqual(attested["attested_child_detail_link_gain"], 1)
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

    def test_observer_funnel_is_bound_to_parent_projection_receipts(self) -> None:
        _, envelope = self._run()
        parent_result = envelope["parent_result"]
        observers = envelope["detail_stage_observer_receipts"]
        for phase in target.PHASES:
            parent_fetch = parent_result["physical_wave_receipts"][phase]["fetch_receipt"]
            observed = observers[phase]
            self.assertEqual(
                observed["observed_detail_receipt_count"],
                parent_fetch["projected_page_count"],
            )
            self.assertEqual(
                observed["retained_record_count"],
                parent_fetch["retained_record_count"],
            )
            self.assertEqual(observed["invalid_observer_envelope_count"], 0)
        second = observers[target.SECOND_PHASE]
        self.assertGreater(second["identity_url_path_bound_page_count"], 0)
        self.assertGreater(second["discovered_record_page_count"], 0)

    def test_parent_module_globals_are_not_mutated(self) -> None:
        before_selector = parent.select_page_visible_link_prefixes
        before_second = parent._run_second_wave
        target.validate_binding()
        self._run()
        self.assertIs(parent.select_page_visible_link_prefixes, before_selector)
        self.assertIs(parent._run_second_wave, before_second)

    def test_context_local_receipts_do_not_cross_concurrent_tasks(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self._run, identity=identity)
                for identity in ("AlphaKit", "BetaKit")
            ]
            results = [future.result()[1] for future in futures]
        for result in results:
            self.assertEqual(
                result["attested_selection_receipt"][
                    "attested_child_detail_link_gain"
                ],
                1,
            )
            target.validate_result(result)

    def test_resealed_nested_tamper_is_rejected(self) -> None:
        _, envelope = self._run()
        changed = copy.deepcopy(envelope)
        changed["attested_selection_receipt"][
            "candidate_attested_child_detail_link_count"
        ] = 0
        changed["attested_selection_receipt"]["attested_child_detail_link_gain"] = 0
        selection = changed["attested_selection_receipt"]
        selection.pop("receipt_payload_sha256")
        selection["receipt_payload_sha256"] = payload_sha256(selection)
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(changed)

        changed = copy.deepcopy(envelope)
        observer = changed["detail_stage_observer_receipts"][target.SECOND_PHASE]
        observer["retained_record_count"] = 0
        observer.pop("receipt_payload_sha256")
        observer["receipt_payload_sha256"] = payload_sha256(observer)
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(changed)

    def test_rejects_nonobserved_clients_before_effects(self) -> None:
        with self.assertRaisesRegex(ValueError, "two distinct observed detail"):
            target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": "x"},
                model=object(),
                searches={},
                limits=object(),
            )

    def test_module_has_no_direct_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25011_attested_detail_observed_runtime.py"
        source_text = path.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "socket",
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
        for forbidden in (
            "answer_key",
            "benchmark_question_type",
            "results.csv",
            "ground_truth",
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
