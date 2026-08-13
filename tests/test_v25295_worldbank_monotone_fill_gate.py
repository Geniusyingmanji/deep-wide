from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent import v25295_worldbank_monotone_fill_gate as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v24319_runner_integration import Clock  # noqa: E402


CODES = tuple(
    f"{chr(65 + index // 26)}{chr(65 + index % 26)}{index % 10}"
    for index in range(265)
)
TARGETS = tuple(
    target.TargetSpec(
        label=f"Metric {index}",
        indicator=f"ZZ.TEST.{index}",
        year="2022",
        urls=(
            f"https://api.worldbank.org/v2/country/all/indicator/ZZ.TEST.{index}?date=2022&format=json&page=1&per_page=200",
            f"https://api.worldbank.org/v2/country/all/indicator/ZZ.TEST.{index}?date=2022&format=json&page=2&per_page=200",
        ),
    )
    for index in range(24)
)


def blob(spec: target.TargetSpec, page: int, codes=CODES) -> bytes:
    subset = codes[:200] if page == 1 else codes[200:]
    return json.dumps(
        [
            {
                "page": page,
                "pages": 2,
                "per_page": 200,
                "total": len(codes),
            },
            [
                {
                    "countryiso3code": code,
                    "indicator": {"id": spec.indicator},
                    "date": spec.year,
                    "value": f"{page}{position:03d}",
                }
                for position, code in enumerate(subset)
            ],
        ],
        separators=(",", ":"),
    ).encode()


def code3(value: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(
        (
            alphabet[(value // (36 * 36)) % 36],
            alphabet[(value // 36) % 36],
            alphabet[value % 36],
        )
    )


def population() -> dict:
    return target.select_and_render_population(
        {spec: (blob(spec, 1), blob(spec, 2)) for spec in TARGETS},
        historical_target_keys=(),
    )


class SyntheticModel:
    def __init__(self, values: list[object]) -> None:
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.deadline_failures = 0

    def complete(self, *_args, **kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value, output_truncated=False)


def make_slots(root: Path, count: int = 8) -> Path:
    directory = root / "slots"
    directory.mkdir()
    for index in range(1, count + 1):
        (directory / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return directory


def table(columns: list[str], rows: list[list[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


class V25295WorldBankMonotoneFillGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.population = population()

    def test_parser_renderer_selector_are_deterministic_and_exact(self) -> None:
        first = population()
        second = target.select_and_render_population(
            dict(reversed(list({spec: (blob(spec, 1), blob(spec, 2)) for spec in TARGETS}.items()))),
            historical_target_keys=(),
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first["target_keys"]), 4)
        self.assertEqual(len(first["entities"]), 144)
        self.assertEqual(len(first["pages"]), 8)
        self.assertEqual(len(first["tasks"]), 12)
        self.assertTrue(all(len(page["content"]) <= 5_000 for page in first["pages"]))
        self.assertLessEqual(sum(len(page["content"]) for page in first["pages"]), 40_000)
        self.assertEqual(target.PARENT_LIMITS, contract.LIMITS)
        self.assertEqual(target.PARENT_TWO_WAVE_POLICY, contract.TWO_WAVE_POLICY)
        self.assertEqual(
            target.PARENT_TAVILY_KEY_SLOT_CAP, contract.TAVILY_KEY_SLOT_CAP
        )

    def test_parser_rejects_target_pagination_value_or_duplicate_drift(self) -> None:
        spec = TARGETS[0]
        wrong_page = json.loads(blob(spec, 1))
        wrong_page[0]["page"] = 2
        with self.assertRaisesRegex(ValueError, "pagination"):
            target.parse_worldbank_page(
                json.dumps(wrong_page).encode(), target=spec, page=1
            )
        wrong_target = json.loads(blob(spec, 1))
        wrong_target[1][0]["indicator"]["id"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "target binding"):
            target.parse_worldbank_page(
                json.dumps(wrong_target).encode(), target=spec, page=1
            )
        duplicate = json.loads(blob(spec, 1))
        duplicate[1][-1] = copy.deepcopy(duplicate[1][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            target.parse_worldbank_page(
                json.dumps(duplicate).encode(), target=spec, page=1
            )
        duplicate_null = json.loads(blob(spec, 1))
        duplicate_null[1][0]["value"] = None
        duplicate_null[1][1]["countryiso3code"] = duplicate_null[1][0][
            "countryiso3code"
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            target.parse_worldbank_page(
                json.dumps(duplicate_null).encode(), target=spec, page=1
            )
        incomplete = [json.loads(blob(spec, 1)), json.loads(blob(spec, 2))]
        incomplete[1][1].pop()
        with self.assertRaisesRegex(ValueError, "coverage"):
            target.parse_target_pages(
                tuple(json.dumps(value).encode() for value in incomplete),
                target=spec,
            )
        cross_page_duplicate = [json.loads(blob(spec, 1)), json.loads(blob(spec, 2))]
        cross_page_duplicate[0][1][0]["value"] = None
        cross_page_duplicate[1][1][0]["value"] = None
        cross_page_duplicate[1][1][0]["countryiso3code"] = (
            cross_page_duplicate[0][1][0]["countryiso3code"]
        )
        with self.assertRaisesRegex(ValueError, "crosses target pages"):
            target.parse_target_pages(
                tuple(json.dumps(value).encode() for value in cross_page_duplicate),
                target=spec,
            )
        bad_url = target.TargetSpec(
            label=spec.label,
            indicator=spec.indicator,
            year=spec.year,
            urls=(spec.urls[0].replace("page=1", "page=2"), spec.urls[1]),
        )
        with self.assertRaisesRegex(ValueError, "target spec"):
            bad_url.validate()

    def test_population_is_no_go_when_fresh_capacity_or_common_entities_fail(self) -> None:
        candidates = {spec: (blob(spec, 1), blob(spec, 2)) for spec in TARGETS}
        with self.assertRaisesRegex(RuntimeError, "fresh target"):
            target.select_and_render_population(
                candidates,
                historical_target_keys=[spec.key for spec in TARGETS[:-3]],
            )
        disconnected = {}
        for index, spec in enumerate(TARGETS):
            codes = tuple(code3(index * 265 + position) for position in range(265))
            disconnected[spec] = (blob(spec, 1, codes), blob(spec, 2, codes))
        with self.assertRaisesRegex(RuntimeError, "no viable"):
            target.select_and_render_population(
                disconnected, historical_target_keys=()
            )

    def _run(self, *, fill: bool = True, plan_failure: bool = False):
        visible = self.population["tasks"][0]
        columns = ["Entity code", *self.population["target_columns"]]
        codes = self.population["entities"][:12]
        baseline_rows = []
        for code in codes:
            row = [code]
            for column in columns[1:]:
                value = "Unknown"
                for page in self.population["pages"]:
                    if page["content"].splitlines()[0] == f"| Entity code | {column} |":
                        for line in page["content"].splitlines()[2:]:
                            cells = [item.strip() for item in line.strip("|").split("|")]
                            if cells[0] == code:
                                value = cells[1]
                                break
                row.append(value)
            baseline_rows.append(row)
        if fill:
            baseline_rows[0][1] = "Unknown"
        baseline = table(columns, baseline_rows)
        proposed_rows = copy.deepcopy(baseline_rows)
        if fill:
            for page in self.population["pages"]:
                if page["content"].splitlines()[0] == f"| Entity code | {columns[1]} |":
                    for line in page["content"].splitlines()[2:]:
                        cells = [item.strip() for item in line.strip("|").split("|")]
                        if cells[0] == codes[0]:
                            proposed_rows[0][1] = cells[1]
        proposal = table(columns, proposed_rows)
        plan = json.dumps(
            {"queries": ["q1", "q2", "q3", "q4"], "columns": columns}
        )
        values = (
            [RuntimeError("synthetic plan failure")]
            if plan_failure
            else [plan, baseline, proposal]
            if fill
            else [plan, baseline]
        )
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock(100.0)
        inner = SyntheticModel(values)
        model = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=make_slots(output),
            output_root=output,
            slot_cap=8,
            pool_id=POOL_ID,
            absolute_deadline=340.0,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        search = target.FrozenWorldBankSnapshotSearchClient(
            self.population["pages"],
            absolute_deadline=340.0,
            monotonic=clock,
        )
        result = target.run_paired_task(
            visible,
            model=model,
            search=search,
            limits=ScoreFirstLimits(**target.PARENT_LIMITS),
            two_wave_policy=TwoWavePolicy(**target.PARENT_TWO_WAVE_POLICY),
            monotonic=clock,
        )
        return inner, search, result

    def test_real_parent_chain_and_third_slot_admit_supported_fill(self) -> None:
        inner, search, result = self._run(fill=True)
        checked = target.validate_result(result)
        receipt = checked["content_free_paired_receipt"]
        self.assertTrue(receipt["candidate_prediction_changed"])
        self.assertEqual(receipt["candidate_disposition"], "admitted_monotone_unknown_fill")
        self.assertEqual(receipt["parent_logical_model_calls"], 2)
        self.assertEqual(receipt["final_logical_model_calls"], 3)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertEqual(receipt["physical_fetch_count"], 8)
        self.assertEqual(receipt["supported_unknown_fill_count"], 1)
        self.assertEqual(inner.requests, 3)
        snapshot = search.snapshot_transport_receipt()
        self.assertEqual(snapshot["search_invocations"], 2)
        self.assertEqual(snapshot["fetch_hits"], 8)
        self.assertEqual(snapshot["network_search_calls"], 0)
        self.assertEqual(snapshot["network_fetch_calls"], 0)
        transport = receipt["content_free_parent_transport_receipts"]
        self.assertEqual(transport["direct_search_receipt"]["provider_attempts"], 0)
        self.assertEqual(
            transport["rate_aware_search_receipt"]["provider_start_reservations"],
            0,
        )
        self.assertFalse(
            transport["pacing_admission_receipt"]["decision_changed"]
        )

    def test_no_unknown_skips_third_slot_and_preserves_control(self) -> None:
        inner, _search, result = self._run(fill=False)
        receipt = result["content_free_paired_receipt"]
        self.assertFalse(receipt["candidate_prediction_changed"])
        self.assertEqual(receipt["candidate_disposition"], "identity_no_baseline_unknown")
        self.assertEqual(receipt["final_logical_model_calls"], 2)
        self.assertEqual(inner.requests, 2)
        parent = result["parent_envelope"]["result"]["prediction"]
        candidate_prediction = result["candidate_result"]["prediction"]
        self.assertEqual(candidate_prediction, parent)

    def test_privileged_runtime_input_fails_before_any_effect(self) -> None:
        visible = dict(self.population["tasks"][0])
        visible["category"] = "forbidden-runtime-label"
        clock = Clock(100.0)
        with self.assertRaises(ValueError):
            target.run_paired_task(
                visible,
                model=object(),
                search=object(),
                limits=ScoreFirstLimits(**target.PARENT_LIMITS),
                two_wave_policy=TwoWavePolicy(**target.PARENT_TWO_WAVE_POLICY),
                monotonic=clock,
            )

    def test_parent_plan_failure_remains_terminal_with_actual_effect_counts(self) -> None:
        inner, search, result = self._run(fill=False, plan_failure=True)
        checked = target.validate_result(result)
        receipt = checked["content_free_paired_receipt"]
        self.assertEqual(receipt["candidate_disposition"], "identity_parent_not_eligible")
        self.assertFalse(receipt["candidate_prediction_changed"])
        snapshot = search.snapshot_transport_receipt()
        self.assertEqual(receipt["physical_query_count"], 2)
        self.assertEqual(receipt["physical_fetch_count"], 6)
        self.assertIsNotNone(
            receipt["content_free_parent_transport_receipts"][
                "pacing_admission_receipt"
            ]
        )
        self.assertEqual(snapshot["search_invocations"], 1)
        self.assertEqual(snapshot["fetch_hits"], 6)
        self.assertEqual(inner.requests, 2)

    def test_snapshot_and_parent_receipts_validate_without_network(self) -> None:
        _inner, search, result = self._run(fill=True)
        target.validate_snapshot_receipt(search.snapshot_transport_receipt())
        self.assertEqual(
            result["parent_envelope"]["search_single_shot_receipt"][
                "multi_query_chunks"
            ],
            2,
        )
        self.assertEqual(
            result["parent_envelope"]["citation_title_backfill_receipt"][
                "multi_query_payload_count"
            ],
            2,
        )

    def test_resealed_prediction_receipt_or_snapshot_tamper_fails(self) -> None:
        _inner, _search, value = self._run(fill=True)
        for kind in (
            "prediction",
            "receipt",
            "snapshot",
            "snapshot_binding",
            "direct",
            "rate",
            "pacing",
            "credit",
        ):
            changed = copy.deepcopy(value)
            paired = changed["content_free_paired_receipt"]
            if kind == "prediction":
                changed["candidate_result"]["prediction"] += " altered"
            elif kind == "receipt":
                paired["physical_fetch_count"] = 9
            elif kind == "snapshot":
                snapshot = paired["snapshot_transport_receipt"]
                snapshot["network_fetch_calls"] = 1
                snapshot.pop("receipt_payload_sha256")
                snapshot["receipt_payload_sha256"] = target.payload_sha256(snapshot)
            elif kind == "snapshot_binding":
                snapshot = paired["snapshot_transport_receipt"]
                snapshot["search_invocations"] = 1
                snapshot.pop("receipt_payload_sha256")
                snapshot["receipt_payload_sha256"] = target.payload_sha256(snapshot)
            elif kind == "direct":
                direct = paired["content_free_parent_transport_receipts"][
                    "direct_search_receipt"
                ]
                direct["provider_attempts"] = 1
                direct.pop("receipt_payload_sha256")
                direct["receipt_payload_sha256"] = target.payload_sha256(direct)
            elif kind == "rate":
                rate = paired["content_free_parent_transport_receipts"][
                    "rate_aware_search_receipt"
                ]
                rate["provider_start_reservations"] = 1
                rate.pop("receipt_payload_sha256")
                rate["receipt_payload_sha256"] = target.payload_sha256(rate)
            elif kind == "pacing":
                pacing = paired["content_free_parent_transport_receipts"][
                    "pacing_admission_receipt"
                ]
                pacing["benchmark_launch_or_evaluator_authorized"] = True
                pacing.pop("receipt_payload_sha256")
                pacing["receipt_payload_sha256"] = target.payload_sha256(pacing)
            else:
                paired["positive_signed_credit_count"] = 1
            paired.pop("receipt_payload_sha256")
            paired["receipt_payload_sha256"] = target.payload_sha256(paired)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_source_has_no_filesystem_network_evaluator_or_privileged_routing(self) -> None:
        source_path = ROOT / "src/deepwide_agent/v25295_worldbank_monotone_fill_gate.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
        for forbidden in ("os", "pathlib", "requests", "subprocess", "urllib.request"):
            self.assertNotIn(forbidden, imports)
        for forbidden in (
            "benchmark_question_type",
            "ground_truth",
            "answer_key",
            "run_official_eval_local",
            "results.csv",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
