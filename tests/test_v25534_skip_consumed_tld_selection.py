from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25534_skip_consumed_tld_selection as target  # noqa: E402
from test_v25532_official_tld_population_selection import official_fixture  # noqa: E402


def skip_fixture() -> str:
    names = target.parse_official_names(official_fixture())
    insertion = names.index(target.PREDECESSOR) + 1
    raw = [value.removeprefix(".").upper() for value in names]
    raw[insertion:insertion] = [
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
    ]
    raw = sorted(set(raw))
    return (
        "# Version 2026081401, Last Updated Thu Aug 14 01:00:00 2026 UTC\n"
        + "\n".join(raw)
        + "\n"
    )


class V25534SkipConsumedTldSelectionTests(unittest.TestCase):
    def test_skips_consumed_names_and_takes_first_forty_unconsumed(self) -> None:
        names = target.parse_official_names(skip_fixture())
        selected = target.selected_identities(names)
        self.assertEqual(len(selected), 40)
        self.assertEqual(selected[0], ".candidate00")
        self.assertEqual(selected[-1], ".candidate39")
        self.assertFalse(set(selected) & target.consumed_identities())
        pairs = target.validate_pairs(
            [tuple(selected[index : index + 2]) for index in range(0, 40, 2)]
        )
        self.assertEqual(len(pairs), 20)

    def test_inserting_consumed_names_does_not_change_selected_vector(self) -> None:
        plain = target.parse_official_names(official_fixture())
        mixed = target.parse_official_names(skip_fixture())
        self.assertEqual(
            target.selected_identities(plain),
            target.selected_identities(mixed),
        )

    def test_order_missing_predecessor_or_short_suffix_fails(self) -> None:
        names = target.parse_official_names(skip_fixture())
        for kind in ("order", "missing", "short"):
            changed = list(names)
            if kind == "order":
                changed[0], changed[1] = changed[1], changed[0]
            elif kind == "missing":
                changed.remove(target.PREDECESSOR)
            else:
                changed = changed[: changed.index(target.PREDECESSOR) + 10]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.selected_identities(changed)

    def test_policy_records_prior_no_go_and_authorizes_name_snapshot_only(self) -> None:
        policy = target.selection_policy()
        self.assertFalse(policy["v25533_old_raw_consecutive_rule_retry_or_reuse"])
        self.assertTrue(policy["complete_v25532_consumed_union_frozen_unchanged"])
        self.assertEqual(policy["maximum_http_attempts"], 1)
        self.assertFalse(policy["allow_redirects"])
        self.assertFalse(
            policy[
                "detail_endpoint_page_field_value_question_prediction_quality_or_outcome_read"
            ]
        )
        self.assertFalse(
            policy[
                "external_mechanism_quality_deepwidebench_or_leaderboard_launch_authorized"
            ]
        )

    def test_manifest_tamper_fails(self) -> None:
        value = target.manifest()
        self.assertEqual(target.validate_manifest(value), value)
        changed = copy.deepcopy(value)
        changed["selection_policy"]["maximum_http_attempts"] = 2
        with self.assertRaises(ValueError):
            target.validate_manifest(changed)

    def test_module_is_pure_and_has_no_effect_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any(
                name == blocked or name.startswith(blocked + ".")
                for blocked in (
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "httpx",
                )
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
