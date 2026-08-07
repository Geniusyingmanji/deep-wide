from __future__ import annotations

import ast
import copy
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24784_projection_funnel_integration as target  # noqa: E402
from test_v24778_staged_fetch_fallback_runtime import (  # noqa: E402
    ENTITIES,
    LIMITS,
    Model,
    Search,
    TASK,
    lead,
    two_round_values,
)


def run(contents: dict[str, str], *, values=None):
    model = Model()
    search = Search(values or two_round_values(), contents)
    result = target.run_v24784_task(
        TASK,
        model=model,
        search=search,
        limits=LIMITS,
        monotonic=time.monotonic,
    )
    return result, model, search


class V24784ProjectionFunnelIntegrationTests(unittest.TestCase):
    def test_validated_two_source_projection_preserves_predictions_and_effects(self) -> None:
        values = two_round_values()
        contents = {
            item["url"]: (
                f"{ENTITIES[0]} was founded in 1999."
                if item["title"].startswith(ENTITIES[0])
                else item["title"] + ". Generic profile text."
            )
            for item in values
        }
        with (
            patch.object(target.base, "validate_result", wraps=target.base.validate_result) as validate_base,
            patch.object(
                target.funnel,
                "build_projection_conversion_funnel",
                wraps=target.funnel.build_projection_conversion_funnel,
            ) as build_funnel,
            patch.object(
                target.funnel,
                "validate_receipt",
                wraps=target.funnel.validate_receipt,
            ) as validate_funnel,
        ):
            result, model, search = run(contents, values=values)
        self.assertEqual(target.validate_projection(result), result)
        self.assertEqual(result["status"], "validated")
        self.assertEqual(validate_base.call_count, 1)
        self.assertEqual(build_funnel.call_count, 1)
        # One validation is the builder's terminal validation; the second is
        # the outer projection's counts-only schema replay.  The catalog is
        # observed only by the single builder call.
        self.assertEqual(validate_funnel.call_count, 2)
        self.assertTrue(result["private_catalog_observed_by_funnel_at_most_once"])
        self.assertTrue(
            result[
                "counts_only_funnel_receipt_revalidation_may_repeat_without_private_access"
            ]
        )
        receipt = result["projection_funnel_receipt"]
        self.assertGreaterEqual(receipt["projection_emitted_pair_count"], 1)
        self.assertGreaterEqual(
            receipt["projection_backed_eligible_support_set_count"], 1
        )
        self.assertGreaterEqual(
            receipt["unconflicted_projection_backed_unknown_proposal_count"], 1
        )
        self.assertEqual(
            result["predictions"]["staged_fallback_semantic"],
            target.base.run_v24778_task(
                TASK,
                model=Model(),
                search=Search(values, contents),
                limits=LIMITS,
                monotonic=time.monotonic,
            )["predictions"]["staged_fallback_semantic"],
        )
        self.assertEqual(model.requests, 2)
        self.assertEqual(search.calls, 1)
        self.assertLessEqual(search.fetch_calls, 10)

    def test_public_projection_contains_counts_but_no_private_literals(self) -> None:
        values = two_round_values()
        contents = {
            item["url"]: f"{item['title']}. {ENTITIES[0]} was founded in 1999."
            for item in values
        }
        result, _model, _search = run(contents, values=values)
        encoded = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("private_semantic_catalog", encoded)
        self.assertNotIn("private_scheduler_state", encoded)
        self.assertNotIn("private_visible_task", encoded)
        self.assertNotIn("raw_content", encoded)
        self.assertNotIn("1999", json.dumps(result["projection_funnel_receipt"]))
        self.assertFalse(
            result["catalog_or_private_content_serialized_to_public_projection"]
        )

    def test_private_catalog_absence_is_explicit_not_fabricated_zero_receipt(self) -> None:
        invalid_baseline = (
            "```markdown\n| Organization | Founded | Country |\n"
            "| --- | --- | --- |\n"
            "| Wrong Entity | Unknown | Unknown |\n```"
        )

        class BadModel(Model):
            def complete(self, system, user, *, max_output_tokens, json_mode=False):
                value = super().complete(
                    system, user, max_output_tokens=max_output_tokens, json_mode=json_mode
                )
                if not json_mode:
                    return type(value)(invalid_baseline, {}, None, 1)
                return value

        values = [lead(entity, f"source{index}.example") for index, entity in enumerate(ENTITIES)]
        contents = {item["url"]: item["title"] for item in values}
        result = target.run_v24784_task(
            TASK,
            model=BadModel(),
            search=Search(values, contents),
            limits=LIMITS,
            monotonic=time.monotonic,
        )
        self.assertEqual(result["status"], "private_catalog_absent")
        self.assertFalse(result["private_catalog_present"])
        self.assertIsNone(result["projection_funnel_receipt"])
        self.assertFalse(result["funnel_receipt_valid"])

    def test_base_failure_is_terminal_and_does_not_call_funnel(self) -> None:
        with (
            patch.object(target.base, "run_v24778_task", side_effect=RuntimeError("boom")),
            patch.object(target.funnel, "build_projection_conversion_funnel") as build,
        ):
            result = target.run_v24784_task(
                TASK,
                model=Model(),
                search=Search([], {}),
                limits=LIMITS,
                monotonic=time.monotonic,
            )
        self.assertEqual(result["status"], "base_runtime_failure")
        self.assertFalse(result["base_result_valid"])
        self.assertEqual(result["predictions"], {})
        self.assertIsNone(result["projection_funnel_receipt"])
        build.assert_not_called()

    def test_funnel_failure_is_explicit_and_preserves_validated_base_predictions(self) -> None:
        values = two_round_values()
        contents = {item["url"]: item["title"] for item in values}
        with patch.object(
            target.funnel,
            "build_projection_conversion_funnel",
            side_effect=ValueError("synthetic funnel failure"),
        ):
            result, _model, _search = run(contents, values=values)
        self.assertEqual(result["status"], "funnel_validation_failure")
        self.assertTrue(result["base_result_valid"])
        self.assertTrue(result["private_catalog_present"])
        self.assertFalse(result["funnel_receipt_valid"])
        self.assertIsNone(result["projection_funnel_receipt"])
        self.assertEqual(set(result["predictions"]), set(target.base.ARMS))

    def test_resealed_private_or_authority_tamper_fails_closed(self) -> None:
        values = two_round_values()
        contents = {item["url"]: item["title"] for item in values}
        result, _model, _search = run(contents, values=values)
        for mutate in (
            lambda value: value.__setitem__(
                "catalog_or_private_content_serialized_to_public_projection", True
            ),
            lambda value: value.__setitem__(
                "additional_model_search_fetch_or_evaluator_effect", 1
            ),
            lambda value: value.__setitem__(
                "benchmark_launch_or_evaluator_authorized", True
            ),
        ):
            altered = copy.deepcopy(result)
            mutate(altered)
            altered.pop("result_sha256")
            altered["result_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(ValueError):
                target.validate_projection(altered)

    def test_runtime_is_label_blind_and_has_no_external_capability(self) -> None:
        tree = ast.parse(Path(target.__file__).read_text(encoding="utf-8"))
        privileged = {
            "answer",
            "answer_key",
            "category",
            "evaluator",
            "gold",
            "ground_truth",
            "mapping",
            "question_type",
            "reward",
            "score",
            "split",
            "task_category",
        }
        forbidden_imports = {"httpx", "os", "pathlib", "requests", "socket", "subprocess"}
        findings = []
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            if isinstance(key, str) and key.casefold() in privileged:
                findings.append((node.lineno, key))
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            findings.extend(
                (node.lineno, name) for name in names if name in forbidden_imports
            )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
