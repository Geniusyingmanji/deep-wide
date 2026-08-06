from __future__ import annotations

import copy
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
from deepwide_agent.v24686_worldbank_target_value_runtime import (  # noqa: E402
    _visible_contract,
    apply_target_values,
    exact_lookup_url,
    project_exact_lookup_responses,
    run_v24686_task,
    target_lookup_requests,
    validate_result,
    validate_visible_contract,
    visible_query_vector,
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
        ["Country", *(f"{label} [{indicator}] @{year}" for label, indicator, year in TARGETS)]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{countries}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\n"
        "Use the World Bank API values. Preserve the decimal representation returned by "
        "the official API. Use Unknown when unavailable. Return one table only."
    )


def task(opaque_id: str = "task_000000000000000000246861") -> dict[str, str]:
    return {"opaque_id": opaque_id, "question": visible_question()}


def columns() -> list[str]:
    return [
        "Country",
        "Internet use (%) [IT.NET.USER.ZS] @2022",
        "Life expectancy [SP.DYN.LE00.IN] @2022",
    ]


def table(rows: list[list[str]], header: list[str] | None = None) -> str:
    selected = header or columns()
    return (
        "```markdown\n| "
        + " | ".join(selected)
        + " |\n| "
        + " | ".join("---" for _ in selected)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def expanded_prediction() -> str:
    return table(
        [
            ["Bhutan", "Unknown", "70"],
            ["Liechtenstein", "98.1", "84.0"],
            ["Monaco", "wrong", "Unknown"],
            ["San Marino", "95.4", "85.3"],
        ]
    )


def response(iso3: str, indicator: str, year: str, value: str) -> str:
    raw_value = str(value)
    if not Decimal(raw_value).is_finite():
        raise ValueError("fixture value must be finite")
    marker = "__V24686_RAW_DECIMAL__"
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
    if rendered.count(json.dumps(marker)) != 1:
        raise AssertionError("fixture decimal marker drifted")
    return rendered.replace(json.dumps(marker), raw_value)


def lookup_batches(*, omit: tuple[str, str, str] | None = None) -> list[dict]:
    values = []
    for key, value in VALUES.items():
        if key == omit:
            continue
        iso3, indicator, year = key
        values.append(
            {
                "query": "world-bank target-value lookup",
                "results": [
                    {
                        "url": exact_lookup_url(iso3, indicator, year),
                        "raw_content": response(iso3, indicator, year, value),
                    }
                ],
            }
        )
    return values


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
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
    )


class Model:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.synthesis_columns: list[list[str]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if json_mode:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["Country", "Internet", "Life"],
                    "row_target_hint": "four countries",
                    "queries": ["ignored"],
                }
            )
        else:
            marker = "REQUIRED COLUMNS:\n"
            raw_columns = json.loads(user.split(marker, 1)[1].split("\n\n", 1)[0])
            self.synthesis_columns.append(raw_columns)
            if raw_columns == columns():
                text = expanded_prediction()
            else:
                text = table(
                    [["Bhutan", "bad", "schema"]],
                    header=raw_columns,
                )
        return ModelResult(text, {}, None, 1)


class Search:
    def __init__(self) -> None:
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
        self.search_vectors: list[list[str]] = []
        self.fetch_vectors: list[list[dict[str, str]]] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        vector = list(queries)
        self.calls += 1
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
        self.fetch_calls += 1
        self.fetch_vectors.append(vector)
        if vector and "api.worldbank.org" in vector[0]["url"]:
            batches = []
            for request in vector:
                iso3, indicator, year = request["member_label"].split("|")
                batches.append(
                    {
                        "query": request["query"],
                        "results": [
                            {
                                "title": "",
                                "url": request["url"],
                                "raw_content": response(
                                    iso3, indicator, year, VALUES[(iso3, indicator, year)]
                                ),
                            }
                        ],
                        "error": None,
                    }
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


class VisibleContractTests(unittest.TestCase):
    def test_expanded_parser_only_gap_is_exact(self) -> None:
        contract = _visible_contract(visible_question())
        self.assertEqual(contract["frozen_parser_columns"], [])
        self.assertEqual(contract["expanded_parser_columns"], columns())
        self.assertEqual(
            [item["iso3"] for item in contract["countries"]],
            [country[1] for country in COUNTRIES],
        )
        self.assertEqual(
            [(item["indicator"], item["year"]) for item in contract["targets"]],
            [(item[1], item[2]) for item in TARGETS],
        )

    def test_queries_and_lookup_addresses_use_visible_targets_without_values(self) -> None:
        queries = visible_query_vector(visible_question(), 4)
        self.assertEqual(len(queries), 4)
        self.assertTrue(all("IT.NET.USER.ZS 2022" in query for query in queries))
        self.assertTrue(all(value not in " ".join(queries) for value in VALUES.values()))
        requests = target_lookup_requests(_visible_contract(visible_question()))
        self.assertEqual(len(requests), 8)
        self.assertEqual(
            requests[0]["url"],
            exact_lookup_url("BTN", "IT.NET.USER.ZS", "2022"),
        )

    def test_visible_contract_rejects_injected_or_duplicate_addresses(self) -> None:
        for question in (
            visible_question().replace("BTN]", "BTN|bad]"),
            visible_question().replace("SP.DYN.LE00.IN", "IT.NET.USER.ZS"),
            visible_question().replace("@2022", "@2040", 1),
        ):
            with self.assertRaises(ValueError):
                _visible_contract(question)

    def test_resealed_contract_fields_must_match_reparsed_column(self) -> None:
        for field, value in (
            ("label", "Different label"),
            ("indicator", "NY.GDP.PCAP.CD"),
            ("year", "2023"),
        ):
            with self.subTest(field=field):
                contract = _visible_contract(visible_question())
                contract["targets"][0][field] = value
                with self.assertRaises(ValueError):
                    validate_visible_contract(contract)


class LookupProjectionTests(unittest.TestCase):
    def test_exact_records_preserve_decimal_text_and_bind_all_targets(self) -> None:
        contract = _visible_contract(visible_question())
        records, stats = project_exact_lookup_responses(lookup_batches(), contract)
        self.assertEqual(len(records), 8)
        self.assertEqual(stats["valid_exact_record_count"], 8)
        self.assertEqual(stats["returned_result_count"], 8)
        self.assertEqual(stats["missing_response_count"], 0)
        self.assertIn("84.0", {record["value"] for record in records})
        record_key = tuple(
            records[0][key] for key in ("country_iso3", "indicator", "year")
        )
        self.assertEqual(records[0]["value"], VALUES[record_key])
        candidate, admissions, check = apply_target_values(
            expanded_prediction(), contract, records
        )
        self.assertEqual(len(admissions), 8)
        self.assertTrue(check["passed"])
        self.assertGreater(check["corrected_nonunknown_count"], 0)
        self.assertGreater(check["filled_unknown_count"], 0)
        self.assertIn("| Bhutan | 88.35620117 | 72.229 |", candidate)

    def test_missing_or_mismatched_record_fails_completion_closed(self) -> None:
        contract = _visible_contract(visible_question())
        missing = ("MCO", "SP.DYN.LE00.IN", "2022")
        records, stats = project_exact_lookup_responses(
            lookup_batches(omit=missing), contract
        )
        self.assertEqual(stats["missing_response_count"], 1)
        candidate, _admissions, check = apply_target_values(
            expanded_prediction(), contract, records
        )
        self.assertFalse(check["passed"])
        self.assertIn("| Monaco | 97.2 | Unknown |", candidate)

        tampered = lookup_batches()
        tampered[0]["results"][0]["url"] = tampered[0]["results"][0][
            "url"
        ].replace("/BTN/", "/ZZZ/")
        records, stats = project_exact_lookup_responses(tampered, contract)
        self.assertEqual(len(records), 7)
        self.assertGreater(stats["unmatched_or_duplicate_result_count"], 0)

        malformed = lookup_batches()
        malformed[0]["results"][0]["raw_content"] = "{"
        records, stats = project_exact_lookup_responses(malformed, contract)
        self.assertEqual(len(records), 7)
        self.assertEqual(stats["invalid_exact_response_count"], 1)
        self.assertEqual(stats["missing_response_count"], 0)
        self.assertEqual(
            stats["requested_target_count"],
            stats["valid_exact_record_count"]
            + stats["null_value_record_count"]
            + stats["invalid_exact_response_count"]
            + stats["missing_response_count"],
        )

    def test_resealed_record_or_candidate_tamper_fails_validation(self) -> None:
        model = Model()
        search = Search()
        value = run_v24686_task(task(), model=model, search=search, limits=limits())
        changed = copy.deepcopy(value)
        changed["official_lookup_records"][0]["value"] = "999"
        changed.pop("result_sha256")
        changed["result_sha256"] = hashlib.sha256(
            json.dumps(changed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self.assertRaises(ValueError):
            validate_result(changed)

        changed = copy.deepcopy(value)
        changed["receipt"]["lookup"]["valid_exact_record_count"] = 7
        changed["receipt"].pop("receipt_sha256")
        changed["receipt"]["receipt_sha256"] = hashlib.sha256(
            json.dumps(
                changed["receipt"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        changed.pop("result_sha256")
        changed["result_sha256"] = hashlib.sha256(
            json.dumps(
                changed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        with self.assertRaises(ValueError):
            validate_result(changed)


class RuntimeTests(unittest.TestCase):
    def test_privileged_task_is_rejected_before_model_or_search_effect(self) -> None:
        model = Model()
        search = Search()
        privileged = {**task(), "question_type": "hidden-label"}
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24686_task(privileged, model=model, search=search, limits=limits())
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_three_arms_share_prefix_and_use_balanced_synthesis(self) -> None:
        for opaque_id, expected_order in (
            ("task_000000000000000000246861", ["frozen_parser", "expanded_parser"]),
            ("task_000000000000000000246862", ["expanded_parser", "frozen_parser"]),
        ):
            model = Model()
            search = Search()
            result = run_v24686_task(
                task(opaque_id),
                model=model,
                search=search,
                limits=limits(),
                monotonic=time.monotonic,
            )
            validate_result(result)
            receipt = result["receipt"]
            self.assertEqual(receipt["synthesis_order"], expected_order)
            self.assertEqual(model.requests, 3)
            self.assertEqual(len(search.search_vectors), 1)
            self.assertEqual(len(search.search_vectors[0]), 4)
            self.assertEqual([len(vector) for vector in search.fetch_vectors], [2, 8])
            self.assertEqual(receipt["admitted_total_fetch_targets"], 10)
            self.assertEqual(
                receipt["lookup"]["returned_result_count"],
                receipt["lookup"]["valid_exact_record_count"]
                + receipt["lookup"]["null_value_record_count"]
                + receipt["lookup"]["invalid_exact_response_count"]
                + receipt["lookup"]["unmatched_or_duplicate_result_count"],
            )
            self.assertTrue(receipt["completion_check"]["passed"])
            self.assertNotEqual(
                result["prediction_sha256"]["frozen_parser"],
                result["prediction_sha256"]["expanded_parser"],
            )
            self.assertEqual(
                model.synthesis_columns[expected_order.index("frozen_parser")],
                ["Country", "Internet", "Life"],
            )
            self.assertEqual(
                model.synthesis_columns[expected_order.index("expanded_parser")],
                columns(),
            )
            self.assertNotEqual(
                result["prediction_sha256"]["expanded_parser"],
                result["prediction_sha256"]["target_value"],
            )
            self.assertFalse(receipt["positive_task_credit_assigned"])

    def test_runtime_source_has_no_privileged_or_effect_capability(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        relative = Path("src/deepwide_agent/v24686_worldbank_target_value_runtime.py")
        accesses, imports = audit.ast_findings(relative)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        source = (ROOT / relative).read_text(encoding="utf-8")
        forbidden_modules = (
            "import os",
            "import pathlib",
            "import subprocess",
            "import requests",
            "import socket",
            "from urllib.request",
        )
        self.assertFalse(any(marker in source for marker in forbidden_modules))


if __name__ == "__main__":
    unittest.main()
