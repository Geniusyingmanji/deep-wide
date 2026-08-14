from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25532_official_tld_population_selection as target  # noqa: E402


def official_fixture() -> str:
    names = [f"A{index:04d}" for index in range(1000)]
    insert = names.index("A0500") + 1
    names[insert:insert] = [
        "BRADESCO",
        *[f"CANDIDATE{index:02d}" for index in range(40)],
    ]
    names = sorted(set(names + ["AAA", "AARP", "BANK"]))
    return "# Version 2026081400, Last Updated Thu Aug 14 00:00:00 2026 UTC\n" + "\n".join(names) + "\n"


class V25532OfficialTldPopulationSelectionTests(unittest.TestCase):
    def test_consumed_union_binds_predecessor_and_all_explicit_populations(self) -> None:
        consumed = target.consumed_identities()
        self.assertIn(target.PREDECESSOR, consumed)
        for population in (target.prior9, target.prior16, target.prior23):
            self.assertTrue(
                {
                    identity
                    for pair in population.PAIRS
                    for identity in pair
                }.issubset(consumed)
            )
        self.assertTrue(set(target.research.STUDY_IDENTITIES).issubset(consumed))

    def test_official_parser_and_next_exact_forty_rule(self) -> None:
        names = target.parse_official_names(official_fixture())
        selected = target.selected_identities(names)
        self.assertEqual(len(selected), 40)
        self.assertEqual(selected[0], ".candidate00")
        self.assertEqual(selected[-1], ".candidate39")
        pairs = target.validate_pairs(
            [tuple(selected[index : index + 2]) for index in range(0, 40, 2)]
        )
        self.assertEqual(len(pairs), 20)

    def test_overlap_missing_predecessor_or_nonconsecutive_shape_fails(self) -> None:
        names = target.parse_official_names(official_fixture())
        for kind in ("overlap", "missing", "order"):
            changed = list(names)
            if kind == "overlap":
                start = changed.index(target.PREDECESSOR) + 1
                changed[start] = ".bank"
                changed = sorted(set(changed))
            elif kind == "missing":
                changed.remove(target.PREDECESSOR)
            else:
                changed[0], changed[1] = changed[1], changed[0]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.selected_identities(changed)

    def test_policy_is_name_only_one_attempt_and_authorizes_no_forward(self) -> None:
        policy = target.selection_policy()
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
        self.assertEqual(policy["positive_signed_credit_count"], 0)

    def test_manifest_tamper_fails(self) -> None:
        value = target.manifest()
        self.assertEqual(target.validate_manifest(value), value)
        changed = copy.deepcopy(value)
        changed["predecessor"] = ".bank"
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
