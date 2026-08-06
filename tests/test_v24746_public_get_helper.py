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

from scripts import v24746_public_get_helper as target  # noqa: E402


class V24746PublicGetHelperTests(unittest.TestCase):
    def test_allowlist_is_exact_unique_32_url_vector(self) -> None:
        self.assertEqual(len(target.ALLOWED_URLS), 32)
        self.assertEqual(
            {target.urlsplit(url).hostname for url in target.ALLOWED_URLS},
            target.ALLOWED_HOSTS,
        )
        for url in target.ALLOWED_URLS:
            target._validate_url(url)

    def test_unrelated_url_is_rejected_before_network(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / "scripts/v24746_public_get_helper.py")],
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
                    "url": "https://api.crossref.org/works/10.0000%2Funrelated",
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

    def test_query_scheme_or_fragment_tamper_is_rejected(self) -> None:
        url = next(iter(target.ALLOWED_URLS))
        for altered in (url + "#x", url.replace("https://", "http://"), url + "?x=1"):
            with self.assertRaises(ValueError):
                target._validate_url(altered)


if __name__ == "__main__":
    unittest.main()
