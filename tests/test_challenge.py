"""Lock the checker's measured behavior on the challenge set.

A failure here means ste-preserve.py changed behavior on a recorded case.
If the change is an improvement, update that case's "checker" field.
Run: python -m unittest discover -s tests -v
"""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "challenge", Path(__file__).resolve().parent / "challenge.py")
challenge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(challenge)


class ChallengeTests(unittest.TestCase):
    def test_recorded_results_match(self):
        for result in challenge.run():
            with self.subTest(case=result["id"]):
                self.assertEqual(result["actual"], result["checker"], result["categories"])

    def test_cases_are_well_formed(self):
        ids = [case["id"] for case in challenge.CASES]
        self.assertEqual(len(ids), len(set(ids)))
        for case in challenge.CASES:
            self.assertIn(case["kind"], {"corruption", "paraphrase"})
            self.assertIn(case["checker"], {"flag", "clean"})
            self.assertNotEqual(case["source"], case["rewrite"])


    def test_summary_matches_readme(self):
        # README.md quotes these numbers; update both together.
        totals = challenge.summary(challenge.run())
        self.assertEqual((totals["corruptions"], len(totals["missed"])), (36, 6))
        self.assertEqual((totals["paraphrases"], len(totals["false_alarms"])), (20, 3))

    def test_pilot_checker_results_are_current(self):
        pilot = Path(__file__).resolve().parents[1] / "evals/pilot-01"
        source = {p["id"]: p["text"] for p in json.loads((pilot / "passages.json").read_text(encoding="utf-8"))}
        recorded = json.loads((pilot / "outputs/checker_results.json").read_text(encoding="utf-8"))
        arms = {"A_skill": "arm_a_skill.json", "B_short": "arm_b_short_instruction.json",
                "C_plain": "arm_c_plain.json"}
        for arm, name in arms.items():
            rewrites = json.loads((pilot / "outputs" / name).read_text(encoding="utf-8"))
            for pid, text in source.items():
                with self.subTest(arm=arm, passage=pid):
                    current = {k: [list(r) for r in v]
                               for k, v in challenge.sp.compare(text, rewrites[pid]).items()}
                    self.assertEqual(current, recorded[pid][arm])


if __name__ == "__main__":
    unittest.main()
