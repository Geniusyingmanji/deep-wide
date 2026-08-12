from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25147_deterministic_quote_candidate_runtime as target,
)
from deepwide_agent.clients import ModelRequestError, ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
    QUESTION,
    TASK,
)


PRODUCTION = (
    "```markdown\n| Domain | Type | TLD Manager |\n"
    "| --- | --- | --- |\n| .in | country-code | 111 |\n```"
)
QUOTE = "Domain | Type | TLD Manager\n.in | country-code | 999"


def limits(**changes: int) -> ScoreFirstLimits:
    values = {
        "wall_seconds": 240,
        "model_calls": 3,
        "search_queries": 4,
        "fetch_targets": 10,
        "search_results_per_query": 3,
        "evidence_chars": 60_000,
        "page_chars": 5_000,
    }
    values.update(changes)
    return ScoreFirstLimits(**values)


class CandidateModel(CompatibleModel):
    def __init__(
        self,
        *,
        candidate_ids=None,
        malformed=False,
        fail_revision=False,
    ) -> None:
        super().__init__()
        self.candidate_ids = ["C001"] if candidate_ids is None else candidate_ids
        self.malformed = malformed
        self.fail_revision = fail_revision
        self.prompts: list[tuple[str, str, bool]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.prompts.append((str(system), str(user), bool(json_mode)))
        if self.logical_calls == 3:
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            if self.fail_revision:
                raise ModelRequestError("synthetic selector failure")
            text = (
                "not-json"
                if self.malformed
                else json.dumps({"candidate_ids": self.candidate_ids})
            )
            return ModelResult(text=text, usage={}, response_id=None, attempts=1)
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class DeterministicQuoteCandidateTests(unittest.TestCase):
    def _run(self, *, field_page=True, inner=None, post_effect_failure=False):
        inner = inner or CandidateModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GroundedFrontierSearch(
                    QUESTION, phase, field_page=field_page
                )
                for phase in target.PHASES
            }
            original = target.sparse_parent.parent.validate_result
            if post_effect_failure:

                def fail_after_effect(value):
                    checked = original(value)
                    if checked["content_free_receipt"][
                        "physical_model_logical_call_count"
                    ]:
                        raise RuntimeError("synthetic post-effect failure")
                    return checked

                target.sparse_parent.parent.validate_result = fail_after_effect
            try:
                result = target.run_task(
                    TASK, model=model, searches=searches, limits=limits()
                )
            finally:
                target.sparse_parent.parent.validate_result = original
        return inner, searches, target.validate_result(result)

    def test_atomic_bound_json_and_pipe_candidates_are_preverified(self) -> None:
        atomic = (
            "[IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]\n"
            '{"record_id":"R1","row":".in","cells":'
            '[["Type","country-code"],["TLD Manager","999"]]}\n'
            "[/IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]"
        )
        pipe = "| Domain | Type | TLD Manager |\n| --- | --- | --- |\n| .in | country-code | 999 |"
        for mode, content in (("atomic", atomic), ("pipe", pipe)):
            candidates, diagnostics = target.extract_quote_candidates(
                PRODUCTION,
                columns=("Domain", "Type", "TLD Manager"),
                pages=[{"title": "ignored", "content": content}],
            )
            with self.subTest(mode=mode):
                self.assertEqual(len(candidates), 1)
                self.assertEqual(candidates[0]["candidate_id"], "C001")
                self.assertEqual(candidates[0]["row_identity"], ".in")
                self.assertEqual(candidates[0]["field"], "TLD Manager")
                self.assertEqual(candidates[0]["new_value"], "999")
                self.assertIn(candidates[0]["exact_quote"], content)
                self.assertEqual(diagnostics["available_candidate_count"], 1)

    def test_indexed_sbcl_schema_span_is_exact_quote(self) -> None:
        schema = (
            '[SBCL-SCHEMA] {"source_host":"example.test",'
            '"row_key_label":"Domain","targets":'
            '[[1,"Type"],[2,"TLD Manager"]],"binding":"exact","conflicts":"omitted"}'
        )
        record = '[SBCL:R1] {"row":".in","cells":[[1,"country-code"],[2,"999"]]}'
        content = schema + "\n" + record
        candidates, diagnostics = target.extract_quote_candidates(
            PRODUCTION,
            columns=("Domain", "Type", "TLD Manager"),
            pages=[{"title": "", "content": content}],
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["exact_quote"], content)
        self.assertEqual(candidates[0]["new_value"], "999")
        self.assertEqual(diagnostics["json_record_observation_count"], 1)

    def test_conflict_is_omitted_and_duplicate_is_deduplicated(self) -> None:
        line_999 = '{"record_id":"R1","row":".in","cells":[["TLD Manager","999"]]}'
        line_998 = '{"record_id":"R2","row":".in","cells":[["TLD Manager","998"]]}'
        wrapped = lambda body: (
            "[IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]\n"
            + body
            + "\n[/IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]"
        )
        candidates, diagnostics = target.extract_quote_candidates(
            PRODUCTION,
            columns=("Domain", "Type", "TLD Manager"),
            pages=[{"title": "", "content": wrapped(line_999 + "\n" + line_998)}],
        )
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostics["conflicting_candidate_count"], 2)

        candidates, diagnostics = target.extract_quote_candidates(
            PRODUCTION,
            columns=("Domain", "Type", "TLD Manager"),
            pages=[{"title": "", "content": wrapped(line_999 + "\n" + line_999)}],
        )
        # A quote repeated twice in the same page cannot pass the exact-unique gate.
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostics["verifier_admissible_candidate_count"], 0)

        candidates, diagnostics = target.extract_quote_candidates(
            PRODUCTION,
            columns=("Domain", "Type", "TLD Manager"),
            pages=[{"title": "", "content": line_999}],
        )
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostics["json_record_observation_count"], 0)

    def test_selector_accepts_only_unique_known_ids_in_strict_json(self) -> None:
        candidates = [{"candidate_id": "C001"}, {"candidate_id": "C002"}]
        self.assertEqual(
            target._selection('{"candidate_ids":["C002"]}', candidates),
            ["C002"],
        )
        for text in (
            '{"candidate_ids":["C999"]}',
            '{"candidate_ids":["C001","C001"]}',
            '```json\n{"candidate_ids":[]}\n```',
            '{"candidate_ids":[],"extra":1}',
        ):
            with self.subTest(text=text), self.assertRaises((ValueError, json.JSONDecodeError)):
                target._selection(text, candidates)

    def test_no_gain_keeps_three_forwards_and_production(self) -> None:
        inner, _searches, result = self._run(field_page=False)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["candidate_revision_entry_count"], 0)
        self.assertEqual(receipt["underlying_provider_forward_count"], 0)
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_positive_gain_selects_preverified_candidate(self) -> None:
        inner, _searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(inner.prompts[-1][0], target.SELECTOR_SYSTEM)
        self.assertTrue(inner.prompts[-1][2])
        self.assertIn(result["production_prediction"], inner.prompts[-1][1])
        self.assertGreaterEqual(receipt["available_candidate_count"], 1)
        self.assertGreaterEqual(receipt["supplied_candidate_count"], 1)
        self.assertEqual(receipt["selected_candidate_count"], 1)
        self.assertEqual(receipt["applied_edit_count"], 1)
        self.assertEqual(receipt["rejected_selected_edit_count"], 0)
        self.assertTrue(receipt["selection_response_strict_json"])
        self.assertTrue(receipt["candidate_projection_valid"])
        self.assertIn("999", result["prediction"])
        self.assertNotEqual(result["prediction"], result["production_prediction"])

    def test_abstain_empty_candidates_and_selector_failure_preserve_production(self) -> None:
        for mode, inner in (
            ("abstain", CandidateModel(candidate_ids=[])),
            ("malformed", CandidateModel(malformed=True)),
            ("provider", CandidateModel(fail_revision=True)),
        ):
            with self.subTest(mode=mode):
                model, _searches, result = self._run(inner=inner)
                receipt = result["content_free_receipt"]
                self.assertEqual(model.logical_calls, 4)
                self.assertEqual(result["prediction"], result["production_prediction"])
                if mode == "abstain":
                    self.assertTrue(receipt["candidate_projection_valid"])
                    self.assertEqual(receipt["selected_candidate_count"], 0)
                elif mode == "malformed":
                    self.assertTrue(receipt["projection_failure_present"])
                else:
                    self.assertTrue(receipt["provider_failure_present"])

    def test_parent_posteffect_failure_preserves_production(self) -> None:
        inner, _searches, result = self._run(post_effect_failure=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["parent_post_effect_failure_present"])
        self.assertTrue(receipt["production_prediction_preserved_on_failure"])
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_privileged_or_budget_drift_fails_before_effect(self) -> None:
        for mode in ("privileged", "budget"):
            inner = CandidateModel()
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
                output_root = Path(raw)
                slots = output_root / "slots"
                slots.mkdir()
                for index in range(1, 5):
                    (slots / f"slot_{index:02d}.lock").write_text("{}\n")
                model = DeadlineAwareGlobalModelSlotLimiter(
                    inner,
                    slot_directory=slots,
                    output_root=output_root,
                    slot_cap=4,
                    absolute_deadline=time.monotonic() + 240,
                )
                searches = {
                    phase: GroundedFrontierSearch(QUESTION, phase)
                    for phase in target.PHASES
                }
                task = (
                    {**TASK, "question_type": "forbidden"}
                    if mode == "privileged"
                    else TASK
                )
                chosen = limits(model_calls=2) if mode == "budget" else limits()
                with self.assertRaises(ValueError):
                    target.run_task(task, model=model, searches=searches, limits=chosen)
            self.assertEqual(inner.logical_calls, 0)
            self.assertTrue(all(search.calls == 0 for search in searches.values()))

    def test_receipt_parent_and_accounting_tamper_fail_closed(self) -> None:
        _inner, _searches, result = self._run()
        for mode in ("available", "accounting", "launch", "parent"):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if mode == "available":
                receipt["available_candidate_count"] += 1
            elif mode == "accounting":
                receipt["selected_candidate_count"] += 1
            elif mode == "launch":
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["parent_result_payload_sha256"] = "0" * 64
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_receipt_is_content_free_and_signed_credit_zero(self) -> None:
        _inner, _searches, result = self._run()
        semantic = {
            key: value
            for key, value in result["content_free_receipt"].items()
            if not key.endswith("sha256")
        }
        encoded = json.dumps(semantic, ensure_ascii=False)
        for forbidden in (
            "New Delhi",
            "India",
            "IANA",
            "https://",
            "111",
            "999",
            TASK["opaque_id"],
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(result["entropy_or_information_gain_assigns_signed_credit"])

    def test_module_is_label_blind_build_only_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v25147_deterministic_quote_candidate_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "task_category",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "httpx",
            "socket",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])
        encoded = path.read_text(encoding="utf-8")
        self.assertNotIn("run_official_eval_local", encoded)
        self.assertNotIn("target/main", encoded)


if __name__ == "__main__":
    unittest.main()
