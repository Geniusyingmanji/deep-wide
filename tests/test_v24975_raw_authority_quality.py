from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24974_raw_authority_compact_fields as compact  # noqa: E402
from deepwide_agent import v24975_raw_authority_quality_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24975_raw_authority_quality as control  # noqa: E402
from scripts import finalize_v24975_raw_authority_quality as finalizer  # noqa: E402
from scripts import run_v24973_identity_bound_field_quality as parent_runner  # noqa: E402
from scripts import run_v24975_raw_authority_quality as runner  # noqa: E402


class V24975RawAuthorityQualityTests(unittest.TestCase):
    def test_population_is_fresh_fixed_and_never_layout_probed(self) -> None:
        projects = {project for project, _repo in contract.TASKS}
        self.assertEqual(len(contract.TASKS), 20)
        self.assertEqual(len(set(contract.TASKS)), 20)
        self.assertFalse(projects & contract.PRIOR_PROJECTS)
        self.assertFalse(projects & contract.LAYOUT_PROBE_EXCLUSIONS)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in contract.task_vector()))
        self.assertTrue(
            all(task["opaque_id"].startswith("task_") for task in contract.task_vector())
        )

    def test_protocol_is_independent_and_freezes_raw_page_treatment(self) -> None:
        value = contract.validate_protocol_untracked(
            ROOT, contract.build_protocol_untracked(ROOT, now=1)
        )
        self.assertEqual(value["protocol_id"], contract.PROTOCOL_ID)
        self.assertNotEqual(
            contract.PROTOCOL,
            Path("results/v24973_identity_bound_field_preregistration_v1_20260809.json"),
        )
        self.assertTrue(value["source_policy"]["control_is_fixed_prefix_of_noisy_raw_authority_bytes"])
        self.assertTrue(value["source_policy"]["candidate_compact_record_derived_from_complete_shared_bytes"])
        self.assertFalse(value["authorization"]["public_exact220_or_sota"])

    def test_schema_compatibility_never_reuses_parent_predictions(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(policy["v24973_artifact_role_strings_reused_as_schema_only"])
        self.assertFalse(policy["v24973_predictions_results_or_task_vector_reused"])
        self.assertNotEqual(
            contract.OUTPUT_ROOT,
            Path("outputs/v24973_identity_bound_field_quality_v1_20260809"),
        )

    def test_runner_rebinds_raw_compactor_and_independent_contract(self) -> None:
        runner.configure()
        self.assertIs(parent_runner.contract, contract)
        self.assertIs(parent_runner.compact, compact)
        self.assertIs(parent_runner._fetch_exact, runner._fetch_exact)

    def test_raw_evidence_keeps_noisy_prefix_and_fixed_budget(self) -> None:
        pages = [{"text": "{\"noise\":\"" + "p" * 20_000}, {"text": "<html>" + "g" * 20_000}]
        value = runner._raw_balanced_evidence(pages)
        self.assertEqual(len(value), contract.EVIDENCE_CHARS)
        self.assertIn("noise", value[: contract.NAMESPACE_EVIDENCE_CHARS])
        self.assertIn("<html>", value[contract.NAMESPACE_EVIDENCE_CHARS :])

    def test_streaming_fetch_rejects_oversized_before_unbounded_join(self) -> None:
        class Response:
            status_code = 200
            url = "https://pypi.org/pypi/demo/json"
            encoding = "utf-8"
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def raise_for_status(self): return None
            def iter_content(self, chunk_size):
                del chunk_size
                yield b"x" * (contract.MAX_RESPONSE_BYTES // 2 + 1)
                yield b"x" * (contract.MAX_RESPONSE_BYTES // 2 + 1)
        with mock.patch.object(runner.requests, "get", return_value=Response()):
            with self.assertRaises(ValueError):
                runner._fetch_exact(
                    "https://pypi.org/pypi/demo/json",
                    kind="pypi_json",
                    repository="owner/repo",
                    deadline=10**12,
                )

    def test_streaming_fetch_preserves_complete_raw_json(self) -> None:
        payload = json.dumps({"noise": "x" * 10_000, "info": {"name": "demo"}}).encode()
        class Response:
            status_code = 200
            url = "https://pypi.org/pypi/demo/json"
            encoding = "utf-8"
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def raise_for_status(self): return None
            def iter_content(self, chunk_size):
                del chunk_size
                yield payload[:5000]
                yield payload[5000:]
        with mock.patch.object(runner.requests, "get", return_value=Response()):
            page, status = runner._fetch_exact(
                "https://pypi.org/pypi/demo/json",
                kind="pypi_json",
                repository="owner/repo",
                deadline=10**12,
            )
        self.assertEqual(status, 200)
        self.assertEqual(page["text"], payload.decode())

    def test_control_audit_includes_parent_runtime_and_new_seam(self) -> None:
        control.configure()
        self.assertIn(contract.PARENT_RUNTIME, control.base.FORWARD_SOURCES)
        self.assertIn(contract.EXTRACTOR, control.base.FORWARD_SOURCES)
        self.assertEqual(control.base.EXPECTED_TESTS, 46)

    def test_finalizer_rebinds_independent_contract_and_runner(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertIs(finalizer.base.runner, runner)

    def test_forward_sources_are_label_blind_and_evaluator_free(self) -> None:
        for relative in (
            contract.SOURCE, contract.EXTRACTOR, contract.RUNTIME,
            contract.PARENT_CONTRACT, contract.PARENT_RUNTIME, contract.FIELD_EXTRACTOR,
        ):
            path = ROOT / relative
            self.assertEqual(semantic_audit._accesses(path, ROOT), [])
            self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])
        imports = []
        for node in ast.walk(ast.parse((ROOT / contract.RUNTIME).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("deepwidebench" in name or "finalize" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
