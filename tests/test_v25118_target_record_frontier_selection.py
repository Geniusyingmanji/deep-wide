from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25118_target_record_frontier_selection as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


TARGETS = (".in", ".jp")
PIVOTS = ("India", "Japan")
AUTHORITIES = ("IANA Root Zone Database",)
COLUMNS = ("Domain", "Type", "TLD Manager")


def source(url: str, title: str = "search source") -> dict[str, str]:
    return {"url": url, "fetch_url": url, "title": title}


def second_wave() -> list[dict[str, object]]:
    return [
        {
            "query": "discarded query",
            "answer": "discarded narrative",
            "results": [
                source("https://noise.example/one"),
                source("https://noise.example/two"),
                source(
                    "https://iana.org/domains/root/db/in.html",
                    "IN Domain Type TLD Manager",
                ),
            ],
            "hosted_search_trace": {
                "actions": [
                    {
                        "sources": [
                            source("https://noise.example/three"),
                            source(
                                "https://www.iana.org/domains/root/db/jp.html",
                                "JP Domain Type TLD Manager",
                            ),
                        ]
                    }
                ]
            },
        }
    ]


def first_wave() -> list[dict[str, object]]:
    return [
        {
            "query": "first",
            "results": [
                {
                    "requested_url": "https://www.iana.org/domains/root/db/",
                    "url": "https://www.iana.org/domains/root/db/",
                    "raw_content": "body content must never rank a URL",
                    "page_links": [
                        {"url": "noise.html", "text": "noise"},
                        {"url": "in.html", "text": "IN Domain Type TLD Manager"},
                        {"url": "jp.html", "text": "JP Domain Type TLD Manager"},
                    ],
                }
            ],
        }
    ]


class TargetRecordFrontierSelectionTests(unittest.TestCase):
    def select(self, *, first=None, second=None, cap: int = 3, exclude=()):
        return target.select_target_record_frontier(
            first_wave() if first is None else first,
            second_wave() if second is None else second,
            row_targets=TARGETS,
            pivots=PIVOTS,
            authority_terms=AUTHORITIES,
            columns=COLUMNS,
            cap=cap,
            exclude_urls=exclude,
        )

    def test_promotes_distinct_target_authority_field_records(self) -> None:
        value = self.select()
        control = [item["url"] for item in value["control"]]
        candidate = [item["url"] for item in value["candidate"]]
        self.assertEqual(len(control), len(candidate))
        self.assertEqual(len(candidate), 3)
        self.assertIn("https://iana.org/domains/root/db/in.html", candidate)
        self.assertIn("https://www.iana.org/domains/root/db/jp.html", candidate)
        receipt = value["content_free_receipt"]
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertGreater(receipt["candidate_distinct_target_record_count"], receipt["control_distinct_target_record_count"])
        self.assertGreaterEqual(receipt["candidate_target_field_pair_count"], receipt["control_target_field_pair_count"])
        self.assertEqual(receipt["control_selected_url_count"], receipt["candidate_selected_url_count"])

    def test_same_complete_frontier_search_precedence_and_deduplication(self) -> None:
        second = second_wave()
        second[0]["hosted_search_trace"]["actions"][0]["sources"].append(
            source("https://iana.org/domains/root/db/in.html", "duplicate")
        )
        first = first_wave()
        first[0]["results"][0]["page_links"].append(
            {"url": "https://iana.org/domains/root/db/in.html", "text": "duplicate link"}
        )
        value = self.select(first=first, second=second)
        receipt = value["content_free_receipt"]
        self.assertEqual(
            receipt["complete_unique_url_count_before_exclusion"],
            receipt["unique_search_url_count"] + receipt["unique_page_link_url_count"],
        )
        self.assertEqual(
            sum(item["url"] == "https://iana.org/domains/root/db/in.html" for item in value["candidate"]),
            1,
        )

    def test_unbound_authority_ambiguous_target_and_body_only_signal_do_not_rank(self) -> None:
        second = [
            {
                "query": "discarded",
                "results": [
                    source("https://noise.example/in/record", "Domain Type TLD Manager"),
                    source("https://iana.org/domains/root/db/in-jp.html", "Domain Type TLD Manager"),
                    source("https://noise.example/other"),
                ],
                "hosted_search_trace": {"actions": []},
            }
        ]
        value = self.select(first=[], second=second, cap=2)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["target_record_url_count"], 0)
        self.assertEqual(value["control"], value["candidate"])
        self.assertFalse(receipt["mechanism_engaged"])

        changed_first = copy.deepcopy(first_wave())
        changed_first[0]["results"][0]["raw_content"] = (
            "India Japan IANA Domain Type TLD Manager " * 1000
        )
        self.assertEqual(
            [item["url"] for item in self.select()["candidate"]],
            [item["url"] for item in self.select(first=changed_first)["candidate"]],
        )

    def test_exact_handoff_without_strict_gain_or_grounded_plan(self) -> None:
        value = target.select_target_record_frontier(
            first_wave(),
            second_wave(),
            row_targets=(),
            pivots=(),
            authority_terms=(),
            columns=COLUMNS,
            cap=3,
        )
        self.assertEqual(value["control"], value["candidate"])
        self.assertTrue(value["content_free_receipt"]["selection_changed"] == 0)
        full = self.select(cap=8)
        self.assertEqual(full["control"], full["candidate"])

    def test_private_invalid_relative_and_exclusion_handling(self) -> None:
        first = first_wave()
        first[0]["results"][0]["page_links"].extend(
            [
                {"url": "http://127.0.0.1/in.json", "text": "private"},
                {"url": "https://user:secret@example.org/in.json", "text": "credential"},
                {"url": "javascript:alert(1)", "text": "invalid"},
            ]
        )
        value = self.select(
            first=first,
            exclude=("https://iana.org/domains/root/db/in.html",),
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["rejected_private_or_credential_link_count"], 2)
        self.assertEqual(receipt["rejected_invalid_or_non_http_link_count"], 1)
        self.assertNotIn(
            "https://iana.org/domains/root/db/in.html",
            [item["url"] for item in value["candidate"]],
        )

    def test_receipt_content_free_replay_bound_and_resealed_tamper_fails(self) -> None:
        value = self.select()
        encoded = json.dumps(value["content_free_receipt"], ensure_ascii=False)
        for forbidden in ("India", "Japan", ".in", ".jp", "IANA", "Domain", "https://"):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["content_free_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        self.assertEqual(
            target.validate_result(
                value,
                first_wave_page_batches=first_wave(),
                second_wave_raw=second_wave(),
                row_targets=TARGETS,
                pivots=PIVOTS,
                authority_terms=AUTHORITIES,
                columns=COLUMNS,
                cap=3,
            ),
            value,
        )
        tampered = copy.deepcopy(value["content_free_receipt"])
        tampered["candidate_distinct_target_record_count"] = 0
        tampered["distinct_target_record_gain"] = 0
        tampered.pop("receipt_payload_sha256")
        tampered["receipt_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_receipt(tampered)

    def test_module_has_no_io_or_privileged_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25118_target_record_frontier_selection.py"
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
