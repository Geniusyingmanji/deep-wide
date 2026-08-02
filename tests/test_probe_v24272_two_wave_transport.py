from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from deepwide_agent.v24272_two_wave_entropy_voc import object_sha256  # noqa: E402
from scripts import probe_v24272_two_wave_transport as target  # noqa: E402
from test_v24272_two_wave_retrieval import Clock, FakeSearch  # noqa: E402
from deepwide_agent.v24272_two_wave_retrieval import run_two_wave_retrieval  # noqa: E402


def synthetic_result():
    client = FakeSearch()
    retrieval = run_two_wave_retrieval(
        target.NEUTRAL_QUERIES,
        search=client,
        required_column_count=3,
        monotonic=Clock(),
    )
    value = {
        "artifact_version": 1,
        "role": "v24272_neutral_two_wave_transport_probe",
        "created_at_unix": 1,
        "probe_scope": "neutral_public_documentation_transport_latency_only",
        "provider": "azure-native-keyless-batched",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "neutral_query_count": len(target.NEUTRAL_QUERIES),
        "wall_seconds": 1.0,
        "client_counters": {
            name: int(getattr(client, name, 0) or 0) for name in target.CLIENT_COUNTERS
        },
        "retrieval_receipt": retrieval["receipt"],
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "query_url_host_page_or_answer_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired": True,
        },
        "authorization": {
            "dev_benchmark_launch": False,
            "exact220_launch": False,
            "leaderboard_submission": False,
            "sota_claim": False,
            "training_credit_assignment": False,
        },
    }
    value["result_payload_sha256"] = object_sha256(value)
    return value


class ProbeV24272TwoWaveTransportTests(unittest.TestCase):
    def test_synthetic_content_free_result_validates(self):
        value = synthetic_result()
        target.validate_result(value)
        self.assertFalse(any(value["authorization"].values()))

    def test_resealed_source_policy_or_counter_tamper_is_rejected(self):
        value = synthetic_result()
        for mutation in ("source", "counter"):
            altered = copy.deepcopy(value)
            if mutation == "source":
                altered["source_policy"][
                    "benchmark_manifest_mapping_gold_prediction_or_evaluator_read"
                ] = True
            else:
                altered["client_counters"]["fetch_calls"] += 1
            unsigned = dict(altered)
            unsigned.pop("result_payload_sha256")
            altered["result_payload_sha256"] = object_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "probe"):
                target.validate_result(altered)

    def test_neutral_query_set_contains_no_benchmark_identifier_or_url(self):
        encoded = "\n".join(target.NEUTRAL_QUERIES)
        self.assertNotIn("task_", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)
        self.assertNotIn("DeepWide", encoded)


if __name__ == "__main__":
    unittest.main()
