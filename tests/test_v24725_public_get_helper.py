from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as runtime  # noqa: E402
from scripts import v24725_public_get_helper as target  # noqa: E402


class V24725PublicGetHelperTests(unittest.TestCase):
    def test_allowlist_matches_fresh_vector_only(self) -> None:
        expected = {
            runtime.endpoint_url(spec, representation)
            for spec in runtime.TARGETS
            for representation in runtime.REPRESENTATIONS
        }
        self.assertEqual(target.ALLOWED_URLS, expected)
        self.assertEqual(len(expected), 4)

    def test_old_or_unrelated_url_is_rejected_before_network(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / "scripts/v24725_public_get_helper.py")],
            cwd=ROOT,
            env={
                "HOME": os.environ.get("HOME", str(Path.home())),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "DEEPWIDE_EXPECTED_PARENT_PID": str(os.getpid()),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            input=json.dumps(
                {
                    "url": "https://api.worldbank.org/v2/en/indicator/AG.SRF.TOTL.K2?downloadformat=csv",
                    "socket_timeout_seconds": 1,
                }
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        value = json.loads(completed.stdout)
        self.assertEqual(value["kind"], "invalid_input")
        self.assertEqual(value["body_base64"], "")


if __name__ == "__main__":
    unittest.main()
