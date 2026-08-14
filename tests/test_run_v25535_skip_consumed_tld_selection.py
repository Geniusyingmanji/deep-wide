from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v25535_skip_consumed_tld_selection as target  # noqa: E402
from test_v25534_skip_consumed_tld_selection import skip_fixture  # noqa: E402


class Response:
    def __init__(self, *, status: int = 200, url: str | None = None) -> None:
        self.status_code = status
        self.url = url or target.contract.OFFICIAL_ENDPOINT
        self.encoding = "utf-8"
        self.content = skip_fixture().encode()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class V25535SkipConsumedTldSelectionRunnerTests(unittest.TestCase):
    def test_fetch_is_one_exact_redirect_disabled_name_list_request(self) -> None:
        calls = []

        def get(url: str, **kwargs):
            calls.append((url, kwargs))
            return Response()

        raw, status, final_url, encoding = target.fetch_name_list(get=get)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], target.contract.OFFICIAL_ENDPOINT)
        self.assertFalse(calls[0][1]["allow_redirects"])
        self.assertEqual(status, 200)
        self.assertEqual(final_url, target.contract.OFFICIAL_ENDPOINT)
        self.assertEqual(encoding, "utf-8")
        self.assertTrue(raw.startswith(b"# Version "))

    def test_snapshot_records_skipped_consumed_and_selected_pairs(self) -> None:
        value = target.build_snapshot(
            skip_fixture().encode(),
            status=200,
            final_url=target.contract.OFFICIAL_ENDPOINT,
            encoding="utf-8",
            now=1,
            head="a" * 40,
        )
        self.assertEqual(target.validate_snapshot(value), value)
        selection = value["selection"]
        self.assertEqual(selection["selected_identity_count"], 40)
        self.assertEqual(selection["pair_count"], 20)
        self.assertEqual(selection["consumed_identity_overlap_count"], 0)
        self.assertEqual(selection["skipped_consumed_identity_count"], 7)
        self.assertEqual(selection["scanned_suffix_identity_count"], 47)
        self.assertTrue(selection["first_forty_unconsumed_in_official_order"])
        self.assertFalse(
            value["effect_receipt"][
                "v25533_old_name_list_attempt_retried_or_reused"
            ]
        )

    def test_http_redirect_or_status_failure_is_single_attempt(self) -> None:
        for response in (
            Response(status=503),
            Response(url="https://example.invalid/list.txt"),
        ):
            calls = 0

            def get(_url: str, **_kwargs):
                nonlocal calls
                calls += 1
                return response

            with self.subTest(response=response), self.assertRaises(RuntimeError):
                target.fetch_name_list(get=get)
            self.assertEqual(calls, 1)

    def test_resealed_selection_effect_or_launch_tamper_fails(self) -> None:
        value = target.build_snapshot(
            skip_fixture().encode(),
            status=200,
            final_url=target.contract.OFFICIAL_ENDPOINT,
            encoding="utf-8",
            now=1,
        )
        for kind in ("selection", "effect", "launch"):
            changed = copy.deepcopy(value)
            if kind == "selection":
                changed["selection"]["selected_identities"][0] = ".bank"
            elif kind == "effect":
                changed["effect_receipt"]["ordinary_public_https_get_count"] = 2
            else:
                changed["authorization"]["deepwidebench_forward_or_evaluator"] = True
            changed.pop("snapshot_payload_sha256")
            changed["snapshot_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_snapshot(changed)


if __name__ == "__main__":
    unittest.main()
