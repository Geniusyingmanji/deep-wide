from __future__ import annotations

import ast
import concurrent.futures
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    GATE_BASENAME,
    RateAwareDeadlineTavilyThinCompatibilityClient,
    empty_rate_aware_receipt,
    prepare_rate_aware_key_slots,
    validate_receipt,
    validate_search_class,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


def response(
    status: int, payload: dict | None = None, *, retry_after: str | None = None
) -> Mock:
    value = Mock()
    value.status_code = status
    value.json.return_value = payload or {}
    value.headers = {} if retry_after is None else {"Retry-After": retry_after}
    return value


def success(label: str = "a") -> Mock:
    return response(
        200,
        {
            "results": [
                {
                    "title": label,
                    "url": f"https://{label}.example/page",
                    "content": "discarded",
                    "score": 1.0,
                }
            ]
        },
    )


class V24852RateAwareTavilyTests(unittest.TestCase):
    def client(
        self,
        directory: Path,
        post,
        *,
        keys: tuple[str, ...] = ("secret-one", "secret-two"),
        interval: float = 0.003,
        cooldown: float = 0.01,
        attempts: int = 2,
    ) -> RateAwareDeadlineTavilyThinCompatibilityClient:
        return RateAwareDeadlineTavilyThinCompatibilityClient(
            "http://127.0.0.1:9878/responses",
            "gpt-5.6-sol",
            timeout=5,
            max_retries=2,
            fetch_pages=False,
            fetch_workers=1,
            fetch_timeout=20,
            max_page_chars=5000,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=time.monotonic() + 10,
            cleanup_reserve_seconds=0.01,
            minimum_attempt_seconds=0.01,
            credentials=keys,
            key_slot_directory=directory,
            output_root=directory.parent,
            direct_timeout_seconds=5,
            direct_workers=2,
            direct_post=post,
            provider_attempt_cap=attempts,
            minimum_start_interval_seconds=interval,
            default_provider_cooldown_seconds=cooldown,
            maximum_provider_cooldown_seconds=max(cooldown, 0.05),
            provider_gate_poll_seconds=0.001,
            slot_poll_seconds=0.001,
        )

    def test_append_only_class_and_create_only_provider_gate(self) -> None:
        validate_search_class()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            path = Path(raw) / "slots"
            prepare_rate_aware_key_slots(path, 2)
            self.assertTrue((path / GATE_BASENAME).is_file())
            with self.assertRaises(FileExistsError):
                prepare_rate_aware_key_slots(path, 2)

    def test_empty_rate_receipt_is_valid_and_content_free(self) -> None:
        value = empty_rate_aware_receipt()
        self.assertEqual(value["provider_start_reservations"], 0)
        self.assertEqual(value["provider_429_responses"], 0)
        self.assertFalse(
            value["credential_value_persisted_hashed_emitted_or_in_error"]
        )

    def test_success_keeps_header_only_projection(self) -> None:
        post = Mock(return_value=success())
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_rate_aware_key_slots(slots, 2)
            client = self.client(slots, post)
            batch = client.search_many(
                ["neutral query"], max_results=3, include_raw_content=False
            )[0]
            direct = client.direct_search_receipt()
            rate = client.rate_aware_search_receipt()
        self.assertEqual(len(batch["results"]), 1)
        self.assertEqual(batch["results"][0]["content"], "")
        self.assertEqual(batch["results"][0]["raw_content"], "")
        self.assertIsNone(batch["results"][0]["score"])
        self.assertEqual(post.call_count, 1)
        self.assertEqual(direct["provider_attempts"], 1)
        self.assertEqual(rate["provider_start_reservations"], 1)

    def test_one_429_waits_then_recovers_without_full_key_rotation(self) -> None:
        post = Mock(side_effect=[response(429, retry_after="0.02"), success("b")])
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_rate_aware_key_slots(slots, 12)
            client = self.client(
                slots,
                post,
                keys=tuple(f"secret-{index:02d}" for index in range(12)),
                cooldown=0.01,
            )
            started = time.monotonic()
            batch = client.search_many(
                ["neutral query"], max_results=3, include_raw_content=False
            )[0]
            elapsed = time.monotonic() - started
            direct = client.direct_search_receipt()
            rate = client.rate_aware_search_receipt()
        self.assertEqual(len(batch["results"]), 1)
        self.assertEqual(post.call_count, 2)
        self.assertGreaterEqual(elapsed, 0.018)
        self.assertEqual(direct["status_429"], 1)
        self.assertEqual(rate["provider_429_responses"], 1)
        self.assertEqual(rate["provider_cooldown_activations"], 1)
        self.assertEqual(rate["retry_after_values_honored"], 1)

    def test_persistent_429_is_capped_at_two_not_twelve_attempts(self) -> None:
        post = Mock(return_value=response(429))
        keys = tuple(f"secret-{index:02d}" for index in range(12))
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_rate_aware_key_slots(slots, len(keys))
            client = self.client(slots, post, keys=keys)
            batch = client.search_many(
                ["neutral query"], max_results=3, include_raw_content=False
            )[0]
            direct = client.direct_search_receipt()
            rate = client.rate_aware_search_receipt()
        self.assertEqual(batch["results"], [])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(direct["provider_attempts"], 2)
        self.assertEqual(direct["status_429"], 2)
        self.assertEqual(direct["failed_queries"], 1)
        self.assertEqual(
            rate["provider_non_key_local_attempt_cap_per_logical_query"], 2
        )
        self.assertFalse(rate["provider_wide_429_rotates_all_keys_immediately"])

    def test_shared_provider_gate_paces_concurrent_process_clients(self) -> None:
        starts: list[float] = []
        lock = threading.Lock()

        def post(*_args, **_kwargs):
            with lock:
                starts.append(time.monotonic())
                label = f"p{len(starts)}"
            return success(label)

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            keys = tuple(f"secret-{index:02d}" for index in range(4))
            prepare_rate_aware_key_slots(slots, len(keys))
            clients = [
                self.client(slots, post, keys=keys, interval=0.02)
                for _ in range(4)
            ]
            started = time.monotonic()
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                batches = list(
                    pool.map(
                        lambda pair: pair[0].search_many(
                            [f"neutral query {pair[1]}"],
                            max_results=3,
                            include_raw_content=False,
                        )[0],
                        zip(clients, range(4)),
                    )
                )
            elapsed = time.monotonic() - started
            gate = json.loads(
                (slots / GATE_BASENAME).read_text(encoding="utf-8")
            )
        self.assertEqual(sum(bool(batch["results"]) for batch in batches), 4)
        ordered = sorted(starts)
        self.assertEqual(len(ordered), 4)
        self.assertEqual(gate["generation"], 4)
        self.assertGreaterEqual(elapsed, 0.05)
        self.assertEqual(
            sum(
                client.rate_aware_search_receipt()["provider_start_reservations"]
                for client in clients
            ),
            4,
        )

    def test_key_local_quota_status_remains_local(self) -> None:
        post = Mock(side_effect=[response(432), success("next")])
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_rate_aware_key_slots(slots, 2)
            client = self.client(slots, post)
            batch = client.search_many(
                ["neutral query"], max_results=3, include_raw_content=False
            )[0]
            direct = client.direct_search_receipt()
            rate = client.rate_aware_search_receipt()
            stored = "\n".join(
                path.read_text(encoding="utf-8") for path in slots.iterdir()
            )
        self.assertEqual(len(batch["results"]), 1)
        self.assertEqual(direct["key_local_disables"], 1)
        self.assertTrue(rate["credential_local_statuses_remain_key_local"])
        self.assertNotIn("secret-one", stored)
        self.assertNotIn("secret-two", stored)

    def test_key_local_failures_do_not_consume_provider_attempt_cap(self) -> None:
        post = Mock(
            side_effect=[response(432), response(401), response(403), success("live")]
        )
        keys = tuple(f"secret-{index:02d}" for index in range(4))
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_rate_aware_key_slots(slots, len(keys))
            client = self.client(slots, post, keys=keys, attempts=2)
            batch = client.search_many(
                ["neutral query"], max_results=3, include_raw_content=False
            )[0]
            direct = client.direct_search_receipt()
        self.assertEqual(len(batch["results"]), 1)
        self.assertEqual(post.call_count, 4)
        self.assertEqual(direct["key_local_disables"], 3)
        self.assertEqual(direct["status_429"], 0)

    def test_receipt_is_content_free_and_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_rate_aware_key_slots(slots, 2)
            receipt = self.client(slots, Mock(return_value=success())).rate_aware_search_receipt()
        validate_receipt(receipt)
        encoded = json.dumps(receipt)
        self.assertNotIn("secret-one", encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
        )
        changed = dict(receipt)
        changed["provider_wide_429_rotates_all_keys_immediately"] = True
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = __import__(
            "deepwide_agent.v24852_rate_aware_tavily_search",
            fromlist=["payload_sha256"],
        ).payload_sha256(changed)
        with self.assertRaises(ValueError):
            validate_receipt(changed)

    def test_invalid_or_symlink_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            slots = Path(raw) / "slots"
            prepare_rate_aware_key_slots(slots, 2)
            gate = slots / GATE_BASENAME
            gate.unlink()
            gate.symlink_to(slots / "slot_01.lock")
            with self.assertRaises(ValueError):
                self.client(slots, Mock(return_value=success()))

    def test_runtime_source_has_no_privileged_or_evaluator_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24852_rate_aware_tavily_search.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertEqual(semantic_audit._accesses(path, ROOT), [])
        self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])


if __name__ == "__main__":
    unittest.main()
