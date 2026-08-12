from __future__ import annotations

import copy
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24984_robust_late_page_projection as projection  # noqa: E402
from deepwide_agent import v25155_projection_structure_observer as observer  # noqa: E402
from deepwide_agent.v25155_projection_structure_observer_fetch import (  # noqa: E402
    HELPER,
    ProjectionStructureObservedSearchClient,
    validate_helper_result,
    validate_search_class,
)
from scripts import run_v25155_projection_structure_observer_fetch_helper as helper  # noqa: E402


QUESTION = "Return a table. Column names: Entity | Value"


class Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class Process:
    def __init__(self, payload: dict, *, returncode: int = 0) -> None:
        self.pid = 123456789
        self.returncode = returncode
        self.payload = payload
        self.command = None
        self.stdin_value = None

    def communicate(self, value: str, timeout: float | None = None):
        del timeout
        self.stdin_value = json.loads(value)
        return json.dumps(self.payload), ""

    def wait(self, timeout: float | None = None):
        del timeout
        return self.returncode


def observed_payload() -> dict:
    content = (
        "Entity | Value\nLate Entity | 999\n" + "padding " * 900
    )
    projected = projection.build_projection(
        QUESTION,
        {
            "title": "Official",
            "url": "https://official.example/data",
            "text": content,
        },
    )
    structure = observer.observe_structure(
        "<table><tr><th>Entity</th><th>Value</th></tr>"
        "<tr><td>Late Entity</td><td>999</td></tr></table>",
        content,
        projected["projection"],
    )
    return {
        "status": "ok",
        "url": "https://official.example/data",
        "title": "Official",
        "text": projected["projection"],
        "links": [],
        "projection_receipt": projected["content_free_receipt"],
        "parent_prefix": content[:5_000],
        "structure_observation": structure,
    }


def client(process: Process) -> ProjectionStructureObservedSearchClient:
    def launch(command, **kwargs):
        del kwargs
        process.command = command
        return process

    return ProjectionStructureObservedSearchClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        visible_question=QUESTION,
        timeout=65,
        max_retries=2,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=5_000,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=200.0,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        monotonic=Clock(),
        late_page_fetch_popen=launch,
    )


class V25155ProjectionStructureObserverFetchTests(unittest.TestCase):
    def test_observed_helper_result_is_forwarded_and_aggregated(self) -> None:
        process = Process(observed_payload())
        target = client(process)
        result = target._fetch_url("https://official.example/data")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(Path(process.command[-1]).resolve(), HELPER.resolve())
        self.assertEqual(process.stdin_value["question"], QUESTION)
        projection_receipt = target.late_page_projection_receipt()
        self.assertEqual(projection_receipt["projected_page_count"], 1)
        structure = target.projection_structure_observation_receipt()
        self.assertEqual(structure["counts"]["observed_page_count"], 1)
        self.assertEqual(structure["counts"]["raw_structured_page_count"], 1)
        self.assertEqual(
            structure["counts"]["projected_structured_page_count"], 1
        )
        self.assertFalse(structure["entropy_or_information_gain_assigns_signed_credit"])

    def test_invalid_or_missing_structure_receipt_fails_closed(self) -> None:
        missing = observed_payload()
        missing["structure_observation"] = None
        self.assertEqual(
            client(Process(missing))._fetch_url("https://official.example/data")[
                "status"
            ],
            "helper_invalid_result",
        )
        tampered = observed_payload()
        tampered["structure_observation"] = copy.deepcopy(
            tampered["structure_observation"]
        )
        tampered["structure_observation"]["benchmark_launch_or_evaluator_authorized"] = True
        with self.assertRaises(ValueError):
            validate_helper_result(tampered)

    def test_helper_nonzero_and_timeout_remain_bounded(self) -> None:
        nonzero = client(Process({}, returncode=2))
        self.assertEqual(
            nonzero._fetch_url("https://official.example/data")["status"],
            "helper_nonzero_exit",
        )

        class SlowProcess(Process):
            def communicate(self, value, timeout=None):
                del value
                raise subprocess.TimeoutExpired("helper", timeout)

        slow = client(SlowProcess({}))
        slow._terminate_group = lambda _process: None
        self.assertEqual(
            slow._fetch_url("https://official.example/data")["status"],
            "hard_deadline_exceeded",
        )

    def test_class_preserves_parent_effect_boundary(self) -> None:
        validate_search_class()
        self.assertTrue(HELPER.is_file())
        self.assertFalse(HELPER.is_symlink())

    def test_helper_builds_three_layer_receipt_in_one_fetch(self) -> None:
        class FakeClient:
            def __init__(self, *args, **kwargs) -> None:
                del args
                self.observer = kwargs["content_free_structure_observer"]

            def _fetch_url(self, url: str) -> dict:
                extracted = "Entity | Value\nLate Entity | 999"
                return {
                    "status": "ok",
                    "url": url,
                    "title": "Official",
                    "text": extracted,
                    "links": [],
                    "content_free_structure_receipt": self.observer(
                        "<table><tr><th>Entity</th><th>Value</th></tr>"
                        "<tr><td>Late Entity</td><td>999</td></tr></table>",
                        extracted,
                    ),
                }

        stdin = io.StringIO(
            json.dumps(
                {
                    "url": "https://official.example/data",
                    "question": QUESTION,
                }
            )
        )
        stdout = io.StringIO()
        with mock.patch.object(helper, "AzureNativeSearchClient", FakeClient), mock.patch.object(
            helper.sys, "stdin", stdin
        ), mock.patch.object(helper.sys, "stdout", stdout):
            helper.main()
        value = validate_helper_result(json.loads(stdout.getvalue()))
        self.assertEqual(value["status"], "ok")
        structure = value["structure_observation"]
        self.assertTrue(
            structure["transitions"]["raw_structured_surface_present"]
        )
        self.assertFalse(
            structure["entropy_or_information_gain_assigns_signed_credit"]
        )
        encoded = json.dumps(structure, ensure_ascii=False)
        self.assertNotIn("Late Entity", encoded)
        self.assertNotIn("999", encoded)


if __name__ == "__main__":
    unittest.main()
