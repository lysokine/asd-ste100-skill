"""Behavior checks for the source-versus-rewrite marker comparison.

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ste-preserve.py"
spec = importlib.util.spec_from_file_location("ste_preserve", SCRIPT)
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)


def run_cli(source, rewrite, *args):
    with tempfile.TemporaryDirectory() as directory:
        src = Path(directory) / "source.md"
        rw = Path(directory) / "rewrite.md"
        src.write_text(source, encoding="utf-8")
        rw.write_text(rewrite, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(src), str(rw), *args],
            text=True, capture_output=True, check=False,
        )
        unchanged = (src.read_text(encoding="utf-8") == source
                     and rw.read_text(encoding="utf-8") == rewrite)
    return result, unchanged


class PreserveTests(unittest.TestCase):
    def test_identical_text_is_clean(self):
        text = "Retry at most 3 times, and only for HTTP 503. Do not retry HTTP 429."
        self.assertEqual(sp.compare(text, text), {})

    def test_plain_rewording_is_clean(self):
        self.assertEqual(sp.compare(
            "The agent will perform an analysis of the log and will then provide "
            "a report of the errors.",
            "The agent will analyze the log. It will then report the errors."), {})

    def test_requirement_strength_change_is_reported(self):
        self.assertEqual(sp.compare("You should wait.", "You must wait.")["modality"],
                         [("must", 0, 1), ("should", 1, 0)])

    def test_dropped_hedge_is_reported(self):
        diff = sp.compare("The request may have failed. It is possibly a timeout.",
                          "The request failed. It is a timeout.")
        self.assertEqual(diff["modality"], [("may", 1, 0)])
        self.assertEqual(diff["hedges"], [("possible", 1, 0)])

    def test_added_certainty_is_reported(self):
        diff = sp.compare("Partial artifacts are sometimes produced.",
                          "Partial artifacts are always produced.")
        self.assertEqual(diff["frequency"], [("always", 0, 1), ("sometimes", 1, 0)])

    def test_number_change_is_reported_and_unit_spelling_is_not(self):
        self.assertEqual(sp.compare("Wait 30 seconds, then 2 hours.",
                                    "Wait 30 s, then 2 h."), {})
        self.assertEqual(sp.compare("Retry at most 3 times.", "Retry at most 5 times.")["numbers"],
                         [("3", 1, 0), ("5", 0, 1)])
        self.assertEqual(sp.compare("Allocate 10 GB.", "Allocate 10 MB.")["numbers"],
                         [("10 GB", 1, 0), ("10 MB", 0, 1)])

    def test_word_numbers_and_thousands_separators_match(self):
        self.assertEqual(sp.compare("Retry three times on 1,000 nodes.",
                                    "Retry 3 times on 1000 nodes."), {})

    def test_contractions_are_normalized(self):
        self.assertEqual(sp.compare("Don't retry. It can't wait. You cannot skip it.",
                                    "Do not retry. It can not wait. You can not skip it."), {})

    def test_dropped_negation_is_reported(self):
        self.assertEqual(sp.compare("Do not retry HTTP 429.", "Retry HTTP 429.")["negation"],
                         [("not", 1, 0)])

    def test_scope_words_are_reported(self):
        diff = sp.compare("Retry only for HTTP 503, unless the budget is spent.",
                          "Retry for HTTP 503.")
        self.assertEqual(diff["quantifiers"], [("only", 1, 0)])
        self.assertEqual(diff["conditions"], [("unless", 1, 0)])

    def test_lost_contrast_is_reported(self):
        diff = sp.compare(
            "Option A has lower latency but uses more memory; option B is the opposite.",
            "Option A has lower latency. It uses more memory. Option B uses less memory.")
        self.assertEqual(diff["contrast"], [("but", 1, 0), ("the opposite", 1, 0)])

    def test_code_is_compared_exactly_and_not_as_prose(self):
        diff = sp.compare("Set `max_retries` to 3.", "Set `max-retries` to 3.")
        self.assertEqual(diff["code"], [("max-retries", 0, 1), ("max_retries", 1, 0)])
        self.assertEqual(sp.compare("Run `must_not_fail` now.", "Run `must_not_fail` now."), {})
        self.assertEqual(sp.compare("Use `if x` here.", "Use `if x` here."), {})
        diff = sp.compare("```\nmake all\n```\n", "```\nmake test\n```\n")
        self.assertEqual(sorted(diff), ["code"])

    def test_identifiers_outside_backticks_are_compared(self):
        source = ("Submit with bsub -P das and keep CUDA_VISIBLE_DEVICES unset; "
                  "logs go to /scratch/$USER/logs and config.toml.")
        self.assertEqual(sp.compare(source, source), {})
        diff = sp.compare(source, source.replace("-P das", "-p das")
                          .replace("CUDA_VISIBLE_DEVICES", "the GPU variable"))
        self.assertEqual(diff["code"], [("-P", 1, 0), ("-p", 0, 1),
                                        ("CUDA_VISIBLE_DEVICES", 1, 0)])

    def test_sentence_final_punctuation_does_not_change_identifiers(self):
        self.assertEqual(sp.compare("Edit config.toml.", "Edit config.toml and restart."), {})

    def test_urls_are_compared_as_code(self):
        diff = sp.compare("See https://example.org/a.", "See https://example.org/b.")
        self.assertEqual(sorted(diff), ["code"])

    def test_example_c_rewrite_lists_condition_changes_for_review(self):
        diff = sp.compare(
            "Once the upstream job has completed and assuming no errors were raised, "
            "the downstream agent should proceed to consume the output artifact, though "
            "it is worth noting that partial artifacts are sometimes produced under "
            "timeout conditions.",
            "If the upstream job has completed and no errors were raised, the downstream "
            "agent should consume the output artifact. Partial artifacts are sometimes "
            "produced under timeout conditions.")
        self.assertNotIn("modality", diff)
        self.assertNotIn("frequency", diff)
        self.assertEqual(diff["conditions"], [("assuming", 1, 0), ("if", 0, 1), ("once", 1, 0)])
        self.assertEqual(diff["contrast"], [("though", 1, 0)])

    def test_user_guide_passage(self):
        source = ("You should probably run the validation step before merging, and the job "
                  "must be submitted with bsub -P das, which has been the convention since "
                  "the cluster migration.")
        kept = ("You should probably run the validation step before merging. Submit the job "
                "with bsub -P das. This must be done because it has been the convention "
                "since the cluster migration.")
        self.assertEqual(sp.compare(source, kept), {})
        hardened = ("Run the validation step before merging. Submit the job with bsub -P das.")
        diff = sp.compare(source, hardened)
        self.assertEqual(diff["modality"], [("must", 1, 0), ("should", 1, 0)])
        self.assertEqual(diff["hedges"], [("probable", 1, 0)])

    def test_hedge_to_certainty_is_reported(self):
        cases = [
            ("It is unclear whether the cache caused the 502s.", "The cache caused the 502s.",
             "hedges", [("unclear", 1, 0), ("whether", 1, 0)]),
            ("This would reduce latency.", "This reduces latency.",
             "modality", [("would", 1, 0)]),
            ("The job will fail.", "The job fails.", "modality", [("will", 1, 0)]),
            ("We think it is a race condition.", "It is a race condition.",
             "hedges", [("think", 1, 0)]),
            ("There is a possibility of data loss.", "There is data loss.",
             "hedges", [("possible", 1, 0)]),
            ("Wait about 30 s on around 5 nodes.", "Wait 30 s on 5 nodes.",
             "hedges", [("about (number)", 2, 0)]),
            ("Retries tend to succeed.", "Retries succeed.", "hedges", [("tend to", 1, 0)]),
        ]
        for source, rewrite, category, expected in cases:
            with self.subTest(rewrite=rewrite):
                self.assertEqual(sp.compare(source, rewrite)[category], expected)

    def test_letter_digit_tokens_are_compared(self):
        diff = sp.compare("Use API v2 on an H100 with Python3.",
                          "Use API v3 on an A100 with Python2.")
        self.assertEqual(diff["code"], [("A100", 0, 1), ("H100", 1, 0), ("Python2", 0, 1),
                                        ("Python3", 1, 0), ("v2", 1, 0), ("v3", 0, 1)])

    def test_backticks_alone_are_not_a_difference(self):
        self.assertEqual(sp.compare("Run with --no-cache and set timeout to 30.",
                                    "Run with `--no-cache` and set timeout to `30`."), {})

    def test_flag_words_do_not_count_as_prose(self):
        self.assertEqual(sp.compare("Pass --no-cache.", "Pass --no-cache, then wait.")
                         .get("negation"), None)

    def test_routine_rewording_noise_is_suppressed(self):
        for source, rewrite in (("Pick one of the nodes.", "Pick a node."),
                                ("Use 50% of RAM.", "Use 50 percent of RAM."),
                                ("Wait 5 weeks.", "Wait 5 wk."),
                                ("It needs read/write access.", "It needs read and write access.")):
            with self.subTest(rewrite=rewrite):
                self.assertEqual(sp.compare(source, rewrite), {})

    def test_bits_and_bytes_differ(self):
        self.assertEqual(sp.compare("Use 10 Mb links.", "Use 10 MB links.")["numbers"],
                         [("10 MB", 0, 1), ("10 Mb", 1, 0)])
        self.assertEqual(sp.compare("Use 4 GiB.", "Use 4 GIB."), {})

    def test_sign_is_kept(self):
        self.assertEqual(sp.compare("Set the offset to -5.", "Set the offset to 5.")["numbers"],
                         [("-5", 1, 0), ("5", 0, 1)])
        self.assertEqual(sp.compare("Use 5-10 workers.", "Use 5-10 workers."), {})

    def test_leading_dot_and_scientific_numbers(self):
        self.assertEqual(sp.compare("Set the tolerance to .5.", "Set the tolerance to .9.")["numbers"],
                         [(".5", 1, 0), (".9", 0, 1)])
        self.assertEqual(sp.compare("Set the limit to 1e3.", "Set the limit to 1e6.")["numbers"],
                         [("1e3", 1, 0), ("1e6", 0, 1)])
        self.assertEqual(sp.compare("Use 2.5e-3 s.", "Use 2.5e-3 s."), {})

    def test_code_is_not_unicode_normalized(self):
        diff = sp.compare('Run `print("−")`.', 'Run `print("-")`.')
        self.assertEqual(sorted(diff), ["code"])
        self.assertEqual(sp.compare("Set the offset to −5.", "Set the offset to -5."), {})

    def test_longer_fences_are_code(self):
        diff = sp.compare("````sh\necho hello\n````\n", "````sh\necho goodbye\n````\n")
        self.assertEqual(sorted(diff), ["code"])
        self.assertEqual(sp.compare("````\n```\nnested\n```\n````\n",
                                    "````\n```\nnested\n```\n````\n"), {})

    def test_urls_keep_balanced_parentheses(self):
        diff = sp.compare("Use https://example.org/a(x).", "Use https://example.org/a(y).")
        self.assertEqual(diff["code"], [("https://example.org/a(x)", 1, 0),
                                        ("https://example.org/a(y)", 0, 1)])
        self.assertEqual(sp.compare("See [docs](https://example.org/d).",
                                    "See [the docs](https://example.org/d)."), {})

    def test_word_numbers_bind_units(self):
        self.assertEqual(sp.compare("Wait three seconds.", "Wait 3 seconds."), {})
        self.assertEqual(sp.compare("Wait about three seconds.", "Wait three seconds.")["hedges"],
                         [("about (number)", 1, 0)])

    def test_line_wrap_does_not_change_phrases(self):
        self.assertEqual(sp.compare("Wait at\nmost 3 seconds.", "Wait at most 3 seconds."), {})
        self.assertEqual(sp.compare("Do not\nretry.", "Do not retry."), {})

    def test_comparison_operators(self):
        self.assertEqual(sp.compare("Keep wells with SNR ≥5.", "Keep wells with SNR >5.")["comparison"],
                         [(">", 0, 1), ("≥", 1, 0)])
        self.assertEqual(sp.compare("Keep SNR >= 5 and n <= 3.", "Keep SNR ≥ 5 and n ≤ 3."), {})
        self.assertEqual(sp.compare("Use 5 or more nodes.", "Use 5 nodes.")["comparison"],
                         [("or more", 1, 0)])
        self.assertEqual(sp.compare("Wait ~30 s.", "Wait 30 s.")["comparison"], [("≈", 1, 0)])
        self.assertEqual(sp.compare("Set n=3.", "Set n to 3.")["comparison"], [("=", 1, 0)])

    def test_arrows_and_blockquotes_are_not_comparisons(self):
        self.assertEqual(sp.compare("> Note: A -> B => C == D <- E.", "Note: A, B, C, D, E."), {})

    def test_swapped_markers_are_reported_as_order(self):
        diff = sp.compare("Clients should retry, and servers must log the error.",
                          "Clients must retry, and servers should log the error.")
        self.assertEqual(diff, {"order": [("sequence", "should, must", "must, should")]})
        diff = sp.compare("Only admins can delete projects; users must not edit them.",
                          "Admins can delete projects; only users must not edit them.")
        self.assertEqual(diff["order"], [("sequence", "only, can", "can, only")])

    def test_order_is_silent_when_counts_already_differ(self):
        diff = sp.compare("You should wait, and you must log it.", "You must wait.")
        self.assertNotIn("order", diff)
        self.assertEqual(sp.compare("You should wait, and you must log it.",
                                    "You should wait. You must log it."), {})

    def test_conditions_and_contrast_do_not_enter_order(self):
        self.assertEqual(sp.compare("If the job fails, retry, but log it.",
                                    "Retry if the job fails, but log it."), {})

    def test_order_row_in_json(self):
        result, _ = run_cli("A should run; B must stop.", "A must run; B should stop.", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["differences"]["order"],
                         [{"item": "sequence", "source": "should, must", "rewrite": "must, should"}])

    def test_alternatives_are_compared(self):
        self.assertEqual(sp.compare("Alert if CPU is high and memory is low.",
                                    "Alert if CPU is high or memory is low.")["alternatives"],
                         [("or", 0, 1)])

    def test_unreadable_files_exit_2(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--json", "nope1", "nope2"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("ste-preserve:", result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.md"
            bad.write_bytes(b"\xff\xfe not utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(bad), str(bad)],
                                    text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)

    def test_cli_exit_codes_json_and_read_only(self):
        result, unchanged = run_cli("You should wait.", "You should wait.")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(unchanged)
        result, unchanged = run_cli("You should wait.", "You must wait.", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(unchanged)
        report = json.loads(result.stdout)
        self.assertEqual(set(report), {"differences", "count"})
        self.assertEqual(report["count"], 2)
        self.assertEqual(report["differences"]["modality"][0],
                         {"item": "must", "source": 0, "rewrite": 1})

    def test_cli_usage_error(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "only-one-file"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)
        result = subprocess.run([sys.executable, str(SCRIPT), "a", "b", "--bogus"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)

    def test_selftest(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--selftest"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("selftest OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
