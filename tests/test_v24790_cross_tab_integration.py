from __future__ import annotations

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

from deepwide_agent import v24790_cross_tab_integration as target  # noqa: E402
from test_v24778_staged_fetch_fallback_runtime import ENTITIES, LIMITS, Model, Search, TASK, lead, two_round_values  # noqa: E402


def run(contents: dict[str, str], *, values=None, model=None):
    model = model or Model()
    search = Search(values or two_round_values(), contents)
    result = target.run_v24790_task(TASK, model=model, search=search, limits=LIMITS, monotonic=time.monotonic)
    return result, model, search


class V24790CrossTabIntegrationTests(unittest.TestCase):
    def test_validated_receipt_preserves_predictions_and_effects(self) -> None:
        values = two_round_values()
        contents = {item["url"]: (f"{ENTITIES[0]} was founded in 1999." if item["title"].startswith(ENTITIES[0]) else item["title"] + ".") for item in values}
        with patch.object(target.selected, "build_selected_target_cross_tab", wraps=target.selected.build_selected_target_cross_tab) as build:
            result, model, search = run(contents, values=values)
        self.assertEqual(result["status"], "validated")
        self.assertEqual(build.call_count, 1)
        self.assertEqual(result["selected_cross_tab_receipt"]["cross_tab_receipt"]["strict_joint_safe_change_group_count"], 1)
        self.assertEqual(model.requests, 2)
        self.assertEqual(search.calls, 1)
        self.assertLessEqual(search.fetch_calls, 10)
        self.assertTrue(result["predictions_equal_validated_base_result"])

    def test_public_projection_excludes_private_literals(self) -> None:
        values = two_round_values()
        contents = {item["url"]: f"{item['title']}. {ENTITIES[0]} was founded in 1987." for item in values}
        result, _model, _search = run(contents, values=values)
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("private_semantic_catalog", encoded)
        self.assertNotIn("raw_content", encoded)
        self.assertNotIn("1987", json.dumps(result["selected_cross_tab_receipt"]))

    def test_base_failure_does_not_call_observer(self) -> None:
        with (
            patch.object(target.base, "run_v24778_task", side_effect=RuntimeError("boom")),
            patch.object(target.selected, "build_selected_target_cross_tab") as build,
        ):
            result = target.run_v24790_task(TASK, model=Model(), search=Search([], {}), limits=LIMITS, monotonic=time.monotonic)
        self.assertEqual(result["status"], "base_runtime_failure")
        self.assertEqual(result["predictions"], {})
        build.assert_not_called()

    def test_observer_failure_preserves_base_predictions(self) -> None:
        values = two_round_values()
        contents = {item["url"]: item["title"] for item in values}
        with patch.object(target.selected, "build_selected_target_cross_tab", side_effect=ValueError("synthetic")):
            result, _model, _search = run(contents, values=values)
        self.assertEqual(result["status"], "selected_catalog_or_observer_failure")
        self.assertTrue(result["base_result_valid"])
        self.assertEqual(set(result["predictions"]), set(target.base.ARMS))
        self.assertIsNone(result["selected_cross_tab_receipt"])

    def test_no_unknown_status_is_explicit(self) -> None:
        complete = (
            "```markdown\n| Organization | Founded | Country |\n| --- | --- | --- |\n"
            + "\n".join(f"| {entity} | 1999 | Canada |" for entity in ENTITIES)
            + "\n```"
        )

        class CompleteModel(Model):
            def complete(self, system, user, *, max_output_tokens, json_mode=False):
                value = super().complete(system, user, max_output_tokens=max_output_tokens, json_mode=json_mode)
                if not json_mode:
                    return type(value)(complete, {}, None, 1)
                return value

        values = [lead(entity, f"source{index}.example") for index, entity in enumerate(ENTITIES)]
        result, _model, _search = run({item["url"]: item["title"] for item in values}, values=values, model=CompleteModel())
        self.assertEqual(result["status"], "no_baseline_unknown_target")
        self.assertFalse(result["baseline_unknown_target_present"])
        self.assertIsNone(result["selected_cross_tab_receipt"])

    def test_resealed_private_or_authority_tamper_fails(self) -> None:
        values = two_round_values()
        contents = {item["url"]: item["title"] for item in values}
        result, _model, _search = run(contents, values=values)
        for mutate in (
            lambda value: value.__setitem__("catalog_or_private_content_serialized_to_public_projection", True),
            lambda value: value.__setitem__("additional_model_search_fetch_or_evaluator_effect", 1),
            lambda value: value.__setitem__("benchmark_launch_or_evaluator_authorized", True),
        ):
            altered = copy.deepcopy(result)
            mutate(altered)
            altered.pop("result_sha256")
            altered["result_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(ValueError):
                target.validate_projection(altered)


if __name__ == "__main__":
    unittest.main()
