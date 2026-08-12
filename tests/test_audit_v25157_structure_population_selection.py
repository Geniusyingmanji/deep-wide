from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v25157_structure_population_selection as target  # noqa: E402


class V25157StructurePopulationSelectionTests(unittest.TestCase):
    def test_fixed_twenty_identity_vector(self) -> None:
        self.assertEqual(len(target.PACKAGES), 20)
        self.assertEqual(len(set(target.PACKAGES)), 20)
        value = target.build_audit(now=1)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["identity_history_zero_hit_count"], 20)

    def test_every_identity_has_zero_parent_history_introduction(self) -> None:
        parent = subprocess.run(
            ["git", "rev-parse", "--verify", target.PARENT_COMMIT + "^{commit}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=True,
        ).stdout.strip()
        for package in target.PACKAGES:
            completed = subprocess.run(
                [
                    "git",
                    "log",
                    "--format=%H",
                    "-S",
                    package,
                    parent,
                    "--",
                    *target.SCOPES,
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                check=True,
            )
            self.assertEqual(completed.stdout, "")

    def test_artifact_is_aggregate_only_and_resealed_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        encoded = json.dumps(value, ensure_ascii=False)
        for package in target.PACKAGES:
            self.assertNotIn(package, encoded)
        for kind in ("history", "effect", "mapping"):
            changed = copy.deepcopy(value)
            if kind == "history":
                changed["identity_history_total_hit_count"] = 1
            elif kind == "effect":
                changed[
                    "endpoint_page_value_model_search_evaluator_credential_or_benchmark_opened"
                ] = True
            else:
                changed[
                    "mapping_gold_category_question_type_split_score_reward_or_historical_result_read"
                ] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
