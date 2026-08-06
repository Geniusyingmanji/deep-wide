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

from deepwide_agent.v24719_worldbank_transport_reliability import (  # noqa: E402
    REPRESENTATIONS,
    TARGETS,
    endpoint_url,
)
from scripts import v24720_public_get_helper as target  # noqa: E402


class V24720PublicGetHelperTests(unittest.TestCase):
    def test_allowlist_is_exact_frozen_vector(self) -> None:
        expected = {
            endpoint_url(spec, representation)
            for spec in TARGETS
            for representation in REPRESENTATIONS
        }
        self.assertEqual(target.ALLOWED_URLS, expected)
        self.assertEqual(len(expected), 12)

    def test_invalid_url_is_rejected_without_network(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / "scripts/v24720_public_get_helper.py")],
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
                    "url": "https://example.com/private",
                    "socket_timeout_seconds": 1,
                }
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(value["kind"], "invalid_input")
        self.assertEqual(value["body_base64"], "")

    def test_output_never_contains_exception_or_credential_fields(self) -> None:
        value = target._output("transport_error")
        self.assertEqual(set(value), target.OUTPUT_KEYS)
        encoded = json.dumps(value)
        for forbidden in ("exception", "credential", "header", "traceback"):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
