from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24390_uncertainty_active_evidence_runtime as runtime  # noqa: E402
from deepwide_agent import v24428_unique_title_anchor_projection as title  # noqa: E402
from deepwide_agent import v24502_record_bound_title_projection as record  # noqa: E402
from deepwide_agent import v24503_record_bound_reserve_integration as integration  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24333_programmatic_support_catalog import _source_key  # noqa: E402
from deepwide_agent.v24485_execution_scoped_validation_memo import (  # noqa: E402
    ExecutionValidationMemo,
)
from deepwide_agent.v24504_proof_carrying_record_bound_reserve import (  # noqa: E402
    run_single_validation_v24503_task,
)
from deepwide_agent.v24508_execution_scoped_high_level_validation_memo import (  # noqa: E402
    HighLevelValidationMemo,
)
from deepwide_agent.v24518_conversion_observability import (  # noqa: E402
    REASONS,
    ROUTES,
    _observation_key,
    _pair_diagnosis,
    build_from_validated_execution,
    validate_conversion_observability,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24503_record_bound_reserve_integration import clients  # noqa: E402


BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2024 |
| Beta | 2024 |
```"""
UNSUPPORTED_BASELINE = """```markdown
| Name | Free-form note |
| --- | --- |
| Alpha | unknown |
```"""


def page(
    content: str,
    *,
    page_title: str = "Alpha official history",
    host: str = "one.example",
) -> dict:
    return {
        "host": host,
        "title": page_title,
        "content": content,
        "fetch_integrity": True,
    }


def diagnose(
    content: str,
    *,
    page_title: str = "Alpha official history",
    baseline: str = BASELINE,
    before: bool = False,
    after: bool = False,
    source_count: int = 1,
):
    current = page(content, page_title=page_title)
    cells = runtime._baseline_cells(baseline)
    target = next(cell for cell in cells if cell.row_key == "Alpha")
    selected = {runtime._target_identity(target.row_key, target.column)}
    catalog = record.build_record_bound_title_projection(
        baseline, [current], selected_identities=selected
    )
    keys = {_observation_key(item) for item in catalog["observations"]}
    anchor_counts = Counter(
        {
            (
                _source_key(current["host"]),
                runtime._target_identity(target.row_key, "")[0],
            ): source_count
        }
    )
    reason, routes, signals = _pair_diagnosis(
        current,
        target,
        cells=cells,
        rows=title._visible_rows(cells),
        page_catalog=catalog,
        before_keys=keys if before else set(),
        after_keys=keys if after else set(),
        full_title_source_counts=anchor_counts,
    )
    return reason, routes, signals, catalog


class V24518ConversionObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(
            Path(cls.temporary.name), clock, mode="split_support"
        )
        low = ExecutionValidationMemo()
        high = HighLevelValidationMemo()
        with low, high:
            cls.validated = run_single_validation_v24503_task(
                TASK,
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
            cls.receipt = build_from_validated_execution(cls.validated)
        cls.model_acquisitions = model.acquisitions
        cls.search_requests = search.request_invocations
        cls.fetch_invocations = search.fetch_invocations

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_reason_partition_positive_duplicate_and_rejection_paths(self) -> None:
        cases = (
            (
                "new",
                dict(content="Established\n2025", after=True),
                "new_observation_emitted",
            ),
            (
                "duplicate",
                dict(content="Established\n2025", before=True, after=True),
                "projection_duplicate_parent_observation",
            ),
            (
                "ambiguous",
                dict(content="Established\n2025", source_count=2),
                "projection_rejected_source_ambiguity",
            ),
            (
                "post_projection_safety",
                dict(content="Established\n2025"),
                "projection_rejected_post_projection_safety",
            ),
        )
        for name, kwargs, expected in cases:
            with self.subTest(name=name):
                reason, _routes, signals, _catalog = diagnose(**kwargs)
                self.assertEqual(reason, expected)
                self.assertTrue(signals["grammar_projection"])

    def test_reason_partition_zero_projection_paths(self) -> None:
        cases = (
            (
                "unsupported",
                dict(
                    content="Alpha has a note from 2025.",
                    baseline=UNSUPPORTED_BASELINE,
                ),
                "no_projection_unsupported_column_kind",
            ),
            (
                "multiple_years",
                dict(content="Established\n2025 and 2026"),
                "no_projection_multiple_distinct_candidate_years",
            ),
            (
                "other_row_title",
                dict(content="Historical notes.", page_title="Beta official history"),
                "no_projection_unique_title_anchor_bound_to_other_visible_row",
            ),
            (
                "anchor_absent",
                dict(content="The organization began operations.", page_title="General history"),
                "no_projection_exact_entity_and_unique_title_anchor_absent_or_ambiguous",
            ),
            (
                "relation_absent",
                dict(content="Historical notes without a dated relation."),
                "no_projection_explicit_relation_absent",
            ),
            (
                "relation_without_year",
                dict(content="Alpha was founded recently."),
                "no_projection_relation_present_but_candidate_year_absent",
            ),
            (
                "candidate_year_safety",
                dict(content="Established\napproximately in 2025"),
                "no_projection_candidate_year_present_but_safety_rejected",
            ),
        )
        for name, kwargs, expected in cases:
            with self.subTest(name=name):
                reason, _routes, signals, _catalog = diagnose(**kwargs)
                self.assertEqual(reason, expected)
                self.assertTrue(signals["zero_projection"])

    def test_all_frozen_projection_routes_are_observable(self) -> None:
        cases = {
            "entity_segment": dict(
                content="Alpha was founded in 2025.", page_title="General history"
            ),
            "structured_label_value": dict(
                content="Alpha\nEstablished | 2025", page_title="General history"
            ),
            "unique_title_label_value": dict(content="Established | 2025"),
            "unique_title_narrative": dict(
                content="The institution was established in 2025."
            ),
            "unique_title_split_record": dict(content="Established\n2025"),
        }
        observed = set()
        for expected, kwargs in cases.items():
            with self.subTest(route=expected):
                _reason, routes, _signals, _catalog = diagnose(**kwargs)
                self.assertTrue(routes[expected])
                observed.update(name for name, present in routes.items() if present)
        self.assertEqual(observed, set(ROUTES))

    def test_typed_execution_receipt_is_exact_and_adds_no_effect(self) -> None:
        receipt = validate_conversion_observability(self.receipt)
        self.assertEqual(set(receipt["reason_counts"]), set(REASONS))
        self.assertEqual(
            sum(receipt["reason_counts"].values()),
            receipt["page_target_pair_count"],
        )
        self.assertEqual(
            receipt["grammar_projection_pair_count"]
            + receipt["zero_projection_pair_count"],
            receipt["page_target_pair_count"],
        )
        self.assertEqual(self.model_acquisitions, 2)
        self.assertEqual(self.search_requests, 4)
        self.assertEqual(self.fetch_invocations, 5)
        self.assertGreater(receipt["new_observation_pair_count"], 0)

    def test_receipt_tamper_and_raw_mapping_forgery_fail_closed(self) -> None:
        changed = copy.deepcopy(self.receipt)
        changed["reason_counts"]["new_observation_emitted"] -= 1
        changed["reason_counts"][
            "no_projection_explicit_relation_absent"
        ] += 1
        changed.pop("receipt_sha256")
        changed["receipt_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            validate_conversion_observability(changed)
        with self.assertRaises(TypeError):
            build_from_validated_execution(
                self.validated._trusted_outcome().record_bound_result  # type: ignore[arg-type]
            )

    def test_receipt_is_content_free_and_runtime_source_is_label_blind(self) -> None:
        encoded = json.dumps(self.receipt, ensure_ascii=False, sort_keys=True)
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "Alpha",
            "Beta",
            "2025",
            "one.example",
            "query_vector",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24518_conversion_observability.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
