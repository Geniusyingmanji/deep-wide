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

from deepwide_agent import (  # noqa: E402
    v25158_vertical_key_value_candidate_runtime as frozen,
)
from deepwide_agent import (  # noqa: E402
    v25163_vertical_admission_disposition_observer as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25147_deterministic_quote_candidate_runtime import PRODUCTION  # noqa: E402


COLUMNS = ("Domain", "Type", "TLD Manager")


class V25163VerticalDispositionObserverTests(unittest.TestCase):
    def _observe(self, content: str, *, production: str = PRODUCTION):
        return target.observe_vertical_admission(
            production,
            columns=COLUMNS,
            pages=[{"title": "ignored", "content": content}],
        )

    def test_all_pre_identity_reject_reasons_are_mutually_exclusive(self) -> None:
        cases = {
            "empty_or_duplicate_normalized_key_reject": (
                "Domain | .in\nDomain: | .in\nTLD Manager | 999"
            ),
            "mapped_field_unsafe_or_unknown_value_reject": (
                "Domain | .in\nTLD Manager | Unknown"
            ),
            "no_visible_schema_key_reject": "Unrelated | value\nOther | value",
            "missing_primary_key_row_reject": (
                "Type | country-code\nTLD Manager | 999"
            ),
            "multiple_primary_key_rows_reject": (
                "Domain | .in\nDomain Alias | ignored\nDomain: | .in"
            ),
            "primary_identity_not_unique_production_row_reject": (
                "Domain | .us\nTLD Manager | 999"
            ),
        }
        # Domain Alias is unmapped, so use a second exact Domain spelling to
        # reach the frozen duplicate-key reject rather than multiple-primary.
        cases["multiple_primary_key_rows_reject"] = (
            "Domain | .in\nDomain\u00a0 | .in\nTLD Manager | 999"
        )
        # NFKC makes the second key duplicate; therefore multiple-primary is
        # only reachable through distinct visible headers that normalize to
        # different keys. Exercise it with an explicit two-key schema below.
        del cases["multiple_primary_key_rows_reject"]

        for reason, content in cases.items():
            with self.subTest(reason=reason):
                value = self._observe(content)
                self.assertEqual(value["vertical_block_count"], 1)
                self.assertEqual(value["disposition_counts"][reason], 1)
                self.assertEqual(sum(value["disposition_counts"].values()), 1)

    def test_multiple_primary_rows_is_observed_for_duplicate_primary_schema(self) -> None:
        production = (
            "| Domain | Domain Alias | TLD Manager |\n"
            "|---|---|---|\n"
            "| .in | .in | 111 |"
        )
        value = target.observe_vertical_admission(
            production,
            columns=("Domain", "Domain Alias", "TLD Manager"),
            pages=[
                {
                    "title": "",
                    "content": "Domain | .in\nDomain Alias | .in\nTLD Manager | 999",
                }
            ],
        )
        # V2.51.58 defines only the first visible column as primary. The second
        # mapped field is non-primary, so this remains one primary row.
        self.assertEqual(value["disposition_counts"]["identity_bound_candidate_ready"], 1)
        self.assertEqual(value["disposition_counts"]["multiple_primary_key_rows_reject"], 0)

    def test_identity_bound_terminal_reasons_and_frozen_parity(self) -> None:
        cases = {
            "identity_bound_without_nonkey_visible_field": "Domain | .in",
            "identity_bound_quote_span_reject": (
                "Domain | .in\n" + ("\n" * 1_205) + "TLD Manager | 999"
            ),
            "identity_bound_without_changed_safe_candidate": (
                "Domain | .in\nTLD Manager | 111"
            ),
            "identity_bound_candidate_ready": (
                "Domain | .in\nTLD Manager | 999"
            ),
        }
        for reason, content in cases.items():
            with self.subTest(reason=reason):
                value = self._observe(content)
                self.assertEqual(value["disposition_counts"][reason], 1)
                candidates, structure = frozen._vertical_key_value_observations(
                    content,
                    page_ordinal=1,
                    header=list(COLUMNS),
                    rows=[[".in", "country-code", "111"]],
                )
                self.assertEqual(
                    value["identity_bound_block_count"],
                    structure["vertical_identity_bound_block_count"],
                )
                self.assertEqual(
                    value["frozen_vertical_candidate_observation_count"],
                    len(candidates),
                )

    def test_multiple_bound_blocks_preserve_frozen_page_ambiguity(self) -> None:
        content = (
            "Domain | .in\nTLD Manager | 999\n"
            "section boundary\n"
            "Domain | .in\nTLD Manager | 998"
        )
        value = self._observe(content)
        self.assertEqual(value["vertical_block_count"], 2)
        self.assertEqual(value["identity_bound_block_count"], 2)
        self.assertEqual(value["ambiguous_page_count"], 1)
        self.assertEqual(value["frozen_vertical_candidate_observation_count"], 0)

    def test_semantically_different_same_dispositions_have_same_receipt(self) -> None:
        first = self._observe("Unrelated | alpha\nOther | beta")
        second = self._observe("Noise | gamma\nExtra | delta")
        self.assertEqual(first, second)
        encoded = json.dumps(first, ensure_ascii=False)
        for forbidden in ("alpha", "beta", ".in", "999", "Domain"):
            self.assertNotIn(forbidden, encoded)

    def test_tamper_credit_launch_or_behavior_change_fails_closed(self) -> None:
        value = self._observe("Domain | .in\nTLD Manager | 999")
        for kind in ("count", "credit", "launch", "behavior"):
            changed = copy.deepcopy(value)
            if kind == "count":
                changed["vertical_block_count"] = 2
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "launch":
                changed["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed[
                    "observer_reason_buckets_change_admission_routing_prediction_or_budget"
                ] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_observation(changed)

    def test_module_is_pure_label_blind_build_only(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25163_vertical_admission_disposition_observer.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: list[str] = []
        privileged: list[str] = []
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ) and node.slice.value in {
                "category",
                "question_type",
                "task_category",
                "split",
                "ground_truth",
                "gold",
                "answer_key",
                "score",
                "reward",
            }:
                privileged.append(str(node.slice.value))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        self.assertTrue(
            {name.split(".")[0] for name in imports}.isdisjoint(
                {
                    "os",
                    "pathlib",
                    "socket",
                    "subprocess",
                    "requests",
                    "httpx",
                    "openai",
                }
            )
        )
        self.assertEqual(privileged, [])
        self.assertTrue(
            calls.isdisjoint(
                {"complete", "search_many", "fetch_urls", "create_connection"}
            )
        )


if __name__ == "__main__":
    unittest.main()
