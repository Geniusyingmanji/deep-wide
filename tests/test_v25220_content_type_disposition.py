from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25217_single_snapshot_transport as parent  # noqa: E402
from deepwide_agent import v25220_content_type_disposition as target  # noqa: E402


def parent_accepts(stratum: str, raw_header: str) -> bool:
    normalized = str(raw_header).split(";", 1)[0].strip().casefold()
    return normalized in parent.ENDPOINTS[stratum]["accepted_content_types"]


class V25220ContentTypeDispositionTests(unittest.TestCase):
    def test_frozen_strata_and_accepted_types_match_parent_exactly(self) -> None:
        self.assertEqual(target.STRATA, tuple(parent.ENDPOINTS))
        self.assertEqual(
            target.ACCEPTED_CONTENT_TYPES,
            {
                stratum: tuple(spec["accepted_content_types"])
                for stratum, spec in parent.ENDPOINTS.items()
            },
        )

    def test_accepted_case_parameters_and_whitespace_match_parent(self) -> None:
        for stratum, accepted_types in target.ACCEPTED_CONTENT_TYPES.items():
            for accepted in accepted_types:
                for raw in (accepted, accepted.upper(), f" {accepted} ; charset=UTF-8"):
                    value = target.observe_content_type(
                        stratum, header_present=True, raw_header=raw
                    )
                    with self.subTest(stratum=stratum, raw=raw):
                        self.assertEqual(value["disposition"], "accepted")
                        self.assertEqual(
                            value["frozen_parent_transport_accepts"],
                            parent_accepts(stratum, raw),
                        )
                        self.assertTrue(
                            value["observer_successor_transport_accepts"]
                        )

    def test_missing_empty_and_unknown_values_preserve_parent_rejection(self) -> None:
        for stratum in target.STRATA:
            cases = (
                (False, None, "missing"),
                (True, "", "missing"),
                (True, "  ; charset=utf-8", "missing"),
                (True, "application/octet-stream", "unknown_disallowed"),
                (True, "application/x-private-secret", "unknown_disallowed"),
            )
            for present, raw, expected in cases:
                value = target.observe_content_type(
                    stratum, header_present=present, raw_header=raw
                )
                with self.subTest(stratum=stratum, raw=raw):
                    self.assertEqual(value["disposition"], expected)
                    self.assertFalse(value["frozen_parent_transport_accepts"])
                    self.assertFalse(value["observer_successor_transport_accepts"])

    def test_known_safe_alternate_is_reserved_but_public_allowlist_is_empty(self) -> None:
        self.assertEqual(
            target.KNOWN_SAFE_ALTERNATES,
            {stratum: () for stratum in target.STRATA},
        )
        self.assertEqual(
            target._classify(
                "application/example",
                accepted=("text/plain",),
                known_safe_alternates=("application/example",),
            ),
            "known_safe_alternate",
        )
        value = target.observe_content_type(
            target.STRATA[1],
            header_present=True,
            raw_header="application/example",
        )
        self.assertEqual(value["disposition"], "unknown_disallowed")
        self.assertEqual(value["known_safe_alternate_allowlist_count"], 0)

    def test_observation_is_content_free_and_does_not_change_acceptance(self) -> None:
        secret = "application/x-private-secret-value"
        value = target.observe_content_type(
            target.STRATA[1], header_present=True, raw_header=secret
        )
        rendered = json.dumps(value, sort_keys=True)
        self.assertNotIn(secret, rendered)
        self.assertFalse(value["header_original_normalized_value_or_hash_persisted"])
        self.assertFalse(value["observer_changes_transport_acceptance"])
        self.assertFalse(
            value[
                "transport_relaxation_population_freeze_external_forward_or_runtime_compatibility_authorized"
            ]
        )

    def test_invalid_input_shapes_fail_before_observation(self) -> None:
        cases = (
            ("unknown", True, "text/plain"),
            (target.STRATA[0], 1, "application/json"),
            (target.STRATA[0], True, None),
            (target.STRATA[0], False, "application/json"),
        )
        for stratum, present, raw in cases:
            with self.subTest(stratum=stratum, present=present, raw=raw), self.assertRaises(
                ValueError
            ):
                target.observe_content_type(
                    stratum, header_present=present, raw_header=raw
                )

    def test_resealed_schema_disposition_acceptance_or_authority_tamper_fails(self) -> None:
        value = target.observe_content_type(
            target.STRATA[0], header_present=True, raw_header="application/json"
        )
        for kind in ("schema", "disposition", "acceptance", "alternate", "authority"):
            changed = copy.deepcopy(value)
            if kind == "schema":
                changed["normalized_media_type"] = "application/json"
            elif kind == "disposition":
                changed["disposition"] = "known_safe_alternate"
                changed["frozen_parent_transport_accepts"] = False
                changed["observer_successor_transport_accepts"] = False
            elif kind == "acceptance":
                changed["observer_successor_transport_accepts"] = False
            elif kind == "alternate":
                changed["known_safe_alternate_allowlist_count"] = 1
            else:
                changed[
                    "transport_relaxation_population_freeze_external_forward_or_runtime_compatibility_authorized"
                ] = True
            changed.pop("observation_payload_sha256")
            changed["observation_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_observation(changed)

    def test_source_is_pure_label_blind_secret_free_and_evaluator_free(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v25220_content_type_disposition.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "socket",
            "subprocess",
            "pathlib",
            "openai",
            "httpx",
            "gh" + "p_",
            "tvly-" + "dev-",
            "run_official_eval_local",
            "/mnt",
            "/data",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
