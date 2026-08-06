from __future__ import annotations

import concurrent.futures
import copy
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

from deepwide_agent import v24318_deadline_conservation_runtime as parent  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24677_expanded_visible_schema_runtime import (  # noqa: E402
    _isolated_conservation_task,
    _transition,
    run_v24677_conservation_task,
    run_v24677_exact220_task,
    validate_receipt,
)


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += float(seconds)


class Model:
    def __init__(self) -> None:
        self.values = [
            json.dumps(
                {
                    "columns": ["wrong", "schema"],
                    "queries": ["one", "two", "three", "four"],
                }
            ),
            "| Name | Date |\n| --- | --- |\n| A | 2026 |",
        ]
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 1
        self.output_tokens += 1
        self.total_tokens += 2
        return SimpleNamespace(text=self.values.pop(0))


class Search(DeadlineAwareNativeSearchClient):
    def __init__(self, clock: Clock) -> None:
        super().__init__(
            "http://unused.invalid/responses",
            "synthetic",
            timeout=120,
            max_retries=1,
            fetch_pages=False,
            max_workers=1,
            fetch_workers=1,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=300,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        self.index = 0

    def search_many(self, queries, **_kwargs):
        self._increment("calls")
        self._increment("tool_calls")
        rows = []
        for query in queries:
            self.index += 1
            rows.append(
                {
                    "query": query,
                    "answer": "",
                    "results": [
                        {
                            "url": f"https://synthetic-{self.index}.invalid/page",
                            "title": "synthetic",
                            "content": "",
                        }
                    ],
                }
            )
        return rows

    def fetch_urls(self, requests_):
        values = list(requests_)
        self._increment("fetch_calls", len(values))
        return [
            {
                "query": item["query"],
                "results": [
                    {
                        "url": item["url"],
                        "title": "synthetic",
                        "raw_content": "public synthetic page " + "x" * 1000,
                    }
                ],
            }
            for item in values
        ]


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


def run(question: str):
    clock = Clock()
    return run_v24677_conservation_task(
        {"opaque_id": "task_0123456789abcdef01234567", "question": question},
        arm="baseline",
        model=Model(),
        search=Search(clock),
        limits=limits(),
        two_wave_policy=TwoWavePolicy(),
        monotonic=clock,
    )


class V24677ExpandedVisibleSchemaRuntimeTests(unittest.TestCase):
    def test_incremental_schema_executes_in_task_local_namespace(self) -> None:
        outcome = run(
            "Please output one Markdown table with the columns, in this exact order:\n"
            "Name | Date\nDo not omit cells."
        )
        receipt = validate_receipt(outcome.schema_transition_receipt)
        self.assertEqual(receipt["status"], "incremental_explicit_schema")
        self.assertEqual(outcome.result["visible_schema"]["status"], "applied")
        self.assertEqual(outcome.result["visible_schema"]["column_count"], 2)

    def test_frozen_nonempty_path_is_byte_equivalent(self) -> None:
        question = "Return one table. The column names are: Name, Date."
        clock = Clock()
        expected = parent.run_v24318_task(
            {"opaque_id": "task_0123456789abcdef01234567", "question": question},
            arm="baseline",
            model=Model(),
            search=Search(clock),
            limits=limits(),
            two_wave_policy=TwoWavePolicy(),
            monotonic=clock,
        )
        observed = run(question)
        self.assertEqual(observed.result, expected)
        self.assertEqual(
            observed.schema_transition_receipt["status"], "frozen_schema_preserved"
        )

    def test_absent_schema_preserves_frozen_abstention(self) -> None:
        outcome = run("Return a useful table without an explicit field declaration.")
        self.assertEqual(
            outcome.schema_transition_receipt["status"],
            "no_unambiguous_explicit_schema",
        )
        self.assertEqual(
            outcome.result["visible_schema"]["status"],
            "no_unambiguous_visible_schema",
        )

    def test_isolated_function_does_not_mutate_parent_globals(self) -> None:
        original = parent.extract_robust_visible_columns
        isolated = _isolated_conservation_task()
        isolated_parent = isolated.__globals__["_run_parent"]
        self.assertIsNot(isolated, parent.run_v24318_task)
        self.assertIsNot(isolated_parent, parent._run_parent)
        self.assertIsNot(
            isolated_parent.__globals__["extract_robust_visible_columns"], original
        )
        self.assertIs(parent.extract_robust_visible_columns, original)

    def test_eight_way_mixed_concurrency_preserves_parent_identity(self) -> None:
        original = parent.extract_robust_visible_columns
        questions = [
            "Please output one Markdown table with the columns, in this exact order:\n"
            "Name | Date\nDo not omit cells."
            if index % 2
            else "Return one table. The column names are: Name, Date."
            for index in range(8)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(run, questions))
        self.assertEqual(
            sum(item.schema_transition_receipt["incremental_schema_applied"] for item in values),
            4,
        )
        self.assertTrue(
            all(item.result["visible_schema"]["status"] == "applied" for item in values)
        )
        self.assertIs(parent.extract_robust_visible_columns, original)

    def test_receipt_reseal_cannot_claim_global_mutation(self) -> None:
        _old, _new, receipt = _transition(
            "Please output one Markdown table with the columns, in this exact order:\n"
            "Name | Date\nDo not omit cells."
        )
        changed = copy.deepcopy(receipt)
        changed["module_global_parser_mutated"] = True
        changed.pop("receipt_sha256")
        from deepwide_agent.v24263_global_model_limiter import payload_sha256

        changed["receipt_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            validate_receipt(changed)

    def test_exact220_integration_rejects_nonbaseline_before_effect(self) -> None:
        model = Model()
        clock = Clock()
        search = Search(clock)
        with self.assertRaisesRegex(ValueError, "frozen baseline arm"):
            run_v24677_exact220_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": "The column names are: Name, Date.",
                },
                arm="candidate",
                model=model,  # rejected before the concrete client type is inspected
                search=search,
                limits=limits(),
                two_wave_policy=TwoWavePolicy(),
                monotonic=clock,
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24677_expanded_visible_schema_runtime.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
