from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25309_pipe_visible_schema_worldbank_gate as adapter  # noqa: E402
from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25309_worldbank_monotone_fill_external as runner  # noqa: E402
from test_v24319_runner_integration import Clock  # noqa: E402


class SyntheticModel:
    def __init__(self, values: list[object]) -> None:
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.deadline_failures = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value, output_truncated=False)


def _make_slots(root: Path) -> Path:
    slots = root / "slots"
    slots.mkdir()
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
    return slots


def _table(columns: list[str], rows: list[list[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


class V25309WorldBankMonotoneFillExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.population = contract.frozen_population(ROOT)

    def _fixture(self, task_index: int = 0, *, fill: bool = True):
        visible = self.population["tasks"][task_index]
        columns = ["Entity code", *self.population["target_columns"]]
        codes = [
            value.strip()
            for value in visible["question"]
            .split("Include exactly these entity-code rows in this order: ", 1)[1]
            .split(". Use Unknown", 1)[0]
            .split(",")
        ]
        values: dict[tuple[str, str], str] = {}
        for page in self.population["pages"]:
            lines = page["content"].splitlines()
            column = lines[0].strip("|").split("|")[1].strip()
            for line in lines[2:]:
                cells = [item.strip() for item in line.strip("|").split("|")]
                values[(cells[0], column)] = cells[1]
        rows = [
            [code, *(values[(code, column)] for column in columns[1:])]
            for code in codes
        ]
        if fill:
            rows[0][1] = "Unknown"
        baseline = _table(columns, rows)
        proposal_rows = copy.deepcopy(rows)
        if fill:
            proposal_rows[0][1] = values[(codes[0], columns[1])]
        plan = json.dumps(
            {"queries": ["q1", "q2", "q3", "q4"], "columns": columns}
        )
        model_values: list[object] = [plan, baseline]
        if fill:
            model_values.append(_table(columns, proposal_rows))
        return visible, columns, model_values

    def _run(self, task_index: int = 0, *, fill: bool = True):
        visible, _columns, values = self._fixture(task_index, fill=fill)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock(100.0)
        inner = SyntheticModel(values)
        model = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=_make_slots(output),
            output_root=output,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=340.0,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        search = adapter.FrozenWorldBankSnapshotSearchClient(
            self.population["pages"], absolute_deadline=340.0, monotonic=clock
        )
        result = adapter.run_paired_task(
            visible,
            model=model,
            search=search,
            limits=ScoreFirstLimits(**contract.LIMITS),
            two_wave_policy=TwoWavePolicy(**contract.TWO_WAVE_POLICY),
            monotonic=clock,
        )
        row = runner._from_runtime(visible, result, 1.0)
        return inner, result, row

    def test_frozen_population_and_contract_are_exact(self) -> None:
        population = contract.frozen_population(ROOT)
        self.assertEqual(len(population["tasks"]), 12)
        self.assertEqual(len(population["pages"]), 8)
        self.assertEqual(contract.payload_sha256(population["tasks"]), contract.TASK_VECTOR_SHA256)
        self.assertEqual(contract.payload_sha256(population["pages"]), contract.RENDERED_PAGES_SHA256)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.PHYSICAL_CAPS, {
            "queries_per_task": 4,
            "fetches_per_task": 10,
            "model_forwards_per_task": 3,
            "wall_seconds_per_task": 240,
        })

    def test_pipe_parser_preserves_long_top_level_comma_columns(self) -> None:
        question = self.population["tasks"][0]["question"]
        self.assertEqual(
            adapter.extract_pipe_delimited_visible_columns(question),
            ["Entity code", *self.population["target_columns"]],
        )
        self.assertGreater(max(map(len, self.population["target_columns"])), 80)
        self.assertEqual(
            adapter.extract_pipe_delimited_visible_columns(
                question.replace(" | ", ", ", 1)
            ),
            [],
        )
        adapter.validate_isolation()

    def test_real_parent_chain_admits_one_supported_third_slot_fill(self) -> None:
        inner, result, row = self._run(fill=True)
        receipt = result["content_free_paired_receipt"]
        integration = row["content_free_integration_receipt"]
        self.assertEqual(result["parent_envelope"]["result"]["columns"], [
            "Entity code", *self.population["target_columns"]
        ])
        self.assertEqual(result["parent_envelope"]["result"]["completion_kind"], "primary")
        self.assertEqual(receipt["parent_logical_model_calls"], 2)
        self.assertEqual(receipt["final_logical_model_calls"], 3)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertEqual(receipt["physical_fetch_count"], 8)
        self.assertEqual(receipt["supported_unknown_fill_count"], 1)
        self.assertTrue(receipt["candidate_prediction_changed"])
        self.assertTrue(integration["complete_same_forward_page_prefix"])
        self.assertTrue(integration["revision_prompt_within_parent_cap"])
        self.assertEqual(inner.requests, 3)
        self.assertTrue(row["runtime_completed"])

    def test_no_unknown_preserves_parent_without_third_slot(self) -> None:
        inner, result, row = self._run(fill=False)
        receipt = result["content_free_paired_receipt"]
        self.assertEqual(receipt["candidate_disposition"], "identity_no_baseline_unknown")
        self.assertEqual(receipt["final_logical_model_calls"], 2)
        self.assertFalse(receipt["candidate_prediction_changed"])
        self.assertEqual(row["parent_prediction"], row["candidate_prediction"])
        self.assertEqual(inner.requests, 2)

    def test_privileged_runtime_field_fails_before_model_effect(self) -> None:
        visible, _columns, values = self._fixture(fill=True)
        visible = {**visible, "category": "forbidden"}
        inner = SyntheticModel(values)
        with self.assertRaises(ValueError):
            adapter.run_paired_task(
                visible,
                model=inner,
                search=object(),
                limits=ScoreFirstLimits(**contract.LIMITS),
                two_wave_policy=TwoWavePolicy(**contract.TWO_WAVE_POLICY),
                monotonic=Clock(100.0),
            )
        self.assertEqual(inner.requests, 0)

    def test_task_row_tamper_and_failure_as_zero_validate(self) -> None:
        _inner, _result, row = self._run(fill=True)
        changed = copy.deepcopy(row)
        changed["candidate_prediction_sha256"] = "0" * 64
        changed.pop("task_payload_sha256")
        changed["task_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            runner.validate_task_row(changed)
        failure = runner._terminal_outer_failure(
            self.population["tasks"][0], RuntimeError("private"), 1.0, None
        )
        self.assertTrue(failure["failure_as_zero"])
        self.assertIsNone(failure["paired_runtime_result"])

    def test_aggregate_and_mechanism_gate_pass_for_twelve_supported_rows(self) -> None:
        rows = [self._run(index, fill=True)[2] for index in range(12)]
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["terminal_tasks"], 12)
        self.assertEqual(aggregate["supported_unknown_fill_tasks"], 12)
        self.assertEqual(aggregate["supported_unknown_fill_cells"], 12)
        self.assertEqual(aggregate["attributable_prediction_change_tasks"], 12)
        self.assertEqual(aggregate["query_effect_equal_tasks"], 12)
        self.assertEqual(aggregate["fetch_effect_equal_tasks"], 12)
        self.assertEqual(aggregate["maximum_model_forwards_on_one_task"], 3)
        self.assertTrue(decision["mechanism_gate_passed"])

    def test_mechanism_gate_is_no_go_below_two_supported_tasks(self) -> None:
        rows = [self._run(index, fill=index == 0)[2] for index in range(12)]
        decision = runner.mechanism_decision(
            runner.aggregate_rows(rows, wall_seconds=2.0)
        )
        self.assertFalse(decision["mechanism_gate_passed"])
        self.assertIn("minimum_supported_unknown_fill_tasks", decision["failed_checks"])
        self.assertIn("minimum_attributable_prediction_change_tasks", decision["failed_checks"])
        self.assertFalse(decision["postfreeze_evaluator_after_pushed_forward_audit"])

    def test_attempt_claim_is_sealed_and_effect_authority_is_single_use(self) -> None:
        protocol = contract.build_protocol(
            source_manifest={str(contract.CONTRACT): contract.sha256(ROOT / contract.CONTRACT)},
            now=1,
        )
        with mock.patch.object(contract, "validate_protocol", return_value=protocol), mock.patch.object(
            contract, "sha256", return_value="a" * 64
        ):
            start = contract.seal(
                {
                    "role": "v25310_worldbank_monotone_fill_execution_start",
                    "protocol_id": contract.PROTOCOL_ID,
                },
                "execution_start_payload_sha256",
            )
            claim = runner.build_attempt_claim(protocol, start, now=2)
        self.assertTrue(
            claim["attempt_authority_consumed_before_endpoint_model_or_output_effect"]
        )
        self.assertFalse(
            claim["retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt"]
        )
        runner.validate_attempt_claim(claim)

    def test_source_is_label_blind_and_runner_uses_native_limiter(self) -> None:
        adapter_source = (ROOT / contract.CONTRACT.parent / "v25309_pipe_visible_schema_worldbank_gate.py").read_text(encoding="utf-8")
        runner_source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        tree = ast.parse(adapter_source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
        for forbidden in ("os", "pathlib", "requests", "subprocess", "urllib.request"):
            self.assertNotIn(forbidden, imports)
        for forbidden in (
            "benchmark_question_type", "ground_truth", "answer_key", "results.csv"
        ):
            self.assertNotIn(forbidden, adapter_source)
        run_tree = ast.parse(runner_source)
        limiter_calls = [
            node for node in ast.walk(run_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "DeadlineAwareGlobalModelSlotLimiter"
        ]
        self.assertEqual(len(limiter_calls), 1)
        self.assertNotIn("HardCappedModelLimiter", runner_source)


if __name__ == "__main__":
    unittest.main()
