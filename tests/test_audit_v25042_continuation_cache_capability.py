from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25042_continuation_cache_capability as target  # noqa: E402


class _Response:
    status_code = 404


class _Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **_kwargs: object) -> _Response:
        self.calls.append((method, url))
        return _Response()


class V25042ContinuationCacheAuditTests(unittest.TestCase):
    def test_historical_negative_control_is_below_cache_minimum(self) -> None:
        value = target.historical_evidence()
        self.assertEqual(value["outcomes"], 32)
        self.assertEqual(value["cached_input_tokens"], 0)
        self.assertLess(value["maximum_input_tokens_per_request"], 1024)
        self.assertTrue(value["does_not_test_cache_eligible_prefix"])

    def test_active_clients_do_not_request_or_account_for_cache(self) -> None:
        value = target.local_source_evidence()
        self.assertTrue(value["active_request_fields_all_absent"])
        self.assertTrue(value["active_cache_usage_fields_all_absent"])
        self.assertTrue(value["historical_parser_reads_cached_tokens"])
        self.assertFalse(value["historical_parser_reads_cache_write_tokens"])

    def test_schema_probe_is_exact_two_non_model_requests(self) -> None:
        session = _Session()
        value = target.schema_probe(session)
        self.assertEqual(value["request_count"], 2)
        self.assertEqual(value["model_search_fetch_or_evaluator_calls"], 0)
        self.assertFalse(value["discoverable_schema_found"])
        self.assertEqual([row["http_status"] for row in value["requests"]], [404, 404])

    def test_decision_rejects_continuation_savings_and_cache_probe(self) -> None:
        value = target.validate(
            target.build(now=1, require_clean=False, session=_Session())
        )
        self.assertEqual(
            value["decision"]["previous_response_id_input_token_savings_hypothesis"],
            "no_go",
        )
        self.assertFalse(value["decision"]["prompt_cache_support_on_local_proxy_established"])
        self.assertFalse(value["authorization"]["prompt_cache_effect_probe"])
        self.assertTrue(value["authorization"]["resume_shared_page_quality_mainline"])


if __name__ == "__main__":
    unittest.main()
