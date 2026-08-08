from __future__ import annotations

import ast
import copy
import fcntl
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    payload_sha256,
)
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24318_deadline_conservation_runtime import (  # noqa: E402
    MODEL_FIELD,
    validate_v24318_result,
)
from deepwide_agent.v24319_runner_integration import run_v24319_task  # noqa: E402
from deepwide_agent.v24860_coverage_revision_integration import (  # noqa: E402
    run_coverage_revision,
    validate_integration_receipt,
    validate_result,
)
from test_v24319_runner_integration import (  # noqa: E402
    Clock,
    SyntheticDeadlineSearch,
)


PLAN = json.dumps(
    {
        "columns": ["Name", "Date"],
        "queries": ["one", "two", "three", "four"],
    }
)
BASELINE = "| Name | Date |\n| --- | --- |\n| Alpha | Unknown |"
SUPPORTED = "| Name | Date |\n| --- | --- |\n| Alpha | 2026 |"


class SyntheticModel:
    def __init__(self, values: list[object]) -> None:
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.deadline_failures = 0
        self.max_output_tokens: list[int] = []

    def complete(self, *_args, **kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        self.max_output_tokens.append(int(kwargs["max_output_tokens"]))
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, SimpleNamespace):
            return value
        return SimpleNamespace(text=value, output_truncated=False)


def task() -> dict[str, str]:
    return {
        "opaque_id": "task_0123456789abcdef01234567",
        "question": "Return one table. The column names are: Name, Date.",
    }


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        repair_output_tokens=12_000,
    )


def make_slots(root: Path, count: int = 2) -> Path:
    directory = root / "slots"
    directory.mkdir()
    for index in range(1, count + 1):
        (directory / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return directory


def pages_for(parent: dict) -> list[dict[str, object]]:
    count = int(parent["evidence"]["fetch_target_count"])
    return [
        {
            "evidence_id": f"E{index:04d}",
            "url": f"https://source-{index}.example/record",
            "raw_content": "Alpha record. Date: 2026.",
            "fetch_integrity": True,
        }
        for index in range(1, count + 1)
    ]


class V24860CoverageRevisionIntegrationTests(unittest.TestCase):
    def build_parent(self, values: list[object]):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output = Path(temporary.name)
        clock = Clock(100.0)
        inner = SyntheticModel(values)
        model = build_deadline_model(
            url="http://unused.invalid/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=make_slots(output),
            output_root=output,
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=220.0,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=inner,
        )
        search = SyntheticDeadlineSearch(clock, deadline=220.0)
        parent = run_v24319_task(
            task(),
            arm="baseline",
            model=model,
            search=search,
            limits=limits(),
            two_wave_policy=TwoWavePolicy(),
            monotonic=clock,
        )
        validate_v24318_result(parent.result, "baseline")
        return temporary, clock, inner, model, parent

    def test_supported_revision_spends_exact_third_slot(self) -> None:
        temporary, clock, inner, model, parent = self.build_parent(
            [PLAN, BASELINE, SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(parent.result[MODEL_FIELD]["logical_admissions_total"], 2)
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages_for(parent.result),
            limits=limits(),
            monotonic=clock,
        )
        receipt = validate_integration_receipt(value.integration_receipt)
        validate_result(
            value.result,
            final_model_slot_receipt=value.final_model_slot_receipt,
        )
        self.assertEqual(receipt["disposition"], "admitted_supported_revision")
        self.assertEqual(receipt["logical_final_model_calls"], 3)
        self.assertEqual(receipt["provider_request_delta"], 1)
        self.assertEqual(receipt["model_slot_acquisition_delta"], 1)
        self.assertEqual(value.final_model_slot_receipt["acquisitions"], 3)
        self.assertIn("| Alpha | 2026 |", value.result["prediction"])
        self.assertEqual(
            receipt["coverage_receipt"]["admitted_existing_unknown_fills"], 1
        )
        self.assertEqual(value.result["parent_result"], parent.result)
        self.assertEqual(
            value.result["cost"]["search"], parent.result["cost"]["search"]
        )
        self.assertEqual(inner.max_output_tokens[-1], limits().repair_output_tokens)

    def test_incomplete_prefix_is_identity_without_third_call(self) -> None:
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        incomplete = pages_for(parent.result)[:-1]
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=incomplete,
            limits=limits(),
            monotonic=clock,
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_incomplete_page_prefix")
        self.assertFalse(receipt["logical_revision_call_admitted"])
        self.assertEqual(value.final_model_slot_receipt["acquisitions"], 2)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_unsupported_proposal_spends_slot_but_preserves_parent(self) -> None:
        unsupported = "| Name | Date |\n| --- | --- |\n| Alpha | 2099 |"
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, unsupported]
        )
        self.addCleanup(temporary.cleanup)
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages_for(parent.result),
            limits=limits(),
            monotonic=clock,
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_no_supported_change")
        self.assertTrue(receipt["logical_revision_call_admitted"])
        self.assertEqual(receipt["provider_request_delta"], 1)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_prompt_above_parent_context_cap_skips_third_call(self) -> None:
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        pages = pages_for(parent.result)
        page_chars = sum(len(str(item["raw_content"])) for item in pages)
        too_small = copy.deepcopy(limits())
        too_small = ScoreFirstLimits(
            **{
                **too_small.__dict__,
                "evidence_chars": page_chars,
            }
        )
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages,
            limits=too_small,
            monotonic=clock,
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_context_cap")
        self.assertFalse(receipt["revision_prompt_within_parent_cap"])
        self.assertFalse(receipt["logical_revision_call_admitted"])
        self.assertEqual(value.final_model_slot_receipt["acquisitions"], 2)

    def test_truncated_proposal_spends_slot_but_is_not_gated(self) -> None:
        truncated = SimpleNamespace(text=SUPPORTED, output_truncated=True)
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, truncated]
        )
        self.addCleanup(temporary.cleanup)
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages_for(parent.result),
            limits=limits(),
            monotonic=clock,
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_truncated_proposal")
        self.assertTrue(receipt["proposal_truncated"])
        self.assertFalse(receipt["coverage_gate_invoked"])
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_empty_proposal_has_explicit_identity_state(self) -> None:
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, ""]
        )
        self.addCleanup(temporary.cleanup)
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages_for(parent.result),
            limits=limits(),
            monotonic=clock,
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_empty_proposal")
        self.assertTrue(receipt["logical_revision_call_admitted"])
        self.assertEqual(receipt["provider_request_delta"], 1)
        self.assertFalse(receipt["proposal_returned"])
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_parent_repair_uses_all_three_slots_and_blocks_revision(self) -> None:
        repaired = "| Name | Date |\n| --- | --- |\n| Alpha | Unknown |"
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, "not a table", repaired, SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(parent.result[MODEL_FIELD]["logical_admissions_total"], 3)
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages_for(parent.result),
            limits=limits(),
            monotonic=clock,
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_parent_not_eligible")
        self.assertEqual(receipt["logical_parent_model_calls"], 3)
        self.assertEqual(receipt["logical_final_model_calls"], 3)
        self.assertFalse(receipt["logical_revision_call_admitted"])
        self.assertEqual(value.final_model_slot_receipt["acquisitions"], 3)

    def test_third_slot_timeout_is_conserved_without_provider_request(self) -> None:
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        handles = [
            open(Path(temporary.name) / "slots" / f"slot_{index:02d}.lock", "r+")
            for index in (1, 2)
        ]
        for handle in handles:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        clock.value = 215.0
        try:
            value = run_coverage_revision(
                task(),
                parent_result=parent.result,
                parent_model_slot_receipt=parent.model_slot_receipt,
                model=model,
                pages=pages_for(parent.result),
                limits=limits(),
                monotonic=clock,
            )
        finally:
            for handle in handles:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_model_effect_failed")
        self.assertTrue(receipt["logical_revision_call_admitted"])
        self.assertEqual(receipt["provider_request_delta"], 0)
        self.assertEqual(receipt["model_slot_timeout_delta"], 1)
        self.assertEqual(value.final_model_slot_receipt["acquisitions"], 2)
        self.assertEqual(value.final_model_slot_receipt["slot_timeouts"], 1)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_resealed_result_budget_or_receipt_tamper_fails(self) -> None:
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        value = run_coverage_revision(
            task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages_for(parent.result),
            limits=limits(),
            monotonic=clock,
        )
        altered = copy.deepcopy(value.result)
        altered["coverage_revision_receipt"]["revision_max_output_tokens"] += 1
        altered["coverage_revision_receipt"].pop("receipt_payload_sha256")
        altered["coverage_revision_receipt"]["receipt_payload_sha256"] = payload_sha256(
            altered["coverage_revision_receipt"]
        )
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_result(
                altered,
                final_model_slot_receipt=value.final_model_slot_receipt,
            )

    def test_privileged_input_fails_before_third_effect(self) -> None:
        temporary, clock, _inner, model, parent = self.build_parent(
            [PLAN, BASELINE, SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        before = model.receipt()
        with self.assertRaises(ValueError):
            run_coverage_revision(
                {**task(), "question_type": "forbidden"},
                parent_result=parent.result,
                parent_model_slot_receipt=parent.model_slot_receipt,
                model=model,
                pages=pages_for(parent.result),
                limits=limits(),
                monotonic=clock,
            )
        after = model.receipt()
        self.assertEqual(before["acquisitions"], after["acquisitions"])
        self.assertEqual(before["slot_timeouts"], after["slot_timeouts"])

    def test_runtime_has_no_evaluator_or_historical_result_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24860_coverage_revision_integration.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any("evaluator" in name or "finalize" in name for name in imports)
        )
        public = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "run_coverage_revision"
        )
        arguments = [item.arg for item in public.args.args + public.args.kwonlyargs]
        self.assertEqual(
            arguments,
            [
                "task",
                "parent_result",
                "parent_model_slot_receipt",
                "model",
                "pages",
                "limits",
                "monotonic",
            ],
        )


if __name__ == "__main__":
    unittest.main()
