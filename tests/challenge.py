#!/usr/bin/env python3
"""Score ste-preserve.py on deliberate corruptions and legitimate paraphrases.

Ideal behavior: every corruption is flagged and every paraphrase is clean.
Each case in challenge_cases.json records the checker's current result in
"checker"; a case where that result is not ideal is a known limitation.

Usage:
    python3 tests/challenge.py           # table and miss / false-alarm rates
    python3 tests/challenge.py --json    # machine-readable results
"""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ste_preserve", HERE.parent / "scripts/ste-preserve.py")
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)

CASES = json.loads((HERE / "challenge_cases.json").read_text(encoding="utf-8"))


def run():
    results = []
    for case in CASES:
        differences = sp.compare(case["source"], case["rewrite"])
        actual = "flag" if differences else "clean"
        ideal = "flag" if case["kind"] == "corruption" else "clean"
        results.append({**case, "actual": actual, "ideal": ideal,
                        "categories": sorted(differences)})
    return results


def summary(results):
    corruptions = [r for r in results if r["kind"] == "corruption"]
    paraphrases = [r for r in results if r["kind"] == "paraphrase"]
    return {
        "corruptions": len(corruptions),
        "missed": [r["id"] for r in corruptions if r["actual"] == "clean"],
        "paraphrases": len(paraphrases),
        "false_alarms": [r["id"] for r in paraphrases if r["actual"] == "flag"],
    }


def main(argv):
    results = run()
    totals = summary(results)
    if "--json" in argv:
        print(json.dumps({"results": results, "summary": totals}, indent=2))
        return 0
    for r in results:
        status = "ok" if r["actual"] == r["ideal"] else (
            "MISSED" if r["kind"] == "corruption" else "FALSE ALARM")
        flagged = ", ".join(r["categories"]) or "-"
        print(f"{r['id']}  {r['kind']:<10} {r['type']:<14} {status:<12} {flagged}")
    print(f"\nCorruptions flagged: {totals['corruptions'] - len(totals['missed'])}/{totals['corruptions']}"
          f"  missed: {', '.join(totals['missed']) or 'none'}")
    print(f"Paraphrases clean:   {totals['paraphrases'] - len(totals['false_alarms'])}/{totals['paraphrases']}"
          f"  false alarms: {', '.join(totals['false_alarms']) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
