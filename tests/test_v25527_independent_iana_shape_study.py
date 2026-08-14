from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25527_independent_iana_shape_study as target  # noqa: E402


class V25527IndependentIanaShapeStudyTests(unittest.TestCase):
    def test_frozen_research_identities_are_consumed_and_forward_disjoint(self) -> None:
        identities = target.identity_vector()
        consumed = {
            identity for pair in target.consumed.PAIRS for identity in pair
        }
        frozen = {
            identity
            for pair in target.frozen_forward.PAIRS
            for identity in pair
        }
        self.assertEqual(len(identities), 8)
        self.assertTrue(set(identities).issubset(consumed))
        self.assertFalse(set(identities) & frozen)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )

    def test_exact_url_vector_and_one_request_cap_are_frozen(self) -> None:
        urls = target.url_vector()
        self.assertEqual(len(urls), 8)
        self.assertTrue(
            all(
                url.startswith(target.IANA_PREFIX) and url.endswith(".html")
                for url in urls
            )
        )
        self.assertEqual(
            target.payload_sha256(urls), target.EXPECTED_URL_VECTOR_SHA256
        )
        self.assertEqual(target.MAXIMUM_TOTAL_HTTP_REQUESTS, len(urls))
        self.assertEqual(target.MAXIMUM_REQUESTS_PER_URL, 1)

    def test_policy_excludes_research_set_and_authorizes_no_benchmark(self) -> None:
        policy = target.study_policy()
        self.assertTrue(
            policy[
                "identities_permanently_excluded_from_future_mechanism_quality_or_confirmation_populations"
            ]
        )
        self.assertTrue(policy["exact_public_urls_only"])
        self.assertFalse(policy["redirects_allowed"])
        self.assertFalse(
            policy[
                "external_mechanism_quality_deepwidebench_or_leaderboard_launch_authorized"
            ]
        )
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            ]
        )
        self.assertEqual(policy["positive_signed_credit_count"], 0)

    def test_manifest_tamper_fails(self) -> None:
        value = target.manifest()
        self.assertEqual(target.validate_manifest(value), value)
        changed = copy.deepcopy(value)
        changed["identities"][0] = ".bar"
        with self.assertRaises(ValueError):
            target.validate_manifest(changed)

    def test_contract_is_pure_and_has_no_effect_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any(
                name == blocked or name.startswith(blocked + ".")
                for blocked in (
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "httpx",
                )
                for name in imports
            )
        )
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)


if __name__ == "__main__":
    unittest.main()
