from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25014_multi_identity_detail_fields as target  # noqa: E402
from deepwide_agent.v24980_late_page_bound_projection import payload_sha256  # noqa: E402


QUESTION = """Use web search and the official Acme Package Index public page to return one Markdown table.
<PACKAGES>
1. AlphaKit
2. BetaCore
3. GammaTools
</PACKAGES>
Column names: Package, Version, Published, License. Return one table only."""


def page(
    identity: str = "AlphaKit",
    *,
    text: str | None = None,
    url: str | None = None,
    title: str | None = None,
) -> dict[str, str]:
    content = text or "\n".join(
        (
            f"Acme: Package {identity}",
            "",
            f"{identity}: Synthetic package detail",
            "",
            "Version: | 2.4.1",
            "Published: | 2026-07-08",
            "License: | Apache-2.0",
            "NeedsCompilation: | no",
            *("Additional public documentation line." for _ in range(30)),
        )
    )
    return {
        "title": title or f"Acme: Package {identity}",
        "url": url
        or f"https://packages.acme.example/web/packages/{identity}/index.html",
        "text": content,
    }


class MultiIdentityDetailFieldTests(unittest.TestCase):
    def test_numbered_visible_identity_vector_and_one_page_record(self) -> None:
        self.assertEqual(
            target.visible_identities(QUESTION),
            ("AlphaKit", "BetaCore", "GammaTools"),
        )
        value = target.build_projection(QUESTION, page("BetaCore"))
        receipt = value["multi_identity_detail_receipt"]
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertEqual(receipt["visible_identity_count"], 3)
        self.assertEqual(receipt["joint_identity_path_surface_match_count"], 1)
        self.assertEqual(receipt["retained_record_count"], 1)
        self.assertEqual(receipt["retained_bound_observation_count"], 3)
        self.assertIn('"row":"BetaCore"', value["projection"])
        self.assertNotIn('"row":"AlphaKit"', value["projection"])
        self.assertEqual(len(value["projection"]), len(page("BetaCore")["text"]))

    def test_repeated_single_tag_vector_is_supported_but_mixed_tags_fail(self) -> None:
        repeated = QUESTION.replace(
            "<PACKAGES>\n1. AlphaKit\n2. BetaCore\n3. GammaTools\n</PACKAGES>",
            "<PACKAGE>AlphaKit</PACKAGE>, <PACKAGE>BetaCore</PACKAGE>, and "
            "<PACKAGE>GammaTools</PACKAGE>",
        )
        self.assertEqual(
            target.visible_identities(repeated),
            ("AlphaKit", "BetaCore", "GammaTools"),
        )
        self.assertTrue(
            target.build_projection(repeated, page("GammaTools"))[
                "multi_identity_detail_receipt"
            ]["mechanism_engaged"]
        )
        mixed = repeated.replace(
            "<PACKAGE>GammaTools</PACKAGE>", "<PROJECT>GammaTools</PROJECT>"
        )
        self.assertEqual(target.visible_identities(mixed), ())
        self.assertEqual(
            target.build_projection(mixed, page())["projection"], page()["text"][:5_000]
        )

    def test_ambiguous_similar_identity_binding_fails_closed(self) -> None:
        ambiguous_question = QUESTION.replace(
            "1. AlphaKit\n2. BetaCore\n3. GammaTools",
            "1. Alpha\n2. Alpha Kit\n3. GammaTools",
        )
        raw = page(
            "Alpha-Kit",
            title="Acme package Alpha Kit",
            text=page("Alpha-Kit")["text"].replace("Alpha-Kit", "Alpha Kit"),
        )
        value = target.build_projection(ambiguous_question, raw)
        receipt = value["multi_identity_detail_receipt"]
        self.assertEqual(receipt["joint_identity_path_surface_match_count"], 2)
        self.assertEqual(receipt["ambiguous_joint_identity_binding_count"], 1)
        self.assertEqual(receipt["retained_record_count"], 0)
        self.assertEqual(value["projection"], raw["text"][:5_000])

    def test_wrong_path_surface_or_authority_falls_back_exactly(self) -> None:
        cases = (
            page(url="https://packages.acme.example/web/packages/Other/index.html"),
            page(title="Unrelated page", text="Unrelated\n" + "x\n" * 700),
            page(url="https://packages.example/web/packages/AlphaKit/index.html"),
        )
        for raw in cases:
            with self.subTest(url=raw["url"]):
                value = target.build_projection(QUESTION, raw)
                self.assertEqual(value["projection"], raw["text"][:5_000])
                self.assertTrue(
                    value["multi_identity_detail_receipt"][
                        "exact_parent_prefix_handoff"
                    ]
                )

    def test_fields_are_complete_unique_and_same_page_or_no_record(self) -> None:
        base = page()["text"]
        cases = (
            base.replace("License: | Apache-2.0\n", ""),
            base.replace(
                "License: | Apache-2.0",
                "License: | Apache-2.0\nLicense: | GPL-3.0",
            ),
            base.replace("Published: | 2026-07-08", "Published: | Unknown"),
        )
        for text in cases:
            with self.subTest(tail=text[-100:]):
                value = target.build_projection(QUESTION, page(text=text))
                self.assertEqual(value["projection"], text[:5_000])
                self.assertEqual(
                    value["multi_identity_detail_receipt"]["retained_record_count"],
                    0,
                )

    def test_malformed_duplicate_single_or_competing_identity_vectors_fail(self) -> None:
        cases = (
            QUESTION.replace("2. BetaCore", "3. BetaCore"),
            QUESTION.replace("2. BetaCore", "2. AlphaKit"),
            QUESTION.replace("2. BetaCore\n3. GammaTools\n", ""),
            QUESTION
            + " Extra visible value <PACKAGE>AlphaKit</PACKAGE> is not a row block.",
        )
        for question in cases:
            with self.subTest(question=question[-100:]):
                self.assertEqual(target.visible_identities(question), ())
                self.assertEqual(
                    target.build_projection(question, page())["projection"],
                    page()["text"][:5_000],
                )

    def test_long_page_preserves_parent_cap_and_atomic_record(self) -> None:
        raw = page(text=page()["text"] + "\n" + ("Long documentation line.\n" * 500))
        value = target.build_projection(QUESTION, raw)
        receipt = value["multi_identity_detail_receipt"]
        self.assertEqual(len(value["projection"]), 5_000)
        self.assertGreaterEqual(receipt["raw_prefix_characters_retained"], 512)
        self.assertEqual(
            receipt["input_characters_beyond_parent_prefix"], len(raw["text"]) - 5_000
        )

    def test_content_free_receipt_replay_tamper_and_zero_credit(self) -> None:
        value = target.build_projection(QUESTION, page())
        self.assertEqual(
            target.validate_projection(value, question=QUESTION, page=page()), value
        )
        serialized = str(value["multi_identity_detail_receipt"])
        for forbidden in (
            "AlphaKit",
            "BetaCore",
            "2.4.1",
            "Apache-2.0",
            "packages.acme",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(
            value["multi_identity_detail_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        changed = copy.deepcopy(value)
        receipt = changed["multi_identity_detail_receipt"]
        receipt["joint_identity_path_surface_match_count"] = 2
        receipt["ambiguous_joint_identity_binding_count"] = 1
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = payload_sha256(receipt)
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_projection(changed, question=QUESTION, page=page())

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25014_multi_identity_detail_fields.py"
        source = path.read_text(encoding="utf-8")
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
            "socket",
            "subprocess",
            "requests",
            "deepwidebench",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden in (
            "answer_key",
            "benchmark_question_type",
            "results.csv",
            "ground_truth",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
