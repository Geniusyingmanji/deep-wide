from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25049_page_self_identified_record as representation  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    LatePageBoundFetchMixin,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
)
from deepwide_agent.v25055_page_self_production_fetch import (  # noqa: E402
    HELPER,
    PageSelfProductionSearchClient,
    validate_policy,
    validate_search_class,
)


QUESTION = (
    "Use the supplied public package page and return one Markdown table. "
    "Column names: Package, Version, Published, License."
)
URL = "https://packages.example.org/web/packages/AlphaKit/index.html"


def page(*, title: str = "Example Repository: Package AlphaKit") -> dict[str, str]:
    return {
        "title": title,
        "url": URL,
        "text": "\n".join(
            (
                "Package AlphaKit",
                *("Early public documentation line." for _ in range(180)),
                "Version: | 2.4.1",
                "Published: | 2026-07-08",
                "License: | Apache-2.0",
                *("Late public documentation line." for _ in range(120)),
            )
        ),
    }


def helper_payload(raw: dict[str, str]) -> dict:
    value = representation.build_representation(QUESTION, raw)
    return {
        "status": "ok",
        "url": raw["url"],
        "title": raw["title"],
        "text": value["candidate_evidence"],
        "links": [],
        "projection_receipt": value["content_free_receipt"],
        "parent_prefix": raw["text"][:5_000],
    }


class Process:
    def __init__(self, payload: dict) -> None:
        self.pid = 123456789
        self.returncode = 0
        self.payload = payload
        self.command = None
        self.stdin_value = None

    def communicate(self, value: str, timeout: float | None = None):
        del timeout
        self.stdin_value = json.loads(value)
        return json.dumps(self.payload), ""


def client(process: Process) -> PageSelfProductionSearchClient:
    def launch(command, **kwargs):
        del kwargs
        process.command = command
        return process

    return PageSelfProductionSearchClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        visible_question=QUESTION,
        timeout=65,
        max_retries=2,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=5_000,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=200.0,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        monotonic=lambda: 100.0,
        late_page_fetch_popen=launch,
    )


class PageSelfProductionFetchTests(unittest.TestCase):
    def test_search_client_preserves_parent_effect_boundary(self) -> None:
        validate_search_class()
        self.assertTrue(
            issubclass(PageSelfProductionSearchClient, RobustLatePageBoundSearchClient)
        )
        owner = next(
            base
            for base in PageSelfProductionSearchClient.__mro__
            if "_fetch_url" in base.__dict__
        )
        self.assertIs(owner, LatePageBoundFetchMixin)
        self.assertTrue(HELPER.is_file())
        self.assertFalse(HELPER.is_symlink())

    def test_bound_page_changes_evidence_under_exact_parent_cap(self) -> None:
        process = Process(helper_payload(page()))
        target = client(process)
        result = target._fetch_url(URL)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(Path(process.command[-1]).resolve(), HELPER.resolve())
        self.assertEqual(process.stdin_value, {"url": URL, "question": QUESTION})
        self.assertEqual(len(result["text"]), 5_000)
        self.assertIn('"row":"AlphaKit"', result["text"])
        receipt = target.late_page_projection_receipt()
        self.assertEqual(receipt["projected_page_count"], 1)
        self.assertEqual(receipt["mechanism_engaged_page_count"], 1)
        self.assertEqual(receipt["candidate_evidence_changed_page_count"], 1)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_unbound_page_hands_parent_prefix_through_byte_for_byte(self) -> None:
        raw = page(title="Example Repository package details")
        process = Process(helper_payload(raw))
        target = client(process)
        result = target._fetch_url(URL)
        self.assertEqual(result["text"], raw["text"][:5_000])
        receipt = target.late_page_projection_receipt()
        self.assertEqual(receipt["exact_parent_prefix_handoff_page_count"], 1)
        self.assertEqual(receipt["mechanism_engaged_page_count"], 0)

    def test_policy_preserves_all_production_caps_and_disables_credit(self) -> None:
        policy = validate_policy()
        self.assertEqual(policy["maximum_network_response_bytes_per_fetch"], 3_000_000)
        self.assertEqual(policy["parent_page_character_cap"], 5_000)
        self.assertFalse(
            policy[
                "additional_query_fetch_model_token_context_wall_or_network_byte_cap"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])

    def test_helper_uses_pure_v25049_candidate_without_privileged_imports(self) -> None:
        helper_source = HELPER.read_text(encoding="utf-8")
        self.assertIn("build_representation", helper_source)
        self.assertIn('representation["candidate_evidence"]', helper_source)
        for relative in (
            "src/deepwide_agent/v25055_page_self_production_fetch.py",
            "scripts/run_v25055_page_self_production_fetch_helper.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
            self.assertFalse(
                any(name == "deepwidebench" or name.startswith("deepwidebench.") for name in imported)
            )
            for forbidden in (
                "benchmark_question_type",
                "ground_truth",
                "answer_key",
                "results.csv",
            ):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
