from __future__ import annotations

import copy
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v25469_row_key_source_external as harness  # noqa: E402
from scripts import v25478_clone_safe_runner_namespace as target  # noqa: E402


SOURCE_NAMES = (
    "_read", "_publish_json", "_publish_jsonl", "_clean_pushed",
    "_lease_inactive", "_active_conflicts", "_search", "_empty_effect_snapshot",
    "_effect_snapshot", "_health", "_health_snapshot", "_validate_cost",
    "_prepare_output", "_fallback_prediction", "_task_metadata", "_metadata",
    "_decode_completed", "_terminal_outer_failure", "_from_runtime",
    "validate_task_row", "validate_aggregate", "aggregate_rows",
    "run_one_task", "run_forward",
)


def sources() -> dict[str, types.FunctionType]:
    return {name: getattr(harness, name) for name in SOURCE_NAMES}


class V25478CloneSafeRunnerNamespaceTests(unittest.TestCase):
    def test_visible_wrapper_globals_alone_reproduce_v25476_missing_fcntl(self) -> None:
        self.assertIn(
            "fcntl", target.referenced_global_names(harness._lease_inactive)
        )
        self.assertNotIn("fcntl", harness.__dict__)
        naive = types.FunctionType(
            harness._lease_inactive.__code__,
            dict(harness.__dict__),
            name=harness._lease_inactive.__name__,
            argdefs=harness._lease_inactive.__defaults__,
            closure=harness._lease_inactive.__closure__,
        )
        self.assertNotIn("fcntl", naive.__globals__)

        namespace = target.build_namespace(
            [harness._lease_inactive],
            visible_globals=harness.__dict__,
            overrides={},
        )
        self.assertIn("fcntl", namespace)

    def test_actual_source_function_globals_resolve_all_effect_infrastructure(self) -> None:
        namespace = target.build_namespace(
            list(sources().values()),
            visible_globals=harness.__dict__,
            overrides={},
        )
        receipt = target.content_free_receipt(sources(), namespace)
        self.assertEqual(receipt["unresolved_global_name_count"], 0)
        for name in (
            "fcntl_resolved", "socket_resolved", "subprocess_resolved",
            "thread_pool_executor_resolved", "as_completed_resolved",
            "lease_helper_resolved",
        ):
            self.assertTrue(receipt[name])

    def test_clone_group_cross_calls_bind_to_one_successor_namespace(self) -> None:
        namespace, clones = target.clone_group(
            sources(),
            visible_globals=harness.__dict__,
            overrides={"SENTINEL": object()},
            rename_from="v25469",
            rename_to="v25479",
        )
        self.assertTrue(all(function.__globals__ is namespace for function in clones.values()))
        self.assertIs(namespace["run_one_task"], clones["run_one_task"])
        self.assertIs(namespace["_lease_inactive"], clones["_lease_inactive"])
        self.assertEqual(
            target.content_free_receipt(clones, namespace)["unresolved_function_count"],
            0,
        )

    def test_missing_nonbuiltin_global_fails_before_clone(self) -> None:
        namespace: dict[str, object] = {}
        exec("def synthetic():\n    return missing_effect_capability\n", namespace)
        with self.assertRaisesRegex(RuntimeError, "missing_effect_capability"):
            target.build_namespace(
                [namespace["synthetic"]], visible_globals={}, overrides={}
            )

    def test_receipt_and_overrides_are_content_free(self) -> None:
        namespace = target.build_namespace(
            [harness._lease_inactive],
            visible_globals=harness._lease_inactive.__globals__,
            overrides={"contract": object()},
        )
        receipt = target.content_free_receipt(
            {"_lease_inactive": harness._lease_inactive}, namespace
        )
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertFalse(receipt["file_environment_process_network_model_search_fetch_or_evaluator_accessed"])
        changed = copy.deepcopy(receipt)
        changed["unresolved_global_name_count"] = 1
        self.assertNotEqual(changed, receipt)


if __name__ == "__main__":
    unittest.main()
