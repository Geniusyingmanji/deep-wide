from __future__ import annotations

import ast
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24263_global_model_limiter as global_pool  # noqa: E402
from deepwide_agent import v25558_model_pool_contract as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402


class DummyModel:
    pass


class V25558ModelPoolContractTests(unittest.TestCase):
    def test_contract_reuses_exact_frozen_global_pool_id(self) -> None:
        value = target.contract()
        self.assertEqual(target.MODEL_POOL_ID, global_pool.POOL_ID)
        self.assertEqual(value["model_pool_id"], global_pool.POOL_ID)
        self.assertTrue(value["successor_specific_pool_id_forbidden"])
        self.assertEqual(target.validate_contract(value), value)

    def test_real_deadline_limiter_constructor_accepts_contract_pool(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output = Path(raw)
            slots = output / "slots"
            slots.mkdir()
            for index in range(1, 3):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            value = DeadlineAwareGlobalModelSlotLimiter(
                DummyModel(),
                slot_directory=slots,
                output_root=output,
                slot_cap=2,
                pool_id=target.MODEL_POOL_ID,
                absolute_deadline=time.monotonic() + 60,
            )
        self.assertEqual(value.pool_id, global_pool.POOL_ID)
        self.assertEqual(value.slot_cap, 2)

    def test_successor_specific_pool_and_resealed_tamper_fail(self) -> None:
        with self.assertRaises(ValueError):
            target.validate_pool_id("v25558_custom_successor_pool")
        value = target.contract()
        for kind in ("pool", "smoke", "credit", "authority"):
            changed = copy.deepcopy(value)
            if kind == "pool":
                changed["model_pool_id"] = "v25558_custom_successor_pool"
            elif kind == "smoke":
                changed[
                    "deadline_limiter_constructor_smoke_required_before_external_effect"
                ] = False
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("contract_payload_sha256")
            changed["contract_payload_sha256"] = global_pool.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_contract(changed)

    def test_module_is_pure_and_has_no_effect_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden_call in ("open(", "getenv(", "requests.get(", "fetch_urls("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
