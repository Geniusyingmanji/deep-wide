from __future__ import annotations

import hashlib
import copy
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import run_observed_subprocess  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import (  # noqa: E402
    build_shared_prefix_receipt,
)
from deepwide_agent.v24324_shared_prefix_runner import (  # noqa: E402
    build_pair_envelope,
    build_prefix_bundle,
    validate_branch_effect_receipt,
    validate_branch_envelope,
    validate_no_external_transport_receipt,
    validate_pair_envelope,
    validate_prefix_bundle,
)


FIXTURE = ROOT / "tests/fixtures/v24324_shared_prefix_child.py"
MODES = {
    "baseline_success": ("success", "baseline", "success"),
    "candidate_success": ("success", "candidate", "success"),
    "candidate_unreliable": ("unreliable_candidate", "candidate", "success"),
    "wrong_prefix": ("wrong_prefix", "candidate", "result_envelope_invalid"),
    "duplicate_upstream": (
        "duplicate_upstream",
        "candidate",
        "result_envelope_invalid",
    ),
    "nonzero": ("nonzero", "candidate", "child_nonzero_with_terminal_receipt"),
    "timeout": ("timeout", "candidate", "hard_deadline_timeout"),
    "missing_result": (
        "missing_result",
        "candidate",
        "zero_exit_missing_result_envelope",
    ),
}


def environment() -> dict[str, str]:
    return {
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prefix_bundle() -> dict:
    prefix = build_shared_prefix_receipt(
        visible_plan_sha256="1" * 64,
        planned_query_vector_sha256="2" * 64,
        first_wave_search_receipt_sha256="3" * 64,
        core_evidence_vector_sha256="4" * 64,
        plan_model_effects=1,
        first_wave_search_effects=1,
        first_wave_fetch_effects=6,
        core_usable_pages=5,
    )
    return build_prefix_bundle(prefix)


def run_matrix() -> dict[str, dict]:
    output: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
        root = Path(temporary)
        bundle = prefix_bundle()
        prefix = root / "shared_prefix_bundle.json"
        write(prefix, bundle)
        prefix.chmod(0o444)
        prefix_file_sha = sha256(prefix)
        for name, (mode, arm, expected) in MODES.items():
            directory = root / name
            directory.mkdir()
            result = directory / "result.json"
            effect = directory / "branch_effect_receipt.json"
            transport = directory / "transport_receipt.json"
            terminal = directory / "child_terminal_receipt.json"

            def validate_result(value, *, directory=directory):
                return validate_branch_envelope(
                    value,
                    prefix_bundle=bundle,
                    effect_receipt=json.loads(
                        (directory / "branch_effect_receipt.json").read_text()
                    ),
                    transport_receipt=json.loads(
                        (directory / "transport_receipt.json").read_text()
                    ),
                )

            observed = run_observed_subprocess(
                cwd=ROOT,
                output_root=root,
                directory=directory,
                command=[
                    str(ROOT / ".venv-eval/bin/python"),
                    "-I",
                    "-B",
                    str(FIXTURE),
                    "--mode",
                    mode,
                    "--arm",
                    arm,
                    "--prefix",
                    str(prefix),
                    "--result",
                    str(result),
                    "--effect",
                    str(effect),
                    "--transport",
                    str(transport),
                    "--terminal",
                    str(terminal),
                    "--output-root",
                    str(root),
                ],
                environment=environment(),
                timeout_seconds=0.35 if mode == "timeout" else 4.0,
                result_validator=validate_result,
                model_receipt_validator=validate_branch_effect_receipt,
                transport_receipt_validator=validate_no_external_transport_receipt,
                result_name=result.name,
                model_receipt_name=effect.name,
                transport_receipt_name=transport.name,
                terminal_name=terminal.name,
                parent_name="parent_exit_receipt.json",
            )
            parent = validate_parent_receipt(observed.receipt)
            row = {"expected": expected, "parent": parent}
            if expected == "success":
                row["branch"] = json.loads(result.read_text())
                row["effect"] = json.loads(effect.read_text())
                row["transport"] = json.loads(transport.read_text())
            output[name] = row
        if sha256(prefix) != prefix_file_sha:
            raise RuntimeError("V2.43.24 shared prefix file mutated")
        pair = build_pair_envelope(
            prefix_bundle=bundle,
            baseline_branch=output["baseline_success"]["branch"],
            baseline_effect_receipt=output["baseline_success"]["effect"],
            baseline_transport_receipt=output["baseline_success"]["transport"],
            candidate_branch=output["candidate_success"]["branch"],
            candidate_effect_receipt=output["candidate_success"]["effect"],
            candidate_transport_receipt=output["candidate_success"]["transport"],
            synthesis_prompt_template_sha256="5" * 64,
            model_configuration_sha256="6" * 64,
        )
        validate_pair_envelope(pair)
        output["pair"] = pair
        output["prefix_bundle"] = bundle
        output["prefix_file_sha256"] = prefix_file_sha
    return output


class V24324SharedPrefixSubprocessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = run_matrix()

    def test_all_parent_taxonomies_are_exact(self) -> None:
        self.assertEqual(
            {
                name: self.rows[name]["parent"]["failure_taxonomy"]
                for name in MODES
            },
            {name: expected for name, (_, _, expected) in MODES.items()},
        )

    def test_pair_uses_one_unchanged_prefix_without_upstream_replay(self) -> None:
        pair = self.rows["pair"]
        self.assertEqual(pair["prefix_producer_execution_count"], 1)
        self.assertTrue(pair["shared_prefix_file_unchanged_across_both_branches"])
        self.assertEqual(pair["total_repeated_upstream_effects"], 0)
        self.assertTrue(
            pair["v24323_pair_contract"][
                "shared_plan_query_first_wave_and_core_evidence_exact"
            ]
        )

    def test_unreliable_million_character_candidate_stays_core_only(self) -> None:
        branch = self.rows["candidate_unreliable"]["branch"]
        self.assertEqual(branch["context_action"], "core_only")
        self.assertEqual(
            branch["admission_receipt"]["disposition"],
            "quarantine_low_reliability",
        )
        self.assertEqual(
            branch["admission_receipt"]["anonymous_evidence"]["evidence_chars"],
            1_000_000,
        )

    def test_pair_builder_rejects_cross_artifact_receipt_drift(self) -> None:
        with self.assertRaises(ValueError):
            build_pair_envelope(
                prefix_bundle=self.rows["prefix_bundle"],
                baseline_branch=self.rows["baseline_success"]["branch"],
                baseline_effect_receipt=self.rows["baseline_success"]["effect"],
                baseline_transport_receipt=self.rows["baseline_success"]["transport"],
                candidate_branch=self.rows["candidate_success"]["branch"],
                candidate_effect_receipt=copy.deepcopy(
                    self.rows["baseline_success"]["effect"]
                ),
                candidate_transport_receipt=self.rows["candidate_success"][
                    "transport"
                ],
                synthesis_prompt_template_sha256="5" * 64,
                model_configuration_sha256="6" * 64,
            )
    def test_public_matrix_is_content_free_and_external_effect_free(self) -> None:
        serialized = json.dumps(self.rows, ensure_ascii=False)
        for forbidden in ("deep2wide_result_", '"question":', '"prediction":'):
            self.assertNotIn(forbidden, serialized)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", serialized))
        self.assertEqual(
            self.rows["pair"]["external_effect_ledger"],
            {
                "remote_network": 0,
                "model_provider": 0,
                "hosted_search": 0,
                "fetch": 0,
                "evaluator": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
