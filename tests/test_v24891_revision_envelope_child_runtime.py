from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24882_mapping_recovery_stage_runtime as frozen  # noqa: E402
from deepwide_agent import v24891_revision_envelope_child_runtime as target  # noqa: E402
import test_v24860_coverage_revision_integration as core  # noqa: E402
from test_v24875_keyless_coverage_child_runtime import (  # noqa: E402
    MeteredFullSearch,
    V24875KeylessCoverageChildRuntimeTests,
)


class V24891RevisionEnvelopeChildRuntimeTests(unittest.TestCase):
    def test_real_synthetic_child_commits_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            clock, _inner, model, search = (
                V24875KeylessCoverageChildRuntimeTests().clients(
                    output, MeteredFullSearch
                )
            )
            target.run_child_bundle(
                output_root=output,
                directory=directory,
                task=core.task(),
                model=model,
                search=search,
                limits=core.limits(),
                expected_model_slot_cap=2,
                monotonic=clock,
            )
            self.assertTrue((directory / target.STAGE_NAME).is_file())

    def test_isolation(self) -> None:
        target.validate_isolation()
        self.assertIsNot(target.run_child_bundle, frozen.run_child_bundle)


if __name__ == "__main__":
    unittest.main()
