from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25580_pypi_stable_version_truth as target  # noqa: E402


def payload(
    identity: str, releases: dict[str, list[dict[str, object]]]
) -> bytes:
    return json.dumps(
        {"info": {"name": identity}, "releases": releases}, sort_keys=True
    ).encode()


class V25580PypiStableVersionTruthTests(unittest.TestCase):
    def test_latest_stable_uses_pep440_and_file_bearing_releases(self) -> None:
        raw = payload(
            "Demo_Pkg",
            {
                "1.9": [{}],
                "1.10rc1": [{}],
                "1.10": [{"filename": "demo.whl"}],
                "2.0": [],
            },
        )
        value = target.parse_response(raw, "demo-pkg")
        self.assertEqual(value["canonical_project_name"], "Demo_Pkg")
        self.assertEqual(value["availability"], "stable_release")
        self.assertEqual(value["latest_stable_version"], "1.10")
        self.assertEqual(value["normalized_latest_stable_version"], "1.10")
        self.assertEqual(value["canonical_value"], "1.10")
        self.assertEqual(value["release_file_count"], 1)

    def test_only_prerelease_or_dev_is_valid_unknown(self) -> None:
        raw = payload(
            "preview-only",
            {"3.0b1": [{}], "3.0.dev2": [{}], "4.0": []},
        )
        value = target.parse_response(raw, "preview-only")
        self.assertEqual(value["availability"], "no_stable_release")
        self.assertEqual(value["canonical_value"], "Unknown")
        self.assertIsNone(value["latest_stable_version"])
        self.assertTrue(value["no_stable_release_is_valid_unknown"])

    def test_semantic_version_accepts_pep440_aliases_and_rejects_unknown_predev(self) -> None:
        self.assertEqual(target.semantic_version("1.0.0"), target.semantic_version("1.0"))
        self.assertIsNone(target.semantic_version("Unknown"))
        self.assertIsNone(target.semantic_version("1.0rc1"))
        self.assertIsNone(target.semantic_version("1.0.dev1"))
        self.assertIsNone(target.semantic_version("not a version"))

    def test_identity_schema_invalid_version_alias_and_empty_fail_closed(self) -> None:
        cases = (
            (payload("wrong", {"1.0": [{}]}), "right"),
            (payload("demo", {"bad version": [{}]}), "demo"),
            (payload("demo", {"1.0": [{}], "1.0.0": [{}]}), "demo"),
            (payload("demo", {}), "demo"),
            (payload("demo", {"1.0": ["not-a-file-record"]}), "demo"),
        )
        for raw, identity in cases:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                target.parse_response(raw, identity)

    def test_record_resealed_value_name_or_credit_tamper_fails(self) -> None:
        value = target.parse_response(payload("demo", {"1.0": [{}]}), "demo")
        self.assertEqual(target.validate_record(value), value)
        for kind in ("value", "name", "credit"):
            changed = copy.deepcopy(value)
            if kind == "value":
                changed["canonical_value"] = "2.0"
            elif kind == "name":
                changed["canonical_project_name"] = "other"
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("record_payload_sha256")
            changed["record_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_record(changed)

    def test_module_is_pure_and_has_no_external_effect_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
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
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden_call in ("open(", "getenv(", "requests.get(", "fetch_urls("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
