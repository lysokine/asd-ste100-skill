"""Behavior checks, not a measure of rewrite quality.

STE_LINT_PATH lets the same tests exercise a saved upstream script.
Run: python -m unittest discover -s tests -v
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(os.environ.get(
    "STE_LINT_PATH", Path(__file__).resolve().parents[1] / "scripts/ste-lint.py"
)).resolve()
spec = importlib.util.spec_from_file_location("ste_lint", SCRIPT)
ste = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ste)


def run_cli(text, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args], input=text,
        text=True, capture_output=True, check=False,
    )


class LinterTests(unittest.TestCase):
    def test_distinct_actions_are_not_declared_synonyms(self):
        for text in (
            "Validate the JSON schema. Verify the signature. "
            "Confirm deployment with the operator.",
            "Remove the disk from the server. Delete the temporary file.",
            "Stop accepting requests. Terminate the process after draining.",
        ):
            with self.subTest(text=text):
                findings, _ = ste.lint(text)
                self.assertFalse(any(f["rule"] == "synonym-rotation" for f in findings))

    def test_style_findings_are_advisory(self):
        result = run_cli("Perform an analysis of the seamless log; spin up the job. "
                         "The panel is removed. We have received the report. "
                         + "word " * 30 + ".")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual({f["rule"] for f in report["violations"]},
                         {"semicolon", "phrasal-verb", "marketing-adjective",
                          "nominalization", "passive-voice", "present-perfect",
                          "long-sentence"})
        self.assertEqual(report["hard_count"], 0)
        self.assertTrue(all(f["level"] == "advisory" for f in report["violations"]))

    def test_soft_wrap_does_not_hide_long_sentence(self):
        words = [f"word{i}" for i in range(30)]
        for separator in (" ", "\n", "\r\n"):
            text = separator.join(" ".join(words[i:i+10]) for i in range(0, 30, 10)) + "."
            with self.subTest(separator=separator):
                findings, _ = ste.lint(text, "wrapped.md")
                long = [f for f in findings if f["rule"] == "long-sentence"]
                self.assertEqual(len(long), 1)
                self.assertEqual(long[0]["match"], "30 words")
                self.assertEqual(long[0]["file"], "wrapped.md")
                self.assertEqual(long[0]["line"], 1)

    def test_sentence_boundary_across_wrap_is_respected(self):
        findings, _ = ste.lint("word " * 20 + ".\n" + "word " * 20 + ".")
        self.assertFalse(any(f["rule"] == "long-sentence" for f in findings))

    def test_blank_line_and_heading_separate_blocks(self):
        for separator in ("\n\n", "\n# Next\n"):
            findings, _ = ste.lint("word " * 15 + separator + "word " * 15)
            self.assertFalse(any(f["rule"] == "long-sentence" for f in findings))

    def test_separate_list_items_are_not_one_sentence(self):
        findings, _ = ste.lint("- " + "word " * 15 + "\n- " + "word " * 15)
        self.assertFalse(any(f["rule"] == "long-sentence" for f in findings))

    def test_list_continuation_is_one_sentence(self):
        findings, _ = ste.lint("- " + "word " * 15 + "\n  " + ("word " * 15).rstrip() + ".")
        long = [f for f in findings if f["rule"] == "long-sentence"]
        self.assertEqual(len(long), 1)
        self.assertEqual(long[0]["match"], "30 words")

    def test_table_cells_remain_independent(self):
        cell = " ".join(["word"] * 20)
        findings, count = ste.lint(f"| A | B |\n| --- | --- |\n| {cell} | {cell} |")
        self.assertFalse(any(f["rule"] == "long-sentence" for f in findings))
        self.assertEqual(count, 42)

    def test_long_table_cell_is_reported(self):
        findings, _ = ste.lint("| A | B |\n| --- | --- |\n| x | " + "word " * 30 + "|")
        long = [f for f in findings if f["rule"] == "long-sentence"]
        self.assertEqual(len(long), 1)
        self.assertEqual(long[0]["line"], 3)
        self.assertEqual(long[0]["match"], "30 words")

    def test_fenced_code_and_inline_code_are_not_style_targets(self):
        for fence in ("```", "~~~"):
            findings, _ = ste.lint(f"{fence}\n" + "word " * 30 + ";\n" + fence)
            self.assertEqual(findings, [])
        findings, _ = ste.lint("Use `spin up; seamless` as the exact label.")
        self.assertEqual(findings, [])

    def test_modality_is_not_an_error(self):
        findings, _ = ste.lint("The request may have failed. The disk might have filled. "
                               "You should wait. You must not retry. It could be a timeout.")
        self.assertEqual(findings, [])

    def test_dangling_conjunction_still_fails(self):
        result = run_cli("- Read the file and")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["hard_count"], 1)
        self.assertEqual(report["violations"][0]["rule"], "dangling-conjunction")

    def test_baseline_and_disable_still_work(self):
        for args in (("--baseline", "1"), ("--disable", "dangling-conjunction")):
            result = run_cli("- Read the file and", *args)
            self.assertEqual(result.returncode, 0)
        result = run_cli("- Read the file and\n- Record the result or", "--baseline", "1")
        self.assertEqual(result.returncode, 1)

    def test_json_contract_is_preserved(self):
        result = run_cli("Clear text.")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(set(json.loads(result.stdout)),
                         {"violations", "count", "hard_count", "baseline", "words", "per_100_words"})

    def test_linter_is_read_only_and_keeps_file_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.md"
            original = b"Read the file; record the result.\n"
            path.write_bytes(original)
            result = run_cli("", str(path))
            self.assertEqual(path.read_bytes(), original)
            report = json.loads(result.stdout)
            self.assertTrue(all(f["file"] == str(path) for f in report["violations"]))

    def test_green_lint_is_not_semantic_validation(self):
        # The claim is invented relative to "no vendor lock-in". No regex can
        # establish that relationship without the source and semantic judgment.
        result = run_cli("This cache stores no data outside your stack.")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["count"], 0)


if __name__ == "__main__":
    unittest.main()
