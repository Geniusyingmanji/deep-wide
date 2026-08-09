from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    RateAwareDeadlineTavilyThinCompatibilityClient,
)
from deepwide_agent.v24981_late_page_bound_fetch import LatePageBoundFetchMixin  # noqa: E402
from deepwide_agent.v25016_multi_identity_detail_fetch import (  # noqa: E402
    MultiIdentityDetailSearchClient,
)
from deepwide_agent.v25021_rate_aware_multi_identity_search import (  # noqa: E402
    RateAwareMultiIdentityDetailSearchClient,
    validate_search_class,
)


class RateAwareMultiIdentitySearchTests(unittest.TestCase):
    def test_composed_mro_preserves_fetch_and_search_owners(self) -> None:
        validate_search_class()
        cls = RateAwareMultiIdentityDetailSearchClient
        self.assertIs(
            next(base for base in cls.__mro__ if "_fetch_url" in base.__dict__),
            LatePageBoundFetchMixin,
        )
        self.assertIs(
            next(base for base in cls.__mro__ if "_direct_search" in base.__dict__),
            RateAwareDeadlineTavilyThinCompatibilityClient,
        )

    def test_composed_client_is_both_frozen_boundaries(self) -> None:
        self.assertTrue(
            issubclass(
                RateAwareMultiIdentityDetailSearchClient,
                MultiIdentityDetailSearchClient,
            )
        )
        self.assertTrue(
            issubclass(
                RateAwareMultiIdentityDetailSearchClient,
                RateAwareDeadlineTavilyThinCompatibilityClient,
            )
        )

    def test_module_adds_no_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25021_rate_aware_multi_identity_search.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ]
        self.assertFalse(
            any(
                name.startswith(("requests", "subprocess", "deepwidebench"))
                for name in imports
            )
        )
        for forbidden in ("ground_truth", "answer_key", "results.csv"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
