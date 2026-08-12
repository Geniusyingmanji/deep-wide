from __future__ import annotations

import ast
import copy
import json
import string
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import freeze_v25235_local_package_shadow_population as target  # noqa: E402


def suffix(index: int, width: int = 5) -> str:
    alphabet = string.ascii_lowercase
    chars = []
    value = index
    for _ in range(width):
        chars.append(alphabet[value % len(alphabet)])
        value //= len(alphabet)
    return "".join(reversed(chars))


def candidates(count: int = 70) -> list[str]:
    output = []
    for index in range(count):
        token = suffix(index)
        output.extend(
            (
                "c" + token,
                "single-" + token,
                "multi-part-" + token,
                "digit" + str(index) + "x",
            )
        )
    return sorted(output)


class V25235LocalPackagePopulationFreezeTests(unittest.TestCase):
    def test_morphologies_are_mutually_exclusive_and_boundary_exact(self) -> None:
        cases = {
            "abcdef": "compact_alpha",
            "single-alpha": "single_hyphen_alpha",
            "multi-part-alpha": "multi_hyphen_alpha",
            "alpha9": "digit_bearing",
            "a-b+c": None,
            "alpha.beta": None,
            "abcd": None,
            "a" * 37: None,
        }
        for package, expected in cases.items():
            with self.subTest(package=package):
                self.assertEqual(target._morphology(package), expected)

    def test_dpkg_parser_keeps_only_installed_unique_valid_names(self) -> None:
        text = "\n".join(
            (
                "ii \tabcdef",
                "ii \tabcdef",
                "rc \tremoved",
                "ii \tsingle-alpha",
                "ii \tbad:name",
                "malformed",
            )
        )
        packages, counts = target._parse_dpkg(text)
        self.assertEqual(packages, ["abcdef", "single-alpha"])
        self.assertEqual(counts["installed_unique_accepted_name_count"], 2)
        self.assertEqual(counts["malformed_line_count"], 1)
        self.assertEqual(counts["noninstalled_or_invalid_name_line_count"], 2)

    def test_rank_is_deterministic_and_morphology_bound(self) -> None:
        snapshot = "a" * 64
        first = target._rank(
            "abcdef", morphology="compact_alpha", snapshot_sha256=snapshot
        )
        second = target._rank(
            "abcdef", morphology="compact_alpha", snapshot_sha256=snapshot
        )
        self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            target._rank(
                "abcdef",
                morphology="digit_bearing",
                snapshot_sha256=snapshot,
            )

    def test_selection_skips_predeclared_history_hits_without_manual_choice(self) -> None:
        packages = candidates()
        snapshot = target._snapshot_sha256(packages)

        def hits(package: str, *, parent_commit: str) -> int:
            del parent_commit
            return int(package.endswith("aaaaa") or package.endswith("aaaab"))

        with mock.patch.object(target, "_history_hits", side_effect=hits):
            selected, history = target._select(
                packages,
                snapshot_sha256=snapshot,
                parent_commit="f" * 40,
            )
        self.assertEqual(set(selected), set(target.MORPHOLOGIES))
        self.assertTrue(
            all(len(values) == target.PACKAGES_PER_MORPHOLOGY for values in selected.values())
        )
        self.assertTrue(
            all(row["history_zero_selected_count"] == 64 for row in history.values())
        )

    def test_insufficient_history_zero_capacity_fails_whole_population(self) -> None:
        packages = candidates(64)
        snapshot = target._snapshot_sha256(packages)
        with mock.patch.object(target, "_history_hits", return_value=1), self.assertRaisesRegex(
            RuntimeError, "insufficient"
        ):
            target._select(
                packages,
                snapshot_sha256=snapshot,
                parent_commit="f" * 40,
            )

    def test_task_vector_is_visible_only_interleaved_and_roundtrips(self) -> None:
        from deepwide_agent import v25110_exact_visible_schema as visible_schema

        packages = candidates(64)
        selected = {
            morphology: [
                package
                for package in packages
                if target._morphology(package) == morphology
            ]
            for morphology in target.MORPHOLOGIES
        }
        tasks = target._task_vector(selected)
        self.assertEqual(len(tasks), 64)
        self.assertEqual(target.validate_task_vector(tasks), tasks)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(all("morphology" not in task["question"] for task in tasks))
        self.assertTrue(all("Columns exactly:" in task["question"] for task in tasks))
        self.assertTrue(
            all(
                visible_schema.extract_exact_visible_columns(task["question"])
                == list(target.REQUIRED_COLUMNS)
                for task in tasks
            )
        )

    def test_mocked_freeze_is_reconstructable_and_authorizes_design_only(self) -> None:
        packages = candidates()
        source_counts = {
            "installed_unique_accepted_name_count": len(packages),
            "malformed_line_count": 0,
            "noninstalled_or_invalid_name_line_count": 0,
            **{
                morphology: sum(
                    target._morphology(package) == morphology for package in packages
                )
                for morphology in target.MORPHOLOGIES
            },
            "excluded_other": 0,
        }
        with mock.patch.object(target, "_design_barrier", return_value=True), mock.patch.object(
            target, "_resolve_parent", return_value="f" * 40
        ), mock.patch.object(
            target, "_read_installed_packages", return_value=(packages, source_counts)
        ), mock.patch.object(target, "_history_hits", return_value=0):
            value = target.build_freeze(parent_commit="HEAD", now=1)
        self.assertEqual(target.validate_freeze(value), value)
        self.assertEqual(value["population"]["task_count"], 64)
        self.assertEqual(value["population"]["package_count"], 256)
        self.assertTrue(value["authorization"]["shadow_reliability_protocol_design"])
        self.assertFalse(value["authorization"]["shadow_external_activation_or_launch"])
        self.assertFalse(value["population"]["morphology_field_passed_to_runtime"])

    def test_resealed_task_history_launch_or_credit_tamper_fails(self) -> None:
        packages = candidates()
        source_counts = {
            "installed_unique_accepted_name_count": len(packages),
            "malformed_line_count": 0,
            "noninstalled_or_invalid_name_line_count": 0,
            **{
                morphology: sum(
                    target._morphology(package) == morphology for package in packages
                )
                for morphology in target.MORPHOLOGIES
            },
            "excluded_other": 0,
        }
        with mock.patch.object(target, "_design_barrier", return_value=True), mock.patch.object(
            target, "_resolve_parent", return_value="f" * 40
        ), mock.patch.object(
            target, "_read_installed_packages", return_value=(packages, source_counts)
        ), mock.patch.object(target, "_history_hits", return_value=0):
            value = target.build_freeze(parent_commit="HEAD", now=1)
        for kind in ("task", "history", "launch", "credit", "nested"):
            changed = copy.deepcopy(value)
            if kind == "task":
                changed["population"]["task_vector"][0]["question"] += " drift"
            elif kind == "history":
                changed["history_receipt"]["history_zero_selected_total"] = 255
            elif kind == "launch":
                changed["authorization"]["shadow_external_activation_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["source_receipt"]["hidden_identity"] = "leak"
            changed.pop("freeze_payload_sha256")
            changed["freeze_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_freeze(changed)

    def test_source_uses_fixed_argument_vectors_without_shell_or_privileged_fields(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        privileged = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value
            in {
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
        }
        shell_true = any(
            isinstance(node, ast.keyword)
            and node.arg == "shell"
            and isinstance(node.value, ast.Constant)
            and node.value.value is True
            for node in ast.walk(tree)
        )
        self.assertEqual(privileged, set())
        self.assertFalse(shell_true)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "freeze.json"
            value = {"safe": True}
            target.publish_exclusive(path, value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, value)


if __name__ == "__main__":
    unittest.main()
