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

from deepwide_agent import v24976_section_bound_raw_authority_fields as section  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


PROJECT = "section-demo"
REPOSITORY = "owner/repo"
RAW = "x" * 16_000


def pypi_page() -> dict:
    return {
        "url": f"https://pypi.org/pypi/{PROJECT}/json",
        "text": json.dumps(
            {
                "info": {
                    "name": PROJECT,
                    "version": "3.2.1",
                    "requires_python": ">=3.10",
                }
            }
        ),
    }


def github_page(*, prefix: str = "", sections: str | None = None) -> dict:
    release = sections or (
        '<section id="release-v3.2.1">'
        '<a href="/owner/repo/releases/tag/v3.2.1">Display title</a>'
        '<a href="/owner/repo/releases/latest">Latest</a>'
        '<relative-time datetime="2026-08-08T12:00:00Z">date</relative-time>'
        "</section>"
    )
    return {
        "url": f"https://github.com/{REPOSITORY}/releases",
        "text": (
            f"<html><head><title>Releases · {REPOSITORY} · GitHub</title></head>"
            + prefix
            + release
            + "</html>"
        ),
    }


class V24976SectionBoundRawAuthorityFieldsTests(unittest.TestCase):
    def build(self, github=None):
        return section.build_compact_evidence(
            [pypi_page(), github or github_page()],
            RAW,
            project=PROJECT,
            repository=REPOSITORY,
            total_chars=len(RAW),
        )

    def test_nearby_toc_tags_cannot_create_false_ambiguity(self) -> None:
        toc = (
            '<nav><a href="/owner/repo/releases/tag/v1">v1</a>'
            '<a href="/owner/repo/releases/tag/v2">v2</a></nav>'
        )
        result = self.build(github_page(prefix=toc))
        self.assertTrue(result["receipt"]["record_admitted"])
        self.assertIn("GitHub latest release tag: v3.2.1", result["evidence"])

    def test_duplicate_latest_markers_in_same_section_deduplicate(self) -> None:
        release = (
            '<section><a href="/owner/repo/releases/tag/v3.2.1">Title</a>'
            '<a href="/owner/repo/releases/latest">Latest</a>'
            '<a href="/owner/repo/releases/latest">Latest mobile</a>'
            '<relative-time datetime="2026-08-08T12:00:00Z">date</relative-time>'
            "</section>"
        )
        result = self.build(github_page(sections=release))
        self.assertEqual(result["receipt"]["unique_bound_field_count"], 4)

    def test_tag_and_latest_in_different_sections_fail_closed(self) -> None:
        release = (
            '<section><a href="/owner/repo/releases/tag/v3.2.1">Title</a></section>'
            '<section><a href="/owner/repo/releases/latest">Latest</a>'
            '<relative-time datetime="2026-08-08T12:00:00Z">date</relative-time></section>'
        )
        with self.assertRaises(ValueError):
            self.build(github_page(sections=release))

    def test_two_distinct_latest_sections_are_ambiguous(self) -> None:
        release = "".join(
            f'<section><a href="/owner/repo/releases/tag/v{version}">Title</a>'
            '<a href="/owner/repo/releases/latest">Latest</a>'
            f'<relative-time datetime="2026-08-0{version}T00:00:00Z">date</relative-time></section>'
            for version in (1, 2)
        )
        with self.assertRaises(ValueError):
            self.build(github_page(sections=release))

    def test_projection_receipt_declares_same_section_binding(self) -> None:
        receipt = self.build()["projection_receipt"]
        self.assertTrue(receipt["tag_latest_and_date_bound_to_same_release_section"])
        encoded = json.dumps(receipt, sort_keys=True)
        for forbidden in (PROJECT, REPOSITORY, "3.2.1", "2026-08-08", "https://"):
            self.assertNotIn(forbidden, encoded)

    def test_source_is_pure_label_blind_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v24976_section_bound_raw_authority_fields.py"
        imports = []
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
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
