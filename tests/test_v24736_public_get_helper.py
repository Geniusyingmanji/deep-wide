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

from scripts import v24736_public_get_helper as target  # noqa: E402


class V24736PublicGetHelperTests(unittest.TestCase):
    def test_allowlist_contains_exact_visible_targets_only(self) -> None:
        self.assertEqual(len(target.ROR_URLS), 48)
        self.assertEqual(len(target.WORLD_BANK_URLS), 2)
        self.assertEqual(len(target.ALLOWED_URLS), 50)
        for url in target.ALLOWED_URLS:
            target._validate_url(url)

    def test_unrelated_or_old_url_is_rejected_before_network(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / "scripts/v24736_public_get_helper.py")],
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
                    "url": "https://api.worldbank.org/v2/en/indicator/SP.POP.TOTL?downloadformat=csv",
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

    def test_query_or_redirect_surface_tamper_is_rejected(self) -> None:
        ror = next(iter(target.ROR_URLS))
        for url in (ror + "&extra=1", ror.replace("https://", "http://")):
            with self.assertRaises(ValueError):
                target._validate_url(url)


if __name__ == "__main__":
    unittest.main()
