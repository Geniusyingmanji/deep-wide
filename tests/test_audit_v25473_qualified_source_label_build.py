from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT=Path(__file__).resolve().parents[1]
for path in (ROOT,ROOT/"src"):
    if str(path) not in sys.path:sys.path.insert(0,str(path))

from scripts import audit_v25473_qualified_source_label_build as target  # noqa: E402


class V25473BuildAuditTests(unittest.TestCase):
    def test_diagnosis_barrier_and_frozen_hashes_are_exact(self) -> None:
        self.assertTrue(target._diagnosis_barrier())
        self.assertTrue(all(target.base.sha256(path)==digest for path,digest in target.FIXED_HASHES.items()))

    def test_closure_count_and_hash_are_frozen(self) -> None:
        closure,vector=target._closure();self.assertEqual(len(closure),90);self.assertEqual(target.base.payload_sha256(vector),target.EXPECTED_CLOSURE_VECTOR_SHA256);self.assertEqual(target.base.payload_sha256([row["path"] for row in vector]),target.EXPECTED_CLOSURE_PATH_SHA256)

    def test_build_audit_passes_without_external_effect(self) -> None:
        tests={"expected":target.EXPECTED_TESTS,"observed":target.EXPECTED_TESTS,"passed":True,"suites":[]}
        with mock.patch.object(target,"_tests",return_value=tests):
            value=target.build_audit(now=1,tracked=False)
        self.assertEqual(target.validate_audit(value),value);self.assertTrue(value["audit_valid"]);self.assertEqual(value["tests"]["observed"],68);self.assertFalse(value["authorization"]["external_protocol_or_forward"])

    def test_resealed_credit_or_launch_tamper_fails(self) -> None:
        tests={"expected":target.EXPECTED_TESTS,"observed":target.EXPECTED_TESTS,"passed":True,"suites":[]}
        with mock.patch.object(target,"_tests",return_value=tests):
            value=target.build_audit(now=1,tracked=False)
        for kind in ("credit","launch"):
            changed=copy.deepcopy(value)
            if kind=="credit":changed["positive_signed_credit_count"]=1
            else:changed["authorization"]["external_protocol_or_forward"]=True
            changed.pop("audit_payload_sha256");changed["audit_payload_sha256"]=target.base.payload_sha256(changed)
            with self.subTest(kind=kind),self.assertRaises(ValueError):target.validate_audit(changed)


if __name__=="__main__":unittest.main()
