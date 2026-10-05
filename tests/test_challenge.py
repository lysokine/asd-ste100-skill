"""Lock the checker's measured behavior on the challenge set.

A failure here means ste-preserve.py changed behavior on a recorded case.
If the change is an improvement, update that case's "checker" field.
Run: python -m unittest discover -s tests -v
"""
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
