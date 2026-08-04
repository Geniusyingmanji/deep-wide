from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import SearchRequestError  # noqa: E402
from deepwide_agent.v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    UncertaintyDeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    build_effect_timeout_contract,
)
from deepwide_agent import v24468_total_wall_transport as transport  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallNativeSearchClient,
)
from deepwide_agent.v24470_bounded_adaptive_integration import (  # noqa: E402
    HardTotalWallUncertaintyNativeSearchClient,
    build_hard_total_wall_model,
)
from deepwide_agent.v24474_nominal_hard_total_wall_search import (  # noqa: E402
    NominalCompatibleHardTotalWallUncertaintyNativeSearchClient,
    build_nominal_compatible_hard_total_wall_search,
    validate_compatibility_class,
)


def response_payload() -> dict:
    return {
        "kind": "response",
        "status_code": 200,
        "retry_after": "",
        "payload_is_object": True,
        "payload": {
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
    }


def build_search(*, deadline: float, events: list[str]):
    return build_nominal_compatible_hard_total_wall_search(
        url="http://127.0.0.1:9/responses",
        model_name="synthetic",
        reasoning_effort="low",
        service_tier="",
        static_timeout_seconds=70,
        max_retries=1,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.05,
        stage_callback=events.append,
        fetch_pages=False,
    )


class V24474NominalHardTotalWallSearchTests(unittest.TestCase):
    def test_compatibility_mro_preserves_hard_request_and_task_union(self) -> None:
        validate_compatibility_class()
        cls = NominalCompatibleHardTotalWallUncertaintyNativeSearchClient
        self.assertTrue(issubclass(cls, HardTotalWallUncertaintyNativeSearchClient))
        self.assertTrue(issubclass(cls, UncertaintyDeadlineAwareNativeSearchClient))
        request_owner = next(base for base in cls.__mro__ if "_request" in base.__dict__)
        chunk_owner = next(base for base in cls.__mro__ if "_run_chunk" in base.__dict__)
        self.assertIs(request_owner, HardTotalWallNativeSearchClient)
        self.assertEqual(chunk_owner.__name__, "TaskUnionSingleShotMixin")

    def test_factory_builds_both_nominal_and_hard_type(self) -> None:
        deadline = time.monotonic() + 150
        client = build_search(deadline=deadline, events=[])
        self.assertIsInstance(client, UncertaintyDeadlineAwareNativeSearchClient)
        self.assertIsInstance(client, HardTotalWallUncertaintyNativeSearchClient)
        self.assertEqual(client.absolute_deadline, deadline)
        self.assertEqual(client.hosted_search_attempts, 0)
        self.assertEqual(client.multi_query_chunks, 0)

    def test_frozen_v24438_timeout_contract_accepts_compatible_client(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in (1, 2):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            deadline = time.monotonic() + 150
            model = build_hard_total_wall_model(
                url="http://127.0.0.1:9/responses",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=70,
                max_retries=1,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=2,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=5,
                minimum_attempt_seconds=0.05,
                stage_callback=lambda _stage: None,
            )
            search = build_search(deadline=deadline, events=[])
            value = build_effect_timeout_contract(model, search)
        self.assertTrue(value["model_and_search_share_absolute_deadline"])
        self.assertEqual(value["model_provider_timeout_seconds"], 70)
        self.assertEqual(value["hosted_search_timeout_seconds"], 70)
        self.assertEqual(model.receipt()["acquisitions"], 0)
        self.assertEqual(search.transport_health()["hosted_search_attempts"], 0)

    def test_request_path_uses_hard_total_wall_function_and_callbacks(self) -> None:
        events: list[str] = []
        client = build_search(deadline=time.monotonic() + 150, events=events)
        with patch.object(
            transport, "run_total_wall_post", return_value=response_payload()
        ) as request:
            payload = client._request(["synthetic"])
        self.assertEqual(payload["id"], "synthetic")
        self.assertEqual(
            events,
            ["hosted_search_effect_started", "hosted_search_effect_finished"],
        )
        self.assertEqual(request.call_count, 1)
        self.assertEqual(client.hosted_search_attempts, 1)
        self.assertEqual(client.calls, 1)
        self.assertEqual(client.total_tokens, 6)

    def test_hard_total_wall_timeout_remains_terminal_and_observable(self) -> None:
        events: list[str] = []
        client = build_search(deadline=time.monotonic() + 150, events=events)
        timeout = {
            "kind": "hard_total_wall_timeout",
            "status_code": None,
            "retry_after": "",
            "payload": None,
            "payload_is_object": False,
        }
        with patch.object(transport, "run_total_wall_post", return_value=timeout):
            with self.assertRaises(SearchRequestError):
                client._request(["synthetic"])
        health = client.transport_health()
        self.assertEqual(client.hard_total_wall_timeouts, 1)
        self.assertEqual(health["hosted_search_attempts"], 1)
        self.assertEqual(health["hosted_search_deadline_failures"], 1)
        self.assertEqual(
            events,
            ["hosted_search_effect_started", "hosted_search_effect_finished"],
        )

    def test_receipts_remain_content_free_after_synthetic_effect(self) -> None:
        client = build_search(deadline=time.monotonic() + 150, events=[])
        with patch.object(
            transport, "run_total_wall_post", return_value=response_payload()
        ):
            client._request(["private synthetic query"])
        encoded = json.dumps(
            {
                "transport": client.transport_health(),
                "single_shot": client.single_shot_receipt(),
            },
            sort_keys=True,
        )
        self.assertNotIn("private synthetic query", encoded)
        self.assertNotIn("http://127.0.0.1:9", encoded)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24474_nominal_hard_total_wall_search.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
