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

from deepwide_agent import v24972_identity_bound_compact_fields as fields  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


PROJECT = "demo-pkg"
REPOSITORY = "demo-owner/demo-repo"
RAW = ("raw shared evidence\n" * 400)[:6000]


def pypi_html(version: str = "2.3.4", project: str = PROJECT) -> dict:
    return {
        "url": f"https://pypi.org/project/{project}/",
        "text": f"{project} · PyPI\n\n{project} {version}\n\nDescription\n",
    }


def pypi_json(
    version: str = "2.3.4",
    requires_python: str | None = ">=3.10",
    project: str = PROJECT,
) -> dict:
    return {
        "url": f"https://pypi.org/pypi/{project}/json",
        "text": json.dumps(
            {
                "info": {
                    "name": project,
                    "version": version,
                    "requires_python": requires_python,
                }
            }
        ),
    }


def github_html(
    tag: str = "v2.3.4",
    released: str = "2026-08-01",
    repository: str = REPOSITORY,
) -> dict:
    return {
        "url": f"https://github.com/{repository}/releases",
        "text": (
            f"Releases · {repository} · GitHub\n"
            f"Releases: {repository}\nRelease list\n"
            f"{tag} {released}\nLatest\nCompare\n"
        ),
    }


def github_json(
    tag: str = "v2.3.4",
    released: str = "2026-08-01T12:30:00Z",
    repository: str = REPOSITORY,
    *,
    draft: bool = False,
    prerelease: bool = False,
) -> dict:
    return {
        "url": f"https://api.github.com/repos/{repository}/releases/latest",
        "text": json.dumps(
            {
                "html_url": f"https://github.com/{repository}/releases/tag/{tag}",
                "tag_name": tag,
                "published_at": released,
                "draft": draft,
                "prerelease": prerelease,
            }
        ),
    }


class V24972IdentityBoundCompactFieldsTests(unittest.TestCase):
    def build(self, pages):
        return fields.build_compact_evidence(
            pages,
            RAW,
            project=PROJECT,
            repository=REPOSITORY,
            total_chars=len(RAW),
        )

    def test_exact_authority_surfaces_only(self) -> None:
        accepted = {
            "https://pypi.org/project/demo-pkg/": "pypi_html",
            "https://pypi.org/pypi/demo-pkg/json": "pypi_json",
            "https://github.com/demo-owner/demo-repo/releases": "github_html",
            "https://api.github.com/repos/demo-owner/demo-repo/releases/latest": "github_json",
        }
        for url, expected in accepted.items():
            self.assertEqual(
                fields.authority_kind(
                    url, project=PROJECT, repository=REPOSITORY
                ),
                expected,
            )
        rejected = (
            "https://evil.pypi.org/project/demo-pkg/",
            "https://pypi.org/project/demo-pkg/files",
            "https://pypi.org/project/other/",
            "https://pypi.org/project/demo-pkg/?answer=1",
            "https://github.com/demo-owner/demo-repo/issues",
            "https://github.com/demo-owner/other/releases",
            "https://github.com.evil.example/demo-owner/demo-repo/releases",
            "https://api.github.com/repos/demo-owner/demo-repo/releases/1",
        )
        for url in rejected:
            self.assertIsNone(
                fields.authority_kind(
                    url, project=PROJECT, repository=REPOSITORY
                )
            )

    def test_html_pages_form_compact_record_with_missing_unknown(self) -> None:
        result = self.build([pypi_html(), github_html()])
        record = result["record"]["fields"]
        self.assertEqual(record["pypi_latest_version"]["value"], "2.3.4")
        self.assertEqual(record["requires_python"]["value"], fields.UNKNOWN)
        self.assertEqual(record["github_latest_release_tag"]["value"], "v2.3.4")
        self.assertEqual(
            record["github_latest_release_date"]["value"], "2026-08-01"
        )
        self.assertEqual(len(result["evidence"]), len(RAW))
        self.assertTrue(result["receipt"]["record_admitted"])
        self.assertEqual(result["receipt"]["unique_bound_field_count"], 3)
        self.assertEqual(result["receipt"]["unknown_field_count"], 1)

    def test_json_pages_form_all_four_fields(self) -> None:
        result = self.build([pypi_json(), github_json()])
        record = result["record"]["fields"]
        self.assertEqual(
            {name: row["value"] for name, row in record.items()},
            {
                "pypi_latest_version": "2.3.4",
                "requires_python": ">=3.10",
                "github_latest_release_tag": "v2.3.4",
                "github_latest_release_date": "2026-08-01",
            },
        )
        self.assertEqual(result["receipt"]["unique_bound_field_count"], 4)
        self.assertEqual(result["receipt"]["unknown_field_count"], 0)

    def test_same_value_html_json_corroboration_is_not_a_conflict(self) -> None:
        result = self.build(
            [pypi_html(), pypi_json(), github_html(), github_json()]
        )
        self.assertTrue(result["receipt"]["record_admitted"])
        self.assertEqual(result["receipt"]["field_observation_count"], 7)
        self.assertEqual(result["receipt"]["conflicting_field_count"], 0)
        self.assertEqual(
            len(result["record"]["fields"]["pypi_latest_version"]["sources"]),
            2,
        )

    def test_any_cross_page_field_conflict_returns_raw_identity(self) -> None:
        result = self.build([pypi_html("2.3.4"), pypi_json("9.9.9")])
        self.assertEqual(result["evidence"], RAW)
        self.assertFalse(result["receipt"]["record_admitted"])
        self.assertFalse(result["receipt"]["candidate_evidence_changed"])
        self.assertEqual(result["receipt"]["conflicting_field_count"], 1)
        self.assertTrue(
            all(
                row["value"] == fields.UNKNOWN
                for row in result["record"]["fields"].values()
            )
        )

    def test_wrong_primary_identity_is_counted_but_never_bound(self) -> None:
        wrong = pypi_json(project="other")
        wrong["url"] = "https://pypi.org/pypi/demo-pkg/json"
        result = self.build([wrong])
        self.assertEqual(result["evidence"], RAW)
        self.assertEqual(result["receipt"]["exact_authority_page_count"], 1)
        self.assertEqual(result["receipt"]["identity_mismatch_page_count"], 1)
        self.assertEqual(result["receipt"]["identity_bound_page_count"], 0)

    def test_wrong_github_json_tag_address_is_rejected(self) -> None:
        page = github_json(tag="v2.3.4")
        payload = json.loads(page["text"])
        payload["html_url"] = (
            "https://github.com/demo-owner/demo-repo/releases/tag/v9.9.9"
        )
        page["text"] = json.dumps(payload)
        result = self.build([page])
        self.assertFalse(result["receipt"]["record_admitted"])
        self.assertEqual(result["receipt"]["identity_mismatch_page_count"], 1)

    def test_draft_and_prerelease_latest_json_fail_closed(self) -> None:
        for page in (github_json(draft=True), github_json(prerelease=True)):
            result = self.build([page])
            self.assertFalse(result["receipt"]["record_admitted"])
            self.assertEqual(result["receipt"]["identity_mismatch_page_count"], 1)

    def test_html_without_explicit_latest_marker_is_rejected(self) -> None:
        page = github_html()
        page["text"] = page["text"].replace("Latest", "Compare")
        result = self.build([page])
        self.assertFalse(result["receipt"]["record_admitted"])
        self.assertEqual(result["receipt"]["identity_mismatch_page_count"], 1)

    def test_provider_summary_and_title_cannot_supply_fields(self) -> None:
        page = {
            "url": "https://pypi.org/project/demo-pkg/",
            "title": "demo-pkg 9.9.9 Requires-Python >=1",
            "content": "provider says demo-pkg 9.9.9",
            "text": "demo-pkg · PyPI\nDescription only",
        }
        result = self.build([page])
        self.assertFalse(result["receipt"]["record_admitted"])
        self.assertNotIn("9.9.9", result["evidence"])

    def test_malformed_empty_and_oversized_pages_fail_closed(self) -> None:
        oversized = pypi_html()
        oversized["text"] = "x" * (fields.MAX_PAGE_CHARS + 1)
        result = self.build([None, {"url": "bad"}, oversized])
        self.assertEqual(result["evidence"], RAW)
        self.assertEqual(result["receipt"]["malformed_page_count"], 1)
        self.assertEqual(result["receipt"]["identity_mismatch_page_count"], 1)

    def test_input_and_budget_validation(self) -> None:
        with self.assertRaises(ValueError):
            fields.build_compact_evidence(
                [pypi_html()],
                RAW[:-1],
                project=PROJECT,
                repository=REPOSITORY,
                total_chars=len(RAW),
            )

    def test_compact_record_must_fit_whole_or_candidate_is_identity(self) -> None:
        raw = "x" * 64
        result = fields.build_compact_evidence(
            [pypi_json(), github_json()],
            raw,
            project=PROJECT,
            repository=REPOSITORY,
            total_chars=len(raw),
        )
        self.assertEqual(result["evidence"], raw)
        self.assertFalse(result["receipt"]["record_admitted"])
        self.assertEqual(result["receipt"]["compact_prefix_chars"], 0)
        with self.assertRaises(ValueError):
            self.build([pypi_html()] * (fields.MAX_PAGES + 1))
        with self.assertRaises(ValueError):
            fields.build_compact_evidence(
                [pypi_html()],
                RAW,
                project="bad project!",
                repository=REPOSITORY,
                total_chars=len(RAW),
            )

    def test_receipt_is_counts_only_and_tamper_fails(self) -> None:
        result = self.build([pypi_json(), github_json()])
        receipt = result["receipt"]
        encoded = json.dumps(receipt, sort_keys=True)
        for literal in (
            PROJECT,
            REPOSITORY,
            "2.3.4",
            ">=3.10",
            "2026-08-01",
            "https://",
        ):
            self.assertNotIn(literal, encoded)
        changed = copy.deepcopy(receipt)
        changed["unique_bound_field_count"] = 3
        changed["unknown_field_count"] = 1
        with self.assertRaises(ValueError):
            fields.validate_receipt(changed, total_chars=len(RAW))
        changed["receipt_payload_sha256"] = fields.payload_sha256(
            {key: value for key, value in changed.items() if key != "receipt_payload_sha256"}
        )
        fields.validate_receipt(changed, total_chars=len(RAW))

    def test_source_is_pure_label_blind_and_has_no_effect_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24972_identity_bound_compact_fields.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        forbidden = (
            "requests",
            "urllib.request",
            "subprocess",
            "socket",
            "evaluator",
            "finalize",
        )
        self.assertFalse(any(any(token in name for token in forbidden) for name in imports))
        self.assertEqual(semantic_audit._accesses(path, ROOT), [])
        self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])


if __name__ == "__main__":
    unittest.main()
