from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    POLICY_ID as SINGLE_POLICY_ID,
)
from deepwide_agent.v24630_exact220_task_integration import (  # noqa: E402
    IntegratedExact220TaskOutcome,
)
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    COUNT_FIELDS,
    POLICY_ID as BACKFILL_POLICY_ID,
    RECEIPT_ROLE as BACKFILL_ROLE,
)
from deepwide_agent.v24860_coverage_revision_integration import (  # noqa: E402
    run_coverage_revision,
)
from deepwide_agent.v24861_coverage_revision_exact_task import (  # noqa: E402
    IntegratedCoverageRevisionTaskOutcome,
    build_envelope,
    integrate_parent_outcome,
    validate_envelope,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402


def single_receipt() -> dict[str, object]:
    return {
        "artifact_version": 1,
        "role": "v24280_task_union_single_shot_receipt",
        "policy_id": SINGLE_POLICY_ID,
        "multi_query_chunks": 0,
        "incomplete_mapping_chunks": 0,
        "mapping_failure_rows_normalized": 0,
        "action_trace_attachments": 0,
        "recursive_split_requests": 0,
        "one_action_trace_per_chunk": True,
        "task_union_only": True,
        "benchmark_metadata_or_evaluator_read": False,
    }


def backfill_receipt() -> dict[str, object]:
    return {
        "artifact_version": 1,
        "role": BACKFILL_ROLE,
        "policy_id": BACKFILL_POLICY_ID,
        **{name: 0 for name in COUNT_FIELDS},
        "same_provider_response_only": True,
        "canonical_url_match_only": True,
        "unique_nonempty_citation_title_only": True,
        "existing_action_title_preserved": True,
        "conflicting_citation_titles_fail_closed": True,
        "provider_payload_mutated": False,
        "post_fetch_title_used": False,
        "cross_response_state_used": False,
        "legacy_single_shot_receipt_changed": False,
        "additional_search_fetch_model_process_evaluator_or_credit_effect": False,
        "raw_task_question_query_url_title_page_prediction_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


class V24861CoverageRevisionExactTaskTests(unittest.TestCase):
    def build(self):
        helper = core_test.V24860CoverageRevisionIntegrationTests()
        temporary, clock, _inner, model, parent = helper.build_parent(
            [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
        )
        exact_parent = IntegratedExact220TaskOutcome(
            copy.deepcopy(parent.result),
            copy.deepcopy(parent.model_slot_receipt),
            copy.deepcopy(parent.transport_health),
            copy.deepcopy(single_receipt()),
            copy.deepcopy(backfill_receipt()),
        )
        revision = run_coverage_revision(
            core_test.task(),
            parent_result=exact_parent.result,
            parent_model_slot_receipt=exact_parent.model_slot_receipt,
            model=model,
            pages=core_test.pages_for(exact_parent.result),
            limits=core_test.limits(),
            monotonic=clock,
        )
        outcome = integrate_parent_outcome(exact_parent, revision)
        return temporary, outcome

    def test_envelope_preserves_parent_and_final_slot_receipts(self) -> None:
        temporary, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        envelope = build_envelope(outcome, arm="baseline")
        validated = validate_envelope(envelope)
        self.assertEqual(
            validated["parent_model_slot_receipt"]["acquisitions"], 2
        )
        self.assertEqual(validated["model_slot_receipt"]["acquisitions"], 3)
        self.assertEqual(
            validated["coverage_revision_receipt"]["provider_request_delta"], 1
        )
        self.assertEqual(
            validated["result"]["parent_result"]["prediction"],
            core_test.BASELINE.replace("| Name", "```markdown\n| Name") + "\n```",
        )

    def test_resealed_final_slot_tamper_is_rejected(self) -> None:
        temporary, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        envelope = build_envelope(outcome, arm="baseline")
        altered = copy.deepcopy(envelope)
        altered["model_slot_receipt"]["acquisitions"] += 1
        altered["model_slot_receipt"]["slot_acquisition_counts"][0] += 1
        altered["model_slot_receipt"].pop("receipt_payload_sha256")
        altered["model_slot_receipt"]["receipt_payload_sha256"] = payload_sha256(
            altered["model_slot_receipt"]
        )
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_envelope(altered)

    def test_resealed_parent_slot_tamper_is_rejected(self) -> None:
        temporary, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        envelope = build_envelope(outcome, arm="baseline")
        altered = copy.deepcopy(envelope)
        altered["parent_model_slot_receipt"]["acquisitions"] += 1
        altered["parent_model_slot_receipt"]["slot_acquisition_counts"][0] += 1
        altered["parent_model_slot_receipt"].pop("receipt_payload_sha256")
        altered["parent_model_slot_receipt"]["receipt_payload_sha256"] = payload_sha256(
            altered["parent_model_slot_receipt"]
        )
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_envelope(altered)

    def test_search_receipt_mismatch_is_rejected(self) -> None:
        temporary, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        altered = IntegratedCoverageRevisionTaskOutcome(
            copy.deepcopy(outcome.result),
            copy.deepcopy(outcome.parent_model_slot_receipt),
            copy.deepcopy(outcome.model_slot_receipt),
            copy.deepcopy(outcome.transport_health),
            {**copy.deepcopy(outcome.search_single_shot_receipt), "multi_query_chunks": 1},
            copy.deepcopy(outcome.citation_title_backfill_receipt),
            copy.deepcopy(outcome.coverage_revision_receipt),
        )
        with self.assertRaises(ValueError):
            build_envelope(altered, arm="baseline")


if __name__ == "__main__":
    unittest.main()
