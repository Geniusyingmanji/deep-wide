from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from deepwide_agent.v24275_hard_deadline_fetch import (
    HardDeadlineNativeSearchClient,
    validate_fetch_result,
)


class V24275HardDeadlineFetchTests(unittest.TestCase):
    def test_url_is_stdin_only_and_valid_result_is_counted(self) -> None:
        calls: list[tuple[list[str], dict]] = []

        class Process:
            pid = 123456789
            returncode = 0

            def communicate(self, value, timeout=None):
                self.input = value
                self.timeout = timeout
                return (
                    '{"status":"ok","url":"https://example.com/final",'
                    '"title":"Title","text":"page body","links":[]}',
                    None,
                )

        process = Process()

        def popen(command, **kwargs):
            calls.append((list(command), dict(kwargs)))
            return process

        client = HardDeadlineNativeSearchClient(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            hard_fetch_deadline_seconds=25,
            popen=popen,
        )
        source = "https://example.com/private-path"
        result = client._fetch_url(source)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(client.fetch_calls, 1)
        self.assertEqual(client.hard_fetch_helper_calls, 1)
        self.assertEqual(client.fetch_failures, 0)
        self.assertNotIn(source, "\n".join(calls[0][0]))
        self.assertIn(source, process.input)
        self.assertEqual(process.timeout, 25)
        self.assertTrue(calls[0][1]["start_new_session"])

    def test_timeout_is_one_total_deadline_and_kills_process_group(self) -> None:
        class Process:
            pid = 123456789
            returncode = None

            def communicate(self, value, timeout=None):
                raise subprocess.TimeoutExpired("helper", timeout)

            def wait(self, timeout=None):
                self.returncode = -15
                return self.returncode

        client = HardDeadlineNativeSearchClient(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            hard_fetch_deadline_seconds=25,
            popen=lambda *args, **kwargs: Process(),
        )
        with mock.patch("os.killpg") as killpg:
            result = client._fetch_url("https://example.com/slow")
        self.assertEqual(result["status"], "hard_deadline_exceeded")
        self.assertEqual(client.fetch_calls, 1)
        self.assertEqual(client.fetch_failures, 1)
        self.assertEqual(client.hard_fetch_deadline_failures, 1)
        killpg.assert_called_once()

    def test_result_schema_rejects_oversize_or_extra_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_fetch_result(
                {
                    "status": "ok",
                    "url": "https://example.com",
                    "title": "Title",
                    "text": "x" * 5001,
                    "links": [],
                }
            )
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_fetch_result(
                {
                    "status": "ok",
                    "url": "https://example.com",
                    "title": "Title",
                    "text": "body",
                    "links": [],
                    "prediction": "forbidden",
                }
            )


if __name__ == "__main__":
    unittest.main()
