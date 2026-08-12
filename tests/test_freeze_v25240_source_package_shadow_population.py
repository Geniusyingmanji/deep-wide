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

from scripts import freeze_v25240_source_package_shadow_population as target  # noqa: E402


def suffix(index: int, width: int = 5) -> str:
    chars = []
    value = index
    for _ in range(width):
        chars.append(string.ascii_lowercase[value % 26])
        value //= 26
    return "".join(reversed(chars))


def candidates(count: int = 70) -> list[str]:
    output = []
    for index in range(count):
        token = suffix(index)
        output.extend((
            "s" + token,
            "long" + token,
            "source-" + token,
            "source" + str(index) + "x",
        ))
    return sorted(output)


def source_counts(packages: list[str]) -> dict[str, int]:
    return {
        "installed_binary_unique_count": 1000,
        "source_name_disjoint_from_all_installed_binary_names_count": len(packages),
        "malformed_line_count": 0,
        "noninstalled_or_invalid_binary_line_count": 0,
        **{name: sum(target._stratum(package) == name for package in packages) for name in target.STRATA},
        "excluded_other": sum(target._stratum(package) is None for package in packages),
    }


def successful_probe(package: str, *, parent_commit: str) -> dict:
    del package, parent_commit
    return {
        "hits": 0,
        "completed": True,
        "timed_out": False,
        "returncode_zero": True,
        "stderr_empty": True,
    }


class V25240SourcePackagePopulationFreezeTests(unittest.TestCase):
    def test_strata_are_mutually_exclusive_and_boundary_exact(self) -> None:
        cases = {
            "abcde": "short_alpha",
            "abcdefgh": "short_alpha",
            "abcdefghi": "long_alpha",
            "abcdefghijklmnop": "long_alpha",
            "source-alpha": "single_hyphen_alpha",
            "source9": "digit_bearing",
            "abcd": None,
            "abcdefghijklmnopq": None,
            "multi-part-alpha": None,
            "source.alpha": None,
        }
        for package, expected in cases.items():
            with self.subTest(package=package):
                self.assertEqual(target._stratum(package), expected)

    def test_dpkg_parser_keeps_only_source_names_disjoint_from_binary_names(self) -> None:
        text = "\n".join((
            "ii \tbinaryone\tsourcealpha",
            "ii \tsourcealpha\tsourcealpha",
            "ii \tbinarytwo\tsource-beta",
            "rc \tremoved\tignoredsource",
            "ii \tbad:name\tignoredsource",
            "malformed",
        ))
        packages, counts = target._parse_dpkg(text)
        self.assertEqual(packages, ["source-beta"])
        self.assertEqual(counts["installed_binary_unique_count"], 3)
        self.assertEqual(counts["source_name_disjoint_from_all_installed_binary_names_count"], 1)
        self.assertEqual(counts["malformed_line_count"], 1)
        self.assertEqual(counts["noninstalled_or_invalid_binary_line_count"], 2)

    def test_rank_uses_new_salt_and_is_stratum_bound(self) -> None:
        snapshot = "a" * 64
        value = target._rank("saaaaa", stratum="short_alpha", snapshot_sha256=snapshot)
        self.assertEqual(value, target._rank("saaaaa", stratum="short_alpha", snapshot_sha256=snapshot))
        self.assertNotEqual(
            value,
            target.hashlib.sha256(f"v25234\0{snapshot}\0short_alpha\0saaaaa".encode()).hexdigest(),
        )
        with self.assertRaises(ValueError):
            target._rank("saaaaa", stratum="digit_bearing", snapshot_sha256=snapshot)

    def test_history_scan_checks_every_candidate_once_with_zero_failure_receipt(self) -> None:
        packages = candidates()
        seen: list[str] = []

        def probe(package: str, *, parent_commit: str) -> dict:
            del parent_commit
            seen.append(package)
            return successful_probe(package, parent_commit="f" * 40)

        with mock.patch.object(target, "_history_probe", side_effect=probe):
            hits, receipt = target._scan_history(packages, parent_commit="f" * 40)
        self.assertEqual(sorted(seen), packages)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(hits), set(packages))
        self.assertEqual(receipt["submitted_count"], len(packages))
        self.assertEqual(receipt["completed_count"], len(packages))
        self.assertTrue(receipt["all_admitted_candidates_checked_exactly_once"])
        self.assertTrue(receipt["all_history_probes_succeeded_within_wall_ceiling"])

    def test_any_history_timeout_nonzero_or_stderr_fails_whole_scan(self) -> None:
        packages = candidates(2)
        for kind in ("timeout", "nonzero", "stderr"):
            def probe(package: str, *, parent_commit: str) -> dict:
                del parent_commit
                row = successful_probe(package, parent_commit="f" * 40)
                if package == packages[0]:
                    if kind == "timeout":
                        row.update(completed=False, timed_out=True, returncode_zero=False)
                    elif kind == "nonzero":
                        row["returncode_zero"] = False
                    else:
                        row["stderr_empty"] = False
                return row

            with self.subTest(kind=kind), mock.patch.object(target, "_history_probe", side_effect=probe), self.assertRaisesRegex(RuntimeError, "failed closed"):
                target._scan_history(packages, parent_commit="f" * 40)

    def test_selection_and_visible_task_vector_roundtrip(self) -> None:
        from deepwide_agent import v25110_exact_visible_schema as visible_schema

        packages = candidates()
        snapshot = target._snapshot_sha256(packages)
        with mock.patch.object(target, "_history_probe", side_effect=successful_probe):
            selected, history = target._select(packages, snapshot_sha256=snapshot, parent_commit="f" * 40)
        tasks = target._task_vector(selected)
        self.assertEqual(len(tasks), 64)
        self.assertEqual(target.validate_task_vector(tasks), tasks)
        self.assertEqual(history["probe"]["submitted_count"], len(packages))
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(all("stratum" not in task["question"] for task in tasks))
        self.assertTrue(all(
            visible_schema.extract_exact_visible_columns(task["question"])
            == list(target.REQUIRED_COLUMNS)
            for task in tasks
        ))

    def test_mocked_freeze_is_reconstructable_and_authorizes_design_only(self) -> None:
        packages = candidates()
        with mock.patch.object(target, "_design_barrier", return_value=True), mock.patch.object(
            target, "_resolve_parent", return_value="f" * 40
        ), mock.patch.object(
            target, "_read_source_packages", return_value=(packages, source_counts(packages))
        ), mock.patch.object(target, "_history_probe", side_effect=successful_probe):
            value = target.build_freeze(parent_commit="f" * 40, now=1)
        self.assertEqual(target.validate_freeze(value), value)
        self.assertEqual(value["population"]["task_count"], 64)
        self.assertEqual(value["population"]["package_count"], 256)
        self.assertTrue(value["authorization"]["shadow_reliability_protocol_design"])
        self.assertFalse(value["authorization"]["shadow_external_activation_or_launch"])

    def test_attempt_claim_is_sealed_and_precedes_effectful_build(self) -> None:
        claim = target.build_attempt_claim(parent_commit="f" * 40, now=1)
        self.assertEqual(target.validate_attempt_claim(claim), claim)
        changed = copy.deepcopy(claim)
        changed["retry_resume_replacement_selective_backfill_or_second_freeze"] = True
        changed.pop("claim_payload_sha256")
        changed["claim_payload_sha256"] = target.base.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_attempt_claim(changed)

        events: list[str] = []
        fake = {"population": {"task_count": 64, "package_count": 256}, "authorization": {"shadow_reliability_protocol_design": True, "shadow_external_activation_or_launch": False}}
        with mock.patch.object(target, "publish_exclusive", side_effect=lambda path, value: events.append("claim" if value.get("role") == target.CLAIM_ROLE else "result")), mock.patch.object(
            target, "build_freeze", side_effect=lambda **kwargs: events.append("build") or fake
        ):
            self.assertEqual(target.execute(parent_commit="f" * 40), fake)
        self.assertEqual(events, ["claim", "build", "result"])

    def test_resealed_task_history_launch_credit_or_hidden_tamper_fails(self) -> None:
        packages = candidates()
        with mock.patch.object(target, "_design_barrier", return_value=True), mock.patch.object(
            target, "_resolve_parent", return_value="f" * 40
        ), mock.patch.object(
            target, "_read_source_packages", return_value=(packages, source_counts(packages))
        ), mock.patch.object(target, "_history_probe", side_effect=successful_probe):
            value = target.build_freeze(parent_commit="f" * 40, now=1)
        for kind in ("task", "history", "launch", "credit", "nested"):
            changed = copy.deepcopy(value)
            if kind == "task":
                changed["population"]["task_vector"][0]["question"] += " drift"
            elif kind == "history":
                changed["history_receipt"]["probe"]["completed_count"] -= 1
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

    def test_source_uses_only_subprocess_run_without_privileged_fields(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        process_methods = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ]
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
        self.assertEqual(process_methods, ["run", "run", "run"])
        self.assertEqual(privileged, set())

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.json"
            target.publish_exclusive(path, {"safe": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"safe": True})
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, {"safe": True})


if __name__ == "__main__":
    unittest.main()
