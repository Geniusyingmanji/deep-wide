from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24873_keyless_fixed_coverage_runtime as frozen  # noqa: E402
from deepwide_agent import v24889_revision_envelope_runtime as target  # noqa: E402
import test_v24860_coverage_revision_integration as core  # noqa: E402
from test_v24873_keyless_fixed_coverage_runtime import (  # noqa: E402
    V24873KeylessFixedCoverageRuntimeTests,
)


class V24889RevisionEnvelopeRuntimeTests(unittest.TestCase):
    def test_low_full_and_privileged_behaviors_remain_valid(self) -> None:
        helper = V24873KeylessFixedCoverageRuntimeTests()
        for name in (
            "test_full_fixed_budget_chain_captures_ten_pages",
            "test_low_source_count_is_actual_fetch_not_cap_failure",
            "test_privileged_input_fails_before_model_or_search_effect",
        ):
            with self.subTest(name=name):
                getattr(helper, name)()

    def test_isolation(self) -> None:
        target.validate_isolation()
        self.assertIsNot(target.run_v24889_task, frozen.run_v24873_task)


if __name__ == "__main__":
    unittest.main()
