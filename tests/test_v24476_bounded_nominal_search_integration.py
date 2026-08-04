from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent import v24468_total_wall_transport as transport  # noqa: E402
from deepwide_agent.v24459_proof_carrying_adaptive_entropy_support import (  # noqa: E402
    CERTIFICATE_NAME,
)
from deepwide_agent.v24470_bounded_adaptive_integration import (  # noqa: E402
    run_and_persist_stage_hooked_task,
)
from deepwide_agent.v24476_bounded_nominal_search_integration import (  # noqa: E402
    build_bounded_nominal_hard_total_wall_search,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import slots  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    IdentityModel,
    SEED,
    TASK,
)
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import (  # noqa: E402
    KNOWN_BASELINE,
)


MANIFEST = hashlib.sha256(b"v24476-local-validator-manifest").hexdigest()


def hosted_payload(call: int, queries: list[str]) -> dict:
    if call <= 2:
        prefix = "wavea" if call == 1 else "waveb"
        sources = [
            {
                "type": "web_source",
                "url": f"https://{prefix}{index}.example/item/{index}",
                "title": f"proposal {queries[(index - 1) % len(queries)]}",
            }
            for index in range(1, 9)
        ]
    else:
        sources = [
            {
                "type": "web_source",
                "url": "https://active-alpha.example/record",
                "title": "Alpha official Founding year",
            },
            {
                "type": "web_source",
                "url": "https://active-beta.example/record",
                "title": "Beta official Founding year",
            },
            {
                "type": "web_source",
                "url": "https://active-alpha-three.example/record",
                "title": "Alpha official history",
            },
            {
                "type": "web_source",
                "url": "https://active-alpha-four.example/record",
                "title": "Alpha official founding chronology",
            },
            {
                "type": "web_source",
                "url": "https://active-alpha-five.example/record",
                "title": "Alpha historical founding archive",
            },
        ]
    payload = {
        "id": f"response-{call}",
        "output": [
            {
                "type": "web_search_call",
                "id": f"call-{call}",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": list(queries),
                    "sources": sources,
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "[[QUERY Q0001]]\nsummary\n[[END Q0001]]\n",
                        "annotations": [],
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
    }
    return {
        "kind": "response",
        "status_code": 200,
        "retry_after": "",
        "payload": payload,
        "payload_is_object": True,
    }


class V24476BoundedNominalSearchIntegrationTests(unittest.TestCase):
    def test_full_frozen_chain_succeeds_with_hard_request_and_certificate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            directory.mkdir()
            clock = AdvancingClock()
            deadline = 300.0
            model = build_deadline_model(
                url="http://127.0.0.1:9/responses",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=70,
                max_retries=1,
                slot_directory=slots(output_root),
                output_root=output_root,
                slot_cap=2,
                pool_id=POOL_ID,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=5,
                minimum_attempt_seconds=0.01,
                monotonic=clock,
                sleeper=clock.sleep,
                inner=IdentityModel(baseline=KNOWN_BASELINE),
            )
            model.inner.timeout = 70
            events: list[str] = []
            search = build_bounded_nominal_hard_total_wall_search(
                url="http://127.0.0.1:9/responses",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=70,
                max_retries=1,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=5,
                minimum_attempt_seconds=0.01,
                stage_callback=events.append,
                fetch_pages=False,
                max_workers=1,
                fetch_workers=1,
                monotonic=clock,
                sleeper=clock.sleep,
            )
            search.fetch_invocations = 0

            def fake_fetch(instance, requests_):
                instance.fetch_invocations += 1
                requested = list(requests_)
                instance._increment("fetch_calls", len(requested))
                instance._increment("hard_fetch_helper_calls", len(requested))
                content = (
                    "The product was founded in 2025 and later expanded."
                    if instance.fetch_invocations >= 3
                    else "The product publishes documentation and software."
                )
                return [
                    {
                        "query": "synthetic",
                        "results": [
                            {
                                "url": item["url"],
                                "requested_url": item["url"],
                                "title": item["title"],
                                "raw_content": content,
                            }
                        ],
                    }
                    for item in requested
                ]

            search.fetch_urls = types.MethodType(fake_fetch, search)
            request_count = 0

            def local_post(*, body, **_kwargs):
                nonlocal request_count
                request_count += 1
                del body
                # The exact visible queries are intentionally not persisted;
                # the synthetic response only needs stable section markers.
                return hosted_payload(request_count, ["synthetic"])

            with patch.object(transport, "run_total_wall_post", side_effect=local_post):
                outcome = run_and_persist_stage_hooked_task(
                    TASK,
                    model_factory=lambda: model,
                    search_factory=lambda: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    directory=directory,
                    writer=lambda name, value: _new_json(directory / name, value),
                    validator_manifest_sha256=MANIFEST,
                    stage_callback=events.append,
                )

            receipt = outcome.adaptive_result["adaptive_support_receipt"]
            self.assertEqual(request_count, 3)
            self.assertEqual(search.hosted_search_attempts, 3)
            self.assertEqual(search.calls, 3)
            self.assertEqual(search.recursive_split_requests, 0)
            self.assertEqual(model.acquisitions, 2)
            self.assertEqual(receipt["safe_change_count"], 1, receipt)
            self.assertGreater(receipt["final_decision_credit_total_nats"], 0)
            self.assertTrue((directory / CERTIFICATE_NAME).is_file())
            self.assertIn("complete_validation_returned", events)
            self.assertIn("certificate_persistence_entered", events)
            self.assertEqual(
                events.count("hosted_search_effect_started"),
                events.count("hosted_search_effect_finished"),
            )
            encoded = json.dumps(
                {
                    "model": outcome.model_slot_receipt,
                    "transport": outcome.transport_health,
                    "search": outcome.search_single_shot_receipt,
                },
                sort_keys=True,
            )
            self.assertNotIn(TASK["question"], encoded)
            self.assertNotIn(TASK["opaque_id"], encoded)

    def test_factory_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24476_bounded_nominal_search_integration.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
