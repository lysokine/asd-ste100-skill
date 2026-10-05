#!/usr/bin/env python3
"""List meaning markers that differ between a source text and its rewrite.

Compares modality, hedges, frequency words, negation, quantifiers, condition
and contrast markers, signed numbers with units, and code (code spans, fenced
blocks, URLs, and identifiers such as flags, paths, snake_case, and H100). A
listed difference needs a human decision, because some differences are
legitimate rewording. A clean result does not prove that the meaning is
preserved.

Read-only. Standard library only. Pass the rewritten text alone, without any
"Needs clarification:" or "Strict not applied:" note.

Usage:
    ste-preserve.py SOURCE_FILE REWRITE_FILE [--json]
    ste-preserve.py --selftest

Exit 0 when no difference is found, 1 when differences are found, 2 on a
usage error or an unreadable file.
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
        ("will", _w("will")), ("would", _w("would")),
        ("shall", _w("shall")), ("ought to", _w(r"ought\s+to")),
        ("need to", _w(r"need(?:s|ed)?\s+to")),
        ("have to", _w(r"(?:has|have|had)\s+to")),
        ("require", _w(r"requir(?:e|es|ed|ing|ement|ements)")),
        ("optional", _w(r"optional(?:ly)?")),
        ("recommend", _w(r"recommend(?:s|ed|ation)?")),
    ]),
    ("hedges", [
        ("possible", _w(r"possibl[ey]|possibilit(?:y|ies)")),
        ("probable", _w(r"probabl[ey]|probabilit(?:y|ies)")),
        ("likely", _w("likely")), ("unlikely", _w("unlikely")),
        ("perhaps", _w("perhaps")), ("maybe", _w("maybe")),
        ("appear", _w(r"appear(?:s|ed|ing)?")), ("seem", _w(r"seem(?:s|ed|ing)?")),
        ("apparently", _w("apparently")), ("potential", _w(r"potential(?:ly)?")),
        ("presumably", _w("presumably")), ("suspect", _w(r"suspect(?:s|ed)?")),
        ("approximately", _w("approximately")), ("roughly", _w("roughly")),
        ("about (number)", re.compile(r"\b(?:about|around)(?=\s+[-+]?\d)")),
        ("unclear", _w("unclear")), ("uncertain", _w(r"uncertain(?:ty|ties)?")),
        ("unknown", _w("unknown")), ("unsure", _w("unsure")),
        ("whether", _w("whether")), ("think", _w(r"thinks?")),
        ("believe", _w(r"believ(?:e|es|ed)")),
        ("assume", _w(r"assum(?:e|es|ed|ption|ptions)")),
        ("expect", _w(r"expect(?:s|ed)?")),
        ("hypothesis", _w(r"hypothes(?:is|es|ize|izes|ized)")),
        ("tend to", _w(r"tend(?:s|ed)?\s+to")),
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
    # Symbols (>=, <, ~5, ...) are added to this category separately; see COMPARISON_SYMBOLS.
    ("comparison", [
        ("or more", _w(r"or\s+more")), ("or fewer", _w(r"or\s+fewer")),
        ("or less", _w(r"or\s+less")), ("greater than", _w(r"greater\s+than")),
    ]),
    ("conditions", [
        (word, _w(word)) for word in (
            "if", "unless", "when", "whenever", "until", "before", "after",
            "once", "except", "provided", "assuming", "otherwise")
    ]),
    ("alternatives", [("or", _w("or"))]),
    ("contrast", [
        ("on the other hand", _w(r"on\s+the\s+other\s+hand")),
        ("in contrast", _w(r"in\s+contrast")),
        ("the opposite", _w(r"the\s+opposite")),
        ("rather than", _w(r"rather\s+than")),
    ] + [(word, _w(word)) for word in (
        "but", "however", "although", "though", "whereas", "yet", "despite",
        "instead", "conversely", "nevertheless", "nonetheless")]),
]

# Condition and contrast markers move legitimately when a clause is fronted, so
# only these categories are checked for order.
ORDER_CATEGORIES = ("modality", "hedges", "quantifiers", "negation")

# Arrows (->, =>, <-) and doubled operators (==, <<) are not comparisons.
COMPARISON_SYMBOLS = [
    ("≥", re.compile(r"≥|⩾|>=")),
    ("≤", re.compile(r"≤|⩽|<=")),
    ("≠", re.compile(r"≠|!=")),
    ("≈", re.compile(r"≈|(?<![\w~])~(?=\s*[-+]?\.?\d)")),
    (">", re.compile(r"(?<![-=>])>(?![=>])")),
    ("<", re.compile(r"(?<!<)<(?![=<-])")),
    ("=", re.compile(r"(?<![=!<>])=(?![=>])")),
]
BLOCKQUOTE_RE = re.compile(r"^[ \t]*(?:>[ \t]?)+", re.M)

CONTRACTIONS = [
    (re.compile(r"\bcannot\b"), "can not"),
    (re.compile(r"\bcan't\b"), "can not"),
    (re.compile(r"\bwon't\b"), "will not"),
    (re.compile(r"\bshan't\b"), "shall not"),
    (re.compile(r"n't\b"), " not"),
]

# "one" is left out: as a pronoun or determiner it is too common to track.
WORD_NUMBERS = {
    "zero": "0", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "twice": "2",
}
WORD_NUMBER_RE = re.compile(r"\b(?:" + "|".join(WORD_NUMBERS) + r")\b", re.I)

UNITS = {
    "%": "%", "percent": "%", "ms": "ms", "s": "s", "sec": "s", "secs": "s",
    "second": "s", "seconds": "s", "min": "min", "mins": "min", "minute": "min",
    "minutes": "min", "h": "h", "hr": "h", "hrs": "h", "hour": "h",
    "hours": "h", "day": "d", "days": "d", "week": "wk", "weeks": "wk",
    "wk": "wk", "wks": "wk", "byte": "B", "bytes": "B",
}
NUMBER_RE = re.compile(
    r"(?<![\w.])([-+]?(?:\d+(?:[.,:]\d+)*|\.\d+)(?:[eE][-+]?\d+)?)"
    r"(?:\s*(%|(?:ms|secs?|seconds?|s|mins?|minutes?|hrs?|hours?|h|days?|weeks?|wks?"
    r"|percent|bytes?|[kmgtp]i?b)\b))?",
    re.I,
)

# A closing fence repeats the opening fence character at least as many times.
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[^\n]*\n(.*?)^ {0,3}\1[`~]*[ \t]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
URL_RE = re.compile(r"\bhttps?://(?:[^\s<>()\"']|\([^\s<>()\"']*\))+")
IDENTIFIER_RE = re.compile(r"""(?<![\w/.$~-])(
      --?[A-Za-z][\w-]*                    # command-line flags
    | (?:~|\.{1,2})?/[\w.$~{}/-]+          # absolute or home-relative paths
    | [\w$~.{}-]+/[\w$~.{}/-]+             # relative paths
    | [A-Za-z_]\w*_\w+                     # snake_case and SCREAMING_SNAKE
    | [a-z]+[A-Z]\w*                       # camelCase
    | [A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+      # dotted names and file names
    | \$\{?[A-Za-z_]\w*\}?                 # shell variables
    | [A-Za-z]+\d[\w.-]*                   # letter+digit tokens: H100, v2, Python3
)""", re.X)
IDENTIFIER_STOPLIST = {"e.g", "i.e", "and/or", "vs"}
TRAILING_PUNCT = ".,;:!?"


def _number_item(digits, unit):
    if re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+", digits):
        digits = digits.replace(",", "")
    if not unit:
        return digits
    if re.fullmatch(r"[kmgtp]i?b", unit, re.I):
        # Keep the case of the final b: Mb (bits) and MB (bytes) differ.
        return f"{digits} {unit[0].upper()}{unit[1:-1].lower()}{unit[-1]}"
    return f"{digits} {UNITS.get(unit.lower(), unit.lower())}"


def _is_identifier(item):
    if item.lower() in IDENTIFIER_STOPLIST or len(item) < 2:
        return False
    # A single slash between plain words (read/write, A/B) is prose, not a path.
    if (item.count("/") == 1 and not item.startswith(("/", "~", "."))
            and not re.search(r"[.$~{}]", item)):
        return False
    return True


def extract(text):
    """Return {category: Counter} of the meaning markers in one text."""
    return _extract(text)[0]


def _extract(text):
    """Return ({category: Counter}, ordered markers) for one text.

    The ordered list holds the ORDER_CATEGORIES markers in document order, so a
    rewrite that swaps `should` and `must` between clauses can be detected even
    though the counts match.
    """
    text = text.replace("\r\n", "\n")
    found = {name: Counter() for name, _ in WORD_CATEGORIES}
    found.update(numbers=Counter(), code=Counter())

    def take_fence(match):
        body = "\n".join(line.rstrip() for line in match.group(2).strip("\n").split("\n"))
        found["code"][f"[block] {body}"] += 1
        return "\n"

    def take_span(match):
        # Backticks are formatting: `--no-cache` and --no-cache are one item.
        content = match.group(1).strip()
        number = NUMBER_RE.fullmatch(content)
        if number:
            found["numbers"][_number_item(number.group(1), number.group(2))] += 1
        else:
            found["code"][content] += 1
        return " "

    def take_url(match):
        found["code"][match.group(0).rstrip(TRAILING_PUNCT)] += 1
        return " "

    def take_identifier(match):
        item = match.group(1).rstrip(TRAILING_PUNCT)
        if not _is_identifier(item):
            return match.group(0)
        found["code"][item] += 1
        return " " + match.group(0)[len(item):]

    prose = FENCE_RE.sub(take_fence, text)
    prose = INLINE_CODE_RE.sub(take_span, prose)
    prose = URL_RE.sub(take_url, prose)
    prose = IDENTIFIER_RE.sub(take_identifier, prose)

    # Normalize prose only after code is removed, so code is compared verbatim.
    prose = (prose.replace("’", "'").replace("‘", "'").replace("−", "-"))
    prose = WORD_NUMBER_RE.sub(lambda match: WORD_NUMBERS[match.group(0).lower()], prose)
    for match in NUMBER_RE.finditer(prose):
        found["numbers"][_number_item(match.group(1), match.group(2))] += 1
    unquoted = BLOCKQUOTE_RE.sub("", prose)
    for item, pattern in COMPARISON_SYMBOLS:
        count = len(pattern.findall(unquoted))
        if count:
            found["comparison"][item] += count

    lowered = re.sub(r"\s+", " ", prose.lower())
    for pattern, replacement in CONTRACTIONS:
        lowered = pattern.sub(replacement, lowered)
    ordered = []
    for name, terms in WORD_CATEGORIES:
        for item, pattern in terms:
            starts = [match.start() for match in pattern.finditer(lowered)]
            if starts:
                found[name][item] += len(starts)
                if name in ORDER_CATEGORIES:
                    ordered.extend((start, item) for start in starts)
    return found, [item for _, item in sorted(ordered)]


def _order_difference(before, after):
    """Return the differing middle of two marker sequences, or None if equal."""
    if before == after:
        return None
    head = 0
    while head < min(len(before), len(after)) and before[head] == after[head]:
        head += 1
    tail = 0
    while (tail < min(len(before), len(after)) - head
           and before[-1 - tail] == after[-1 - tail]):
        tail += 1
    return before[head:len(before) - tail], after[head:len(after) - tail]


def compare(source, rewrite):
    """Return {category: [(item, source, rewrite)]} for differences.

    Count rows give the item and its two counts. An "order" row appears only
    when the ORDER_CATEGORIES markers have identical counts but a different
    sequence; it gives the two differing sub-sequences as strings.
    """
    (before, seq_before), (after, seq_after) = _extract(source), _extract(rewrite)
    differences = {}
    for name in before:
        rows = []
        for item in sorted(set(before[name]) | set(after[name])):
            if before[name][item] != after[name][item]:
                rows.append((item, before[name][item], after[name][item]))
        if rows:
            differences[name] = rows
    if Counter(seq_before) == Counter(seq_after):
        moved = _order_difference(seq_before, seq_after)
        if moved:
            differences["order"] = [("sequence", ", ".join(moved[0]), ", ".join(moved[1]))]
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
        print("No marker differences found. That does not prove the meaning is preserved.")
        return
    for name, rows in differences.items():
        if name == "order":
            print("order: " + "; ".join(f"{src} -> {rw}" for _, src, rw in rows))
        else:
            print(f"{name}: " + "; ".join(f"{item} {src} -> {rw}" for item, src, rw in rows))
    print("Review each listed difference; some are legitimate rewording.")


def selftest():
    assert compare("Retry at most 3 times.", "Retry at most 3 times.") == {}
    assert compare("You should wait.", "You must wait.")["modality"] == [
        ("must", 0, 1), ("should", 1, 0)]
    assert compare("It may have failed.", "It failed.")["modality"] == [("may", 1, 0)]
    assert compare("We think it is a race.", "It is a race.")["hedges"] == [("think", 1, 0)]
    assert compare("Wait 30 seconds.", "Wait 30 s.") == {}
    assert compare("Retry three times.", "Retry 3 times.") == {}
    assert compare("Don't retry.", "Do not retry.") == {}
    assert compare("Set `max_retries`.", "Set `max-retries`.")["code"] == [
        ("max-retries", 0, 1), ("max_retries", 1, 0)]
    assert compare("Use --no-cache.", "Use `--no-cache`.") == {}
    assert compare("Run `must_run`.", "Run `must_run`.") == {}
    assert compare("A is fast but uses memory.", "A is fast. It uses memory.")["contrast"] == [
        ("but", 1, 0)]
    assert compare("Keep SNR >= 5.", "Keep SNR ≥ 5.") == {}
    assert compare("Keep SNR ≥5.", "Keep SNR >5.")["comparison"] == [(">", 0, 1), ("≥", 1, 0)]
    assert compare("A -> B => C == D <- E", "A, B, C, D, E") == {}
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
    try:
        with open(paths[0], encoding="utf-8") as handle:
            source = handle.read()
        with open(paths[1], encoding="utf-8") as handle:
            rewrite = handle.read()
    except (OSError, UnicodeDecodeError) as error:
        print(f"ste-preserve: {error}", file=sys.stderr)
        return 2
    differences = compare(source, rewrite)
    report(differences, as_json)
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
