from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24222_fixed_sufficiency_baseline import (  # noqa: E402
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_action_step,
    build_criterion_catalog,
    build_evidence_snapshot,
    decide_fixed_sufficiency_baseline,
    object_sha256,
    validate_action_trace,
    validate_criterion_catalog,
    validate_decision_receipt,
    validate_evidence_snapshot,
)


VISIBLE = "0" * 64
ROOT_SCOPE = "1" * 64
TASK_REF = "2" * 64


def digest(character: str) -> str:
    return character * 64


def criterion(
    reference: str,
    action: str,
    *,
    priority: int,
    kind: str = "coverage",
    minimum_evidence: int = 1,
    minimum_sources: int = 1,
) -> dict[str, object]:
    return {
        "criterion_ref_sha256": reference,
        "criterion_kind": kind,
        "priority": priority,
        "action_class_sha256": action,
        "minimum_clean_evidence_classes": minimum_evidence,
        "minimum_clean_source_classes": minimum_sources,
    }


def assertion(
    reference: str,
    evidence_class: str,
    source_class: str,
    *,
    page_backed: bool = True,
    assertion_kind: str = "support",
) -> dict[str, object]:
    return {
        "criterion_ref_sha256": reference,
        "evidence_class_sha256": evidence_class,
        "source_class_sha256": source_class,
        "page_backed": page_backed,
        "assertion_kind": assertion_kind,
    }


def catalog(
    criteria: list[dict[str, object]], *, max_action_steps: int = 3
) -> dict[str, object]:
    return build_criterion_catalog(
        visible_input_projection_sha256=VISIBLE,
        root_scope_sha256=ROOT_SCOPE,
        max_action_steps=max_action_steps,
        criteria=criteria,
    )


def trace(*actions: str) -> list[dict[str, object]]:
    return [
        build_action_step(step_index=index, action_class_sha256=action)
        for index, action in enumerate(actions)
    ]


def snapshot(
    assertions: list[dict[str, object]], *, after_action_count: int
) -> dict[str, object]:
    return build_evidence_snapshot(
        root_scope_sha256=ROOT_SCOPE,
        after_action_count=after_action_count,
        assertions=assertions,
    )


def decide(
    criteria: list[dict[str, object]],
    actions: list[dict[str, object]],
    assertions: list[dict[str, object]],
    *,
    max_action_steps: int = 3,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    frozen = catalog(criteria, max_action_steps=max_action_steps)
    evidence = snapshot(assertions, after_action_count=len(actions))
    receipt = decide_fixed_sufficiency_baseline(
        criterion_catalog=frozen,
        action_trace=actions,
        evidence_snapshot=evidence,
        opaque_task_ref_sha256=TASK_REF,
    )
    return frozen, evidence, receipt


class V24222FixedSufficiencyBaselineTests(unittest.TestCase):
    def test_catalog_requires_empty_presearch_trace(self) -> None:
        action = digest("a")
        with self.assertRaisesRegex(ValueError, "before the first action"):
            build_criterion_catalog(
                visible_input_projection_sha256=VISIBLE,
                root_scope_sha256=ROOT_SCOPE,
                max_action_steps=3,
                criteria=[criterion(digest("b"), action, priority=0)],
                presearch_action_trace=trace(action),
            )

    def test_catalog_requires_coverage_and_sorts_unique_criteria(self) -> None:
        action_a = digest("a")
        action_b = digest("b")
        frozen = catalog(
            [
                criterion(
                    digest("d"), action_b, priority=2, kind="source"
                ),
                criterion(digest("c"), action_a, priority=1),
            ]
        )
        self.assertEqual(
            [row["criterion_ref_sha256"] for row in frozen["criteria"]],
            [digest("c"), digest("d")],
        )
        self.assertTrue(frozen["catalog_frozen_before_first_action"])
        self.assertEqual(frozen["construction_action_trace_sha256"], object_sha256([]))
        with self.assertRaisesRegex(ValueError, "no coverage criterion"):
            catalog(
                [
                    criterion(
                        digest("c"), action_a, priority=0, kind="source"
                    )
                ]
            )
        with self.assertRaisesRegex(ValueError, "not unique"):
            catalog(
                [
                    criterion(digest("c"), action_a, priority=0),
                    criterion(digest("c"), action_b, priority=1),
                ]
            )

    def test_all_satisfied_is_answer_ready_but_not_success(self) -> None:
        action = digest("a")
        reference = digest("b")
        _, _, receipt = decide(
            [criterion(reference, action, priority=0)],
            trace(action),
            [assertion(reference, digest("c"), digest("d"))],
        )
        self.assertEqual(receipt["decision_kind"], "answer_ready")
        self.assertEqual(receipt["satisfied_criterion_count"], 1)
        self.assertEqual(receipt["remaining_action_steps"], 2)
        self.assertTrue(receipt["answer_ready_is_not_task_success"])
        self.assertTrue(receipt["budget_exhaustion_is_not_task_success"])
        self.assertFalse(receipt["open_set_completeness_claimed"])

    def test_unresolved_selects_highest_priority_criterion(self) -> None:
        action_a = digest("a")
        action_b = digest("b")
        _, _, receipt = decide(
            [
                criterion(digest("c"), action_a, priority=9),
                criterion(
                    digest("d"), action_b, priority=1, kind="time"
                ),
            ],
            [],
            [],
        )
        self.assertEqual(receipt["decision_kind"], "continue")
        self.assertEqual(receipt["selected_criterion_ref_sha256"], digest("d"))
        self.assertEqual(receipt["selected_action_class_sha256"], action_b)
        self.assertEqual(
            receipt["decision_reason"],
            "highest_priority_unresolved_criterion_with_budget",
        )

    def test_contradicted_criterion_precedes_unresolved(self) -> None:
        action_a = digest("a")
        action_b = digest("b")
        contradicted = digest("d")
        _, _, receipt = decide(
            [
                criterion(digest("c"), action_a, priority=0),
                criterion(
                    contradicted,
                    action_b,
                    priority=100,
                    kind="exclusion",
                ),
            ],
            [],
            [
                assertion(
                    contradicted,
                    digest("e"),
                    digest("f"),
                    assertion_kind="contradiction",
                )
            ],
        )
        self.assertEqual(receipt["decision_kind"], "continue")
        self.assertEqual(receipt["selected_criterion_ref_sha256"], contradicted)
        self.assertEqual(receipt["selected_action_class_sha256"], action_b)
        self.assertEqual(receipt["contradicted_criterion_count"], 1)

    def test_distinct_evidence_and_source_thresholds_are_both_required(self) -> None:
        action = digest("a")
        reference = digest("b")
        criterion_value = criterion(
            reference,
            action,
            priority=0,
            minimum_evidence=2,
            minimum_sources=2,
        )
        one_evidence_two_sources = [
            assertion(reference, digest("c"), digest("d")),
            assertion(reference, digest("c"), digest("e")),
        ]
        _, _, pending = decide(
            [criterion_value], [], one_evidence_two_sources
        )
        diagnostic = pending["criterion_diagnostics"][0]
        self.assertEqual(diagnostic["clean_page_evidence_class_count"], 1)
        self.assertEqual(diagnostic["clean_source_class_count"], 2)
        self.assertEqual(diagnostic["status"], "unresolved")

        enough = one_evidence_two_sources + [
            assertion(reference, digest("f"), digest("e"))
        ]
        _, _, ready = decide([criterion_value], [], enough)
        self.assertEqual(ready["decision_kind"], "answer_ready")

    def test_nonpage_assertions_never_satisfy_or_contradict(self) -> None:
        action = digest("a")
        reference = digest("b")
        _, _, receipt = decide(
            [criterion(reference, action, priority=0)],
            [],
            [
                assertion(
                    reference,
                    digest("c"),
                    digest("d"),
                    page_backed=False,
                ),
                assertion(
                    reference,
                    digest("e"),
                    digest("f"),
                    page_backed=False,
                    assertion_kind="contradiction",
                ),
            ],
        )
        self.assertEqual(receipt["decision_kind"], "continue")
        self.assertEqual(receipt["nonpage_assertion_count"], 2)
        diagnostic = receipt["criterion_diagnostics"][0]
        self.assertEqual(diagnostic["clean_page_evidence_class_count"], 0)
        self.assertEqual(diagnostic["contradiction_page_evidence_class_count"], 0)

    def test_page_contradiction_dominates_other_clean_support(self) -> None:
        action = digest("a")
        reference = digest("b")
        _, _, receipt = decide(
            [criterion(reference, action, priority=0)],
            [],
            [
                assertion(reference, digest("c"), digest("d")),
                assertion(
                    reference,
                    digest("e"),
                    digest("f"),
                    assertion_kind="contradiction",
                ),
            ],
        )
        diagnostic = receipt["criterion_diagnostics"][0]
        self.assertEqual(diagnostic["clean_page_evidence_class_count"], 1)
        self.assertEqual(diagnostic["status"], "contradicted")
        self.assertEqual(receipt["decision_kind"], "continue")

    def test_same_page_evidence_class_with_both_polarities_fails_closed(self) -> None:
        action = digest("a")
        reference = digest("b")
        assertions = [
            assertion(reference, digest("c"), digest("d")),
            assertion(
                reference,
                digest("c"),
                digest("e"),
                assertion_kind="contradiction",
            ),
        ]
        with self.assertRaisesRegex(ValueError, "both support and contradiction"):
            decide([criterion(reference, action, priority=0)], [], assertions)

    def test_pending_at_hard_budget_abstains_without_success_claim(self) -> None:
        action = digest("a")
        reference = digest("b")
        _, _, receipt = decide(
            [criterion(reference, action, priority=0)],
            trace(action, action),
            [],
            max_action_steps=2,
        )
        self.assertEqual(receipt["decision_kind"], "abstain_budget_exhausted")
        self.assertEqual(receipt["remaining_action_steps"], 0)
        self.assertIsNone(receipt["selected_criterion_ref_sha256"])
        self.assertIsNone(receipt["selected_action_class_sha256"])
        self.assertTrue(receipt["budget_exhaustion_is_not_task_success"])

    def test_satisfied_at_hard_budget_is_ready_not_abstain(self) -> None:
        action = digest("a")
        reference = digest("b")
        _, _, receipt = decide(
            [criterion(reference, action, priority=0)],
            trace(action),
            [assertion(reference, digest("c"), digest("d"))],
            max_action_steps=1,
        )
        self.assertEqual(receipt["remaining_action_steps"], 0)
        self.assertEqual(receipt["decision_kind"], "answer_ready")

    def test_snapshot_must_bind_trace_count_and_root_scope(self) -> None:
        action = digest("a")
        reference = digest("b")
        frozen = catalog([criterion(reference, action, priority=0)])
        actions = trace(action)
        stale = snapshot([], after_action_count=0)
        with self.assertRaisesRegex(ValueError, "not bound to the action trace"):
            decide_fixed_sufficiency_baseline(
                criterion_catalog=frozen,
                action_trace=actions,
                evidence_snapshot=stale,
                opaque_task_ref_sha256=TASK_REF,
            )
        wrong_root = build_evidence_snapshot(
            root_scope_sha256=digest("9"),
            after_action_count=1,
            assertions=[],
        )
        with self.assertRaisesRegex(ValueError, "root scopes differ"):
            decide_fixed_sufficiency_baseline(
                criterion_catalog=frozen,
                action_trace=actions,
                evidence_snapshot=wrong_root,
                opaque_task_ref_sha256=TASK_REF,
            )

    def test_unknown_criterion_and_action_fail_closed(self) -> None:
        action = digest("a")
        reference = digest("b")
        frozen = catalog([criterion(reference, action, priority=0)])
        unknown_assertion = snapshot(
            [assertion(digest("c"), digest("d"), digest("e"))],
            after_action_count=0,
        )
        with self.assertRaisesRegex(ValueError, "unknown criterion"):
            decide_fixed_sufficiency_baseline(
                criterion_catalog=frozen,
                action_trace=[],
                evidence_snapshot=unknown_assertion,
                opaque_task_ref_sha256=TASK_REF,
            )
        with self.assertRaisesRegex(ValueError, "outside the frozen menu"):
            decide_fixed_sufficiency_baseline(
                criterion_catalog=frozen,
                action_trace=trace(digest("f")),
                evidence_snapshot=snapshot([], after_action_count=1),
                opaque_task_ref_sha256=TASK_REF,
            )

    def test_trace_cannot_exceed_frozen_budget(self) -> None:
        action = digest("a")
        reference = digest("b")
        frozen = catalog(
            [criterion(reference, action, priority=0)], max_action_steps=1
        )
        actions = trace(action, action)
        with self.assertRaisesRegex(ValueError, "exceeds the frozen budget"):
            decide_fixed_sufficiency_baseline(
                criterion_catalog=frozen,
                action_trace=actions,
                evidence_snapshot=snapshot([], after_action_count=2),
                opaque_task_ref_sha256=TASK_REF,
            )

    def test_duplicate_assertion_and_invalid_threshold_fail_closed(self) -> None:
        action = digest("a")
        reference = digest("b")
        row = assertion(reference, digest("c"), digest("d"))
        with self.assertRaisesRegex(ValueError, "duplicate assertions"):
            snapshot([row, dict(row)], after_action_count=0)
        with self.assertRaisesRegex(ValueError, "integer bounds"):
            catalog(
                [
                    criterion(
                        reference,
                        action,
                        priority=0,
                        minimum_evidence=0,
                    )
                ]
            )

    def test_nested_forbidden_metadata_is_rejected_everywhere(self) -> None:
        action = digest("a")
        reference = digest("b")
        unsafe_criterion = criterion(reference, action, priority=0)
        unsafe_criterion["priority"] = {"safe": [{"question_type": "hidden"}]}
        with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
            catalog([unsafe_criterion])

        unsafe_step = build_action_step(step_index=0, action_class_sha256=action)
        unsafe_step["step_index"] = {"safe": {"gold_answer": "hidden"}}
        with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
            validate_action_trace([unsafe_step])

        unsafe_assertion = assertion(reference, digest("c"), digest("d"))
        unsafe_assertion["page_backed"] = {"safe": {"evaluator_score": 1}}
        with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
            snapshot([unsafe_assertion], after_action_count=0)

        frozen, evidence, receipt = decide(
            [criterion(reference, action, priority=0)], [], []
        )
        unsafe_receipt = copy.deepcopy(receipt)
        unsafe_receipt["criterion_diagnostics"] = [
            {"safe": {"ground_truth": "hidden"}}
        ]
        with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
            validate_decision_receipt(
                unsafe_receipt,
                criterion_catalog=frozen,
                action_trace=[],
                evidence_snapshot=evidence,
                opaque_task_ref_sha256=TASK_REF,
            )

    def test_tampered_and_resealed_artifacts_are_rejected(self) -> None:
        action = digest("a")
        reference = digest("b")
        actions = trace(action)
        frozen, evidence, receipt = decide(
            [criterion(reference, action, priority=0)], actions, []
        )

        tampered_catalog = copy.deepcopy(frozen)
        tampered_catalog["role"] = "resealed_wrong_role"
        tampered_catalog.pop("catalog_sha256")
        tampered_catalog["catalog_sha256"] = object_sha256(tampered_catalog)
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            validate_criterion_catalog(tampered_catalog)

        tampered_trace = copy.deepcopy(actions)
        tampered_trace[0]["role"] = "resealed_wrong_role"
        tampered_trace[0].pop("step_sha256")
        tampered_trace[0]["step_sha256"] = object_sha256(tampered_trace[0])
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            validate_action_trace(tampered_trace)

        tampered_snapshot = copy.deepcopy(evidence)
        tampered_snapshot["active_evidence_only"] = False
        tampered_snapshot.pop("snapshot_sha256")
        tampered_snapshot["snapshot_sha256"] = object_sha256(tampered_snapshot)
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            validate_evidence_snapshot(tampered_snapshot)

        tampered_receipt = copy.deepcopy(receipt)
        tampered_receipt["decision_kind"] = "answer_ready"
        tampered_receipt.pop("receipt_sha256")
        tampered_receipt["receipt_sha256"] = object_sha256(tampered_receipt)
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            validate_decision_receipt(
                tampered_receipt,
                criterion_catalog=frozen,
                action_trace=actions,
                evidence_snapshot=evidence,
                opaque_task_ref_sha256=TASK_REF,
            )

    def test_schemas_and_output_order_are_exact(self) -> None:
        action = digest("a")
        reference = digest("b")
        frozen, evidence, receipt = decide(
            [criterion(reference, action, priority=0)], [], []
        )
        self.assertEqual(
            list(frozen),
            [
                "artifact_version",
                "role",
                "policy_id",
                "visible_input_projection_sha256",
                "root_scope_sha256",
                "construction_policy",
                "construction_action_trace_sha256",
                "catalog_frozen_before_first_action",
                "max_action_steps",
                "criteria",
                "question_text_or_raw_evidence_embedded",
                "benchmark_metadata_or_outcome_embedded",
                "catalog_sha256",
            ],
        )
        self.assertEqual(
            list(evidence),
            [
                "artifact_version",
                "role",
                "policy_id",
                "root_scope_sha256",
                "after_action_count",
                "active_evidence_only",
                "assertions",
                "question_text_or_raw_evidence_embedded",
                "benchmark_metadata_or_outcome_embedded",
                "snapshot_sha256",
            ],
        )
        self.assertEqual(
            list(receipt),
            [
                "artifact_version",
                "role",
                "policy_id",
                "label_blind",
                "baseline_only",
                "opaque_task_ref_sha256",
                "root_scope_sha256",
                "decision_index",
                "criterion_catalog_sha256",
                "action_trace_sha256",
                "evidence_snapshot_sha256",
                "max_action_steps",
                "consumed_action_steps",
                "remaining_action_steps",
                "criterion_count",
                "satisfied_criterion_count",
                "unresolved_criterion_count",
                "contradicted_criterion_count",
                "nonpage_assertion_count",
                "criterion_diagnostics",
                "decision_kind",
                "selected_criterion_ref_sha256",
                "selected_action_class_sha256",
                "decision_reason",
                "criteria_frozen_before_first_action",
                "answer_ready_is_not_task_success",
                "budget_exhaustion_is_not_task_success",
                "open_set_completeness_claimed",
                "source_independence_claimed",
                "four_layer_risk_entropy_or_voc_used",
                "question_text_or_raw_evidence_read",
                "mapping_gold_category_question_type_evaluator_score_or_reward_read",
                "file_environment_network_model_search_fetch_or_process_accessed",
                "benchmark_forward_evaluator_credit_or_training_authorized",
                "receipt_sha256",
            ],
        )
        self.assertEqual(
            list(receipt["criterion_diagnostics"][0]),
            [
                "criterion_ref_sha256",
                "criterion_kind",
                "priority",
                "action_class_sha256",
                "status",
                "clean_page_evidence_class_count",
                "clean_source_class_count",
                "contradiction_page_evidence_class_count",
                "minimum_clean_evidence_classes",
                "minimum_clean_source_classes",
            ],
        )
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_criterion_catalog({**frozen, "extra": False})

    def test_all_authorities_and_unimplemented_claims_are_false(self) -> None:
        action = digest("a")
        _, _, receipt = decide(
            [criterion(digest("b"), action, priority=0)], [], []
        )
        self.assertIs(PRODUCTION_PACKAGE_AUTHORIZED, False)
        for field in (
            "open_set_completeness_claimed",
            "source_independence_claimed",
            "four_layer_risk_entropy_or_voc_used",
            "question_text_or_raw_evidence_read",
            "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "file_environment_network_model_search_fetch_or_process_accessed",
            "benchmark_forward_evaluator_credit_or_training_authorized",
        ):
            self.assertIs(receipt[field], False, field)

    def test_module_ast_has_no_io_network_process_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24222_fixed_sufficiency_baseline.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed_imports = {
            "__future__",
            "collections",
            "hashlib",
            "json",
            "re",
            "typing",
        }
        forbidden_calls = {
            "__import__",
            "breakpoint",
            "compile",
            "eval",
            "exec",
            "input",
            "open",
        }
        forbidden_roots = {
            "asyncio",
            "builtins",
            "http",
            "httpx",
            "importlib",
            "os",
            "pathlib",
            "requests",
            "shutil",
            "socket",
            "subprocess",
            "urllib",
        }
        imports: set[str] = set()
        calls: set[str] = set()
        attributes: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in forbidden_calls:
                    calls.add(node.func.id)
            elif isinstance(node, ast.Attribute):
                current: ast.expr = node
                while isinstance(current, ast.Attribute):
                    current = current.value
                if isinstance(current, ast.Name) and current.id in forbidden_roots:
                    attributes.add(current.id)
        self.assertEqual(imports - allowed_imports, set())
        self.assertEqual(calls, set())
        self.assertEqual(attributes, set())


if __name__ == "__main__":
    unittest.main()
