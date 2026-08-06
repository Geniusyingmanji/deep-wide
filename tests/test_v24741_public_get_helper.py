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

from deepwide_agent import v24740_dual_representation_resilience as runtime  # noqa: E402
from scripts import v24741_public_get_helper as target  # noqa: E402


class V24741PublicGetHelperTests(unittest.TestCase):
    def test_allowlist_contains_exact_four_fresh_urls(self) -> None:
        expected = {
            runtime.endpoint_url(spec, representation)
            for spec in runtime.TARGETS
            for representation in runtime.REPRESENTATIONS
        }
        self.assertEqual(target.ALLOWED_URLS, expected)
        self.assertEqual(len(expected), 4)
        for url in expected:
            target._validate_url(url)

    def test_old_or_benchmark_url_is_rejected_before_network(self) -> None:
        for url in (
            "https://api.worldbank.org/v2/en/indicator/IT.NET.USER.ZS?downloadformat=csv",
            "https://api.worldbank.org/v2/en/indicator/SP.DYN.LE00.IN?downloadformat=csv",
            "https://example.invalid/",
        ):
            completed = subprocess.run(
                [sys.executable, "-I", "-B", str(ROOT / "scripts/v24741_public_get_helper.py")],
                cwd=ROOT,
                env={
                    "HOME": os.environ.get("HOME", str(Path.home())),
                    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "DEEPWIDE_EXPECTED_PARENT_PID": str(os.getpid()),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONNOUSERSITE": "1",
                    "PYTHONSAFEPATH": "1",
                },
                input=json.dumps({"url": url, "socket_timeout_seconds": 1}),
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

    def test_query_or_authority_tamper_is_rejected(self) -> None:
        valid = runtime.endpoint_url(runtime.TARGETS[0], "aggregate_json")
        for url in (
            valid + "&page=2",
            valid.replace("https://", "http://"),
            valid.replace("api.worldbank.org", "api.worldbank.org:443"),
            valid.replace("per_page=400", "per_page=401"),
        ):
            with self.assertRaises(ValueError):
                target._validate_url(url)


if __name__ == "__main__":
    unittest.main()
