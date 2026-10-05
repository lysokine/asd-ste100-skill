#!/usr/bin/env python3
"""List meaning markers that differ between a source text and its rewrite.

Compares modality, hedges, frequency words, negation, quantifiers, condition
and contrast markers, numbers with units, code, and identifiers. A listed
difference needs a human decision, because some differences are legitimate
rewording. A clean result does not prove that the meaning is preserved.

Read-only. Standard library only. Pass the rewritten text alone, without any
"Needs clarification:" note.

Usage:
    ste-preserve.py SOURCE_FILE REWRITE_FILE [--json]
    ste-preserve.py --selftest

Exit 0 when no difference is found, 1 when differences are found, 2 on a
usage error.
"""
import json
import re
import sys
from collections import Counter


def _w(pattern):
    return re.compile(r"\b(?:" + pattern + r")\b")


# (category, [(canonical item, pattern)]) applied to lowercased prose.
# Inflections share one canonical item so a grammar-only change is not reported.
WORD_CATEGORIES = [
    ("modality", [
        ("may", _w("may")), ("might", _w("might")), ("could", _w("could")),
        ("can", _w("can")), ("should", _w("should")), ("must", _w("must")),
        ("shall", _w("shall")), ("ought to", _w(r"ought\s+to")),
        ("need to", _w(r"need(?:s|ed)?\s+to")),
        ("have to", _w(r"(?:has|have|had)\s+to")),
        ("require", _w(r"requir(?:e|es|ed|ing|ement|ements)")),
        ("optional", _w(r"optional(?:ly)?")),
        ("recommend", _w(r"recommend(?:s|ed|ation)?")),
    ]),
    ("hedges", [
        ("possible", _w(r"possibl[ey]")), ("probable", _w(r"probabl[ey]")),
        ("likely", _w("likely")), ("unlikely", _w("unlikely")),
        ("perhaps", _w("perhaps")), ("maybe", _w("maybe")),
        ("appear", _w(r"appear(?:s|ed|ing)?")), ("seem", _w(r"seem(?:s|ed|ing)?")),
        ("apparently", _w("apparently")), ("potential", _w(r"potential(?:ly)?")),
        ("presumably", _w("presumably")), ("suspect", _w(r"suspect(?:s|ed)?")),
        ("approximately", _w("approximately")), ("roughly", _w("roughly")),
    ]),
    ("frequency", [
        (word, _w(word)) for word in (
            "always", "usually", "often", "sometimes", "rarely", "occasionally",
            "typically", "generally", "frequently", "commonly", "seldom", "normally")
    ]),
    ("negation", [
        (word, _w(word)) for word in (
            "not", "no", "never", "none", "nothing", "neither", "nor", "without",
            "nobody", "nowhere")
    ]),
    ("quantifiers", [
        ("at most", _w(r"at\s+most")), ("at least", _w(r"at\s+least")),
        ("more than", _w(r"more\s+than")), ("less than", _w(r"less\s+than")),
        ("fewer than", _w(r"fewer\s+than")), ("up to", _w(r"up\s+to")),
        ("exactly", _w("exactly")),
        ("most", re.compile(r"(?<!\bat )\bmost\b")),
    ] + [(word, _w(word)) for word in (
        "all", "every", "each", "any", "some", "only", "both", "either",
        "several", "many", "few")]),
    ("conditions", [
        (word, _w(word)) for word in (
            "if", "unless", "when", "whenever", "until", "before", "after",
            "once", "except", "provided", "assuming", "otherwise")
    ]),
    ("contrast", [
        ("on the other hand", _w(r"on\s+the\s+other\s+hand")),
        ("in contrast", _w(r"in\s+contrast")),
        ("the opposite", _w(r"the\s+opposite")),
        ("rather than", _w(r"rather\s+than")),
    ] + [(word, _w(word)) for word in (
        "but", "however", "although", "though", "whereas", "yet", "despite",
        "instead", "conversely", "nevertheless", "nonetheless")]),
]

CONTRACTIONS = [
    (re.compile(r"\bcannot\b"), "can not"),
    (re.compile(r"\bcan't\b"), "can not"),
    (re.compile(r"\bwon't\b"), "will not"),
    (re.compile(r"\bshan't\b"), "shall not"),
    (re.compile(r"n't\b"), " not"),
]

WORD_NUMBERS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "twice": "2",
}
WORD_NUMBER_RE = _w("|".join(WORD_NUMBERS))

UNITS = {
    "%": "%", "ms": "ms", "s": "s", "sec": "s", "secs": "s", "second": "s",
    "seconds": "s", "min": "min", "mins": "min", "minute": "min",
    "minutes": "min", "h": "h", "hr": "h", "hrs": "h", "hour": "h",
    "hours": "h", "day": "d", "days": "d", "week": "wk", "weeks": "wk",
    "byte": "B", "bytes": "B",
}
NUMBER_RE = re.compile(
    r"(?<![\w.])(\d+(?:[.,:]\d+)*)"
    r"(?:\s*(%|(?:ms|secs?|seconds?|s|mins?|minutes?|hrs?|hours?|h|days?|weeks?"
    r"|bytes?|[kmgtp]i?b)\b))?",
    re.I,
)

FENCE_RE = re.compile(r"^ {0,3}(```|~~~)[^\n]*\n(.*?)^ {0,3}\1[ \t]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
URL_RE = re.compile(r"\bhttps?://[^\s<>()\"']+")
IDENTIFIER_RE = re.compile(r"""(?<![\w/.$~-])(
      --?[A-Za-z][\w-]*                    # command-line flags
    | (?:~|\.{1,2})?/[\w.$~{}/-]+          # absolute or home-relative paths
    | [\w$~.{}-]+/[\w$~.{}/-]+             # relative paths
    | [A-Za-z_]\w*_\w+                     # snake_case and SCREAMING_SNAKE
    | [a-z]+[A-Z]\w*                       # camelCase
    | [A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+      # dotted names and file names
    | \$\{?[A-Za-z_]\w*\}?                 # shell variables
)""", re.X)
IDENTIFIER_STOPLIST = {"e.g", "i.e", "and/or", "vs"}
TRAILING_PUNCT = ".,;:!?"


def _number_item(digits, unit):
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", digits):
        digits = digits.replace(",", "")
    if not unit:
        return digits
    unit = unit.lower()
    if unit not in UNITS and re.fullmatch(r"[kmgtp]i?b", unit):
        return f"{digits} {unit.upper()}"
    return f"{digits} {UNITS.get(unit, unit)}"


def extract(text):
    """Return {category: Counter} of the meaning markers in one text."""
    text = text.replace("\r\n", "\n").replace("’", "'").replace("‘", "'")
    found = {name: Counter() for name, _ in WORD_CATEGORIES}
    found.update(numbers=Counter(), code=Counter(), identifiers=Counter())

    def take_fence(match):
        body = "\n".join(line.rstrip() for line in match.group(2).strip("\n").split("\n"))
        found["code"][f"[block] {body}"] += 1
        return "\n"

    prose = FENCE_RE.sub(take_fence, text)
    for match in INLINE_CODE_RE.finditer(prose):
        found["code"][f"`{match.group(1)}`"] += 1
    prose = INLINE_CODE_RE.sub(" ", prose)
    for match in URL_RE.finditer(prose):
        found["code"][match.group(0).rstrip(TRAILING_PUNCT)] += 1
    prose = URL_RE.sub(" ", prose)

    for match in IDENTIFIER_RE.finditer(prose):
        item = match.group(1).rstrip(TRAILING_PUNCT)
        if item.lower() not in IDENTIFIER_STOPLIST and len(item) > 1:
            found["identifiers"][item] += 1

    for match in NUMBER_RE.finditer(prose):
        found["numbers"][_number_item(match.group(1), match.group(2))] += 1

    lowered = prose.lower()
    for pattern, replacement in CONTRACTIONS:
        lowered = pattern.sub(replacement, lowered)
    for match in WORD_NUMBER_RE.finditer(lowered):
        found["numbers"][WORD_NUMBERS[match.group(0)]] += 1
    for name, terms in WORD_CATEGORIES:
        for item, pattern in terms:
            count = len(pattern.findall(lowered))
            if count:
                found[name][item] += count
    return found


def compare(source, rewrite):
    """Return {category: [(item, source_count, rewrite_count)]} for differences."""
    before, after = extract(source), extract(rewrite)
    differences = {}
    for name in before:
        rows = []
        for item in sorted(set(before[name]) | set(after[name])):
            if before[name][item] != after[name][item]:
                rows.append((item, before[name][item], after[name][item]))
        if rows:
            differences[name] = rows
    return differences


def report(differences, as_json):
    if as_json:
        print(json.dumps({
            "differences": {
                name: [{"item": item, "source": src, "rewrite": rw}
                       for item, src, rw in rows]
                for name, rows in differences.items()},
            "count": sum(len(rows) for rows in differences.values()),
        }, indent=2))
        return
    if not differences:
        print("No marker differences found.")
    for name, rows in differences.items():
        print(f"{name}: " + "; ".join(f"{item} {src} -> {rw}" for item, src, rw in rows))
    print("Review each listed difference. A clean result does not prove the meaning is preserved.")


def selftest():
    assert compare("Retry at most 3 times.", "Retry at most 3 times.") == {}
    assert compare("You should wait.", "You must wait.")["modality"] == [
        ("must", 0, 1), ("should", 1, 0)]
    assert "hedges" not in compare("It may have failed.", "It may have failed.")
    assert compare("It may have failed.", "It failed.")["modality"] == [("may", 1, 0)]
    assert compare("Wait 30 seconds.", "Wait 30 s.") == {}
    assert compare("Retry three times.", "Retry 3 times.") == {}
    assert compare("Don't retry.", "Do not retry.") == {}
    assert compare("Set `max_retries`.", "Set `max-retries`.")["code"] == [
        ("`max-retries`", 0, 1), ("`max_retries`", 1, 0)]
    assert compare("Run `must_run`.", "Run `must_run`.") == {}
    assert compare("A is fast but uses memory.", "A is fast. It uses memory.")["contrast"] == [
        ("but", 1, 0)]
    print("selftest OK")


def main(argv):
    if "--selftest" in argv:
        selftest()
        return 0
    as_json = "--json" in argv
    paths = [arg for arg in argv if not arg.startswith("--")]
    unknown = [arg for arg in argv if arg.startswith("--") and arg != "--json"]
    if len(paths) != 2 or unknown:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    with open(paths[0], encoding="utf-8") as handle:
        source = handle.read()
    with open(paths[1], encoding="utf-8") as handle:
        rewrite = handle.read()
    differences = compare(source, rewrite)
    report(differences, as_json)
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
