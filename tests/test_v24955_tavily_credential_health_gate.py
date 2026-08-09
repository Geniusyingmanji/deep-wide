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

from scripts import v24955_tavily_credential_health_gate as gate  # noqa: E402


class V24955TavilyCredentialHealthTests(unittest.TestCase):
    def test_protocol_is_strict_and_authorizes_no_benchmark(self) -> None:
        value = gate.build_protocol(now=1, require_clean=False, require_pristine=False)
        self.assertEqual(value["schedule"]["ephemeral_key_count"], 12)
        self.assertEqual(value["gates"]["healthy_key_count"], 12)
        self.assertEqual(value["gates"]["status_432"], 0)
        self.assertFalse(value["authorization"]["external_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_credentials_remain_ephemeral(self) -> None:
        values = tuple(f"ephemeral-neutral-{index:02d}" for index in range(12))
        self.assertEqual(gate.ephemeral_credentials(io.StringIO("\n".join(values))), values)
        with self.assertRaises(RuntimeError):
            gate.ephemeral_credentials(io.StringIO("short\n"))

    def test_aggregate_contains_no_per_key_or_content_surface(self) -> None:
        rows = [{
            "healthy": True, "status_2xx": 1, "status_401": 0,
            "status_403": 0, "status_429": 0, "status_432": 0,
            "status_other": 0, "transport_failures": 0,
            "slot_timeouts": 0, "credential_echo_rejections": 0,
        } for _ in range(12)]
        value = gate._aggregate(rows)
        self.assertEqual(value["healthy_key_count"], 12)
        self.assertFalse(value["contains_credential_value_or_hash"])
        self.assertFalse(value["contains_per_key_rows"])
        self.assertFalse(value["contains_query_url_title_snippet_page_answer_or_provider_payload"])

    def test_runtime_source_has_no_evaluator_import_or_secret_literal(self) -> None:
        source = (ROOT / "scripts/v24955_tavily_credential_health_gate.py").read_text()
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertIsNone(gate.SECRET.search(source))


if __name__ == "__main__":
    unittest.main()
