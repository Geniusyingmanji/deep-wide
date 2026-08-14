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

from deepwide_agent import v25552_pypi_stable_truth as target  # noqa: E402


def payload(identity: str, releases: dict[str, list[dict[str, object]]]) -> bytes:
    return json.dumps(
        {"info": {"name": identity}, "releases": releases}, sort_keys=True
    ).encode()


class V25552PypiStableTruthTests(unittest.TestCase):
    def test_latest_stable_uses_pep440_and_earliest_utc_file_date(self) -> None:
        raw = payload(
            "demo_pkg",
            {
                "1.9": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}],
                "1.10rc1": [
                    {"upload_time_iso_8601": "2026-04-01T00:00:00Z"}
                ],
                "1.10": [
                    {"upload_time_iso_8601": "2026-03-02T00:00:00Z"},
                    {"upload_time_iso_8601": "2026-03-01T00:30:00+02:00"},
                ],
            },
        )
        value = target.parse_response(raw, "demo-pkg")
        self.assertEqual(value["availability"], "stable_release")
        self.assertEqual(value["latest_stable_version"], "1.10")
        self.assertEqual(value["release_date_iso"], "2026-02-28")
        self.assertEqual(value["canonical_value"], "2026年2月28日")

    def test_only_prerelease_or_dev_is_valid_unknown(self) -> None:
        raw = payload(
            "preview-only",
            {
                "3.0.0b1": [
                    {"upload_time_iso_8601": "2026-01-01T00:00:00Z"}
                ],
                "3.0.0.dev2": [
                    {"upload_time_iso_8601": "2026-01-02T00:00:00Z"}
                ],
            },
        )
        value = target.parse_response(raw, "preview-only")
        self.assertEqual(value["availability"], "no_stable_release")
        self.assertEqual(value["canonical_value"], "Unknown")
        self.assertIsNone(value["sort_key"])
        self.assertTrue(value["no_stable_release_is_valid_unknown"])

    def test_unknown_sort_is_after_known_and_stable_within_unknowns(self) -> None:
        first_unknown = target.parse_response(
            payload(
                "u-one",
                {"1.0rc1": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}]},
            ),
            "u-one",
        )
        old = target.parse_response(
            payload(
                "old",
                {"1.0": [{"upload_time_iso_8601": "2025-01-01T00:00:00Z"}]},
            ),
            "old",
        )
        new = target.parse_response(
            payload(
                "new",
                {"1.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}]},
            ),
            "new",
        )
        second_unknown = copy.deepcopy(first_unknown)
        second_unknown["identity"] = "u-two"
        second_unknown.pop("record_payload_sha256")
        second_unknown["record_payload_sha256"] = target.payload_sha256(second_unknown)
        ordered = target.ordered_records(
            [first_unknown, old, second_unknown, new]
        )
        self.assertEqual(
            [row["identity"] for row in ordered],
            ["new", "old", "u-one", "u-two"],
        )

    def test_identity_schema_timezone_invalid_version_and_alias_fail_closed(self) -> None:
        cases = (
            (payload("wrong", {"1.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}]}), "right"),
            (payload("demo", {"1.0": [{"upload_time": "2026-01-01T00:00:00"}]}), "demo"),
            (payload("demo", {"bad version": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}]}), "demo"),
            (
                payload(
                    "demo",
                    {
                        "1.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}],
                        "1.0.0": [{"upload_time_iso_8601": "2026-01-02T00:00:00Z"}],
                    },
                ),
                "demo",
            ),
            (payload("demo", {}), "demo"),
        )
        for raw, identity in cases:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                target.parse_response(raw, identity)

    def test_record_seal_tamper_fails(self) -> None:
        value = target.parse_response(
            payload(
                "demo",
                {"1.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}]},
            ),
            "demo",
        )
        self.assertEqual(target.validate_record(value), value)
        for kind in ("value", "availability", "credit"):
            changed = copy.deepcopy(value)
            if kind == "value":
                changed["canonical_value"] = "Unknown"
            elif kind == "availability":
                changed["availability"] = "no_stable_release"
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("record_payload_sha256")
            changed["record_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_record(changed)

    def test_module_is_pure_and_has_no_forward_or_evaluator_effect_capability(self) -> None:
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
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden_call in ("open(", "getenv(", "requests.get(", "fetch_urls("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
