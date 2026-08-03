from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
)
from deepwide_agent import v24309_runner_exit_integration as target  # noqa: E402


def marker(path: Path) -> None:
    path.write_text('{"valid": true}\n', encoding="utf-8")


class V24309RunnerExitIntegrationTests(unittest.TestCase):
    def test_child_success_receipt_is_written_after_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)

            def action() -> str:
                marker(directory / target.RESULT_NAME)
                marker(directory / target.MODEL_RECEIPT_NAME)
                marker(directory / target.TRANSPORT_RECEIPT_NAME)
                self.assertFalse((directory / target.CHILD_TERMINAL_NAME).exists())
                return "done"

            value = target.run_child_with_terminal_receipt(
                output_root=ROOT / "outputs",
                directory=directory,
                action=action,
            )
            self.assertEqual(value, "done")
            receipt = json.loads(
                (directory / target.CHILD_TERMINAL_NAME).read_text(encoding="utf-8")
            )
            validate_child_receipt(receipt)
            self.assertEqual(receipt["stage"], "result_envelope_written")
            self.assertTrue(receipt["result_envelope_written"])
            self.assertTrue(receipt["model_receipt_written"])
            self.assertTrue(receipt["transport_receipt_written"])

    def test_child_exception_is_coarsened_without_message(self) -> None:
        class SecretTaskIdentifierError(Exception):
            pass

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            with self.assertRaises(SecretTaskIdentifierError):
                target.run_child_with_terminal_receipt(
                    output_root=ROOT / "outputs",
                    directory=directory,
                    action=lambda: (_ for _ in ()).throw(
                        SecretTaskIdentifierError("task_0123456789abcdef01234567")
                    ),
                )
            encoded = (directory / target.CHILD_TERMINAL_NAME).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("task_0123456789abcdef01234567", encoded)
            receipt = json.loads(encoded)
            self.assertEqual(receipt["exception_type"], "UnknownError")

    def test_directory_escape_fails_before_action(self) -> None:
        called = False

        def action() -> None:
            nonlocal called
            called = True

        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            with self.assertRaisesRegex(RuntimeError, "escaped"):
                target.run_child_with_terminal_receipt(
                    output_root=ROOT / "outputs",
                    directory=Path(temporary),
                    action=action,
                )
        self.assertFalse(called)

    def test_artifact_names_cannot_escape_or_alias(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            with self.assertRaisesRegex(ValueError, "distinct basenames"):
                target.run_child_with_terminal_receipt(
                    output_root=ROOT / "outputs",
                    directory=directory,
                    action=lambda: None,
                    result_name="../result.json",
                )
            with self.assertRaisesRegex(ValueError, "distinct basenames"):
                target.run_child_with_terminal_receipt(
                    output_root=ROOT / "outputs",
                    directory=directory,
                    action=lambda: None,
                    result_name=target.MODEL_RECEIPT_NAME,
                )

    def test_non_os_launch_exception_is_content_free_parent_failure(self) -> None:
        class SensitiveLaunchError(RuntimeError):
            pass

        def fail(*_args, **_kwargs):
            raise SensitiveLaunchError("task_0123456789abcdef01234567")

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            outcome = target.run_observed_subprocess(
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=Path(temporary),
                command=["synthetic"],
                environment={},
                timeout_seconds=1,
                result_validator=lambda _value: None,
                model_receipt_validator=lambda _value: None,
                transport_receipt_validator=lambda _value: None,
                popen=fail,
            )
            self.assertEqual(
                outcome.receipt["failure_taxonomy"],
                "parent_subprocess_exception",
            )
            encoded = json.dumps(outcome.receipt)
            self.assertNotIn("SensitiveLaunchError", encoded)
            self.assertNotIn("task_0123456789abcdef01234567", encoded)


if __name__ == "__main__":
    unittest.main()
