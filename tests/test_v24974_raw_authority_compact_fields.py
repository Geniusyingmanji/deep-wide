from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24974_raw_authority_compact_fields as raw  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


PROJECT = "never-probed-demo"
REPOSITORY = "demo-owner/demo-repo"
RAW_EVIDENCE = ("raw noisy authority prefix\n" * 1000)[:16_000]


def pypi_page(*, name: str = PROJECT, version: str = "2.4.0") -> dict:
    return {
        "url": f"https://pypi.org/pypi/{PROJECT}/json",
        "text": json.dumps(
            {
                "noise": "x" * 12_000,
                "info": {
                    "name": name,
                    "version": version,
                    "requires_python": ">=3.10, <4",
                },
            }
        ),
    }


def github_page(
    *, repository: str = REPOSITORY, tag: str = "v2.4.0", date: str = "2026-08-08"
) -> dict:
    return {
        "url": f"https://github.com/{REPOSITORY}/releases",
        "text": (
            f"<html><head><title>Releases · {repository} · GitHub</title></head>"
            + "<script>" + "n" * 12_000 + "</script>"
            + f'<section><a href="/{repository}/releases/tag/{tag}">Named release</a>'
            + f'<a href="/{repository}/releases/latest">Latest</a>'
            + f'<relative-time datetime="{date}T12:00:00Z">date</relative-time>'
            + "</section></html>"
        ),
    }


class V24974RawAuthorityCompactFieldsTests(unittest.TestCase):
    def build(self, pages=None):
        return raw.build_compact_evidence(
            pages or [pypi_page(), github_page()],
            RAW_EVIDENCE,
            project=PROJECT,
            repository=REPOSITORY,
            total_chars=len(RAW_EVIDENCE),
        )

    def test_noisy_full_pages_surface_late_fields_under_same_total_cap(self) -> None:
        result = self.build()
        evidence = result["evidence"]
        self.assertEqual(len(evidence), len(RAW_EVIDENCE))
        self.assertNotEqual(evidence, RAW_EVIDENCE)
        self.assertIn("PyPI latest version: 2.4.0", evidence)
        self.assertIn("Requires-Python: >=3.10, <4", evidence)
        self.assertIn("GitHub latest release tag: v2.4.0", evidence)
        self.assertIn("2026-08-08", evidence)
        self.assertEqual(result["receipt"]["unique_bound_field_count"], 4)

    def test_projection_receipt_is_counts_only(self) -> None:
        receipt = self.build()["projection_receipt"]
        encoded = json.dumps(receipt, sort_keys=True)
        self.assertEqual(receipt["raw_page_count"], 2)
        self.assertEqual(receipt["projected_page_count"], 2)
        for forbidden in (PROJECT, REPOSITORY, "2.4.0", "2026-08-08", "https://"):
            self.assertNotIn(forbidden, encoded)

    def test_exact_authority_pair_and_primary_identities_are_required(self) -> None:
        with self.assertRaises(ValueError):
            self.build([pypi_page()])
        wrong_url = github_page()
        wrong_url["url"] = "https://github.com/other/repo/releases"
        with self.assertRaises(ValueError):
            self.build([pypi_page(), wrong_url])
        with self.assertRaises(ValueError):
            self.build([pypi_page(name="other"), github_page()])
        with self.assertRaises(ValueError):
            self.build([pypi_page(), github_page(repository="other/repo")])

    def test_named_release_anchor_uses_tag_from_exact_href(self) -> None:
        result = self.build([pypi_page(), github_page(tag="release-2.4")])
        self.assertIn("GitHub latest release tag: release-2.4", result["evidence"])

    def test_ambiguous_latest_release_fails_closed(self) -> None:
        page = github_page()
        page["text"] = page["text"].replace(
            "</section></html>",
            '<a href="/demo-owner/demo-repo/releases/tag/v9.9">Other</a>'
            '<a href="/demo-owner/demo-repo/releases/latest">Latest</a>'
            '<relative-time datetime="2026-08-09T00:00:00Z">date</relative-time>'
            "</section></html>",
        )
        with self.assertRaises(ValueError):
            self.build([pypi_page(), page])

    def test_oversized_nul_and_duplicate_namespace_fail_closed(self) -> None:
        oversized = pypi_page()
        oversized["text"] = "x" * (raw.MAX_RAW_PAGE_CHARS + 1)
        with self.assertRaises(ValueError):
            self.build([oversized, github_page()])
        nul = pypi_page()
        nul["text"] += "\0"
        with self.assertRaises(ValueError):
            self.build([nul, github_page()])
        duplicate = copy.deepcopy(pypi_page())
        with self.assertRaises(ValueError):
            self.build([pypi_page(), duplicate])

    def test_source_is_pure_label_blind_and_has_no_effect_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24974_raw_authority_compact_fields.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        forbidden = ("requests", "socket", "subprocess", "urllib.request", "evaluator")
        self.assertFalse(any(any(token in name for token in forbidden) for name in imports))
        self.assertEqual(semantic_audit._accesses(path, ROOT), [])
        self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])


if __name__ == "__main__":
    unittest.main()
