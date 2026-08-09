from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    LatePageBoundFetchMixin,
    LatePageBoundSearchClient,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    HELPER,
    RobustLatePageBoundSearchClient,
    validate_search_class,
)


class RobustLatePageFetchTests(unittest.TestCase):
    def test_helper_is_ordinary_repo_local_file(self) -> None:
        self.assertTrue(HELPER.is_file())
        self.assertFalse(HELPER.is_symlink())
        self.assertTrue(HELPER.resolve().is_relative_to(ROOT))

    def test_search_class_preserves_parent_boundary(self) -> None:
        validate_search_class()
        self.assertTrue(issubclass(RobustLatePageBoundSearchClient, LatePageBoundSearchClient))
        owner = next(
            base
            for base in RobustLatePageBoundSearchClient.__mro__
            if "_fetch_url" in base.__dict__
        )
        self.assertIs(owner, LatePageBoundFetchMixin)


if __name__ == "__main__":
    unittest.main()
