from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import sys
import time
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24804_shared_prefix_budget_ladder import (  # noqa: E402
    ARMS,
    AdaptivePolicy,
    decide_adaptive,
    run_v24804_task,
    validate_result,
)


COUNTRIES = (
    ("Bhutan", "BTN"),
    ("Liechtenstein", "LIE"),
    ("Monaco", "MCO"),
    ("San Marino", "SMR"),
)
TARGETS = (
    ("Internet use (%)", "IT.NET.USER.ZS", "2022"),
    ("Life expectancy", "SP.DYN.LE00.IN", "2022"),
)
VALUES = {
    ("BTN", "IT.NET.USER.ZS", "2022"): "88.35620117",
    ("BTN", "SP.DYN.LE00.IN", "2022"): "72.229",
    ("LIE", "IT.NET.USER.ZS", "2022"): "98.1",
    ("LIE", "SP.DYN.LE00.IN", "2022"): "84.0",
    ("MCO", "IT.NET.USER.ZS", "2022"): "97.2",
    ("MCO", "SP.DYN.LE00.IN", "2022"): "86.5",
    ("SMR", "IT.NET.USER.ZS", "2022"): "95.4",
    ("SMR", "SP.DYN.LE00.IN", "2022"): "85.3",
}


def visible_question() -> str:
    countries = "\n".join(
        f"{index}. {name} [{iso3}]"
        for index, (name, iso3) in enumerate(COUNTRIES, 1)
    )
    columns = " | ".join(
        [
            "Country",
            *(
                f"{label} [{indicator}] @{year}"
                for label, indicator, year in TARGETS
            ),
        ]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{countries}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\n"
        "Use the World Bank API values. Preserve the decimal representation returned by "
        "the official API. Use Unknown when unavailable. Return one table only."
    )


def task() -> dict[str, str]:
    return {
        "opaque_id": "task_000000000000000000248041",
        "question": visible_question(),
    }


def columns() -> list[str]:
    return [
        "Country",
        "Internet use (%) [IT.NET.USER.ZS] @2022",
        "Life expectancy [SP.DYN.LE00.IN] @2022",
    ]


def table() -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns())
        + " |\n| --- | --- | --- |\n"
        + "\n".join(
            f"| {name} | Unknown | Unknown |" for name, _iso3 in COUNTRIES
        )
        + "\n```"
    )


def response(iso3: str, indicator: str, year: str, value: str) -> str:
    raw_value = str(value)
    if not Decimal(raw_value).is_finite():
        raise ValueError("fixture value must be finite")
    marker = "__RAW_DECIMAL__"
    rendered = json.dumps(
        [
            {
                "page": 1,
                "pages": 1,
                "per_page": 100,
                "total": 1,
                "sourceid": "2",
                "lastupdated": "2026-07-13",
            },
            [
                {
                    "indicator": {"id": indicator, "value": "visible-name"},
                    "country": {"id": iso3[:2], "value": "visible-country"},
                    "countryiso3code": iso3,
                    "date": year,
                    "value": marker,
                    "unit": "",
                    "obs_status": "",
                    "decimal": 0,
                }
            ],
        ],
        separators=(",", ":"),
    )
    return rendered.replace(json.dumps(marker), raw_value)


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=240,
        model_calls=2,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )


def policy(*, cost: float = 0.04, ready: bool = True) -> AdaptivePolicy:
    return AdaptivePolicy(
        calibration_ref_sha256=hashlib.sha256(b"external-calibration").hexdigest(),
        calibration_complete=ready,
        per_lookup_cost=cost,
    )


class Model:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        text = (
            json.dumps(
                {
                    "language": "English",
                    "columns": columns(),
                    "row_target_hint": "four countries",
                    "queries": ["ignored"],
                }
            )
            if json_mode
            else table()
        )
        return ModelResult(text, {}, None, 1)


class Search:
    def __init__(self, *, omit_first: bool = False) -> None:
        for name in (
            "calls", "failures", "tool_calls", "fetch_calls",
            "fetch_failures", "input_tokens", "output_tokens", "total_tokens",
        ):
            setattr(self, name, 0)
        self.omit_first = omit_first
        self.search_vectors: list[list[str]] = []
        self.fetch_vectors: list[list[dict[str, str]]] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        vector = list(queries)
        self.calls += len(vector)
        self.search_vectors.append(vector)
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "title": f"generic-{index}",
                        "url": f"https://example.org/{index}",
                        "fetch_url": f"https://example.org/{index}",
                    }
                ],
                "error": None,
            }
            for index, query in enumerate(vector)
        ]

    def fetch_urls(self, requests):
        vector = list(requests)
        self.fetch_calls += len(vector)
        self.fetch_vectors.append(copy.deepcopy(vector))
        if vector and "api.worldbank.org" in vector[0]["url"]:
            batches = []
            for index, request in enumerate(vector):
                iso3, indicator, year = request["member_label"].split("|")
                results = []
                if not (self.omit_first and len(self.fetch_vectors) == 2 and index == 0):
                    results = [
                        {
                            "title": "",
                            "url": request["url"],
                            "raw_content": response(
                                iso3,
                                indicator,
                                year,
                                VALUES[(iso3, indicator, year)],
                            ),
                        }
                    ]
                batches.append(
                    {"query": request["query"], "results": results, "error": None}
                )
            return batches
        return [
            {
                "query": request["query"],
                "results": [
                    {
                        "title": request["title"],
                        "url": request["url"],
                        "raw_content": "generic evidence",
                    }
                ],
                "error": None,
            }
            for request in vector
        ]


class RuntimeTests(unittest.TestCase):
    def test_shared_prefix_and_fixed_full_expand_are_exact(self) -> None:
        model = Model()
        search = Search()
        value = run_v24804_task(
            task(), model=model, search=search, limits=limits(),
            adaptive_policy=policy(), monotonic=time.monotonic,
        )
        validate_result(value)
        self.assertEqual(model.requests, 2)
        self.assertEqual([len(vector) for vector in search.search_vectors], [4])
        self.assertEqual([len(vector) for vector in search.fetch_vectors], [2, 4, 4])
        self.assertEqual(value["adaptive_decision"]["decision"], "expand")
        self.assertEqual(
            value["predictions"]["coverage_risk_adaptive"],
            value["predictions"]["fixed_full_budget"],
        )
        self.assertNotEqual(
            value["predictions"]["first_wave_only"],
            value["predictions"]["fixed_full_budget"],
        )
        self.assertTrue(value["full_completion_check"]["passed"])
        self.assertFalse(value["first_wave_completion_check"]["passed"])
        self.assertEqual(value["receipt"]["prefix_effect_executions"], 1)
        self.assertEqual(value["receipt"]["repeated_upstream_effects"], 0)
        self.assertFalse(value["receipt"]["positive_task_credit_assigned"])

    def test_stopping_adaptive_is_prefix_identical_and_suffix_blind(self) -> None:
        value = run_v24804_task(
            task(), model=Model(), search=Search(), limits=limits(),
            adaptive_policy=policy(cost=1.0), monotonic=time.monotonic,
        )
        self.assertEqual(value["adaptive_decision"]["decision"], "stop")
        self.assertFalse(value["adaptive_decision"]["wave_two_response_or_value_read"])
        self.assertEqual(
            value["predictions"]["coverage_risk_adaptive"],
            value["predictions"]["first_wave_only"],
        )
        self.assertEqual(
            value["receipt"]["arm_logical_fetch_targets"],
            {
                "first_wave_only": 6,
                "fixed_full_budget": 10,
                "coverage_risk_adaptive": 6,
            },
        )

    def test_missing_calibration_fails_closed_and_entropy_weight_is_rejected(self) -> None:
        decision = decide_adaptive(
            first_records=[],
            first_stats={
                "requested_target_count": 8,
                "returned_result_count": 0,
                "valid_exact_record_count": 0,
                "null_value_record_count": 0,
                "invalid_exact_response_count": 0,
                "unmatched_or_duplicate_result_count": 0,
                "missing_response_count": 8,
            },
            policy=policy(ready=False),
        )
        self.assertEqual(decision["decision"], "stop")
        self.assertEqual(decision["reason"], "calibration_incomplete_fail_closed")
        self.assertGreater(decision["expected_information_gain_nats"], 0)
        self.assertEqual(decision["information_gain_feature_value"], 0)
        with self.assertRaisesRegex(ValueError, "entropy"):
            policy_value = dataclasses.replace(
                policy(), information_gain_feature_weight=0.1
            )
            policy_value.validate()

    def test_privileged_task_rejected_before_any_effect(self) -> None:
        model = Model()
        search = Search()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24804_task(
                {**task(), "question_type": "hidden"},
                model=model,
                search=search,
                limits=limits(),
                adaptive_policy=policy(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_resealed_suffix_or_prefix_tamper_fails(self) -> None:
        value = run_v24804_task(
            task(), model=Model(), search=Search(), limits=limits(),
            adaptive_policy=policy(),
        )
        for mutate in (
            lambda changed: changed["shared_prefix"].update(
                {"base_prediction": "tampered"}
            ),
            lambda changed: changed["adaptive_decision"].update(
                {"decision": "stop"}
            ),
        ):
            changed = copy.deepcopy(value)
            mutate(changed)
            changed.pop("result_sha256")
            changed["result_sha256"] = hashlib.sha256(
                json.dumps(
                    changed,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            with self.assertRaises(ValueError):
                validate_result(changed)

        changed = copy.deepcopy(value)
        first_key = changed["shared_prefix"]["first_wave_records"][0]["target_key"]
        full = next(
            record
            for record in changed["full_official_records"]
            if record["target_key"] == first_key
        )
        full["response_sha256"] = "0" * 64
        changed.pop("result_sha256")
        changed["result_sha256"] = hashlib.sha256(
            json.dumps(
                changed,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        with self.assertRaises(ValueError):
            validate_result(changed)

    def test_runtime_ast_has_no_privileged_access_or_evaluator_import(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        relative = Path("src/deepwide_agent/v24804_shared_prefix_budget_ladder.py")
        accesses, imports = audit.ast_findings(relative)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
