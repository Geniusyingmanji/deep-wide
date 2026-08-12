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

from scripts import freeze_v25256_disjoint_observed_reliability_population as target  # noqa: E402


def suffix(index: int, width: int = 5) -> str:
    chars = []
    value = index
    for _ in range(width):
        chars.append(string.ascii_lowercase[value % 26])
        value //= 26
    return "".join(reversed(chars))


def candidates(count: int = 90) -> list[str]:
    output = []
    for index in range(count):
        token = suffix(index)
        output.extend(("s" + token, "long" + token, "source-" + token, "source" + str(index) + "x"))
    return sorted(output)


def successful_probe(package: str, *, parent_commit: str) -> dict[str, object]:
    del package, parent_commit
    return {"hits": 0, "completed": True, "timed_out": False, "returncode_zero": True, "stderr_empty": True}


def source_counts(packages: list[str]) -> dict[str, int]:
    return {
        "installed_binary_unique_count": 1000,
        "source_name_disjoint_from_all_installed_binary_names_count": len(packages),
        "malformed_line_count": 0,
        "noninstalled_or_invalid_binary_line_count": 0,
        **{name: sum(target.old._stratum(package) == name for package in packages) for name in target.STRATA},
        "excluded_other": sum(target.old._stratum(package) is None for package in packages),
    }


class V25256DisjointObservedReliabilityPopulationFreezeTests(unittest.TestCase):
    def test_design_and_old_population_authority_are_exact(self) -> None:
        self.assertTrue(target._design_barrier())
        self.assertEqual(len(target._old_entities()), 256)

    def test_rank_uses_v25255_salt_and_is_stratum_bound(self) -> None:
        snapshot = "a" * 64
        value = target._rank("saaaaa", stratum="short_alpha", snapshot_sha256=snapshot)
        self.assertEqual(value, target._rank("saaaaa", stratum="short_alpha", snapshot_sha256=snapshot))
        self.assertNotEqual(value, target.hashlib.sha256(f"v25239\0{snapshot}\0short_alpha\0saaaaa".encode()).hexdigest())
        with self.assertRaises(ValueError):
            target._rank("saaaaa", stratum="digit_bearing", snapshot_sha256=snapshot)

    def test_selection_excludes_old_entities_and_uses_exact_balanced_counts(self) -> None:
        packages = candidates()
        old_entities = {f"old{index}" for index in range(256)}
        snapshot = target.old._snapshot_sha256(packages)
        with mock.patch.object(target.old, "_history_probe", side_effect=successful_probe):
            selected, history = target._select(
                packages,
                snapshot_sha256=snapshot,
                parent_commit="f" * 40,
                old_entities=old_entities,
            )
        flat = [package for values in selected.values() for package in values]
        self.assertEqual(len(flat), 128)
        self.assertFalse(set(flat).intersection(old_entities))
        self.assertEqual({name: len(values) for name, values in selected.items()}, target.PACKAGES_BY_STRATUM)
        self.assertEqual(history["probe"]["submitted_count"], len(packages))

    def test_visible_task_vector_is_64_by_2_globally_unique_and_label_blind(self) -> None:
        packages = candidates()
        old_entities = set()
        while len(old_entities) < 256:
            old_entities.add(f"old{len(old_entities)}")
        snapshot = target.old._snapshot_sha256(packages)
        with mock.patch.object(target.old, "_history_probe", side_effect=successful_probe):
            selected, _history = target._select(
                packages,
                snapshot_sha256=snapshot,
                parent_commit="f" * 40,
                old_entities=old_entities,
            )
        tasks = target._task_vector(selected)
        entities = [package for task in tasks for package in target._packages_from_question(task["question"])]
        self.assertEqual(len(tasks), 64)
        self.assertEqual(len(entities), len(set(entities)), 128)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(all("stratum" not in task["question"] for task in tasks))

    def test_mocked_freeze_is_reconstructable_and_design_only(self) -> None:
        packages = candidates()
        old_entities = {f"old{index}" for index in range(256)}
        with mock.patch.object(target, "_design_barrier", return_value=True), mock.patch.object(
            target.old, "_resolve_parent", return_value="f" * 40
        ), mock.patch.object(
            target.old, "_read_source_packages", return_value=(packages, source_counts(packages))
        ), mock.patch.object(target, "_old_entities", return_value=old_entities), mock.patch.object(
            target.old, "_history_probe", side_effect=successful_probe
        ):
            value = target.build_freeze(
                parent_commit="f" * 40,
                attempt_claim_sha256="a" * 64,
                execution_start_sha256="b" * 64,
                now=1,
            )
        self.assertEqual(target.validate_freeze(value), value)
        self.assertEqual(value["population"]["task_count"], 64)
        self.assertEqual(value["population"]["package_count"], 128)
        self.assertEqual(value["old_population_exclusion_receipt"]["selected_entity_overlap_count"], 0)
        self.assertTrue(value["authorization"]["observed_reliability_protocol_design"])
        self.assertFalse(value["authorization"]["external_activation_or_launch"])

    def test_attempt_claim_is_sealed_and_precedes_effect_authority(self) -> None:
        value = target.build_attempt_claim(
            parent_commit="f" * 40,
            execution_start_sha256="a" * 64,
            now=1,
        )
        self.assertEqual(target.validate_attempt_claim(value), value)
        self.assertTrue(value["attempt_authority_consumed_before_dpkg_or_history_effect"])
        changed = copy.deepcopy(value)
        changed["retry_resume_replacement_selective_backfill_or_second_freeze"] = True
        changed.pop("claim_payload_sha256")
        changed["claim_payload_sha256"] = target.base.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_attempt_claim(changed)

    def test_resealed_overlap_history_launch_credit_or_hidden_tamper_fails(self) -> None:
        packages = candidates()
        old_entities = {f"old{index}" for index in range(256)}
        with mock.patch.object(target, "_design_barrier", return_value=True), mock.patch.object(
            target.old, "_resolve_parent", return_value="f" * 40
        ), mock.patch.object(
            target.old, "_read_source_packages", return_value=(packages, source_counts(packages))
        ), mock.patch.object(target, "_old_entities", return_value=old_entities), mock.patch.object(
            target.old, "_history_probe", side_effect=successful_probe
        ):
            value = target.build_freeze(
                parent_commit="f" * 40,
                attempt_claim_sha256="a" * 64,
                execution_start_sha256="b" * 64,
                now=1,
            )
        for kind in ("overlap", "history", "launch", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "overlap":
                changed["old_population_exclusion_receipt"]["selected_entity_overlap_count"] = 1
            elif kind == "history":
                changed["history_receipt"]["probe"]["completed_count"] -= 1
            elif kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["population"]["hidden_stratum"] = "short_alpha"
            changed.pop("freeze_payload_sha256")
            changed["freeze_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_freeze(changed)

    def test_source_has_no_privileged_runtime_field_or_network_model_import(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        privileged = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in {
                "category", "question_type", "task_category", "split",
                "ground_truth", "gold", "answer_key", "score", "reward",
            }
        }
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertEqual(privileged, set())
        self.assertFalse(imports.intersection({"requests", "openai"}))

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.json"
            target.publish_exclusive(path, {"safe": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"safe": True})
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, {"safe": True})


if __name__ == "__main__":
    unittest.main()
