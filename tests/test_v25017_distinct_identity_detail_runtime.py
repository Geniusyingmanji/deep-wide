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
from deepwide_agent import v25014_multi_identity_detail_fields as projection  # noqa: E402
from deepwide_agent import v25017_distinct_identity_detail_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    validate_receipt as validate_parent_projection_receipt,
)
from deepwide_agent.v25016_multi_identity_detail_fetch import (  # noqa: E402
    MultiIdentityDetailSearchClient,
)


QUESTION = """Use web search and the official Acme Package Index public page to return one Markdown table.
<PACKAGES>
1. AlphaKit
2. BetaCore
3. GammaTools
</PACKAGES>
Column names: Package, Version, Published, License. Return one table only."""


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
            rows = []
            for identity, version, published, license_value in (
                ("AlphaKit", "1.0.1", "2026-08-01", "MIT"),
                ("BetaCore", "2.0.2", "2026-08-02", "Apache-2.0"),
                ("GammaTools", "3.0.3", "2026-08-03", "BSD-3-Clause"),
            ):
                present = version in user and published in user and license_value in user
                rows.append(
                    f"| {identity} | {version if present else 'Unknown'} | "
                    f"{published if present else 'Unknown'} | "
                    f"{license_value if present else 'Unknown'} |"
                )
            text = "\n".join(
                (
                    "| Package | Version | Published | License |",
                    "|---|---|---|---|",
                    *rows,
                )
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


class SyntheticMultiSearch(MultiIdentityDetailSearchClient):
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

    @staticmethod
    def _record(identity: str) -> tuple[str, str, str]:
        return {
            "AlphaKit": ("1.0.1", "2026-08-01", "MIT"),
            "BetaCore": ("2.0.2", "2026-08-02", "Apache-2.0"),
            "GammaTools": ("3.0.3", "2026-08-03", "BSD-3-Clause"),
        }[identity]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        output = []
        for item in values:
            url = str(item["url"])
            identity = next(
                (name for name in ("AlphaKit", "BetaCore", "GammaTools") if f"/{name}/" in url),
                None,
            )
            if identity is None:
                raw = "UNBOUND INDEX OR DETAIL MATERIAL\n" * 30
                title = "Index"
            else:
                version, published, license_value = self._record(identity)
                raw = (
                    f"Acme: Package {identity}\n"
                    f"{identity} synthetic detail\n"
                    f"Version: | {version}\n"
                    f"Published: | {published}\n"
                    f"License: | {license_value}\n"
                    + "Additional public detail line.\n" * 30
                )
                title = f"Acme: Package {identity}"
            projected = projection.build_projection(
                self._question,
                {"title": title, "url": url, "text": raw},
            )
            self._prefixes[url] = raw[:5_000]
            self._receipts.append(projected["content_free_receipt"])
            links = []
            if (
                self._phase == target.FIRST_PHASE
                and url == "https://packages.acme.example/web/packages/"
            ):
                links = [
                    {"url": "noise-one/", "text": "noise"},
                    {"url": "noise-two/", "text": "noise"},
                    {"url": "AlphaKit/index.html", "text": "alpha"},
                    {"url": "BetaCore/index.html", "text": "beta"},
                    {"url": "GammaTools/index.html", "text": "gamma"},
                ]
            output.append(
                {
                    "query": item.get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": title,
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
            self._receipts,
            fetch_calls=self.fetch_calls,
            fetch_failures=self.fetch_failures,
        )


class DistinctIdentityDetailRuntimeTests(unittest.TestCase):
    def _run(self, *, opaque: str = "0"):
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
                phase: SyntheticMultiSearch(QUESTION, phase) for phase in target.PHASES
            }
            result = target.run_paired_task(
                {"opaque_id": "task_" + opaque * 24, "question": QUESTION},
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        return inner, result

    def test_distinct_coverage_record_and_prediction_gain_closes(self) -> None:
        inner, envelope = self._run()
        result = envelope["parent_result"]
        main = result["content_free_receipt"]
        distinct = envelope["distinct_identity_selection_receipt"]
        control = main["arm_metrics"][target.CONTROL_ARM]
        candidate = main["arm_metrics"][target.CANDIDATE_ARM]
        self.assertEqual(distinct["control_new_distinct_identity_count"], 1)
        self.assertEqual(distinct["candidate_new_distinct_identity_count"], 3)
        self.assertEqual(distinct["new_distinct_identity_gain"], 2)
        self.assertEqual(main["bound_visible_link_gain"], 2)
        self.assertEqual(control["second_wave_bound_visible_links"], 1)
        self.assertEqual(candidate["second_wave_bound_visible_links"], 3)
        self.assertEqual(control["second_wave_target_bound_records"], 1)
        self.assertEqual(candidate["second_wave_target_bound_records"], 3)
        self.assertEqual(main["candidate_target_bound_record_gain"], 2)
        self.assertTrue(main["target_bound_record_mechanism_engaged"])
        self.assertTrue(result["prediction_changed"])
        self.assertIn("Unknown", result["predictions"][target.CONTROL_ARM])
        self.assertIn("2.0.2", result["predictions"][target.CANDIDATE_ARM])
        self.assertIn("3.0.3", result["predictions"][target.CANDIDATE_ARM])
        self.assertEqual(main["physical_query_count"], 4)
        self.assertLessEqual(main["physical_fetch_count"], 14)
        self.assertEqual(inner.requests, 3)

    def test_parent_module_globals_are_not_mutated(self) -> None:
        before_selector = parent.select_page_visible_link_prefixes
        before_second = parent._run_second_wave
        target.validate_binding()
        self._run()
        self.assertIs(parent.select_page_visible_link_prefixes, before_selector)
        self.assertIs(parent._run_second_wave, before_second)

    def test_context_local_receipts_do_not_cross_concurrent_tasks(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [
                future.result()[1]
                for future in (
                    pool.submit(self._run, opaque="1"),
                    pool.submit(self._run, opaque="2"),
                )
            ]
        for result in results:
            self.assertEqual(
                result["distinct_identity_selection_receipt"][
                    "new_distinct_identity_gain"
                ],
                2,
            )
            target.validate_result(result)

    def test_resealed_distinct_or_parent_mapping_tamper_is_rejected(self) -> None:
        _, envelope = self._run()
        changed = copy.deepcopy(envelope)
        receipt = changed["distinct_identity_selection_receipt"]
        receipt["candidate_new_distinct_identity_count"] = 2
        receipt["new_distinct_identity_gain"] = 1
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = payload_sha256(receipt)
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(changed)

        changed = copy.deepcopy(envelope)
        changed["parent_result"]["content_free_receipt"]["bound_visible_link_gain"] = 1
        nested = changed["parent_result"]["content_free_receipt"]
        nested.pop("receipt_payload_sha256")
        nested["receipt_payload_sha256"] = payload_sha256(nested)
        changed["parent_result"].pop("result_payload_sha256")
        changed["parent_result"]["result_payload_sha256"] = payload_sha256(
            changed["parent_result"]
        )
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(changed)

    def test_rejects_non_multi_identity_clients_before_effects(self) -> None:
        with self.assertRaisesRegex(ValueError, "two distinct multi-identity"):
            target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=object(),
                searches={},
                limits=object(),
            )

    def test_module_has_no_direct_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25017_distinct_identity_detail_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
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
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
