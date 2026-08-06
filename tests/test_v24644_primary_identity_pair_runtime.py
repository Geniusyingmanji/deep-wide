from __future__ import annotations

import ast
import hashlib
import json
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits
from deepwide_agent.v24637_objective_alignment_runtime import payload_sha256
from deepwide_agent import v24642_deterministic_pair_runtime as frozen
from deepwide_agent.v24644_primary_identity_pair_runtime import (
    binding_is_private_and_stable,
    discover_pairs,
    primary_identity_bound_ror_suffixes,
    run_v24644_task,
    validate_result,
)


ENTITIES = (
    "Alpha Research Institute",
    "Beta Foundation",
    "Gamma Laboratory",
    "Delta Centre",
)
SUFFIXES = ("01abc2d34", "02abc3d45", "03abc4d56", "04abc5d67")


def table(rows: list[list[str]]) -> str:
    return (
        "```markdown\n| Organization | ROR ID | Country code |\n"
        "| --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def baseline() -> str:
    return table(
        [
            [ENTITIES[0], "Unknown", "FR"],
            [ENTITIES[1], "099999999", "US"],
            [ENTITIES[2], "Unknown", "DE"],
            [ENTITIES[3], "Unknown", "AU"],
        ]
    )


def api_page(entity: str, suffix: str) -> dict[str, str]:
    return {
        "evidence_id": "E0001",
        "url": f"https://api.ror.org/v2/organizations/{suffix}",
        "title": "ROR API response",
        "content": json.dumps(
            {
                "id": f"https://ror.org/{suffix}",
                "names": [
                    {"value": entity, "types": ["ror_display"]},
                    {"value": "Acronym", "types": ["acronym"]},
                ],
            }
        ),
    }


class BindingTests(unittest.TestCase):
    def test_body_only_official_profile_is_rejected(self) -> None:
        page = {
            "evidence_id": "E0001",
            "url": f"https://ror.org/{SUFFIXES[0]}",
            "title": "Different Primary Organization",
            "content": f"Affiliated with {ENTITIES[0]}.",
        }
        self.assertEqual(primary_identity_bound_ror_suffixes(page, ENTITIES[0]), ())
        candidate, receipt = discover_pairs(
            baseline(), entities=ENTITIES, pages=[page]
        )
        self.assertIn(f"| {ENTITIES[0]} | Unknown | FR |", candidate)
        self.assertEqual(receipt["body_only_identity_rejected_pair_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 0)

    def test_exact_normalized_whole_title_and_profile_url_are_admitted(self) -> None:
        page = {
            "evidence_id": "E0001",
            "url": f"https://ror.org/{SUFFIXES[0]}",
            "title": "Álpha Research-Institute",
            "content": "Official organization profile.",
        }
        self.assertEqual(
            primary_identity_bound_ror_suffixes(page, ENTITIES[0]), (SUFFIXES[0],)
        )
        candidate, receipt = discover_pairs(
            baseline(), entities=ENTITIES, pages=[page]
        )
        self.assertIn(f"| {ENTITIES[0]} | {SUFFIXES[0]} | FR |", candidate)
        self.assertEqual(receipt["exact_title_identity_pair_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 1)

    def test_title_containment_is_not_whole_title_identity(self) -> None:
        page = {
            "evidence_id": "E0001",
            "url": f"https://ror.org/{SUFFIXES[0]}",
            "title": f"{ENTITIES[0]} — partners and affiliations",
            "content": ENTITIES[0],
        }
        self.assertEqual(primary_identity_bound_ror_suffixes(page, ENTITIES[0]), ())
        candidate, receipt = discover_pairs(
            baseline(), entities=ENTITIES, pages=[page]
        )
        self.assertIn(f"| {ENTITIES[0]} | Unknown | FR |", candidate)
        self.assertEqual(receipt["body_only_identity_rejected_pair_count"], 1)

    def test_official_structured_primary_identity_is_admitted(self) -> None:
        page = api_page(ENTITIES[0], SUFFIXES[0])
        self.assertEqual(
            primary_identity_bound_ror_suffixes(page, ENTITIES[0]), (SUFFIXES[0],)
        )
        candidate, receipt = discover_pairs(
            baseline(), entities=ENTITIES, pages=[page]
        )
        self.assertIn(f"| {ENTITIES[0]} | {SUFFIXES[0]} | FR |", candidate)
        self.assertEqual(receipt["structured_primary_identity_pair_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 1)

    def test_structured_url_id_or_primary_display_mismatch_is_rejected(self) -> None:
        wrong_id = api_page(ENTITIES[0], SUFFIXES[0])
        record = json.loads(wrong_id["content"])
        record["id"] = f"https://ror.org/{SUFFIXES[2]}"
        wrong_id["content"] = json.dumps(record)
        wrong_name = api_page("Different Primary Organization", SUFFIXES[0])
        for page in (wrong_id, wrong_name):
            self.assertEqual(
                primary_identity_bound_ror_suffixes(page, ENTITIES[0]), ()
            )
            candidate, receipt = discover_pairs(
                baseline(), entities=ENTITIES, pages=[page]
            )
            self.assertIn(f"| {ENTITIES[0]} | Unknown | FR |", candidate)
            self.assertEqual(receipt["admitted_replacement_count"], 0)

    def test_two_primary_identity_bound_values_fail_closed(self) -> None:
        pages = [
            {
                "evidence_id": "E0001",
                "url": f"https://ror.org/{SUFFIXES[0]}",
                "title": ENTITIES[0],
                "content": "Official profile.",
            },
            {
                "evidence_id": "E0002",
                "url": f"https://ror.org/{SUFFIXES[2]}",
                "title": ENTITIES[0],
                "content": "Official profile.",
            },
        ]
        candidate, receipt = discover_pairs(
            baseline(), entities=ENTITIES, pages=pages
        )
        self.assertIn(f"| {ENTITIES[0]} | Unknown | FR |", candidate)
        self.assertEqual(receipt["unknown_target_ambiguous_pair_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 0)

    def test_nonunknown_ror_and_all_country_cells_are_immutable(self) -> None:
        pages = [
            {
                "evidence_id": "E0001",
                "url": f"https://ror.org/{SUFFIXES[1]}",
                "title": ENTITIES[1],
                "content": "Official profile.",
            }
        ]
        candidate, receipt = discover_pairs(
            baseline(), entities=ENTITIES, pages=pages
        )
        self.assertIn(f"| {ENTITIES[1]} | 099999999 | US |", candidate)
        self.assertEqual(receipt["nonunknown_target_pair_count"], 1)
        self.assertFalse(receipt["existing_nonunknown_cells_changed"])
        self.assertFalse(receipt["country_code_cells_changed"])


class Model:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        if self.requests == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["Organization", "ROR ID", "Country code"],
                    "row_target_hint": "4",
                    "queries": ["ignored"],
                }
            )
        else:
            text = baseline()
        return ModelResult(text, {}, None, 1)


class Search:
    def __init__(
        self,
        *,
        redirect_first_to: str | None = None,
        omit_first_final_url: bool = False,
        oversized_api_record: bool = False,
    ) -> None:
        for name in (
            "calls",
            "failures",
            "tool_calls",
            "fetch_calls",
            "fetch_failures",
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            setattr(self, name, 0)
        self.queries: list[str] = []
        self.fetch_count = 0
        self.fetch_request_titles: list[str] = []
        self.fetch_request_urls: list[str] = []
        self.redirect_first_to = redirect_first_to
        self.omit_first_final_url = omit_first_final_url
        self.oversized_api_record = oversized_api_record

    def search_many(self, queries, **kwargs):
        self.calls += 1
        self.queries = list(queries)
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "title": entity,
                        "url": f"https://ror.org/{suffix}",
                        "fetch_url": f"https://ror.org/{suffix}",
                    }
                ],
                "error": None,
            }
            for entity, suffix, query in zip(ENTITIES, SUFFIXES, queries, strict=True)
        ]

    def fetch_urls(self, requests):
        self.fetch_calls += 1
        values = list(requests)
        self.fetch_count = len(values)
        self.fetch_request_titles = [str(request.get("title", "")) for request in values]
        self.fetch_request_urls = [str(request.get("url", "")) for request in values]
        return [
            {
                "query": request["query"],
                "answer": "",
                "results": [
                    {
                        "title": (
                            ENTITIES[index]
                            if index == 0
                            and (
                                self.redirect_first_to is not None
                                or self.omit_first_final_url
                            )
                            else "ROR API response"
                        ),
                        "url": (
                            ""
                            if index == 0 and self.omit_first_final_url
                            else (
                                f"https://ror.org/{self.redirect_first_to}"
                                if index == 0 and self.redirect_first_to is not None
                                else f"https://api.ror.org/v2/organizations/{SUFFIXES[index]}"
                            )
                        ),
                        "requested_url": request["url"],
                        "raw_content": (
                            "Official profile."
                            if index == 0
                            and (
                                self.redirect_first_to is not None
                                or self.omit_first_final_url
                            )
                            else (
                                api_page(ENTITIES[index], SUFFIXES[index])["content"]
                                if not self.oversized_api_record
                                else json.dumps(
                                    {
                                        **json.loads(
                                            api_page(ENTITIES[index], SUFFIXES[index])[
                                                "content"
                                            ]
                                        ),
                                        "padding": "x" * 20_000,
                                    }
                                )
                            )
                        ),
                    }
                ],
                "error": None,
            }
            for index, request in enumerate(values)
        ]


def visible_task() -> dict[str, str]:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(ENTITIES, 1))
    return {
        "opaque_id": "task_000000000000000000246440",
        "question": (
            "Use public web sources to return one Markdown table about these organizations:\n"
            f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
            "The column names are: Organization, ROR ID, Country code. "
            "Use the 9-character ROR ID suffix, not the full URL, and the ISO 3166-1 alpha-2 country code. "
            "Return one table only."
        ),
    }


class RuntimeTests(unittest.TestCase):
    def test_private_binding_and_two_model_call_effect_conservation(self) -> None:
        self.assertTrue(binding_is_private_and_stable())
        original_discovery = frozen.run_v24642_task.__globals__["discover_pairs"]
        model = Model()
        search = Search()
        result = run_v24644_task(
            visible_task(),
            model=model,
            search=search,
            limits=ScoreFirstLimits(
                wall_seconds=240,
                model_calls=3,
                search_queries=4,
                fetch_targets=10,
                search_results_per_query=3,
                evidence_chars=60_000,
                page_chars=5_000,
                plan_output_tokens=4_000,
                synthesis_output_tokens=30_000,
                repair_output_tokens=12_000,
            ),
            monotonic=time.monotonic,
        )
        validate_result(result)
        self.assertIs(
            frozen.run_v24642_task.__globals__["discover_pairs"], original_discovery
        )
        self.assertEqual(model.requests, 2)
        self.assertEqual(len(search.queries), 4)
        self.assertLessEqual(search.fetch_count, 10)
        self.assertEqual(search.fetch_request_titles, [""] * search.fetch_count)
        self.assertEqual(
            search.fetch_request_urls,
            [
                f"https://api.ror.org/v2/organizations/{suffix}"
                for suffix in SUFFIXES
            ],
        )
        self.assertEqual(result["receipt"]["model_cost"]["requests"], 2)
        self.assertTrue(result["receipt"]["body_only_identity_binding_removed"])
        self.assertTrue(
            result["receipt"]["search_lead_title_blanked_before_fetch_effect"]
        )
        self.assertTrue(
            result["receipt"][
                "ror_profile_lead_rewritten_to_official_api_before_fetch"
            ]
        )
        self.assertTrue(
            result["receipt"]["final_fetched_url_used_for_identity_binding"]
        )
        self.assertTrue(
            result["receipt"][
                "official_api_identity_projected_before_shared_evidence"
            ]
        )
        self.assertEqual(
            result["receipt"]["discovery"]["admitted_replacement_count"], 3
        )

    def test_oversized_api_record_is_projected_before_page_cap(self) -> None:
        result = run_v24644_task(
            visible_task(),
            model=Model(),
            search=Search(oversized_api_record=True),
            limits=ScoreFirstLimits(
                wall_seconds=240,
                model_calls=3,
                search_queries=4,
                fetch_targets=10,
                search_results_per_query=3,
                evidence_chars=60_000,
                page_chars=5_000,
                plan_output_tokens=4_000,
                synthesis_output_tokens=30_000,
                repair_output_tokens=12_000,
            ),
            monotonic=time.monotonic,
        )
        validate_result(result)
        self.assertEqual(
            result["receipt"]["discovery"][
                "structured_primary_identity_pair_count"
            ],
            4,
        )
        self.assertEqual(
            result["receipt"]["discovery"]["admitted_replacement_count"], 3
        )

    def test_redirect_uses_final_ror_profile_id_not_requested_id(self) -> None:
        result = run_v24644_task(
            visible_task(),
            model=Model(),
            search=Search(redirect_first_to=SUFFIXES[2]),
            limits=ScoreFirstLimits(
                wall_seconds=240,
                model_calls=3,
                search_queries=4,
                fetch_targets=10,
                search_results_per_query=3,
                evidence_chars=60_000,
                page_chars=5_000,
                plan_output_tokens=4_000,
                synthesis_output_tokens=30_000,
                repair_output_tokens=12_000,
            ),
            monotonic=time.monotonic,
        )
        validate_result(result)
        self.assertIn(
            f"| {ENTITIES[0]} | {SUFFIXES[2]} | FR |",
            result["predictions"]["deterministic_pair"],
        )
        self.assertNotIn(
            f"| {ENTITIES[0]} | {SUFFIXES[0]} | FR |",
            result["predictions"]["deterministic_pair"],
        )

    def test_missing_final_url_cannot_fall_back_to_requested_identity(self) -> None:
        result = run_v24644_task(
            visible_task(),
            model=Model(),
            search=Search(omit_first_final_url=True),
            limits=ScoreFirstLimits(
                wall_seconds=240,
                model_calls=3,
                search_queries=4,
                fetch_targets=10,
                search_results_per_query=3,
                evidence_chars=60_000,
                page_chars=5_000,
                plan_output_tokens=4_000,
                synthesis_output_tokens=30_000,
                repair_output_tokens=12_000,
            ),
            monotonic=time.monotonic,
        )
        validate_result(result)
        self.assertIn(
            f"| {ENTITIES[0]} | Unknown | FR |",
            result["predictions"]["deterministic_pair"],
        )
        self.assertEqual(
            result["receipt"]["discovery"]["admitted_replacement_count"], 2
        )

    def test_coordinated_binding_count_tamper_fails_closed(self) -> None:
        result = run_v24644_task(
            visible_task(),
            model=Model(),
            search=Search(),
            limits=ScoreFirstLimits(
                wall_seconds=240,
                model_calls=3,
                search_queries=4,
                fetch_targets=10,
                search_results_per_query=3,
                evidence_chars=60_000,
                page_chars=5_000,
                plan_output_tokens=4_000,
                synthesis_output_tokens=30_000,
                repair_output_tokens=12_000,
            ),
            monotonic=time.monotonic,
        )
        result["receipt"]["discovery"]["exact_title_identity_pair_count"] += 1
        result["receipt"].pop("receipt_sha256")
        result["receipt"]["receipt_sha256"] = payload_sha256(result["receipt"])
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        with self.assertRaisesRegex(ValueError, "content-free receipt drifted"):
            validate_result(result)

    def test_result_validator_rejects_country_mutation(self) -> None:
        result = run_v24644_task(
            visible_task(),
            model=Model(),
            search=Search(),
            limits=ScoreFirstLimits(
                wall_seconds=240,
                model_calls=3,
                search_queries=4,
                fetch_targets=10,
                search_results_per_query=3,
                evidence_chars=60_000,
                page_chars=5_000,
                plan_output_tokens=4_000,
                synthesis_output_tokens=30_000,
                repair_output_tokens=12_000,
            ),
            monotonic=time.monotonic,
        )
        candidate = result["predictions"]["deterministic_pair"].replace(
            "| US |", "| ZZ |", 1
        )
        result["predictions"]["deterministic_pair"] = candidate
        result["prediction_sha256"]["deterministic_pair"] = hashlib.sha256(
            candidate.encode()
        ).hexdigest()
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        with self.assertRaisesRegex(ValueError, "country monotonicity"):
            validate_result(result)

    def test_runtime_source_is_label_blind_and_has_no_io_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24644_primary_identity_pair_runtime.py"
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "gold" in name for name in imports))
        self.assertNotIn("evaluation/", text)
        self.assertNotIn("Path(", text)
        self.assertNotIn("subprocess", text)
        self.assertNotIn("open(", text)


if __name__ == "__main__":
    unittest.main()
