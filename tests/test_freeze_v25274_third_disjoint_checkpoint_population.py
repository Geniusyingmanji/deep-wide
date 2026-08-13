from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import freeze_v25274_third_disjoint_checkpoint_population as target  # noqa: E402


class V25274ThirdDisjointCheckpointPopulationSelectorTests(unittest.TestCase):
    def test_design_and_prior_population_barriers_are_exact(self) -> None:
        self.assertTrue(target._design_barrier())
        self.assertEqual(len(target._prior_entities()), 384)

    def test_rank_and_task_vector_are_deterministic_and_balanced(self) -> None:
        selected = {
            "short_alpha": [f"shrt{chr(97 + index)}" for index in range(20)],
            "long_alpha": [f"longpackage{chr(97 + index)}" for index in range(4)],
            "single_hyphen_alpha": [
                f"single-{chr(97 + index)}" for index in range(16)
            ],
        }
        tasks = target._task_vector(selected)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(target.validate_task_vector(tasks), tasks)
        entities = [
            package
            for task in tasks
            for package in target._packages_from_question(task["question"])
        ]
        self.assertEqual(len(entities), 40)
        self.assertEqual(len(set(entities)), 40)
        self.assertEqual(
            target._rank(
                selected["short_alpha"][0],
                stratum="short_alpha",
                snapshot_sha256="a" * 64,
            ),
            target._rank(
                selected["short_alpha"][0],
                stratum="short_alpha",
                snapshot_sha256="a" * 64,
            ),
        )

    def test_selector_excludes_prior_entities_and_never_cross_fills(self) -> None:
        packages = sorted(
            [f"shrt{chr(97 + index)}" for index in range(35)]
            + [f"longpackage{chr(97 + index)}" for index in range(5)]
            + [f"single-{chr(97 + index)}" for index in range(19)]
            + ["digit1"]
        )
        prior = {"shrtz", *[f"old{index}" for index in range(383)]}
        history = {package: 0 for package in packages}
        receipt = {
            "worker_cap": 16,
            "per_candidate_timeout_seconds": 30,
            "whole_selection_wall_ceiling_seconds": 240,
            "submitted_count": len(packages),
            "completed_count": len(packages),
            "coordinator_cancelled_count": 0,
            "subprocess_timeout_count": 0,
            "subprocess_nonzero_returncode_count": 0,
            "subprocess_stderr_nonempty_count": 0,
            "subprocess_incomplete_or_exception_count": 0,
            "all_admitted_candidates_checked_exactly_once": True,
            "all_history_probes_succeeded_within_wall_ceiling": True,
        }
        with mock.patch.object(target.first, "_scan_history", return_value=(history, receipt)):
            selected, observed = target._select(
                packages,
                snapshot_sha256="b" * 64,
                parent_commit="c" * 40,
                prior_entities=prior,
            )
        self.assertEqual(
            {name: len(values) for name, values in selected.items()},
            target.PACKAGES_BY_STRATUM,
        )
        self.assertEqual(observed["probe"]["submitted_count"], len(packages))
        self.assertFalse(set().union(*map(set, selected.values())).intersection(prior))
        self.assertNotIn("digit_bearing", selected)

    def test_insufficient_one_stratum_fails_whole_selection(self) -> None:
        packages = sorted(
            [f"shrt{chr(97 + index)}" for index in range(20)]
            + ["longpackagea", "longpackageb", "longpackagec"]
            + [f"single-{chr(97 + index)}" for index in range(16)]
        )
        history = {package: 0 for package in packages}
        receipt = {"all_history_probes_succeeded_within_wall_ceiling": True}
        with mock.patch.object(target.first, "_scan_history", return_value=(history, receipt)):
            with self.assertRaises(RuntimeError):
                target._select(
                    packages,
                    snapshot_sha256="d" * 64,
                    parent_commit="e" * 40,
                    prior_entities={f"old{index}" for index in range(384)},
                )

    def test_attempt_claim_is_create_exclusive_authority_and_tamper_safe(self) -> None:
        value = target.build_attempt_claim(
            parent_commit="a" * 40,
            execution_start_sha256="b" * 64,
            now=1,
        )
        self.assertEqual(target.validate_attempt_claim(value), value)
        for kind in ("retry", "parent", "result"):
            changed = copy.deepcopy(value)
            if kind == "retry":
                changed["retry_resume_replacement_selective_backfill_or_second_freeze"] = True
            elif kind == "parent":
                changed["selection_parent_commit"] = "c" * 39
            else:
                changed["result_path"] = "other.json"
            changed.pop("claim_payload_sha256")
            changed["claim_payload_sha256"] = target.contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_attempt_claim(changed)

    def test_task_vector_resealed_hidden_or_duplicate_tamper_fails(self) -> None:
        selected = {
            "short_alpha": [f"shrt{chr(97 + index)}" for index in range(20)],
            "long_alpha": [f"longpackage{chr(97 + index)}" for index in range(4)],
            "single_hyphen_alpha": [
                f"single-{chr(97 + index)}" for index in range(16)
            ],
        }
        tasks = target._task_vector(selected)
        hidden = copy.deepcopy(tasks)
        hidden[0]["stratum"] = "short_alpha"
        with self.assertRaises(ValueError):
            target.validate_task_vector(hidden)
        duplicate = copy.deepcopy(tasks)
        duplicate[1] = copy.deepcopy(duplicate[0])
        with self.assertRaises(ValueError):
            target.validate_task_vector(duplicate)

    def test_publication_is_create_exclusive(self) -> None:
        value = target.build_attempt_claim(
            parent_commit="a" * 40,
            execution_start_sha256="b" * 64,
            now=1,
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "claim.json"
            target.publish_exclusive(path, value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, value)


if __name__ == "__main__":
    unittest.main()
