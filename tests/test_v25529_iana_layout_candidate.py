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

from deepwide_agent import v25529_iana_layout_candidate as target  # noqa: E402


COLUMNS = ("Domain", "Type", "TLD Manager")
SNAPSHOT = Path(
    "results/v25528_independent_iana_shape_snapshot_v1_20260814.json"
)
EXPECTED = {
    ".aaa": ("Generic", "American Automobile Association, Inc."),
    ".abbott": ("Generic", "Abbott Laboratories, Inc."),
    ".abudhabi": ("Generic", "Abu Dhabi Systems and Information Centre"),
    ".academy": ("Generic", "Binky Moon, LLC"),
    ".aero": (
        "Sponsored",
        "Societe Internationale de Telecommunications Aeronautique (SITA INC USA)",
    ),
    ".africa": ("Generic", "ZA Central Registry NPC trading as Registry.Africa"),
    ".amazon": ("Generic", "Amazon Registry Services, Inc."),
    ".americanfamily": ("Generic", "AmFam, Inc."),
}


def base(identity: str, *, kind: str = "legacy", manager: str = "Old Registry") -> str:
    return (
        "```markdown\n"
        "| Domain | Type | TLD Manager |\n"
        "| --- | --- | --- |\n"
        f"| {identity} | {kind} | {manager} |\n"
        "| .synthetic-control | unchanged | Control Registry |\n"
        "```"
    )


def page(identity: str, content: str) -> dict[str, str]:
    return {
        "url": (
            "https://www.iana.org/domains/root/db/"
            + identity.removeprefix(".")
            + ".html"
        ),
        "title": f"{identity} Domain Delegation Data",
        "content": content,
    }


def layout(
    identity: str,
    *,
    kind: str = "Generic",
    manager: str = "Example Registry, Inc.",
) -> str:
    return (
        f"{identity} Domain Delegation Data\n\n"
        f"Delegation Record for {identity.upper()}\n\n"
        f"({kind} top-level domain)\n\n"
        "Sponsoring Organisation\n\n"
        f"{manager}\n\n"
        "Administrative Contact\n\nPerson"
    )


class V25529IanaLayoutCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = json.loads((ROOT / SNAPSHOT).read_text(encoding="utf-8"))
        cls.snapshot_pages = {
            row["identity"]: {
                "url": row["requested_url"],
                "title": row["title"],
                "content": row["content"],
            }
            for row in raw["pages"]
        }

    def test_all_eight_independent_public_pages_replay_two_coordinates(self) -> None:
        for identity, expected in EXPECTED.items():
            with self.subTest(identity=identity):
                value = target.build_candidate(
                    base(identity),
                    columns=COLUMNS,
                    pages=[self.snapshot_pages[identity]],
                )
                self.assertTrue(value["candidate_prediction_changed"])
                self.assertIn(
                    f"| {identity} | {expected[0]} | {expected[1]} |",
                    value["candidate_prediction"],
                )
                self.assertIn(
                    "| .synthetic-control | unchanged | Control Registry |",
                    value["candidate_prediction"],
                )
                receipt = value["content_free_receipt"]
                self.assertEqual(receipt["iana_delegation_heading_surface_count"], 1)
                self.assertEqual(receipt["iana_parenthetical_type_surface_count"], 1)
                self.assertEqual(
                    receipt["iana_sponsoring_organisation_surface_count"], 1
                )
                self.assertEqual(receipt["iana_layout_complete_page_count"], 1)
                self.assertEqual(receipt["evidence_closed_observation_count"], 2)
                self.assertEqual(receipt["applied_coordinate_count"], 2)

    def test_synthetic_layout_changes_only_url_bound_row(self) -> None:
        identity = ".synthetic-long"
        value = target.build_candidate(
            base(identity),
            columns=COLUMNS,
            pages=[page(identity, layout(identity))],
        )
        self.assertEqual(target.validate_candidate(value), value)
        self.assertIn(
            "| .synthetic-long | Generic | Example Registry, Inc. |",
            value["candidate_prediction"],
        )
        self.assertEqual(
            {row["source_kind"] for row in value["private_observations"]},
            {
                "iana_delegation_parenthetical_type",
                "iana_sponsoring_organisation_bounded_value",
            },
        )

    def test_wrong_url_heading_order_or_missing_boundary_fail_closed(self) -> None:
        identity = ".synthetic-long"
        fixtures = {
            "wrong_url": page(
                identity,
                layout(identity),
            )
            | {
                "url": "https://www.iana.org/domains/root/db/other.html",
            },
            "wrong_heading": page(
                identity, layout(identity).replace(identity.upper(), ".OTHER")
            ),
            "reversed": page(
                identity,
                layout(identity).replace(
                    "(Generic top-level domain)\n\nSponsoring Organisation",
                    "Sponsoring Organisation\n\nExample Registry, Inc.\n\n(Generic top-level domain)\n\nIgnored",
                ),
            ),
            "no_boundary": page(
                identity,
                layout(identity).replace("Administrative Contact", "Other Section"),
            ),
        }
        for name, raw in fixtures.items():
            with self.subTest(name=name):
                value = target.build_candidate(
                    base(identity), columns=COLUMNS, pages=[raw]
                )
                self.assertFalse(value["candidate_prediction_changed"])
                self.assertEqual(value["candidate_prediction"], base(identity))

    def test_duplicate_or_conflicting_layout_coordinates_fail_closed(self) -> None:
        identity = ".synthetic-long"
        fixtures = {
            "duplicate_type": layout(identity).replace(
                "(Generic top-level domain)",
                "(Generic top-level domain)\n\n(Generic top-level domain)",
            ),
            "conflicting_type": layout(identity).replace(
                "(Generic top-level domain)",
                "(Generic top-level domain)\n\n(Sponsored top-level domain)",
            ),
            "duplicate_manager": layout(identity).replace(
                "Sponsoring Organisation\n\nExample Registry, Inc.",
                "Sponsoring Organisation\n\nExample Registry, Inc.\n\n"
                "Sponsoring Organisation\n\nExample Registry, Inc.",
            ),
            "missing_manager": layout(identity).replace(
                "Sponsoring Organisation\n\nExample Registry, Inc.\n\n",
                "Sponsoring Organisation\n\n",
            ),
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                value = target.build_candidate(
                    base(identity),
                    columns=COLUMNS,
                    pages=[page(identity, content)],
                )
                self.assertFalse(value["candidate_prediction_changed"])
                self.assertEqual(
                    value["content_free_receipt"]["available_candidate_count"], 0
                )

    def test_unchanged_and_unsafe_values_preserve_parent(self) -> None:
        identity = ".synthetic-long"
        unchanged = target.build_candidate(
            base(identity, kind="Generic", manager="Example Registry, Inc."),
            columns=COLUMNS,
            pages=[page(identity, layout(identity))],
        )
        self.assertFalse(unchanged["candidate_prediction_changed"])
        self.assertEqual(
            unchanged["content_free_receipt"]["unchanged_coordinate_count"], 2
        )
        unsafe = target.build_candidate(
            base(identity),
            columns=COLUMNS,
            pages=[page(identity, layout(identity, manager="Unknown"))],
        )
        self.assertFalse(unsafe["candidate_prediction_changed"])
        self.assertGreaterEqual(
            unsafe["content_free_receipt"]["unsafe_value_rejected_surface_count"],
            1,
        )

    def test_resealed_observation_receipt_or_credit_tamper_fails(self) -> None:
        identity = ".synthetic-long"
        value = target.build_candidate(
            base(identity),
            columns=COLUMNS,
            pages=[page(identity, layout(identity))],
        )
        for kind in ("observation", "receipt", "credit"):
            changed = copy.deepcopy(value)
            if kind == "observation":
                changed["private_observations"][0]["exact_value"] += "x"
            elif kind == "receipt":
                changed["content_free_receipt"][
                    "iana_layout_complete_page_count"
                ] = 0
            else:
                changed["content_free_receipt"]["positive_signed_credit_count"] = 1
            changed["content_free_receipt"].pop("receipt_payload_sha256", None)
            changed["content_free_receipt"][
                "receipt_payload_sha256"
            ] = target.payload_sha256(changed["content_free_receipt"])
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_candidate(changed)

    def test_module_is_pure_label_blind_and_zero_effect(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(contract["additional_provider_effects"], 0)
        self.assertEqual(
            contract["source_specific_column_mapping"],
            {
                "parenthetical_delegation_type": "Type",
                "Sponsoring Organisation": "TLD Manager",
            },
        )
        source_text = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
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
