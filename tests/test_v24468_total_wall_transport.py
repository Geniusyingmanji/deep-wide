from __future__ import annotations

import json
import os
import socketserver
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError, SearchRequestError  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallNativeSearchClient,
    HardTotalWallResponsesClient,
    run_total_wall_post,
)


def model_payload() -> bytes:
    return json.dumps(
        {
            "id": "synthetic",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "ok"}],
                }
            ],
            "usage": {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
        },
        separators=(",", ":"),
    ).encode()


def search_payload() -> bytes:
    return json.dumps(
        {
            "id": "synthetic",
            "output": [
                {
                    "type": "web_search_call",
                    "id": "search",
                    "status": "completed",
                    "action": {
                        "type": "search",
                        "query": "synthetic",
                        "sources": [],
                    },
                }
            ],
            "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
        },
        separators=(",", ":"),
    ).encode()


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class TotalWallServer:
    def __init__(self, *, drip_seconds: float = 0.0) -> None:
        self.drip_seconds = drip_seconds
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                body = model_payload() if self.path == "/model" else search_payload()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if outer.drip_seconds:
                    for byte in body:
                        try:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            break
                        time.sleep(outer.drip_seconds)
                else:
                    self.wfile.write(body)
                    self.wfile.flush()

            def log_message(self, *_: object) -> None:
                return None

        self.server = Server(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> "TotalWallServer":
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()


def model(url: str, *, deadline_seconds: float) -> HardTotalWallResponsesClient:
    return HardTotalWallResponsesClient(
        url,
        "synthetic",
        timeout=10,
        max_retries=1,
        absolute_deadline=time.monotonic() + deadline_seconds,
        cleanup_reserve_seconds=0.10,
        minimum_attempt_seconds=0.01,
    )


def search(url: str, *, deadline_seconds: float) -> HardTotalWallNativeSearchClient:
    return HardTotalWallNativeSearchClient(
        url,
        "synthetic",
        timeout=10,
        max_retries=1,
        fetch_pages=False,
        max_workers=1,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=time.monotonic() + deadline_seconds,
        cleanup_reserve_seconds=0.10,
        minimum_attempt_seconds=0.01,
    )


class V24468TotalWallTransportTests(unittest.TestCase):
    def test_fast_model_and_search_preserve_payload_and_counters(self) -> None:
        with TotalWallServer() as server:
            model_client = model(server.base_url + "/model", deadline_seconds=2)
            result = model_client.complete("s", "u", max_output_tokens=1)
            search_client = search(server.base_url + "/search", deadline_seconds=2)
            payload = search_client._request(["synthetic"])
        self.assertEqual(result.text, "ok")
        self.assertEqual(model_client.requests, 1)
        self.assertEqual(model_client.attempts, 1)
        self.assertEqual(model_client.calls, 1)
        self.assertEqual(model_client.total_tokens, 3)
        self.assertEqual(model_client.hard_total_wall_timeouts, 0)
        self.assertEqual(payload["id"], "synthetic")
        self.assertEqual(search_client.calls, 1)
        self.assertEqual(search_client.hosted_search_attempts, 1)
        self.assertEqual(search_client.total_tokens, 6)
        self.assertEqual(search_client.hard_total_wall_timeouts, 0)

    def test_slow_drip_model_is_killed_before_absolute_deadline(self) -> None:
        with TotalWallServer(drip_seconds=0.012) as server:
            client = model(server.base_url + "/model", deadline_seconds=0.35)
            started = time.monotonic()
            with self.assertRaises(ModelRequestError) as raised:
                client.complete("private-system", "private-user", max_output_tokens=1)
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.45)
        self.assertEqual(client.hard_total_wall_timeouts, 1)
        self.assertEqual(client.deadline_failures, 1)
        self.assertEqual(
            raised.exception.model_traces[0]["error_type"],
            "task_deadline_exhausted",
        )
        self.assertNotIn("private", json.dumps(raised.exception.model_traces))

    def test_slow_drip_search_is_killed_before_absolute_deadline(self) -> None:
        with TotalWallServer(drip_seconds=0.012) as server:
            client = search(server.base_url + "/search", deadline_seconds=0.35)
            started = time.monotonic()
            with self.assertRaises(SearchRequestError):
                client._request(["private query"])
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.45)
        self.assertEqual(client.hard_total_wall_timeouts, 1)
        self.assertEqual(client.hosted_search_deadline_failures, 1)
        self.assertTrue(client.transport_health()["deadline_exhausted"])

    def test_repeated_timeout_does_not_leak_file_descriptors(self) -> None:
        before = len(os.listdir("/proc/self/fd"))
        with TotalWallServer(drip_seconds=0.012) as server:
            for _ in range(3):
                client = model(server.base_url + "/model", deadline_seconds=0.25)
                with self.assertRaises(ModelRequestError):
                    client.complete("s", "u", max_output_tokens=1)
        after = len(os.listdir("/proc/self/fd"))
        self.assertLessEqual(after, before + 1)

    def test_helper_rejects_non_loopback_endpoint_without_request(self) -> None:
        value = run_total_wall_post(
            url="https://example.com/private",
            body={"secret": "never-sent"},
            timeout_seconds=1,
            static_socket_timeout_seconds=1,
        )
        self.assertEqual(value["kind"], "invalid_input_or_payload")
        self.assertIsNone(value["payload"])

    def test_helper_does_not_follow_redirects(self) -> None:
        target_calls = 0

        class TargetHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                nonlocal target_calls
                target_calls += 1
                self.send_response(204)
                self.end_headers()

            def log_message(self, *_: object) -> None:
                return None

        with Server(("127.0.0.1", 0), TargetHandler) as target:
            target_thread = threading.Thread(target=target.serve_forever, daemon=True)
            target_thread.start()
            target_url = f"http://127.0.0.1:{target.server_address[1]}/sink"

            class RedirectHandler(BaseHTTPRequestHandler):
                def do_POST(self) -> None:  # noqa: N802
                    length = int(self.headers.get("Content-Length", "0"))
                    self.rfile.read(length)
                    self.send_response(307)
                    self.send_header("Location", target_url)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

                def log_message(self, *_: object) -> None:
                    return None

            with Server(("127.0.0.1", 0), RedirectHandler) as redirect:
                redirect_thread = threading.Thread(
                    target=redirect.serve_forever, daemon=True
                )
                redirect_thread.start()
                value = run_total_wall_post(
                    url=f"http://127.0.0.1:{redirect.server_address[1]}/redirect",
                    body={"private": "pipe-only"},
                    timeout_seconds=1,
                    static_socket_timeout_seconds=1,
                )
                redirect.shutdown()
                redirect_thread.join(timeout=2)
            target.shutdown()
            target_thread.join(timeout=2)
        self.assertEqual(value["kind"], "response")
        self.assertEqual(value["status_code"], 307)
        self.assertEqual(target_calls, 0)

    def test_total_wall_is_recomputed_after_helper_launch(self) -> None:
        class Process:
            pid = 99_999_999
            returncode = None
            stdin = stdout = stderr = None
            observed_timeout = None

            def communicate(self, _request, timeout=None):
                self.observed_timeout = timeout
                raise subprocess.TimeoutExpired("helper", timeout)

            def terminate(self):
                self.returncode = -15

            def kill(self):
                self.returncode = -9

            def wait(self, timeout=None):
                del timeout
                return self.returncode

        process = Process()

        def launch(*_args, **_kwargs):
            time.sleep(0.08)
            return process

        value = run_total_wall_post(
            url="http://127.0.0.1:9/responses",
            body={"synthetic": True},
            timeout_seconds=0.20,
            static_socket_timeout_seconds=1,
            popen=launch,
        )
        self.assertEqual(value["kind"], "hard_total_wall_timeout")
        self.assertIsNotNone(process.observed_timeout)
        self.assertLess(process.observed_timeout, 0.15)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24465_single_validation_adaptive_build as audit

        accesses, imports = audit.base._ast_findings(
            Path("src/deepwide_agent/v24468_total_wall_transport.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
