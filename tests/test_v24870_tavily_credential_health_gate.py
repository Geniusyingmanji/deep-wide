from __future__ import annotations

import ast
import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24870_tavily_credential_health_gate as gate  # noqa: E402


class V24870TavilyCredentialHealthGateTests(unittest.TestCase):
    def test_protocol_is_per_key_neutral_and_authorizes_no_benchmark(self) -> None:
        value = gate.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )
        self.assertEqual(value["schedule"]["ephemeral_key_count"], 12)
        self.assertEqual(value["schedule"]["executor_concurrency"], 12)
        self.assertEqual(value["schedule"]["attempts_per_key"], 1)
        self.assertTrue(
            value["schedule"]["every_key_isolated_in_own_one_slot_client"]
        )
        self.assertFalse(value["authorization"]["external_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(
            value["supersedes_pre_effect_invalid_protocol"][
                "network_provider_search_fetch_model_or_evaluator_effect"
            ]
        )
        self.assertFalse(
            value["supersedes_pre_effect_invalid_protocol"][
                "credential_health_conclusion_drawn"
            ]
        )

    def test_credentials_are_exactly_twelve_distinct_ephemeral_lines(self) -> None:
        values = tuple(f"neutral-secret-{index:02d}" for index in range(12))
        self.assertEqual(
            gate.ephemeral_credentials(io.StringIO("\n".join(values))), values
        )
        with self.assertRaises(RuntimeError):
            gate.ephemeral_credentials(io.StringIO("one\n"))

    def test_aggregate_has_no_per_key_identity_or_private_content(self) -> None:
        rows = [
            {
                "healthy": True,
                "status_2xx": 1,
                "status_401": 0,
                "status_403": 0,
                "status_432": 0,
                "status_429": 0,
                "status_other": 0,
                "transport_failures": 0,
                "slot_timeouts": 0,
                "credential_echo_rejections": 0,
            }
            for _ in range(12)
        ]
        value = gate._aggregate(rows)
        self.assertEqual(value["healthy_key_count"], 12)
        self.assertFalse(value["contains_credential_value_or_hash"])
        self.assertFalse(value["contains_per_key_rows"])
        self.assertFalse(
            value[
                "contains_query_url_title_snippet_page_answer_or_provider_payload"
            ]
        )

    def test_source_has_no_evaluator_or_benchmark_data_access(self) -> None:
        source = (ROOT / "scripts/v24870_tavily_credential_health_gate.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertNotIn("mapping", {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)})


if __name__ == "__main__":
    unittest.main()
