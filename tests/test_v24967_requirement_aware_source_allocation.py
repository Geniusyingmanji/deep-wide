from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24967_requirement_aware_source_allocation as policy  # noqa: E402
from deepwide_agent.clients import canonicalize_url  # noqa: E402


def batches(urls: list[str]) -> list[dict[str, object]]:
    return [
        {
            "query": "discarded",
            "answer": "discarded",
            "results": [
                {
                    "url": url,
                    "fetch_url": url,
                    "title": "discarded",
                }
                for url in urls
            ],
            "hosted_search_trace": {
                "actions": [
                    {
                        "id": "action-1",
                        "sources": [
                            {"url": url, "title": "discarded"} for url in urls
                        ],
                    }
                ]
            },
        }
    ]


class V24967RequirementAwareSourceAllocationTests(unittest.TestCase):
    def test_exact_authority_paths_match(self) -> None:
        self.assertEqual(
            policy.authority_requirement(
                "https://pypi.org/project/Example_Pkg/",
                project="example-pkg",
                repository="owner/repository",
            ),
            "pypi_project",
        )
        self.assertEqual(
            policy.authority_requirement(
                "https://github.com/Owner/Repository/releases/tag/v1",
                project="example-pkg",
                repository="owner/repository",
            ),
            "github_release",
        )

    def test_lookalikes_and_wrong_records_are_rejected(self) -> None:
        values = (
            "https://pypi.org.evil.example/project/example-pkg/",
            "https://pypi.org/project/example-pkg-typo/",
            "https://github.com/owner/repository/issues/1",
            "https://github.com/owner/other/releases/latest",
            "https://evil.example/github.com/owner/repository/releases/latest",
        )
        self.assertTrue(
            all(
                policy.authority_requirement(
                    value,
                    project="example-pkg",
                    repository="owner/repository",
                )
                is None
                for value in values
            )
        )

    def test_requirement_selection_precedes_source_fair_fill(self) -> None:
        urls = [
            "https://docs.example/a",
            "https://mirror.example/b",
            "https://github.com/owner/repository/releases/latest",
            "https://pypi.org/project/example-pkg/",
            "https://other.example/c",
        ]
        value = policy.select_requirement_aware(
            batches(urls),
            cap=3,
            project="example-pkg",
            repository="owner/repository",
        )
        selected = [canonicalize_url(item["url"]) for item in value["selected"]]
        self.assertEqual(len(selected), 3)
        self.assertEqual(
            {
                policy.authority_requirement(
                    url,
                    project="example-pkg",
                    repository="owner/repository",
                )
                for url in selected[:2]
            },
            set(policy.REQUIREMENTS),
        )
        self.assertEqual(value["receipt"]["cumulative_requirement_count"], 2)

    def test_prior_requirement_is_not_forced_again(self) -> None:
        urls = [
            "https://pypi.org/project/example-pkg/",
            "https://github.com/owner/repository/releases/latest",
            "https://docs.example/a",
        ]
        value = policy.select_requirement_aware(
            batches(urls),
            cap=2,
            project="example-pkg",
            repository="owner/repository",
            prior_requirements={"pypi_project"},
        )
        self.assertIn("github_release", value["cumulative_requirements"])
        self.assertEqual(value["receipt"]["new_requirement_count"], 1)

    def test_requirement_aware_evidence_reserves_both_namespaces(self) -> None:
        leads = [
            {"url": "https://noise.example/a"},
            {"url": "https://pypi.org/project/example-pkg/"},
            {"url": "https://github.com/owner/repository/releases/latest"},
        ]
        fetched = {
            canonicalize_url(lead["url"]): {
                "title": "Fetched title",
                "raw_content": character * 8_000,
            }
            for lead, character in zip(leads, "npg", strict=True)
        }
        evidence, receipt = policy.compose_evidence(
            leads,
            fetched,
            project="example-pkg",
            repository="owner/repository",
            total_chars=12_000,
            requirement_quota_chars=4_000,
            requirement_aware=True,
        )
        self.assertEqual(len(evidence), 12_000)
        self.assertGreaterEqual(receipt["pypi_project_evidence_chars"], 4_000)
        self.assertGreaterEqual(receipt["github_release_evidence_chars"], 4_000)

    def test_stable_evidence_can_spend_budget_before_requirements(self) -> None:
        leads = [
            {"url": "https://noise.example/a"},
            {"url": "https://pypi.org/project/example-pkg/"},
            {"url": "https://github.com/owner/repository/releases/latest"},
        ]
        fetched = {
            canonicalize_url(lead["url"]): {
                "title": "Fetched title",
                "raw_content": character * 8_000,
            }
            for lead, character in zip(leads, "npg", strict=True)
        }
        _evidence, receipt = policy.compose_evidence(
            leads,
            fetched,
            project="example-pkg",
            repository="owner/repository",
            total_chars=6_000,
            requirement_quota_chars=2_000,
            requirement_aware=False,
        )
        self.assertEqual(receipt["total_requirement_evidence_chars"], 0)

    def test_insufficient_total_content_fails_closed(self) -> None:
        leads = [{"url": "https://pypi.org/project/example-pkg/"}]
        fetched = {
            canonicalize_url(leads[0]["url"]): {"raw_content": "short"}
        }
        with self.assertRaises(RuntimeError):
            policy.compose_evidence(
                leads,
                fetched,
                project="example-pkg",
                repository="owner/repository",
                total_chars=1_000,
                requirement_quota_chars=200,
                requirement_aware=True,
            )

    def test_source_has_no_io_model_evaluator_or_credential_capability(self) -> None:
        source = (
            ROOT
            / "src/deepwide_agent/v24967_requirement_aware_source_allocation.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any(
                token in name
                for name in imports
                for token in ("requests", "subprocess", "evaluator", "finalize")
            )
        )
        self.assertNotIn("os.environ", source)
        self.assertNotIn("open(", source)


if __name__ == "__main__":
    unittest.main()
